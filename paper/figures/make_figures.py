"""Figures for the INCOM 2027 paper, built only from the result files of the pipeline (nothing typed in).

  fig1_framework      the evidence-first pipeline: data -> twin (Python = UPPAAL) -> disruptions -> L1-L4
  fig2_validation     cumulative F12 sales and transfers: twin (median, 5-95 % band, 50 seeds) vs the recorded game
  fig3_resilience     Phase E: extra lost demand per disruption level, per run (same physics, same player group, different decisions)
  fig4_l1_coverage    L1: prediction error and conformal coverage, in the build year and under shift
  fig5_l2_frontier    L2: lost demand vs added inventory capital, per policy
  fig6_tree           L3: the certified decision tree (normal 2)
  fig7_certificates   L4: certified service level and harm, Python episodes and UPPAAL model (stochastic mirror)

Sizes follow the IFAC two-column format (column 8.4 cm, page 17.4 cm), Times-metric font, embedded fonts.
Colour follows the entity in every figure: AI policy blue, players grey, lookup rule orange, oracle hollow black,
fixed actions light grey (palette validated with the dataviz validator; aqua only with direct labels).

Usage:
    python make_figures.py [--out .] [--seeds 50]
"""
import argparse
import json
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402
from scipy.stats import beta  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "model", "twin"))
sys.path.insert(0, os.path.join(ROOT, "model", "ai"))
sys.path.insert(0, os.path.join(ROOT, "model", "uppaal"))

COL, PAGE = 3.31, 6.85                     # inches: 8.4 cm column, 17.4 cm page
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
GREY, LIGHT, INK, INK2, GRID = "#6b6a65", "#c9c8c2", "#0b0b0b", "#52514e", "#e6e5e0"
RUNS = ["normal_2", "fraud_2", "fraud_3"]
YEAR = {"normal_2": "Y1 (build run)", "fraud_2": "Y2", "fraud_3": "Y3"}

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Liberation Serif", "Times New Roman", "DejaVu Serif"],
    "font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
    "legend.fontsize": 6.5, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.5, "axes.axisbelow": True, "axes.spines.top": False,
    "axes.spines.right": False, "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.dpi": 300,
    "legend.frameon": False, "figure.facecolor": "white", "axes.facecolor": "white"})


def save(fig, out, name):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(out, f"{name}.{ext}"), bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print("wrote", name)


# ---------------------------------------------------------------------------------------------------- fig 1
def fig_framework(out):
    fig, ax = plt.subplots(figsize=(PAGE, 1.55))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 22)
    ax.axis("off")

    def box(x, y, w, h, title, body, edge=INK2, fill="white"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=0.8",
                                    linewidth=0.7, edgecolor=edge, facecolor=fill))
        ax.text(x + w / 2, y + h - 1.6, title, ha="center", va="top", fontsize=6.6, fontweight="bold", color=INK)
        ax.text(x + w / 2, y + h - 4.6, body, ha="center", va="top", fontsize=5.6, color=INK2, linespacing=1.25)

    def arrow(x0, x1, y=11):
        ax.annotate("", xy=(x1, y), xytext=(x0, y), arrowprops=dict(arrowstyle="-|>", lw=0.7, color=INK2))

    box(0.5, 2, 14.5, 18, "ERPsim SAP data", "3 runs of one game,\nsame company and\nplayer group\n(Y1 build; Y2, Y3)\n+ USAID, DataCo")
    arrow(15.3, 16.9)
    box(17.2, 2, 15, 18, "Evidence first", "cleaning rules,\nevidence ledger,\n17 structure checks,\nMRP replica,\nprices (VBAP, EKPO)")
    arrow(32.5, 34.1)
    box(34.4, 2, 16.5, 18, "Validated twin", "Python twin and\ngenerated UPPAAL\nmodel (591/591\nmirror configs);\nvalidation on Y2, Y3")
    arrow(51.2, 52.8)
    box(53.1, 2, 13.5, 18, "Disruptions", "E1–E5 sampled\nwithin evidence\nbounds; only the\nplayers' 3 levers")
    arrow(66.9, 68.5)
    w = 7.25
    labels = [("L1", "predict", "conformal\nbounds"), ("L2", "decide", "risk-\nbounded"),
              ("L3", "explain", "tree,\nSHAP"), ("L4", "guarantee", "Clopper–\nPearson\nbounds")]
    for i, (k, t, b) in enumerate(labels):
        x = 68.8 + i * (w + 0.55)
        box(x, 2, w, 18, k, f"{t}\n\n{b}", edge=BLUE)
    ax.text(68.8 + 2 * (w + 0.55) - 0.3, 21.4, "AI layers (built on Y1, tested on later runs Y2, Y3)",
            ha="center", va="bottom", fontsize=6, color=BLUE)
    save(fig, out, "fig1_framework")


