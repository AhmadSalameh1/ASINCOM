# INCOM 2027 Paper Plan (v2: calibration-uncertainty version)

**Target:** INCOM 2027 (21st IFAC Symposium, Nantes, 28–30 June 2027). Invited session *"From Supply Chain to Shop Floor: Trustworthy AI for Resilient Decision-Making under Disruption"* (organisers: Martinez-Arellano, Himmiche, Aubry, Bouazza).
**Format:** IFAC paper, 6 pages, submitted via PaperCept.
**Deadline:** invited-session paper submission, **14 Dec 2026**. That leaves about 10.5 weeks from 30 Sep 2026.
**Builds on:** `AhmadSalameh1/switchable-sta-prmm`, the switchable STA model in UPPAAL SMC with the PRMM toolchain (V11.4.1).

> **What changed from v1.** v1 trained the AI layers on the single calibrated model. Most of that model's disruption parameters were set by hand, because the ERPsim run used for calibration (normal 2: one game year, played in about 6.5 h) contains no disruptions and so cannot identify them. An AI trained on that one model would learn our calibration choices, and its accuracy would measure how well it copies the simulator, not how well it handles real disruptions. v2 treats those hand-set parameters as **uncertain**. It trains, explains and certifies the AI across an **ensemble of plausible models**, and reports how results change when the model is wrong.

---

## 1. Positioning

### The problem, stated honestly
A digital twin built from scarce data has two kinds of parameters:
- **Data-anchored:** read from ERPsim (network size, bill of materials, batch sizes, capacities, safety thresholds).
- **Assumed:** chosen by the modeller to get plausible behaviour (disruption periods, durations and severities, transport-time ranges, distribution shapes).

AI trained on such a twin inherits the assumed parameters. Most "AI + digital twin for supply chain" papers never separate the two kinds or measure what the assumptions cost.

### The paper's answer
Do not pick one calibration. Define a **credible range** for every assumed parameter, anchored where possible in open real data. Sample an **ensemble** of twins from those ranges. Then:
1. **Predict:** train on part of the ensemble and test on held-out parts. This measures the *sim-to-sim gap*, which stands in for the sim-to-real gap.
2. **Decide:** compare a strategy synthesised on the nominal twin with one synthesised across the ensemble (robust).
3. **Explain:** check whether the explanations (decision-tree rules, SHAP drivers) stay stable across the ensemble. An explanation that flips when an assumed parameter moves should not be trusted.
4. **Certify:** give guarantees that hold *across the credible parameter set*, not only at one point.
5. **Bonus:** global sensitivity analysis shows **which assumed parameters matter most**, so it tells a company which data to collect first.

### Working title
*Trustworthy AI for Supply-Chain Disruption Response under Digital-Twin Calibration Uncertainty: Learning, Explaining and Certifying on an Ensemble of Stochastic Timed Automata*

Shorter alternative: *When the Twin Is Uncertain: Robust, Explainable and Certified AI for Supply-Chain Resilience*

### Pitch for the professor (ready to send)
> The model's structure and quantities are calibrated from one ERPsim game year (the normal 2 run), but that run contains no disruptions, so all disruption parameters had to be set by hand, so training the AI layers on this single calibrated model would mean the AI learns our assumptions. Instead, I propose to keep all three layers (prediction, decision, explainability) and add certification, but run them on an ensemble of models sampled from credible ranges of the hand-set parameters, anchored where possible in open real datasets (DataCo, USAID SCMS). Two further game years of the same company (the fraud 2 and fraud 3 runs, same 71 customers) give independent validation data. We then report how much each AI layer degrades when the model is wrong, whether the explanations are stable, and guarantees that hold across the whole credible parameter set. This makes data scarcity and calibration uncertainty the contribution rather than a limitation, and it matches the session's topics: robust learning under data scarcity and distribution shift, uncertainty quantification, XAI, and formal verification/certification.

---

## 2. Calibration from ERPsim data (V12)

V12 is calibrated directly from the SAP tables of the ERPsim runs published by Tritscher et al. (2022). Everything below is produced by `data/derive_calibration.py`. The outputs are in `data/calibration/`: `calibration_normal_2.json` holds every derived quantity, and `across_runs.csv` holds the year-to-year comparison.

