# Revision statistics (answers to the mock review)

## 1. Random vs grouped (by start day) split, built on normal 2

| split | L1 MAE held-out | L1 coverage held-out | L1 coverage cert. sample | L2 lost held-out | players lost held-out | L2 service cert. | players service cert. |
|---|---|---|---|---|---|---|---|
| random episodes (test n=400) | 0.221 | 88.0% | 89.6% | 1.987 | 2.264 | 82.7% | 77.6% |
| grouped by start day (test n=387) | 0.377 | 87.3% | 93.2% | 1.653 | 1.984 | 81.5% | 77.6% |

## 2. Paired comparisons (common random numbers)

Service = share of episodes with 60-day loss <= L*. McNemar: exact two-sided test on discordant pairs. Differences: mean and paired bootstrap 95 % CI.

| sample | comparison | A | B | B - A (95 % CI) | discordant B>A / A>B | McNemar p |
|---|---|---|---|---|---|---|
| Y1 certification sample (n=2000) | service tree vs players | 77.6% | 80.0% | +2.5% (+1.8%, +3.1%) | 50 / 1 | 4.6e-14 |
| Y1 certification sample (n=2000) | service L2 vs players | 77.6% | 82.7% | +5.1% (+4.1%, +6.0%) | 104 / 3 | 2.5e-27 |
| Y1 certification sample (n=2000) | service L2 vs tree | 80.0% | 82.7% | +2.6% (+1.9%, +3.5%) | 57 / 5 | 3.1e-12 |
| Y1 certification sample (n=2000) | loss (days) tree vs players | 1.838 | 1.612 | -0.227 (-0.271, -0.183) | | |
| Y1 certification sample (n=2000) | loss (days) L2 vs players | 1.838 | 1.577 | -0.261 (-0.310, -0.216) | | |
| fraud_2 other 1,600 (adapted) | service tree vs players | 78.9% | 85.9% | +6.9% (+5.5%, +8.3%) | 124 / 13 | 6.8e-24 |
| fraud_2 other 1,600 (adapted) | service L2 vs players | 78.9% | 83.6% | +4.6% (+3.3%, +5.9%) | 96 / 22 | 3.3e-12 |
| fraud_2 other 1,600 (adapted) | service L2 vs tree | 85.9% | 83.6% | -2.3% (-3.2%, -1.4%) | 9 / 46 | 4.3e-07 |
| fraud_2 other 1,600 (adapted) | loss (days) tree vs players | 1.401 | 1.097 | -0.304 (-0.377, -0.236) | | |
| fraud_2 other 1,600 (adapted) | loss (days) L2 vs players | 1.401 | 1.191 | -0.211 (-0.274, -0.149) | | |
| fraud_2 other 1,600 (built on normal 2) | service tree vs players | 78.9% | 78.6% | -0.4% (-0.9%, +0.1%) | 4 / 10 | 0.18 |
| fraud_2 other 1,600 (built on normal 2) | service L2 vs players | 78.9% | 78.4% | -0.5% (-1.1%, +0.1%) | 6 / 14 | 0.12 |
| fraud_2 other 1,600 (built on normal 2) | service L2 vs tree | 78.6% | 78.4% | -0.1% (-0.5%, +0.2%) | 3 / 5 | 0.73 |
| fraud_2 other 1,600 (built on normal 2) | loss (days) tree vs players | 1.401 | 1.431 | +0.030 (+0.008, +0.053) | | |
| fraud_2 other 1,600 (built on normal 2) | loss (days) L2 vs players | 1.401 | 1.439 | +0.038 (+0.004, +0.072) | | |
| fraud_3 other 1,600 (adapted) | service tree vs players | 91.1% | 91.4% | +0.2% (-0.1%, +0.6%) | 6 / 2 | 0.29 |
| fraud_3 other 1,600 (adapted) | service L2 vs players | 91.1% | 91.5% | +0.4% (-0.1%, +0.9%) | 11 / 5 | 0.21 |
| fraud_3 other 1,600 (adapted) | service L2 vs tree | 91.4% | 91.5% | +0.1% (-0.3%, +0.6%) | 7 / 5 | 0.77 |
| fraud_3 other 1,600 (adapted) | loss (days) tree vs players | 0.663 | 0.687 | +0.024 (+0.003, +0.046) | | |
| fraud_3 other 1,600 (adapted) | loss (days) L2 vs players | 0.663 | 0.672 | +0.008 (-0.014, +0.032) | | |
| fraud_3 other 1,600 (built on normal 2) | service tree vs players | 91.1% | 91.3% | +0.2% (-0.1%, +0.6%) | 6 / 3 | 0.51 |
| fraud_3 other 1,600 (built on normal 2) | service L2 vs players | 91.1% | 91.3% | +0.2% (-0.2%, +0.6%) | 7 / 4 | 0.55 |
| fraud_3 other 1,600 (built on normal 2) | service L2 vs tree | 91.3% | 91.3% | +0.0% (-0.4%, +0.4%) | 5 / 5 | 1 |
| fraud_3 other 1,600 (built on normal 2) | loss (days) tree vs players | 0.663 | 0.686 | +0.023 (+0.003, +0.044) | | |
| fraud_3 other 1,600 (built on normal 2) | loss (days) L2 vs players | 0.663 | 0.688 | +0.024 (+0.003, +0.046) | | |
| Y1 held-out (n=400) | loss (days) L2 vs players | 2.264 | 1.987 | -0.277 (-0.382, -0.181) | | |