# ---------------------------------------------------------------------------------------------------- fig 2
def fig_validation(out, seeds):
    from twin import Twin
    fig, axes = plt.subplots(2, 3, figsize=(PAGE, 2.75), sharex="col")
    for j, run in enumerate(RUNS):
        inp = json.load(open(os.path.join(ROOT, "model", "twin", "inputs", f"{run}.json")))
        rec = inp["recorded"]
        days = np.arange(inp["days"]["first"] - 1, inp["days"]["last"] + 1)
        sims = [Twin(inp, seed=s, demand_mode="replay", policy="replay", push_rule="replay_deferred").run()
                .set_index("day") for s in range(seeds)]
        for i, (col, key, label) in enumerate([("sales", "daily_sales", "sales"),
                                               ("transferred", "daily_transfers", "transfers")]):
            ax = axes[i, j]
            r = pd.Series({d: rec[key].get(str(d), 0.0) for d in days}).cumsum() / 1e3
            sim = pd.concat([s[col].cumsum() for s in sims], axis=1) / 1e3
            lo, med, hi = sim.quantile(0.05, axis=1), sim.median(axis=1), sim.quantile(0.95, axis=1)
            ax.fill_between(sim.index, lo, hi, color=BLUE, alpha=0.18, linewidth=0, label="twin 5–95 %")
            ax.plot(sim.index, med, color=BLUE, lw=1.2, label="twin median")
            ax.plot(r.index, r.values, color=INK, lw=0.9, ls=(0, (3, 2)), label="recorded game")
            a1 = float((med - r.reindex(med.index)).abs().max() / r.iloc[-1])
            ax.text(0.03, 0.92, f"max deviation {a1:.1%} of year total", transform=ax.transAxes, fontsize=6,
                    color=INK2, va="top")
            if i == 0:
                ax.set_title(YEAR[run])
            if j == 0:
                ax.set_ylabel(f"cum. {label} (k units)")
            if i == 1:
                ax.set_xlabel("game day")
    axes[0, 0].legend(loc="lower right", handlelength=1.6)
    fig.tight_layout(h_pad=0.6, w_pad=0.8)
    save(fig, out, "fig2_validation")


# ---------------------------------------------------------------------------------------------------- fig 3
def fig_resilience(out):
    rows = []
    for run in RUNS:
        for line in open(os.path.join(ROOT, "model", "twin", "disruptions", f"{run}_impact.md")):
            if line.startswith("| E"):
                c = [x.strip() for x in line.split("|")]
                m = re.match(r"([+-]?[\d,]+) \[([+-]?[\d,]+)\]", c[5])
                rows.append({"run": run, "dis": c[1], "sev": c[2], "med": float(m.group(1).replace(",", "")),
                             "p95": float(m.group(2).replace(",", "")), "share": float(c[6].rstrip("%")) / 100})
    d = pd.DataFrame(rows)
    d = d[~d.sev.str.contains("STRESS")]
    short = {"median late shipment (+0.12 x lead)": "E1 supplier delay q50", "severe (+0.75 x lead)": "E1 supplier delay q90",
             "extreme (+1.0 x lead)": "E1 supplier delay q95", "wheat receipts: 4.1 % blocked, +2 d": "E2 quality, wheat",
             "all food receipts: 4.1 % blocked, +2 d": "E2 quality, all food", "3 days": "E3 stoppage 3 d",
             "10 days": "E3 stoppage 10 d", "25 days": "E3 stoppage 25 d", "surge +19 % for a month": "E4 surge +19 %",
             "+1 day": "E5 transit +1 d", "+4 days": "E5 transit +4 d"}
    d["label"] = d.sev.map(short)
    order = list(short.values())
    fig, axes = plt.subplots(1, 3, figsize=(PAGE, 2.35), sharey=True, sharex=True)
    for j, run in enumerate(RUNS):
        ax = axes[j]
        g = d[d.run == run].set_index("label").reindex(order)
        y = np.arange(len(order))[::-1]
        for yy, (_, r) in zip(y, g.iterrows()):
            ax.plot([r.med / 1e3, r.p95 / 1e3], [yy, yy], color=LIGHT, lw=1.6, solid_capstyle="round", zorder=1)
            ax.scatter([r.p95 / 1e3], [yy], s=10, color="white", edgecolor=GREY, linewidth=0.8, zorder=2)
            ax.scatter([r.med / 1e3], [yy], s=14, color=BLUE, zorder=3)
            ax.text(1.02, yy, f"{r.share:.0%}", va="center", ha="left", fontsize=5.8, color=INK2,
                    transform=ax.get_yaxis_transform(), clip_on=False)
        ax.set_title(YEAR[run])
        ax.set_xlim(-5, 180)
        ax.text(1.02, len(order) - 0.4, "share\nhit", ha="left", va="bottom", fontsize=5.8, color=INK2,
                transform=ax.get_yaxis_transform(), clip_on=False)
        ax.set_yticks(y)
        ax.set_yticklabels(order)
        ax.set_xlabel("extra lost demand (thousand units)")
        ax.grid(axis="y", visible=False)
    axes[0].scatter([], [], s=14, color=BLUE, label="median")
    axes[0].scatter([], [], s=10, color="white", edgecolor=GREY, label="95th percentile")
    axes[0].legend(loc="upper right", handletextpad=0.2)
    fig.tight_layout(w_pad=2.2)
    save(fig, out, "fig3_resilience")


