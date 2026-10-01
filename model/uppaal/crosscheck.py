"""Cross-check of the UPPAAL V12 model against the Python twin (deterministic mode: every lead time at its median).

Reference: the Python twin (model/twin/twin.py) with the players' recorded decisions (transfers deferred,
Amendment 3), the response levers of model/twin/controllers.py (ResponseController), the AI-episode observer
(model/ai/episodes.py, Observer) and lead_mode="median". Scenario, controller mode, fixed action and tree are read
from the XML, so every configuration the XML can express is checked against the same reference.

  mirror    Executes the generated XML itself in Python: every constant (data arrays, switches, actions, tree) is
            parsed from the XML's declaration and the day step is a line-by-line transcription of its UPPAAL
            functions. Checks the data export, the levers, the 34 features and the tree. Runs without UPPAAL.
  suite     The mirror over a battery of configurations (all disruption types x all actions x the tree, several
            notice days, all switches), for one input file.
  expected  Writes the twin's expected trace (CSV) for comparison by hand.
  smc       Stochastic mirror of a SCEN_MODE 2 model: estimates Pr(win_done && win_ok) in Python with the XML's
            own random semantics; verifyta's query 2 on the same XML should agree within sampling error.
  compare   Parses the output of `verifyta -q -s <deterministic XML>` (query 1, `simulate`) and compares it with the
            twin day by day. This is the check that proves the UPPAAL model itself.

Usage:
    python crosscheck.py mirror   V12_normal_2_crosscheck.xml ../twin/inputs/normal_2.json
    python crosscheck.py suite    ../twin/inputs/normal_2.json
    python crosscheck.py expected V12_normal_2_crosscheck.xml ../twin/inputs/normal_2.json [--out expected.csv]
    python crosscheck.py compare  V12_normal_2_crosscheck.xml ../twin/inputs/normal_2.json verifyta_output.txt
    python crosscheck.py smc      V12_normal_2_ai_tree.xml [--runs 1000]

Time mapping: the automaton's first step fires at t = 1 and executes day FIRST - 1, so the state at time t is the
twin's end-of-day state of day FIRST - 2 + t.
"""
import argparse
import json
import math
import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "twin"))
sys.path.insert(0, os.path.join(HERE, "..", "ai"))
from controllers import ResponseController  # noqa: E402
from episodes import Observer  # noqa: E402
from generate_uppaal import FEATURES, TYPES, build, start_days  # noqa: E402
from twin import DCS, Twin  # noqa: E402

REL_TOL = 1e-6      # doubles; verifyta may print fewer digits, hence the absolute tolerance below
ABS_TOL = 0.5
FOOD_NAMES = ["AA-R01", "AA-R02", "AA-R03", "AA-R04", "AA-R05", "AA-R06"]


# ---------------------------------------------------------------- XML constants
def constants(xml_path):
    decl = ET.parse(xml_path).getroot().find("declaration").text
    decl = re.sub(r"//[^\n]*", "", decl)
    env = {}
    for typ, name, value in re.findall(r"const\s+(int|double|bool)\s+(\w+)(?:\[[^=]*\])?\s*=\s*([^;]*);", decl):
        v = value.strip().replace("{", "[").replace("}", "]").replace("true", "True").replace("false", "False")
        env[name] = eval(v, {}, dict(env))      # values are literals or expressions of earlier constants
    return env


def levers(k, a):
    return dict(po_days=k["ACT_PO"][a], fg_units=k["ACT_FG"][a], ship=k["ACT_SHIP"][a], prio=k["ACT_PRIO"][a])


def tree_action(k, x):
    n = 0
    while k["TREE_F"][n] >= 0:
        n = k["TREE_L"][n] if x[k["TREE_F"][n]] <= k["TREE_T"][n] else k["TREE_R"][n]
    return k["TREE_A"][n]


