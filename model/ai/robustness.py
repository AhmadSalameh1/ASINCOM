"""Robustness check of the headline AI results against the shipping replay rule (validation Amendment 3).

The AI layers use deferred transfer replay. Plain replay strands stock at the plant, so it is a deliberately
pessimistic alternative. The same pipeline (L1 coverage, L2 comparison) is rebuilt on episodes generated with
plain replay (episodes.py --plain-push), with the same protocol: built on normal 2, tested on its held-out
episodes and on the other years.

Usage:
    python robustness.py [--out results]
"""
import argparse
import os
import warnings

import numpy as np
import pandas as pd

from common import RUNS, load, split_within
from l1_predict import L1, TARGET
from l2_decide import L2, L_STAR, compare_core, type_rule

warnings.filterwarnings("ignore")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"))
    a = ap.parse_args()
    md = ["# Robustness: AI results under plain transfer replay (pessimistic shipping)\n"]
    for suffix, label in [("", "deferred replay (nominal)"), ("_plainpush", "plain replay")]:
        data = {r: load(r, suffix=suffix) for r in RUNS}
        tr, cal, te = split_within(data["normal_2"])
        l1 = L1().fit(tr, cal)
        model, rule = L2().fit(tr, cal), type_rule(tr)
        md.append(f"\n## {label}\n")
        md.append("| test set | L1 coverage (90 % bound) | policy | lost (days) | violation of L* | added inventory (EUR) | acted |")
        md.append("|---|---|---|---|---|---|---|")
        for s, d in [("normal 2 held-out", te), ("fraud 2", data["fraud_2"]), ("fraud 3", data["fraud_3"])]:
            cov = float(np.mean(d[TARGET].values <= l1.upper(d)))
            for r in compare_core(model, rule, d, L_STAR):
                md.append(f"| {s} | {cov:.1%} | {r['policy']} | {r['lost_days']:.3f} | {r['violation']:.1%} | "
                          f"{r['added_inv_eur']:,.0f} | {r['acted']:.0%} |")
    with open(os.path.join(a.out, "robustness.md"), "w") as fh:
        fh.write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
