"""Export the certified decision trees (L3/L4) as plain arrays, for the UPPAAL model (model/uppaal).

Trees (built exactly as in l4_certify.py):
  tree_normal_2          L2 built on normal 2, distilled to depth 3 (the certified policy)
  tree_fraud_2_adapted   L2 built on normal 2 + 400 fraud 2 episodes, distilled (certified on the other 1,600)
  tree_fraud_3_adapted   same for fraud 3

Each JSON holds the feature list, the node arrays (feature index or -1 at a leaf, threshold, left, right, leaf
action) and the action table (lever parameters, from episodes.py). The array evaluation is checked against
scikit-learn's own predictions on every episode available (scikit-learn compares in float32, the arrays in
double precision, so a disagreement can only occur exactly at a threshold; the count is reported).

Usage:
    python export_tree.py [--out results]
"""
import argparse
import json
import os
import warnings

import numpy as np
import pandas as pd

from common import ACTIONS, FEATURES, RUNS, load
from episodes import ACTIONS as ACTION_LEVERS
from l2_decide import L2
from l3_explain import build, distil

warnings.filterwarnings("ignore")


def to_arrays(tree):
    t = tree.tree_
    act = [ACTIONS.index(tree.classes_[int(np.argmax(v))]) for v in t.value[:, 0, :]]
    return {"feature": [int(f) if f >= 0 else -1 for f in t.feature], "threshold": [float(x) for x in t.threshold],
            "left": [int(x) for x in t.children_left], "right": [int(x) for x in t.children_right], "action": act}


def predict_arrays(arrs, X):
    out = []
    for x in X:
        n = 0
        while arrs["feature"][n] >= 0:
            n = arrs["left"][n] if x[arrs["feature"][n]] <= arrs["threshold"][n] else arrs["right"][n]
        out.append(ACTIONS[arrs["action"][n]])
    return np.array(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"))
    a = ap.parse_args()
    data, tr, cal, te, sets = build()
    trees = {"tree_normal_2": distil(L2().fit(tr, cal), pd.concat([tr, cal]), 3)}
    perm = np.random.default_rng(2027).permutation(2000)
    for r in ["fraud_2", "fraud_3"]:
        tgt = data[r].iloc[perm]
        ta, ca = tgt.iloc[:300], tgt.iloc[300:400]
        trees[f"tree_{r}_adapted"] = distil(L2().fit(pd.concat([tr, ta]), ca), pd.concat([tr, cal, ta, ca]), 3)
    allx = pd.concat([load(r) for r in RUNS] + [load("normal_2", cert=True)] + [load(r, True) for r in RUNS])
    levers = {n: {"po_days": p, "fg_units": f, "ship": bool(s), "prio": pr} for n, p, f, s, pr in ACTION_LEVERS}
    for name, t in trees.items():
        arrs = to_arrays(t)
        agree = float((predict_arrays(arrs, allx[FEATURES].values) == t.predict(allx[FEATURES])).mean())
        doc = {"name": name, "features": FEATURES, "actions": ACTIONS, "levers": [levers[x] for x in ACTIONS],
               **arrs, "check_agreement_with_sklearn": agree, "check_episodes": len(allx)}
        with open(os.path.join(a.out, f"{name}.json"), "w") as fh:
            json.dump(doc, fh, indent=1)
        print(f"{name}: {len(arrs['feature'])} nodes, agreement with scikit-learn on {len(allx)} episodes: {agree:.4%}")


if __name__ == "__main__":
    main()
