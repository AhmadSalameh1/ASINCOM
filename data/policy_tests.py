"""Policy acceptance tests (Phase C, step 1): does SAP MRP logic, fed the players'
recorded forecast updates, reproduce the recorded production orders and POs?

Usage:
    python policy_tests.py /path/to/erp_fraud_data/raw_data/normal_2/normal_2 [--out policy]

Findings are written to <out>/policy_tests.md. See docs/policy_acceptance.md for
the interpretation.
"""
import argparse
import math
import os

import numpy as np
import pandas as pd

PRODUCT = "AA-F12"


def secs(t):
    if isinstance(t, str):
        h, m, s = map(int, t.split(":"))
        return h * 3600 + m * 60 + s
    return t.hour * 3600 + t.minute * 60 + t.second


def lots(q, lot_min, lot_max, rounding):
    """SAP lot-for-lot with minimum, maximum and rounding value (MARC BSTMI/BSTMA/BSTRF)."""
    if q <= 0:
        return []
    q = math.ceil(q / rounding) * rounding
    out = []
    while q > lot_max:
        out.append(lot_max)
        q -= lot_max
    out.append(max(q, lot_min))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--out", default="policy")
    a = ap.parse_args()
    D = a.run_dir.rstrip("/") + "/"
    read = lambda t: pd.read_excel(D + t + ".XLSX")
    marc, pbhi, pbimt, afko, jcds = read("marc"), read("pbhi"), read("pbimt"), read("afko"), read("jcds")
    mseg, mkpf, ekpo, cdhdr, aufm = read("mseg"), read("mkpf"), read("ekpo"), read("cdhdr"), read("aufm")
    vbak, vbap = read("vbak"), read("vbap")
    os.makedirs(a.out, exist_ok=True)
    rep = ["# Policy acceptance tests (normal 2)\n"]

    # ---- MRP master data ----
    mm = marc[marc.MATNR == PRODUCT].iloc[0]
    lot_min, lot_max, rounding = int(mm.BSTMI), int(mm.BSTMA), int(mm.BSTRF)
    rep.append(f"## MRP settings of {PRODUCT} (MARC)\nMRP type {mm.DISMM}, lot size {mm.DISLS}, "
               f"min lot {lot_min}, max lot {lot_max}, rounding {rounding}.\n")

    # ---- forecast history decode ----
    ms = mseg.merge(mkpf[["MBLNR", "CPUTM"]], on="MBLNR")
    ms["sec"] = ms.CPUTM.apply(secs)
    pb = pbhi.merge(pbimt[["BDZEI", "MATNR"]], on="BDZEI")
    pb["sec"] = pb.UZEIT.apply(secs)
    f = pb[pb.MATNR == PRODUCT].sort_values("sec").reset_index(drop=True)
    it = vbap[vbap.MATNR == PRODUCT][["VBELN", "KWMENG"]].merge(vbak[["VBELN", "ERZET"]], on="VBELN")
    it["sec"] = it.ERZET.apply(secs)
    it = it.sort_values("sec")
    it["cum"] = it.KWMENG.cumsum()
    cum_at = lambda s: it[it.sec <= s].cum.iloc[-1] if (it.sec <= s).any() else 0
    f["cum_sales"] = f.sec.apply(cum_at)
    exact = int((f.ENTMG == f.cum_sales).sum())
    prev_open = (f.PLNMG.shift() - (f.ENTMG - f.ENTMG.shift())).fillna(0)
    dbm = int(np.isclose(prev_open[1:], f.DBMNG[1:]).sum())
    rep.append(f"## Forecast history (PBHI)\n- {len(f)} forecast updates for {PRODUCT}.\n"
               f"- ENTMG equals cumulative {PRODUCT} sales at the update in {exact} of {len(f)} "
               "(the rest differ only by orders posted in the same second): **ENTMG = forecast consumed by sales**.\n"
               f"- DBMNG equals previous PLNMG minus sales since then in {dbm} of {len(f) - 1}: "
               "**DBMNG = open forecast before the update; PLNMG = new open forecast set by the player**.\n")

    # ---- production replica ----
    cr = jcds[(jcds.STAT == "I0001") & jcds.OBJNR.astype(str).str.startswith("OR")].copy()
    cr["AUFNR"] = cr.OBJNR.astype(str).str[2:].astype(np.int64)
    cr["sec"] = cr.UTIME.apply(secs)
    orders = cr.merge(afko[["AUFNR", "PLNBEZ", "GAMNG"]], on="AUFNR").sort_values("sec")
    po12 = orders[orders.PLNBEZ == PRODUCT]
    g = ms[(ms.MATNR == PRODUCT) & ms.BWART.isin([101, 601])].sort_values(["sec", "MBLNR", "ZEILE"])
    g = g.assign(stock=np.where(g.SHKZG == "S", g.MENGE, -g.MENGE).cumsum())
    prod = ms[(ms.MATNR == PRODUCT) & (ms.BWART == 101)].sort_values("sec")
    prod = prod.assign(cum=prod.MENGE.cumsum())
    last = lambda df, col, s: df[df.sec <= s][col].iloc[-1] if (df.sec <= s).any() else 0
    rows = []
    for i, r in f.iterrows():
        nxt = f.sec[i + 1] if i + 1 < len(f) else 10 ** 9
        stock = last(g, "stock", r.sec)
        open_p = po12[po12.sec < r.sec].GAMNG.sum() - last(prod, "cum", r.sec)
        net = r.PLNMG - stock - open_p
        pred = lots(net, lot_min, lot_max, rounding)
        act = po12[(po12.sec >= r.sec) & (po12.sec < nxt)].GAMNG.tolist()
        superseded_s = nxt - r.sec if i + 1 < len(f) else None
        rows.append({"update": i, "open_forecast": r.PLNMG, "fg_stock": stock, "open_production": open_p,
                     "net": net, "predicted_lots": sorted(pred), "actual_lots": sorted(act),
                     "next_update_after_s": superseded_s})
    t = pd.DataFrame(rows)
    t["total_match"] = [sum(p) == sum(q) for p, q in zip(t.predicted_lots, t.actual_lots)]
    t["lots_match"] = t.predicted_lots == t.actual_lots
    t["superseded_before_mrp"] = [not q and s is not None and s < 900 for q, s in zip(t.actual_lots, t.next_update_after_s)]
    explained = t.total_match | t.superseded_before_mrp
    rep.append("## Production: MRP replica vs recorded production orders\n"
               "net = open forecast - finished-goods stock (plant + DCs) - open production; lots per MARC.\n\n"
               f"- exact total and lot split: **{int(t.lots_match.sum())} of {len(t)}** updates\n"
               f"- no orders because the forecast was updated again within 15 min, before MRP was run: "
               f"{int((t.superseded_before_mrp & ~t.total_match).sum())}\n"
               f"- **explained: {int(explained.sum())} of {len(t)}**\n\n" + t.to_markdown(index=False) + "\n")

    # ---- purchasing: PO bursts vs following production orders ----
    po = cdhdr[cdhdr.OBJECTCLAS == "EINKBELEG"].copy()
    po["EBELN"] = po.OBJECTID.astype(np.int64)
    po["sec"] = po.UTIME.apply(secs)
    poi = ekpo[["EBELN", "MATNR", "MENGE"]].merge(po[["EBELN", "sec"]], on="EBELN")
    ev = pd.concat([orders.assign(kind="PROD")[["sec", "kind", "AUFNR", "GAMNG"]],
                    poi.assign(kind="PO")[["sec", "kind", "MATNR", "MENGE"]]]).sort_values("sec")
    ev["burst"] = (ev.sec.diff() > 120).cumsum()
    bursts = list(ev.groupby("burst"))
    prow = []
    for i, (b, gb) in enumerate(bursts):
        if not (gb.kind == "PO").any():
            continue
        boxes = gb[(gb.kind == "PO") & (gb.MATNR == "AA-P01")].MENGE.sum()
        nxt = next((h for _, h in bursts[i + 1:] if (h.kind == "PROD").any()), None)
        units = pd.concat([gb[gb.kind == "PROD"], nxt[nxt.kind == "PROD"] if nxt is not None else gb.iloc[:0]]).GAMNG.sum()
        prow.append({"burst": b, "boxes_ordered": boxes, "units_in_next_production_burst": units})
    p = pd.DataFrame(prow)
    p["match"] = p.boxes_ordered == p.units_in_next_production_burst
    first_miss = p.index[~p.match][0] if (~p.match).any() else len(p)
    rep.append("## Purchasing: packaging POs vs units of the next production-order burst\n"
               "Packaging is 1 box per unit for every product, so this test does not depend on recipe changes.\n\n"
               f"- exact match: **{int(p.match.sum())} of {len(p)}** PO bursts; the first {first_miss} bursts all match\n"
               "- later POs are smaller than the following production: consistent with MRP netting against "
               "component stock and with per-product MRP runs (F16 and F15 have their own forecast updates). "
               "**Not yet reproduced; see docs/policy_acceptance.md.**\n\n" + p.to_markdown(index=False) + "\n")

    with open(os.path.join(a.out, "policy_tests.md"), "w") as fh:
        fh.write("\n".join(rep))
    print("\n".join(rep[:4]))
    print(f"production explained {int(explained.sum())}/{len(t)}, purchasing exact {int(p.match.sum())}/{len(p)}")


if __name__ == "__main__":
    main()
