"""Phase E: inject evidence-based disruptions into the validated twin and measure their physical impact.

Decisions are replayed (policy/push/demand replay), except the one reaction of the accepted MRP replica that
a quantity loss triggers (rule R5: blocked material is re-ordered the same day). This measures how each disruption propagates through
the validated physics when the players' historical decisions do NOT react (open loop). The AI layers
(prediction, decision) come later.

Every severity level cites its evidence (docs/disruptions.md). Levels beyond the evidence are labelled STRESS.

Usage:
    python disruptions.py inputs/fraud_2.json [--seeds 30] [--start DAY] [--out disruptions]
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from twin import DCS, Twin  # noqa: E402

EPISODE = 20  # one game month


def scenarios(start):
    w = [start, start + EPISODE - 1]
    return [
        ("baseline", "none", {}, "-"),
        ("E1 supplier delay", "median late shipment (+0.12 x lead)", {"supplier_delay": {"window": w, "relative": 0.12}}, "USAID SCMS q50"),
        ("E1 supplier delay", "severe (+0.75 x lead)", {"supplier_delay": {"window": w, "relative": 0.75}}, "USAID SCMS q90"),
        ("E1 supplier delay", "extreme (+1.0 x lead)", {"supplier_delay": {"window": w, "relative": 1.0}}, "USAID SCMS q95"),
        ("E2 quality loss", "wheat receipts: 4.1 % blocked, +2 d", {"quality": {"window": w, "block_share": 0.041, "extra_delay": 2, "materials": ["AA-R05"]}}, "ERPsim Q2 max, Q1"),
        ("E2 quality loss", "all food receipts: 4.1 % blocked, +2 d", {"quality": {"window": w, "block_share": 0.041, "extra_delay": 2, "materials": ["AA-R01", "AA-R02", "AA-R03", "AA-R04", "AA-R05", "AA-R06"]}}, "ERPsim Q2 max, applied widely"),
        ("E2 quality loss", "STRESS all food receipts: 25 % blocked, +2 d", {"quality": {"window": w, "block_share": 0.25, "extra_delay": 2, "materials": ["AA-R01", "AA-R02", "AA-R03", "AA-R04", "AA-R05", "AA-R06"]}}, "beyond evidence"),
        ("E3 line stoppage", "3 days", {"line_down": [[start, start + 2]]}, "short breakdown (assumed)"),
        ("E3 line stoppage", "10 days", {"line_down": [[start, start + 9]]}, "between"),
        ("E3 line stoppage", "25 days", {"line_down": [[start, start + 24]]}, "shortest observed pause (B17, fraud 3)"),
        ("E4 demand", "surge +19 % for a month", {"demand": {"window": w, "factor": 1.19}}, "max steady month, normal 2"),
        ("E4 demand", "STRESS surge +50 % for a month", {"demand": {"window": w, "factor": 1.5}}, "beyond evidence"),
        ("E5 transit delay", "+1 day", {"transit": {"window": w, "days": 1}}, "DataCo q50 (semi-synthetic)"),
        ("E5 transit delay", "+4 days", {"transit": {"window": w, "days": 4}}, "DataCo q95 (semi-synthetic)"),
    ]


def start_days(inp, seeds):
    """One start day per seed, drawn uniformly over the steady months (impact depends strongly on timing)."""
    steady = sorted(inp["demand"]["steady_months"])
    days = [d for m in steady for d in range((m - 1) * 20 + 1, m * 20 + 1) if d + EPISODE + 60 <= inp["days"]["last"]]
    rng = np.random.default_rng(12345)
    return [int(x) for x in rng.choice(days, size=seeds)]


def run(inp, make_scen, starts):
    rows = []
    for s, st in enumerate(starts):
        df = Twin(inp, seed=s, demand_mode="replay", policy="replay", push_rule="replay",
                  scenario=make_scen(st)).run()
        rows.append(df.set_index("day"))
    return rows


def kpis(runs, starts, base_runs):
    """Per seed; each disruption run is compared with the baseline run of the SAME seed (common random numbers)."""
    out = []
    for df, b, start in zip(runs, base_runs, starts):
        end = start + EPISODE - 1
        lost = df["lost"]
        dem = df["sales"] + df["lost"]
        after = df.loc[start:]
        so = after[[f"dc_{d}" for d in DCS]].le(0).any(axis=1)
        excess = (lost - b["lost"]).loc[start:]
        bad = excess[excess > 1]
        rec = float(max(bad.index.max() - end, 0)) if len(bad) else 0.0
        out.append({"lost_total": lost.sum(),
                    "lost_after_start": lost.loc[start:].sum(),
                    "fill_rate_60d": 1 - lost.loc[start:start + 59].sum() / max(dem.loc[start:start + 59].sum(), 1),
                    "stockout_days_after": int(so.sum()),
                    "extra_lost": float(excess.sum()),
                    "days_until_no_excess_loss": rec})
    return pd.DataFrame(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs")
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--start", type=int, default=None, help="first disruption day (default: middle of the steady window)")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "disruptions"))
    a = ap.parse_args()
    inp = json.load(open(a.inputs))
    starts = [a.start] * a.seeds if a.start else start_days(inp, a.seeds)
    os.makedirs(a.out, exist_ok=True)
    base_runs = run(inp, lambda st: {}, starts)
    base = kpis(base_runs, starts, base_runs)
    lines = [f"# Disruption impact (open loop, decisions replayed): {inp['run']}\n",
             f"{a.seeds} seeds; each seed draws its own start day uniformly over the steady months "
             f"(days {min(starts)}-{max(starts)}); episode {EPISODE} days; KPIs from the start day on, each run paired "
             "with the baseline run of the same seed.\n",
             "| disruption | severity | evidence | lost demand from start (units, median [5 %, 95 %]) | extra lost vs same-seed baseline: median [95 %] | share of seeds with any extra loss | fill rate next 60 d | DC stock-out days after start | days of excess loss after the episode ends |",
             "|---|---|---|---|---|---|---|---|---|"]
    for i, (name, sev, _, evid) in enumerate(scenarios(0)):
        make = lambda st, i=i: scenarios(st)[i][2]
        k = base if i == 0 else kpis(run(inp, make, starts), starts, base_runs)
        l = k.lost_after_start
        extra = k.extra_lost.median()
        lines.append(f"| {name} | {sev} | {evid} | {l.median():,.0f} [{l.quantile(.05):,.0f}, {l.quantile(.95):,.0f}] | "
                     f"{extra:+,.0f} [{k.extra_lost.quantile(.95):+,.0f}] | {(k.extra_lost > 1).mean():.0%} | "
                     f"{k.fill_rate_60d.median():.1%} | {k.stockout_days_after.median():.0f} | "
                     f"{k.days_until_no_excess_loss.median():.0f} |")
    path = os.path.join(a.out, f"{inp['run']}_impact.md")
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
