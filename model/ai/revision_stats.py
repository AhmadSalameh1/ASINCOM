"""Statistics requested by the mock review (paper/reviews): checks of leakage, paired differences, recalibration
variability and the coverage of the action selected by L2.

  1. grouped split   L1 and L2 rebuilt with train/calibration/test split by START DAY (no start day shared),
                     compared with the random episode split used so far
  2. paired tests    common random numbers make every comparison paired:
                     - service (loss <= L*) tree vs players, L2 vs tree: exact McNemar test and 95 % CI of the
                       paired difference (bootstrap)
                     - mean loss differences: paired bootstrap 95 % CI
  3. recalibration   the 100-episode recalibration of L1 repeated over 200 resamples: coverage mean, SD, width
  5. ablation       L1 point models (per-type mean, notice only, state only, both) under the grouped split
  4. selection       L2 chooses the action after seeing 8 bounds, so per-action coverage does not carry over to the
                     chosen action. Reported: empirical coverage of the chosen action's bound, the share of each branch
                     of the decision rule, and a joint calibration (score max_a (y_a - q_a)) for comparison

Usage:
    python revision_stats.py [--out results]
"""
import argparse
import os
import warnings

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from common import ACTIONS, FEATURES, RUNS, SEED, load, split_within
from l1_predict import ALPHA, GBM, L1, TARGET, TypeMean, ablation, conformal_quantile
from l2_decide import L2, L_STAR, outcome
from l3_explain import distil, tree_policy

warnings.filterwarnings("ignore")
B = 2000


def split_grouped(d, seed=SEED, frac=(0.6, 0.2)):
    days = np.array(sorted(d.start.unique()))
    rng = np.random.default_rng(seed)
    rng.shuffle(days)
    a, b = int(frac[0] * len(days)), int((frac[0] + frac[1]) * len(days))
    tr, ca = set(days[:a]), set(days[a:b])
    return d[d.start.isin(tr)], d[d.start.isin(ca)], d[~d.start.isin(tr | ca)]


def mcnemar(a, b):
    """Exact McNemar test on paired booleans a (policy A ok) and b (policy B ok)."""
    n01, n10 = int((~a & b).sum()), int((a & ~b).sum())
    p = binomtest(n10, n01 + n10, 0.5).pvalue if n01 + n10 else 1.0
    return n10, n01, p


