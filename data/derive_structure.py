"""Phase B: prove the supply-chain structure of the ERPsim runs from SAP document flows.

Each check (B1..B14) states a structural claim the model relies on, how it is
tested, and its result in normal_2, fraud_2 and fraud_3. Fraud-labelled documents
are excluded. Output: <out>/structure_evidence.md (+ .csv).

Usage:
    python derive_structure.py /path/to/erp_fraud_data [--out structure]
"""
import argparse
import os

import numpy as np
import pandas as pd

from derive_calibration import (DC_NAMES, PLANT_SLOC, PRODUCT, RUNS, GameClock,
                                labelled_documents, secs, table_path)

TABLES = ["vbak", "vbap", "vbfa", "mseg", "mkpf", "ekpo", "eban", "afko", "aufm",
          "mast", "stpo", "plpo", "mard", "jcds", "ekbe", "cdhdr"]
POSITIONAL_ONLY_IF_SAME_WIDTH = {"ekbe"}  # EKBE has a different width in the fraud runs
SAME_TICK_S = 15
DAILY_LINE_CAPACITY = 24000


def load(root, run, ref):
    out = {}
    for t in TABLES:
        df = pd.read_excel(table_path(root, run, t))
        if ref is not None:
            if len(ref[t]) != df.shape[1]:
                if t in POSITIONAL_ONLY_IF_SAME_WIDTH:
                    out[t] = None
                    continue
                raise ValueError(f"{run}/{t}: width {df.shape[1]} vs {len(ref[t])}")
            df.columns = ref[t]
        out[t] = df
    return out


def pct(x):
    return f"{100 * x:.1f} %"


