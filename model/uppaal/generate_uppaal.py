"""Generate the UPPAAL V12 model from a twin input file (same spec, same data as the Python twin).

The model is one day-tick timed automaton whose single edge calls step() every time unit (1 tu = 1 game day,
DR-1). step() executes the twin's day in the same order (docs/model_spec.md, model/twin/twin.py):
    [notice day: observe the plant, choose the response]
    transit arrivals -> supplier receipts -> production (erpsim line rule) -> plant->DC transfers -> sales
    -> other products' sales -> decisions
Decisions are the players' recorded decisions (policy replay, transfers deferred: validation Amendment 3),
plus, from the disruption notice on, a response with the players' three levers (model/twin/controllers.py,
ResponseController): component buffer (POs), extra F12 batch and F12 line priority (conversions), DC rebalancing
(transfers). The response is either a fixed action or the certified decision tree (docs/ai_layers.md, L3/L4),
which reads the same 34 features as in Python, computed inside the model.

Scenario modes (SCEN_MODE)
  0  switches: any combination of the five disruptions, fixed windows (the earlier switchable style); no notice
  1  one fixed disruption (FIX_*), notified on FIX_START
  2  one disruption sampled at t = 0 within its evidence bounds, at a start day drawn uniformly over the
     steady months: the population of the AI episodes (model/ai/episodes.py). The query
     Pr[...](<> win_done && win_ok) is then an SMC estimate, with confidence interval, of the L4 service property.
Controller modes (CTRL_MODE): 0 players only, 1 fixed action ACT_FIXED from the notice day, 2 certified tree.

Stochastic elements: supplier lead times (recorded PMFs) and, in SCEN_MODE 2, the disruption. With LEAD_MODE = 1
every lead time is the PMF median, so with SCEN_MODE 0 or 1 the model is deterministic and must match the
Python twin day by day (crosscheck.py).

Quantities are UPPAAL `double`s (supported for statistical model checking, which is all this model is used for),
so the arithmetic is the same IEEE arithmetic as the Python twin.

Usage:
    python generate_uppaal.py ../twin/inputs/normal_2.json                      # players, switches (V12_<run>.xml)
    python generate_uppaal.py ../twin/inputs/normal_2.json --crosscheck         # same, LEAD_MODE = 1
    python generate_uppaal.py ../twin/inputs/normal_2.json --ai                 # certification models (tree, players)
    python generate_uppaal.py IN --scen-mode 1 --ctrl-mode 2 --fix E3,120,10 --lead-mode 1 --out X.xml   # tests
"""
import argparse
import json
import os
from collections import defaultdict
from xml.sax.saxutils import escape

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DCS = ["North", "South", "West"]
CHANGEOVER_DAYS = 0.6
USAID_Q = ([0.0, 0.5, 0.75, 0.9, 0.95], [0.0, 0.124, 0.372, 0.746, 0.963])   # model/ai/episodes.py
EPISODE, HORIZON, RESP_WINDOW, L_STAR = 20, 60, 40, 1.0
TYPES = ["E1", "E2", "E3", "E4", "E5"]
# the 34 features, in the order of model/ai/common.py FEATURES
FEATURES = ([f"type_{t}" for t in TYPES] + ["e1_rel", "e2_share", "e2_allfood", "e3_days", "e4_factor", "e5_days"]
            + [f"cover_{c}" for c in ["AA-R01", "AA-R02", "AA-R03", "AA-R04", "AA-R05", "AA-R06", "AA-P01", "AA-P02"]]
            + ["min_cover_f12_components", "queue_f12_days", "queue_other_line_days", "queue_orders", "head_blocked",
               "head_is_f12", "changeover_line_days", "plant_days"] + [f"dc_cover_{d}" for d in DCS]
            + ["dc_min_cover", "fg_cover", "lost_20d_days", "backlog_days"])
# expressions in the cross-check trace (crosscheck.py compares each of them day by day)
TRACE = ["sold_day", "lost_day", "lost_total", "stockout_days", "dc[0]", "dc[1]", "dc[2]", "plant", "produced_f12",
         "lost_other_day", "lost_win", "action"]


def trace_exprs(n_comp):
    return TRACE + [f"comp[{i}]" for i in range(n_comp)]


def default_tree(run):
    name = "tree_normal_2" if run == "normal_2" else f"tree_{run}_adapted"
    return os.path.join(HERE, "..", "ai", "results", f"{name}.json")


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


def start_days(inp):
    """Same start-day population as model/ai/episodes.py."""
    steady = sorted(inp["demand"]["steady_months"])
    return [d for m in steady for d in range((m - 1) * 20 + 1, m * 20 + 1) if d + HORIZON + 20 <= inp["days"]["last"]]


