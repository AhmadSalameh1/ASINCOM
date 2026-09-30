"""Derive the V12 model calibration from the ERPsim runs of Tritscher et al. (2022).

Data: "Open ERP System Data For Occupational Fraud Detection", raw_data/*.zip
(SAP tables exported to .XLSX). The calibration run is `normal_2`; `fraud_2`
and `fraud_3` were played by the same participant group (same company, same
71 customers) and are used to measure year-to-year variation. Documents that
the dataset's fraud-label file marks as fraud are excluded.

Usage:
    python derive_calibration.py /path/to/erp_fraud_data [--out calibration]

Outputs (in --out):
    calibration_normal_2.json   every derived quantity for the calibration run
    across_runs.csv             headline statistics for normal_2 / fraud_2 / fraud_3
    calibration_summary.md      human-readable summary

Conventions:
  * Game time. ERPsim encodes round and day in the customer PO number
    (VBAK.BSTNK = "Order" + RR + DD + ...). All SAP calendar dates of a run are
    the same day, so every event is placed on the game clock by mapping its
    wall-clock time to the game day whose first sales order precedes it.
    One round = 20 game days; a run has 12 rounds (one game year).
  * Quantities are reported in real units. The model uses real / QTY_SCALE.
  * Only product AA-F12 and its five BOM components are modelled.
"""
import argparse
import glob
import json
import os
import re

import numpy as np
import pandas as pd

RUNS = ["normal_2", "fraud_2", "fraud_3"]
PRODUCT = "AA-F12"
QTY_SCALE = 100
DAYS_PER_ROUND = 20
DC_NAMES = {"02N": "North", "02S": "South", "02W": "West"}
TABLES = ["vbak", "vbap", "likp", "lips", "ekpo", "mseg", "mkpf", "cdhdr",
          "afko", "jcds", "stpo", "mast"]
STAT_RELEASED, STAT_DELIVERED = "I0002", "I0012"


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def table_path(root, run, table):
    hits = [p for p in glob.glob(os.path.join(root, "raw_data", run, "**", "*"), recursive=True)
            if re.search(rf"[/\\]{table}\.xlsx$", p, re.I)]
    if not hits:
        raise FileNotFoundError(f"{run}/{table}")
    return hits[0]


def load_run(root, run, reference_headers):
    """Load a run's tables. Header languages differ between runs (technical
    names / German / English), but column order is identical, so non-reference
    runs are renamed positionally to the reference technical names."""
    out = {}
    for t in TABLES:
        df = pd.read_excel(table_path(root, run, t))
        if reference_headers is not None:
            ref = reference_headers[t]
            if len(ref) != df.shape[1]:
                raise ValueError(f"{run}/{t}: {df.shape[1]} columns, reference has {len(ref)}")
            df.columns = ref
        out[t] = df
    return out


def fraud_documents(root):
    """POs and sales orders listed in the fraud-label file, per run."""
    sheets = pd.read_excel(os.path.join(root, "fraud_labels_all_data.xlsx"), sheet_name=None, header=None)
    result = {}
    for name, df in sheets.items():
        run = name.strip().replace(" ", "_")
        events = {"fraud_po": set(), "fraud_so": set(), "sale_so": set(), "scrap_po": set()}
        for _, row in df.iloc[2:].iterrows():
            label = str(row[0])
            po = [int(x) for x in re.findall(r"\d+", str(row[2])) if len(x) >= 9]
            so = [int(x) for x in re.findall(r"\d+", str(row[3])) if str(row[3]) != "nan"]
            if label.startswith("Sale"):
                events["sale_so"].update(so)
            elif label.startswith("Scrap"):
                events["scrap_po"].update(po)
            else:
                events["fraud_po"].update(po)
                events["fraud_so"].update(so)
        result[run] = events
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def secs(t):
    if isinstance(t, str):
        h, m, s = map(int, t.split(":"))
        return h * 3600 + m * 60 + s
    return t.hour * 3600 + t.minute * 60 + t.second


def summary(x):
    x = pd.Series(x, dtype=float).dropna()
    if x.empty:
        return {"n": 0}
    return {"n": int(len(x)), "mean": round(x.mean(), 3), "std": round(x.std(), 3),
            "min": round(x.min(), 3), "q05": round(x.quantile(.05), 3),
            "q25": round(x.quantile(.25), 3), "median": round(x.median(), 3),
            "q75": round(x.quantile(.75), 3), "q95": round(x.quantile(.95), 3),
            "max": round(x.max(), 3)}