# ---------------------------------------------------------------- reference: the Python twin
def scenario_from(k, comps):
    """The disruption and the notice, as the twin and the AI episodes define them."""
    if k["SCEN_MODE"] == 0:
        sc = {}
        if k["EN_SUPPLIER_DELAY"]:
            sc["supplier_delay"] = {"window": [k["SD_START"], k["SD_END"]], "relative": k["SD_REL100"] / 100}
        if k["EN_QUALITY"]:
            sc["quality"] = {"window": [k["Q_START"], k["Q_END"]], "block_share": k["Q_BLOCK"],
                             "extra_delay": k["Q_EXTRA"], "materials": [c for c, f in zip(comps, k["Q_MAT"]) if f]}
        if k["EN_LINE_DOWN"]:
            sc["line_down"] = [[k["LD_START"], k["LD_END"]]]
        if k["EN_DEMAND"]:
            sc["demand"] = {"window": [k["DS_START"], k["DS_END"]], "factor": k["DF"]}
        if k["EN_TRANSIT"]:
            sc["transit"] = {"window": [k["T_START"], k["T_END"]], "days": k["T_DAYS"]}
        return sc, k["RESP_START"], {"type": None}
    if k["SCEN_MODE"] != 1:
        raise SystemExit("only SCEN_MODE 0 and 1 are deterministic")
    t, s = TYPES[k["FIX_TYPE"] - 1], k["FIX_START"]
    w = [s, s + 19]
    note = {"type": t, "e1_rel": 0.0, "e2_share": 0.0, "e2_allfood": 0, "e3_days": 0, "e4_factor": 1.0, "e5_days": 0}
    if t == "E1":
        note["e1_rel"] = k["FIX_E1_REL"]
        sc = {"supplier_delay": {"window": w, "relative": k["FIX_E1_REL"]}}
    elif t == "E2":
        note["e2_share"], note["e2_allfood"] = k["FIX_E2_SHARE"], int(k["FIX_E2_MAT"] < 0)
        mats = FOOD_NAMES if k["FIX_E2_MAT"] < 0 else [comps[k["FIX_E2_MAT"]]]
        sc = {"quality": {"window": w, "block_share": k["FIX_E2_SHARE"], "extra_delay": 2, "materials": mats}}
    elif t == "E3":
        note["e3_days"] = k["FIX_E3_DAYS"]
        sc = {"line_down": [[s, s + k["FIX_E3_DAYS"] - 1]]}
    elif t == "E4":
        note["e4_factor"] = k["FIX_E4_FACTOR"]
        sc = {"demand": {"window": w, "factor": k["FIX_E4_FACTOR"]}}
    else:
        note["e5_days"] = k["FIX_E5_DAYS"]
        sc = {"transit": {"window": w, "days": k["FIX_E5_DAYS"]}}
    return sc, s, note


def feature_vector(x, note):
    """The 34 features, as model/ai/common.py derives them from the observer's record."""
    dem = max(x["demand_20d"], 1.0)
    v = {f"type_{t}": float(note["type"] == t) for t in TYPES}
    v.update({k_: float(note.get(k_, 0.0)) if note["type"] else (1.0 if k_ == "e4_factor" else 0.0)
              for k_ in ["e1_rel", "e2_share", "e2_allfood", "e3_days", "e4_factor", "e5_days"]})
    v.update({k_: x[k_] for k_ in x if k_.startswith("cover_")})
    v.update({"min_cover_f12_components": x["min_cover_f12_components"], "queue_f12_days": x["queue_f12_units"] / dem,
              "queue_other_line_days": x["queue_other_units"] / 24000.0, "queue_orders": x["queue_orders"],
              "head_blocked": x["head_blocked"], "head_is_f12": x["head_is_f12"],
              "changeover_line_days": x["changeover_left"] / 24000.0, "plant_days": x["plant"] / dem,
              "dc_min_cover": x["dc_min_cover"], "fg_cover": x["fg_cover"], "lost_20d_days": x["lost_20d"] / dem,
              "backlog_days": x["transfer_backlog"] / dem})
    v.update({f"dc_cover_{d}": x[f"dc_cover_{d}"] for d in DCS})
    return np.array([v[f] for f in FEATURES], dtype=float)


def twin_run(inp, sc, s, action, k):
    ctl = ResponseController(inp, s, **levers(k, action))
    obs = Observer(s)
    df = Twin(inp, seed=0, demand_mode="replay", policy="controller", controller=ctl, scenario=sc,
              lead_mode="median", observer=obs).run()
    return df, obs.x


def twin_trace(inp, k):
    """Reference trace, plus the features and the action the twin's side computes."""
    sc, s, note = scenario_from(k, inp["components"])
    feats = None
    action = 0
    if k["CTRL_MODE"] == 1:
        action = k["ACT_FIXED"]
    if k["CTRL_MODE"] == 2 or note["type"]:
        _, x = twin_run(inp, sc, s, 0, k)
        if x is not None:
            feats = feature_vector(x, note)
            if k["CTRL_MODE"] == 2:
                action = tree_action(k, feats)
    df, _ = twin_run(inp, sc, s, action, k)
    out = pd.DataFrame({"day": df.day, "sold_day": df.sales, "lost_day": df.lost, "lost_total": df.lost.cumsum(),
                        "stockout_days": df[[f"dc_{d}" for d in DCS]].le(0).any(axis=1).cumsum()})
    for i, d in enumerate(DCS):
        out[f"dc[{i}]"] = df[f"dc_{d}"]
    out["plant"] = df.plant_stock
    out["produced_f12"] = df.production_f12.cumsum()
    out["lost_other_day"] = df.lost_other
    inwin = (df.day >= s) & (df.day <= s + k["WIN"] - 1)
    out["lost_win"] = ((df.lost + df.lost_other) * inwin).cumsum()
    out["action"] = np.where(df.day >= s, action, 0)
    for i, c in enumerate(inp["components"]):
        out[f"comp[{i}]"] = df[f"stock_{c}"]
    return out.reset_index(drop=True), feats, action


