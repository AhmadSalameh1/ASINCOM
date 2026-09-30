"""Run the twin for many seeds and compare it with the recorded game year.

Usage:
    python run_twin.py inputs/normal_2.json [--seeds 50] [--out results]
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from twin import DCS, Twin  # noqa: E402

DAYS_PER_ROUND = 20


def month(day):
    return (day - 1) // DAYS_PER_ROUND + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs")
    ap.add_argument("--seeds", type=int, default=50)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "results"))
    ap.add_argument("--demand", default="sample", choices=["sample", "replay"])
    ap.add_argument("--line", default="erpsim", choices=["fifo_block", "fifo_skip", "erpsim"])
    ap.add_argument("--others", default="mrp", choices=["mrp", "replay"])
    a = ap.parse_args()
    inp = json.load(open(a.inputs))
    run = f'{inp["run"]}_{a.demand}_{a.line}_{a.others}'
    os.makedirs(a.out, exist_ok=True)

    runs, queue = [], []
    for s in range(a.seeds):
        tw = Twin(inp, seed=s, demand_mode=a.demand, line_rule=a.line, others=a.others)
        df = tw.run()
        df["seed"] = s
        runs.append(df)
        queue += [o["start"] - o["created"] for o in tw.order_log if o["product"] == inp["product"]]
    sim = pd.concat(runs)
    sim.to_csv(os.path.join(a.out, f"{run}_daily.csv.gz"), index=False)
    sim["month"] = month(sim.day)

    rec = inp["recorded"]
    rec_m = pd.DataFrame({
        "sales": pd.Series(rec["daily_sales"]).rename(index=int).groupby(lambda d: month(d)).sum(),
        "production_f12": pd.Series(rec["daily_production"]).rename(index=int).groupby(lambda d: month(d)).sum(),
        "transferred": pd.Series(rec["daily_transfers"]).rename(index=int).groupby(lambda d: month(d)).sum(),
    }).fillna(0)
    per_seed = sim.groupby(["seed", "month"])[["sales", "production_f12", "transferred", "lost"]].sum()
    q = per_seed.groupby("month").quantile([0.05, 0.5, 0.95]).unstack()

    lines = [f"# Twin vs recorded year: {run}\n", f"{a.seeds} seeds, forecast replay, demand {a.demand}, line rule {a.line}, other products {a.others}.\n",
             "Monthly totals of F12 units: recorded vs simulated median [5 %, 95 %].\n",
             "| month | sales rec | sales sim | production rec | production sim | transfers rec | transfers sim | lost sim |",
             "|---|---|---|---|---|---|---|---|"]
    inside = {"sales": 0, "production_f12": 0, "transferred": 0}
    months = sorted(set(rec_m.index) | set(q.index))
    for m in months:
        cells = [str(m)]
        for k in ["sales", "production_f12", "transferred"]:
            r = rec_m[k].get(m, 0.0)
            lo, md, hi = (q[(k, x)].get(m, 0.0) for x in (0.05, 0.5, 0.95))
            inside[k] += lo <= r <= hi
            cells += [f"{r:,.0f}", f"{md:,.0f} [{lo:,.0f}, {hi:,.0f}]"]
        cells.append(f"{q[('lost', 0.5)].get(m, 0.0):,.0f}")
        lines.append("| " + " | ".join(cells) + " |")
    totals = per_seed.groupby("seed").sum()
    lines += ["", f"Recorded value inside the simulated 90 % band: "
              f"sales {inside['sales']}/{len(months)}, production {inside['production_f12']}/{len(months)}, "
              f"transfers {inside['transferred']}/{len(months)} months.",
              "", "| year total | recorded | simulated median [5 %, 95 %] |", "|---|---|---|"]
    for k, rk in [("sales", "daily_sales"), ("production_f12", "daily_production"), ("transferred", "daily_transfers")]:
        r = sum(rec[rk].values())
        lo, md, hi = totals[k].quantile([0.05, 0.5, 0.95])
        lines.append(f"| {k} | {r:,.0f} | {md:,.0f} [{lo:,.0f}, {hi:,.0f}] |")
    lo, md, hi = totals["lost"].quantile([0.05, 0.5, 0.95])
    lines.append(f"| lost demand (simulated only) | n/a | {md:,.0f} [{lo:,.0f}, {hi:,.0f}] |")
    steady = inp["demand"]["steady_months"]
    st = sim[sim.month.isin(steady)]
    comp_zero = {c: float((st[f"stock_{c}"] <= 0).mean()) for c in inp["components"] if f"stock_{c}" in st}
    lines += ["", f"F12 production queue time (created -> start), simulated: median {np.median(queue):.1f} days, "
              f"q75 {np.percentile(queue, 75):.1f} (recorded: ledger M5)"]
    lines += ["", "Steady months: share of simulated days ending with zero component stock (recorded: ledger K1 <= 0.8 %): " +
              ", ".join(f"{c} {v:.1%}" for c, v in comp_zero.items())]
    with open(os.path.join(a.out, f"{run}_vs_recorded.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
