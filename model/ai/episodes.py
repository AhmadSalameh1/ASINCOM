"""Episode dataset for the AI layers (L1 predict, L2 decide): disruptions sampled within their evidence bounds,
hitting the validated twin at a random day, with the outcome of every response action.

One episode = (year, start day s, seed, disruption). For each episode the twin is run
  - once without the disruption and without a response (the reference for "extra" loss), and
  - once per response action under the disruption (the action set, docs/ai_layers.md),
all with the same seed and keyed lead-time streams (common random numbers: runs differ only by the disruption
and the action). Decisions are the players' recorded ones (validated round-2 physics) plus the response; the
blocked-material re-order (rule R5) is always on. Recorded transfers are replayed with deferral (a part that
cannot ship for lack of plant stock ships as soon as stock allows; validation Amendment 3).

The features are what a planner observes at the start of day s, plus the disruption notice (type and announced
severity). They are recorded by an observer inside the run, so no future information can leak into them.

Severity sampling (docs/disruptions.md for the evidence):
  E1 supplier delay   relative delay r from the USAID SCMS late-shipment quantiles (q0 = 0, q50 0.124,
                      q75 0.372, q90 0.746, q95 0.963), u ~ U(0, 0.95], linear interpolation
  E2 quality loss     blocked share ~ U[0.002, 0.041] (ERPsim Q2 range), +2 days (Q1); one food material or
                      all food materials (equal odds)
  E3 line stoppage    1..25 days (25 = shortest observed production pause, B17)
  E4 demand surge     factor ~ U[1.05, 1.19] (normal 2 steady monthly range)
  E5 transit delay    1..4 days (DataCo q50..q95)
STRESS episodes (--stress) use levels beyond the evidence: E2 25 % blocked, all food; E4 factor 1.5.

Usage:
    python episodes.py --runs normal_2 fraud_2 fraud_3 --n 2000 [--stress] [--cert] [--out data]
"""
import argparse
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "twin"))
from controllers import ResponseController  # noqa: E402
from twin import DCS, Twin  # noqa: E402

INPUTS = os.path.join(HERE, "..", "twin", "inputs")
PRICES = os.path.join(HERE, "..", "..", "data", "prices", "prices.json")
EPISODE = 20          # disruption window (one game month), as in Phase E
HORIZON = 60          # outcome window from the start day
FOOD = ["AA-R01", "AA-R02", "AA-R03", "AA-R04", "AA-R05", "AA-R06"]
USAID_Q = ([0.0, 0.5, 0.75, 0.9, 0.95], [0.0, 0.124, 0.372, 0.746, 0.963])
TYPES = ["E1", "E2", "E3", "E4", "E5"]
DEFERRED = True       # transfer replay with deferral (Amendment 3); --plain-push for the robustness check

# response actions: (name, po_days, fg_units, ship, prio_days); fg_units = one line-day of output (M6)
ACTIONS = [("none", 0, 0, False, 0), ("po5", 5, 0, False, 0), ("po10", 10, 0, False, 0), ("fg", 0, 24000, False, 0),
           ("ship", 0, 0, True, 0), ("prio", 0, 0, False, 20), ("fg+prio", 0, 24000, False, 20),
           ("po10+fg+prio", 10, 24000, False, 20)]


def sample_disruption(rng, stress=False):
    t = TYPES[rng.integers(5)] if not stress else ["E2", "E4"][rng.integers(2)]
    d = {"type": t, "e1_rel": 0.0, "e2_share": 0.0, "e2_allfood": 0, "e3_days": 0, "e4_factor": 1.0, "e5_days": 0}
    if t == "E1":
        d["e1_rel"] = float(np.interp(rng.uniform(1e-9, 0.95), *USAID_Q))
    elif t == "E2":
        d["e2_share"] = 0.25 if stress else float(rng.uniform(0.002, 0.041))
        d["e2_allfood"] = 1 if stress else int(rng.integers(2))
        d["e2_material"] = "all" if d["e2_allfood"] else FOOD[rng.integers(len(FOOD))]
    elif t == "E3":
        d["e3_days"] = int(rng.integers(1, 26))
    elif t == "E4":
        d["e4_factor"] = 1.5 if stress else float(rng.uniform(1.05, 1.19))
    else:
        d["e5_days"] = int(rng.integers(1, 5))
    return d


