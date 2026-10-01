"""Prices for the cost side of the AI decision layer (L2), from the same SAP tables as the rest of the ledger.

  PR1  F12 net sales price per unit   VBAP NETWR / KWMENG, F12 lines, fraud-labelled sales orders excluded
  PR2  component purchase price       EKPO NETPR / PEINH per material, fraud-labelled POs excluded
  PR3  F12 material cost per unit     sum over the BOM in force (the most frequent F12 issued recipe in the
                                      twin input) of PR2 x quantity per unit

All are quantity-weighted means over the game year; min and max are reported because the players changed
prices during the game. These values are used only to put lost sales and extra inventory in the same unit
(money); the physics of the twin does not use them.

Usage:
    python derive_prices.py /path/to/erp_fraud_data [--out prices]
"""
import argparse
import json
import os
from collections import Counter

import pandas as pd

from build_twin_inputs import COMPONENTS, find
from derive_calibration import PRODUCT, labelled_documents

RUNS = ["normal_2", "fraud_2", "fraud_3"]


def table(root, run, name):
    df = pd.read_excel(find(root, run, [name]))
    if run != "normal_2":
        ref = pd.read_excel(find(root, "normal_2", [name]), nrows=0).columns
        if len(ref) != df.shape[1]:
            raise ValueError(f"{run}/{name}: width {df.shape[1]} vs {len(ref)}")
        df.columns = ref
    return df


def wmean(price, qty):
    return float((price * qty).sum() / qty.sum())


def derive(root, run, inputs_dir):
    ev = labelled_documents(root).get(run, {"fraud_po": set(), "fraud_so": set()})
    vbap = table(root, run, "vbap")
    v = vbap[(vbap.MATNR == PRODUCT) & ~vbap.VBELN.isin(ev["fraud_so"]) & (vbap.KWMENG > 0)]
    p = v.NETWR / v.KWMENG
    out = {"run": run, "PR1_sales_price": {"mean": round(wmean(p, v.KWMENG), 4), "min": float(p.min()),
                                           "max": float(p.max()), "lines": int(len(v))}}
    ekpo = table(root, run, "ekpo")
    e = ekpo[ekpo.MATNR.isin(COMPONENTS) & ~ekpo.EBELN.isin(ev["fraud_po"]) & (ekpo.MENGE > 0)]
    e = e.assign(p=e.NETPR / e.PEINH)
    out["PR2_purchase_price"] = {m: {"mean": round(wmean(g.p, g.MENGE), 4), "min": float(g.p.min()),
                                     "max": float(g.p.max()), "lines": int(len(g))} for m, g in e.groupby("MATNR")}
    inp = json.load(open(os.path.join(inputs_dir, f"{run}.json")))
    recipes = Counter(json.dumps(o.get("issued_recipe") or o["recipe"], sort_keys=True)
                      for o in inp["recorded_production_orders"])
    bom = json.loads(recipes.most_common(1)[0][0])
    out["PR3_material_cost"] = {"bom": bom, "cost_per_unit": round(sum(
        q * out["PR2_purchase_price"][c]["mean"] for c, q in bom.items()), 4)}
    out["margin_per_unit"] = round(out["PR1_sales_price"]["mean"] - out["PR3_material_cost"]["cost_per_unit"], 4)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--inputs", default=os.path.join(os.path.dirname(__file__), "..", "model", "twin", "inputs"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "prices"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    allp = {r: derive(a.root, r, a.inputs) for r in RUNS}
    with open(os.path.join(a.out, "prices.json"), "w") as fh:
        json.dump(allp, fh, indent=1)
    lines = ["# Prices (PR1-PR3)\n", "Quantity-weighted means over the game year; fraud-labelled documents excluded.\n",
             "| | " + " | ".join(RUNS) + " |", "|---|" + "---|" * len(RUNS)]
    lines.append("| PR1 F12 sales price per unit [min, max] | " + " | ".join(
        f"{allp[r]['PR1_sales_price']['mean']:.2f} [{allp[r]['PR1_sales_price']['min']:.2f}, {allp[r]['PR1_sales_price']['max']:.2f}]" for r in RUNS) + " |")
    for c in COMPONENTS:
        lines.append(f"| PR2 {c} purchase price | " + " | ".join(
            f"{allp[r]['PR2_purchase_price'][c]['mean']:.3f}" if c in allp[r]["PR2_purchase_price"] else "-" for r in RUNS) + " |")
    lines.append("| PR3 F12 material cost per unit | " + " | ".join(f"{allp[r]['PR3_material_cost']['cost_per_unit']:.3f}" for r in RUNS) + " |")
    lines.append("| margin per unit (PR1 - PR3) | " + " | ".join(f"{allp[r]['margin_per_unit']:.3f}" for r in RUNS) + " |")
    with open(os.path.join(a.out, "prices.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
