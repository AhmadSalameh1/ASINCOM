"""Generate the UPPAAL V12 model from a twin input file (same spec, same data as the Python twin).

The model is one day-tick timed automaton whose single edge calls step() every time unit (1 tu = 1 game day,
DR-1). step() executes the twin's day in the same order (docs/model_spec.md):
    transit arrivals -> supplier receipts -> production (erpsim line rule) -> plant->DC transfers -> sales -> decisions
Decisions are the players' recorded decisions (policy replay, as in validation round 2). Disruptions are
switchable constants, in the style of the earlier switchable STA model.

Stochastic element: supplier lead times, sampled from the recorded PMFs with random(). With LEAD_MODE = 1 every
lead time is the PMF median, which makes the model deterministic: its `simulate` trace must then match the
Python twin run with lead_mode="median" (see crosscheck.py).

Quantities are UPPAAL `double`s (supported for statistical model checking, which is all this model is used for),
so the arithmetic is the same IEEE arithmetic as the Python twin: recipes such as 0.35 units per unit need no
scaling, no rounding differences arise, and no 32-bit integer overflow is possible.

Usage:
    python generate_uppaal.py ../twin/inputs/normal_2.json [--out V12_normal_2.xml]
"""
import argparse
import json
import os
from collections import defaultdict
from xml.sax.saxutils import escape

import numpy as np

DCS = ["North", "South", "West"]
CHANGEOVER_DAYS = 0.6
# expressions in the cross-check trace (crosscheck.py compares each of them day by day)
TRACE = ["sold_day", "lost_day", "lost_total", "stockout_days", "dc[0]", "dc[1]", "dc[2]", "plant", "produced_f12"]


def trace_exprs(n_comp):
    return TRACE + [f"comp[{i}]" for i in range(n_comp)]


def arr(values):
    return "{" + ", ".join(str(int(v)) for v in values) + "}"


def arr2(rows):
    return "{" + ", ".join(arr(r) for r in rows) + "}"


def dlit(v):
    """UPPAAL double literal, never in scientific notation."""
    return np.format_float_positional(float(v), unique=True, trim="0")


def darr(values):
    return "{" + ", ".join(dlit(v) for v in values) + "}"


def darr2(rows):
    return "{" + ", ".join(darr(r) for r in rows) + "}"


def barr(values):
    return "{" + ", ".join("true" if v else "false" for v in values) + "}"


