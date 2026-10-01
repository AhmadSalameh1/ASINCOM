# AI layers L1–L4: predict, decide, explain, certify

Code: `model/ai/` (`episodes.py`, `common.py`, `l1_predict.py`, `l2_decide.py`, `l3_explain.py`, `l4_certify.py`, `robustness.py`). Results: `model/ai/results/*.md|csv`. Prices: `data/derive_prices.py` → `data/prices/`.

## 0. What changed in the twin before the AI layers could run (and why)

Two corrections were found while building the AI layers. Both are reported, not hidden.

1. **Stranded plant stock in transfer replay** (validation Amendment 3, `docs/validation_report.md`, round 3).
   - **The symptom:** a "ship the plant stock" lever cut lost demand by 60–90 % and *reduced* inventory. That looked too good.
   - **The cause:** plain replay clips a recorded transfer to the plant stock and never ships the clipped part.
   - **The fix:** deferred replay (the clipped part ships as soon as stock allows). With it, sales are within 1 % in every year and transfers are exact.
   - **What it changes:** Phase E and the B controller comparison were re-run under the corrected rule.
2. **The other products' losses are now logged** (`lost_other`). A lever that gives F12 priority on the shared line must pay for what the other products lose.

## 1. The question and the evidence base

> When a disruption is notified, how bad will it be (L1)? What should the planner do with the levers they actually have (L2)? Can the recommendation be read as a rule (L3)? And what can be **guaranteed** about that rule (L4)?

