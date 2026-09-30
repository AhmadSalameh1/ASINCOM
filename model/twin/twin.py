"""Python reference twin of the ERPsim supply chain (AA-F12), per docs/model_spec.md.

One step = one game day (DR-1). Order of events within a day (spec section 1):
  1. supplier receipts         (POs due today; L3, L4)
  2. production                (shared FIFO line, 24,000 units/day, components per recipe; B11-B13, M6)
  3. plant -> DC push          (fitted push rule; spec section 4, item 3)
  4. customer orders and sales (sale = min(order, DC stock), excess lost; B2-B4)
  5. decisions                 (forecast updates -> MRP for production and purchasing; policy rules R1-R6)

The twin knows nothing about SAP: everything comes from an input file built by
data/build_twin_inputs.py. Quantities are real units (the UPPAAL model divides by 100).

Modes
  forecast_mode "replay" : forecast updates replayed from the recorded year (validation, Phase D)
  demand_mode   "replay" : the recorded customer orders (day, customer, quantity) are replayed; sales are
                           still clipped to the twin's own DC stock. Isolates the supply-side physics.
                "sample" : customers order at sampled intervals and sizes (D1-D3, D5; experiments)
  line_rule     "fifo_block" : the order at the head of the line waits for its components
                "fifo_skip"  : an order short of components is skipped; the next one proceeds
                "erpsim"     : FIFO; an order starts only when components for its whole batch are in stock
                               (78 of 78 recorded starts), and switching to another product costs one
                               idle day (recorded gap between orders: median 1 day on a product switch,
                               0 days otherwise)
  others        "mrp"    : the other products (F16, F15) are planned by the same MRP from their own replayed
                           forecasts and replayed sales (planning level: total stock, no customers or DCs)
                "replay" : their recorded production orders are replayed as background line load
"""
import math
from collections import defaultdict

import numpy as np
import pandas as pd

DCS = ["North", "South", "West"]