# ---------------------------------------------------------------------------------------------------- fig 4
def fig_l1(out):
    p = pd.read_csv(os.path.join(ROOT, "model", "ai", "results", "l1_primary.csv"))
    a = pd.read_csv(os.path.join(ROOT, "model", "ai", "results", "l1_ablation.csv"))
    names = {"normal 2 held-out (interior)": "Y1 (build run)", "fraud 2 (policy shift)": "Y2 (later run)",
             "fraud 3 (policy shift)": "Y3 (later run)", "STRESS, all years (severity shift)": "beyond evidence"}
    p["name"] = p.set.map(names)
    a["name"] = a.set.map(names)
    y = np.arange(len(p))[::-1]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(PAGE, 2.1), sharey=True, gridspec_kw={"width_ratios": [1, 1.25]})
    models = [("gbm (notice+state)", "notice + state (L1)", BLUE, "o"),
              ("gbm-notice", "notice only", ORANGE, "s")]
    for k, (m, lab, col, mk) in enumerate(models):
        v = a[a.model == m].set_index("name").reindex(p.name).MAE_days.values
        ax1.scatter(v, y + (0.12 if k == 0 else -0.12), s=16, color=col, marker=mk, label=lab, zorder=3)
    ax1.scatter(p.MAE_type_mean_days, y, s=16, color="white", edgecolor=GREY, marker="D", linewidth=0.8,
                label="per-type mean", zorder=2)
    ax1.set_yticks(y)
    ax1.set_yticklabels(p.name)
    ax1.set_xlabel("mean absolute error (days of demand)")
    ax1.set_xlim(0, 1.35)
    ax1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=2, handletextpad=0.2, columnspacing=1.0)
    ax1.set_title("(a) impact prediction error")
    ax1.grid(axis="y", visible=False)
    ax2.axvline(90, color=INK2, lw=0.7, ls=(0, (2, 2)))
    ax2.set_ylim(y.min() - 0.45, y.max() + 0.75)
    ax2.text(89.6, y.max() + 0.5, "nominal 90 %", fontsize=5.8, color=INK2, va="center", ha="right")
    for k, (pre, lab, col, mk) in enumerate([("cov_cqr", "built on normal 2", BLUE, "o"),
                                             ("cov_recal", "recalibrated on 100 target runs", AQUA, "s")]):
        off = 0.12 if k == 0 else -0.12
        ax2.scatter(p[pre] * 100, y + off, s=16, color=col, marker=mk, label=lab, zorder=3)
        ax2.scatter(p[f"{pre}_worst_type"] * 100, y + off, s=13, color="white", edgecolor=col, marker=mk,
                    linewidth=0.8, zorder=3)
        for yy, a_, b_ in zip(y + off, p[f"{pre}_worst_type"] * 100, p[pre] * 100):
            ax2.plot([a_, b_], [yy, yy], color=col, lw=0.7, alpha=0.6, zorder=2)
    ax2.scatter([], [], s=13, color="white", edgecolor=GREY, label="worst disruption type (hollow)")
    ax2.set_xlim(48, 100)
    ax2.set_xlabel("coverage of the 90 % upper bound (%)")
    ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=2, handletextpad=0.2, columnspacing=1.0)
    ax2.set_title("(b) conformal coverage under shift")
    ax2.grid(axis="y", visible=False)
    fig.tight_layout(w_pad=0.8)
    save(fig, out, "fig4_l1_coverage")


