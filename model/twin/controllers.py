"""Controllers for the three real decisions of the ERPsim players (production-order conversions, POs,
transfers to DCs). The AI decision layer (L2) will be one more controller; these are the baselines.

Every controller only uses levers the players had (docs/disruptions.md, section 5).
"""
import math
from collections import defaultdict

import numpy as np


class ReplayController:
    """The players' recorded decisions (identical to policy='replay', push_rule='replay')."""

    def __init__(self, inp, deferred=True):
        self.deferred = deferred      # False: plain transfer replay (clipped part is lost), for robustness checks
        self.orders, self.pos, self.transfers_ = defaultdict(list), defaultdict(list), defaultdict(dict)
        for o in inp["recorded_production_orders"] + inp["other_production_orders"]:
            self.orders[o["day"]].append((o["product"], o["qty"], o.get("issued_recipe") or o["recipe"]))
        for p in inp.get("recorded_pos", []):
            self.pos[p["day"]].append(p)
        for t in inp.get("recorded_transfers", []):
            self.transfers_[t["day"]][t["dc"]] = self.transfers_[t["day"]].get(t["dc"], 0.0) + t["qty"]
        self.owed = {}

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
        """Recorded transfers, deferred: a part that cannot be shipped for lack of plant stock stays owed to its
        DC and ships as soon as stock allows (same rule as push_rule="replay_deferred", Amendment 3)."""
        if not self.deferred:
            return dict(self.transfers_.get(day, {}))
        for d, q in self.transfers_.get(day, {}).items():
            self.owed[d] = self.owed.get(d, 0.0) + q
        plan, left = {}, tw.plant
        for d in tw.dc:                                   # same DC order as the twin
            q = min(self.owed.get(d, 0.0), left)
            if q > 0:
                plan[d] = q
                left -= q
        return plan

    def shipped(self, done):
        """Called by the twin with what was actually shipped; owed quantities ship first."""
        for d, q in done.items():
            if d in self.owed:
                self.owed[d] -= min(self.owed[d], q)


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


def recipe_in_force(inp, day):
    """Issued recipe of the most recent recorded F12 order created on or before `day` (else the first one)."""
    orders = sorted(inp["recorded_production_orders"], key=lambda o: o["day"])
    past = [o for o in orders if o["day"] <= day] or orders[:1]
    o = past[-1]
    return o.get("issued_recipe") or o["recipe"]


def water_fill(levels, rates, amount):
    """Split `amount` over DCs so that the lowest days of cover (level / rate) is raised first."""
    lo, hi = 0.0, (sum(levels.values()) + amount) / min(rates.values()) + 1
    for _ in range(60):
        mid = (lo + hi) / 2
        need = sum(max(0.0, mid * rates[d] - levels[d]) for d in levels)
        lo, hi = (mid, hi) if need < amount else (lo, mid)
    alloc = {d: max(0.0, lo * rates[d] - levels[d]) for d in levels}
    tot = sum(alloc.values())
    return {d: amount * v / tot for d, v in alloc.items()} if tot > 0 else {d: 0.0 for d in levels}


class ResponseController(ReplayController):
    """The players' decisions plus a response to a disruption notified on day `start`, using only the
    players' three levers, active for `window` days (AI layer L2's action space, docs/ai_layers.md):

      po_days  lever 2: extra POs keep available + on-order stock of each component >= po_days days of its
               recent (20-day) consumption
      fg_units lever 1: one extra F12 production order of fg_units on day `start` (recipe in force), with
               lot-for-lot POs for its components
      ship     lever 3: plant stock left after the recorded transfers is shipped the same day, split over the
               DCs to equalise days of cover
      prio     lever 1: for `prio` days, the other products' recorded conversions are held back while F12 orders
               are waiting for the line, and released as soon as no F12 order waits (or when the period ends), so
               that F12 gets the line first; the cost is the other products' lost sales (twin log: lost_other)
    """

    def __init__(self, inp, start, po_days=0, fg_units=0, ship=False, prio=0, window=40, deferred=True):
        super().__init__(inp, deferred)
        self.start, self.po_days, self.fg_units, self.ship, self.window = start, po_days, fg_units, ship, window
        self.prio, self.held = prio, []
        self.use = defaultdict(list)
        self.recipe = recipe_in_force(inp, start)

    def _active(self, day):
        return self.start <= day < self.start + self.window

    def production_orders(self, tw, day):
        out = list(super().production_orders(tw, day))
        if self.prio:
            if self.start <= day < self.start + self.prio:
                self.held += [o for o in out if o[0] != tw.product]
                out = [o for o in out if o[0] == tw.product]
                f12_waiting = any(o["product"] == tw.product for o in tw.queue) or bool(out)
                if not f12_waiting:
                    out, self.held = self.held + out, []
            elif self.held:
                out, self.held = self.held + out, []
        if self.fg_units and day == self.start:
            out.append((tw.product, float(self.fg_units), self.recipe))
        return out

    def purchase_orders(self, tw, day):
        out = super().purchase_orders(tw, day)
        for c, q in getattr(tw, "last_consumption", {}).items():
            self.use[c].append(q)
        if self.fg_units and day == self.start:
            for c, r in self.recipe.items():
                if r > 0:
                    step = tw.inp["po_rounding"][c]
                    out.append((c, math.ceil(r * self.fg_units / step) * step))
        if self.po_days and self._active(day):
            for c in tw.components:
                hist = self.use[c][-20:]
                target = self.po_days * (float(np.mean(hist)) if hist else 0.0)
                position = (tw.comp[c] + sum(p["qty"] for p in tw.open_pos if p["material"] == c)
                            + sum(q for m, q in out if m == c))
                if target > position:
                    step = tw.inp["po_rounding"][c]
                    out.append((c, math.ceil((target - position) / step) * step))
        return out

    def transfers(self, tw, day, carried):
        plan = dict(super().transfers(tw, day, carried))
        if self.ship and self._active(day):
            left = tw.plant - sum(plan.values())
            if left > 0:
                rates = {d: max(float(np.mean(tw.recent_sales[d][-20:])) if tw.recent_sales[d] else 1.0, 1.0)
                         for d in tw.dc}
                levels = {d: tw.dc[d] + plan.get(d, 0.0) for d in tw.dc}
                for d, q in water_fill(levels, rates, left).items():
                    plan[d] = plan.get(d, 0.0) + q
        return plan