# ---------------------------------------------------------------- mirror: the XML's functions in Python
class Mirror:
    """Line-by-line transcription of the UPPAAL functions in generate_uppaal.py (deterministic lead mode)."""

    def __init__(self, k, rng=None):
        self.k = k
        self.rng = rng                  # for LEAD_MODE 0 / SCEN_MODE 2 (stochastic mirror, `smc` mode)
        nc, ndc, nday = k["NC"], k["NDC"], k["NDAY"]
        self.day = k["FIRST"] - 1
        self.initialised = False
        self.comp = [0.0] * nc
        self.plant = 0.0
        self.dc = [0.0] * ndc
        self.intransit = [[0.0] * nday for _ in range(ndc)]
        self.owed = [0.0] * ndc
        self.other_stock = [0.0] * k["NPROD"]
        self.po = []                    # [qty, due, mat, open, qdone]
        self.queue = []                 # [ord_index (recipe), prod, remaining, started]
        self.qhead = 0
        self.held = []
        self.next_ord = self.next_po = self.next_tr = 0
        self.last_prod = -1
        self.changeover_left = 0.0
        self.cons_hist = [[0.0] * nday for _ in range(nc)]
        self.dem_hist = [[0.0] * nday for _ in range(ndc)]
        self.lost_hist = [0.0] * nday
        self.action, self.rec_idx, self.feat = 0, 0, None
        self.sold_total = self.lost_total = self.sold_day = self.lost_day = self.produced_f12 = 0.0
        self.lost_other_day = self.lost_win = 0.0
        self.dem_s = 1.0
        self.win_done = self.win_ok = False
        self.stockout_days = 0
        self.en_sd = self.en_q = self.en_ld = self.en_dm = self.en_tr = False
        self.q_mat = [False] * nc
        self.s_start, self.d_type = -100, 0
        self.n = {"e1": 0.0, "e2": 0.0, "e2all": 0.0, "e3": 0.0, "e4": 1.0, "e5": 0.0}

    # -- scenario
    def init_scen(self):
        k = self.k
        if k["SCEN_MODE"] == 0:
            self.en_sd, self.sd_s, self.sd_e, self.sd_rel = k["EN_SUPPLIER_DELAY"], k["SD_START"], k["SD_END"], k["SD_REL100"] / 100.0
            self.en_q, self.q_s, self.q_e, self.q_block, self.q_extra = k["EN_QUALITY"], k["Q_START"], k["Q_END"], k["Q_BLOCK"], k["Q_EXTRA"]
            self.q_mat = list(k["Q_MAT"])
            self.en_ld, self.ld_s, self.ld_e = k["EN_LINE_DOWN"], k["LD_START"], k["LD_END"]
            self.en_dm, self.dm_s, self.dm_e, self.dm_f = k["EN_DEMAND"], k["DS_START"], k["DS_END"], k["DF"]
            self.en_tr, self.tr_s, self.tr_e, self.tr_k = k["EN_TRANSIT"], k["T_START"], k["T_END"], k["T_DAYS"]
            self.s_start = k["RESP_START"]
            return
        n = self.n
        if k["SCEN_MODE"] == 1:
            t, s, m = k["FIX_TYPE"], k["FIX_START"], k["FIX_E2_MAT"]
            n.update(e1=k["FIX_E1_REL"], e2=k["FIX_E2_SHARE"], e2all=1.0 if m < 0 else 0.0, e3=float(k["FIX_E3_DAYS"]),
                     e4=k["FIX_E4_FACTOR"], e5=float(k["FIX_E5_DAYS"]))
        else:                                       # SCEN_MODE 2, as init_scen() samples it
            r = self.rng.random
            t = min(1 + int(r() * 5.0), 5)
            s = k["START_DAYS"][min(int(r() * k["NS"]), k["NS"] - 1)]
            u = r() * 0.95
            for i in range(4):
                if k["USAID_U"][i] <= u <= k["USAID_U"][i + 1]:
                    n["e1"] = k["USAID_R"][i] + (u - k["USAID_U"][i]) * (k["USAID_R"][i + 1] - k["USAID_R"][i]) / (k["USAID_U"][i + 1] - k["USAID_U"][i])
            n["e2"] = 0.002 + r() * 0.039
            n["e2all"] = 1.0 if r() < 0.5 else 0.0
            m = -1 if n["e2all"] > 0.5 else k["FOOD"][min(int(r() * k["NFOOD"]), k["NFOOD"] - 1)]
            n["e3"] = float(min(1 + int(r() * 25.0), 25))
            n["e4"] = 1.05 + r() * 0.14
            n["e5"] = float(min(1 + int(r() * 4.0), 4))
        self.s_start, self.d_type = s, t
        if t != 1:
            n["e1"] = 0.0
        if t != 2:
            n["e2"], n["e2all"] = 0.0, 0.0
        if t != 3:
            n["e3"] = 0.0
        if t != 4:
            n["e4"] = 1.0
        if t != 5:
            n["e5"] = 0.0
        if t == 1:
            self.en_sd, self.sd_s, self.sd_e, self.sd_rel = True, s, s + 19, n["e1"]
        if t == 2:
            self.en_q, self.q_s, self.q_e, self.q_block, self.q_extra = True, s, s + 19, n["e2"], 2
            if m < 0:
                self.q_mat = list(k["IS_FOOD"])
            else:
                self.q_mat[m] = True
        if t == 3:
            self.en_ld, self.ld_s, self.ld_e = True, s, s + int(n["e3"]) - 1
        if t == 4:
            self.en_dm, self.dm_s, self.dm_e, self.dm_f = True, s, s + 19, n["e4"]
        if t == 5:
            self.en_tr, self.tr_s, self.tr_e, self.tr_k = True, s, s + 19, int(n["e5"])

    # -- helpers
    def lead(self, m):
        k = self.k
        food = k["IS_FOOD"][m]
        if k["LEAD_MODE"] == 1:
            return k["F_MED"] if food else k["P_MED"]
        u = self.rng.random()
        vals, cum = (k["F_VAL"], k["F_CUM"]) if food else (k["P_VAL"], k["P_CUM"])
        for v, c in zip(vals, cum):
            if u < c:
                return v
        return vals[-1]

    def new_po(self, m, q, due_offset, qdone):
        l = due_offset
        if l < 0:
            l = self.lead(m)
            if self.en_sd and self.sd_s <= self.day <= self.sd_e:
                l = l + math.ceil(self.sd_rel * l)
        self.po.append([q, self.day + l, m, True, qdone])
        assert len(self.po) <= self.k["N_PO_MAX"], "N_PO_MAX too small"

    def mean_hist(self, hist, lastday, n):
        vals = [hist[d] for d in range(lastday - n + 1, lastday + 1) if d >= self.k["FIRST"] - 1]
        if not vals:
            return -1.0
        s = 0.0
        for v in vals:
            s += v
        return s / len(vals)

    def open_qty(self, c):
        s = 0.0
        for p in self.po:
            if p[3] and p[2] == c:
                s += p[0]
        return s

    def can_start(self, qi):
        rec = self.k["ORD_REC"][self.queue[qi][0]]
        return all(not (rec[c] > 0.0 and self.comp[c] + 0.000001 < rec[c] * self.queue[qi][2]) for c in range(self.k["NC"]))

    def tree_action(self):
        return tree_action(self.k, self.feat)

    def observe(self):
        k = self.k
        s = self.s_start
        self.rec_idx = -1
        for i in range(k["N_ORD"]):
            if k["ORD_PROD"][i] == 0 and k["ORD_DAY"][i] <= s:
                self.rec_idx = i
        if self.rec_idx < 0:
            self.rec_idx = next(i for i in range(k["N_ORD"]) if k["ORD_PROD"][i] == 0)
        f = [0.0] * k["NFEAT"]
        for i in range(5):
            f[i] = 1.0 if self.d_type == i + 1 else 0.0
        n = self.n
        f[5:11] = [n["e1"], n["e2"], n["e2all"], n["e3"], n["e4"], n["e5"]]
        mc, found = 60.0, False
        for c in range(k["NC"]):
            rate = max(self.mean_hist(self.cons_hist[c], s - 1, 20), 0.0)
            onord = self.open_qty(c)
            f[11 + c] = min((self.comp[c] + onord) / rate, 60.0) if rate > 0.0 else 60.0
            if k["ORD_REC"][self.rec_idx][c] > 0.0:
                cv = min(self.comp[c] / max(rate, 0.000000001), 60.0) if rate > 0.0 else 60.0
                if not found or cv < mc:
                    mc = cv
                found = True
        f[19] = mc if found else 60.0
        dem = [max(self.mean_hist(self.dem_hist[d], s - 1, 20), 0.0) for d in range(k["NDC"])]
        dtot = 0.0
        for d in range(k["NDC"]):
            dtot += dem[d]
        dcl = max(dtot, 1.0)
        qf = qo = 0.0
        for e in self.queue[self.qhead:]:
            if e[1] == 0:
                qf += e[2]
            else:
                qo += e[2]
        f[20], f[21] = qf / dcl, qo / k["CAP"]
        f[22] = float(len(self.queue) - self.qhead)
        has = self.qhead < len(self.queue)
        f[23] = 1.0 if has and not self.queue[self.qhead][3] and not self.can_start(self.qhead) else 0.0
        f[24] = 1.0 if has and self.queue[self.qhead][1] == 0 else 0.0
        f[25], f[26] = self.changeover_left / k["CAP"], self.plant / dcl
        dct = 0.0
        for d in range(k["NDC"]):
            f[27 + d] = min(self.dc[d] / dem[d], 60.0) if dem[d] > 0.0 else 60.0
            dct += self.dc[d]
        f[30] = min(f[27], min(f[28], f[29]))
        f[31] = min((dct + self.plant + qf) / max(dtot, 1.0), 120.0)
        lsum = 0.0
        for d in range(s - 20, s):
            if d >= k["FIRST"] - 1:
                lsum += self.lost_hist[d]
        f[32] = lsum / dcl
        f[33] = (self.owed[0] + self.owed[1] + self.owed[2]) / dcl
        self.feat, self.dem_s = f, dcl
        if k["CTRL_MODE"] == 1:
            self.action = k["ACT_FIXED"]
        if k["CTRL_MODE"] == 2:
            self.action = self.tree_action()

    # -- day steps
    def arrivals(self):
        for d in range(self.k["NDC"]):
            self.dc[d] += self.intransit[d][self.day]
            self.intransit[d][self.day] = 0.0

    def receipts(self):
        for i in range(len(self.po)):
            p = self.po[i]
            if p[3] and p[1] <= self.day:
                p[3] = False
                m = p[2]
                if self.en_q and not p[4] and self.q_mat[m] and self.q_s <= self.day <= self.q_e:
                    blocked = p[0] * self.q_block
                    rest = p[0] - blocked
                    if blocked > 0.0:
                        self.new_po(m, blocked, -1, True)
                    if self.q_extra > 0:
                        self.new_po(m, rest, self.q_extra, True)
                    else:
                        self.comp[m] += rest
                else:
                    self.comp[m] += p[0]

    def produce(self):
        k = self.k
        cap = float(k["CAP"])
        if self.en_ld and self.ld_s <= self.day <= self.ld_e:
            return
        used = min(self.changeover_left, cap)
        self.changeover_left -= used
        cap -= used
        while self.qhead < len(self.queue) and cap > 0.0:
            e = self.queue[self.qhead]
            if not e[3]:
                if not self.can_start(self.qhead):
                    return
                if self.last_prod != -1 and e[1] != self.last_prod:
                    self.last_prod = e[1]
                    self.changeover_left = k["CHANGEOVER"]
                    used = min(self.changeover_left, cap)
                    self.changeover_left -= used
                    cap -= used
                    if cap <= 0.0:
                        return
                e[3] = True
            q = min(e[2], cap)
            for c in range(k["NC"]):
                self.comp[c] -= k["ORD_REC"][e[0]][c] * q
            e[2] -= q
            cap -= q
            self.last_prod = e[1]
            if e[1] == 0:
                self.plant += q
                self.produced_f12 += q
            else:
                self.other_stock[e[1]] += q
            if e[2] <= 0.0:
                self.qhead += 1

    def to_dc(self, d, q):
        if self.en_tr and self.tr_s <= self.day <= self.tr_e:
            self.intransit[d][self.day + self.tr_k] += q
        else:
            self.dc[d] += q

    def water_fill(self, amount, levels, rates, pplan):
        lo, hi = 0.0, (levels[0] + levels[1] + levels[2] + amount) / min(rates[0], min(rates[1], rates[2])) + 1
        for _ in range(60):
            mid = (lo + hi) / 2
            need = 0.0
            for d in range(3):
                need += max(0.0, mid * rates[d] - levels[d])
            if need < amount:
                lo = mid
            else:
                hi = mid
        a = [max(0.0, lo * rates[d] - levels[d]) for d in range(3)]
        tot = 0.0
        for d in range(3):
            tot += a[d]
        for d in range(3):
            pplan[d] += amount * a[d] / tot if tot > 0.0 else 0.0

    def push(self):
        k = self.k
        sent = 0.0
        while self.next_tr < k["N_TR"] and k["TR_DAY"][self.next_tr] < self.day:
            self.next_tr += 1
        while self.next_tr < k["N_TR"] and k["TR_DAY"][self.next_tr] == self.day:
            self.owed[k["TR_DC"][self.next_tr]] += k["TR_QTY"][self.next_tr]
            self.next_tr += 1
        left = self.plant
        pplan = [0.0] * 3
        for d in range(3):
            q = min(self.owed[d], left)
            if q > 0.0:
                pplan[d] = q
                left -= q
        if k["ACT_SHIP"][self.action] and self.s_start <= self.day < self.s_start + k["RESP_WINDOW"]:
            left = self.plant - (pplan[0] + pplan[1] + pplan[2])
            if left > 0.0:
                rates, levels = [0.0] * 3, [0.0] * 3
                for d in range(3):
                    r = self.mean_hist(self.dem_hist[d], self.day - 1, 20)
                    rates[d] = 1.0 if r < 0.0 else max(r, 1.0)
                    levels[d] = self.dc[d] + pplan[d]
                self.water_fill(left, levels, rates, pplan)
        for d in range(3):
            q = max(0.0, min(pplan[d], self.plant - sent))
            if q > 0.0:
                self.to_dc(d, q)
                sent += q
                self.owed[d] -= min(self.owed[d], q)
        self.plant -= sent

    def sales(self):
        k = self.k
        self.sold_day = self.lost_day = 0.0
        for d in range(k["NDC"]):
            dem = k["DEMAND"][d][self.day] * 1.0
            if self.en_dm and self.dm_s <= self.day <= self.dm_e:
                dem = dem * self.dm_f
            s = min(dem, self.dc[d])
            self.dc[d] -= s
            self.sold_day += s
            self.lost_day += dem - s
            self.dem_hist[d][self.day] = s + (dem - s)
        self.sold_total += self.sold_day
        self.lost_total += self.lost_day
        self.lost_hist[self.day] = self.lost_day

    def other_sales(self):
        k = self.k
        self.lost_other_day = 0.0
        for p in k["PLAN"]:
            q = k["OSALES"][p][self.day]
            s = min(q, self.other_stock[p])
            self.other_stock[p] -= s
            self.lost_other_day += q - s

    def decide(self):
        k = self.k
        a = self.action
        out = []
        while self.next_ord < k["N_ORD"] and k["ORD_DAY"][self.next_ord] == self.day:
            out.append(self.next_ord)
            self.next_ord += 1
        if k["ACT_PRIO"][a] > 0:
            if self.s_start <= self.day < self.s_start + k["ACT_PRIO"][a]:
                self.held += [o for o in out if k["ORD_PROD"][o] != 0]
                out = [o for o in out if k["ORD_PROD"][o] == 0]
                waiting = len(out) > 0 or any(e[1] == 0 for e in self.queue[self.qhead:])
                if not waiting:
                    out, self.held = self.held + out, []
            elif self.held:
                out, self.held = self.held + out, []
        if k["ACT_FG"][a] > 0.0 and self.day == self.s_start:
            out.append(-1)
        for o in out:
            if o < 0:
                self.queue.append([self.rec_idx, 0, k["ACT_FG"][a], False])
            else:
                self.queue.append([o, k["ORD_PROD"][o], k["ORD_QTY"][o], False])
        while self.next_po < k["N_REC_PO"] and k["RPO_DAY"][self.next_po] == self.day:
            pre = k["RPO_PRE"][self.next_po]
            self.new_po(k["RPO_MAT"][self.next_po], k["RPO_QTY"][self.next_po], 1 if pre else -1, False)
            self.next_po += 1
        if k["ACT_FG"][a] > 0.0 and self.day == self.s_start:
            for c in range(k["NC"]):
                rec = k["ORD_REC"][self.rec_idx][c]
                if rec > 0.0:
                    self.new_po(c, math.ceil(rec * k["ACT_FG"][a] / k["PO_STEP"][c]) * k["PO_STEP"][c], -1, False)
        if k["ACT_PO"][a] > 0 and self.s_start <= self.day < self.s_start + k["RESP_WINDOW"]:
            for c in range(k["NC"]):
                target = k["ACT_PO"][a] * self.mean_hist(self.cons_hist[c], self.day, 20)
                position = self.comp[c] + self.open_qty(c)
                if target > position:
                    self.new_po(c, math.ceil((target - position) / k["PO_STEP"][c]) * k["PO_STEP"][c], -1, False)
        if any(self.dc[d] <= 0.0 for d in range(k["NDC"])):
            self.stockout_days += 1

    def step(self):
        k = self.k
        if not self.initialised:
            self.init_scen()
            self.initialised = True
        if self.day == self.s_start:
            self.observe()
        self.arrivals()
        self.receipts()
        before = list(self.comp)
        self.produce()
        for c in range(k["NC"]):
            self.cons_hist[c][self.day] = before[c] - self.comp[c]
        self.push()
        self.sales()
        self.other_sales()
        if self.s_start <= self.day <= self.s_start + k["WIN"] - 1:
            self.lost_win += self.lost_day + self.lost_other_day
        if self.day == self.s_start + k["WIN"] - 1:
            self.win_done, self.win_ok = True, self.lost_win / self.dem_s <= k["L_STAR"] + 0.000000001
        self.decide()
        self.day += 1

    def run(self):
        rows = []
        while self.day <= self.k["LAST"]:
            d = self.day
            self.step()
            row = {"day": d, "sold_day": self.sold_day, "lost_day": self.lost_day, "lost_total": self.lost_total,
                   "stockout_days": self.stockout_days, "plant": self.plant, "produced_f12": self.produced_f12,
                   "lost_other_day": self.lost_other_day, "lost_win": self.lost_win, "action": self.action}
            row.update({f"dc[{i}]": v for i, v in enumerate(self.dc)})
            row.update({f"comp[{i}]": v for i, v in enumerate(self.comp)})
            rows.append(row)
        return pd.DataFrame(rows)


