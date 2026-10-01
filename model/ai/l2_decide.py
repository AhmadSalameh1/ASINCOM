"""L2 decide: a risk-constrained response policy over the players' three levers.

For every action a (common.ACTIONS; levers in model/twin/controllers.py, ResponseController):
  U_a(x)  conformal 90 % upper bound on the lost demand of all products over the 60 days after the notice
          (quantile model + split-conformal correction from the calibration set), in days of demand
  C_a(x)  predicted added inventory capital (material-cost value, days of demand), the price of the action
Rule: take the cheapest action whose bound meets the service limit, U_a(x) <= L*. If none does, take the action
with the lowest bound. No action is taken on faith: "do nothing" (the players' own plan) wins whenever it
already meets the limit, because it costs nothing extra.

Baselines (evaluated on the same episodes; every outcome is a twin run, common random numbers):
  players      no response (the recorded decisions)
  always-<a>   one fixed action for every disruption
  type-rule    per disruption type, the action with the lowest mean loss in training (cheapest on ties):
               what the Phase E impact table alone would recommend
  point-L2     the L2 rule with point predictions instead of conformal bounds (what the trust layer adds)
  oracle       knows the outcomes: the cheapest action that meets L*, else the one with the least loss

Protocol: as L1 (built on normal 2, tested on normal 2 held-out, fraud 2, fraud 3, STRESS). L* is stated, not
tuned: the headline is L* = 1 day of demand over 60 days (fill rate >= 98.3 %); a sweep is reported.
Two remedies for transfer to another player team (added after the first run showed that a policy built on
normal 2 does not transfer; all variants are reported):
  LOYO     built on two years (80 % train, 20 % calibration), tested on the third
  adapted  built on normal 2 plus 400 episodes of the target year (300 train, 100 calibration), tested on
           the other 1,600 target episodes

Usage:
    python l2_decide.py [--out results]
"""
import argparse
import os
import warnings

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

from common import ACTIONS, FEATURES, RUNS, SEED, TYPES, load, split_within
from l1_predict import ALPHA, GBM, conformal_quantile

warnings.filterwarnings("ignore")
L_STAR = 1.0
SWEEP = [0.25, 0.5, 1.0, 2.0, 4.0]


class L2:
    def __init__(self, l_star=L_STAR, features=FEATURES):
        self.l_star, self.f = l_star, features

    def fit(self, tr, cal):
        self.q, self.pt, self.c, self.cost = {}, {}, {}, {}
        for a in ACTIONS:
            y = tr[f"y_tot_{a}"]
            self.q[a] = LGBMRegressor(objective="quantile", alpha=ALPHA, **GBM).fit(tr[self.f], y)
            self.pt[a] = LGBMRegressor(**GBM).fit(tr[self.f], y)
            self.c[a] = conformal_quantile(cal[f"y_tot_{a}"].values - self.q[a].predict(cal[self.f]), ALPHA)
            self.cost[a] = LGBMRegressor(**GBM).fit(tr[self.f], tr[f"y_inv_{a}"]) if a != "none" else None
        return self

    def bounds(self, d):
        return pd.DataFrame({a: self.q[a].predict(d[self.f]) + self.c[a] for a in ACTIONS}, index=d.index)

    def points(self, d):
        return pd.DataFrame({a: self.pt[a].predict(d[self.f]) for a in ACTIONS}, index=d.index)

    def costs(self, d):
        return pd.DataFrame({a: (self.cost[a].predict(d[self.f]) if self.cost[a] is not None else np.zeros(len(d)))
                             for a in ACTIONS}, index=d.index)

    def choose(self, d, l_star=None, use_points=False):
        l_star = self.l_star if l_star is None else l_star
        U = self.points(d) if use_points else self.bounds(d)
        C = self.costs(d)
        return pd.Series([pick(U.iloc[k], C.iloc[k], l_star) for k in range(len(d))], index=d.index)


