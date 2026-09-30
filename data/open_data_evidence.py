"""Disruption evidence from open datasets (Phase E).

Datasets (downloaded from GitHub mirrors; licences: USAID data CC BY, DataCo CC BY 4.0):
  - USAID SCMS Delivery History (PEPFAR, 2006-2015): scheduled vs actual delivery per shipment
  - DataCo Smart Supply Chain (Constante, Silva, Pereira 2019): real vs scheduled shipping days, order dates

Only dimensionless quantities are extracted, so they can be transferred onto the twin's own lead times and
demand level (no claim that these supply chains resemble ERPsim):
  upstream (USAID):  share of late shipments; delay relative to planned lead time; severe-delay frequency
  downstream (DataCo): share of late deliveries; excess days relative to scheduled days
  demand (DataCo):   daily order-volume surges relative to the rolling median (size, duration, frequency)

Usage:
    python open_data_evidence.py SCMS.csv DATACO.csv [--out open_data]
"""
import argparse
import json
import os

import numpy as np
import pandas as pd


def q(s, ps=(0.5, 0.75, 0.9, 0.95)):
    s = pd.Series(s).dropna()
    return {f"q{int(p * 100)}": round(float(s.quantile(p)), 3) for p in ps} | {"mean": round(float(s.mean()), 3), "n": int(len(s))}


def usaid(path):
    d = pd.read_csv(path, encoding="utf-8-sig")
    date = lambda c: pd.to_datetime(d[c], errors="coerce", format="mixed")
    sched, deliv, po = date("Scheduled Delivery Date"), date("Delivered to Client Date"), date("PO Sent to Vendor Date")
    delay = (deliv - sched).dt.days
    lead = (sched - po).dt.days
    ok = delay.notna()
    late = delay > 0
    rel = (delay / lead).where((lead > 0) & late)
    return {
        "shipments": int(ok.sum()),
        "share_late": round(float(late[ok].mean()), 4),
        "delay_days_if_late": q(delay[late]),
        "shipments_with_planned_lead": int((lead > 0).sum()),
        "relative_delay_if_late": q(rel),          # delay / planned lead time
        "share_late_by_mode": {k: round(float(v), 4) for k, v in late[ok].groupby(d["Shipment Mode"][ok]).mean().items()},
    }


def dataco(path):
    d = pd.read_csv(path, encoding="latin-1", usecols=["Days for shipping (real)", "Days for shipment (scheduled)",
                                                        "Late_delivery_risk", "order date (DateOrders)",
                                                        "Order Item Quantity", "Shipping Mode"])
    real, sched = d["Days for shipping (real)"], d["Days for shipment (scheduled)"]
    excess = real - sched
    late = excess > 0
    rel = (excess / sched).where(late & (sched > 0))
    day = pd.to_datetime(d["order date (DateOrders)"], errors="coerce").dt.floor("D")
    daily = d.groupby(day)["Order Item Quantity"].sum().asfreq("D", fill_value=0)
    base = daily.rolling(28, min_periods=14, center=True).median()
    ratio = (daily / base).replace([np.inf, -np.inf], np.nan).dropna()
    surge = ratio > 1.5
    runs = (surge != surge.shift()).cumsum()[surge]
    lens = runs.value_counts()
    drop = ratio < 0.5
    druns = (drop != drop.shift()).cumsum()[drop]
    return {
        "order_items": int(len(d)),
        "share_late": round(float(late.mean()), 4),
        "late_delivery_risk_flag_mean": round(float(d["Late_delivery_risk"].mean()), 4),
        "excess_days_if_late": q(excess[late]),
        "relative_excess_if_late": q(rel),         # excess days / scheduled days
        "days_observed": int(len(ratio)),
        "demand_surge": {"threshold": "> 1.5 x rolling 28-day median",
                         "share_of_days": round(float(surge.mean()), 4),
                         "episodes": int(len(lens)),
                         "episode_length_days": q(lens.values),
                         "size_ratio_on_surge_days": q(ratio[surge])},
        "demand_drop": {"threshold": "< 0.5 x rolling 28-day median",
                        "share_of_days": round(float(drop.mean()), 4),
                        "episodes": int(druns.nunique()),
                        "size_ratio_on_drop_days": q(ratio[drop])},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scms")
    ap.add_argument("dataco")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "open_data"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    ev = {"usaid_scms": usaid(a.scms), "dataco": dataco(a.dataco)}
    json.dump(ev, open(os.path.join(a.out, "open_data_evidence.json"), "w"), indent=2)
    print(json.dumps(ev, indent=1))


if __name__ == "__main__":
    main()