### 2.1 The data
| Item | Value |
|---|---|
| Calibration run | **normal 2**: one game year, **12 rounds × 20 days**, with sales on 229 game days (played in about 6.5 h of wall-clock time) |
| Validation runs | **fraud 2** and **fraud 3**: same participant group, **same 71 customers**, same 12 rounds. Documents labelled as fraud are excluded. |
| Game clock | Round and day are decoded from the customer PO number (`VBAK.BSTNK`). Events are placed on the game clock from their wall-clock time (about 58 real seconds per game day). |
| Network | 71 customers, 1 plant, **3 DCs: South 30 customers, North 21, West 20**. Each customer is served by exactly one DC. |
| Product | **AA-F12**: 48 % of units sold in normal 2, sharing the production line with AA-F16 and AA-F15 |
| BOM (per unit) | AA-R02 blueberries 0.30 kg, AA-R05 wheat 0.35 kg, AA-R06 oats 0.35 kg, AA-P01 box ×1, AA-P02 bag ×1 |
| Labelled events in normal 2 | 2 sales promotions (sales orders), 3 scrap events (on purchase orders) |
| Quantity scale | Model quantity = real quantity ÷ 100 |

### 2.2 Derived parameters (normal 2; spread across the three runs in brackets)
| Model element | Derived from | Value (game days / real units) | Across-run CV |
|---|---|---|---|
| Customer inter-order time (F12) | Per-customer gaps between F12 orders | mean 9.8 d, median 8; shifted gamma fit: 1 + Γ(0.88, 10.0) | 0.04 |
| Customer order size (F12) | Order items | mean 477 (≈ 440–530 typical) | 0.06 |
| F12 demand level | Units per game day | 5,796 (4,422–5,796) | 0.15 |
| Raw-material lead time | PO creation → goods receipt | food ingredients median 2.6–2.7 d (1.1–5.2); packaging median 3.9 d (1.0–6.1) | 0.03 (median) |
| Purchase order size | PO items per component | e.g. R02 mean 15.3k, R05 27.0k, R06 29.3k, P01 79.6k | 0.24 |
| Component reorder point | Component stock when a PO is created | e.g. R02 median 22.5k, R05/R06 45k, P01/P02 150k | — |
| Production batch | Production orders for F12 | **bimodal: 16k (10 orders) or 48k (20 orders)**, mean 37.6k | 0.01 |
| Production time | Order release → delivered status | median 4.2 d, q25–q75 2.7–6.1 d | 0.17 |
| Production trigger | Plant F12 stock at order creation | median 0: production is mostly started when plant stock is empty | — |
| Plant → DC transfer size | Stock transfers to DCs | mean 8.3k (7.0k–8.3k) | 0.09 |
| DC replenishment point | DC stock just before an inbound transfer | median 23k (North), 44k (South), … | — |
| DC capacity | Peak DC stock | North 131.8k, South 143.7k, West 137.6k | — |
| Horizon | One game year | 240 game days | — |

### 2.3 Not observable in the data (assumed and varied in the ensemble)
| Element | Why it cannot be derived | Ensemble anchor |
|---|---|---|
| Plant → DC transport time | ERPsim posts transfers as one instantaneous document | Short fixed value, varied over a small range |
| Demand shock **D** | The two labelled promotions did not raise observed sales (0.90× and 0.64× the preceding 20 days); ERPsim sales depend on price and available stock | DataCo daily order bursts |
| Raw shortage **R** | No shortages occur in the run | USAID SCMS late or short deliveries |
| Quality shock **Q** | Scrap events appear only as normal goods receipts; scrapped quantities are not recorded separately | Literature range |
| Transport delay **F** | No downstream delays exist (transfers are instantaneous) | DataCo late-delivery share and excess days |

### 2.4 Resulting taxonomy
- **Data-anchored (fixed):** network, customer-to-DC assignment, BOM, DC capacities, quantity scale.
- **Data-bounded (ensemble range = variation across normal 2, fraud 2 and fraud 3, plus sampling uncertainty):** inter-order time, order size, demand level, lead times, PO sizes, production batch and time, transfer size, reorder points.
- **Assumed (ensemble range from open data and literature):** D, R, Q, F and plant → DC transport time.

### 2.5 Modelling decisions for Ahmad
1. **Time unit.** The data is in game days. Choose the model's resolution, for example 1 tu = ¼ game day, which gives a 960 tu horizon; the lead-time and production spreads need sub-day resolution.
2. **Product scope.** Either model only F12 on a production line with reduced capacity (48 % of line time), or add F16 as a second product. The first option is simpler and keeps the model tractable.
3. **Policies vs parameters.** The reorder points and the production trigger are *player decisions*. Keep them as the nominal policy, and let the L2 decision layer choose alternatives.

**Twin validation (before any AI):** simulate nominal V12 and compare its lead-time, inter-order, production-time and DC-stock distributions with fraud 2 and fraud 3, using two-sample KS tests and quantile coverage.