def pick(u, c, l_star):
    if u["none"] <= l_star:                      # the players' own plan meets the limit: no response
        return "none"
    ok = [a for a in ACTIONS if u[a] <= l_star]
    if ok:
        return min(ok, key=lambda a: (max(c[a], 0.0), ACTIONS.index(a)))
    return min(ACTIONS, key=lambda a: (u[a], max(c[a], 0.0)))


def outcome(d, choice, l_star):
    tot = np.array([d.at[i, f"y_tot_{a}"] for i, a in choice.items()])
    inv = np.array([d.at[i, f"y_inv_{a}"] for i, a in choice.items()])
    units = np.array([d.at[i, f"lost_{a}"] + d.at[i, f"lostother_{a}"] for i, a in choice.items()])
    eur = np.array([d.at[i, f"addinv_{a}"] for i, a in choice.items()])
    return {"lost_days": tot.mean(), "lost_units": units.mean(), "violation": (tot > l_star + 1e-9).mean(),
            "added_inv_days": inv.mean(), "added_inv_eur": eur.mean(),
            "acted": float((choice != "none").mean())}


def type_rule(tr):
    rule = {}
    for t in TYPES:
        g = tr[tr.type == t]
        rule[t] = min(ACTIONS, key=lambda a: (round(g[f"y_tot_{a}"].mean(), 6), g[f"y_inv_{a}"].mean()))
    return rule


def oracle(d, l_star):
    out = {}
    for i in d.index:
        ok = [a for a in ACTIONS if d.at[i, f"y_tot_{a}"] <= l_star + 1e-9]
        out[i] = (min(ok, key=lambda a: d.at[i, f"y_inv_{a}"]) if ok
                  else min(ACTIONS, key=lambda a: (d.at[i, f"y_tot_{a}"], d.at[i, f"y_inv_{a}"])))
    return pd.Series(out)


def compare(model, rule, sets, l_star):
    rows = []
    for sname, d in sets.items():
        pol = {"players (no response)": pd.Series("none", index=d.index)}
        for a in ACTIONS[1:]:
            pol[f"always {a}"] = pd.Series(a, index=d.index)
        pol["type-rule (Phase E table)"] = d.type.map(rule)
        pol["point-L2 (no conformal margin)"] = model.choose(d, l_star, use_points=True)
        pol["**L2 (conformal, risk-constrained)**"] = model.choose(d, l_star)
        pol["oracle (knows outcomes)"] = oracle(d, l_star)
        for p, ch in pol.items():
            rows.append({"set": sname, "policy": p, **outcome(d, ch, l_star)})
    return pd.DataFrame(rows)


