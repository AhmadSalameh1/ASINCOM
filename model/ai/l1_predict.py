"""L1 predict: the impact of a notified disruption, with a distribution-free upper bound (conformal prediction).

Target: extra lost demand in the 60 days from the notice (vs the same-seed run without the disruption), under the
players' decisions (open loop), in days of demand. Secondary target: whether there is any extra loss.

Protocol (fixed before any test result was seen; models and hyperparameters are not tuned on test data):
  build      normal 2 episodes: 60 % train, 20 % calibration (the calibration year of the twin)
  test       normal 2 held-out 20 % (interior); fraud 2 and fraud 3 (later runs of the same group: different decisions and lead times:
             a real distribution shift); STRESS episodes (severity beyond the evidence)
  supplement leave-one-year-out: build on two years, test on the third
Models
  type-mean   the per-disruption-type mean from training (what the Phase E impact table alone would say)
  ridge       linear, notice + state
  gbm-notice  gradient boosting, disruption notice only
  gbm-state   gradient boosting, plant state only
  gbm         gradient boosting, notice + state (the L1 model)
Upper bound at 90 % (one-sided; what L2 needs)
  CQR           quantile model (alpha 0.9) + split-conformal correction from the calibration set
  Mondrian CQR  correction per disruption type
  weighted CQR  covariate-shift weights (Tibshirani et al. 2019) from a classifier that separates the
                calibration states from the (unlabelled) test states
  recalibrated  CQR correction recomputed from 100 labelled episodes of the target set; coverage on the rest

Usage:
    python l1_predict.py [--out results]
"""
import argparse
import json
import os
import warnings

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier, LGBMRegressor
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from common import FEATURES, NOTICE, RUNS, SEED, STATE, TYPES, load, split_within

warnings.filterwarnings("ignore")
ALPHA = 0.9
RECAL = 100       # labelled target episodes for recalibration
TARGET = "y_extra_none"
GBM = dict(n_estimators=400, learning_rate=0.03, num_leaves=15, min_child_samples=20, subsample=0.8,
           subsample_freq=1, colsample_bytree=0.8, random_state=SEED, verbose=-1)


def any_loss(d):
    return (d["extra_none"] > 1).astype(int).values


class L1:
    """Point model, quantile model and classifier on notice + state features, plus conformal corrections."""

    def __init__(self, features=FEATURES):
        self.f = features

    def fit(self, tr, cal):
        X, y = tr[self.f], tr[TARGET]
        self.point = LGBMRegressor(**GBM).fit(X, y)
        self.q = LGBMRegressor(objective="quantile", alpha=ALPHA, **GBM).fit(X, y)
        self.clf = LGBMClassifier(**GBM).fit(X, any_loss(tr)) if any_loss(tr).min() != any_loss(tr).max() else None
        self.cal_scores = cal[TARGET].values - self.q.predict(cal[self.f])
        self.cal_type = cal.type.values
        self.cal_X = cal[STATE].values
        self.c = conformal_quantile(self.cal_scores, ALPHA)
        self.c_type = {t: conformal_quantile(self.cal_scores[self.cal_type == t], ALPHA) for t in TYPES}
        return self

    def predict(self, d):
        return self.point.predict(d[self.f])

    def p_any(self, d):
        return self.clf.predict_proba(d[self.f])[:, 1] if self.clf is not None else np.zeros(len(d))

    def upper(self, d, method="cqr", test_states=None):
        q = self.q.predict(d[self.f])
        if method == "cqr":
            return q + self.c
        if method == "mondrian":
            return q + np.array([self.c_type[t] for t in d.type])
        if method == "weighted":
            return q + weighted_corrections(self.cal_X, self.cal_scores, d[STATE].values,
                                            test_states if test_states is not None else d[STATE].values)
        raise ValueError(method)


def conformal_quantile(scores, alpha):
    n = len(scores)
    if n == 0:
        return np.inf
    k = int(np.ceil((n + 1) * alpha))
    return np.inf if k > n else float(np.sort(scores)[k - 1])