---

## 3. Method

### Step 0: V12 model (prerequisite)
1. Lift hard-coded distribution parameters into named constants.
2. **Make practices controllable:** change the `const bool ENABLE_P_*` flags into variables set by a `Controller` template on **controllable** edges at each decision epoch (for example each `TimeTicker` day). Disruptions stay **uncontrollable**. The UPPAAL 5.0 build already has TIGA/Stratego.
3. Add a practice **cost** variable (activation plus running cost per practice).
4. **Structural regression check:** before recalibrating, V12 with the V11.4.1 constants and fixed flags must reproduce the V11.4.1 17-query results within CI (CRN seeds). This shows the refactor changed no behaviour. Then apply the Section 2 calibration.

### Step 1: The ensemble
- **Sampling:** Latin hypercube over the assumed ranges, giving about 200 parameter vectors θ₁…θ₂₀₀. Split them into **train (60 %)**, **held-out interior (20 %)** and **held-out extreme corners (20 %)**, the last being the hardest shift.
- **Real-anchored twins:** 3–5 extra θ vectors whose delay and lead-time parameters are fitted from DataCo and USAID (Section 4). These are the "closest to reality" test points.
- **Implementation:** generate one model file per θ with a Python script, or sample θ inside the model at t = 0 with an `Init` template. The second option lets Stratego learn over the ensemble directly (domain randomisation).
- **Global sensitivity:** run Morris screening, then Sobol indices on the main KPIs (service ratio, stockout duration, recovery time). Question answered: *which assumed parameters actually drive resilience outcomes?*

### L1: Predict (early warning under calibration shift)
- **Target:** service ratio drops below 95 %, or a store stocks out, within h ∈ {25, 50} time units. Secondary target: time-to-recovery.
- **Features:** only what a planner observes: stocks, incoming quantities, pending requests, truck states, rolling demand, rolling KPIs. **The θ values are never features**, because a real planner does not know them.
- **Data:** `simulate` traces, about 25 runs per θ, giving roughly 5k training trajectories.
- **Models:** logistic regression as the baseline, then LightGBM.
- **Trust:** split conformal prediction calibrated on train-θ. Measure coverage and set width on held-out interior, extreme corners and real-anchored twins. Compare with adaptive conformal inference (ACI) and weighted conformal.
- **Key result:** a **coverage-vs-shift curve**, showing how coverage decays as θ moves away from the training region (distance in normalised θ space).

### L2: Decide (practice activation)
Policies compared:
1. No practices.
2. The static full portfolio E,A,S,B, the best case from the previous paper.
3. A threshold rule.
4. **Risk-triggered:** activate a practice when L1's conformal upper bound exceeds τ.
5. **Stratego-nominal:** strategy synthesised on nominal θ only.
6. **Stratego-robust:** strategy synthesised over the train ensemble.

- **Objective:** `minE(practice_cost + λ·lost_sales)`, with a service-level safety constraint.
- **Key result:** the performance gap between nominal and robust strategies on held-out θ. This shows the price of a single calibration.

### L3: Explain (and test explanation stability)
- Distil each Stratego strategy into a decision tree (dtControl or CART). Report fidelity, depth and size.
- Use SHAP on the L1 predictor.
- **Stability across the ensemble:**
  - Re-distil or re-fit per θ bootstrap.
  - Report the agreement of tree splits (the same variables and similar thresholds).
  - Report the rank correlation of SHAP importances across θ groups.
- **Claim to test:** "explanations that stay stable across the credible set can be trusted; the ones that flip show where calibration data is needed". Cross-reference with the Sobol results.

### L4: Certify (guarantees across calibration uncertainty)
- Encode the decision tree back into UPPAAL as a controller template. The certified object is then **the explanation itself**.
- **Two-level certificate:**
  1. **Within each θ:** SMC gives `Pr[<=800](<> service_ratio ≥ 95)` with a 95 % Clopper–Pearson interval, reusing the existing 17-query battery and FDR code.
  2. **Across θ:** test on n held-out θ, drawn independently of synthesis. If the lower bound is at least p* in all n, then with confidence 1 − (1 − ε)ⁿ the share of the credible set where the guarantee fails is at most ε. For example, n = 60 gives ε = 5 % at 95 % confidence. Also report the worst case and the 5th percentile.
- **PRMM link:** Level 5 ("benchmark-based effectiveness") is hard-coded to 0 today (`s5_ceiling_derivation.py`). Use the certified robust policy as the **benchmark**. A static portfolio's S5 is then its performance relative to that benchmark, **averaged over the ensemble**, so the maturity score also carries the uncertainty.

