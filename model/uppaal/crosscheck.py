"""Cross-check of the UPPAAL V12 model against the Python twin (deterministic mode: every lead time at its median).

Three checks, all against the same reference: the Python twin (model/twin/twin.py) run with policy, push and demand
replay and lead_mode="median", with the disruption switches read from the XML (so any EN_* setting is checked).

  mirror    Executes the generated XML itself in Python: every constant (data arrays, switches) is parsed from the
            XML's declaration and the day step is a line-by-line transcription of its UPPAAL functions. Checks the
            data export and the day-aggregated formulation. Runs without UPPAAL.
  expected  Writes the twin's expected trace (CSV) for comparison by hand.
  compare   Parses the output of `verifyta -q -s <model with LEAD_MODE = 1>` (query 1, `simulate`) and compares it
            with the twin day by day. This is the check that proves the UPPAAL model itself.

Usage:
    python crosscheck.py mirror   V12_normal_2.xml ../twin/inputs/normal_2.json
    python crosscheck.py expected V12_normal_2.xml ../twin/inputs/normal_2.json [--out expected_normal_2.csv]
    python crosscheck.py compare  V12_normal_2.xml ../twin/inputs/normal_2.json verifyta_output.txt

Time mapping: the automaton's first step fires at t = 1 and executes day FIRST - 1, so the state at time t is the
twin's end-of-day state of day FIRST - 2 + t.
"""
import argparse
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "twin"))
from twin import DCS, Twin  # noqa: E402

REL_TOL = 1e-6      # doubles; verifyta may print fewer digits, hence the absolute tolerance below
ABS_TOL = 0.5


# ---------------------------------------------------------------- XML constants
def constants(xml_path):
    decl = ET.parse(xml_path).getroot().find("declaration").text
    decl = re.sub(r"//[^\n]*", "", decl)
    env = {}
    for typ, name, value in re.findall(r"const\s+(int|double|bool)\s+(\w+)(?:\[[^=]*\])?\s*=\s*([^;]*);", decl):
        v = value.strip().replace("{", "[").replace("}", "]").replace("true", "True").replace("false", "False")
        env[name] = eval(v, {}, dict(env))      # values are literals or expressions of earlier constants
    return env


# ---------------------------------------------------------------- reference: the Python twin
def scenario_from(k, comps):
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
    return sc


def twin_trace(inp, k):
    df = Twin(inp, seed=0, demand_mode="replay", policy="replay", push_rule="replay", lead_mode="median",
              scenario=scenario_from(k, inp["components"])).run()
    out = pd.DataFrame({"day": df.day, "sold_day": df.sales, "lost_day": df.lost, "lost_total": df.lost.cumsum(),
                        "stockout_days": df[[f"dc_{d}" for d in DCS]].le(0).any(axis=1).cumsum()})
    for i, d in enumerate(DCS):
        out[f"dc[{i}]"] = df[f"dc_{d}"]
    out["plant"] = df.plant_stock
    out["produced_f12"] = df.production_f12.cumsum()
    for i, c in enumerate(inp["components"]):
        out[f"comp[{i}]"] = df[f"stock_{c}"]
    return out.reset_index(drop=True)


