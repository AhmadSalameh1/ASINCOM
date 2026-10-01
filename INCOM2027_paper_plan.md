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

## 2. Evidence-first model build

**Principle:** every part of the model (entity, flow, rule) and every number in it traces to a row of the **evidence ledger**. Each row gives the source tables and columns, the filter, the method, and the value in all three game years. Nothing enters the model without a ledger ID. Disruptions are added only after the undisrupted model is validated against held-out data.

Pipeline: `data/derive_calibration.py` → `data/calibration/`:
- `evidence_ledger.md` / `.csv`: one row per parameter, with its evidence class
- `cleaning_log.md`: every cleaning rule and what it removed, per run
- `calibration_<run>.json`: every derived quantity, per run

### 2.1 Data
- **Calibration run:** normal 2. One game year (12 months × 20 game days, sales on 229 days).
- **Validation runs:** fraud 2 and fraud 3. Same participant group, same 71 customers, same 12 months. Documents labelled as fraud are excluded.
- **Game clock:** decoded from the customer PO number (`VBAK.BSTNK`). Events are placed on the game clock by their wall-clock time.
- **Scope:** product AA-F12 and its 5 components. Quantity scale 1:100.

### 2.2 Phase A: cleaning (first pass done)
| Rule | What it does | normal 2 |
|---|---|---|
| C0 integrity | Checks for duplicates, rejected orders, deleted POs, reversal movements | none found |
| C1 fraud documents | Drops labelled fraud sales orders and POs | none in normal 2 (12 SO / 5 PO in fraud 2; 29 SO / 5 PO in fraud 3) |
| C2 steady-state window | Demand statistics only from months where every DC ends ≤ 5 % of days with zero stock. Outside it, sales are capped by stock, so **sales ≠ demand**. | months 4–9 (start-up 1–3; end of game 10–12 with stock-outs) |
| C4 pre-start POs | Drops POs created before the first trading tick (game initialisation) from lead times | 2 POs |
| C5 scrap POs | Drops scrap-labelled POs from normal lead times; kept as quality-event evidence | 3 POs |
| C3 promotions | Drops promotion-labelled orders from baseline demand | 23 F12 items |

### 2.3 Evidence classes (from the ledger)
| Class | Meaning | Examples |
|---|---|---|
| **anchored** | Structural fact read from master or transaction data | 71 customers; customer → DC assignment (N 21 / S 30 / W 20); BOM (**run-specific**: fraud 2 uses wheat 0.20 / oats 0.50) |
| **bounded** | Statistical parameter; ensemble range from the three years | inter-order time (mean 8.2 / 10.6 / 9.2 d), order size (491 / 453 / 432), food lead time (1–6 days, median 2 / 2 / 3), production processing (median 1 / 2 / 1.5 d) |
| **policy** | Player decision. Kept as the nominal policy; the L2 decision layer may change it. | reorder points, PO sizes, production batch (16k or 48k), transfer size, peak DC stock (**not a capacity**: 132k / 77k / 58k across years) |
| **unobserved** | Not recorded in the data; assumed and varied | plant → DC transport time (ERPsim transfers are instantaneous) |

### 2.4 Phase B: structure proof (done)
`data/derive_structure.py` → `data/structure/structure_evidence.md`. There are 17 structural claims, each tested in all three years, and the proven structure is drawn as a diagram. What the model must implement:

| Claim | Result (normal 2 / fraud 2 / fraud 3) |
|---|---|
| **B1–B3** Order → delivery → goods issue → invoice is one chain; delivered in full; in the same tick | 100 % / 100 % / 100 % |
| **B4** An order is clipped to the DC stock; the excess is **lost** (no backorders) | sales that empty a DC are much smaller than usual (median 320 vs 482, …) |
| **B5** Each customer is served by one fixed DC | 100 % |
| **B6–B7** Purchasing: requisition → PO → full receipt | 98–100 %; the only short POs were created 3 days before game end |
| **B8** Split receipts occur only in scrap events | 3/3, 2/3, 1/1. One unexplained PO (fraud 2, 4500000018). |
| **B10** Production orders deliver their full quantity | 100 % / 95 % / 89 %; every incomplete order was released in the last 5 days |
| **B11** Components are consumed per BOM | the recipe changes during the game (fraud 2 changed the F12 recipe) → use per-period consumption |
| **B12–B13** Production is a daily flow of ≤ 24,000 units/tick on **one shared line** for all products | 96–98 % of ticks; the rest are batched catch-up postings |
| **B14** Distribution is plant → DC only, as instantaneous transfers; no returns | all transfer documents |
| **B15** The network is closed: produced = to DCs = sold + closing stock | residual 0 in all three years |
| **B16** The game starts with empty stock | every stock path's minimum is 0 |
| **B17** The observed production pause is a **planning gap** (no production started), not a breakdown | 52 / 60 / 25 days |

Cleaning rule **C1a**: the label file lists one fraud-3 PO as `450000015`, a typo for 4500000015.

### 2.5 Phase C–D: build and validate the undisrupted model
- **Build:** a new UPPAAL model (V12). Each constant and distribution carries its ledger ID in a comment.
- **Modelling decisions:** each is justified in `docs/decision_records.md` with its evidence, the result that would overturn it, and the remaining risk.
  - **DR-1 time unit = 1 game day.** 95 % of engine postings fall on day ticks; lead times are whole days; line capacity is 24,000 units per day.
  - **DR-2 F12 in detail, plus the other products as background load on the shared line.** The line is busy on 82–93 % of steady days, so contention is real. Shared components run out on at most 0.8 % of steady days (zero-stock days are start-up and end-of-game effects), so material coupling does not bind.
  - **DR-3 nominal policy = the normal 2 players' decisions.** Validation replays each year's own policy, so it tests the physics.
