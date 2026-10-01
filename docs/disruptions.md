# Phase E: evidence-based disruptions

Code: `model/twin/twin.py` (the `scenario` hooks) and `model/twin/disruptions.py` (the experiment runner). Results are in `model/twin/disruptions/<run>_impact.md`. Open-data evidence: `data/open_data_evidence.py` → `data/open_data/open_data_evidence.json`.

## 1. Rule for admitting a disruption
A disruption must (a) act through a mechanism of the **validated physics** (`docs/validation_report.md`, round 2) and (b) take its severity from **evidence**. Levels beyond the evidence are labelled **STRESS**. Open-data evidence is transferred only as **dimensionless** quantities (ratios and shares), never as absolute days or units.

## 2. Disruptions and their evidence
| ID | Mechanism in the twin | Levels | Evidence |
|---|---|---|---|
| E1 supplier delay | POs created in a 20-day window arrive `ceil(r × lead)` days later | r = 0.12 / 0.75 / 1.0 | **USAID SCMS** (10,324 shipments, 2006–15): 11.5 % late. When late, delay / planned lead time is q50 0.12, q90 0.75, q95 0.96. |
| E2 quality loss | receipts in the window lose a share to blocked stock; the rest arrives 2 days late; the MRP reaction (rule R5) re-orders the blocked quantity | 4.1 % on wheat / 4.1 % on all food / STRESS 25 % | **ERPsim** Q2: 6 scrap events in 3 years lost 0.2–4.1 % of the affected receipt; Q1: scrap receipts arrive late |
| E3 line stoppage | shared line unavailable for n days | 3 / 10 / 25 days | 25 days = shortest observed production pause (B17, fraud 3; 52 and 60 days in the other years). 3 and 10 days are assumed breakdown lengths, and are labelled as such. |
| E4 demand shift | customer order quantities × f for a month | +19 % / STRESS +50 % | **ERPsim** normal 2: steady monthly sales range 0.78–1.19 × the mean. DataCo daily demand has no surges (> 1.5×) and one 0.24× step in 10/2017 that looks like a data artefact, so it is **not used**. |
| E5 transit delay | plant → DC shipments in the window arrive k days later (ERPsim transfers are otherwise instantaneous, B14) | +1 / +4 days | **DataCo**: 57 % late, excess q50 1 day, q95 4 days. DataCo is semi-synthetic, so this is an upper bound. |

## 3. Experimental design
- **Open loop:** all player decisions are replayed (conversions, POs, transfers, demand), so each result is the **physical propagation** through the validated twin. Transfers are replayed with deferral (validation Amendment 3). The single exception is the MRP reaction to blocked material (rule R5), without which a quantity loss would block the line for ever (see 5).
- **Timing randomised:** each seed draws its own disruption start day uniformly over the steady months, because a fixed start day gave misleading results (see 5).
- **Common random numbers:** each disruption run is compared with the baseline run of the same seed, so the extra loss is not noise.
- Three game years, 60 seeds each.

## 4. Results: extra lost demand vs the same-seed baseline (median [95th percentile]; share of seeds with any extra loss)
| Disruption | normal 2 | fraud 2 | fraud 3 |
|---|---|---|---|
| E1 supplier delay, q50 | +0 [+0]; 0% | +0 [+0]; 0% | +0 [+0]; 0% |
| E1 supplier delay, q90 | +0 [+934]; 13% | +0 [+0]; 2% | +0 [+0]; 0% |
| E1 supplier delay, q95 | +0 [+4,790]; 13% | +0 [+0]; 2% | +0 [+0]; 3% |
| E2 quality, wheat only | +0 [+7,023]; 23% | +0 [+5,406]; 20% | +0 [+0]; 0% |
| E2 quality, all food 4.1 % | +0 [+7,023]; 27% | +0 [+13,363]; 13% | +0 [+0]; 0% |
| E2 quality, all food 25 % (STRESS) | +0 [+7,023]; 27% | +0 [+13,363]; 13% | +0 [+0]; 0% |
| E3 stoppage, 3 days | +0 [+0]; 0% | +0 [+0]; 0% | +0 [+0]; 0% |
| E3 stoppage, 10 days | +0 [+33,059]; 37% | +0 [+0]; 3% | +0 [+1,155]; 18% |
| E3 stoppage, 25 days | +54,531 [+172,028]; 100% | +13,363 [+44,197]; 83% | +19,324 [+40,273]; 77% |
| E4 demand, +19 % | +28,296 [+36,595]; 100% | +5,915 [+12,040]; 92% | +0 [+3,186]; 38% |
| E4 demand, +50 % (STRESS) | +74,471 [+96,308]; 100% | +36,399 [+49,293]; 100% | +1,987 [+15,295]; 83% |
| E5 transit, +1 day | +0 [+0]; 0% | +0 [+0]; 0% | +0 [+0]; 0% |
| E5 transit, +4 days | +0 [+5,392]; 27% | +0 [+0]; 0% | +0 [+217]; 12% |

**Re-run after validation Amendment 3.** A first version of this table used plain transfer replay, which strands stock at the plant whenever the twin's output is later than the recorded output (`docs/validation_report.md`, round 3). That artefact made normal 2 look fragile to upstream disruptions: E1 q90 hit 73 % of seeds, with a median extra loss of +32,800 units. With deferred replay, E1 and E2 hit 13–27 % of normal 2 seeds with a median extra loss of 0. The demand-surge and long-stoppage results barely change. **Every number above is from the corrected twin.**

## 5. Findings
1. **Resilience differs strongly between the three teams' policies, on the same company, network and physics.**
   - A one-month +19 % surge costs normal 2 a median of +28,296 units; fraud 2 +5,915; fraud 3 nothing.
   - A 25-day stoppage costs +54,531 / +13,363 / +19,324.
   - **This motivates the AI decision layer, and it warns the prediction layer:** an impact predictor must see the policy state (buffers, queue), not only the disruption (confirmed in `docs/ai_layers.md`, L1).
2. **Under ERPsim's full-batch start rule, a quality loss hurts through the replacement lead time, not through the lost quantity.** The 4.1 % and 25 % losses give the same impact, because any shortfall holds the order until the replacement arrives.
3. **Impact depends strongly on timing.** The same disruption hits 0–100 % of seeds depending on where it falls relative to the production queue. Randomised timing is required.
4. **Upstream disruptions are mostly absorbed by the players' own buffers.** E1 and E2 never have a positive median impact; they cause losses only in the unlucky 13–27 % of timings. **Downstream transit delays barely matter,** because the DCs hold weeks of cover.
5. **Short stoppages (3 days) are absorbed in every year; long ones are not.** The shared line runs at 82–93 % load (DR-2), so lost line-days cannot be made up.
6. **Open-loop replay is valid for timing disruptions but not for quantity losses.** With every decision frozen, blocked material is never re-ordered and the line stays blocked for the rest of the year. The accepted MRP rule R5 (re-order the blocked quantity) is the minimal reaction that makes quantity disruptions meaningful.

## 6. Next
Done: the AI layers (`docs/ai_layers.md`) sample these disruptions continuously within the same evidence bounds.