def scenario(d, s):
    w = [s, s + EPISODE - 1]
    t = d["type"]
    if t == "E1":
        return {"supplier_delay": {"window": w, "relative": d["e1_rel"]}}
    if t == "E2":
        mats = FOOD if d["e2_allfood"] else [d["e2_material"]]
        return {"quality": {"window": w, "block_share": d["e2_share"], "extra_delay": 2, "materials": mats}}
    if t == "E3":
        return {"line_down": [[s, s + d["e3_days"] - 1]]}
    if t == "E4":
        return {"demand": {"window": w, "factor": d["e4_factor"]}}
    return {"transit": {"window": w, "days": d["e5_days"]}}


class Observer:
    """Records the planner-observable state at the start of day `at` (and the history it needs)."""

    def __init__(self, at):
        self.at, self.use, self.lost, self.x = at, [], [], None

    def __call__(self, tw, day):
        if tw.log:
            self.lost.append(tw.log[-1]["lost"])
        if getattr(tw, "last_consumption", None) is not None and tw.log:
            self.use.append(dict(tw.last_consumption))
        if day != self.at:
            return
        x = {}
        use20 = self.use[-20:]
        recipe = tw.controller.recipe if tw.controller is not None else {}
        covers = []
        for c in tw.components:
            rate = float(np.mean([u[c] for u in use20])) if use20 else 0.0
            onord = sum(p["qty"] for p in tw.open_pos if p["material"] == c)
            x[f"stock_{c}"] = tw.comp[c]
            x[f"onorder_{c}"] = onord
            x[f"cover_{c}"] = min((tw.comp[c] + onord) / rate, 60.0) if rate > 0 else 60.0
            if recipe.get(c, 0) > 0:
                covers.append(min(tw.comp[c] / max(rate, 1e-9), 60.0) if rate > 0 else 60.0)
        x["min_cover_f12_components"] = min(covers) if covers else 60.0
        head = tw.queue[0] if tw.queue else None
        x["queue_f12_units"] = sum(o["remaining"] for o in tw.queue if o["product"] == tw.product)
        x["queue_other_units"] = sum(o["remaining"] for o in tw.queue if o["product"] != tw.product)
        x["queue_orders"] = len(tw.queue)
        x["head_blocked"] = int(head is not None and "start" not in head and not tw._can_start(head))
        x["head_is_f12"] = int(head is not None and head["product"] == tw.product)
        x["changeover_left"] = tw.changeover_left
        x["plant"] = tw.plant
        dem = {d: float(np.mean(tw.recent_sales[d][-20:])) if tw.recent_sales[d] else 0.0 for d in DCS}
        for d in DCS:
            x[f"dc_{d}"] = tw.dc[d]
            x[f"dc_cover_{d}"] = min(tw.dc[d] / dem[d], 60.0) if dem[d] > 0 else 60.0
        x["dc_total"] = sum(tw.dc.values())
        x["dc_min_cover"] = min(x[f"dc_cover_{d}"] for d in DCS)
        x["demand_20d"] = sum(dem.values())
        x["fg_cover"] = min((x["dc_total"] + tw.plant + x["queue_f12_units"]) / max(x["demand_20d"], 1.0), 120.0)
        x["lost_20d"] = float(np.sum(self.lost[-20:]))
        x["transfer_backlog"] = float(sum(getattr(tw.controller, "owed", {}).values())) if tw.controller else 0.0
        self.x = x


def inventory_value(df, comps, price):
    comp_val = sum(df[f"stock_{c}"] * price["PR2_purchase_price"][c]["mean"] for c in comps)
    fg_units = df.plant_stock + df[[f"dc_{d}" for d in DCS]].sum(axis=1)
    return comp_val + fg_units * price["PR3_material_cost"]["cost_per_unit"]