- **Validation** on fraud 2 and fraud 3 (steady months, their own recipe and policy):
  - lead-time, inter-order, queue, processing and DC-stock distributions (two-sample KS tests, quantile coverage)
  - monthly throughput

### 2.6 Phase E: realistic disruptions
A disruption is admitted only if (a) it acts through a mechanism that exists in the validated model and (b) its frequency, severity and duration come from evidence:

| Disruption | Mechanism in the model | Evidence for its parameters |
|---|---|---|
| **Production stoppage** | Shared line unavailable | **Observed production pauses** (B17: 52 and 60 days without F12 production starts in normal 2 and fraud 2), with the resulting DC stock-outs. They are planning gaps, not breakdowns, but the downstream propagation is real, so they **validate how the model propagates a stoppage**. |
| Supplier delay | Lead-time distribution shifted or scaled | USAID SCMS delivery-delay distribution (dimensionless: delay / planned lead time) |
| Supply shortage | Partial goods receipt | USAID short or partial shipments; literature |
| Demand surge or drop | Customer ordering rate scaled | DataCo order-volume bursts; the price-driven demand variation between the three years |
| Downstream delay | Plant → DC transfer time > 0 | DataCo late-delivery share and excess days |
| Quality loss | Part of a receipt set aside (blocked or held in inspection, never released); late receipt | **Measured:** the 6 labelled scrap events in the three years lose **0.2–4.1 %** of the affected receipt (ledger Q2) and arrive later than normal (Q1) |

Only after this do the AI layers (Section 3) run: predict the effect of injected disruptions, then decide the response.

---

## 3. Method

> **Implemented design (October 2026; details and results in `docs/ai_layers.md`).** The data-backed twin changed what "calibration uncertainty" means, and the method below has been adapted accordingly:
> - **The shift is real, not synthetic.** The three game years are three player teams on the same company. The AI is built on normal 2 and tested on fraud 2 and fraud 3: another team's policy and lead times. That replaces the Latin-hypercube θ ensemble. STRESS episodes (beyond the evidence) add a severity shift.
> - **L1:** gradient boosting on the notice plus the plant state, in dimensionless units, with conformal upper bounds. Results:
>   - Coverage decays under the team shift (88 % → 85 % / 79 %).
>   - Weighted conformal fails (the bounds become infinite).
>   - Recalibration on 100 target outcomes restores about 90 %.
> - **L2:** a risk-constrained choice among the players' three levers: the cheapest action whose conformal bound meets the service limit L*. Results:
>   - It cuts loss by 12 % in its build year.
>   - It does not transfer to another team.
>   - Adapting it with 400 target-twin episodes restores a 15 % gain.
> - **L3:** the policy is distilled into a depth-3 tree. SHAP importance is stable across years even where prediction fails, so **stability is not evidence of transfer**.
> - **L4:** Clopper–Pearson certificates of the tree on independent episodes, for service and for **do-no-harm**.
> - **Stratego and the UPPAAL encoding of the tree** come next. The UPPAAL model (`docs/uppaal.md`) first needs the levers.
>
> The text below is the original plan, kept for reference.


### Step 0: V12 model (prerequisite)
Built from the evidence ledger (Section 2):
1. Build the undisrupted model from the proven flows (Phase B) and ledger values (Phase C).
2. **Practices are controllable:** the model has `Controller` template actions on **controllable** edges at each decision epoch. Disruptions stay on **uncontrollable** edges. The UPPAAL 5.0 build has TIGA/Stratego.
3. Add a practice **cost** variable.
4. Validate the undisrupted model against fraud 2 and fraud 3 (Phase D). Then add the disruption modules (Phase E), and check the production-stoppage module against the observed stoppage episodes.

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
| 1 | 30 Sep–6 Oct | **Phase A** cleaning and evidence ledger (done). Decision records DR-1 to DR-3 (done). **Phase B** structure proof (done). Send the pitch to the professor. Read COOL-MC. | Ledger, cleaning log, flow diagram |
| 2 | 7–13 Oct | **Phase C:** build V12 from the ledger (controllable practices, cost variable, ledger IDs in comments). | V12 model |
| 3 | 14–20 Oct | **Phase D:** validate the undisrupted V12 against fraud 2 and fraud 3. **Phase E:** disruption modules; fit USAID / DataCo statistics; check the stoppage module against the observed episodes. | Validation table, disruption table |
| 4 | 21–27 Oct | Ensemble generator (LHS over bounded and unobserved parameters), trace generation, **Morris then Sobol** sensitivity. | Fig. 2 |
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
data/           derive_calibration.py → calibration/ (evidence ledger, cleaning log, per-run JSON); DataCo / USAID fitting scripts (raw data not committed)
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

1. Decisions DR-1 to DR-3 are recorded in `docs/decision_records.md`. Resolve its open items during Phase D.
2. Phase C: build V12 from the evidence ledger and the proven structure (Section 2.4).
3. Send the professor the pitch (Section 1) together with the evidence-first approach (Section 2).
4. Read COOL-MC (arXiv 2603.02396) for positioning.