def shifted_gamma(x):
    """Method-of-moments fit of x = shift + Gamma(shape, scale), shift = min(x)."""
    x = pd.Series(x, dtype=float).dropna()
    shift = x.min()
    y = x - shift
    if y.var() == 0:
        return {"shift": shift, "shape": None, "scale": None}
    shape = y.mean() ** 2 / y.var()
    return {"shift": round(shift, 3), "shape": round(shape, 3), "scale": round(y.var() / y.mean(), 3)}


class GameClock:
    def __init__(self, vbak):
        b = vbak.BSTNK.astype(str)
        vbak["gday"] = (b.str[5:7].astype(int) - 1) * DAYS_PER_ROUND + b.str[7:9].astype(int)
        vbak["sec"] = vbak.ERZET.apply(secs)
        first = vbak.groupby("gday").sec.min().sort_index()
        self.starts, self.days = first.values, first.index.values

    def __call__(self, s):
        i = np.searchsorted(self.starts, s, side="right") - 1
        if i < 0:
            return np.nan
        nxt = self.starts[i + 1] if i + 1 < len(self.starts) else self.starts[i] + 60
        # fraction of the day; long gaps (pauses between rounds) are capped
        return self.days[i] + min((s - self.starts[i]) / max(min(nxt - self.starts[i], 120), 1), 0.999)


def stock_path(moves):
    """Cumulative stock from signed movements, shifted so it never goes negative
    (the opening stock is not in the data; the shift is its lower bound)."""
    level = moves.d.cumsum()
    opening = max(0.0, -level.min())
    return level + opening, opening


