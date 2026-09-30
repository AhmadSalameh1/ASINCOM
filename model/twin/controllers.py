"""Controllers for the three real decisions of the ERPsim players (production-order conversions, POs,
transfers to DCs). The AI decision layer (L2) will be one more controller; these are the baselines.

Every controller only uses levers the players had (docs/disruptions.md, section 5).
"""
import math
from collections import defaultdict

import numpy as np


class ReplayController:
    """The players' recorded decisions (identical to policy='replay', push_rule='replay')."""

    def __init__(self, inp):
        self.orders, self.pos, self.transfers_ = defaultdict(list), defaultdict(list), defaultdict(dict)
        for o in inp["recorded_production_orders"] + inp["other_production_orders"]:
            self.orders[o["day"]].append((o["product"], o["qty"], o.get("issued_recipe") or o["recipe"]))
        for p in inp.get("recorded_pos", []):
            self.pos[p["day"]].append(p)
        for t in inp.get("recorded_transfers", []):
            self.transfers_[t["day"]][t["dc"]] = self.transfers_[t["day"]].get(t["dc"], 0.0) + t["qty"]

    def production_orders(self, tw, day):
        return self.orders.get(day, [])

    def purchase_orders(self, tw, day):
        out = []
        for p in self.pos.get(day, []):
            if p.get("pre_start"):
                tw.open_pos.append({"material": p["material"], "qty": p["qty"], "due": day + 1})
            else:
                out.append((p["material"], p["qty"]))
        return out

    def transfers(self, tw, day, carried):
        return self.transfers_.get(day, {})


class BufferController(ReplayController):
    """Players' decisions plus a component buffer: extra POs keep available + on-order stock of each component
    at >= k days of its recent average consumption. Lever: POs only."""

    def __init__(self, inp, days_of_cover):
        super().__init__(inp)
        self.k = days_of_cover
        self.use = defaultdict(list)

    def purchase_orders(self, tw, day):
        out = super().purchase_orders(tw, day)
        for c, q in getattr(tw, "last_consumption", {}).items():
            self.use[c].append(q)
        for c in tw.components:
            hist = self.use[c][-20:]
            rate = float(np.mean(hist)) if hist else 0.0
            target = self.k * rate
            position = (tw.comp[c] + sum(p["qty"] for p in tw.open_pos if p["material"] == c)
                        + sum(q for m, q in out if m == c))
            if target > position:
                r = tw.inp["po_rounding"][c]
                out.append((c, math.ceil((target - position) / r) * r))
        return out
