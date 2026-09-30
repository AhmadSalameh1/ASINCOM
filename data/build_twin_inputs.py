"""Build the input file of the Python twin (and later the UPPAAL model) for one game year.

Everything the simulator needs is extracted here from the SAP tables, so the twin
itself knows nothing about SAP. Each field names its evidence (ledger / structure
check / policy rule).

Usage:
    python build_twin_inputs.py /path/to/erp_fraud_data RUN [--calibration calibration] [--out ../model/twin/inputs]
"""
import argparse
import glob
import json
import os
import re

import numpy as np
import pandas as pd

from derive_calibration import (DAYS_PER_ROUND, DC_NAMES, PLANT_SLOC, PRODUCT, GameClock,
                                labelled_documents, month_of, secs, table_path)

TABLES = {"vbak": ["vbak"], "vbap": ["vbap"], "likp": ["likp"], "lips": ["lips"], "mseg": ["mseg"],
          "mkpf": ["mkpf"], "cdhdr": ["cdhdr"], "afko": ["afko"], "jcds": ["jcds"], "resb": ["resb"],
          "pbhi": ["pbhi"], "pbim": ["pbimt", "pbim"], "marc": ["marc"], "ekpo": ["ekpo"], "aufm": ["aufm"]}
COMPONENTS = ["AA-R01", "AA-R02", "AA-R03", "AA-R04", "AA-R05", "AA-R06", "AA-P01", "AA-P02"]
OTHER_PRODUCTS_PREFIX = "AA-F"


def find(root, run, names):
    for n in names:
        hits = [p for p in glob.glob(os.path.join(root, "raw_data", run, "**", "*"), recursive=True)
                if re.search(rf"[/\\]{n}\.xlsx$", p, re.I)]
        if hits:
            return hits[0]
    raise FileNotFoundError(f"{run}: {names}")


def load(root, run):
    ref_run = "normal_2"
    out = {}
    for key, names in TABLES.items():
        df = pd.read_excel(find(root, run, names))
        if run != ref_run:
            ref = pd.read_excel(find(root, ref_run, names), nrows=0).columns
            if len(ref) != df.shape[1]:
                raise ValueError(f"{run}/{key}: width {df.shape[1]} vs {len(ref)}")
            df.columns = ref
        out[key] = df
    return out


def pmf(values):
    s = pd.Series(values).value_counts(normalize=True).sort_index()
    return {int(k): round(float(v), 6) for k, v in s.items()}