# ---------------------------------------------------------------------------
# Derivation
# ---------------------------------------------------------------------------
def derive(tb, events):
    vbak, vbap, likp, lips = tb["vbak"].copy(), tb["vbap"], tb["likp"], tb["lips"]
    ekpo, mseg, mkpf, cdhdr = tb["ekpo"], tb["mseg"], tb["mkpf"], tb["cdhdr"]
    afko, jcds, stpo, mast = tb["afko"], tb["jcds"], tb["stpo"], tb["mast"]

    clock = GameClock(vbak)
    vbak = vbak[~vbak.VBELN.isin(events["fraud_so"])]
    out = {"game_days_with_sales": int(vbak.gday.nunique()),
           "rounds": int((vbak.gday.max() - 1) // DAYS_PER_ROUND + 1)}

    # ---- bill of materials ----
    bom = mast[mast.MATNR == PRODUCT].merge(stpo, on="STLNR")
    out["bom_per_unit"] = {r.IDNRK: float(r.MENGE) for r in bom.itertuples()}
    materials = list(out["bom_per_unit"])

    # ---- network: customers per DC ----
    dlv = lips.merge(likp[["VBELN", "KUNNR"]], on="VBELN")
    dc_of = dlv.groupby("KUNNR").LGORT.agg(lambda s: s.mode()[0])
    out["customers"] = int(vbak.KUNNR.nunique())
    out["customers_per_dc"] = {DC_NAMES.get(k, k): int(v) for k, v in dc_of.value_counts().items()}
    out["customers_served_by_more_than_one_dc"] = int((dlv.groupby("KUNNR").LGORT.nunique() > 1).sum())

    # ---- demand for the product ----
    items = vbap.merge(vbak[["VBELN", "KUNNR", "gday"]], on="VBELN")
    out["product_share_of_units"] = round(items[items.MATNR == PRODUCT].KWMENG.sum() / items.KWMENG.sum(), 3)
    prod = items[items.MATNR == PRODUCT]
    promo = prod.VBELN.isin(events["sale_so"])
    base = prod[~promo]
    out["order_qty"] = summary(base.KWMENG)
    orders = base.drop_duplicates("VBELN").sort_values("gday")
    gaps = orders.groupby("KUNNR").gday.diff().dropna()
    out["inter_order_days"] = summary(gaps) | {"shifted_gamma_fit": shifted_gamma(gaps)}
    out["inter_order_days_by_dc"] = {
        DC_NAMES.get(dc, dc): summary(orders[orders.KUNNR.map(dc_of) == dc].groupby("KUNNR").gday.diff().dropna())
        for dc in DC_NAMES}
    daily = prod.groupby("gday").KWMENG.sum().reindex(range(1, out["rounds"] * DAYS_PER_ROUND + 1), fill_value=0)
    out["daily_units"] = summary(daily)
    out["monthly_units"] = {int(k): float(v) for k, v in
                            prod.groupby((prod.gday - 1) // DAYS_PER_ROUND + 1).KWMENG.sum().items()}

    # ---- labelled promotions (demand events) ----
    if events["sale_so"]:
        promo_orders = vbak[vbak.VBELN.isin(events["sale_so"])]
        windows = []
        for grp in np.split(np.sort(promo_orders.gday.unique()),
                            np.where(np.diff(np.sort(promo_orders.gday.unique())) > DAYS_PER_ROUND)[0] + 1):
            lo, hi = int(grp.min()), int(grp.max())
            during = daily.loc[lo:hi].mean()
            before = daily.loc[max(1, lo - 20):lo - 1].mean()
            windows.append({"start_day": lo, "end_day": hi, "duration_days": hi - lo + 1,
                            "mean_daily_units_during": round(during, 1),
                            "mean_daily_units_20d_before": round(before, 1),
                            "uplift_ratio": round(during / before, 3) if before else None})
        out["promotions"] = windows

    # ---- goods movements on the game clock ----
    ms = mseg.merge(mkpf[["MBLNR", "CPUTM"]], on="MBLNR")
    ms["gday"] = ms.CPUTM.apply(lambda t: clock(secs(t)))

    # ---- purchasing: lead time, order quantity, reorder point ----
    po_created = cdhdr[cdhdr.OBJECTCLAS == "EINKBELEG"].copy()
    po_created["EBELN"] = po_created.OBJECTID.astype(np.int64)
    po_created["po_day"] = po_created.UTIME.apply(lambda t: clock(secs(t)))
    receipts = ms[(ms.BWART == 101) & ms.EBELN.notna()].copy()
    receipts["EBELN"] = receipts.EBELN.astype(np.int64)
    receipts = receipts[~receipts.EBELN.isin(events["fraud_po"])]
    lead = receipts.merge(po_created[["EBELN", "po_day"]], on="EBELN")
    lead["lead"] = lead.gday - lead.po_day
    out["lead_time_days"] = {m: summary(lead[lead.MATNR == m].lead) for m in materials}
    out["lead_time_days_all_components"] = summary(lead[lead.MATNR.isin(materials)].lead)
    ek = ekpo[~ekpo.EBELN.isin(events["fraud_po"])]
    out["po_qty"] = {m: summary(ek[ek.MATNR == m].MENGE) for m in materials}

    reorder = {}
    for m in materials:
        mv = ms[(ms.MATNR == m) & ms.BWART.isin([101, 261])].sort_values(["gday", "MBLNR"]).copy()
        mv["d"] = np.where(mv.SHKZG == "S", mv.MENGE, -mv.MENGE)
        mv["level"], opening = stock_path(mv)
        pos = po_created[po_created.EBELN.isin(ek[ek.MATNR == m].EBELN)]
        at_order = [mv[mv.gday <= d].level.iloc[-1] if (mv.gday <= d).any() else opening for d in pos.po_day]
        reorder[m] = {"opening_stock_lower_bound": float(opening),
                      "stock_when_po_created": summary(at_order),
                      "peak_stock": float(mv.level.max())}
    out["component_stock"] = reorder

    # ---- labelled scrap events (quality at goods receipt) ----
    if events["scrap_po"]:
        sc = ms[ms.EBELN.isin(events["scrap_po"])]
        out["scrap_events"] = [{"po": int(p), "material": sorted(g.MATNR.unique().tolist()),
                                "movements": g.BWART.value_counts().to_dict()}
                               for p, g in sc.groupby("EBELN")]

    # ---- production: batch size, duration, stock at order creation ----
    po_prod = afko[afko.PLNBEZ == PRODUCT].copy()
    out["production_batch"] = summary(po_prod.GAMNG) | {
        "values": {int(k): int(v) for k, v in po_prod.GAMNG.value_counts().items()}}
    out["product_share_of_production_orders"] = round(len(po_prod) / len(afko), 3)
    st = jcds[jcds.OBJNR.astype(str).str.startswith("OR")].copy()
    st["AUFNR"] = st.OBJNR.astype(str).str[2:].astype(np.int64)
    st["day"] = st.UTIME.apply(lambda t: clock(secs(t)))
    rel = st[st.STAT == STAT_RELEASED].groupby("AUFNR").day.min()
    dlvd = st[st.STAT == STAT_DELIVERED].groupby("AUFNR").day.min()
    dur = (dlvd - rel).dropna()
    out["production_release_to_delivery_days"] = summary(dur[dur.index.isin(po_prod.AUFNR)])

    fg = ms[(ms.MATNR == PRODUCT) & (ms.LGORT == "02") & ms.BWART.isin([101, 301])].sort_values(["gday", "MBLNR"]).copy()
    fg["d"] = np.where(fg.SHKZG == "S", fg.MENGE, -fg.MENGE)
    fg["level"], opening = stock_path(fg)
    created = st[(st.STAT == "I0001") & st.AUFNR.isin(po_prod.AUFNR)].groupby("AUFNR").day.min()
    at_order = [fg[fg.gday <= d].level.iloc[-1] if (fg.gday <= d).any() else opening for d in created]
    out["plant_stock"] = {"opening_stock_lower_bound": float(opening), "peak_stock": float(fg.level.max()),
                          "stock_when_production_order_created": summary(at_order)}

    # ---- distribution: plant -> DC transfers and DC stock ----
    tr = ms[(ms.BWART == 301) & (ms.MATNR == PRODUCT) & ms.LGORT.isin(DC_NAMES) & (ms.SHKZG == "S")]
    out["transfer_qty"] = {DC_NAMES[dc]: summary(g.MENGE) for dc, g in tr.groupby("LGORT")}
    out["transfer_time_observable"] = False  # ERPsim posts plant->DC transfers as one instantaneous document
    dcs = {}
    for dc, name in DC_NAMES.items():
        mv = ms[(ms.MATNR == PRODUCT) & (ms.LGORT == dc) & ms.BWART.isin([301, 601])].sort_values(["gday", "MBLNR"]).copy()
        mv["d"] = np.where(mv.SHKZG == "S", mv.MENGE, -mv.MENGE)
        mv["level"], opening = stock_path(mv)
        before_transfer = mv.level.shift(1)[(mv.BWART == 301) & (mv.SHKZG == "S")]
        dcs[name] = {"opening_stock_lower_bound": float(opening), "peak_stock": float(mv.level.max()),
                     "stock_before_transfer": summary(before_transfer),
                     "share_of_events_at_zero_stock": round(float((mv.level <= 0).mean()), 4)}
    out["dc_stock"] = dcs
    return out


def headline(run, d):
    comp = [m for m in d["bom_per_unit"] if m.startswith("AA-R")]
    return {"run": run,
            "customers": d["customers"],
            "product_units_per_game_day": d["daily_units"]["mean"],
            "product_share_of_units": d["product_share_of_units"],
            "order_qty_mean": d["order_qty"]["mean"],
            "inter_order_days_mean": d["inter_order_days"]["mean"],
            "inter_order_days_median": d["inter_order_days"]["median"],
            "lead_time_days_median": d["lead_time_days_all_components"]["median"],
            "lead_time_days_q95": d["lead_time_days_all_components"]["q95"],
            "food_po_qty_mean": round(np.mean([d["po_qty"][m]["mean"] for m in comp]), 1),
            "production_batch_mean": d["production_batch"]["mean"],
            "production_days_median": d["production_release_to_delivery_days"].get("median"),
            "transfer_qty_mean": round(np.mean([v["mean"] for v in d["transfer_qty"].values()]), 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="path to erp_fraud_data/")
    ap.add_argument("--out", default="calibration")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    events = fraud_documents(args.root)
    ref_tables = load_run(args.root, RUNS[0], None)
    ref_headers = {t: list(df.columns) for t, df in ref_tables.items()}

    results, rows = {}, []
    for run in RUNS:
        tb = ref_tables if run == RUNS[0] else load_run(args.root, run, ref_headers)
        results[run] = derive(tb, events.get(run, {"fraud_po": set(), "fraud_so": set(),
                                                   "sale_so": set(), "scrap_po": set()}))
        rows.append(headline(run, results[run]))
        print(f"derived {run}")

    with open(os.path.join(args.out, "calibration_normal_2.json"), "w") as f:
        json.dump(results[RUNS[0]], f, indent=2, default=float)
    across = pd.DataFrame(rows).set_index("run")
    across.loc["cv_across_runs"] = (across.std() / across.mean()).round(3)
    across.to_csv(os.path.join(args.out, "across_runs.csv"))
    with open(os.path.join(args.out, "calibration_summary.md"), "w") as f:
        f.write("# Calibration derived from ERPsim\n\nCalibration run: normal_2. Validation runs: fraud_2, fraud_3 "
                "(fraud-labelled documents excluded). Quantities in real units; model uses real / "
                f"{QTY_SCALE}. Times in game days.\n\n## Headline statistics across runs\n\n")
        f.write(across.T.to_markdown() + "\n")
    print(across.T.to_string())


if __name__ == "__main__":
    main()
