"""Twin-rollout baseline (sample-average approximation), requested by the mock review.

At the notice, the planner with a validated twin can simulate each action from the observed state. For every test
episode and action, K rollouts are run with the episode's own history up to the notice day and fresh lead-time
randomness after it (Twin(reseed_from=...)). The rollout policy picks the action with the lowest mean simulated
60-day loss (all products); ties go to the cheaper action. Its realised outcome is then read from the episode
itself (the same run as for every other policy), so all comparisons are paired.

Compared on the same episodes: players (no response), L2, the tree, the oracle.

Usage:
    python rollout_baseline.py [--n 1000] [--k 4] [--out results]
"""
import argparse
import json
import os
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "twin"))
from controllers import ResponseController  # noqa: E402
from twin import Twin  # noqa: E402

from common import ACTIONS, SEED, load, split_within  # noqa: E402
from episodes import ACTIONS as LEVERS, HORIZON, inventory_value, scenario  # noqa: E402
from l2_decide import L2, L_STAR, oracle, outcome  # noqa: E402
from l3_explain import distil, tree_policy  # noqa: E402

INPUTS = os.path.join(HERE, "..", "twin", "inputs")
PRICES = json.load(open(os.path.join(HERE, "..", "..", "data", "prices", "prices.json")))
_INP = {}


def _inp(run):
    if run not in _INP:
        _INP[run] = json.load(open(os.path.join(INPUTS, f"{run}.json")))
    return _INP[run]


def disruption(row):
    d = {k: row[k] for k in ["type", "e1_rel", "e2_share", "e2_allfood", "e3_days", "e4_factor", "e5_days"]}
    d["e2_allfood"] = int(d["e2_allfood"])
    d["e3_days"], d["e5_days"] = int(d["e3_days"]), int(d["e5_days"])
    return d


def rollouts(job):
    run, s, seed, d, k, dem = job
    inp = _inp(run)
    sc = scenario(d, s)
    out = []
    for name, po, fg, ship, prio in LEVERS:
        losses, invs = [], []
        for j in range(k):
            ctl = ResponseController(inp, s, po, fg, ship, prio)
            df = Twin(inp, seed=seed, demand_mode="replay", policy="controller", controller=ctl, scenario=sc,
                      lead_stream="keyed", reseed_from=(s, 10_000_000 + 1000 * seed + j)).run().set_index("day")
            w = df.loc[s:s + HORIZON - 1]
            losses.append(float((w.lost + w.lost_other).sum()) / dem)
            invs.append(float(inventory_value(w, inp["components"], PRICES[run]).mean()))
        out.append((name, float(np.mean(losses)), float(np.mean(invs))))
    best = min(out, key=lambda t: (round(t[1], 9), t[2]))
    return best[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--out", default=os.path.join(HERE, "results"))
    a = ap.parse_args()
    tr, cal, te = split_within(load("normal_2"))
    model = L2().fit(tr, cal)
    tree = distil(model, pd.concat([tr, cal]), 3)
    md = [f"# Twin-rollout baseline (K = {a.k} rollouts per action, lowest mean simulated loss)\n",
          "Realised outcomes on the same episodes for every policy (paired). L* = 1 day of demand.\n",
          "| sample | policy | lost (days) | service (loss <= L*) | added inventory (EUR) | acted |", "|---|---|---|---|---|---|"]
    perm = np.random.default_rng(2027).permutation(2000)
    samples = [("Y1 certification sample", load("normal_2", cert=True).iloc[:a.n], "normal_2", model, tree)]
    d2 = load("fraud_2").iloc[perm]
    ta, ca = d2.iloc[:300], d2.iloc[300:400]
    ma = L2().fit(pd.concat([tr, ta]), ca)
    samples.append(("fraud 2, other episodes (L2/tree adapted)", d2.iloc[400:400 + a.n], "fraud_2", ma,
                    distil(ma, pd.concat([tr, cal, ta, ca]), 3)))
    raw = {"normal_2": pd.read_csv(os.path.join(HERE, "data", "episodes_normal_2_cert.csv.gz")),
           "fraud_2": pd.read_csv(os.path.join(HERE, "data", "episodes_fraud_2.csv.gz"))}
    for sname, d, run, m_, t_ in samples:
        r = raw[run].set_index("episode")
        jobs = []
        for _, row in d.iterrows():
            dd = disruption(row)
            if dd["type"] == "E2" and not dd["e2_allfood"]:
                dd["e2_material"] = recover_material(run, int(row.episode))
            jobs.append((run, int(row.start), int(row.seed), dd, a.k, float(row.dem)))
        with Pool(os.cpu_count()) as pool:
            ch = pool.map(rollouts, jobs, chunksize=2)
        pol = {"players (no response)": pd.Series("none", index=d.index), "L2": m_.choose(d),
               "tree": tree_policy(t_, d), "**twin rollout (SAA)**": pd.Series(ch, index=d.index),
               "oracle": oracle(d, L_STAR)}
        for p, c in pol.items():
            o = outcome(d, c, L_STAR)
            md.append(f"| {sname} (n={len(d)}) | {p} | {o['lost_days']:.3f} | {1 - o['violation']:.1%} | "
                      f"{o['added_inv_eur']:,.0f} | {o['acted']:.0%} |")
        _ = r
    with open(os.path.join(a.out, "rollout_baseline.md"), "w") as fh:
        fh.write("\n".join(md) + "\n")
    print("\n".join(md))


def recover_material(run, episode):
    """Re-draw the episode list exactly as episodes.py did to recover the single E2 material (not stored)."""
    from episodes import FOOD, sample_disruption, start_days
    key = (run, "cert" if run == "normal_2" else "")
    if key not in _MAT:
        inp = _inp(run)
        days = start_days(inp)
        idx = ["normal_2", "fraud_2", "fraud_3"].index(run)
        rng = np.random.default_rng([2027, idx, 0] + ([1] if run == "normal_2" else []))
        mats = {}
        n = 2000
        for i in range(n):
            int(rng.choice(days))
            int(rng.integers(1_000_000))
            dd = sample_disruption(rng, False)
            mats[i] = dd.get("e2_material")
        _MAT[key] = mats
    m = _MAT[key][episode]
    assert m in FOOD
    return m


_MAT = {}

if __name__ == "__main__":
    main()