def build(inp, lead_mode=0, scen_mode=0, ctrl_mode=0, act_fixed=0, fix=None, tree=None):
    first, last = inp["days"]["first"], inp["days"]["last"]
    nday = last + 30                      # room for late arrivals
    comps = inp["components"]
    cidx = {c: i for i, c in enumerate(comps)}
    dc_of = {c["id"]: c["dc"] for c in inp["customers"]}

    demand = [[0] * nday for _ in DCS]
    for o in inp["demand"]["recorded_orders"]:
        if o["customer"] in dc_of and o["day"] < nday:
            demand[DCS.index(dc_of[o["customer"]])][o["day"]] += int(round(o["qty"]))

    transfers = [(t["day"], DCS.index(t["dc"]), int(round(t["qty"]))) for t in inp["recorded_transfers"]]

    per_day = defaultdict(list)           # production orders in the twin's order (F12 list first, then others)
    for o in inp["recorded_production_orders"] + inp["other_production_orders"]:
        per_day[o["day"]].append(o)
    orders = [o for d in sorted(per_day) for o in per_day[d]]
    prod_idx = {inp["product"]: 0}
    for o in orders:
        prod_idx.setdefault(o["product"], len(prod_idx))
    planning = [p for p in inp.get("planning_products", [inp["product"]]) if p != inp["product"]]
    for p in planning:
        prod_idx.setdefault(p, len(prod_idx))
    nprod = len(prod_idx)
    osales = [[0.0] * nday for _ in range(nprod)]
    for p in planning:
        for d, q in inp.get("other_product_daily_sales", {}).get(p, {}).items():
            if int(d) < nday:
                osales[prod_idx[p]][int(d)] = float(q)
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
    food_idx = [i for i, f in enumerate(is_food) if f]
    n_po_max = len(po_rows) + 1200
    sdays = start_days(inp)

    tree = tree or json.load(open(default_tree(inp["run"])))
    if tree["features"] != FEATURES:
        raise ValueError("the tree's feature list differs from the features computed in the model")
    levers = tree["levers"]
    fix = fix or {"type": 3, "start": sdays[len(sdays) // 2], "e1_rel": 0.75, "e2_share": 0.041, "e2_mat": -1,
                  "e3_days": 10, "e4_factor": 1.19, "e5_days": 4}

    decl = f"""// ============================================================================
// V12 supply-chain twin with the AI response (UPPAAL SMC), generated from model/twin/inputs/{inp['run']}.json
// Spec: docs/model_spec.md and docs/uppaal.md. Same data and step order as the Python twin (model/twin/twin.py)
// with the players' recorded decisions (transfers deferred, Amendment 3) and the response levers of
// model/twin/controllers.py (ResponseController). 1 time unit = 1 game day (DR-1).
// ============================================================================
const int FIRST = {first};
const int LAST = {last};
const int NDAY = {nday};
const int NDC = 3;                       // 0 North, 1 South, 2 West
const int NC = {len(comps)};                        // components: {', '.join(comps)}
const int NPROD = {nprod};                     // products: {', '.join(f'{i} {p}' for p, i in prod_idx.items())}
const double CAP = {float(inp['capacity_per_day'])};                  // line capacity per day (M6)
const double CHANGEOVER = {CHANGEOVER_DAYS} * CAP;      // capacity lost on a product switch (0.6 day)

// ---------------- configuration ----------------
const int LEAD_MODE = {lead_mode};                 // 0 = sampled lead times, 1 = PMF median (deterministic cross-check)
const int SCEN_MODE = {scen_mode};                 // 0 switches below, 1 one fixed disruption (FIX_*), 2 sampled within evidence bounds
const int CTRL_MODE = {ctrl_mode};                 // 0 players only, 1 fixed action ACT_FIXED, 2 certified tree ({tree['name']})
const int ACT_FIXED = {act_fixed};                 // 0 none, 1 po5, 2 po10, 3 fg, 4 ship, 5 prio, 6 fg+prio, 7 po10+fg+prio
const int RESP_START = {fix['start']};             // SCEN_MODE 0: notice day for a fixed action

// SCEN_MODE 0 switches. E1 supplier delay: POs created in [S, E] arrive ceil(REL/100 x lead) days later
const bool EN_SUPPLIER_DELAY = false;
const int SD_START = 101; const int SD_END = 120; const int SD_REL100 = 75;
// E2 quality loss: receipts due in [S, E] of flagged materials lose the share Q_BLOCK; the rest arrives Q_EXTRA days
// late; the blocked quantity is re-ordered the same day (MRP rule R5)
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

// SCEN_MODE 1: one disruption (type 1..5 = E1..E5), notified and starting on FIX_START (window 20 days; E3: its length)
const int FIX_TYPE = {fix['type']}; const int FIX_START = {fix['start']};
const double FIX_E1_REL = {dlit(fix['e1_rel'])}; const double FIX_E2_SHARE = {dlit(fix['e2_share'])}; const int FIX_E2_MAT = {fix['e2_mat']};  // -1 = all food
const int FIX_E3_DAYS = {fix['e3_days']}; const double FIX_E4_FACTOR = {dlit(fix['e4_factor'])}; const int FIX_E5_DAYS = {fix['e5_days']};

// SCEN_MODE 2: evidence bounds (docs/disruptions.md, model/ai/episodes.py)
const int NS = {len(sdays)}; const int START_DAYS[NS] = {arr(sdays)};   // steady-month start days
const double USAID_U[5] = {darr(USAID_Q[0])}; const double USAID_R[5] = {darr(USAID_Q[1])};  // E1 relative delay quantiles
const int NFOOD = {len(food_idx)}; const int FOOD[NFOOD] = {arr(food_idx)};

// ---------------- response: actions and certified tree ----------------
const int NACT = {len(levers)};
const int ACT_PO[NACT] = {arr([l['po_days'] for l in levers])};          // component cover target, days (lever 2)
const double ACT_FG[NACT] = {darr([l['fg_units'] for l in levers])};    // extra F12 batch on the notice day (lever 1)
const bool ACT_SHIP[NACT] = {barr([l['ship'] for l in levers])};        // rebalance DCs by days of cover (lever 3)
const int ACT_PRIO[NACT] = {arr([l['prio'] for l in levers])};          // days of F12 line priority (lever 1)
const int RESP_WINDOW = {RESP_WINDOW};
const int NFEAT = {len(FEATURES)};    // {', '.join(f'{i} {f}' for i, f in enumerate(FEATURES))}
const int NNODE = {len(tree['feature'])};
const int TREE_F[NNODE] = {arr(tree['feature'])};
const double TREE_T[NNODE] = {darr(tree['threshold'])};
const int TREE_L[NNODE] = {arr(tree['left'])};
const int TREE_R[NNODE] = {arr(tree['right'])};
const int TREE_A[NNODE] = {arr(tree['action'])};
const double L_STAR = {L_STAR};   // service limit: lost demand (all products) over WIN days <= L_STAR days of demand
const int WIN = {HORIZON};

// ---------------- recorded exogenous inputs and decisions ----------------
const double DEMAND[NDC][NDAY] = {darr2(demand)};   // recorded customer orders per DC and day; unmet demand is lost (B2-B4)
const int N_TR = {len(transfers)};                  // recorded plant -> DC transfers, instantaneous (B14)
const int TR_DAY[N_TR] = {arr([t[0] for t in transfers])};
const int TR_DC[N_TR] = {arr([t[1] for t in transfers])};
const double TR_QTY[N_TR] = {darr([t[2] for t in transfers])};
const int N_ORD = {len(orders)};                  // recorded production orders, all products, one shared FIFO line (B11-B13)
const int ORD_DAY[N_ORD] = {arr([o['day'] for o in orders])};
const int ORD_PROD[N_ORD] = {arr([prod_idx[o['product']] for o in orders])};     // 0 = F12
const double ORD_QTY[N_ORD] = {darr([o['qty'] for o in orders])};
const double ORD_REC[N_ORD][NC] = {darr2(rec)};   // components issued per unit (issued recipe)
const int N_REC_PO = {len(po_rows)};                  // recorded purchase orders; pre-start POs are the opening stock (B16)
const int RPO_DAY[N_REC_PO] = {arr([p[0] for p in po_rows])};
const int RPO_MAT[N_REC_PO] = {arr([p[1] for p in po_rows])};
const double RPO_QTY[N_REC_PO] = {darr([p[2] for p in po_rows])};
const bool RPO_PRE[N_REC_PO] = {barr([p[3] for p in po_rows])};
const double PO_STEP[NC] = {darr([inp['po_rounding'][c] for c in comps])};   // PO rounding (MARC), for response POs
const bool IS_FOOD[NC] = {barr(is_food)};
// other products at planning level (DR-2): replayed daily sales, clipped to their stock
const int NPLAN = {len(planning)}; const int PLAN[NPLAN] = {arr([prod_idx[p] for p in planning])};
const double OSALES[NPROD][NDAY] = {darr2(osales)};
// supplier lead-time PMFs in days, food and packaging (L3, L4)
const int NF = {len(fv)}; const int F_VAL[NF] = {arr(fv)}; const double F_CUM[NF] = {darr(fc)}; const int F_MED = {fmed};
const int NP = {len(pv)}; const int P_VAL[NP] = {arr(pv)}; const double P_CUM[NP] = {darr(pc)}; const int P_MED = {pmed};

// ---------------- state ----------------
int[0, NDAY] day = FIRST - 1;
bool initialised = false;
// disruption in force (set by init_scen)
bool en_sd = false; int sd_s = 0; int sd_e = -1; double sd_rel = 0.0;
bool en_q = false; int q_s = 0; int q_e = -1; double q_block = 0.0; int q_extra = 0; bool q_mat[NC];
bool en_ld = false; int ld_s = 0; int ld_e = -1;
bool en_dm = false; int dm_s = 0; int dm_e = -1; double dm_f = 1.0;
bool en_tr = false; int tr_s = 0; int tr_e = -1; int tr_k = 0;
int d_type = 0; int s_start = -100;
double n_e1 = 0.0; double n_e2 = 0.0; double n_e2all = 0.0; double n_e3 = 0.0; double n_e4 = 1.0; double n_e5 = 0.0;   // notice
// plant
double comp[NC];                         // available component stock (B16: starts empty)
double plant = 0.0;
double dc[NDC];
double intransit[NDC][NDAY];
double owed[NDC];                        // transfers owed to each DC (deferred replay)
double other_stock[NPROD];
const int N_PO_MAX = {n_po_max};
double po_qty[N_PO_MAX]; int[0, NDAY + 90] po_due[N_PO_MAX]; int[0, NC] po_mat[N_PO_MAX]; bool po_open[N_PO_MAX]; bool po_qdone[N_PO_MAX];
int[0, N_PO_MAX] n_po = 0;
const int QMAX = N_ORD + 1;              // the queue: recorded orders plus one extra batch
int q_ord[QMAX]; int q_prod[QMAX]; double q_rem[QMAX]; bool q_started[QMAX];
int[0, QMAX] qhead = 0; int[0, QMAX] qtail = 0;
int held[N_ORD]; int[0, N_ORD] n_held = 0;          // other products' conversions held (priority lever)
int out_o[QMAX]; int[0, QMAX] n_out = 0;            // today's conversions (-1 = extra batch)
int[0, N_ORD] next_ord = 0; int[0, N_REC_PO] next_po = 0; int[0, N_TR] next_tr = 0;
int[-1, 20] last_prod = -1;
double changeover_left = 0.0;
// histories (for the levers and the tree's features)
double cons_hist[NC][NDAY]; double dem_hist[NDC][NDAY]; double lost_hist[NDAY]; double before[NC];
double pplan[NDC]; double rates[NDC]; double levels[NDC];
// response
int[0, NACT - 1] action = 0; int rec_idx = 0; double feat[NFEAT];
// KPIs
double sold_total = 0.0; double lost_total = 0.0; double sold_day = 0.0; double lost_day = 0.0; double produced_f12 = 0.0;
double lost_other_day = 0.0; double lost_win = 0.0; double dem_s = 1.0; bool win_done = false; bool win_ok = false;
int[0, NDAY] stockout_days = 0;

// ---------------- functions ----------------
// quantities are doubles throughout: UPPAAL's plain int is 16-bit ([-32768, 32767]) and order quantities exceed it
int ceil_d(double x) {{                // smallest integer >= x, whatever fint's rounding mode
    int k = fint(x);
    while (k < x) k++;
    while (k - 1 >= x) k--;
    return k;
}}

int floor_d(double x) {{               // largest integer <= x, whatever fint's rounding mode
    int k = fint(x);
    while (k > x) k--;
    while (k + 1 <= x) k++;
    return k;
}}

double dmin(double a, double b) {{ return a < b ? a : b; }}
double dmax(double a, double b) {{ return a > b ? a : b; }}

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

void init_scen() {{
    int i; int t; int m = -1; double u;
    for (i = 0; i < NC; i++) q_mat[i] = false;
    if (SCEN_MODE == 0) {{
        en_sd = EN_SUPPLIER_DELAY; sd_s = SD_START; sd_e = SD_END; sd_rel = SD_REL100 / 100.0;
        en_q = EN_QUALITY; q_s = Q_START; q_e = Q_END; q_block = Q_BLOCK; q_extra = Q_EXTRA;
        for (i = 0; i < NC; i++) q_mat[i] = Q_MAT[i];
        en_ld = EN_LINE_DOWN; ld_s = LD_START; ld_e = LD_END;
        en_dm = EN_DEMAND; dm_s = DS_START; dm_e = DS_END; dm_f = DF;
        en_tr = EN_TRANSIT; tr_s = T_START; tr_e = T_END; tr_k = T_DAYS;
        s_start = RESP_START;
        return;
    }}
    if (SCEN_MODE == 1) {{
        t = FIX_TYPE; s_start = FIX_START;
        n_e1 = FIX_E1_REL; n_e2 = FIX_E2_SHARE; n_e2all = FIX_E2_MAT < 0 ? 1.0 : 0.0; m = FIX_E2_MAT;
        n_e3 = FIX_E3_DAYS; n_e4 = FIX_E4_FACTOR; n_e5 = FIX_E5_DAYS;
    }} else {{
        t = 1 + floor_d(random(5.0)); if (t > 5) t = 5;
        i = floor_d(random(1.0 * NS)); if (i > NS - 1) i = NS - 1;
        s_start = START_DAYS[i];
        u = random(0.95);
        for (i = 0; i < 4; i++) {{
            if (u >= USAID_U[i] && u <= USAID_U[i + 1])
                n_e1 = USAID_R[i] + (u - USAID_U[i]) * (USAID_R[i + 1] - USAID_R[i]) / (USAID_U[i + 1] - USAID_U[i]);
        }}
        n_e2 = 0.002 + random(0.039);
        n_e2all = random(1.0) < 0.5 ? 1.0 : 0.0;
        if (n_e2all < 0.5) {{ i = floor_d(random(1.0 * NFOOD)); if (i > NFOOD - 1) i = NFOOD - 1; m = FOOD[i]; }}
        n_e3 = 1 + floor_d(random(25.0)); if (n_e3 > 25.0) n_e3 = 25.0;
        n_e4 = 1.05 + random(0.14);
        n_e5 = 1 + floor_d(random(4.0)); if (n_e5 > 4.0) n_e5 = 4.0;
    }}
    d_type = t;
    // only the notified disruption's own severity is non-default (as in the episodes)
    if (t != 1) n_e1 = 0.0;
    if (t != 2) {{ n_e2 = 0.0; n_e2all = 0.0; }}
    if (t != 3) n_e3 = 0.0;
    if (t != 4) n_e4 = 1.0;
    if (t != 5) n_e5 = 0.0;
    if (t == 1) {{ en_sd = true; sd_s = s_start; sd_e = s_start + 19; sd_rel = n_e1; }}
    if (t == 2) {{
        en_q = true; q_s = s_start; q_e = s_start + 19; q_block = n_e2; q_extra = 2;
        if (m < 0) {{ for (i = 0; i < NC; i++) q_mat[i] = IS_FOOD[i]; }} else q_mat[m] = true;
    }}
    if (t == 3) {{ en_ld = true; ld_s = s_start; ld_e = s_start + floor_d(n_e3) - 1; }}
    if (t == 4) {{ en_dm = true; dm_s = s_start; dm_e = s_start + 19; dm_f = n_e4; }}
    if (t == 5) {{ en_tr = true; tr_s = s_start; tr_e = s_start + 19; tr_k = floor_d(n_e5); }}
}}

void new_po(int m, double q, int due_offset, bool qdone) {{
    int l = due_offset;
    if (l < 0) {{
        l = lead(m);
        if (en_sd && day >= sd_s && day <= sd_e) l = l + ceil_d(sd_rel * l);
    }}
    po_qty[n_po] = q; po_due[n_po] = day + l; po_mat[n_po] = m; po_open[n_po] = true; po_qdone[n_po] = qdone;
    n_po++;
}}

double mean_hist_c(int c, int lastday, int n) {{        // mean of cons_hist[c] over the n days up to lastday
    double s = 0.0; int k = 0; int d;
    for (d = lastday - n + 1; d <= lastday; d++) {{ if (d >= FIRST - 1) {{ s += cons_hist[c][d]; k++; }} }}
    return k > 0 ? s / k : -1.0;                          // -1: no history
}}

double mean_hist_d(int dd, int lastday, int n) {{
    double s = 0.0; int k = 0; int d;
    for (d = lastday - n + 1; d <= lastday; d++) {{ if (d >= FIRST - 1) {{ s += dem_hist[dd][d]; k++; }} }}
    return k > 0 ? s / k : -1.0;
}}

double open_qty(int c) {{
    double s = 0.0; int i;
    for (i = 0; i < n_po; i++) {{ if (po_open[i] && po_mat[i] == c) s += po_qty[i]; }}
    return s;
}}

bool can_start(int qi) {{
    int c;
    for (c = 0; c < NC; c++) {{
        if (ORD_REC[q_ord[qi]][c] > 0.0 && comp[c] + 0.000001 < ORD_REC[q_ord[qi]][c] * q_rem[qi]) return false;
    }}
    return true;
}}

int tree_action() {{
    int n = 0;
    while (TREE_F[n] >= 0) {{ if (feat[TREE_F[n]] <= TREE_T[n]) n = TREE_L[n]; else n = TREE_R[n]; }}
    return TREE_A[n];
}}

void observe() {{
    // the planner-observable state at the start of the notice day (model/ai/episodes.py, Observer)
    int c; int d; int i; double rate; double onord; double cv; double mc = 60.0; bool found = false;
    double dem[NDC]; double dtot = 0.0; double dcl; double qf = 0.0; double qo = 0.0; double dct = 0.0; double lsum = 0.0;
    rec_idx = -1;
    for (i = 0; i < N_ORD; i++) {{ if (ORD_PROD[i] == 0 && ORD_DAY[i] <= s_start) rec_idx = i; }}
    if (rec_idx < 0) {{ for (i = N_ORD - 1; i >= 0; i--) {{ if (ORD_PROD[i] == 0) rec_idx = i; }} }}
    for (i = 0; i < 5; i++) feat[i] = (d_type == i + 1) ? 1.0 : 0.0;
    feat[5] = n_e1; feat[6] = n_e2; feat[7] = n_e2all; feat[8] = n_e3; feat[9] = n_e4; feat[10] = n_e5;
    for (c = 0; c < NC; c++) {{
        rate = mean_hist_c(c, s_start - 1, 20);
        if (rate < 0.0) rate = 0.0;
        onord = open_qty(c);
        feat[11 + c] = rate > 0.0 ? dmin((comp[c] + onord) / rate, 60.0) : 60.0;
        if (ORD_REC[rec_idx][c] > 0.0) {{
            cv = rate > 0.0 ? dmin(comp[c] / dmax(rate, 0.000000001), 60.0) : 60.0;
            if (!found || cv < mc) mc = cv;
            found = true;
        }}
    }}
    feat[19] = found ? mc : 60.0;
    for (d = 0; d < NDC; d++) {{
        dem[d] = mean_hist_d(d, s_start - 1, 20);
        if (dem[d] < 0.0) dem[d] = 0.0;
        dtot += dem[d];
    }}
    dcl = dmax(dtot, 1.0);
    for (i = qhead; i < qtail; i++) {{ if (q_prod[i] == 0) qf += q_rem[i]; else qo += q_rem[i]; }}
    feat[20] = qf / dcl;
    feat[21] = qo / CAP;
    feat[22] = qtail - qhead;
    feat[23] = (qhead < qtail && !q_started[qhead] && !can_start(qhead)) ? 1.0 : 0.0;
    feat[24] = (qhead < qtail && q_prod[qhead] == 0) ? 1.0 : 0.0;
    feat[25] = changeover_left / CAP;
    feat[26] = plant / dcl;
    for (d = 0; d < NDC; d++) {{
        feat[27 + d] = dem[d] > 0.0 ? dmin(dc[d] / dem[d], 60.0) : 60.0;
        dct += dc[d];
    }}
    feat[30] = dmin(feat[27], dmin(feat[28], feat[29]));
    feat[31] = dmin((dct + plant + qf) / dmax(dtot, 1.0), 120.0);
    for (d = s_start - 20; d < s_start; d++) {{ if (d >= FIRST - 1) lsum += lost_hist[d]; }}
    feat[32] = lsum / dcl;
    feat[33] = (owed[0] + owed[1] + owed[2]) / dcl;
    dem_s = dcl;
    if (CTRL_MODE == 1) action = ACT_FIXED;
    if (CTRL_MODE == 2) action = tree_action();
}}

void arrivals() {{
    int d;
    for (d = 0; d < NDC; d++) {{ dc[d] += intransit[d][day]; intransit[d][day] = 0.0; }}
}}

void receipts() {{
    int i; double blocked; double rest; int m; int n = n_po;
    for (i = 0; i < n; i++) {{
        if (po_open[i] && po_due[i] <= day) {{
            po_open[i] = false; m = po_mat[i];
            if (en_q && !po_qdone[i] && q_mat[m] && day >= q_s && day <= q_e) {{
                blocked = po_qty[i] * q_block;
                rest = po_qty[i] - blocked;
                if (blocked > 0.0) new_po(m, blocked, -1, true);          // rule R5 replacement
                if (q_extra > 0) new_po(m, rest, q_extra, true);
                else comp[m] += rest;
            }} else {{
                comp[m] += po_qty[i];
            }}
        }}
    }}
}}

void produce() {{
    double cap = CAP; double used; double q; int qi; int c;
    if (en_ld && day >= ld_s && day <= ld_e) return;
    used = changeover_left < cap ? changeover_left : cap;
    changeover_left -= used; cap -= used;
    while (qhead < qtail && cap > 0.0) {{
        qi = qhead;
        if (!q_started[qi]) {{
            if (!can_start(qi)) return;                               // waits for its full batch
            if (last_prod != -1 && q_prod[qi] != last_prod) {{
                last_prod = q_prod[qi];
                changeover_left = CHANGEOVER;
                used = changeover_left < cap ? changeover_left : cap;
                changeover_left -= used; cap -= used;
                if (cap <= 0.0) return;
            }}
            q_started[qi] = true;
        }}
        q = q_rem[qi] < cap ? q_rem[qi] : cap;
        for (c = 0; c < NC; c++) comp[c] -= ORD_REC[q_ord[qi]][c] * q;
        q_rem[qi] -= q; cap -= q; last_prod = q_prod[qi];
        if (q_prod[qi] == 0) {{ plant += q; produced_f12 += q; }}
        else other_stock[q_prod[qi]] += q;
        if (q_rem[qi] <= 0.0) qhead++;
    }}
}}

void to_dc(int d, double q) {{
    if (en_tr && day >= tr_s && day <= tr_e) intransit[d][day + tr_k] += q;
    else dc[d] += q;
}}

void water_fill(double amount) {{
    // split `amount` over the DCs, raising the lowest days of cover first (controllers.py, water_fill)
    double lo = 0.0; double hi; double mid; double need; double a[NDC]; double tot; int it; int d;
    hi = (levels[0] + levels[1] + levels[2] + amount) / dmin(rates[0], dmin(rates[1], rates[2])) + 1;
    for (it = 0; it < 60; it++) {{
        mid = (lo + hi) / 2;
        need = 0.0;
        for (d = 0; d < NDC; d++) need += dmax(0.0, mid * rates[d] - levels[d]);
        if (need < amount) lo = mid; else hi = mid;
    }}
    tot = 0.0;
    for (d = 0; d < NDC; d++) {{ a[d] = dmax(0.0, lo * rates[d] - levels[d]); tot += a[d]; }}
    for (d = 0; d < NDC; d++) pplan[d] += tot > 0.0 ? amount * a[d] / tot : 0.0;
}}

void push() {{
    // recorded transfers, deferred (Amendment 3): what cannot ship for lack of plant stock stays owed;
    // lever 3 (ship): plant stock left after them is split over the DCs by days of cover
    double sent = 0.0; double q; double left; double r; int d;
    while (next_tr < N_TR && TR_DAY[next_tr] < day) next_tr++;
    while (next_tr < N_TR && TR_DAY[next_tr] == day) {{ owed[TR_DC[next_tr]] += TR_QTY[next_tr]; next_tr++; }}
    left = plant;
    for (d = 0; d < NDC; d++) {{
        q = owed[d] < left ? owed[d] : left;
        pplan[d] = 0.0;
        if (q > 0.0) {{ pplan[d] = q; left -= q; }}
    }}
    if (ACT_SHIP[action] && day >= s_start && day < s_start + RESP_WINDOW) {{
        left = plant - (pplan[0] + pplan[1] + pplan[2]);
        if (left > 0.0) {{
            for (d = 0; d < NDC; d++) {{
                r = mean_hist_d(d, day - 1, 20);
                rates[d] = r < 0.0 ? 1.0 : dmax(r, 1.0);
                levels[d] = dc[d] + pplan[d];
            }}
            water_fill(left);
        }}
    }}
    for (d = 0; d < NDC; d++) {{
        q = dmax(0.0, dmin(pplan[d], plant - sent));
        if (q > 0.0) {{ to_dc(d, q); sent += q; owed[d] -= dmin(owed[d], q); }}
    }}
    plant -= sent;
}}

void sales() {{
    int d; double dem; double s;
    sold_day = 0.0; lost_day = 0.0;
    for (d = 0; d < NDC; d++) {{
        dem = DEMAND[d][day] * 1.0;
        if (en_dm && day >= dm_s && day <= dm_e) dem = dem * dm_f;
        s = dem < dc[d] ? dem : dc[d];
        dc[d] -= s; sold_day += s; lost_day += dem - s;
        dem_hist[d][day] = s + (dem - s);
    }}
    sold_total += sold_day; lost_total += lost_day;
    lost_hist[day] = lost_day;
}}

void other_sales() {{
    int i; int p; double q; double s;
    lost_other_day = 0.0;
    for (i = 0; i < NPLAN; i++) {{
        p = PLAN[i];
        q = OSALES[p][day];
        s = q < other_stock[p] ? q : other_stock[p];
        other_stock[p] -= s;
        lost_other_day += q - s;
    }}
}}

void release_held() {{
    int i;
    for (i = n_out - 1; i >= 0; i--) out_o[i + n_held] = out_o[i];
    for (i = 0; i < n_held; i++) out_o[i] = held[i];
    n_out += n_held; n_held = 0;
}}

void decide() {{
    int d; int i; int k; int c; int o; bool waiting; bool out = false; double target; double position; double rec;
    // production-order conversions: recorded, then the priority lever, then the extra batch
    n_out = 0;
    while (next_ord < N_ORD && ORD_DAY[next_ord] == day) {{ out_o[n_out] = next_ord; n_out++; next_ord++; }}
    if (ACT_PRIO[action] > 0) {{
        if (day >= s_start && day < s_start + ACT_PRIO[action]) {{
            k = 0;
            for (i = 0; i < n_out; i++) {{
                if (ORD_PROD[out_o[i]] != 0) {{ held[n_held] = out_o[i]; n_held++; }}
                else {{ out_o[k] = out_o[i]; k++; }}
            }}
            n_out = k;
            waiting = n_out > 0;
            for (i = qhead; i < qtail; i++) {{ if (q_prod[i] == 0) waiting = true; }}
            if (!waiting) release_held();
        }} else if (n_held > 0) release_held();
    }}
    if (ACT_FG[action] > 0.0 && day == s_start) {{ out_o[n_out] = -1; n_out++; }}
    for (i = 0; i < n_out; i++) {{
        o = out_o[i];
        q_ord[qtail] = o < 0 ? rec_idx : o;
        q_prod[qtail] = o < 0 ? 0 : ORD_PROD[o];
        q_rem[qtail] = o < 0 ? ACT_FG[action] : ORD_QTY[o];
        q_started[qtail] = false;
        qtail++;
    }}
    // purchase orders: recorded, then the extra batch's components, then the component buffer lever
    while (next_po < N_REC_PO && RPO_DAY[next_po] == day) {{
        if (RPO_PRE[next_po]) new_po(RPO_MAT[next_po], RPO_QTY[next_po], 1, false);   // opening stock
        else new_po(RPO_MAT[next_po], RPO_QTY[next_po], -1, false);
        next_po++;
    }}
    if (ACT_FG[action] > 0.0 && day == s_start) {{
        for (c = 0; c < NC; c++) {{
            rec = ORD_REC[rec_idx][c];
            if (rec > 0.0) new_po(c, ceil_d(rec * ACT_FG[action] / PO_STEP[c]) * PO_STEP[c], -1, false);
        }}
    }}
    if (ACT_PO[action] > 0 && day >= s_start && day < s_start + RESP_WINDOW) {{
        for (c = 0; c < NC; c++) {{
            target = ACT_PO[action] * mean_hist_c(c, day, 20);
            position = comp[c] + open_qty(c);
            if (target > position) new_po(c, ceil_d((target - position) / PO_STEP[c]) * PO_STEP[c], -1, false);
        }}
    }}
    for (d = 0; d < NDC; d++) {{ if (dc[d] <= 0.0) out = true; }}
    if (out) stockout_days++;
}}

void step() {{
    int c;
    if (!initialised) {{ init_scen(); initialised = true; }}
    if (day == s_start) observe();
    arrivals();
    receipts();
    for (c = 0; c < NC; c++) before[c] = comp[c];
    produce();
    for (c = 0; c < NC; c++) cons_hist[c][day] = before[c] - comp[c];
    push();
    sales();
    other_sales();
    if (day >= s_start && day <= s_start + WIN - 1) lost_win += lost_day + lost_other_day;
    if (day == s_start + WIN - 1) {{ win_done = true; win_ok = lost_win / dem_s <= L_STAR + 0.000000001; }}
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
         "Cross-check trace: run on a deterministic file (LEAD_MODE = 1, SCEN_MODE 0 or 1) and compare with crosscheck.py"),
        (f"Pr[<={horizon}] (<> win_done && win_ok)",
         "SCEN_MODE 2: probability that the 60-day loss (all products) stays within L_STAR days of demand (L4 service property)"),
        (f"E[<={horizon}; 1000] (max: lost_win / dem_s)", "SCEN_MODE 2: expected 60-day loss in days of demand"),
        (f"E[<={horizon}; 200] (max: lost_total)", "Expected F12 lost demand over the year"),
        (f"E[<={horizon}; 200] (max: stockout_days)", "Expected number of days with a DC stock-out"),
    ]
    q_xml = "".join(f"<query><formula>{escape(f)}</formula><comment>{escape(c)}</comment></query>" for f, c in queries)
    xml = ('<?xml version="1.0" encoding="utf-8"?>\n'
           '<!DOCTYPE nta PUBLIC \'-//Uppaal Team//DTD Flat System 1.6//EN\' \'http://www.it.uu.se/research/group/darts/uppaal/flat-1_6.dtd\'>\n'
           f"<nta><declaration>{escape(decl)}</declaration>{template}"
           "<system>D = Day();\nsystem D;</system>"
           f"<queries>{q_xml}</queries></nta>\n")
    return xml


def parse_fix(s):
    """E3,120,10 -> type 3 on day 120 with severity 10 (E1 relative delay, E2 share[:material or all], E3 days,
    E4 factor, E5 days)."""
    t, start, sev = s.split(",")
    f = {"type": TYPES.index(t) + 1, "start": int(start), "e1_rel": 0.75, "e2_share": 0.041, "e2_mat": -1,
         "e3_days": 10, "e4_factor": 1.19, "e5_days": 4}
    if t == "E1":
        f["e1_rel"] = float(sev)
    elif t == "E2":
        share, _, mat = sev.partition(":")
        f["e2_share"] = float(share)
        f["e2_mat"] = int(mat) if mat else -1
    elif t == "E3":
        f["e3_days"] = int(sev)
    elif t == "E4":
        f["e4_factor"] = float(sev)
    else:
        f["e5_days"] = int(sev)
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs")
    ap.add_argument("--out")
    ap.add_argument("--crosscheck", action="store_true", help="LEAD_MODE = 1 (deterministic, for crosscheck.py)")
    ap.add_argument("--ai", action="store_true", help="write the certification models V12_<run>_ai_tree.xml and _ai_players.xml")
    ap.add_argument("--lead-mode", type=int, default=0)
    ap.add_argument("--scen-mode", type=int, default=0)
    ap.add_argument("--ctrl-mode", type=int, default=0)
    ap.add_argument("--act", type=int, default=0)
    ap.add_argument("--fix", help="SCEN_MODE 1 disruption, e.g. E3,120,10 or E2,110,0.041:4")
    ap.add_argument("--tree", help="tree JSON (default: model/ai/results/tree_<run>[_adapted].json)")
    a = ap.parse_args()
    inp = json.load(open(a.inputs))
    tree = json.load(open(a.tree)) if a.tree else None
    run = inp["run"]
    if a.ai:
        for ctrl, name in [(2, "tree"), (0, "players")]:
            out = os.path.join(HERE, f"V12_{run}_ai_{name}.xml")
            with open(out, "w") as fh:
                fh.write(build(inp, 0, 2, ctrl, tree=tree))
            print(f"wrote {out}")
        return
    lead = 1 if a.crosscheck else a.lead_mode
    out = a.out or os.path.join(HERE, f"V12_{run}{'_crosscheck' if a.crosscheck else ''}.xml")
    with open(out, "w") as fh:
        fh.write(build(inp, lead, a.scen_mode, a.ctrl_mode, a.act, parse_fix(a.fix) if a.fix else None, tree))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