# ---------------------------------------------------------------- mirror: the XML's functions in Python
class Mirror:
    """Line-by-line transcription of the UPPAAL functions in generate_uppaal.py (deterministic lead mode)."""

    def __init__(self, k):
        self.k = k
        nc, ndc, nday = k["NC"], k["NDC"], k["NDAY"]
        self.day = k["FIRST"] - 1
        self.comp = [0.0] * nc
        self.plant = 0.0
        self.dc = [0.0] * ndc
        self.intransit = [[0.0] * nday for _ in range(ndc)]
        self.po = []                    # [qty, due, mat, open, qdone]
        self.qhead = self.qtail = self.next_ord = self.next_po = self.next_tr = 0
        self.remaining = [0.0] * k["N_ORD"]
        self.started = [False] * k["N_ORD"]
        self.last_prod = -1
        self.changeover_left = 0.0
        self.sold_total = self.lost_total = self.sold_day = self.lost_day = self.produced_f12 = 0.0
        self.stockout_days = 0

    def lead(self, m):
        return self.k["F_MED"] if self.k["IS_FOOD"][m] else self.k["P_MED"]

    def new_po(self, m, q, due_offset, qdone):
        k, l = self.k, due_offset
        if l < 0:
            l = self.lead(m)
            if k["EN_SUPPLIER_DELAY"] and k["SD_START"] <= self.day <= k["SD_END"]:
                l = l + (l * k["SD_REL100"] + 99) // 100
        self.po.append([q, self.day + l, m, True, qdone])
        assert len(self.po) <= k["N_PO_MAX"], "N_PO_MAX too small"

    def arrivals(self):
        for d in range(self.k["NDC"]):
            self.dc[d] += self.intransit[d][self.day]
            self.intransit[d][self.day] = 0.0

    def receipts(self):
        k = self.k
        for i in range(len(self.po)):
            p = self.po[i]
            if p[3] and p[1] <= self.day:
                p[3] = False
                m = p[2]
                if k["EN_QUALITY"] and not p[4] and k["Q_MAT"][m] and k["Q_START"] <= self.day <= k["Q_END"]:
                    blocked = p[0] * k["Q_BLOCK"]
                    rest = p[0] - blocked
                    if blocked > 0.0:
                        self.new_po(m, blocked, -1, True)
                    if k["Q_EXTRA"] > 0:
                        self.new_po(m, rest, k["Q_EXTRA"], True)
                    else:
                        self.comp[m] += rest
                else:
                    self.comp[m] += p[0]

    def can_start(self, o):
        rec = self.k["ORD_REC"][o]
        return all(not (rec[c] > 0.0 and self.comp[c] + 1e-6 < rec[c] * self.remaining[o]) for c in range(self.k["NC"]))

    def produce(self):
        k = self.k
        cap = float(k["CAP"])
        if k["EN_LINE_DOWN"] and k["LD_START"] <= self.day <= k["LD_END"]:
            return
        used = min(self.changeover_left, cap)
        self.changeover_left -= used
        cap -= used
        while self.qhead < self.qtail and cap > 0.0:
            o = self.qhead
            if not self.started[o]:
                if not self.can_start(o):
                    return
                if self.last_prod != -1 and k["ORD_PROD"][o] != self.last_prod:
                    self.last_prod = k["ORD_PROD"][o]
                    self.changeover_left = k["CHANGEOVER"]
                    used = min(self.changeover_left, cap)
                    self.changeover_left -= used
                    cap -= used
                    if cap <= 0.0:
                        return
                self.started[o] = True
            q = min(self.remaining[o], cap)
            for c in range(k["NC"]):
                self.comp[c] -= k["ORD_REC"][o][c] * q
            self.remaining[o] -= q
            cap -= q
            self.last_prod = k["ORD_PROD"][o]
            if k["ORD_PROD"][o] == 0:
                self.plant += q
                self.produced_f12 += q
            if self.remaining[o] <= 0.0:
                self.qhead += 1

    def to_dc(self, d, q):
        k = self.k
        if k["EN_TRANSIT"] and k["T_START"] <= self.day <= k["T_END"]:
            self.intransit[d][self.day + k["T_DAYS"]] += q
        else:
            self.dc[d] += q

    def push(self):
        k, sent = self.k, 0.0
        while self.next_tr < k["N_TR"] and k["TR_DAY"][self.next_tr] < self.day:
            self.next_tr += 1
        while self.next_tr < k["N_TR"] and k["TR_DAY"][self.next_tr] == self.day:
            q = min(k["TR_QTY"][self.next_tr], self.plant - sent)
            if q > 0.0:
                self.to_dc(k["TR_DC"][self.next_tr], q)
                sent += q
            self.next_tr += 1
        self.plant -= sent

    def sales(self):
        k = self.k
        self.sold_day = self.lost_day = 0.0
        for d in range(k["NDC"]):
            dem = k["DEMAND"][d][self.day] * 1.0
            if k["EN_DEMAND"] and k["DS_START"] <= self.day <= k["DS_END"]:
                dem = dem * k["DF"]
            s = min(dem, self.dc[d])
            self.dc[d] -= s
            self.sold_day += s
            self.lost_day += dem - s
        self.sold_total += self.sold_day
        self.lost_total += self.lost_day

    def decide(self):
        k = self.k
        while self.next_ord < k["N_ORD"] and k["ORD_DAY"][self.next_ord] == self.day:
            self.remaining[self.next_ord] = k["ORD_QTY"][self.next_ord]
            self.started[self.next_ord] = False
            self.next_ord += 1
            self.qtail = self.next_ord
        while self.next_po < k["N_REC_PO"] and k["RPO_DAY"][self.next_po] == self.day:
            pre = k["RPO_PRE"][self.next_po]
            self.new_po(k["RPO_MAT"][self.next_po], k["RPO_QTY"][self.next_po], 1 if pre else -1, False)
            self.next_po += 1
        if any(self.dc[d] <= 0.0 for d in range(k["NDC"])):
            self.stockout_days += 1

    def run(self):
        rows = []
        while self.day <= self.k["LAST"]:
            d = self.day
            self.arrivals(); self.receipts(); self.produce(); self.push(); self.sales(); self.decide()
            self.day += 1
            row = {"day": d, "sold_day": self.sold_day, "lost_day": self.lost_day, "lost_total": self.lost_total,
                   "stockout_days": self.stockout_days, "plant": self.plant, "produced_f12": self.produced_f12}
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
def compare(ref, got, label):
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
    print(f"{label}: {len(m)} days, {len(cols)} expressions")
    for c, e, n, fb in worst:
        print(f"  {c:>14}: max |diff| {e:.3g}" + (f"  -> {n} days out of tolerance, first on day {fb}" if n else ""))
    print("  RESULT:", "MATCH" if bad == 0 and len(m) else "MISMATCH")
    return bad == 0 and len(m) > 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["mirror", "expected", "compare"])
    ap.add_argument("xml")
    ap.add_argument("inputs")
    ap.add_argument("verifyta_output", nargs="?")
    ap.add_argument("--out")
    a = ap.parse_args()
    k = constants(a.xml)
    inp = json.load(open(a.inputs))
    ref = twin_trace(inp, k)
    if a.mode == "expected":
        out = a.out or f"expected_{inp['run']}.csv"
        ref.to_csv(out, index=False)
        print(f"wrote {out}")
        return
    if a.mode == "mirror":
        ok = compare(ref, Mirror(k).run(), f"mirror of {os.path.basename(a.xml)} vs twin")
    else:
        if not a.verifyta_output:
            raise SystemExit("compare needs the verifyta output file")
        if k["LEAD_MODE"] != 1:
            print("warning: LEAD_MODE is not 1 in this XML; the trace is stochastic and will not match")
        ok = compare(ref, parse_verifyta(a.verifyta_output, k["FIRST"]), f"UPPAAL {os.path.basename(a.xml)} vs twin")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
