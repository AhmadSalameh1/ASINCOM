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
- **Open loop:** all player decisions are replayed (conversions, POs, transfers, demand), so each result is the **physical propagation** through the validated twin. The single exception is the MRP reaction to blocked material (rule R5), without which a quantity loss would block the line for ever (see 5).
- **Timing randomised:** each seed draws its own disruption start day uniformly over the steady months, because a fixed start day gave misleading results (see 5).
- **Common random numbers:** each disruption run is compared with the baseline run of the same seed, so the extra loss is not noise.
- Three game years, 60 seeds each.

## 4. Results: extra lost demand vs the same-seed baseline (median [95th percentile]; share of seeds with any extra loss)
| Disruption | normal 2 | fraud 2 | fraud 3 |
|---|---|---|---|
| E1 supplier delay, q50 | +0 [+24,000]; 48 % | +0 [+0]; 2 % | +0 [+0]; 0 % |
| E1 supplier delay, q90 | **+32,800** [+58,800]; 73 % | +0 [+0]; 3 % | +0 [+246]; 17 % |
| E1 supplier delay, q95 | **+33,600** [+58,800]; 80 % | +0 [+400]; 5 % | +0 [+246]; 20 % |
| E2 quality, wheat only | +3,200 [+36,000]; 52 % | +0 [+13,018]; 8 % | +0; 0 % |
| E2 quality, all food 4.1 % | **+24,000** [+38,440]; 77 % | +0 [+14,018]; 23 % | +0; 0 % |
| E2 quality, all food 25 % (STRESS) | +24,000 [+38,440]; 78 % | +0 [+13,367]; 23 % | +0; 0 % |
| E3 stoppage, 3 days | **+27,200** [+39,200]; 63 % | +0; 0 % | +0 [+12]; 5 % |
| E3 stoppage, 10 days | +80,600 [+122,800]; 92 % | +0 [+36,498]; 22 % | +246 [+37,523]; 55 % |
| E3 stoppage, 25 days | +183,600 [+235,800]; 100 % | +46,018 [+126,018]; 98 % | +64,677 [+111,657]; 88 % |
| E4 demand +19 % | +28,300 [+36,599]; 100 % | +17,365 [+22,253]; 100 % | +0 [+7,421]; 47 % |
| E4 demand +50 % (STRESS) | +74,475 [+96,312]; 100 % | +48,932 [+61,725]; 100 % | +7,429 [+24,510]; 100 % |
| E5 transit +1 day | +0; 0 % | +0; 0 % | +0; 2 % |
| E5 transit +4 days | +0 [+5,396]; 27 % | +0; 0 % | +0 [+4,452]; 12 % |

## 5. Findings
1. **Resilience is set by the players' policy, not by the supply chain's structure.** The three years are the same company, network and physics, yet the same disruption costs normal 2 tens of thousands of units while fraud 2 and fraud 3 absorb it. The difference is the players' policies: the component and finished-goods buffers they held and when they converted planned orders. **This is the motivation for the AI decision layer**, and a warning for the prediction layer: an impact predictor must see the policy state (buffers, queue), not only the disruption.
2. **Under ERPsim's full-batch start rule, a quality loss hurts through the replacement lead time, not through the lost quantity.** 4.1 % and 25 % losses give identical impact, because any shortfall holds the order until the replacement arrives.
3. **Impact depends strongly on timing.** The same disruption hits 0–100 % of seeds depending on where it falls relative to the production queue. With a single fixed start day, an earlier version of this experiment reported both a 35,200-unit loss and zero loss for the same quality event. Randomised timing is required.
4. **Downstream transit delays barely matter here,** because the DCs hold weeks of cover. That DataCo is semi-synthetic makes this conclusion conservative.
5. **Open-loop replay is valid for timing disruptions but not for quantity losses.** With every decision frozen, blocked material is never re-ordered and the line stays blocked for the rest of the year. The accepted MRP rule R5 (re-order the blocked quantity) is the minimal reaction that makes quantity disruptions meaningful.

## 6. Next
- Closed-loop experiments: the AI decision layer reacts, and is compared with the players' historical decisions (this table) and with the MRP replica.
- Prediction targets for L1: the extra loss and whether any loss occurs, given the disruption and the policy state at its start.