# ---------------------------------------------------------------------------------------------------- fig 5
def fig_l2(out):
    from common import ACTIONS, load
    res = os.path.join(ROOT, "model", "ai", "results")
    comp = pd.read_csv(os.path.join(res, "l2_comparison.csv"))
    tr = pd.read_csv(os.path.join(res, "l2_transfer.csv"))
    fig, axes = plt.subplots(1, 3, figsize=(PAGE, 2.05))
    perm = np.random.default_rng(2027).permutation(2000)
    for j, run in enumerate(RUNS):
        ax = axes[j]
        if run == "normal_2":
            g = comp[comp.set == "normal 2 held-out"]
            fixed = g[g.policy.str.startswith("always")]
            fx, fy = fixed.added_inv_eur / 1e3, fixed.lost_days
            pts = {"players": g[g.policy.str.startswith("players")].iloc[0],
                   "lookup rule": g[g.policy.str.startswith("type-rule")].iloc[0],
                   "L2": g[g.policy == "**L2 (conformal, risk-constrained)**"].iloc[0],
                   "oracle": g[g.policy.str.startswith("oracle")].iloc[0]}
            title = "Y1 held-out (build run)"
        else:
            rem = load(run).iloc[perm[400:]]
            fx = pd.Series([rem[f"addinv_{a}"].mean() / 1e3 for a in ACTIONS[1:]])
            fy = pd.Series([rem[f"y_tot_{a}"].mean() for a in ACTIONS[1:]])
            a_ = tr[(tr.set == run) & tr.variant.str.startswith("adapted")]
            b_ = tr[(tr.set == run) & tr.variant.str.startswith("built on normal 2")]
            pts = {"players": a_[a_.policy.str.startswith("players")].iloc[0],
                   "lookup rule": a_[a_.policy == "type-rule"].iloc[0],
                   "L2 built on Y1": b_[b_.policy == "L2"].iloc[0],
                   "L2": a_[a_.policy == "L2"].iloc[0],
                   "oracle": a_[a_.policy == "oracle"].iloc[0]}
            title = f"{YEAR[run]} (later run; L2 adapted)"
        ax.scatter(fx, fy, s=12, color=LIGHT, zorder=2, label="fixed actions")
        style = {"players": dict(color=GREY, marker="o", s=22), "lookup rule": dict(color=ORANGE, marker="s", s=20),
                 "L2": dict(color=BLUE, marker="o", s=30),
                 "L2 built on Y1": dict(color="white", edgecolor=BLUE, marker="o", s=26, linewidth=1.0),
                 "oracle": dict(color="white", edgecolor=INK, marker="*", s=42, linewidth=0.8)}
        if "L2 built on Y1" in pts:
            p0, p1 = pts["L2 built on Y1"], pts["L2"]
            ax.annotate("", xy=(p1.added_inv_eur / 1e3, p1.lost_days), xytext=(p0.added_inv_eur / 1e3, p0.lost_days),
                        arrowprops=dict(arrowstyle="-|>", lw=0.7, color=BLUE, shrinkA=4, shrinkB=4))
        offs = {"players": (4, -9), "L2 built on Y1": (5, 2), "L2": (5, 3), "lookup rule": (-4, 5),
                "oracle": (5, 2)}
        has = {"lookup rule": "right"}
        for name, r in pts.items():
            ax.scatter(r.added_inv_eur / 1e3, r.lost_days, zorder=4, label=name, **style[name])
            dx, dy = offs[name]
            ax.annotate(name, (r.added_inv_eur / 1e3, r.lost_days), xytext=(dx, dy), textcoords="offset points",
                        fontsize=6.2, color=INK, ha=has.get(name, "left"))
        ax.set_title(title)
        ax.set_xlabel("added inventory capital (k€)")
        if j == 0:
            ax.set_ylabel("lost demand, 60 days\n(days of demand)")
        ax.set_xlim(left=-15)
        ax.margins(y=0.14)
    h, l = axes[1].get_legend_handles_labels()
    lab = {"L2": "L2 (Y1: built on Y1; Y2, Y3: adapted)", "L2 built on Y1": "L2 built on Y1, not adapted"}
    fig.legend(h, [lab.get(x, x) for x in l], loc="upper center", ncol=6, bbox_to_anchor=(0.5, 1.06),
               handletextpad=0.2, columnspacing=1.0)
    fig.tight_layout(w_pad=0.8)
    save(fig, out, "fig5_l2_frontier")


