"""Three-product MRP replica (Phase C, step 1b).

Reproduces the ERPsim players' purchasing decisions from SAP MRP logic fed their
recorded forecast updates, for all products that share components (AA-F12,
AA-F16, AA-F15). Each MRP run is identified with a burst of PO creations. For
every run, the replica computes each component's net requirement and compares it
with the POs actually created in that burst.

MRP rules (each one is an SAP mechanism found in the data):
  R1  open forecast of a product = PLNMG of its last update (PBHI) minus sales since that update
  R2  product net requirement = open forecast - finished stock (plant + DCs) - open production
  R3  planned orders = lot-for-lot with MARC min / max / rounding
  R4  component gross requirement = BOM in force x planned orders
                                    + open reservations of production orders (RESB) until their final issue
                                    + direct forecasts on components (PBHI for AA-P01 / AA-P02)
      BOM in force = reservation ratios of the next production order of that product
  R5  component net = gross - available stock - open POs; available stock excludes blocked stock
      (INSMK '3', created by scrap events)
  R6  PO quantity = net rounded up to the MARC rounding value

Usage:
    python mrp_replica.py /path/to/erp_fraud_data/raw_data/normal_2/normal_2 [--out policy]
"""
import argparse
import math
import os

import numpy as np
import pandas as pd

PRODUCTS = ["AA-F12", "AA-F16", "AA-F15"]
COMPONENTS = ["AA-R01", "AA-R02", "AA-R03", "AA-R04", "AA-R05", "AA-R06", "AA-P01", "AA-P02"]
DIRECT_FORECAST = ["AA-P01", "AA-P02"]
BURST_GAP_S = 120
BLOCKED = "3"


def secs(t):
    if isinstance(t, str):
        h, m, s = map(int, t.split(":"))
        return h * 3600 + m * 60 + s
    return t.hour * 3600 + t.minute * 60 + t.second


