"""Closed-loop comparison of controllers under the Phase E disruptions (first step of B).

For each controller and disruption: lost demand from the disruption start (median over seeds, each with a
randomised start day), and inventory cost proxies: mean component stock and mean DC stock over the same
period. All controllers see the same seeds and start days (common random numbers).

Usage:
    python policy_comparison.py inputs/normal_2.json [--seeds 40] [--out policies]
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from controllers import BufferController, ReplayController  # noqa: E402
from disruptions import scenarios, start_days  # noqa: E402
from twin import DCS, Twin  # noqa: E402

PICK = ["baseline", "E1 supplier delay|severe", "E2 quality loss|all food receipts: 4.1",
        "E3 line stoppage|3 days", "E3 line stoppage|10 days", "E4 demand|surge +19"]


def chosen():
    out = []
    for i, (name, sev, _, _) in enumerate(scenarios(0)):
        for p in PICK:
            n, _, s = p.partition("|")
            if name == n and (not s or sev.startswith(s)):
                out.append((i, f"{name} {sev}".strip()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs")
    ap.add_argument("--seeds", type=int, default=40)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "policies"))
    a = ap.parse_args()
    inp = json.load(open(a.inputs))
    starts = start_days(inp, a.seeds)
    controllers = [("players (replay)", lambda: ReplayController(inp))] + [
        (f"players + component buffer {k} d", (lambda k=k: BufferController(inp, k))) for k in (2, 5, 10)]
    lines = [f"# Controllers under disruption: {inp['run']}\n",
             f"{a.seeds} seeds, randomised start days over the steady months; values from the start day on.\n",
             "| disruption | controller | lost demand (median) | lost 95 % | mean component stock (units) | mean DC stock (units) |",
             "|---|---|---|---|---|---|"]
    for i, label in chosen():
        for cname, make in controllers:
            lost, comp, dcs = [], [], []
            for s, st in enumerate(starts):
                sc = scenarios(st)[i][2]
                df = Twin(inp, seed=s, demand_mode="replay", policy="controller", controller=make(),
                          scenario=sc).run().set_index("day").loc[st:]
                lost.append(df.lost.sum())
                comp.append(df[[f"stock_{c}" for c in inp["components"]]].sum(axis=1).mean())
                dcs.append(df[[f"dc_{d}" for d in DCS]].sum(axis=1).mean())
            lines.append(f"| {label} | {cname} | {np.median(lost):,.0f} | {np.percentile(lost, 95):,.0f} | "
                         f"{np.mean(comp):,.0f} | {np.mean(dcs):,.0f} |")
        print(lines[-4:] if False else "", end="")
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, f"{inp['run']}_controllers.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