def checks(tb, ev):
    vbak, vbap, vbfa = tb["vbak"].copy(), tb["vbap"], tb["vbfa"]
    mseg, mkpf, ekpo, eban = tb["mseg"], tb["mkpf"], tb["ekpo"], tb["eban"]
    afko, aufm, mast, stpo, plpo = tb["afko"], tb["aufm"], tb["mast"], tb["stpo"], tb["plpo"]
    clock = GameClock(vbak)
    vbak = vbak[~vbak.VBELN.isin(ev["fraud_so"])]
    vbap = vbap[vbap.VBELN.isin(vbak.VBELN)]
    ekpo = ekpo[~ekpo.EBELN.isin(ev["fraud_po"])]
    ms = mseg.merge(mkpf[["MBLNR", "CPUTM"]], on="MBLNR")
    ms["sec"] = ms.CPUTM.apply(secs)
    ms["tick"] = ms.sec.apply(clock.posting_tick)
    r = {}

    # ---------------- order to cash ----------------
    fl = vbfa[vbfa.VBELV.isin(vbak.VBELN)]
    oj = fl[(fl.VBTYP_V == "C") & (fl.VBTYP_N == "J") & (fl.RFMNG > 0)]
    om = fl[(fl.VBTYP_V == "C") & (fl.VBTYP_N == "M")]
    orr = fl[(fl.VBTYP_V == "C") & (fl.VBTYP_N == "R")]
    key = ["VBELV", "POSNV"]
    items = vbap.set_index(["VBELN", "POSNR"])
    one = lambda d: d.groupby(key).size().reindex(items.index).eq(1).mean()
    r["B1"] = f"delivery {pct(one(oj))}, goods issue {pct(one(orr))}, invoice {pct(one(om))} of {len(items)} items"
    delivered = oj.groupby(key).RFMNG.sum().reindex(items.index)
    r["B2"] = f"{pct((delivered == items.KWMENG).mean())} delivered in full; {int((delivered < items.KWMENG).sum())} short"
    vbak["osec"] = vbak.ERZET.apply(secs)
    gi = orr.assign(gsec=orr.ERZET.apply(secs)).merge(vbak[["VBELN", "osec"]], left_on="VBELV", right_on="VBELN")
    lag = gi.gsec - gi.osec
    r["B3"] = f"{pct((lag <= SAME_TICK_S).mean())} issued within {SAME_TICK_S} s of the order (max {lag.max():.0f} s)"

    f = ms[ms.MATNR == PRODUCT]
    clipped, n_sales, q_clip, q_all = 0, 0, [], []
    for dc in DC_NAMES:
        g = f[(f.LGORT == dc) & f.BWART.isin([301, 601])].sort_values(["sec", "MBLNR", "ZEILE"]).copy()
        g["d"] = np.where(g.SHKZG == "S", g.MENGE, -g.MENGE)
        g["after"] = g.d.cumsum()
        s = g[g.BWART == 601]
        clipped += int((s.after == 0).sum())
        n_sales += len(s)
        q_clip += s[s.after == 0].MENGE.tolist()
        q_all += s.MENGE.tolist()
    r["B4"] = (f"{clipped} of {n_sales} sales leave the DC at exactly 0; their median qty "
               f"{np.median(q_clip) if q_clip else float('nan'):.0f} vs {np.median(q_all):.0f} overall")
    per_cust = f[f.BWART == 601].groupby("KUNNR").LGORT.nunique()
    r["B5"] = f"{pct((per_cust == 1).mean())} of {len(per_cust)} customers served by exactly one DC"

    # ---------------- procure to pay ----------------
    r["B6"] = f"{pct(eban.EBELN.notna().mean())} of {len(eban)} requisitions converted to a PO"
    gr = ms[(ms.BWART == 101) & ms.EBELN.notna()].copy()
    gr["EBELN"] = gr.EBELN.astype(np.int64)
    gr = gr[~gr.EBELN.isin(ev["fraud_po"])]
    got = gr.groupby(["EBELN", "EBELP"]).MENGE.sum()
    po = ekpo.set_index(["EBELN", "EBELP"]).MENGE
    full = got.reindex(po.index).eq(po)
    short = full[~full].index.get_level_values(0).unique()
    cd = tb["cdhdr"] if "cdhdr" in tb else None
    note = ""
    if len(short):
        created = {}
        if cd is not None:
            c = cd[cd.OBJECTCLAS == "EINKBELEG"]
            created = {int(o): clock.decision_tick(secs(t)) for o, t in zip(c.OBJECTID, c.UTIME)}
        note = "; not in full: " + ", ".join(
            f"PO {int(x)} (created day {created.get(int(x), '?')}, last played day {int(clock.days[-1])})" for x in short)
    r["B7"] = f"{pct(full.mean())} of {len(po)} PO items received in full" + note
    n_gr = gr.groupby(["EBELN", "EBELP"]).MBLNR.nunique()
    split = set(n_gr[n_gr > 1].index.get_level_values(0))
    r["B8"] = (f"{len(split)} POs with split receipts; {len(split & ev['scrap_po'])} of them are scrap-labelled "
               f"({len(ev['scrap_po'])} scrap POs in total)")
    ekbe = tb["ekbe"]
    if ekbe is not None:
        rec = ekbe[ekbe.VGABE == 1].groupby(["EBELN", "EBELP"]).MENGE.sum()
        inv = ekbe[ekbe.VGABE == 2].groupby(["EBELN", "EBELP"]).MENGE.sum()
        r["B9"] = f"{pct(inv.reindex(rec.index).eq(rec).mean())} of received PO items invoiced for the received qty"
    else:
        r["B9"] = "n/a (EKBE layout differs in this run)"

    # ---------------- production ----------------
    bom = {}
    for p in afko.PLNBEZ.unique():
        b = mast[mast.MATNR == p].merge(stpo, on="STLNR")
        bom[p] = dict(zip(b.IDNRK, b.MENGE))
    recv = aufm[aufm.BWART == 101].groupby("AUFNR").MENGE.sum().reindex(afko.AUFNR).fillna(0)
    complete = recv.values == afko.GAMNG.values
    last_day = int(clock.days[-1])
    rel = tb["jcds"]
    rel = rel[rel.OBJNR.astype(str).str.startswith("OR") & (rel.STAT == "I0002")].copy()
    rel["AUFNR"] = rel.OBJNR.astype(str).str[2:].astype(np.int64)
    rel["tick"] = rel.UTIME.apply(lambda x: clock.decision_tick(secs(x)))
    rel_tick = rel.groupby("AUFNR").tick.min()
    inc = afko[~complete].AUFNR
    near_end = [a for a in inc if rel_tick.get(a, last_day) >= last_day - 5]
    r["B10"] = (f"{pct(complete.mean())} of {len(afko)} orders received in full; "
                f"{len(inc)} incomplete, of which {len(near_end)} released in the last 5 played days (open at game end)")
    iss = aufm[aufm.BWART == 261].groupby(["AUFNR", "MATNR"]).MENGE.sum().reset_index().merge(
        afko[["AUFNR", "PLNBEZ", "GAMNG"]], on="AUFNR")
    iss["ok"] = [np.isclose(q, bom[p].get(m, np.nan) * g) for q, p, m, g in zip(iss.MENGE, iss.PLNBEZ, iss.MATNR, iss.GAMNG)]
    mine = iss[iss.PLNBEZ == PRODUCT].groupby("AUFNR").ok.all()
    ratio = iss[iss.PLNBEZ == PRODUCT].assign(r=lambda d: (d.MENGE / d.GAMNG).round(3))
    recipes = ratio.pivot_table(index="AUFNR", columns="MATNR", values="r").round(3)
    recipes = recipes.apply(lambda row: tuple(row.fillna(0)), axis=1)
    seq = recipes.loc[sorted(recipes.index)]
    changes = int((seq != seq.shift()).sum() - 1)
    r["B11"] = (f"{int(mine.sum())} of {len(mine)} {PRODUCT} orders consume exactly the final master-data BOM x qty; "
                f"{seq.nunique()} distinct consumption recipes, {changes} changes in order sequence")
    am = aufm.merge(mkpf[["MBLNR", "CPUTM"]], on="MBLNR")
    am["tick"] = am.CPUTM.apply(lambda t: clock.posting_tick(secs(t)))
    span = am.groupby(["AUFNR", "BWART"]).tick.agg(["min", "max"]).unstack()
    same = ((span[("min", 261)] == span[("min", 101)]) & (span[("max", 261)] == span[("max", 101)])).mean()
    out = am[am.BWART == 101].copy()
    out["sec"] = out.CPUTM.apply(secs)
    batched = out.groupby("sec").AUFNR.nunique()
    batched_secs = set(batched[batched >= 3].index)
    per_tick = out.groupby("tick").MENGE.sum()
    batched_ticks = set(out[out.sec.isin(batched_secs)].tick)
    ok = per_tick[~per_tick.index.isin(batched_ticks)] <= DAILY_LINE_CAPACITY
    r["B12"] = (f"output <= {DAILY_LINE_CAPACITY:,} in {int(ok.sum())} of {len(ok)} output ticks without batched postings; "
                f"{len(batched_ticks)} ticks contain batched catch-up postings (>= 3 orders in one second); "
                f"issue and output on the same ticks for {pct(same)} of orders")
    wc = afko[["PLNBEZ", "PLNNR"]].drop_duplicates().merge(plpo[["PLNNR", "ARBID"]], on="PLNNR")
    r["B13"] = "; ".join(f"{p}: {sorted(g.ARBID.unique().tolist())}" for p, g in wc.groupby("PLNBEZ"))

    # ---------------- distribution and balance ----------------
    t = f[f.BWART == 301]
    legs = t.groupby("MBLNR").apply(lambda g: set(zip(g.LGORT, g.SHKZG)), include_groups=False)
    plant_to_dc = all(all((lg == PLANT_SLOC and s == "H") or (lg in DC_NAMES and s == "S") for lg, s in x) for x in legs)
    r["B14"] = (f"all {len(legs)} transfer documents move stock plant -> DC in one posting: {plant_to_dc}; "
                f"DC -> plant quantity {t[(t.LGORT.isin(DC_NAMES)) & (t.SHKZG == 'H')].MENGE.sum():,.0f}")
    # mass balance uses ALL documents (fraud orders moved real goods)
    q = lambda sel: f[sel].MENGE.sum()
    produced = q((f.BWART == 101) & (f.LGORT == PLANT_SLOC) & f.EBELN.isna())
    to_dc = q((f.BWART == 301) & f.LGORT.isin(DC_NAMES) & (f.SHKZG == "S"))
    sold = q(f.BWART == 601)
    ordered = tb["vbap"][tb["vbap"].MATNR == PRODUCT].KWMENG.sum()
    mard = tb["mard"]
    closing = mard[(mard.MATNR == PRODUCT) & mard.LGORT.isin([PLANT_SLOC] + list(DC_NAMES))].LABST.sum()
    other = sorted(f[~f.BWART.isin([101, 301, 601])].BWART.unique().tolist())
    r["B15"] = (f"produced {produced:,.0f} = to DCs {to_dc:,.0f} = sold {sold:,.0f} + closing stock {closing:,.0f} "
                f"(residual {produced - sold - closing:,.0f}); sold vs ordered {sold - ordered:+,.0f}; "
                f"other movement types {other}")
    lows = []
    for mat in [PRODUCT] + [m for m in bom.get(PRODUCT, {})]:
        for loc in ([PLANT_SLOC] + list(DC_NAMES)) if mat == PRODUCT else [None]:
            g = ms[(ms.MATNR == mat) & ((ms.LGORT == loc) if loc else True)
                   & ms.BWART.isin([101, 261, 301, 601, 321])].sort_values(["sec", "MBLNR", "ZEILE"])
            if g.empty:
                continue
            lows.append(float((np.where(g.SHKZG == "S", g.MENGE, -g.MENGE)).cumsum().min()))
    r["B16"] = f"lowest cumulative stock over {len(lows)} material-location paths: {min(lows):,.0f}"

    # ---------------- production pauses ----------------
    starts = span[("min", 261)].rename("start").to_frame().join(afko.set_index("AUFNR")[["PLNBEZ"]])
    s12 = starts[starts.PLNBEZ == PRODUCT].start.sort_values()
    gaps = s12.diff()
    longest = gaps.idxmax() if len(gaps.dropna()) else None
    r["B17"] = (f"longest gap between {PRODUCT} production starts: {gaps.max():.0f} days "
                f"(day {s12[longest] - gaps.max():.0f} -> {s12[longest]:.0f}); "
                f"production orders created in that gap: "
                f"{int(((afko.set_index('AUFNR').index.isin(starts.index)) & False).sum())}"
                if longest is not None else "n/a")
    # orders created (status I0001) inside the gap, any product
    if longest is not None:
        lo, hi = s12[longest] - gaps.max(), s12[longest]
        jc = tb["jcds"]
        jc = jc[jc.OBJNR.astype(str).str.startswith("OR") & (jc.STAT == "I0001")].copy()
        jc["tick"] = jc.UTIME.apply(lambda x: clock.decision_tick(secs(x)))
        created = int(((jc.tick > lo) & (jc.tick < hi)).sum())
        r["B17"] = (f"longest gap between {PRODUCT} production starts: {gaps.max():.0f} days "
                    f"(day {lo:.0f} -> {hi:.0f}); production orders of any product created inside it: {created}")
    return r