### Claimed contributions
1. **A calibration-uncertainty framework for AI on digital twins:** a taxonomy of data-anchored and assumed parameters, an ensemble anchored in open data, and global sensitivity showing which assumptions matter.
2. **Early warning with measured coverage decay** under twin mis-calibration, and adaptive conformal repair.
3. **An explainable-by-construction robust controller:** Stratego strategy → decision tree, with explanation stability measured across the ensemble.
4. **Two-level statistical certificates** (SMC within each twin, binomial across twins) of the explainable controller, plus an **ensemble-based PRMM Level 5**.

### Related work to position against
- RL and ML for inventory and supply chains: usually one simulator and one calibration, with no guarantees.
- **COOL-MC (arXiv 2603.02396, 2026):** verifies and explains RL inventory policies with probabilistic model checking. **Closest competitor; read first.** Differences: timed stochastic model, multiple disruption types, calibration-uncertainty ensemble, conformal layer, PRMM.
- Domain randomisation and robust MDPs (robotics sim-to-real). Borrow the terminology and cite it.
- dtControl / UPPAAL Stratego explainable controllers. Rarely or never applied to supply-chain resilience.
- Himmiche et al., SMC-based robustness of production schedules. This paper is the AI-driven, uncertainty-aware continuation.

---

## 4. Open real datasets and their role

Real data **sets parameter ranges and the real-anchored test twins**. It is never used as direct training data for a policy.

| Dataset | What it gives | Size / period | Licence | Parameters it anchors |
|---|---|---|---|---|
| **DataCo Smart Supply Chain for Big Data Analysis** (Constante, Silva, Pereira, 2019; Mendeley Data DOI 10.17632/8gx2fvg2k6) | Per-order *Days for shipping (real)* vs *(scheduled)*, `Late_delivery_risk`, shipping mode, order dates and quantities | 180,519 orders, 2015–2018 | CC BY 4.0 (as listed; confirm on the page) | **F:** frequency of late deliveries → delay-window frequency; excess-days distribution → trip-time ratio. **D:** burst size and duration of daily order volume. |
| **USAID SCMS Delivery History / Supply Chain Shipment Pricing Data** (data.usaid.gov) | Per-shipment scheduled vs actual delivery dates, vendor, mode | ~10,324 shipments, 2006–2015 | CC BY (USAID) | **T1 range and tail**; **R:** frequency of severely late upstream deliveries |
| *(context)* NY Fed Global Supply Chain Pressure Index | Monthly disruption intensity | 1997– | Public | Motivating figure; justifies the severity range (normal vs 2021-level stress) |

**Unit mapping.** Transfer only **dimensionless** quantities: coefficient of variation, delay/lead-time ratio, share of late shipments, tail index. Rescale them to the model's own time-unit means. State this openly in a limitations sentence.

---

## 5. Figures and tables (fits 6 pages)

1. **Fig. 1:** framework. Parameter taxonomy → ensemble → four layers → certificate.
2. **Fig. 2:** Sobol total-order indices of the assumed parameters on 2–3 KPIs. *Which assumptions matter.*
3. **Fig. 3:** L1 coverage and AUROC vs distance from the training region (interior, corners, real-anchored), split conformal vs ACI.
4. **Table 1:** L2 policies on held-out θ: cost, Pr(service ≥ 95 %) mean / 5th percentile / worst case. Nominal vs robust Stratego is the headline row pair.
5. **Fig. 4:** the distilled robust decision tree (depth ≤ 4) with a split-stability percentage on each node.
6. **Table 2:** two-level certificate for the tree controller vs the static full portfolio, and ensemble PRMM S_final with S5 implemented.

**Success criteria.** Aim for these; report honestly if not reached:
- The robust strategy's 5th-percentile service is clearly above the nominal strategy's on held-out θ, at similar cost.
- L1 coverage holds in the interior, drops on the corners, and ACI recovers most of the drop.
- At least the top tree splits stay stable (≥ 80 % agreement), and their variables line up with the top Sobol parameters.

---

## 6. Timeline (30 Sep → 14 Dec 2026)