def weighted_corrections(cal_X, cal_scores, X, pool_X):
    """Weighted split conformal under covariate shift. w(x) = p(test | x) / p(cal | x), from a logistic
    classifier between the calibration states and a pool of unlabelled test-domain states."""
    Z = np.vstack([cal_X, pool_X])
    lab = np.r_[np.zeros(len(cal_X)), np.ones(len(pool_X))]
    clf = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000)).fit(Z, lab)
    prior = len(cal_X) / len(pool_X)

    def w(A):
        p = np.clip(clf.predict_proba(A)[:, 1], 1e-4, 1 - 1e-4)
        return p / (1 - p) * prior
    wc, wx = w(cal_X), w(X)
    order = np.argsort(cal_scores)
    s, wc = cal_scores[order], wc[order]
    cum = np.cumsum(wc)
    out = np.empty(len(X))
    for i, wt in enumerate(wx):
        tot = cum[-1] + wt
        k = np.searchsorted(cum / tot, ALPHA)              # first score whose cumulative weight >= alpha
        out[i] = s[k] if k < len(s) else np.inf
    return out


def evaluate(name, m, base, d, pool=None):
    y, yb = d[TARGET].values, any_loss(d)
    pred = m.predict(d)
    r = {"set": name, "n": len(d), "share_any_loss": float(yb.mean()), "mean_extra_days": float(y.mean()),
         "MAE_days": float(np.mean(np.abs(pred - y))),
         "MAE_type_mean_days": float(np.mean(np.abs(base.predict(d) - y))),
         "spearman": float(spearmanr(pred, y).correlation) if np.std(y) > 0 else np.nan}
    p = m.p_any(d)
    r["AUC"] = float(roc_auc_score(yb, p)) if 0 < yb.mean() < 1 else np.nan
    r["Brier"] = float(brier_score_loss(yb, p))
    for meth in ("cqr", "mondrian", "weighted"):
        u = m.upper(d, meth, pool)
        cov = y <= u
        r[f"cov_{meth}"] = float(cov.mean())
        r[f"cov_{meth}_worst_type"] = float(min(cov[d.type.values == t].mean() for t in TYPES if (d.type == t).any()))
        r[f"upper_{meth}_mean_days"] = float(np.nanmean(np.where(np.isfinite(u), u, np.nan))) if np.isfinite(u).any() else np.inf
        r[f"inf_{meth}"] = float((~np.isfinite(u)).mean())
    # recalibration: the conformal correction recomputed from RECAL labelled episodes of the target set, coverage
    # measured on the rest (what an operator can do after a first batch of outcomes in a new setting)
    perm = np.random.default_rng(SEED).permutation(len(d))
    rc, rest = d.iloc[perm[:RECAL]], d.iloc[perm[RECAL:]]
    c = conformal_quantile(rc[TARGET].values - m.q.predict(rc[m.f]), ALPHA)
    u = m.q.predict(rest[m.f]) + c
    cov = rest[TARGET].values <= u
    r["cov_recal"] = float(cov.mean())
    r["cov_recal_worst_type"] = float(min(cov[rest.type.values == t].mean() for t in TYPES if (rest.type == t).any()))
    r["upper_recal_mean_days"] = float(u.mean())
    return r


class TypeMean:
    def fit(self, tr):
        self.m = tr.groupby("type")[TARGET].mean().to_dict()
        return self

    def predict(self, d):
        return np.array([self.m.get(t, 0.0) for t in d.type])