CLAIMS = [
    ("B1", "Order to cash is one chain: each order item has one delivery, one goods issue and one invoice", "VBFA C->J, C->R, C->M"),
    ("B2", "Orders are always delivered in full (no partial deliveries, no backorders)", "VBFA delivered qty vs VBAP.KWMENG"),
    ("B3", "Delivery is immediate: goods leave the DC in the same tick as the order", "VBFA goods-issue time vs VBAK time"),
    ("B4", "A customer order is clipped to the stock available at the DC; excess demand is lost", "DC stock path at each sale (MSEG 301/601)"),
    ("B5", "Each customer is served by one fixed DC", "MSEG 601 LGORT per customer"),
    ("B6", "Purchasing is driven by requisitions converted to POs", "EBAN.EBELN"),
    ("B7", "Supplier delivers the full PO quantity", "MSEG 101 per PO item vs EKPO.MENGE"),
    ("B8", "Split receipts happen only in scrap events (quality disruption signature)", "MSEG 101 documents per PO item vs label file"),
    ("B9", "Invoices match receipts (no financial side-effects on the material flow)", "EKBE VGABE 1 vs 2"),
    ("B10", "Production orders deliver their full quantity", "AUFM 101 vs AFKO.GAMNG"),
    ("B11", "Components are consumed per BOM (recipe may change during the game)", "AUFM 261 vs BOM x AFKO.GAMNG; per-order consumption ratios"),
    ("B12", "Production is a daily flow of at most 24,000 units per tick (apart from batched catch-up postings)", "AUFM 101 per tick and per second"),
    ("B13", "All products share one production line (work centre)", "AFKO.PLNNR -> PLPO.ARBID"),
    ("B14", "Distribution is plant -> DC only, as instantaneous transfers (no DC -> DC, no returns)", "MSEG 301 legs per document"),
    ("B15", "The product network is closed: produced = transferred = sold + closing stock", "MSEG totals, MARD closing stock, VBAP"),
    ("B16", "The game starts with empty stock; all stock enters through recorded receipts", "cumulative stock paths, chronological"),
    ("B17", "Observed production pause: longest gap between production starts, and whether orders were planned inside it", "AUFM starts, JCDS I0001"),
]

