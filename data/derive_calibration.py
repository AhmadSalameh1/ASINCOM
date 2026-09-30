"""Derive the V12 model calibration, with an evidence ledger, from the ERPsim runs
of Tritscher et al. (2022), "Open ERP System Data For Occupational Fraud Detection".

The calibration run is `normal_2`. `fraud_2` and `fraud_3` were played by the same
participant group (same company, same 71 customers) and serve as independent
validation years. Every model parameter is written to an evidence ledger with its
value, source tables, filter, method, and its value in the validation years.

Usage:
    python derive_calibration.py /path/to/erp_fraud_data [--out calibration]

Outputs (in --out):
    evidence_ledger.md / .csv   one row per model parameter, with provenance
    cleaning_log.md             every cleaning rule and what it removed, per run
    calibration_<run>.json      all derived quantities per run
    across_runs.csv             headline statistics for the three runs

Conventions:
  * Game time. ERPsim encodes round and day in the customer PO number
    (VBAK.BSTNK = "Order" + RR + DD + ...). All SAP calendar dates of a run are
    the same day, so each event is placed on the game clock by mapping its
    wall-clock time to the game day whose first sales order precedes it.
    One round (month) = 20 game days; a run has 12 rounds.
  * Quantities are real units. The model uses real / QTY_SCALE.
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
PLANT_SLOC = "02"
TABLES = ["vbak", "vbap", "likp", "lips", "ekpo", "mseg", "mkpf", "cdhdr",
          "afko", "jcds", "stpo", "mast"]
STAT_CREATED, STAT_RELEASED, STAT_DELIVERED = "I0001", "I0002", "I0012"
# A month is "steady" when no DC ends more than this share of its days with zero stock.
STEADY_MAX_ZERO_STOCK_SHARE = 0.05


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
    """Header languages differ between runs (technical / German / English) but
    column order is identical, so non-reference runs are renamed positionally."""
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


def labelled_documents(root):
    """Documents named in the dataset's label file, per run."""
    sheets = pd.read_excel(os.path.join(root, "fraud_labels_all_data.xlsx"), sheet_name=None, header=None)
    result = {}
    for name, df in sheets.items():
        ev = {"fraud_po": set(), "fraud_so": set(), "sale_so": set(), "scrap_po": set()}
        for _, row in df.iloc[2:].iterrows():
            label = str(row[0])
            po = {int(x) for x in re.findall(r"\d+", str(row[2])) if len(x) >= 9}
            so = {int(x) for x in re.findall(r"\d+", str(row[3]))} if str(row[3]) != "nan" else set()
            if label.startswith("Sale"):
                ev["sale_so"] |= so
            elif label.startswith("Scrap"):
                ev["scrap_po"] |= po
            else:
                ev["fraud_po"] |= po
                ev["fraud_so"] |= so
        result[name.strip().replace(" ", "_")] = ev
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
    q = x.quantile([.05, .25, .5, .75, .95])
    return {"n": int(len(x)), "mean": round(x.mean(), 3), "std": round(x.std(), 3),
            "min": round(x.min(), 3), "q05": round(q[.05], 3), "q25": round(q[.25], 3),
            "median": round(q[.5], 3), "q75": round(q[.75], 3), "q95": round(q[.95], 3),
            "max": round(x.max(), 3)}


def shifted_gamma(x):
    """Method-of-moments fit of x = shift + Gamma(shape, scale), shift = min(x)."""
    x = pd.Series(x, dtype=float).dropna()
    y = x - x.min()
    if len(y) < 2 or y.var() == 0:
        return None
    return {"shift": round(x.min(), 3), "shape": round(y.mean() ** 2 / y.var(), 3),
            "scale": round(y.var() / y.mean(), 3)}


def month_of(day):
    return (day - 1) // DAYS_PER_ROUND + 1


class GameClock:
    def __init__(self, vbak):
        b = vbak.BSTNK.astype(str)
        vbak["gday"] = (b.str[5:7].astype(int) - 1) * DAYS_PER_ROUND + b.str[7:9].astype(int)
        vbak["sec"] = vbak.ERZET.apply(secs)
        first = vbak.groupby("gday").sec.min().sort_index()
        self.starts, self.days = first.values, first.index.values

    def __call__(self, s):
        i = np.searchsorted(self.starts, s, side="right") - 1
        if i < 0:  # start-up postings before the first sales order
            return float(self.days[0] - 1)
        nxt = self.starts[i + 1] if i + 1 < len(self.starts) else self.starts[i] + 60
        # fraction of the day; long gaps (pauses between rounds) are capped
        return self.days[i] + min((s - self.starts[i]) / max(min(nxt - self.starts[i], 120), 1), 0.999)