# ---------------------------------------------------------------- verifyta output
def parse_verifyta(path, first):
    """Series per expression from the `simulate` output: the value at integer time t is the last point at t."""
    txt = open(path).read()
    series = {}
    for name, pts in re.findall(r"^([^\s\[][^\n]*?):\s*\n\[0\]:([^\n]*)", txt, flags=re.M):
        pairs = [(float(a), float(b)) for a, b in re.findall(r"\(([-\d.eE+]+),\s*([-\d.eE+]+)\)", pts)]
        if not pairs:
            continue
        horizon = int(math.floor(max(t for t, _ in pairs)))
        vals = {}
        for t, v in pairs:                               # points are in time order; later points override
            if abs(t - round(t)) < 1e-9:
                vals[int(round(t))] = v
        series[name.strip()] = {first - 2 + t: vals[t] for t in range(1, horizon + 1) if t in vals}
    if not series:
        raise SystemExit(f"no simulate trace found in {path}")
    return pd.DataFrame(series).rename_axis("day").reset_index()


# ---------------------------------------------------------------- comparison
def compare(ref, got, label, quiet=False):
    cols = [c for c in ref.columns if c != "day" and c in got.columns]
    m = ref.merge(got, on="day", suffixes=("_twin", "_other"))
    worst, bad = [], 0
    for c in cols:
        a, b = m[f"{c}_twin"].astype(float), m[f"{c}_other"].astype(float)
        err = (a - b).abs()
        tol = ABS_TOL + REL_TOL * a.abs()
        n = int((err > tol).sum())
        bad += n
        first_bad = int(m.day[err > tol].iloc[0]) if n else None
        worst.append((c, float(err.max()), n, first_bad))
    ok = bad == 0 and len(m) > 0
    if not quiet or not ok:
        print(f"{label}: {len(m)} days, {len(cols)} expressions")
        for c, e, n, fb in worst:
            print(f"  {c:>14}: max |diff| {e:.3g}" + (f"  -> {n} days out of tolerance, first on day {fb}" if n else ""))
        print("  RESULT:", "MATCH" if ok else "MISMATCH")
    return ok, max(e for _, e, _, _ in worst)