_CACHE = {}


def _set_push(deferred):
    global DEFERRED
    DEFERRED = deferred


def _inp(run):
    if run not in _CACHE:
        _CACHE[run] = (json.load(open(os.path.join(INPUTS, f"{run}.json"))), json.load(open(PRICES))[run])
    return _CACHE[run]


def run_episode(job):
    eid, run, s, seed, d = job
    inp, price = _inp(run)
    comps = inp["components"]

    def go(sc, action):
        _, po_days, fg, ship, prio = action
        ctl = ResponseController(inp, s, po_days, fg, ship, prio, deferred=DEFERRED)
        obs = Observer(s)
        df = Twin(inp, seed=seed, demand_mode="replay", policy="controller", controller=ctl, scenario=sc,
                  lead_stream="keyed", observer=obs).run().set_index("day").loc[s:s + HORIZON - 1]
        return df, obs.x

    base, x = go({}, ACTIONS[0])
    base_lost = float(base.lost.sum())
    base_other = float(base.lost_other.sum())
    demand = float((base.sales + base.lost).sum())
    row = {"episode": eid, "run": run, "start": s, "seed": seed, **{k: v for k, v in d.items() if k != "e2_material"},
           **x, "base_lost": base_lost, "base_lost_other": base_other, "window_demand": demand}
    sc = scenario(d, s)
    inv0 = None
    for a in ACTIONS:
        df, _ = go(sc, a)
        inv = float(inventory_value(df, comps, price).mean())
        inv0 = inv if inv0 is None else inv0
        lost = float(df.lost.sum())
        row[f"lost_{a[0]}"] = lost
        row[f"extra_{a[0]}"] = lost - base_lost
        row[f"lostother_{a[0]}"] = float(df.lost_other.sum())
        row[f"extraother_{a[0]}"] = float(df.lost_other.sum()) - base_other
        row[f"inv_{a[0]}"] = inv
        row[f"addinv_{a[0]}"] = inv - inv0
        row[f"lostmargin_{a[0]}"] = lost * price["margin_per_unit"]
    return row


def start_days(inp):
    steady = sorted(inp["demand"]["steady_months"])
    return [d for m in steady for d in range((m - 1) * 20 + 1, m * 20 + 1) if d + HORIZON + 20 <= inp["days"]["last"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", default=["normal_2", "fraud_2", "fraud_3"])
    ap.add_argument("--n", type=int, default=1500)
    ap.add_argument("--stress", action="store_true")
    ap.add_argument("--cert", action="store_true", help="independent certification sample (separate random stream)")
    ap.add_argument("--plain-push", action="store_true", help="robustness check: plain transfer replay (no deferral)")
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    ap.add_argument("--out", default=os.path.join(HERE, "data"))
    a = ap.parse_args()
    global DEFERRED
    DEFERRED = not a.plain_push
    os.makedirs(a.out, exist_ok=True)
    for run in a.runs:
        inp, _ = _inp(run)
        days = start_days(inp)
        rng = np.random.default_rng([2027, ["normal_2", "fraud_2", "fraud_3"].index(run), int(a.stress)]
                                    + ([1] if a.cert else []))
        jobs = [(i, run, int(rng.choice(days)), int(rng.integers(1_000_000)), sample_disruption(rng, a.stress))
                for i in range(a.n)]
        t0 = time.time()
        with Pool(a.workers, initializer=_set_push, initargs=(DEFERRED,)) as pool:
            rows = pool.map(run_episode, jobs, chunksize=4)
        name = f"episodes_{run}{'_stress' if a.stress else ''}{'_cert' if a.cert else ''}{'_plainpush' if a.plain_push else ''}.csv.gz"
        pd.DataFrame(rows).to_csv(os.path.join(a.out, name), index=False)
        print(f"{run}: {len(rows)} episodes in {time.time() - t0:.0f} s -> {name}")


if __name__ == "__main__":
    main()