def stock_path(moves):
    """Stock level from signed movements. The opening stock is not in the data;
    the path is shifted by its lower bound so it never goes negative."""
    level = moves.d.cumsum()
    opening = max(0.0, -level.min())
    return level + opening, opening


def signed(moves):
    moves = moves.sort_values(["gday", "MBLNR"]).copy()
    moves["d"] = np.where(moves.SHKZG == "S", moves.MENGE, -moves.MENGE)
    return moves


# ---------------------------------------------------------------------------
# Derivation
# ---------------------------------------------------------------------------
def derive(tb, ev):
    """Return (derived quantities, cleaning log) for one run."""
    vbak, vbap, likp, lips = tb["vbak"].copy(), tb["vbap"], tb["likp"], tb["lips"]
    ekpo, mseg, mkpf, cdhdr = tb["ekpo"], tb["mseg"], tb["mkpf"], tb["cdhdr"]
    afko, jcds, stpo, mast = tb["afko"], tb["jcds"], tb["stpo"], tb["mast"]
    clock = GameClock(vbak)
    n_days = int(vbak.gday.max() // DAYS_PER_ROUND * DAYS_PER_ROUND + (DAYS_PER_ROUND if vbak.gday.max() % DAYS_PER_ROUND else 0))
    out, log = {}, []

    # ---- integrity checks ----
    ms = mseg.merge(mkpf[["MBLNR", "CPUTM"]], on="MBLNR")
    ms["gday"] = ms.CPUTM.apply(lambda t: clock(secs(t)))
    out["integrity"] = {
        "duplicate_sales_items": int(vbap.duplicated(["VBELN", "POSNR"]).sum()),
        "duplicate_goods_movement_lines": int(ms.duplicated(["MBLNR", "ZEILE"]).sum()),
        "rejected_sales_items": int(vbap.ABGRU.notna().sum()),
        "deleted_po_items": int(ekpo.LOEKZ.notna().sum()),
        "movement_types": {int(k): int(v) for k, v in ms.BWART.value_counts().items()},
    }
    log.append(("C0 integrity", "duplicates / rejections / deletions / reversal movement types",
                json.dumps(out["integrity"])))

    # ---- C1: fraud-labelled documents ----
    n0 = len(vbak)
    vbak = vbak[~vbak.VBELN.isin(ev["fraud_so"])]
    ek = ekpo[~ekpo.EBELN.isin(ev["fraud_po"])]
    log.append(("C1 fraud documents", "drop sales orders and POs named in the label file",
                f"{n0 - len(vbak)} sales orders, {ekpo.EBELN.nunique() - ek.EBELN.nunique()} POs removed"))

    # ---- structure: BOM, network ----
    bom = mast[mast.MATNR == PRODUCT].merge(stpo, on="STLNR")
    out["bom_per_unit"] = {r.IDNRK: float(r.MENGE) for r in bom.itertuples()}
    materials = list(out["bom_per_unit"])
    dlv = lips.merge(likp[["VBELN", "KUNNR"]], on="VBELN")
    dc_of = dlv.groupby("KUNNR").LGORT.agg(lambda s: s.mode()[0])
    out["customers"] = int(vbak.KUNNR.nunique())
    out["customers_per_dc"] = {DC_NAMES.get(k, k): int(v) for k, v in dc_of.value_counts().items()}
    out["customers_served_by_more_than_one_dc"] = int((dlv.groupby("KUNNR").LGORT.nunique() > 1).sum())

    # ---- DC stock and steady-state window (C2) ----
    fg = ms[ms.MATNR == PRODUCT]
    zero_share, dc_info = {}, {}
    for dc, name in DC_NAMES.items():
        mv = signed(fg[(fg.LGORT == dc) & fg.BWART.isin([301, 601])])
        mv["stock"], opening = stock_path(mv)
        day_end = mv.groupby(mv.gday.astype(int)).stock.last().reindex(range(1, n_days + 1)).ffill().fillna(opening)
        zero_share[name] = (day_end <= 0).groupby(month_of(day_end.index)).mean()
        inbound = (mv.BWART == 301) & (mv.SHKZG == "S")
        dc_info[name] = {"opening_stock_lower_bound": float(opening), "peak_stock": float(mv.stock.max()),
                         "stock_before_transfer": summary(mv.stock.shift(1)[inbound])}
    zero = pd.DataFrame(zero_share)
    steady = [int(m) for m in zero.index if (zero.loc[m] <= STEADY_MAX_ZERO_STOCK_SHARE).all()]
    out["zero_stock_day_share_by_month"] = zero.round(3).to_dict()
    out["steady_months"] = steady
    out["dc_stock"] = dc_info
    log.append(("C2 steady-state window",
                f"demand statistics use only months where every DC ends <= {STEADY_MAX_ZERO_STOCK_SHARE:.0%} "
                "of days with zero stock (outside it, sales are capped by stock, so sales != demand)",
                f"steady months: {steady}"))

    # ---- demand (C3: promotions excluded from baseline) ----
    items = vbap.merge(vbak[["VBELN", "KUNNR", "gday"]], on="VBELN")
    prod = items[items.MATNR == PRODUCT].copy()
    prod["month"] = month_of(prod.gday)
    prod["price"] = prod.NETWR / prod.KWMENG
    out["product_share_of_units"] = round(prod.KWMENG.sum() / items.KWMENG.sum(), 3)
    promo = prod.VBELN.isin(ev["sale_so"])
    window = prod.month.isin(steady)
    base = prod[~promo & window]
    log.append(("C3 promotions", "drop promotion-labelled orders from baseline demand",
                f"{int(promo.sum())} F12 items removed"))
    log.append(("C2 applied to demand", "F12 order items outside the steady window",
                f"{int((~window).sum())} of {len(prod)} items excluded from demand statistics"))
    out["order_qty"] = summary(base.KWMENG)
    orders = base.drop_duplicates("VBELN").sort_values("gday")
    gaps = orders.groupby("KUNNR").gday.diff().dropna()
    out["inter_order_days"] = summary(gaps) | {"shifted_gamma_fit": shifted_gamma(gaps)}
    out["inter_order_days_by_dc"] = {
        DC_NAMES[dc]: summary(orders[orders.KUNNR.map(dc_of) == dc].groupby("KUNNR").gday.diff().dropna())
        for dc in DC_NAMES}
    daily = prod.groupby("gday").KWMENG.sum().reindex(range(1, n_days + 1), fill_value=0)
    out["daily_units_steady"] = summary(daily[month_of(daily.index).isin(steady)])
    out["monthly"] = {int(m): {"units": float(g.KWMENG.sum()), "orders": int(g.VBELN.nunique()),
                               "customers": int(g.KUNNR.nunique()), "median_price": round(g.price.median(), 3)}
                      for m, g in prod.groupby("month")}
    steady_units = prod[window & ~promo].groupby("month").KWMENG.sum()
    steady_price = prod[window & ~promo].groupby("month").price.median()
    out["price_units_correlation_steady"] = round(float(np.corrcoef(steady_price, steady_units)[0, 1]), 3) \
        if len(steady_units) > 2 else None

    if ev["sale_so"]:
        days = np.sort(vbak[vbak.VBELN.isin(ev["sale_so"])].gday.unique())
        windows = []
        for grp in np.split(days, np.where(np.diff(days) > DAYS_PER_ROUND)[0] + 1):
            lo, hi = int(grp.min()), int(grp.max())
            before = daily.loc[max(1, lo - DAYS_PER_ROUND):lo - 1].mean()
            windows.append({"start_day": lo, "end_day": hi, "months": sorted({month_of(lo), month_of(hi)}),
                            "uplift_vs_previous_20_days": round(daily.loc[lo:hi].mean() / before, 3) if before else None})
        out["promotions"] = windows

    # ---- purchasing: lead time, PO size, reorder point ----
    po_created = cdhdr[cdhdr.OBJECTCLAS == "EINKBELEG"].copy()
    po_created["EBELN"] = po_created.OBJECTID.astype(np.int64)
    po_created["po_day"] = po_created.UTIME.apply(lambda t: clock(secs(t)))
    receipts = ms[(ms.BWART == 101) & ms.EBELN.notna()].copy()
    receipts["EBELN"] = receipts.EBELN.astype(np.int64)
    receipts = receipts[~receipts.EBELN.isin(ev["fraud_po"])]
    lead = receipts.merge(po_created[["EBELN", "po_day"]], on="EBELN")
    lead["lead"] = lead.gday - lead.po_day
    food = [m for m in materials if m.startswith("AA-R")]
    pack = [m for m in materials if m.startswith("AA-P")]
    out["lead_time_days"] = {m: summary(lead[lead.MATNR == m].lead) for m in materials}
    out["lead_time_days_food"] = summary(lead[lead.MATNR.isin(food)].lead) | \
        {"shifted_gamma_fit": shifted_gamma(lead[lead.MATNR.isin(food)].lead)}
    out["lead_time_days_packaging"] = summary(lead[lead.MATNR.isin(pack)].lead) | \
        {"shifted_gamma_fit": shifted_gamma(lead[lead.MATNR.isin(pack)].lead)}
    out["po_qty"] = {m: summary(ek[ek.MATNR == m].MENGE) for m in materials}
    comp = {}
    for m in materials:
        mv = signed(ms[(ms.MATNR == m) & ms.BWART.isin([101, 261])])
        mv["stock"], opening = stock_path(mv)
        pos = po_created[po_created.EBELN.isin(ek[ek.MATNR == m].EBELN)]
        at_po = [mv[mv.gday <= d].stock.iloc[-1] if (mv.gday <= d).any() else opening for d in pos.po_day]
        comp[m] = {"opening_stock_lower_bound": float(opening), "peak_stock": float(mv.stock.max()),
                   "stock_when_po_created": summary(at_po)}
    out["component_stock"] = comp
    if ev["scrap_po"]:
        sc = ms[ms.EBELN.isin(ev["scrap_po"])]
        out["scrap_events"] = [{"po": int(p), "materials": sorted(g.MATNR.unique().tolist()),
                                "movement_types": {int(k): int(v) for k, v in g.BWART.value_counts().items()}}
                               for p, g in sc.groupby("EBELN")]

    # ---- production ----
    orders_p = afko[afko.PLNBEZ == PRODUCT]
    out["production_batch"] = summary(orders_p.GAMNG) | {
        "values": {int(k): int(v) for k, v in orders_p.GAMNG.value_counts().items()}}
    out["product_share_of_production_orders"] = round(len(orders_p) / len(afko), 3)
    st = jcds[jcds.OBJNR.astype(str).str.startswith("OR")].copy()
    st["AUFNR"] = st.OBJNR.astype(str).str[2:].astype(np.int64)
    st["day"] = st.UTIME.apply(lambda t: clock(secs(t)))
    rel = st[st.STAT == STAT_RELEASED].groupby("AUFNR").day.min()
    dlvd = st[st.STAT == STAT_DELIVERED].groupby("AUFNR").day.min()
    dur = (dlvd - rel).dropna()
    dur = dur[dur.index.isin(orders_p.AUFNR)]
    out["production_days"] = summary(dur)
    out["production_days_steady"] = summary(dur[month_of(rel[dur.index].astype(int)).isin(steady)])
    prod_moves = ms[(ms.MATNR == PRODUCT) & (ms.BWART == 101) & (ms.LGORT == PLANT_SLOC) & ms.EBELN.isna()]
    out["units_produced_by_month"] = {int(k): float(v) for k, v in
                                      prod_moves.groupby(month_of(prod_moves.gday.astype(int))).MENGE.sum().items()}
    plant = signed(fg[(fg.LGORT == PLANT_SLOC) & fg.BWART.isin([101, 301])])
    plant["stock"], opening = stock_path(plant)
    created = st[(st.STAT == STAT_CREATED) & st.AUFNR.isin(orders_p.AUFNR)].groupby("AUFNR").day.min()
    at_order = [plant[plant.gday <= d].stock.iloc[-1] if (plant.gday <= d).any() else opening for d in created]
    out["plant_stock"] = {"opening_stock_lower_bound": float(opening), "peak_stock": float(plant.stock.max()),
                          "stock_when_production_order_created": summary(at_order)}

    # ---- distribution ----
    tr = fg[(fg.BWART == 301) & fg.LGORT.isin(DC_NAMES) & (fg.SHKZG == "S")]
    out["transfer_qty"] = {DC_NAMES[dc]: summary(g.MENGE) for dc, g in tr.groupby("LGORT")}
    out["transfer_qty_all"] = summary(tr.MENGE)

    # ---- observed disruption episode: months without production ----
    produced = out["units_produced_by_month"]
    idle = [m for m in range(1, n_days // DAYS_PER_ROUND + 1) if produced.get(m, 0) == 0]
    out["months_without_production"] = idle
    return out, log


# ---------------------------------------------------------------------------
# Evidence ledger
# ---------------------------------------------------------------------------
LEDGER = [
    # id, model element, how to read it from the derived dict, source, method
    ("S1", "Customers", lambda d: d["customers"],
     "VBAK.KUNNR", "distinct sold-to parties"),
    ("S2", "Customers per DC (North/South/West)",
     lambda d: "/".join(str(d["customers_per_dc"].get(n, 0)) for n in DC_NAMES.values()),
     "LIPS.LGORT x LIKP.KUNNR", "modal DC per customer; all customers use exactly one DC"),
    ("S3", "BOM per unit of AA-F12", lambda d: d["bom_per_unit"],
     "MAST x STPO", "bill-of-materials items"),
    ("D1", "Customer inter-order time (days), mean / median",
     lambda d: f'{d["inter_order_days"]["mean"]} / {d["inter_order_days"]["median"]}',
     "VBAK.BSTNK (game day), VBAP", "per-customer gaps between F12 orders, steady months, promotions excluded"),
    ("D2", "Customer inter-order time, shifted-gamma fit (shift, shape, scale)",
     lambda d: d["inter_order_days"]["shifted_gamma_fit"], "as D1", "method of moments"),
    ("D3", "Order size (units), mean / median", lambda d: f'{d["order_qty"]["mean"]} / {d["order_qty"]["median"]}',
     "VBAP.KWMENG", "F12 items, steady months, promotions excluded"),
    ("D4", "Demand level (units per game day), mean", lambda d: d["daily_units_steady"]["mean"],
     "VBAP.KWMENG by game day", "steady months"),
    ("L1", "Lead time food ingredients (days), q05 / median / q95",
     lambda d: f'{d["lead_time_days_food"]["q05"]} / {d["lead_time_days_food"]["median"]} / {d["lead_time_days_food"]["q95"]}',
     "CDHDR (PO created) -> MSEG 101 (goods receipt)", "game-clock difference, fraud POs excluded"),
    ("L2", "Lead time packaging (days), q05 / median / q95",
     lambda d: f'{d["lead_time_days_packaging"]["q05"]} / {d["lead_time_days_packaging"]["median"]} / {d["lead_time_days_packaging"]["q95"]}',
     "as L1", "as L1"),
    ("P1", "PO size R02 / R05 / R06 / P01 (mean units)",
     lambda d: " / ".join(f'{d["po_qty"][m]["mean"]:.0f}' for m in ["AA-R02", "AA-R05", "AA-R06", "AA-P01"]),
     "EKPO.MENGE", "mean per material, fraud POs excluded"),
    ("P2", "Reorder point R02 / R05 / R06 / P01 (median stock at PO creation)",
     lambda d: " / ".join(f'{d["component_stock"][m]["stock_when_po_created"]["median"]:.0f}'
                          for m in ["AA-R02", "AA-R05", "AA-R06", "AA-P01"]),
     "MSEG 101/261 stock path at CDHDR PO time", "player policy, not a physical parameter"),
    ("M1", "Production batch (units): values (count)", lambda d: d["production_batch"]["values"],
     "AFKO.GAMNG", "F12 production orders"),
    ("M2", "Production time (days), median / q75, steady months",
     lambda d: f'{d["production_days_steady"].get("median")} / {d["production_days_steady"].get("q75")}',
     "JCDS status I0002 released -> I0012 delivered", "game-clock difference"),
    ("M3", "Production trigger: plant stock at order creation, median", lambda d:
     d["plant_stock"]["stock_when_production_order_created"]["median"],
     "MSEG 101/301 plant stock path at JCDS I0001", "player policy"),
    ("M4", "Share of production orders for F12", lambda d: d["product_share_of_production_orders"],
     "AFKO.PLNBEZ", "line shared with F16/F15"),
    ("T1", "Plant -> DC transfer size (units), mean", lambda d: d["transfer_qty_all"]["mean"],
     "MSEG 301 inbound to 02N/02S/02W", "F12"),
    ("T2", "Plant -> DC transport time", lambda d: "not observable",
     "MSEG 301", "ERPsim posts transfers as one instantaneous document"),
    ("C1", "Peak DC stock North / South / West (no physical capacity is recorded in ERPsim)",
     lambda d: " / ".join(f'{d["dc_stock"][n]["peak_stock"]:.0f}' for n in DC_NAMES.values()),
     "MSEG 301/601 stock path per DC", "peak level"),
    ("W1", "Steady-state months", lambda d: d["steady_months"],
     "DC stock paths", f"months with <= {STEADY_MAX_ZERO_STOCK_SHARE:.0%} zero-stock days at every DC"),
    ("E1", "Observed episode: months without production", lambda d: d["months_without_production"],
     "MSEG 101 at plant", "candidate real disruption for validation"),
]


# Evidence class of each ledger row:
#   anchored   - structural fact read directly from master/transaction data
#   bounded    - statistical parameter; ensemble range from the three runs
#   policy     - player decision; nominal policy, open to the L2 decision layer
#   unobserved - not recorded in the data; must be assumed and varied
#   context    - cleaning or validation information, not a model parameter
CLASS = {"S1": "anchored", "S2": "anchored", "S3": "anchored (run-specific recipe)",
         "D1": "bounded", "D2": "bounded", "D3": "bounded", "D4": "bounded (price and mix driven)",
         "L1": "bounded", "L2": "bounded", "P1": "policy", "P2": "policy",
         "M1": "policy", "M2": "bounded", "M3": "policy", "M4": "policy",
         "T1": "policy", "T2": "unobserved", "C1": "policy", "W1": "context", "E1": "context"}


def fmt(v):
    if isinstance(v, float):
        return f"{v:,.3f}".rstrip("0").rstrip(".")
    if isinstance(v, dict):
        return ", ".join(f"{k}: {fmt(x)}" for k, x in v.items())
    return str(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="path to erp_fraud_data/")
    ap.add_argument("--out", default="calibration")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    labels = labelled_documents(args.root)
    empty = {"fraud_po": set(), "fraud_so": set(), "sale_so": set(), "scrap_po": set()}
    ref = load_run(args.root, RUNS[0], None)
    headers = {t: list(df.columns) for t, df in ref.items()}

    derived, logs = {}, {}
    for run in RUNS:
        tb = ref if run == RUNS[0] else load_run(args.root, run, headers)
        derived[run], logs[run] = derive(tb, labels.get(run, empty))
        with open(os.path.join(args.out, f"calibration_{run}.json"), "w") as f:
            json.dump(derived[run], f, indent=2, default=float)
        print(f"derived {run}")

    rows = []
    for pid, element, get, source, method in LEDGER:
        row = {"id": pid, "class": CLASS[pid], "element": element}
        for run in RUNS:
            try:
                row[run] = fmt(get(derived[run]))
            except (KeyError, TypeError):
                row[run] = "n/a"
        row.update({"source": source, "method": method})
        rows.append(row)
    ledger = pd.DataFrame(rows)
    ledger.to_csv(os.path.join(args.out, "evidence_ledger.csv"), index=False)
    with open(os.path.join(args.out, "evidence_ledger.md"), "w") as f:
        f.write("# Evidence ledger\n\nEvery model parameter with its value in the calibration run (normal_2), "
                "the two validation years, and its provenance. Generated by `derive_calibration.py`.\n\n")
        f.write(ledger.to_markdown(index=False) + "\n")
    with open(os.path.join(args.out, "cleaning_log.md"), "w") as f:
        f.write("# Cleaning log\n\nGenerated by `derive_calibration.py`.\n")
        for run in RUNS:
            f.write(f"\n## {run}\n\n| Rule | Definition | Effect |\n|---|---|---|\n")
            for rule, definition, effect in logs[run]:
                f.write(f"| {rule} | {definition} | {effect} |\n")
    print(ledger[["id", "element"] + RUNS].to_string(index=False))


if __name__ == "__main__":
    main()