def ablation(tr, te_sets):
    rows = []
    variants = {"ridge (notice+state)": None, "gbm-notice": NOTICE, "gbm-state": STATE, "gbm (notice+state)": FEATURES}
    for name, f in variants.items():
        if f is None:
            mdl = make_pipeline(StandardScaler(), Ridge(alpha=1.0)).fit(tr[FEATURES], tr[TARGET])
            pr = lambda d: mdl.predict(d[FEATURES])
        else:
            mdl = LGBMRegressor(**GBM).fit(tr[f], tr[TARGET])
            pr = (lambda d, mdl=mdl, f=f: mdl.predict(d[f]))
        for sname, d in te_sets.items():
            y = d[TARGET].values
            rows.append({"model": name, "set": sname, "MAE_days": float(np.mean(np.abs(pr(d) - y))),
                         "spearman": float(spearmanr(pr(d), y).correlation) if np.std(y) > 0 else np.nan})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    data = {r: load(r) for r in RUNS}
    stress = pd.concat([load(r, True) for r in RUNS], ignore_index=True)
    tr, cal, te = split_within(data["normal_2"])
    m = L1().fit(tr, cal)
    base = TypeMean().fit(tr)
    sets = {"normal 2 held-out (interior)": (te, None), "fraud 2 (policy shift)": (data["fraud_2"], None),
            "fraud 3 (policy shift)": (data["fraud_3"], None), "STRESS, all years (severity shift)": (stress, None)}
    primary = pd.DataFrame([evaluate(k, m, base, d, pool) for k, (d, pool) in sets.items()])
    abl = ablation(tr, {k: v[0] for k, v in sets.items()})
    loyo = []
    for test in RUNS:
        rest = pd.concat([data[r] for r in RUNS if r != test], ignore_index=True)
        t2, c2, _ = split_within(rest, frac=(0.8, 0.2))
        loyo.append(evaluate(f"LOYO test {test}", L1().fit(t2, c2), TypeMean().fit(t2), data[test]))
    loyo = pd.DataFrame(loyo)
    primary.to_csv(os.path.join(a.out, "l1_primary.csv"), index=False)
    abl.to_csv(os.path.join(a.out, "l1_ablation.csv"), index=False)
    loyo.to_csv(os.path.join(a.out, "l1_loyo.csv"), index=False)

    def tbl(df, cols, fmt):
        lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for _, r in df.iterrows():
            lines.append("| " + " | ".join(fmt.get(c, "{}").format(r[c]) for c in cols) + " |")
        return "\n".join(lines)
    f = {c: "{:.3f}" for c in ["MAE_days", "MAE_type_mean_days", "spearman", "AUC", "Brier", "mean_extra_days"]}
    f.update({c: "{:.1%}" for c in ["share_any_loss", "cov_cqr", "cov_cqr_worst_type", "cov_mondrian",
                                    "cov_mondrian_worst_type", "cov_weighted", "cov_weighted_worst_type"]})
    f.update({c: "{:.2f}" for c in ["upper_cqr_mean_days", "upper_mondrian_mean_days", "upper_weighted_mean_days",
                                    "upper_recal_mean_days"]})
    f.update({c: "{:.1%}" for c in ["inf_weighted", "cov_recal", "cov_recal_worst_type"]})
    cols1 = ["set", "n", "share_any_loss", "mean_extra_days", "MAE_days", "MAE_type_mean_days", "spearman", "AUC", "Brier"]
    cols2 = ["set", "cov_cqr", "cov_cqr_worst_type", "upper_cqr_mean_days", "cov_mondrian", "cov_mondrian_worst_type",
             "upper_mondrian_mean_days", "cov_weighted", "inf_weighted", "upper_weighted_mean_days",
             "cov_recal", "cov_recal_worst_type", "upper_recal_mean_days"]
    md = ["# L1 results: disruption impact prediction\n",
          f"Built on normal 2 ({len(tr)} train, {len(cal)} calibration episodes). Target: extra lost demand over 60 days, "
          "in days of demand. Upper bound: one-sided, nominal coverage 90 %.\n",
          "## Accuracy\n", tbl(primary, cols1, f),
          "\n## Upper bound: coverage (target 90 %) and mean bound (days of demand)\n", tbl(primary, cols2, f),
          "\n## Ablation: what the predictor needs to see\n",
          tbl(abl.pivot(index="model", columns="set", values="MAE_days").reset_index().rename_axis(None, axis=1),
              ["model"] + list(sets), {k: "{:.3f}" for k in sets}),
          "\n(MAE in days of demand)\n",
          "\n## Supplement: leave-one-year-out\n", tbl(loyo, cols1, f), "\n", tbl(loyo, cols2, f)]
    with open(os.path.join(a.out, "l1_results.md"), "w") as fh:
        fh.write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