# ---------------------------------------------------------------------------------------------------- fig 6
FEAT_NAME = {"type_E3": "line stoppage?", "e4_factor": "surge factor", "plant_days": "plant stock (days)",
             "fg_cover": "finished-goods cover (days)", "queue_f12_days": "F12 queue (days)",
             "dc_cover_West": "West DC cover (days)", "dc_cover_North": "North DC cover (days)",
             "dc_cover_South": "South DC cover (days)", "dc_min_cover": "lowest DC cover (days)",
             "min_cover_f12_components": "lowest F12 component cover (days)"}
ACT_NAME = {"none": "no response", "po5": "buffer 5 d", "po10": "buffer 10 d",
            "fg": "extra batch", "ship": "rebalance DCs", "prio": "line priority",
            "fg+prio": "batch + priority", "po10+fg+prio": "buffer + batch\n+ priority"}


def fig_tree(out):
    from common import FEATURES, load
    t = json.load(open(os.path.join(ROOT, "model", "ai", "results", "tree_normal_2.json")))
    X = load("normal_2", cert=True)[FEATURES].values
    reach = np.zeros(len(t["feature"]))
    for x in X:
        n = 0
        reach[n] += 1
        while t["feature"][n] >= 0:
            n = t["left"][n] if x[t["feature"][n]] <= t["threshold"][n] else t["right"][n]
            reach[n] += 1
    share = reach / len(X)
    pos, leaves = {}, []

    def layout(n, depth):
        if t["feature"][n] < 0:
            pos[n] = (len(leaves), depth)
            leaves.append(n)
            return pos[n][0]
        a = layout(t["left"][n], depth + 1)
        b = layout(t["right"][n], depth + 1)
        pos[n] = ((a + b) / 2, depth)
        return pos[n][0]
    layout(0, 0)
    fig, ax = plt.subplots(figsize=(PAGE, 2.6))
    ax.axis("off")
    W = len(leaves) - 1
    sx = lambda v: v / W * 100
    sy = lambda dpt: 100 - dpt * 29
    stag = {n: (-17 if i % 2 else 0) for i, n in enumerate(leaves)}
    for n, (x, dpt) in pos.items():
        if t["feature"][n] >= 0:
            for child, lab in ((t["left"][n], "no" if FEATURES[t["feature"][n]] == "type_E3" else "≤"),
                               (t["right"][n], "yes" if FEATURES[t["feature"][n]] == "type_E3" else ">")):
                cx, cd = pos[child]
                cy = sy(cd) + stag.get(child, 0)
                ax.plot([sx(x), sx(cx)], [sy(dpt) - 4, cy + 5], color=GREY, lw=0.8, zorder=1)
                ax.text((sx(x) + sx(cx)) / 2, (sy(dpt) - 4 + sy(cd) + 5) / 2, lab, fontsize=6.5, color=INK, fontweight="bold",
                        ha="center", va="center", bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none"))
    for n, (x, dpt) in pos.items():
        f = t["feature"][n]
        if f >= 0:
            name = FEAT_NAME.get(FEATURES[f], FEATURES[f])
            txt = name if FEATURES[f] == "type_E3" else f"{name}\n≤ {t['threshold'][n]:.2f}"
            ax.text(sx(x), sy(dpt), txt, ha="center", va="center", fontsize=6.2, color=INK,
                    bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=INK2, lw=0.6))
        else:
            act = t["actions"][t["action"][n]]
            col = GREY if act == "none" else BLUE
            ax.text(sx(x), sy(dpt) + stag[n], f"{ACT_NAME[act]}\n{share[n]:.0%} of episodes", ha="center", va="center",
                    fontsize=5.9, color="white" if act != "none" else INK,
                    bbox=dict(boxstyle="round,pad=0.35", fc=col if act != "none" else "#f0efec",
                              ec=col, lw=0.6))
    ax.set_xlim(-8, 108)
    ax.set_ylim(sy(3) - 28, 108)
    save(fig, out, "fig6_tree")