### Episodes (`episodes.py`)
- **What an episode is:**
  - a game year
  - a start day drawn uniformly over the steady months
  - a seed
  - a disruption drawn **within its evidence bounds**:
    - E1 supplier delay: relative delay from the USAID SCMS late-shipment quantiles, up to q95
    - E2 quality loss: 0.2–4.1 % blocked (ERPsim Q2), one food material or all
    - E3 line stoppage: 1–25 days (B17)
    - E4 demand surge: ×1.05–1.19 (normal 2's steady monthly range)
    - E5 transit delay: 1–4 days (DataCo)
- **STRESS episodes:** go beyond the evidence (E2 25 %, E4 ×1.5) and are used only as a shift test.
- **Runs per episode:** the twin runs once without the disruption, and once under the disruption for each of the **8 response actions**. All runs use the same seed and keyed lead-time streams (common random numbers), so runs differ only by the disruption and the action.
- **Decisions:** the players' recorded decisions plus the response.
- **Outcome window:** 60 days from the notice.
- **Size:**
  - 2,000 episodes per year
  - 600 STRESS episodes per year
  - an independent certification sample of 2,000 normal 2 episodes, from a separate random stream
- **Features:** what a planner observes at the notice, recorded inside the run by an observer, so no future information leaks:
  - component cover
  - the production queue (F12 days, other products' line days, whether the head order is blocked)
  - plant stock
  - DC cover
  - recent losses
  - the transfer backlog
  - the notice itself: type and announced severity
- **All features and targets are dimensionless** (days of demand, days of line capacity, days of cover). The years run at different demand levels (about 8,000 / 6,000 / 4,400 units per day), so a model built on one year has to transfer to another.

### Actions: only the players' three levers (`model/twin/controllers.py`, `ResponseController`)
| Action | Lever | What it does (from the notice day, for 40 days unless stated) |
|---|---|---|
| none | – | the players' recorded plan |
| po5 / po10 | POs | keep available + on-order component stock ≥ 5 / 10 days of recent consumption |
| fg | conversions | one extra F12 order of 24,000 units (one line-day, M6) on the notice day, plus its components |
| ship | transfers | plant stock left after the recorded transfers is shipped, split over the DCs to equalise days of cover |
| prio | conversions | for 20 days, other products' conversions are held while F12 orders wait for the line |
| fg+prio, po10+fg+prio | combinations | |

### Cost side, anchored in the data (`data/prices/prices.md`)
| | normal 2 | fraud 2 | fraud 3 |
|---|---|---|---|
| F12 sales price (PR1) | 4.34 | 4.63 | 4.88 |
| F12 material cost (PR3) | 2.53 | 2.54 | 2.51 |
| margin | 1.81 | 2.09 | 2.37 |

- Component purchase prices come from EKPO (PR2), F12 sales prices from VBAP. Fraud-labelled documents are excluded.
- Two anomalies in fraud 3 (AA-R04 at 4.73; one sales line at 0.99) do not affect PR3: R04 is not in the F12 BOM, and the means are quantity-weighted.
- **The cost of an action is the extra inventory capital it ties up** (material-cost value, mean over 60 days). No holding-cost rate is assumed: the decision rule is a **constraint on service** and a **minimum on capital**, so no money-for-service exchange rate is needed.

## 2. Descriptive result: where the levers can and cannot help
Mean lost demand of all products over 60 days, in days of demand (from `episodes_*.csv.gz`):

| | normal 2 | fraud 2 | fraud 3 |
|---|---|---|---|
| E3 line stoppage, players | 8.55 | 5.08 | 3.34 |
| E3, best action | 8.13 (fg) | 4.96 (po10) | 3.34 (none) |
| E1, E2, E5 (supplier, quality, transit), players | ≤ 0.08 | 0.38–0.61 | ≤ 0.01 |
| E1, E2, E5, best action | ≤ 0.08 | 0.03–0.12 (po10) | ≤ 0.01 |
| E4 surge, players → best | 0.93 → 0.73 (ship) | 0.70 → 0.09 (po10) | 0.04 |
| Players already meet L* = 1 day | 77.7 % | 79.0 % | 90.9 % |
| Best action in hindsight meets L* | 83.5 % | 87.8 % | 92.0 % |

- **The line is the binding constraint in a stoppage.** After a stoppage, every lever only moves the loss between products. Prioritising F12 cuts its loss by about 4k units while the other products lose about 5k more. Hence the objective counts all products.
- **Upstream disruptions hurt fraud 2 through the other products,** and a component buffer (po10) removes almost all of that. In normal 2 and fraud 3, the players' own buffers already absorb them.
- **The room for any decision layer is bounded:** at most +5.8 / +8.8 / +1.1 points of episodes meeting the limit.

## 3. L1 predict (`l1_predict.py`, `results/l1_results.md`)

### Design
- **Target:** extra lost demand caused by the disruption over 60 days (vs the same-seed run without it), under the players' decisions, in days of demand.
- **Protocol:**
  - Built on normal 2: 1,200 train and 400 calibration episodes.
  - Tested on the 400 held-out normal 2 episodes, on fraud 2 and fraud 3 (another team's policy, a real shift), and on STRESS.
  - Model: gradient boosting. The hyperparameters were fixed before testing.

### Results
| | normal 2 held-out | fraud 2 | fraud 3 | STRESS |
|---|---|---|---|---|
| MAE (days) — L1 / per-type mean | **0.22** / 1.20 | 0.78 / 0.86 | 0.51 / 0.82 | 1.12 / 1.21 |
| AUC "any extra loss" | 0.99 | 0.90 | 0.87 | 0.90 |
| 90 % upper bound coverage: CQR (worst type) | 88.0 % (83.1 %) | 84.9 % (65.8 %) | 79.0 % (59.8 %) | 61.2 % (52.4 %) |
| Weighted conformal | 88.0 % | bound infinite in 100 % of episodes | bound infinite in 100 % | infinite in 49 % |
| **Recalibrated on 100 target episodes** (worst type) | 89.7 % (85.5 %) | **88.7 %** (72.2 %) | **89.9 %** (80.4 %) | 87.2 % (74.5 %) |

**Ablation (MAE):**

| | interior | fraud 2 |
|---|---|---|
| notice + state | 0.22 | 0.78 |
| notice only | 0.94 | 0.77 |
| state only | 1.46 | 1.44 |

### Findings
1. **Inside the build year, the predictor must see the plant state.** Adding the state to the notice cuts the error by a factor of 4 (Phase E finding 1, confirmed).
2. **That state knowledge is team-specific.** Under another team's policy, it adds nothing over the notice. Coverage of the conformal bound decays from 88 % to 85 % / 79 % (worst type 60 %).
3. **Importance weighting does not repair a shift this large.** The years' states are nearly separable, so the weighted bound becomes infinite. **Recalibrating the margin on 100 outcomes from the new setting restores about 90 %** marginal coverage at the same width. Per-type coverage stays lower.
4. **Leave-one-year-out (supplement) does not help.** Pooling two teams does not make the third predictable.

## 4. L2 decide (`l2_decide.py`, `results/l2_results.md`)

### Rule
For each action a, compute U_a = the conformal 90 % upper bound on the 60-day loss of all products, and C_a = the predicted added inventory capital. Then:
- **Do nothing** if U_none ≤ L*.
- Otherwise, take the cheapest action with U_a ≤ L*.
- Otherwise, take the action with the lowest bound.

L* = 1 day of demand over 60 days (fill rate ≥ 98.3 %). L* is stated, not tuned; a sweep over 0.25–4 is in the results file.

A first run violated the stated "do nothing first" rule: ship has a tiny negative inventory cost and won ties. This was fixed, and the fix is noted in the code.

### Results (L* = 1)
| | players | type-rule (Phase E table) | L2 | oracle |
|---|---|---|---|---|
| normal 2 held-out: lost (days) / violation / added EUR | 2.26 / 24.8 % / 0 | 2.11 / 20.0 % / 124k | **1.99 / 19.8 % / 25k** | 1.91 / 19.2 % / 4k |
| fraud 2 (built on normal 2) | 1.43 / 20.9 % / 0 | 1.31 / 17.7 % / 111k | 1.47 / 21.3 % / 26k | 1.04 / 12.2 % / 9k |
| fraud 3 (built on normal 2) | 0.66 / 9.1 % / 0 | 0.71 / 9.7 % / 203k | 0.68 / 9.0 % / 34k | 0.60 / 8.0 % / 1k |
| fraud 2, **adapted** (+400 target episodes; the other 1,600) | 1.40 / 21.1 % / 0 | 1.12 / 14.1 % / 144k | **1.19 / 16.4 % / 60k** | 1.01 / 12.2 % / 9k |
| fraud 3, adapted | 0.66 / 8.9 % / 0 | 0.71 / 9.4 % / 206k | 0.67 / 8.5 % / 20k | 0.61 / 7.6 % / 1k |

The best fixed action in hindsight for fraud 2 is po10: 1.02 lost, 147k added inventory.

### Findings
1. **In the year it was built on, L2 cuts lost demand by 12 %.** It nearly reaches the oracle's violation rate (19.8 % vs 19.2 %) with a fifth of the inventory of the Phase E lookup rule, and it acts in only a third of the episodes.
2. **A decision policy learned on one team's twin does not transfer to another team's.** It is slightly worse than doing nothing, and pooling two teams (leave-one-year-out) does not fix it.
3. **A few hundred episodes on the target's own twin restore the gain:** −15 % loss in fraud 2 at 40 % of the inventory of the best fixed rule. Where there is nothing to gain (fraud 3), the adapted L2 mostly does nothing.
4. **The conformal margin costs inventory without changing the mean outcome in-distribution** (point-L2 is similar). Its purpose is the guarantee (L4), not the average.

## 5. L3 explain (`l3_explain.py`, `results/l3_results.md`)

### The policy as a rule
L2 is distilled into a depth-3 tree with 8 leaves and 6 features. This is the certified policy:

```
if line stoppage:
    if finished-goods cover <= 30 days:  extra F12 batch (+ component buffer and line priority if the F12 queue is short)
    else:                                 component buffer or extra batch, by West DC cover
else:
    if surge factor > 1.09 and finished-goods cover <= 20 days:  rebalance DCs (ship)
    elif low surge and plant stock > 11 days:                    line priority
    else:                                                         do nothing
```

### Results
- **Fidelity to L2:** 77 % (normal 2), 69 % (fraud 2), 56 % (fraud 3). As a policy it performs like L2 in every year (`l3_results.md`).
- **Stability over 10 bootstrap refits of the whole pipeline:**
  - The root split (stoppage or not) appears in 10/10 refits.
  - The surge factor appears in every tree.
  - Feature-set Jaccard similarity has a median of 0.5.
  - Bootstrap trees agree on 77 % of normal 2 decisions, and on only 54 % in fraud 3.
- **SHAP of L1:**
  - Top drivers: stoppage length, finished-goods cover, North DC cover, surge factor.
  - The importance ranking is almost identical across years (Spearman 0.96–0.99).

### Finding
**Stable explanations are not evidence of transfer.** L1's explanation is the same in every year while its accuracy and coverage degrade. The decision rule's top split is stable, and its lower splits are not. L3 tells the planner *what* the policy looks at. Only L4 says *whether it can be trusted* where it is used.

## 6. L4 certify (`l4_certify.py`, `results/l4_results.md`)

### What is certified
The certified object is the **tree**, the explanation itself. Each certificate uses episodes never used to build anything, and every outcome is a twin run. The Clopper–Pearson intervals are 95 %.

| | players | L2 (black box) | **tree** |
|---|---|---|---|
| normal 2, independent sample (2,000): service rate / certified ≥ | 77.6 % / 75.7 % | 82.7 % / 80.9 % | **80.0 % / 78.2 %** |
| normal 2: certified harm ≤ (loss > players' + 0.05 days) | – | 3.1 % | **2.0 %** |
| fraud 2 (tree built on normal 2): certified service ≥ / harm ≤ | 77.2 % | 76.8 % / 7.3 % | 77.0 % / 7.1 % |
| fraud 2, **adapted tree** (other 1,600): certified service ≥ / harm ≤ | 76.9 % | – | **84.1 % / 7.0 %** |
| fraud 3, adapted tree: certified service ≥ / harm ≤ | 89.6 % | – | 89.9 % / 3.6 % (6k EUR) |
| worst disruption type (E3 stoppage), certified service ≥ | 20–48 % | 21–49 % | 21–49 % |

### Findings
1. **The explainable policy is certifiably better than the players' own response in its build year,** at a certified harm rate ≤ 2 %. The explanation costs about 2.7 points of service against the black box.
2. **The certificate exposes the transfer failure that L1 and L2 predicted.** The tree built on normal 2 gives fraud 2 nothing, and its harm rate rises to ≤ 7 %. The adapted tree recovers +7 points of certified service.
3. **No policy can certify a high service level against line stoppages** (worst type 20–49 %). This is a property of the plant (one shared line at 82–93 % load), not of the AI, and is reported as a resilience limit.
4. **The certified level is reported rather than a pass/fail at an arbitrary p\*.** In normal 2, even the oracle meets L* in only about 84 % of episodes.

## 7. Robustness to the shipping rule (`robustness.py`, `results/robustness.md`)
The same pipeline is rebuilt on episodes generated with **plain** transfer replay (`episodes.py --plain-push`), the rule that strands stock at the plant.

| (L* = 1; lost in days of demand / violation) | normal 2 held-out | fraud 2 | fraud 3 |
|---|---|---|---|
| deferred (nominal): players → L2 → oracle | 2.26 → **1.99** → 1.91 | 1.43 → 1.47 → 1.04 | 0.66 → 0.68 → 0.60 |
| deferred: L1 coverage | 88.0 % | 84.9 % | 79.0 % |
| plain: players → L2 → oracle | 4.39 → **2.37** → 2.30 | 3.91 → 1.63 → 1.49 | 1.10 → 0.63 → 0.53 |
| plain: L1 coverage | 89.5 % | 94.8 % | 94.4 % |
| plain: best fixed action | ship (2.38) | ship (1.50) | ship (0.53) |

### What holds under both rules
In the build year, L2 beats the players and comes close to the oracle.

### What does not
1. **Under plain replay, the artefact dominates.**
   - The players lose about twice as much.
   - Shipping the stranded stock is the best action in every year, and it even reduces inventory.
   - Because that "repair" works for every team, prediction and decisions appear to transfer across teams: coverage is 95 %, and L2 gains 58 % / 43 % in the fraud years.
2. **The transfer failure is therefore not caused by the Amendment 3 correction. The artefact hid it.** A study on the unvalidated replay would have reported an AI that transfers across teams, for a reason that does not exist in the real game.

### Consequence for the paper
This is direct evidence that **validating the twin against the recorded data, down to the replay rules, is a precondition for trustworthy AI on it**. The paper reports the nominal results and this check side by side.

## 8. What the paper can claim
- A predict → decide → explain → certify pipeline on a supply-chain twin whose every part is backed by data, with disruptions drawn within evidence bounds and only the players' real levers.
- **Positive:** in-distribution, the explainable policy certifiably improves service over the human team's own response, at low certified harm and modest inventory.
- **Negative, and arguably more important for "trustworthy AI":**
  - Prediction coverage, decision value and certificates all degrade when the twin of one team is used for another team's operations.
  - Explanation stability does not reveal this.
  - Recalibration (100 outcomes) restores coverage, and adaptation (a few hundred target episodes) restores decision value.
- **Twin validity matters more than model choice:** an unvalidated replay rule would have produced a falsely transferable AI (section 7).
- **Limits:** line stoppages cannot be mitigated with these levers, and that is stated.

## 9. Next
- UPPAAL encoding of the certified tree as a controller template, on top of `model/uppaal` (the levers must first be added to the generator, then mirror-checked as in `docs/uppaal.md`).
- Figures for the paper: the coverage-vs-shift curve (L1), the lost-demand vs inventory frontier (L2), the tree (L3), and the certificate table (L4).