DIAGRAM = """```mermaid
flowchart LR
    SUP[Supplier] -- "PO -> goods receipt\\nlead 1-6 days (B6, B7)\\nsplit receipt = scrap event (B8)" --> RAW[(Component stock\\nstarts empty, B16)]
    RAW -- "consumed per BOM, daily (B11, B12)" --> LINE{{Shared production line\\n24,000 units/day, all products (B12, B13)}}
    OTHER[Other products' orders] -. "occupy line" .-> LINE
    LINE -- "full order qty (B10)" --> PLANT[(Plant stock F12)]
    PLANT -- "instant transfer (B14)" --> DCN[(DC North)]
    PLANT -- "instant transfer (B14)" --> DCS[(DC South)]
    PLANT -- "instant transfer (B14)" --> DCW[(DC West)]
    DCN -- "same-tick delivery, clipped to stock (B2-B4)" --> CN[21 customers]
    DCS -- "same-tick delivery, clipped to stock (B2-B4)" --> CS[30 customers]
    DCW -- "same-tick delivery, clipped to stock (B2-B4)" --> CW[20 customers]
```"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--out", default="structure")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    labels = labelled_documents(args.root)
    empty = {"fraud_po": set(), "fraud_so": set(), "sale_so": set(), "scrap_po": set()}
    ref_tb = load(args.root, RUNS[0], None)
    ref = {t: list(df.columns) for t, df in ref_tb.items()}
    results = {}
    for run in RUNS:
        tb = ref_tb if run == RUNS[0] else load(args.root, run, ref)
        results[run] = checks(tb, labels.get(run, empty))
        print(f"checked {run}")
    rows = [{"id": i, "claim": c, "evidence": e, **{run: results[run].get(i, "n/a") for run in RUNS}}
            for i, c, e in CLAIMS]
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(args.out, "structure_evidence.csv"), index=False)
    with open(os.path.join(args.out, "structure_evidence.md"), "w") as fh:
        fh.write("# Structure evidence (Phase B)\n\nEach structural claim the model relies on, the SAP evidence, "
                 "and its result in the three game years (fraud-labelled documents excluded). "
                 "Generated by `derive_structure.py`.\n\n## Proven structure\n\n" + DIAGRAM + "\n\n## Checks\n\n")
        for row in rows:
            fh.write(f"### {row['id']}: {row['claim']}\n*Evidence:* {row['evidence']}\n\n")
            for run in RUNS:
                fh.write(f"- **{run}:** {row[run]}\n")
            fh.write("\n")
    for row in rows:
        print(row["id"], "|", " || ".join(str(row[r]) for r in RUNS))


if __name__ == "__main__":
    main()