def boot_ci(x, rng):
    m = np.array([x[rng.integers(0, len(x), len(x))].mean() for _ in range(B)])
    return float(x.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def realised(d, choice, col="y_tot"):
    return np.array([d.at[i, f"{col}_{a}"] for i, a in choice.items()])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"))
    ap.add_argument("--only5", action="store_true", help="compute section 5 only and append it to the existing file")
    a = ap.parse_args()
    rng = np.random.default_rng(SEED)
    md = ["# Revision statistics (answers to the mock review)\n"]
    data = {r: load(r) for r in RUNS}
    cert = load("normal_2", cert=True)
    if a.only5:
        md = section5(data)
        path = os.path.join(a.out, "revision_stats.md")
        old = open(path).read().split("\n## 5.")[0].rstrip("\n")
        with open(path, "w") as fh:
            fh.write(old + "\n" + "\n".join(md) + "\n")
        print("\n".join(md))
        return

    # ---------------------------------------------------------------- 1. grouped split
    md.append("## 1. Random vs grouped (by start day) split, built on normal 2\n")
    md.append("| split | L1 MAE held-out | L1 coverage held-out | L1 coverage cert. sample | L2 lost held-out | players lost held-out | L2 service cert. | players service cert. |")
    md.append("|---|---|---|---|---|---|---|---|")
    for name, fn in [("random episodes", split_within), ("grouped by start day", split_grouped)]:
        tr, cal, te = fn(data["normal_2"])
        l1 = L1().fit(tr, cal)
        mae = float(np.mean(np.abs(l1.predict(te) - te[TARGET])))
        cov = float(np.mean(te[TARGET].values <= l1.upper(te)))
        covc = float(np.mean(cert[TARGET].values <= l1.upper(cert)))
        l2 = L2().fit(tr, cal)
        o = outcome(te, l2.choose(te), L_STAR)
        op = outcome(te, pd.Series("none", index=te.index), L_STAR)
        sc = float((realised(cert, l2.choose(cert)) <= L_STAR + 1e-9).mean())
        sp = float((cert.y_tot_none <= L_STAR + 1e-9).mean())
        md.append(f"| {name} (test n={len(te)}) | {mae:.3f} | {cov:.1%} | {covc:.1%} | {o['lost_days']:.3f} | "
                  f"{op['lost_days']:.3f} | {sc:.1%} | {sp:.1%} |")

    # ---------------------------------------------------------------- 2. paired tests (certification sample)
    tr, cal, te = split_within(data["normal_2"])
    model = L2().fit(tr, cal)
    tree = distil(model, pd.concat([tr, cal]), 3)
    md.append("\n## 2. Paired comparisons (common random numbers)\n")
    md.append("Service = share of episodes with 60-day loss <= L*. McNemar: exact two-sided test on discordant pairs. "
              "Differences: mean and paired bootstrap 95 % CI.\n")
    md.append("| sample | comparison | A | B | B - A (95 % CI) | discordant B>A / A>B | McNemar p |")
    md.append("|---|---|---|---|---|---|---|")
    perm = np.random.default_rng(2027).permutation(2000)
    sets = [("Y1 certification sample (n=2000)", cert, model, tree)]
    for r in ["fraud_2", "fraud_3"]:
        tgt = data[r].iloc[perm]
        ta, ca, rem = tgt.iloc[:300], tgt.iloc[300:400], tgt.iloc[400:]
        ma = L2().fit(pd.concat([tr, ta]), ca)
        sets.append((f"{r} other 1,600 (adapted)", rem, ma, distil(ma, pd.concat([tr, cal, ta, ca]), 3)))
        sets.append((f"{r} other 1,600 (built on normal 2)", rem, model, tree))
    for sname, d, m_, t_ in sets:
        pol = {"players": pd.Series("none", index=d.index), "L2": m_.choose(d), "tree": tree_policy(t_, d)}
        ok = {k: realised(d, v) <= L_STAR + 1e-9 for k, v in pol.items()}
        loss = {k: realised(d, v) for k, v in pol.items()}
        for A, Bn in [("players", "tree"), ("players", "L2"), ("tree", "L2")]:
            diff = ok[Bn].astype(float) - ok[A].astype(float)
            mean, lo, hi = boot_ci(diff, rng)
            n10, n01, p = mcnemar(ok[Bn], ok[A])
            md.append(f"| {sname} | service {Bn} vs {A} | {ok[A].mean():.1%} | {ok[Bn].mean():.1%} | "
                      f"{mean:+.1%} ({lo:+.1%}, {hi:+.1%}) | {n10} / {n01} | {p:.2g} |")
        for A, Bn in [("players", "tree"), ("players", "L2")]:
            mean, lo, hi = boot_ci(loss[Bn] - loss[A], rng)
            md.append(f"| {sname} | loss (days) {Bn} vs {A} | {loss[A].mean():.3f} | {loss[Bn].mean():.3f} | "
                      f"{mean:+.3f} ({lo:+.3f}, {hi:+.3f}) | | |")
    # held-out normal 2 L2 vs players (as reported in the L2 section)
    ch = model.choose(te)
    mean, lo, hi = boot_ci(realised(te, ch) - te.y_tot_none.values, rng)
    md.append(f"| Y1 held-out (n={len(te)}) | loss (days) L2 vs players | {te.y_tot_none.mean():.3f} | "
              f"{realised(te, ch).mean():.3f} | {mean:+.3f} ({lo:+.3f}, {hi:+.3f}) | | |")

    # ---------------------------------------------------------------- 3. recalibration resamples
    md.append("\n## 3. L1 recalibration on 100 target episodes, 200 resamples\n")
    md.append("| target | coverage mean | SD | 5-95 % | mean bound (days) | build-year bound (days) |")
    md.append("|---|---|---|---|---|---|")
    l1 = L1().fit(tr, cal)
    for r in ["fraud_2", "fraud_3"]:
        d = data[r]
        covs, widths = [], []
        for k in range(200):
            p = np.random.default_rng(1000 + k).permutation(len(d))
            rc, rest = d.iloc[p[:100]], d.iloc[p[100:]]
            c = conformal_quantile(rc[TARGET].values - l1.q.predict(rc[FEATURES]), ALPHA)
            u = l1.q.predict(rest[FEATURES]) + c
            covs.append(np.mean(rest[TARGET].values <= u))
            widths.append(np.mean(u))
        covs = np.array(covs)
        md.append(f"| {r} | {covs.mean():.1%} | {covs.std():.1%} | {np.percentile(covs, 5):.1%}-{np.percentile(covs, 95):.1%} | "
                  f"{np.mean(widths):.2f} | {np.mean(l1.upper(d)):.2f} |")

    # ---------------------------------------------------------------- 4. selection and joint calibration
    md.append("\n## 4. L2: coverage of the chosen action's bound, branches, joint calibration\n")
    Q = {a_: model.q[a_].predict(cal[FEATURES]) for a_ in ACTIONS}
    joint = conformal_quantile(np.max(np.column_stack([cal[f"y_tot_{a_}"].values - Q[a_] for a_ in ACTIONS]), axis=1), ALPHA)
    md.append(f"Per-action conformal corrections: {', '.join(f'{a_} {model.c[a_]:.2f}' for a_ in ACTIONS)}; "
              f"joint (max over actions) correction: {joint:.2f} days.\n")
    md.append("| sample | branch | share | Pr(Y_chosen <= U_chosen), per-action | Pr(Y_chosen <= L*) |")
    md.append("|---|---|---|---|---|")
    for sname, d in [("Y1 held-out", te), ("Y1 certification sample", cert)]:
        U = model.bounds(d)
        chs = model.choose(d)
        y = realised(d, chs)
        u = np.array([U.iloc[k][a_] for k, a_ in enumerate(chs)])
        branch = np.where(U["none"].values <= L_STAR, "no response (U_none <= L*)",
                          np.where(U.min(axis=1).values <= L_STAR, "cheapest feasible action", "lowest bound (none feasible)"))
        for b in ["no response (U_none <= L*)", "cheapest feasible action", "lowest bound (none feasible)"]:
            m = branch == b
            if m.any():
                md.append(f"| {sname} | {b} | {m.mean():.1%} | {np.mean(y[m] <= u[m]):.1%} | {np.mean(y[m] <= L_STAR + 1e-9):.1%} |")
        md.append(f"| {sname} | all | 100 % | {np.mean(y <= u):.1%} | {np.mean(y <= L_STAR + 1e-9):.1%} |")
    md += section5(data)
    with open(os.path.join(a.out, "revision_stats.md"), "w") as fh:
        fh.write("\n".join(md) + "\n")
    print("\n".join(md))


def section5(data):
    # ---------------------------------------------------------------- 5. L1 ablation under the grouped split
    md = []
    md.append("\n## 5. L1 point models, grouped split (held-out start days of normal 2), MAE in days\n")
    tr, cal, te = split_grouped(data["normal_2"])
    abl = ablation(tr, {"held-out": te})
    md.append("| model | MAE | Spearman |")
    md.append("|---|---|---|")
    tm = TypeMean().fit(tr)
    md.append(f"| per-type mean | {np.mean(np.abs(tm.predict(te) - te[TARGET].values)):.3f} | |")
    for _, r in abl.iterrows():
        md.append(f"| {r.model} | {r.MAE_days:.3f} | {r.spearman:.2f} |")
    return md


if __name__ == "__main__":
    main()
