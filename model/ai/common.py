"""Shared definitions for the AI layers: episode loading, features, actions, splits.

All features and targets are dimensionless (days of demand, days of line capacity, days of cover), because
the three game years run at different demand levels: a model trained on one year must transfer to another.
"""
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
PRICES = json.load(open(os.path.join(HERE, "..", "..", "data", "prices", "prices.json")))
RUNS = ["normal_2", "fraud_2", "fraud_3"]
COMPONENTS = ["AA-R01", "AA-R02", "AA-R03", "AA-R04", "AA-R05", "AA-R06", "AA-P01", "AA-P02"]
DCS = ["North", "South", "West"]
TYPES = ["E1", "E2", "E3", "E4", "E5"]
ACTIONS = ["none", "po5", "po10", "fg", "ship", "prio", "fg+prio", "po10+fg+prio"]
CAP = 24000.0
SEED = 2027

NOTICE = [f"type_{t}" for t in TYPES] + ["e1_rel", "e2_share", "e2_allfood", "e3_days", "e4_factor", "e5_days"]
STATE = ([f"cover_{c}" for c in COMPONENTS] + ["min_cover_f12_components", "queue_f12_days", "queue_other_line_days",
         "queue_orders", "head_blocked", "head_is_f12", "changeover_line_days", "plant_days"]
         + [f"dc_cover_{d}" for d in DCS] + ["dc_min_cover", "fg_cover", "lost_20d_days", "backlog_days"])
FEATURES = NOTICE + STATE


def load(run, stress=False, cert=False, suffix=""):
    d = pd.read_csv(os.path.join(DATA, f"episodes_{run}{'_stress' if stress else ''}{'_cert' if cert else ''}{suffix}.csv.gz"))
    dem = d.demand_20d.clip(lower=1.0)                       # units per day, recent 20 days
    cost = PRICES[run]["PR3_material_cost"]["cost_per_unit"]
    new = {f"type_{t}": (d.type == t).astype(int) for t in TYPES}
    new.update({"queue_f12_days": d.queue_f12_units / dem, "queue_other_line_days": d.queue_other_units / CAP,
                "changeover_line_days": d.changeover_left / CAP, "plant_days": d.plant / dem,
                "lost_20d_days": d.lost_20d / dem, "backlog_days": d.transfer_backlog / dem, "dem": dem})
    for a in ACTIONS:                                        # targets in days of demand
        new[f"y_extra_{a}"] = d[f"extra_{a}"] / dem
        new[f"y_lost_{a}"] = d[f"lost_{a}"] / dem
        new[f"y_tot_{a}"] = (d[f"lost_{a}"] + d[f"lostother_{a}"]) / dem      # all products (L2 objective)
        # added inventory capital, in days of demand valued at material cost (PR3), so years compare
        new[f"y_inv_{a}"] = d[f"addinv_{a}"] / (dem * cost)
    d = pd.concat([d, pd.DataFrame(new)], axis=1)
    return d


def load_all(stress=False):
    return pd.concat([load(r, stress) for r in RUNS], ignore_index=True)


def split_within(d, seed=SEED, frac=(0.6, 0.2)):
    """Random train / calibration / test split of one year's episodes."""
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(d))
    a, b = int(frac[0] * len(d)), int((frac[0] + frac[1]) * len(d))
    return d.iloc[idx[:a]], d.iloc[idx[a:b]], d.iloc[idx[b:]]