class Twin:
    def __init__(self, inp, seed=0, forecast_mode="replay", demand_mode="sample", line_rule="erpsim", others="mrp"):
        if forecast_mode != "replay":
            raise NotImplementedError("only the replay forecast mode is implemented and validated so far")
        self.demand_mode, self.line_rule, self.others = demand_mode, line_rule, others
        self.planning_products = [p for p in inp.get("planning_products", [inp["product"]])
                                  if p == inp["product"] or others == "mrp"]
        self.recorded_by_product = defaultdict(list)
        for o in inp["recorded_production_orders"] + inp["other_production_orders"]:
            self.recorded_by_product[o["product"]].append(o)
        for p in self.recorded_by_product:
            self.recorded_by_product[p].sort(key=lambda o: o["day"])
        self.other_sales = {p: {int(d): q for d, q in v.items()} for p, v in inp.get("other_product_daily_sales", {}).items()}
        self.replay_orders = defaultdict(list)
        for o in inp["demand"].get("recorded_orders", []):
            self.replay_orders[o["day"]].append(o)
        self.inp = inp
        self.rng = np.random.default_rng(seed)
        self.product = inp["product"]
        self.components = inp["components"]
        self.cap = inp["capacity_per_day"]
        d = inp["demand"]
        self.gap_values = np.array(list(map(int, d["inter_order_days"].keys())))
        self.gap_probs = np.array(list(d["inter_order_days"].values()), dtype=float)
        self.gap_probs /= self.gap_probs.sum()
        self.qty_samples = np.array(d["order_qty_samples"])
        self.lead = {g: (np.array(list(map(int, p.keys()))), np.array(list(p.values()), dtype=float) / sum(p.values()))
                     for g, p in inp["lead_time_pmf"].items()}
        self.push = inp["dc_push"]
        self.updates = defaultdict(list)
        for u in inp["forecast_updates"]:
            self.updates[u["day"]].append(u)
        self.other_orders = defaultdict(list)
        for o in inp["other_production_orders"]:
            self.other_orders[o["day"]].append(o)
        self.recorded_f12 = sorted(inp["recorded_production_orders"], key=lambda o: o["day"])
        self._reset()

    # ------------------------------------------------------------------ state
    def _reset(self):
        self.comp = {c: 0.0 for c in self.components}          # available component stock (B16: starts empty)
        self.open_pos = []                                      # dicts: material, qty, due
        self.queue = []                                         # production orders, FIFO
        self.plant = 0.0
        self.dc = {d: 0.0 for d in DCS}
        self.open_forecast = defaultdict(float)                 # R1, per planning product
        self.other_stock = defaultdict(float)                   # other products: total finished stock
        self.direct_forecast = {"AA-P01": 0.0, "AA-P02": 0.0}  # R4c
        self.next_order = {c["id"]: c["first_order_day"] for c in self.inp["customers"]}
        self.dc_of = {c["id"]: c["dc"] for c in self.inp["customers"]}
        self.log = []
        self.order_log = []
        self.today = None
        self.last_product = None
        self.changeover_left = 0
        self.changeover_days = 1

    # ------------------------------------------------------------------ helpers
    def _gap(self):
        return int(self.rng.choice(self.gap_values, p=self.gap_probs))

    def _qty(self):
        return float(self.rng.choice(self.qty_samples))

    def _lead(self, material):
        vals, p = self.lead["food" if material.startswith("AA-R") else "packaging"]
        return int(self.rng.choice(vals, p=p))

    def _lots(self, q, product):
        r = self.inp["lot_rules"][product]
        if q <= 0:
            return []
        q = math.ceil(q / r["rounding"]) * r["rounding"]
        out = []
        while q > r["max"]:
            out.append(r["max"])
            q -= r["max"]
        out.append(max(q, r["min"]))
        return out

    def _recipe_in_force(self, day, product=None):
        """R4b: the recipe of the next recorded order of `product` created on/after `day`, else the last one."""
        orders = self.recorded_by_product[product or self.product]
        for o in orders:
            if o["day"] >= day:
                return o["recipe"]
        return orders[-1]["recipe"]

    # ------------------------------------------------------------------ day steps
    def _receipts(self, day):
        due = [p for p in self.open_pos if p["due"] <= day]
        for p in due:
            self.comp[p["material"]] += p["qty"]
        self.open_pos = [p for p in self.open_pos if p["due"] > day]
        return sum(p["qty"] for p in due)

    def _can_start(self, o):
        return all(self.comp[c] + 1e-6 >= r * o["remaining"] for c, r in o["recipe"].items() if r > 0)

    def _produce(self):
        cap, out_f12, out_other = self.cap, 0.0, 0.0
        if self.line_rule == "erpsim":
            if self.changeover_left > 0:
                self.changeover_left -= 1
                return out_f12, out_other
            while self.queue and cap > 0:
                o = self.queue[0]
                if "start" not in o:
                    if not self._can_start(o):
                        break                                   # waits for its full batch
                    if self.last_product is not None and o["product"] != self.last_product:
                        self.last_product = o["product"]
                        self.changeover_left = self.changeover_days - 1
                        break                                   # this day is the changeover
                    o["start"] = self.today
                    self.order_log.append({"product": o["product"], "created": o["day"], "start": self.today})
                q = min(o["remaining"], cap)
                for c, r in o["recipe"].items():
                    self.comp[c] -= r * q
                o["remaining"] -= q
                cap -= q
                self.last_product = o["product"]
                if o["product"] == self.product:
                    self.plant += q
                    out_f12 += q
                else:
                    self.other_stock[o["product"]] += q
                    out_other += q
                if o["remaining"] <= 0:
                    self.queue.pop(0)
            return out_f12, out_other
        i = 0
        while i < len(self.queue) and cap > 0:
            o = self.queue[i]
            limit = min(o["remaining"], cap)
            for c, r in o["recipe"].items():
                if r > 0:
                    limit = min(limit, math.floor(self.comp[c] / r))
            if limit <= 0:
                if self.line_rule == "fifo_block":
                    break          # the order at the head waits for its components
                i += 1             # fifo_skip: try the next order
                continue
            for c, r in o["recipe"].items():
                self.comp[c] -= r * limit
            if "start" not in o:
                o["start"] = self.today
                self.order_log.append({"product": o["product"], "created": o["day"], "start": self.today})
            o["remaining"] -= limit
            cap -= limit
            if o["product"] == self.product:
                self.plant += limit
                out_f12 += limit
            else:
                self.other_stock[o["product"]] += limit
                out_other += limit
            if o["remaining"] <= 0:
                self.queue.pop(i)
            else:
                i += 1
        return out_f12, out_other

    def _push(self):
        ship = math.floor(self.plant * self.push["daily_fraction_of_plant_stock"])
        sent = 0.0
        for d in DCS:
            q = math.floor(ship * self.push["dc_shares"].get(d, 0))
            self.dc[d] += q
            sent += q
        self.plant -= sent
        return sent

    def _sales(self, day):
        sold, lost = defaultdict(float), defaultdict(float)
        if self.demand_mode == "replay":
            for o in self.replay_orders.get(day, []):
                dc = self.dc_of.get(o["customer"])
                if dc is None:
                    continue
                s = min(o["qty"], self.dc[dc])
                self.dc[dc] -= s
                sold[dc] += s
                lost[dc] += o["qty"] - s
            return sold, lost
        for k, nd in self.next_order.items():
            if nd != day:
                continue
            dc = self.dc_of[k]
            q = self._qty()
            s = min(q, self.dc[dc])
            self.dc[dc] -= s
            sold[dc] += s
            lost[dc] += q - s
            self.next_order[k] = day + self._gap()
        return sold, lost

    def _other_sales(self, day):
        """Other products at planning level: replayed sales, clipped to their total stock."""
        for p in self.planning_products:
            if p == self.product:
                continue
            q = self.other_sales.get(p, {}).get(day, 0.0)
            s = min(q, self.other_stock[p])
            self.other_stock[p] -= s
            self.open_forecast[p] = max(0.0, self.open_forecast[p] - s)

    def _decide(self, day):
        run_for = []
        for u in self.updates.get(day, []):
            if u["material"] in self.planning_products:
                self.open_forecast[u["material"]] = u["open_qty"]   # R1: new open forecast
                run_for.append(u["material"])
            elif u["material"] in self.direct_forecast:
                self.direct_forecast[u["material"]] = u["open_qty"]
        created = []
        for p in dict.fromkeys(run_for):                            # R2, R3 (one run per product per day)
            open_prod = sum(o["remaining"] for o in self.queue if o["product"] == p)
            stock = self.plant + sum(self.dc.values()) if p == self.product else self.other_stock[p]
            net = self.open_forecast[p] - stock - open_prod
            recipe = self._recipe_in_force(day, p)
            for q in self._lots(net, p):
                created.append({"product": p, "qty": q, "remaining": q, "recipe": recipe, "day": day})
        if self.others == "replay":                                 # background load (DR-2), replayed
            for o in self.other_orders.get(day, []):
                created.append({"product": o["product"], "qty": o["qty"], "remaining": o["qty"],
                                "recipe": o["recipe"], "day": day})
        mrp = bool(run_for)
        self.queue.extend(created)
        if mrp or created:                               # R4, R5, R6: purchasing
            gross = defaultdict(float)
            for o in self.queue:
                for c, r in o["recipe"].items():
                    gross[c] += r * o["remaining"]
            for c, q in self.direct_forecast.items():
                gross[c] += q
            for c in self.components:
                on_order = sum(p["qty"] for p in self.open_pos if p["material"] == c)
                net = gross[c] - self.comp[c] - on_order
                if net > 1e-6:
                    r = self.inp["po_rounding"][c]
                    q = math.ceil(round(net, 6) / r) * r
                    self.open_pos.append({"material": c, "qty": q, "due": day + self._lead(c)})
        return mrp, len(created)

    # ------------------------------------------------------------------ run
    def run(self):
        first, last = self.inp["days"]["first"], self.inp["days"]["last"]
        for day in range(first - 1, last + 1):
            self.today = day
            received = self._receipts(day)
            out_f12, out_other = self._produce()
            sent = self._push()
            sold, lost = self._sales(day)
            self.open_forecast[self.product] = max(0.0, self.open_forecast[self.product] - sum(sold.values()))  # R1
            self._other_sales(day)
            mrp, n_created = self._decide(day)
            row = {"day": day, "received": received, "production_f12": out_f12, "production_other": out_other,
                   "transferred": sent, "sales": sum(sold.values()), "lost": sum(lost.values()),
                   "plant_stock": self.plant, "queue_orders": len(self.queue),
                   "queue_f12_units": sum(o["remaining"] for o in self.queue if o["product"] == self.product),
                   "open_po_qty": sum(p["qty"] for p in self.open_pos), "mrp_run": mrp, "orders_created": n_created}
            for d in DCS:
                row[f"dc_{d}"] = self.dc[d]
                row[f"sales_{d}"] = sold[d]
                row[f"lost_{d}"] = lost[d]
            for c in self.components:
                row[f"stock_{c}"] = self.comp[c]
            self.log.append(row)
        return pd.DataFrame(self.log)