def build(inp, lead_mode=0):
    first, last = inp["days"]["first"], inp["days"]["last"]
    nday = last + 30                      # room for late arrivals
    comps = inp["components"]
    cidx = {c: i for i, c in enumerate(comps)}
    dc_of = {c["id"]: c["dc"] for c in inp["customers"]}

    demand = [[0] * nday for _ in DCS]
    for o in inp["demand"]["recorded_orders"]:
        if o["customer"] in dc_of and o["day"] < nday:
            demand[DCS.index(dc_of[o["customer"]])][o["day"]] += int(round(o["qty"]))

    transfers = []                        # (day, dc, qty) in the twin's order
    for t in inp["recorded_transfers"]:
        transfers.append((t["day"], DCS.index(t["dc"]), int(round(t["qty"]))))

    per_day = defaultdict(list)           # production orders in the twin's order (F12 list first, then others)
    for o in inp["recorded_production_orders"] + inp["other_production_orders"]:
        per_day[o["day"]].append(o)
    orders = [o for d in sorted(per_day) for o in per_day[d]]
    prod_idx = {inp["product"]: 0}
    for o in orders:
        prod_idx.setdefault(o["product"], len(prod_idx))
    rec = [[(o.get("issued_recipe") or o["recipe"]).get(c, 0.0) for c in comps] for o in orders]

    pos = sorted(inp["recorded_pos"], key=lambda p: (p["day"] if not p.get("pre_start") else first - 1))
    po_rows = [(first - 1 if p.get("pre_start") else p["day"], cidx[p["material"]], int(round(p["qty"])),
                1 if p.get("pre_start") else 0) for p in pos]

    def pmf(g):
        # same normalisation and median rule as Twin._lead (input key order, first value with cumsum >= 0.5)
        vals = np.array(list(map(int, inp["lead_time_pmf"][g].keys())))
        p = np.array(list(inp["lead_time_pmf"][g].values()), dtype=float)
        p = p / p.sum()
        cum = np.cumsum(p)
        med = int(vals[np.searchsorted(cum, 0.5)])
        cum[-1] = 1.0
        return list(vals), list(cum), med

    fv, fc, fmed = pmf("food")
    pv, pc, pmed = pmf("packaging")
    is_food = [1 if c.startswith("AA-R") else 0 for c in comps]
    n_po_max = len(po_rows) + 400

    decl = f"""// ============================================================================
// V12 supply-chain twin (UPPAAL SMC), generated from model/twin/inputs/{inp['run']}.json
// Spec: docs/model_spec.md. Same data and step order as the Python twin (model/twin/twin.py),
// policy replay (the players' recorded decisions). 1 time unit = 1 game day (DR-1).
// ============================================================================
const int FIRST = {first};
const int LAST = {last};
const int NDAY = {nday};
const int NDC = 3;                       // 0 North, 1 South, 2 West
const int NC = {len(comps)};                        // components: {', '.join(comps)}
const double CAP = {float(inp['capacity_per_day'])};                  // line capacity per day (M6)
const double CHANGEOVER = {CHANGEOVER_DAYS} * CAP;      // capacity lost on a product switch (0.6 day)

// ---------------- switches ----------------
const int LEAD_MODE = {lead_mode};                 // 0 = sampled lead times, 1 = PMF median (deterministic cross-check)

// E1 supplier delay: POs created in [S1, E1] arrive ceil(REL/100 x lead) days later
const bool EN_SUPPLIER_DELAY = false;
const int SD_START = 101; const int SD_END = 120; const int SD_REL100 = 75;
// E2 quality loss: receipts due in [S, E] of flagged materials lose the share Q_BLOCK; the rest arrives EXTRA days late;
// the blocked quantity is re-ordered the same day (MRP rule R5)
const bool EN_QUALITY = false;
const int Q_START = 101; const int Q_END = 120; const double Q_BLOCK = 0.041; const int Q_EXTRA = 2;
const bool Q_MAT[NC] = {barr(is_food)};
// E3 line stoppage: line unavailable in [LD_START, LD_END]
const bool EN_LINE_DOWN = false;
const int LD_START = 101; const int LD_END = 110;
// E4 demand shift: demand x DF in [DS_START, DS_END]
const bool EN_DEMAND = false;
const int DS_START = 101; const int DS_END = 120; const double DF = 1.19;
// E5 transit delay: shipments leaving in [T_START, T_END] arrive T_DAYS later
const bool EN_TRANSIT = false;
const int T_START = 101; const int T_END = 120; const int T_DAYS = 4;

// ---------------- recorded exogenous inputs and decisions ----------------
const int DEMAND[NDC][NDAY] = {arr2(demand)};   // recorded customer orders per DC and day; unmet demand is lost (B2-B4)
const int N_TR = {len(transfers)};                  // recorded plant -> DC transfers, instantaneous (B14)
const int TR_DAY[N_TR] = {arr([t[0] for t in transfers])};
const int TR_DC[N_TR] = {arr([t[1] for t in transfers])};
const int TR_QTY[N_TR] = {arr([t[2] for t in transfers])};
const int N_ORD = {len(orders)};                  // recorded production orders, all products, one shared FIFO line (B11-B13)
const int ORD_DAY[N_ORD] = {arr([o['day'] for o in orders])};
const int ORD_PROD[N_ORD] = {arr([prod_idx[o['product']] for o in orders])};     // 0 = F12
const double ORD_QTY[N_ORD] = {darr([o['qty'] for o in orders])};
const double ORD_REC[N_ORD][NC] = {darr2(rec)};   // components issued per unit (issued recipe)
const int N_REC_PO = {len(po_rows)};                  // recorded purchase orders; pre-start POs are the opening stock (B16)
const int RPO_DAY[N_REC_PO] = {arr([p[0] for p in po_rows])};
const int RPO_MAT[N_REC_PO] = {arr([p[1] for p in po_rows])};
const int RPO_QTY[N_REC_PO] = {arr([p[2] for p in po_rows])};
const bool RPO_PRE[N_REC_PO] = {barr([p[3] for p in po_rows])};
const bool IS_FOOD[NC] = {barr(is_food)};
// supplier lead-time PMFs in days, food and packaging (L3, L4)
const int NF = {len(fv)}; const int F_VAL[NF] = {arr(fv)}; const double F_CUM[NF] = {darr(fc)}; const int F_MED = {fmed};
const int NP = {len(pv)}; const int P_VAL[NP] = {arr(pv)}; const double P_CUM[NP] = {darr(pc)}; const int P_MED = {pmed};

// ---------------- state ----------------
int[0, NDAY] day = FIRST - 1;
double comp[NC];                         // available component stock (B16: starts empty)
double plant = 0.0;
double dc[NDC];
double intransit[NDC][NDAY];
const int N_PO_MAX = {n_po_max};
double po_qty[N_PO_MAX]; int[0, NDAY + 60] po_due[N_PO_MAX]; int[0, NC] po_mat[N_PO_MAX]; bool po_open[N_PO_MAX]; bool po_qdone[N_PO_MAX];
int[0, N_PO_MAX] n_po = 0;
int[0, N_ORD] qhead = 0; int[0, N_ORD] qtail = 0; int[0, N_ORD] next_ord = 0; int[0, N_REC_PO] next_po = 0; int[0, N_TR] next_tr = 0;
double remaining[N_ORD]; bool started[N_ORD];
int[-1, 10] last_prod = -1;
double changeover_left = 0.0;
// KPIs
double sold_total = 0.0; double lost_total = 0.0; double sold_day = 0.0; double lost_day = 0.0; double produced_f12 = 0.0;
int[0, NDAY] stockout_days = 0;

// ---------------- functions ----------------
int lead(int m) {{
    double u; int i;
    if (IS_FOOD[m]) {{
        if (LEAD_MODE == 1) return F_MED;
        u = random(1.0);
        for (i = 0; i < NF; i++) {{ if (u < F_CUM[i]) return F_VAL[i]; }}
        return F_VAL[NF - 1];
    }}
    if (LEAD_MODE == 1) return P_MED;
    u = random(1.0);
    for (i = 0; i < NP; i++) {{ if (u < P_CUM[i]) return P_VAL[i]; }}
    return P_VAL[NP - 1];
}}

void new_po(int m, double q, int due_offset, bool qdone) {{
    int l = due_offset;
    if (l < 0) {{
        l = lead(m);
        if (EN_SUPPLIER_DELAY && day >= SD_START && day <= SD_END) l = l + (l * SD_REL100 + 99) / 100;
    }}
    po_qty[n_po] = q; po_due[n_po] = day + l; po_mat[n_po] = m; po_open[n_po] = true; po_qdone[n_po] = qdone;
    n_po++;
}}

void arrivals() {{
    int d;
    for (d = 0; d < NDC; d++) {{ dc[d] += intransit[d][day]; intransit[d][day] = 0; }}
}}

void receipts() {{
    int i; double blocked; double rest; int m; int n = n_po;
    for (i = 0; i < n; i++) {{
        if (po_open[i] && po_due[i] <= day) {{
            po_open[i] = false; m = po_mat[i];
            if (EN_QUALITY && !po_qdone[i] && Q_MAT[m] && day >= Q_START && day <= Q_END) {{
                blocked = po_qty[i] * Q_BLOCK;
                rest = po_qty[i] - blocked;
                if (blocked > 0.0) new_po(m, blocked, -1, true);          // rule R5 replacement
                if (Q_EXTRA > 0) new_po(m, rest, Q_EXTRA, true);
                else comp[m] += rest;
            }} else {{
                comp[m] += po_qty[i];
            }}
        }}
    }}
}}

bool can_start(int o) {{
    int c;
    for (c = 0; c < NC; c++) {{
        if (ORD_REC[o][c] > 0.0 && comp[c] + 0.000001 < ORD_REC[o][c] * remaining[o]) return false;
    }}
    return true;
}}

void produce() {{
    double cap = CAP; double used; double q; int o; int c;
    if (EN_LINE_DOWN && day >= LD_START && day <= LD_END) return;
    used = changeover_left < cap ? changeover_left : cap;
    changeover_left -= used; cap -= used;
    while (qhead < qtail && cap > 0.0) {{
        o = qhead;
        if (!started[o]) {{
            if (!can_start(o)) return;                                // waits for its full batch
            if (last_prod != -1 && ORD_PROD[o] != last_prod) {{
                last_prod = ORD_PROD[o];
                changeover_left = CHANGEOVER;
                used = changeover_left < cap ? changeover_left : cap;
                changeover_left -= used; cap -= used;
                if (cap <= 0.0) return;
            }}
            started[o] = true;
        }}
        q = remaining[o] < cap ? remaining[o] : cap;
        for (c = 0; c < NC; c++) comp[c] -= ORD_REC[o][c] * q;
        remaining[o] -= q; cap -= q; last_prod = ORD_PROD[o];
        if (ORD_PROD[o] == 0) {{ plant += q; produced_f12 += q; }}
        if (remaining[o] <= 0.0) qhead++;
    }}
}}

void to_dc(int d, double q) {{
    if (EN_TRANSIT && day >= T_START && day <= T_END) intransit[d][day + T_DAYS] += q;
    else dc[d] += q;
}}

void push() {{
    double sent = 0.0; double q;
    while (next_tr < N_TR && TR_DAY[next_tr] < day) next_tr++;
    while (next_tr < N_TR && TR_DAY[next_tr] == day) {{
        q = TR_QTY[next_tr] < plant - sent ? TR_QTY[next_tr] : plant - sent;
        if (q > 0.0) {{ to_dc(TR_DC[next_tr], q); sent += q; }}
        next_tr++;
    }}
    plant -= sent;
}}

void sales() {{
    int d; double dem; double s;
    sold_day = 0.0; lost_day = 0.0;
    for (d = 0; d < NDC; d++) {{
        dem = DEMAND[d][day] * 1.0;
        if (EN_DEMAND && day >= DS_START && day <= DS_END) dem = dem * DF;
        s = dem < dc[d] ? dem : dc[d];
        dc[d] -= s; sold_day += s; lost_day += dem - s;
    }}
    sold_total += sold_day; lost_total += lost_day;
}}

void decide() {{
    int d;
    bool out = false;
    while (next_ord < N_ORD && ORD_DAY[next_ord] == day) {{
        remaining[next_ord] = ORD_QTY[next_ord]; started[next_ord] = false;
        next_ord++; qtail = next_ord;
    }}
    while (next_po < N_REC_PO && RPO_DAY[next_po] == day) {{
        if (RPO_PRE[next_po]) new_po(RPO_MAT[next_po], RPO_QTY[next_po], 1, false);   // opening stock
        else new_po(RPO_MAT[next_po], RPO_QTY[next_po], -1, false);
        next_po++;
    }}
    for (d = 0; d < NDC; d++) {{ if (dc[d] <= 0.0) out = true; }}
    if (out) stockout_days++;
}}

void step() {{
    arrivals();
    receipts();
    produce();
    push();
    sales();
    decide();
    day++;
}}
"""
    template = """<template><name>Day</name><declaration>clock x;</declaration>
<location id="id0" x="0" y="0"><name x="-10" y="-34">Tick</name><label kind="invariant" x="-10" y="17">x &lt;= 1</label></location>
<location id="id1" x="200" y="0"><name x="190" y="-34">End</name><label kind="invariant" x="190" y="17">x &lt;= 1</label></location>
<init ref="id0"/>
<transition><source ref="id0"/><target ref="id0"/><label kind="guard" x="-60" y="-100">x &gt;= 1 &amp;&amp; day &lt;= LAST</label><label kind="assignment" x="-60" y="-80">x = 0, step()</label><nail x="-50" y="-60"/><nail x="50" y="-60"/></transition>
<transition><source ref="id0"/><target ref="id1"/><label kind="guard" x="60" y="10">x &gt;= 1 &amp;&amp; day &gt; LAST</label></transition>
<transition><source ref="id1"/><target ref="id1"/><label kind="guard" x="160" y="-100">x &gt;= 1</label><label kind="assignment" x="160" y="-80">x = 0</label><nail x="150" y="-60"/><nail x="250" y="-60"/></transition>
</template>"""
    horizon = last - first + 3
    queries = [
        (f"simulate [<={horizon}; 1] {{{', '.join(trace_exprs(len(comps)))}}}",
         "Cross-check trace: run on the _crosscheck file (LEAD_MODE = 1) and compare with crosscheck.py"),
        (f"E[<={horizon}; 200] (max: lost_total)", "Expected lost demand over the year"),
        (f"E[<={horizon}; 200] (max: stockout_days)", "Expected number of days with a DC stock-out"),
        (f"Pr[<={horizon}] (<> lost_total > 50000)", "Probability that lost demand exceeds 50,000 units"),
    ]
    q_xml = "".join(f"<query><formula>{escape(f)}</formula><comment>{escape(c)}</comment></query>" for f, c in queries)
    xml = ('<?xml version="1.0" encoding="utf-8"?>\n'
           '<!DOCTYPE nta PUBLIC \'-//Uppaal Team//DTD Flat System 1.6//EN\' \'http://www.it.uu.se/research/group/darts/uppaal/flat-1_6.dtd\'>\n'
           f"<nta><declaration>{escape(decl)}</declaration>{template}"
           "<system>D = Day();\nsystem D;</system>"
           f"<queries>{q_xml}</queries></nta>\n")
    return xml


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs")
    ap.add_argument("--out")
    ap.add_argument("--crosscheck", action="store_true", help="LEAD_MODE = 1 (deterministic, for crosscheck.py)")
    a = ap.parse_args()
    inp = json.load(open(a.inputs))
    suffix = "_crosscheck" if a.crosscheck else ""
    out = a.out or os.path.join(os.path.dirname(__file__), f"V12_{inp['run']}{suffix}.xml")
    with open(out, "w") as fh:
        fh.write(build(inp, 1 if a.crosscheck else 0))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