def mirror_check(xml, inp, quiet=False):
    k = constants(xml)
    ref, feats, action = twin_trace(inp, k)
    mir = Mirror(k)
    got = mir.run()
    ok, worst = compare(ref, got, f"mirror of {os.path.basename(xml)} vs twin", quiet)
    fdiff = 0.0
    if feats is not None and mir.feat is not None:
        fdiff = float(np.max(np.abs(np.array(mir.feat) - feats)))
        if fdiff > 1e-6:
            ok = False
            bad = [FEATURES[i] for i in np.where(np.abs(np.array(mir.feat) - feats) > 1e-6)[0]]
            print(f"  features differ (max {fdiff:.3g}): {bad}")
    if mir.action != action:
        ok = False
        print(f"  action differs: mirror {mir.action}, twin {action}")
    return ok, worst, fdiff, action


def biting_days(inp, days):
    """First notice days (E3, 10 days) on which the ship lever and the priority lever change the run, so that
    the suite exercises every lever branch (on many days they have nothing to act on)."""
    from generate_uppaal import parse_fix
    tmp = os.path.join(tempfile.mkdtemp(), "scan.xml")
    found = {}
    for s in days[::3]:
        sig = {}
        for a in (0, 4, 5):
            open(tmp, "w").write(build(inp, 1, 1, 1, a, parse_fix(f"E3,{s},10")))
            df = Mirror(constants(tmp)).run()
            sig[a] = (round(df[["dc[0]", "dc[1]", "dc[2]"]].values.sum()), round(df.lost_other_day.sum()),
                      round(df.lost_win.iloc[-1]))
        for a in (4, 5):
            if a not in found and sig[a] != sig[0]:
                found[a] = s
        if len(found) == 2:
            break
    return sorted(set(found.values()))