def compare_core(model, rule, d, l_star):
    pol = {"players (no response)": pd.Series("none", index=d.index),
           "best fixed action in hindsight": None,
           "type-rule": d.type.map(rule), "L2": model.choose(d, l_star), "oracle": oracle(d, l_star)}
    best = min(ACTIONS, key=lambda a: d[f"y_tot_{a}"].mean())
    pol["best fixed action in hindsight"] = pd.Series(best, index=d.index)
    return [{"policy": p if p != "best fixed action in hindsight" else f"{p} ({best})", **outcome(d, ch, l_star)}
            for p, ch in pol.items()]



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    data = {r: load(r) for r in RUNS}
    stress = pd.concat([load(r, True) for r in RUNS], ignore_index=True)
    tr, cal, te = split_within(data["normal_2"])
    model = L2().fit(tr, cal)
    rule = type_rule(tr)
    sets = {"normal 2 held-out": te, "fraud 2": data["fraud_2"], "fraud 3": data["fraud_3"], "STRESS": stress}
    res = compare(model, rule, sets, L_STAR)
    res.to_csv(os.path.join(a.out, "l2_comparison.csv"), index=False)
    sweep = []
    for ls in SWEEP:
        for sname, d in sets.items():
            for pname, ch in [("players", pd.Series("none", index=d.index)), ("L2", model.choose(d, ls)),
                              ("point-L2", model.choose(d, ls, use_points=True)), ("oracle", oracle(d, ls))]:
                sweep.append({"L*": ls, "set": sname, "policy": pname, **outcome(d, ch, ls)})
    sweep = pd.DataFrame(sweep)
    sweep.to_csv(os.path.join(a.out, "l2_sweep.csv"), index=False)
    mix = {s: model.choose(d).value_counts(normalize=True).round(3).to_dict() for s, d in sets.items()}

    # ---- transfer remedies ----
    extra = []
    for test in ["normal_2", "fraud_2", "fraud_3"]:
        rest = pd.concat([data[r] for r in RUNS if r != test], ignore_index=True)
        t2, c2, _ = split_within(rest, frac=(0.8, 0.2))
        mdl = L2().fit(t2, c2)
        extra += [{"variant": "LOYO (built on the other two years)", "set": test, **r}
                  for r in compare_core(mdl, type_rule(t2), data[test], L_STAR)]
        if test != "normal_2":
            perm = np.random.default_rng(SEED).permutation(len(data[test]))
            tgt = data[test].iloc[perm]
            ta, ca, rem = tgt.iloc[:300], tgt.iloc[300:400], tgt.iloc[400:]
            mdl = L2().fit(pd.concat([tr, ta]), ca)
            extra += [{"variant": "adapted (normal 2 + 400 target episodes)", "set": test, **r}
                      for r in compare_core(mdl, type_rule(pd.concat([tr, ta])), rem, L_STAR)]
            extra += [{"variant": "built on normal 2 (same 1,600 episodes)", "set": test, **r}
                      for r in compare_core(model, rule, rem, L_STAR)]
    extra = pd.DataFrame(extra)
    extra.to_csv(os.path.join(a.out, "l2_transfer.csv"), index=False)
    md = [f"# L2 results: risk-constrained response (L* = {L_STAR} day of demand over 60 days)\n",
          f"Built on normal 2 ({len(tr)} train, {len(cal)} calibration episodes). type-rule: {rule}.\n",
          "lost = lost demand of all products over the 60 days after the notice; violation = share of episodes "
          "whose realised loss exceeds L*; added inventory = mean extra inventory capital (material cost) held over "
          "the 60 days.\n"]
    for s in sets:
        md.append(f"\n## {s}\n")
        md.append("| policy | lost (days of demand) | lost (units) | violation of L* | added inventory (days) | added inventory (EUR) | acted |")
        md.append("|---|---|---|---|---|---|---|")
        for _, r in res[res.set == s].iterrows():
            md.append(f"| {r.policy} | {r.lost_days:.3f} | {r.lost_units:,.0f} | {r.violation:.1%} | "
                      f"{r.added_inv_days:.3f} | {r.added_inv_eur:,.0f} | {r.acted:.0%} |")
        md.append(f"\nL2 action mix: {mix[s]}")
    md.append("\n## Transfer to another player team: remedies\n")
    md.append("| variant | test year | policy | lost (days) | violation | added inventory (EUR) | acted |")
    md.append("|---|---|---|---|---|---|---|")
    for _, r in extra.iterrows():
        md.append(f"| {r.variant} | {r.set} | {r.policy} | {r.lost_days:.3f} | {r.violation:.1%} | {r.added_inv_eur:,.0f} | {r.acted:.0%} |")
    md.append("\n## Sweep over the service limit L*\n")
    md.append("| L* | set | policy | lost (days) | violation | added inventory (EUR) | acted |")
    md.append("|---|---|---|---|---|---|---|")
    for _, r in sweep.iterrows():
        md.append(f"| {r['L*']} | {r.set} | {r.policy} | {r.lost_days:.3f} | {r.violation:.1%} | {r.added_inv_eur:,.0f} | {r.acted:.0%} |")
    with open(os.path.join(a.out, "l2_results.md"), "w") as fh:
        fh.write("\n".join(md) + "\n")
    print("\n".join(md[:60]))


if __name__ == "__main__":
    main()