## 3. L1 recalibration on 100 target episodes, 200 resamples

| target | coverage mean | SD | 5-95 % | mean bound (days) | build-year bound (days) |
|---|---|---|---|---|---|
| fraud_2 | 90.4% | 2.7% | 85.9%-94.8% | 1.04 | 1.02 |
| fraud_3 | 89.8% | 3.1% | 83.9%-94.4% | 0.95 | 0.93 |

## 4. L2: coverage of the chosen action's bound, branches, joint calibration

Per-action conformal corrections: none 0.00, po5 0.00, po10 0.00, fg 0.01, ship 0.01, prio 0.01, fg+prio 0.02, po10+fg+prio 0.02; joint (max over actions) correction: 0.12 days.

| sample | branch | share | Pr(Y_chosen <= U_chosen), per-action | Pr(Y_chosen <= L*) |
|---|---|---|---|---|
| Y1 held-out | no response (U_none <= L*) | 66.2% | 95.1% | 99.2% |
| Y1 held-out | cheapest feasible action | 6.0% | 91.7% | 100.0% |
| Y1 held-out | lowest bound (none feasible) | 27.8% | 75.7% | 30.6% |
| Y1 held-out | all | 100 % | 89.5% | 80.2% |
| Y1 certification sample | no response (U_none <= L*) | 68.2% | 90.5% | 99.7% |
| Y1 certification sample | cheapest feasible action | 6.6% | 91.6% | 97.7% |
| Y1 certification sample | lowest bound (none feasible) | 25.3% | 79.8% | 32.8% |
| Y1 certification sample | all | 100 % | 87.9% | 82.7% |

## 5. L1 point models, grouped split (held-out start days of normal 2), MAE in days

| model | MAE | Spearman |
|---|---|---|
| per-type mean | 1.184 | |
| ridge (notice+state) | 1.203 | 0.66 |
| gbm-notice | 0.902 | 0.81 |
| gbm-state | 1.791 | 0.19 |
| gbm (notice+state) | 0.377 | 0.85 |

## 6. L2 cost model C_a: held-out error (Y1, added inventory capital in days of demand)

| action | MAE | mean realised |
|---|---|---|
| po5 | 0.137 | 2.839 |
| po10 | 0.310 | 9.626 |
| fg | 0.127 | 3.317 |
| ship | 0.050 | -0.011 |
| prio | 0.074 | 0.019 |
| fg+prio | 0.162 | 3.393 |
| po10+fg+prio | 0.351 | 12.709 |