class Replica:
    def __init__(self, run_dir):
        D = run_dir.rstrip("/") + "/"
        read = lambda t: pd.read_excel(D + t + ".XLSX")
        self.marc = read("marc").set_index("MATNR")
        afko, ekpo, cdhdr, aufm = read("afko"), read("ekpo"), read("cdhdr"), read("aufm")
        pbhi, pbimt, vbak, vbap, jcds, resb = read("pbhi"), read("pbimt"), read("vbak"), read("vbap"), read("jcds"), read("resb")
        ms = read("mseg").merge(read("mkpf")[["MBLNR", "CPUTM"]], on="MBLNR")
        ms["sec"] = ms.CPUTM.apply(secs)
        self.ms = ms
        pb = pbhi.merge(pbimt[["BDZEI", "MATNR"]], on="BDZEI")
        pb["sec"] = pb.UZEIT.apply(secs)
        self.pb = pb.sort_values("sec")
        cr = jcds[(jcds.STAT == "I0001") & jcds.OBJNR.astype(str).str.startswith("OR")].copy()
        cr["AUFNR"] = cr.OBJNR.astype(str).str[2:].astype(np.int64)
        cr["sec"] = cr.UTIME.apply(secs)
        self.orders = cr.merge(afko[["AUFNR", "PLNBEZ", "GAMNG"]], on="AUFNR").sort_values("sec")
        iss = aufm[aufm.BWART == 261].merge(ms[["MBLNR", "sec"]].drop_duplicates("MBLNR"), on="MBLNR")
        self.iss = iss
        resb = resb[resb.AUFNR.notna()].copy()
        resb["AUFNR"] = resb.AUFNR.astype(np.int64)
        self.reserved = resb.set_index(["AUFNR", "MATNR"]).BDMNG
        self.final = set(zip(resb[resb.KZEAR == "X"].AUFNR, resb[resb.KZEAR == "X"].MATNR))
        self.last_issue = iss.groupby(["AUFNR", "MATNR"]).sec.max()
        self.recipe = resb.pivot_table(index="AUFNR", columns="MATNR", values="BDMNG", aggfunc="sum").fillna(0).div(
            afko.set_index("AUFNR").GAMNG, axis=0).dropna(how="all").fillna(0)
        po = cdhdr[cdhdr.OBJECTCLAS == "EINKBELEG"].copy()
        po["EBELN"] = po.OBJECTID.astype(np.int64)
        po["sec"] = po.UTIME.apply(secs)
        self.poi = ekpo[["EBELN", "MATNR", "MENGE"]].merge(po[["EBELN", "sec"]], on="EBELN").sort_values("sec")
        sales = vbap[["VBELN", "MATNR", "KWMENG"]].merge(vbak[["VBELN", "ERZET"]], on="VBELN")
        sales["sec"] = sales.ERZET.apply(secs)
        self.sales = sales

    # ---- rules ----
    def lots(self, q, p):
        lo, hi, r = int(self.marc.BSTMI[p]), int(self.marc.BSTMA[p]), int(self.marc.BSTRF[p])
        if q <= 0:
            return []
        q = math.ceil(q / r) * r
        out = []
        while q > hi:
            out.append(hi)
            q -= hi
        out.append(max(q, lo))
        return out

    def open_forecast(self, m, s):  # R1
        h = self.pb[(self.pb.MATNR == m) & (self.pb.sec < s)]
        if h.empty:
            return 0.0
        last = h.iloc[-1]
        consumed = self.sales[(self.sales.MATNR == m) & (self.sales.sec >= last.sec) & (self.sales.sec < s)].KWMENG.sum()
        return max(0.0, last.PLNMG - consumed)

    def fg_stock(self, p, s):
        g = self.ms[(self.ms.MATNR == p) & self.ms.BWART.isin([101, 601]) & (self.ms.sec < s)]
        return np.where(g.SHKZG == "S", g.MENGE, -g.MENGE).sum()

    def produced(self, p, s):
        ms = self.ms
        return ms[(ms.MATNR == p) & (ms.BWART == 101) & ms.EBELN.isna() & (ms.sec < s)].MENGE.sum()

    def available(self, c, s):  # R5: blocked stock excluded
        ms = self.ms
        g = ms[(ms.MATNR == c) & ms.BWART.isin([101, 261]) & (ms.sec < s) & (ms.INSMK.astype(str) != BLOCKED)]
        return np.where(g.SHKZG == "S", g.MENGE, -g.MENGE).sum()

    def on_order(self, c, s):
        ms = self.ms
        ordered = self.poi[(self.poi.MATNR == c) & (self.poi.sec < s)].MENGE.sum()
        received = ms[(ms.MATNR == c) & (ms.BWART == 101) & ms.EBELN.notna() & (ms.sec < s)].MENGE.sum()
        return ordered - received

    def bom_in_force(self, p, s):  # R4
        o = self.orders[(self.orders.PLNBEZ == p) & self.orders.AUFNR.isin(self.recipe.index)]
        after = o[o.sec >= s]
        pick = after.iloc[0] if len(after) else (o.iloc[-1] if len(o) else None)
        if pick is None:
            return pd.Series(0.0, index=COMPONENTS)
        return self.recipe.loc[pick.AUFNR].reindex(COMPONENTS).fillna(0)

    def run(self, s):
        gross = pd.Series(0.0, index=COMPONENTS)
        planned = {}
        for p in PRODUCTS:  # R2, R3
            open_prod = self.orders[(self.orders.PLNBEZ == p) & (self.orders.sec < s)].GAMNG.sum() - self.produced(p, s)
            planned[p] = self.lots(self.open_forecast(p, s) - self.fg_stock(p, s) - open_prod, p)
            gross += self.bom_in_force(p, s) * sum(planned[p])
        done = self.iss[self.iss.sec < s].groupby(["AUFNR", "MATNR"]).MENGE.sum()
        for o in self.orders[self.orders.sec < s].itertuples():  # open reservations
            for c in COMPONENTS:
                key = (o.AUFNR, c)
                if key not in self.reserved.index:
                    continue
                if key in self.final and self.last_issue.get(key, 10 ** 9) < s:
                    continue
                gross[c] += max(0.0, self.reserved[key] - done.get(key, 0.0))
        for c in DIRECT_FORECAST:
            gross[c] += self.open_forecast(c, s)
        pos = {}
        for c in COMPONENTS:  # R5, R6
            net = gross[c] - self.available(c, s) - self.on_order(c, s)
            r = int(self.marc.BSTRF[c])
            pos[c] = math.ceil(round(net, 6) / r) * r if net > 1e-6 else 0
        return pos, planned


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--out", default="policy")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rep = Replica(a.run_dir)
    bursts = rep.poi.groupby((rep.poi.sec.diff() > BURST_GAP_S).cumsum())
    last_sec = rep.ms.sec.max()
    rows = []
    for b, g in bursts:
        s = g.sec.min()
        pred, planned = rep.run(s)
        act = g.groupby("MATNR").MENGE.sum()
        for c in COMPONENTS:
            if pred[c] == 0 and act.get(c, 0) == 0:
                continue
            rows.append({"burst": b, "sec": s, "minutes_before_end": round((last_sec - s) / 60, 1),
                         "material": c, "replica": pred[c], "actual": act.get(c, 0),
                         "planned": {k: sum(v) for k, v in planned.items() if v}})
    r = pd.DataFrame(rows)
    r["match"] = r.replica == r.actual
    per_burst = r.groupby("burst").agg(match=("match", "all"), sec=("sec", "first"),
                                       minutes_before_end=("minutes_before_end", "first"))
    miss = per_burst[~per_burst.match]
    lines = ["# Three-product MRP replica vs recorded POs (normal 2)\n",
             "Rules R1-R6 are documented in `mrp_replica.py`. One row per (MRP run, component) with a non-zero value.\n",
             f"- **PO bursts reproduced exactly for every component: {int(per_burst.match.sum())} of {len(per_burst)}**",
             f"- material-burst pairs exact: {int(r.match.sum())} of {len(r)}",
             f"- bursts not reproduced: {miss.index.tolist()} "
             f"(minutes before the end of the game: {miss.minutes_before_end.tolist()})\n",
             r.drop(columns=["planned"]).to_markdown(index=False)]
    with open(os.path.join(a.out, "mrp_replica.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines[2:5]))


if __name__ == "__main__":
    main()