def suite(inp_path):
    """The mirror over a battery of configurations: the switches, and every disruption type at several notice
    days (spread over the steady months, plus days on which the ship and priority levers bite) under each of the
    8 fixed actions and the tree."""
    inp = json.load(open(inp_path))
    days = start_days(inp)
    starts = [days[len(days) // 5], days[len(days) // 2], days[4 * len(days) // 5]]
    starts += [d for d in biting_days(inp, days) if d not in starts]
    sev = {"E1": "0.75", "E2": "0.041", "E3": "10", "E4": "1.19", "E5": "4"}
    rows, tmp = [], tempfile.mkdtemp()
    from generate_uppaal import parse_fix
    cases = [("switches: none", dict(scen_mode=0)),
             ("switches: all five", dict(scen_mode=0, all_switches=True))]
    for s in starts:
        for t in TYPES:
            fix = f"{t},{s},{sev[t] if t != 'E2' else '0.041:4'}" if t == "E2" and s == starts[1] else f"{t},{s},{sev[t]}"
            cases.append((f"{fix} tree", dict(scen_mode=1, ctrl_mode=2, fix=fix)))
            for a in range(8):
                cases.append((f"{fix} action {a}", dict(scen_mode=1, ctrl_mode=1, act=a, fix=fix)))
    for name, cfg in cases:
        xml = build(inp, 1, cfg.get("scen_mode", 0), cfg.get("ctrl_mode", 0), cfg.get("act", 0),
                    parse_fix(cfg["fix"]) if "fix" in cfg else None)
        if cfg.get("all_switches"):
            xml = re.sub(r"const bool (EN_\w+) = false", r"const bool \1 = true", xml)
        path = os.path.join(tmp, "case.xml")
        open(path, "w").write(xml)
        ok, worst, fdiff, action = mirror_check(path, inp, quiet=True)
        rows.append({"case": name, "ok": ok, "max_trace_diff": worst, "max_feature_diff": fdiff, "action": action})
    df = pd.DataFrame(rows)
    print(f"{inp['run']}: {int(df.ok.sum())} / {len(df)} configurations match; max trace difference "
          f"{df.max_trace_diff.max():.3g}, max feature difference {df.max_feature_diff.max():.3g}; tree actions chosen: "
          f"{df[df.case.str.endswith('tree')].action.value_counts().to_dict()}")
    return df


def smc(xml, runs, seed=2027):
    """Stochastic mirror: the XML's random semantics (lead-time sampling, SCEN_MODE 2 disruption sampling)
    executed in Python. Its estimate of Pr(win_done && win_ok) is what verifyta's query 2 should reproduce within
    sampling error; it is compared with the L4 certificate (independent Python episodes)."""
    from scipy.stats import beta
    k = constants(xml)
    rng = np.random.default_rng(seed)
    ok = []
    for _ in range(runs):
        m = Mirror(k, rng)
        while m.day <= k["LAST"]:
            m.step()
        ok.append(m.win_done and m.win_ok)
    n, x = len(ok), int(sum(ok))
    lo = beta.ppf(0.025, x, n - x + 1) if x > 0 else 0.0
    hi = beta.ppf(0.975, x + 1, n - x) if x < n else 1.0
    print(f"{os.path.basename(xml)}: Pr(win_done && win_ok) = {x / n:.1%} [{lo:.1%}, {hi:.1%}] over {n} runs")
    return x / n, lo, hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["mirror", "expected", "compare", "suite", "smc"])
    ap.add_argument("--runs", type=int, default=1000)
    ap.add_argument("xml")
    ap.add_argument("inputs", nargs="?")
    ap.add_argument("verifyta_output", nargs="?")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.mode == "suite":
        df = suite(a.xml)                                 # the first positional argument is the input file
        out = a.out or os.path.join(HERE, f"crosscheck_suite_{json.load(open(a.xml))['run']}.csv")
        df.to_csv(out, index=False)
        sys.exit(0 if df.ok.all() else 1)
    if a.mode == "smc":
        smc(a.xml, a.runs)
        return
    k = constants(a.xml)
    inp = json.load(open(a.inputs))
    if a.mode == "expected":
        ref, _, _ = twin_trace(inp, k)
        out = a.out or f"expected_{inp['run']}.csv"
        ref.to_csv(out, index=False)
        print(f"wrote {out}")
        return
    if a.mode == "mirror":
        ok, _, _, _ = mirror_check(a.xml, inp)
    else:
        if not a.verifyta_output:
            raise SystemExit("compare needs the verifyta output file")
        if k["LEAD_MODE"] != 1 or k["SCEN_MODE"] == 2:
            print("warning: this XML is stochastic (LEAD_MODE != 1 or SCEN_MODE 2); the trace will not match")
        ref, _, _ = twin_trace(inp, k)
        ok, _ = compare(ref, parse_verifyta(a.verifyta_output, k["FIRST"]), f"UPPAAL {os.path.basename(a.xml)} vs twin")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