| Week | Dates | Work | Deliverable |
|---|---|---|---|
| 1 | 30 Sep–6 Oct | Decide the Section 2.5 modelling choices and set ranges. Send the pitch to the professor. Read COOL-MC. Download DataCo and USAID. | Approved taxonomy table |
| 2 | 7–13 Oct | **V12:** lift hard-coded constants, controllable practices, cost variable, **regression check vs V11.4.1**. | V12 plus regression table |
| 3 | 14–20 Oct | Fit the data-bounded distributions from normal 2 (lead time, inter-order, order size), with year-to-year widths from fraud 2 and fraud 3. **Validate the nominal V12 twin against fraud 2 and fraud 3.** Fit dimensionless statistics from DataCo and USAID for the assumed disruption ranges. Ensemble generator (LHS → model files or `Init` sampling). | Twin-validation table, 200 + 5 θ, generator script |
| 4 | 21–27 Oct | Trace generation. **Morris, then Sobol** sensitivity. | Fig. 2 |
| 5 | 28 Oct–3 Nov | **L1:** training, conformal, ACI, coverage-vs-shift. | Fig. 3 |
| 6–7 | 4–17 Nov | **L2:** Stratego nominal and robust, baselines, risk-triggered policy. **Main risk; see Section 7.** | Table 1 |
| 8 | 18–24 Nov | **L3:** tree distillation, SHAP, stability. **L4:** tree → UPPAAL, two-level certificate, ensemble PRMM S5. | Fig. 4, Table 2 |
| 9 | 25 Nov–1 Dec | Full draft (IFAC template). | Draft v1 to professor |
| 10 | 2–8 Dec | Revise; reproducibility release (tag, Zenodo DOI). | Draft v2 |
| 11 | 9–14 Dec | Polish, then PaperCept submission. | **Submitted** |

Compared with v1, the ensemble adds about one week. Weeks 6–8 are now tighter, so the fallbacks in Section 7 matter.

---

## 7. Risks and fallbacks

| Risk | Likelihood | Fallback |
|---|---|---|
| Stratego does not scale (71 customers, large integers), especially over the ensemble | Medium–high | Use a coarse observation set (discretised stocks, disruption-active flags, day). If it still fails, replace Stratego with a **parametric threshold policy** tuned for the ensemble average or worst case via SMC. The thresholds are then the explanation, and the certification stays the same. |
| Ensemble compute is too heavy (200 θ × runs × queries) | Medium | Cut to 100 θ and 20 runs per θ. Use Morris only, not Sobol. Run in parallel on a lab machine or cluster (`verifyta` is single-threaded, so run one per core). |
| Dimensionless transfer from DataCo and USAID is questioned | Medium | Present the real data as setting *ranges*, not point calibration, and show that conclusions hold across the whole range. That is the purpose of the ensemble. |
| Results look "negative" (robust policy ≈ nominal) | Low–medium | Still publishable: it means the nominal calibration was not decisive for the policy. Sobol explains why. Make sure the extreme corners are extreme enough to show *some* gap. |
| Too much for 6 pages | Medium | Must-haves: Figs 2 and 3 and Table 2 (sensitivity, prediction under shift, certificate). L2 can shrink to "risk-triggered vs static"; keep Stratego-robust for the journal extension. |
| Overlap with the pending journal article | Low | That article covers static practices, one calibration and PRMM. This paper covers adaptive AI, calibration uncertainty and certification. Cite it; reuse only the model and statistics code. |

---

## 8. Tooling and repository layout

- **UPPAAL 5.0 with Stratego** (`verifyta`).
- **Python:** the existing toolchain, plus `pandas`, `scipy` (LHS via `scipy.stats.qmc`), `SALib` (Morris / Sobol), `lightgbm`, `scikit-learn`, `mapie` (conformal), `shap`, `dtcontrol`.

```
model/          V12 controllable + parameterised model; link to V11.4.1 baseline
params/         taxonomy table, ranges, LHS design, real-anchored θ
data/           derive_calibration.py + calibration/ outputs (ERPsim); download + fitting scripts for DataCo / USAID (raw data not committed)
ensemble/       model-file generator, parallel verifyta runner, trace export
traces/         generated trajectories (gitignored; regenerable from seeds)
sensitivity/    Morris / Sobol
l1_predict/     features, training, conformal, coverage-vs-shift
l2_decide/      Stratego queries (nominal / robust), baselines, evaluation
l3_explain/     tree distillation, SHAP, stability metrics
l4_certify/     tree → UPPAAL controller, two-level certificate, ensemble PRMM S5
paper/          IFAC LaTeX + figures
```

---

## 9. Immediate next steps

1. **Ahmad:** go through the taxonomy in Section 2. Mark each parameter as ERPsim, assumed, or tuned-to-match-ERPsim, and write down any ranges you already considered during calibration.
2. Send the professor the pitch in Section 1.
3. Start V12: lift the hard-coded gamma parameters and run the regression check against V11.4.1.