def build(root, run, calibration_dir):
    tb = load(root, run)
    ev = labelled_documents(root).get(run, {"fraud_po": set(), "fraud_so": set(), "sale_so": set(), "scrap_po": set()})
    cal = json.load(open(os.path.join(calibration_dir, f"calibration_{run}.json")))
    steady = cal["steady_months"]
    vbak = tb["vbak"].copy()
    clock = GameClock(vbak)
    vbak = vbak[~vbak.VBELN.isin(ev["fraud_so"])]
    ms = tb["mseg"].merge(tb["mkpf"][["MBLNR", "CPUTM"]], on="MBLNR")
    ms["sec"] = ms.CPUTM.apply(secs)
    ms["day"] = ms.sec.apply(clock.posting_tick)
    inp = {"run": run, "product": PRODUCT, "components": COMPONENTS,
           "days": {"first": int(clock.days[0]), "last": int(clock.days[-1]),
                    "horizon": int(np.ceil(clock.days[-1] / DAYS_PER_ROUND) * DAYS_PER_ROUND)},
           "capacity_per_day": 24000, "evidence": {}}

    # ---- customers and demand (S1, S2, B5, D1-D3; steady months, promotions excluded) ----
    dlv = tb["lips"].merge(tb["likp"][["VBELN", "KUNNR"]], on="VBELN")
    dc_of = dlv.groupby("KUNNR").LGORT.agg(lambda s: s.mode()[0])
    items = tb["vbap"].merge(vbak[["VBELN", "KUNNR", "gday"]], on="VBELN")
    f12 = items[items.MATNR == PRODUCT]
    first = f12.groupby("KUNNR").gday.min()
    inp["customers"] = [{"id": int(k), "dc": DC_NAMES[dc_of[k]], "first_order_day": int(first.get(k, clock.days[0]))}
                        for k in sorted(dc_of.index) if k in first.index]
    base = f12[~f12.VBELN.isin(ev["sale_so"]) & month_of(f12.gday).isin(steady)]
    orders = base.drop_duplicates("VBELN").sort_values("gday")
    inp["demand"] = {"inter_order_days": pmf(orders.groupby("KUNNR").gday.diff().dropna().astype(int)),
                     "order_qty_samples": sorted(int(x) for x in base.groupby("VBELN").KWMENG.sum()),
                     "steady_months": steady}
    rec_orders = f12[~f12.VBELN.isin(ev["fraud_so"])].groupby(["VBELN", "KUNNR", "gday"]).KWMENG.sum().reset_index()
    inp["demand"]["recorded_orders"] = [{"day": int(r.gday), "customer": int(r.KUNNR), "qty": float(r.KWMENG)}
                                        for r in rec_orders.sort_values("gday").itertuples()]
    inp["evidence"]["demand"] = "ledger D1-D3, D5 (order size = sum of the order's F12 lines); rules C2, C3"

    # ---- supplier lead times in ticks (L3, L4; rules C4, C5) ----
    cd = tb["cdhdr"]
    po = cd[cd.OBJECTCLAS == "EINKBELEG"].copy()
    po["EBELN"] = po.OBJECTID.astype(np.int64)
    po["psec"] = po.UTIME.apply(secs)
    po["pday"] = po.psec.apply(clock.decision_tick)
    rec = ms[(ms.BWART == 101) & ms.EBELN.notna()].copy()
    rec["EBELN"] = rec.EBELN.astype(np.int64)
    lt = rec.merge(po[["EBELN", "pday", "psec"]], on="EBELN")
    lt = lt[~lt.EBELN.isin(ev["fraud_po"] | ev["scrap_po"]) & (lt.psec >= clock.starts[0])]
    lt["lead"] = lt.day - lt.pday
    food = lt.MATNR.str.startswith("AA-R")
    inp["lead_time_pmf"] = {"food": pmf(lt[food].lead), "packaging": pmf(lt[~food].lead)}
    inp["evidence"]["lead_time_pmf"] = "ledger L3, L4"

    # ---- MRP master data (MARC) ----
    marc = tb["marc"].set_index("MATNR")
    prods = sorted(p for p in tb["afko"].PLNBEZ.unique())
    inp["lot_rules"] = {p: {"min": int(marc.BSTMI[p]), "max": int(marc.BSTMA[p]), "rounding": int(marc.BSTRF[p])}
                        for p in prods}
    inp["po_rounding"] = {c: int(marc.BSTRF[c]) for c in COMPONENTS}
    inp["evidence"]["lot_rules"] = "MARC; docs/policy_acceptance.md"

    # ---- production orders: recipes (RESB) and creation days ----
    jc = tb["jcds"]
    cr = jc[(jc.STAT == "I0001") & jc.OBJNR.astype(str).str.startswith("OR")].copy()
    cr["AUFNR"] = cr.OBJNR.astype(str).str[2:].astype(np.int64)
    cr["day"] = cr.UTIME.apply(lambda t: clock.decision_tick(secs(t)))
    resb = tb["resb"][tb["resb"].AUFNR.notna()].copy()
    resb["AUFNR"] = resb.AUFNR.astype(np.int64)
    afko = tb["afko"].set_index("AUFNR")
    recipe = resb.pivot_table(index="AUFNR", columns="MATNR", values="BDMNG", aggfunc="sum").fillna(0).div(
        afko.GAMNG, axis=0).dropna(how="all").fillna(0)
    created = cr.groupby("AUFNR").day.min()
    orders_all = [{"day": int(created[a]), "product": afko.PLNBEZ[a], "qty": int(afko.GAMNG[a]),
                   "recipe": {c: round(float(recipe.loc[a].get(c, 0)), 6) for c in COMPONENTS if recipe.loc[a].get(c, 0) > 0}}
                  for a in created.index if a in recipe.index]
    orders_all.sort(key=lambda o: o["day"])
    # MRP runs = days on which the players created POs or production orders (planning lag after
    # forecast updates is player behaviour, replayed per DR-3)
    po_days = set(int(d) for d in po[po.psec >= clock.starts[0]].pday)
    inp["mrp_run_days"] = sorted(po_days | set(int(d) for d in created.values))
    inp["recorded_production_orders"] = [o for o in orders_all if o["product"] == PRODUCT]
    inp["other_production_orders"] = [o for o in orders_all if o["product"] != PRODUCT]
    inp["evidence"]["production"] = "B10-B13, M1, M6, M8; RESB recipes (rule R4)"

    # ---- forecast updates (PBHI + PBIM), as decision days ----
    pb = tb["pbhi"].merge(tb["pbim"][["BDZEI", "MATNR"]], on="BDZEI")
    pb["day"] = pb.UZEIT.apply(lambda t: clock.decision_tick(secs(t)))
    pb["sec"] = pb.UZEIT.apply(secs)
    pb = pb.sort_values("sec")
    produced_products = set(tb["afko"].PLNBEZ.unique())
    inp["forecast_updates"] = [{"day": int(r.day), "sec": int(r.sec), "material": r.MATNR, "open_qty": float(r.PLNMG)}
                               for r in pb.itertuples()
                               if r.MATNR in produced_products or r.MATNR in ("AA-P01", "AA-P02")]
    inp["planning_products"] = sorted(produced_products)
    # other products at planning level: their recorded sales per day (fraud orders excluded)
    oth = items[items.MATNR.isin(produced_products - {PRODUCT})]
    inp["other_product_daily_sales"] = {p: {int(d): float(q) for d, q in g.groupby("gday").KWMENG.sum().items()}
                                        for p, g in oth.groupby("MATNR")}
    inp["evidence"]["forecast_updates"] = "PBHI (PLNMG = new open forecast), rules R1-R3"

    # ---- DC push rule (fitted; the only fitted policy element) ----
    f = ms[ms.MATNR == PRODUCT]
    days = list(range(inp["days"]["first"] - 1, inp["days"]["last"] + 1))
    recv = f[(f.BWART == 101) & (f.LGORT == PLANT_SLOC) & f.EBELN.isna()].groupby("day").MENGE.sum().reindex(days, fill_value=0)
    tin = f[(f.BWART == 301) & f.LGORT.isin(DC_NAMES) & (f.SHKZG == "S")]
    sent = tin.groupby("day").MENGE.sum().reindex(days, fill_value=0)
    stock, avail = 0.0, []
    for d in days:
        a = stock + recv[d]
        avail.append(a)
        stock = a - sent[d]
    avail = pd.Series(avail, index=days)
    steady_days = [d for d in days if month_of(d) in steady]
    alpha = float(sent[steady_days].sum() / avail[steady_days][avail[steady_days] > 0].sum())
    shares = (tin[month_of(tin.day).isin(steady)].groupby("LGORT").MENGE.sum())
    shares = {DC_NAMES[k]: round(float(v / shares.sum()), 4) for k, v in shares.items()}
    inp["dc_push"] = {"daily_fraction_of_plant_stock": round(alpha, 4), "dc_shares": shares}
    inp["evidence"]["dc_push"] = "fitted on steady months of MSEG 301 (spec section 4, item 3)"

    # ---- recorded reference values for validation (not used by the simulation) ----
    zs = cal["zero_stock_day_share_by_month"]
    inp["recorded_dc_stockout_months"] = sorted({int(m) for dc in zs.values() for m, v in dc.items() if v > 0})
    am = tb["aufm"].merge(tb["mkpf"][["MBLNR", "CPUTM"]], on="MBLNR")
    am["day"] = am.CPUTM.apply(lambda t: clock.posting_tick(secs(t)))
    start = am[am.BWART == 261].groupby("AUFNR").day.min()
    f12o = [a for a in created.index if afko.PLNBEZ.get(a) == PRODUCT and a in start.index]
    # V6 as defined in the protocol: last F12 forecast update before the order's conversion -> start
    upd = sorted((int(r.sec), int(r.day)) for r in pb.itertuples() if r.MATNR == PRODUCT)
    csec = cr.groupby("AUFNR").UTIME.min().apply(secs)
    upd_to_start = []
    for a_ in f12o:
        prev = [d for sec_, d in upd if sec_ <= csec[a_]]
        if prev:
            upd_to_start.append(int(start[a_] - prev[-1]))
    inp["recorded_mrp_to_start_median"] = float(np.median(upd_to_start)) if upd_to_start else None
    s12 = start[f12o].sort_values()
    gaps = s12.diff()
    if len(gaps.dropna()):
        hi = int(s12[gaps.idxmax()])
        inp["recorded_production_pause"] = [int(hi - gaps.max()), hi]
    # ---- recorded series for comparison (not used by the simulation) ----
    sales_day = f12.groupby("gday").KWMENG.sum()
    inp["recorded"] = {
        "daily_sales": {int(k): float(v) for k, v in sales_day.items()},
        "daily_production": {int(k): float(v) for k, v in recv.items() if v},
        "daily_transfers": {int(k): float(v) for k, v in sent.items() if v},
    }
    return inp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("run")
    ap.add_argument("--calibration", default=os.path.join(os.path.dirname(__file__), "calibration"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "model", "twin", "inputs"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    inp = build(a.root, a.run, a.calibration)
    path = os.path.join(a.out, f"{a.run}.json")
    with open(path, "w") as fh:
        json.dump(inp, fh, indent=1, default=float)
    print(f"wrote {path}: {len(inp['customers'])} customers, {len(inp['forecast_updates'])} forecast updates, "
          f"{len(inp['recorded_production_orders'])} F12 / {len(inp['other_production_orders'])} other orders, "
          f"dc_push {inp['dc_push']}, lead food {inp['lead_time_pmf']['food']}")


if __name__ == "__main__":
    main()
