"""L3 explain: (a) the decision policy distilled into a small decision tree that a planner can read and apply,
(b) what drives the impact predictor (SHAP), and (c) whether both explanations are stable.

  distillation  CART trees (depth 3 and 4) fitted to L2's choices on the normal 2 build episodes (states only,
                no outcomes). Fidelity = agreement with L2 on unseen episodes. The depth-3 tree is the policy
                that L4 certifies: the certified object is the explanation itself.
  stability     the whole pipeline (L2 and its distillation) is refitted on 10 bootstrap resamples of the build
                data: how often does the same root split / the same set of features appear, and how often do
                bootstrap trees agree on unseen episodes?
  SHAP          mean |SHAP| of the L1 impact model per feature on each test set; Spearman rank correlation of
                the importances between the build year and the shifted years

Usage:
    python l3_explain.py [--out results] [--boot 10]
"""
import argparse
import os
import warnings

import numpy as np
import pandas as pd
import shap
from scipy.stats import spearmanr
from sklearn.tree import DecisionTreeClassifier, export_text

from common import FEATURES, RUNS, SEED, load, split_within
from l1_predict import L1
from l2_decide import L2, outcome

warnings.filterwarnings("ignore")


def distil(model, pool, depth):
    y = model.choose(pool)
    return DecisionTreeClassifier(max_depth=depth, min_samples_leaf=20, random_state=SEED).fit(pool[FEATURES], y)


def tree_policy(tree, d):
    return pd.Series(tree.predict(d[FEATURES]), index=d.index)


def used_features(tree):
    f = tree.tree_.feature
    return sorted({FEATURES[i] for i in f if i >= 0})


def build():
    data = {r: load(r) for r in RUNS}
    stress = pd.concat([load(r, True) for r in RUNS], ignore_index=True)
    tr, cal, te = split_within(data["normal_2"])
    sets = {"normal 2 held-out": te, "fraud 2": data["fraud_2"], "fraud 3": data["fraud_3"], "STRESS": stress}
    return data, tr, cal, te, sets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"))
    ap.add_argument("--boot", type=int, default=10)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    data, tr, cal, te, sets = build()
    pool = pd.concat([tr, cal])
    model = L2().fit(tr, cal)
    md = ["# L3 results: explanations and their stability\n"]

    # ---- distillation ----
    trees = {k: distil(model, pool, k) for k in (3, 4)}
    md.append("## Distilled policy (fitted to L2's choices on the normal 2 build episodes)\n")
    md.append("| tree | leaves | features used | " + " | ".join(f"fidelity: {s}" for s in sets) + " |")
    md.append("|---|---|---|" + "---|" * len(sets))
    for k, t in trees.items():
        fid = [float((tree_policy(t, d) == model.choose(d)).mean()) for d in sets.values()]
        md.append(f"| depth {k} | {t.get_n_leaves()} | {len(used_features(t))} | " + " | ".join(f"{x:.1%}" for x in fid) + " |")
    md.append("\n**Depth-3 tree (the certified policy):**\n```\n" + export_text(trees[3], feature_names=FEATURES, decimals=2) + "```\n")
    md.append("Outcome of the tree as a policy vs L2 (L* = 1 day):\n")
    md.append("| set | policy | lost (days) | violation | added inventory (EUR) | acted |")
    md.append("|---|---|---|---|---|---|")
    for s, d in sets.items():
        for name, ch in [("L2", model.choose(d)), ("tree depth 3", tree_policy(trees[3], d)),
                         ("tree depth 4", tree_policy(trees[4], d))]:
            o = outcome(d, ch, 1.0)
            md.append(f"| {s} | {name} | {o['lost_days']:.3f} | {o['violation']:.1%} | {o['added_inv_eur']:,.0f} | {o['acted']:.0%} |")

    # ---- stability over bootstrap refits ----
    rng = np.random.default_rng(SEED)
    roots, feats, preds = [], [], []
    for b in range(a.boot):
        bt = tr.iloc[rng.integers(0, len(tr), len(tr))]
        mb = L2().fit(bt, cal)
        t = distil(mb, pool, 3)
        roots.append(FEATURES[t.tree_.feature[0]])
        feats.append(set(used_features(t)))
        preds.append({s: tree_policy(t, d).values for s, d in sets.items()})
    ref = set(used_features(trees[3]))
    jac = [len(f & ref) / len(f | ref) for f in feats]
    md.append(f"\n## Stability over {a.boot} bootstrap refits of the whole pipeline\n")
    md.append(f"- root split feature: {pd.Series(roots).value_counts().to_dict()} (reference tree: {FEATURES[trees[3].tree_.feature[0]]})")
    md.append(f"- Jaccard similarity of the feature set with the reference tree: median {np.median(jac):.2f}, min {min(jac):.2f}")
    md.append(f"- features in every bootstrap tree: {sorted(set.intersection(*feats))}")
    for s, d in sets.items():
        ref_pred = tree_policy(trees[3], d).values
        agree = [float((p[s] == ref_pred).mean()) for p in preds]
        md.append(f"- {s}: bootstrap trees agree with the reference tree on {np.median(agree):.1%} of episodes (median; min {min(agree):.1%})")

    # ---- SHAP of the L1 impact model ----
    l1 = L1().fit(tr, cal)
    ex = shap.TreeExplainer(l1.point)
    imp = {}
    for s, d in sets.items():
        sv = ex.shap_values(d[FEATURES])
        imp[s] = pd.Series(np.abs(sv).mean(axis=0), index=FEATURES)
    imp = pd.DataFrame(imp)
    imp.to_csv(os.path.join(a.out, "l3_shap_importance.csv"))
    top = imp["normal 2 held-out"].sort_values(ascending=False).index[:10]
    md.append("\n## What drives the impact prediction (L1, mean |SHAP|, days of demand)\n")
    md.append("| feature | " + " | ".join(sets) + " |")
    md.append("|---|" + "---|" * len(sets))
    for f in top:
        md.append(f"| {f} | " + " | ".join(f"{imp.at[f, s]:.3f}" for s in sets) + " |")
    md.append("\nRank correlation of the importances with the build year (all features):")
    for s in list(sets)[1:]:
        md.append(f"- {s}: Spearman {spearmanr(imp['normal 2 held-out'], imp[s]).correlation:.2f}")
    with open(os.path.join(a.out, "l3_results.md"), "w") as fh:
        fh.write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
