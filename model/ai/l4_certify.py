"""L4 certify: statistical guarantees for the explainable policy (the depth-3 tree from L3).

The certified object is the tree itself, the explanation a planner reads, not the black box behind it.
Property: "the lost demand of all products over the 60 days after a disruption notice stays within L*"
(a service guarantee), for disruptions drawn from the evidence-bounded catalogue at a random time.

Each test set is a sample of episodes never used to build or calibrate anything (independent seeds, start days
and disruptions), and every outcome is a twin run. So the satisfaction rate is a binomial proportion and its
95 % Clopper-Pearson interval is a valid certificate for that population:
  level 1  per year: normal 2 (the build year; an independent sample of 2,000 episodes generated from a
           separate random stream), fraud 2 and fraud 3 (other player teams)
  level 2  per disruption type (the worst type bounds every type)
  level 3  across years: the guarantee holds for a year if its lower bound >= p*; reported per year
Second property, do no harm: "the policy's loss exceeds the loss of the players' own plan by more than DELTA"
(DELTA = 0.05 days of demand), certified by an upper Clopper-Pearson bound on its rate. An intervention that
helps on average but often makes things worse would not be trustworthy.
For comparison, the same certificates for the players' own response (none) and for L2 (black box). The
certified level is reported (lower bound), not a pass/fail at an arbitrary p*: the attainable level is set
by line stoppages, which no lever can repair (even the best action in hindsight meets L* in only about 84 % of normal 2 episodes).
Because L2 built on normal 2 does not transfer to the other teams (l2_results.md), the fraud years are also
certified with the adapted tree (normal 2 + 400 target episodes), on the other 1,600 target episodes.
The STRESS set (beyond the evidence) is reported but is outside the certified population.

Usage:
    python l4_certify.py [--out results]
"""
import argparse
import os
import warnings

import numpy as np
import pandas as pd
from scipy.stats import beta

from common import TYPES, load
from l2_decide import L2, L_STAR
from l3_explain import build, distil, tree_policy

warnings.filterwarnings("ignore")
CONF = 0.95
DELTA = 0.05


def clopper_pearson(k, n, conf=CONF):
    lo = beta.ppf((1 - conf) / 2, k, n - k + 1) if k > 0 else 0.0
    hi = beta.ppf(1 - (1 - conf) / 2, k + 1, n - k) if k < n else 1.0
    return float(lo), float(hi)


def satisfied(d, choice, l_star):
    return np.array([d.at[i, f"y_tot_{a}"] <= l_star + 1e-9 for i, a in choice.items()])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"))
    a = ap.parse_args()
    data, tr, cal, te, sets = build()
    model = L2().fit(tr, cal)
    tree = distil(model, pd.concat([tr, cal]), 3)
    md = [f"# L4 results: certificates (L* = {L_STAR} day of demand over 60 days; 95 % Clopper-Pearson)\n",
          "Service: P(lost demand of all products over the 60 days after the notice <= L*), certified lower bound. "
          f"Harm: P(loss > players' loss + {DELTA} days), certified upper bound.\n",
          "| set | policy | n | service rate | certified service >= | worst type: certified service >= | harm rate | certified harm <= | added inventory (EUR) |",
          "|---|---|---|---|---|---|---|---|---|"]
    rows = []
    # normal 2 is certified on an independent sample (separate random stream, never used to build anything);
    # its 400 held-out build episodes would give needlessly wide intervals
    evals = [("normal 2, independent certification sample", load("normal_2", cert=True), None)]
    evals += [(s, d, None) for s, d in sets.items() if s != "normal 2 held-out"]
    perm = np.random.default_rng(2027).permutation(2000)
    for r in ["fraud_2", "fraud_3"]:
        tgt = data[r].iloc[perm]
        ta, ca, rem = tgt.iloc[:300], tgt.iloc[300:400], tgt.iloc[400:]
        ma = L2().fit(pd.concat([tr, ta]), ca)
        evals.append((f"{r.replace('_', ' ')}, other 1,600 episodes", rem, distil(ma, pd.concat([tr, cal, ta, ca]), 3)))
    for s, d, adapted in evals:
        pols = [("players (no response)", pd.Series("none", index=d.index)), ("L2 (black box)", model.choose(d)),
                ("**tree (explainable, certified)**", tree_policy(tree, d))]
        if adapted is not None:
            pols = [pols[0], ("tree built on normal 2", tree_policy(tree, d)), ("**adapted tree**", tree_policy(adapted, d))]
        for pname, ch in pols:
            ok = satisfied(d, ch, L_STAR)
            lo, hi = clopper_pearson(int(ok.sum()), len(ok))
            worst = []
            for t in TYPES:
                m = (d.type == t).values
                if m.any():
                    worst.append((clopper_pearson(int(ok[m].sum()), int(m.sum()))[0], t))
            wlo, wt = min(worst)
            harm = np.array([d.at[i, f"y_tot_{a}"] > d.at[i, "y_tot_none"] + DELTA for i, a in ch.items()])
            hlo, hhi = clopper_pearson(int(harm.sum()), len(harm))
            inv = float(np.mean([d.at[i, f"addinv_{a}"] for i, a in ch.items()]))
            rows.append({"set": s, "policy": pname, "n": len(ok), "service": ok.mean(), "service_lo": lo,
                         "worst_type": wt, "worst_lo": wlo, "harm": harm.mean(), "harm_hi": hhi, "added_inv_eur": inv})
            tag = " (outside the evidence)" if s == "STRESS" else ""
            md.append(f"| {s}{tag} | {pname} | {len(ok)} | {ok.mean():.1%} | {lo:.1%} | {wt}: {wlo:.1%} | "
                      f"{harm.mean():.1%} | {hhi:.1%} | {inv:,.0f} |")
    pd.DataFrame(rows).to_csv(os.path.join(a.out, "l4_certificates.csv"), index=False)
    md.append("\nReading: for disruptions drawn from the evidence-bounded catalogue at a random time in that year, the "
              "policy keeps the 60-day loss within L* with probability at least the certified service level, and makes "
              "things worse than the players' own plan with probability at most the certified harm level, both at 95 % "
              "confidence. The worst-type column bounds the service guarantee for every single disruption type.")
    with open(os.path.join(a.out, "l4_results.md"), "w") as fh:
        fh.write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