# ---------------------------------------------------------------------------------------------------- fig 7
def smc_values(runs=2000):
    path = os.path.join(ROOT, "model", "uppaal", "smc_mirror.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    from crosscheck import smc
    rows = []
    for run in RUNS:
        for pol in ("players", "tree"):
            p, lo, hi = smc(os.path.join(ROOT, "model", "uppaal", f"V12_{run}_ai_{pol}.xml"), runs)
            rows.append({"run": run, "policy": pol, "p": p, "lo": lo, "hi": hi, "runs": runs})
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return df


def cp(k, n):
    return (beta.ppf(0.025, k, n - k + 1) if k > 0 else 0.0, beta.ppf(0.975, k + 1, n - k) if k < n else 1.0)


def fig_certificates(out):
    c = pd.read_csv(os.path.join(ROOT, "model", "ai", "results", "l4_certificates.csv"))
    m = smc_values()
    # rows: (label, l4 set, tree policy name, mirror run or None)
    rows = [("Y1 (build run)", "normal 2, independent certification sample", "**tree (explainable, certified)**", "normal_2"),
            ("Y2, tree built on Y1", "fraud 2, other 1,600 episodes", "tree built on normal 2", None),
            ("Y2, adapted tree", "fraud 2, other 1,600 episodes", "**adapted tree**", "fraud_2"),
            ("Y3, adapted tree", "fraud 3, other 1,600 episodes", "**adapted tree**", "fraud_3")]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(PAGE, 2.45), gridspec_kw={"width_ratios": [1.5, 1]})
    y0 = np.arange(len(rows))[::-1] * 1.0
    seen = set()
    for j, (lab_row, s, pt, mrun) in enumerate(rows):
        for k, (pol, col, lab) in enumerate([("players (no response)", GREY, "players"), (pt, BLUE, "tree")]):
            r = c[(c.set == s) & (c.policy == pol)].iloc[0]
            lo, hi = cp(round(r.service * r.n), r.n)
            yy = y0[j] + (0.30 if k == 0 else -0.02)
            ax1.plot([lo * 100, hi * 100], [yy, yy], color=col, lw=1.4, solid_capstyle="round")
            key = f"{lab}, Python episodes"
            ax1.scatter([r.service * 100], [yy], s=18, color=col, zorder=3, label=key if key not in seen else None)
            seen.add(key)
            if mrun is not None:
                mm = m[(m.run == mrun) & (m.policy == ("players" if k == 0 else "tree"))].iloc[0]
                ym = yy - 0.14
                ax1.plot([mm.lo * 100, mm.hi * 100], [ym, ym], color=col, lw=0.8, alpha=0.7)
                key = f"{lab}, generated UPPAAL model (Python mirror)"
                ax1.scatter([mm.p * 100], [ym], s=15, color="white", edgecolor=col, linewidth=0.9, zorder=3,
                            label=key if key not in seen else None)
                seen.add(key)
            if k == 1:
                h = c[(c.set == s) & (c.policy == pol)].iloc[0]
                ax2.barh(y0[j], h.harm_hi * 100, height=0.32, color=BLUE, alpha=0.85)
                ax2.text(h.harm_hi * 100 + 0.2, y0[j], f"≤ {h.harm_hi:.1%}  (observed {h.harm:.1%})",
                         va="center", fontsize=5.9, color=INK)
    ax1.set_yticks(y0)
    ax1.set_yticklabels([r[0] for r in rows])
    ax1.set_xlabel("P(60-day loss ≤ 1 day of demand), %, two-sided 95 % Clopper–Pearson")
    ax1.legend(loc="lower center", ncol=2, handletextpad=0.2, columnspacing=0.8, bbox_to_anchor=(0.5, 1.10))
    ax1.set_title("(a) service level", pad=34)
    ax1.grid(axis="y", visible=False)
    ax2.set_yticks(y0)
    ax2.set_yticklabels([])
    ax2.set_xlim(0, 10)
    ax2.set_xlabel("P(tree loses > 0.05 days more than players), %")
    ax2.set_ylim(ax1.get_ylim())
    ax2.set_title("(b) harm (upper bound of two-sided 95 % CI)", pad=34)
    ax2.grid(axis="y", visible=False)
    fig.tight_layout(w_pad=0.8)
    save(fig, out, "fig7_certificates")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=HERE)
    ap.add_argument("--seeds", type=int, default=50)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    figs = {"1": lambda: fig_framework(a.out), "2": lambda: fig_validation(a.out, a.seeds),
            "3": lambda: fig_resilience(a.out), "4": lambda: fig_l1(a.out), "5": lambda: fig_l2(a.out),
            "6": lambda: fig_tree(a.out), "7": lambda: fig_certificates(a.out)}
    for k, f in figs.items():
        if not a.only or k in a.only:
            f()


if __name__ == "__main__":
    main()
