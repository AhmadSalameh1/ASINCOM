"""Phase D validation metrics (docs/validation_protocol.md) for one game year.

Usage:
    python validate.py inputs/fraud_2.json [--seeds 50] [--out validation] [twin options]
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
month = lambda d: (d - 1) // DAYS_PER_ROUND + 1


def recorded_series(inp):
    first, last = inp["days"]["first"] - 1, inp["days"]["last"]
    days = range(first, last + 1)
    r = inp["recorded"]
    s = lambda k: pd.Series(r[k]).rename(index=int).reindex(days, fill_value=0.0)
    return pd.DataFrame({"sales": s("daily_sales"), "production_f12": s("daily_production"),
                         "transferred": s("daily_transfers")})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs")
    ap.add_argument("--seeds", type=int, default=50)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "validation"))
    ap.add_argument("--push", default="replay")
    ap.add_argument("--split", default="fixed")
    ap.add_argument("--mrp", default="recorded")
    ap.add_argument("--policy", default="replay", choices=["mrp", "replay"])
    ap.add_argument("--line", default="erpsim")
    ap.add_argument("--demand", default="replay", choices=["replay", "replay_all"])
    ap.add_argument("--changeover", type=float, default=0.6)
    a = ap.parse_args()
    inp = json.load(open(a.inputs))
    run = inp["run"]
    os.makedirs(a.out, exist_ok=True)
    rec = recorded_series(inp)
    sims, starts = [], []
    for s in range(a.seeds):
        tw = Twin(inp, seed=s, demand_mode=a.demand, push_rule=a.push, dc_split=a.split, mrp_timing=a.mrp, policy=a.policy, line_rule=a.line, changeover_days=a.changeover)
        df = tw.run().set_index("day")
        df["seed"] = s
        sims.append(df)
        # V6 (protocol definition): last F12 forecast update on/before the order's creation -> start
        upd = sorted(u["day"] for u in inp["forecast_updates"] if u["material"] == inp["product"])
        for o in tw.order_log:
            if o["product"] == inp["product"]:
                prev = [d for d in upd if d <= o["created"]]
                if prev:
                    starts.append(o["start"] - prev[-1])
    sim = pd.concat(sims)
    res, lines = {}, [f"# Validation metrics: {run}\n",
                      f"{a.seeds} seeds; demand, forecast and MRP days replayed; policy {a.policy}, push {a.push}, DC split {a.split}, demand {a.demand}.\n"]

    # V1 year totals
    tot = sim.groupby("seed")[list(rec.columns)].sum().median()
    v1 = {k: (tot[k] - rec[k].sum()) / rec[k].sum() for k in rec.columns}
    res["V1"] = all(abs(x) <= 0.10 for x in v1.values())
    lines.append("## V1 year totals (twin median vs recorded)\n" + "\n".join(
        f"- {k}: {tot[k]:,.0f} vs {rec[k].sum():,.0f} ({v1[k]:+.1%})" for k in rec.columns) + f"\n- **{'PASS' if res['V1'] else 'FAIL'}** (±10 %)\n")

    # V2-V4 monthly band inclusion (pre-registered) and band width
    sm = sim.groupby(["seed", sim.index.map(month)])[list(rec.columns)].sum()
    rm = rec.groupby(rec.index.map(month)).sum()
    lines.append("## V2-V4 monthly totals inside the 5-95 % band (pre-registered)\n")
    for vid, k in [("V2", "sales"), ("V3", "production_f12"), ("V4", "transferred")]:
        q = sm[k].groupby(level=1).quantile([0.05, 0.95]).unstack()
        inside = ((rm[k] >= q[0.05] - 1e-6) & (rm[k] <= q[0.95] + 1e-6)).reindex(rm.index, fill_value=False)
        width = ((q[0.95] - q[0.05]) / rm[k].replace(0, np.nan)).median()
        res[vid] = int(inside.sum()) >= 9
        lines.append(f"- {vid} {k}: {int(inside.sum())} / {len(rm)} months; median band width {width:.1%} of the "
                     f"recorded month → **{'PASS' if res[vid] else 'FAIL'}**")

    # Amendment A1: cumulative-curve deviation (shift tolerant)
    lines.append("\n## A1 cumulative-curve deviation (amendment 1, primary)\n"
                 "max over days of |twin cumulative (median seed) − recorded cumulative| / recorded year total\n")
    med = sim.groupby(level=0)[list(rec.columns)].median()
    for k in rec.columns:
        dev = (med[k].cumsum() - rec[k].cumsum()).abs().max() / rec[k].sum()
        res[f"A1_{k}"] = dev <= 0.10
        lines.append(f"- {k}: {dev:.1%} → **{'PASS' if dev <= 0.10 else 'FAIL'}** (≤ 10 %)")

    # V5 DC stock-out months (recorded: from inputs if present)
    so = sim[[f"dc_{d}" for d in DCS]].le(0).any(axis=1)
    so_month = so.groupby([sim["seed"], so.index.map(month)]).any().groupby(level=1).mean()
    rec_so = set(inp.get("recorded_dc_stockout_months", []))
    twin_so = {int(m) for m, p in so_month.items() if p >= 0.5}
    months = sorted(rm.index)
    agree = sum((m in rec_so) == (m in twin_so) for m in months)
    res["V5"] = agree >= 10
    lines.append(f"\n## V5 DC stock-out months\n- recorded {sorted(rec_so)}, twin (≥ 50 % of seeds) {sorted(twin_so)}; "
                 f"agreement {agree} / {len(months)} → **{'PASS' if res['V5'] else 'FAIL'}**")

    # V6 MRP -> start
    rec_v6 = inp.get("recorded_mrp_to_start_median")
    tw_v6 = float(np.median(starts)) if starts else float("nan")
    res["V6"] = rec_v6 is not None and abs(tw_v6 - rec_v6) <= 2
    lines.append(f"\n## V6 forecast update (MRP) → production start (F12)\n- twin median {tw_v6:.1f} days, recorded {rec_v6} → "
                 f"**{'PASS' if res['V6'] else 'FAIL'}** (≤ 2 days apart)")

    # V7 component stock-outs, steady months, F12 components
    steady = inp["demand"]["steady_months"]
    st = sim[sim.index.map(month).isin(steady)]
    f12c = [c for c in inp["recorded_production_orders"][0]["recipe"]]
    share = {c: float((st[f"stock_{c}"] <= 0).mean()) for c in f12c}
    res["V7"] = all(v <= 0.05 for v in share.values())
    lines.append("\n## V7 F12 component stock-outs (steady months)\n- " + ", ".join(f"{c} {v:.1%}" for c, v in share.items()) +
                 f" → **{'PASS' if res['V7'] else 'FAIL'}** (each ≤ 5 %)")

    # V8 production pause propagation
    pause = inp.get("recorded_production_pause")
    if pause:
        pm = {month(d) for d in range(pause[0], pause[1] + 1)}
        after = {m for m in range(min(pm), max(pm) + 2)}
        res["V8"] = bool(twin_so & after) == bool(rec_so & after)
        lines.append(f"\n## V8 production pause (days {pause[0]}-{pause[1]}) → DC stock-outs\n- recorded stock-out months "
                     f"in/after the pause {sorted(rec_so & after)}, twin {sorted(twin_so & after)} → "
                     f"**{'PASS' if res['V8'] else 'FAIL'}**")
    with open(os.path.join(a.out, f"{run}_{a.policy}_{a.push}_{a.split}_{a.demand}.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    json.dump({k: bool(v) for k, v in res.items()}, open(os.path.join(a.out, f"{run}_{a.policy}_{a.push}_{a.split}_{a.demand}.json"), "w"))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
