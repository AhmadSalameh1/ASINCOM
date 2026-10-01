# L2 results: risk-constrained response (L* = 1.0 day of demand over 60 days)

Built on normal 2 (1200 train, 400 calibration episodes). type-rule: {'E1': 'po10', 'E2': 'po10', 'E3': 'fg', 'E4': 'ship', 'E5': 'po10'}.

lost = lost demand of all products over the 60 days after the notice; violation = share of episodes whose realised loss exceeds L*; added inventory = mean extra inventory capital (material cost) held over the 60 days.


## normal 2 held-out

| policy | lost (days of demand) | lost (units) | violation of L* | added inventory (days) | added inventory (EUR) | acted |
|---|---|---|---|---|---|---|
| players (no response) | 2.264 | 17,437 | 24.8% | 0.000 | 0 | 0% |
| always po5 | 2.263 | 17,434 | 24.8% | 2.839 | 53,928 | 100% |
| always po10 | 2.262 | 17,424 | 24.8% | 9.626 | 181,317 | 100% |
| always fg | 2.187 | 16,869 | 26.2% | 3.317 | 62,653 | 100% |
| always ship | 2.495 | 19,273 | 26.0% | -0.011 | -146 | 100% |
| always prio | 2.333 | 17,930 | 25.0% | 0.019 | 266 | 100% |
| always fg+prio | 2.378 | 18,379 | 28.5% | 3.393 | 64,037 | 100% |
| always po10+fg+prio | 2.346 | 18,120 | 27.5% | 12.709 | 237,723 | 100% |
| type-rule (Phase E table) | 2.110 | 16,342 | 20.0% | 6.591 | 124,406 | 100% |
| point-L2 (no conformal margin) | 1.974 | 15,240 | 19.5% | 0.628 | 12,066 | 26% |
| **L2 (conformal, risk-constrained)** | 1.987 | 15,359 | 19.8% | 1.291 | 25,090 | 34% |
| oracle (knows outcomes) | 1.907 | 14,730 | 19.2% | 0.201 | 3,958 | 36% |

L2 action mix: {'none': 0.665, 'ship': 0.085, 'po10+fg+prio': 0.075, 'fg': 0.065, 'fg+prio': 0.052, 'po10': 0.028, 'prio': 0.025, 'po5': 0.005}

## fraud 2

| policy | lost (days of demand) | lost (units) | violation of L* | added inventory (days) | added inventory (EUR) | acted |
|---|---|---|---|---|---|---|
| players (no response) | 1.432 | 7,651 | 20.9% | 0.000 | 0 | 0% |
| always po5 | 1.256 | 6,898 | 17.6% | 2.707 | 34,519 | 100% |
| always po10 | 1.047 | 5,953 | 12.6% | 11.227 | 146,329 | 100% |
| always fg | 1.303 | 7,266 | 18.1% | 4.759 | 65,283 | 100% |
| always ship | 1.588 | 8,497 | 27.3% | -0.006 | -132 | 100% |
| always prio | 1.439 | 7,691 | 21.0% | 0.030 | 455 | 100% |
| always fg+prio | 1.325 | 7,401 | 18.3% | 4.915 | 67,431 | 100% |
| always po10+fg+prio | 1.223 | 6,957 | 15.0% | 15.498 | 203,804 | 100% |
| type-rule (Phase E table) | 1.310 | 7,293 | 17.7% | 8.487 | 111,307 | 100% |
| point-L2 (no conformal margin) | 1.495 | 8,038 | 21.4% | 0.993 | 13,382 | 21% |
| **L2 (conformal, risk-constrained)** | 1.466 | 7,911 | 21.3% | 1.991 | 26,218 | 35% |
| oracle (knows outcomes) | 1.042 | 5,916 | 12.2% | 0.792 | 9,049 | 29% |

L2 action mix: {'none': 0.654, 'fg': 0.092, 'fg+prio': 0.078, 'prio': 0.053, 'po10': 0.042, 'po10+fg+prio': 0.04, 'ship': 0.027, 'po5': 0.012}

## fraud 3

| policy | lost (days of demand) | lost (units) | violation of L* | added inventory (days) | added inventory (EUR) | acted |
|---|---|---|---|---|---|---|
| players (no response) | 0.659 | 4,288 | 9.1% | 0.000 | 0 | 0% |
| always po5 | 0.659 | 4,287 | 9.1% | 8.096 | 98,934 | 100% |
| always po10 | 0.659 | 4,287 | 9.1% | 23.962 | 291,118 | 100% |
| always fg | 0.708 | 4,526 | 9.0% | 5.670 | 66,151 | 100% |
| always ship | 0.702 | 4,908 | 10.6% | -0.069 | -685 | 100% |
| always prio | 0.672 | 4,420 | 9.2% | 0.135 | 1,640 | 100% |
| always fg+prio | 0.701 | 4,606 | 8.9% | 5.966 | 69,703 | 100% |
| always po10+fg+prio | 0.701 | 4,606 | 8.9% | 28.547 | 341,779 | 100% |
| type-rule (Phase E table) | 0.707 | 4,545 | 9.7% | 16.696 | 203,005 | 100% |
| point-L2 (no conformal margin) | 0.667 | 4,318 | 8.8% | 1.364 | 15,852 | 24% |
| **L2 (conformal, risk-constrained)** | 0.683 | 4,383 | 9.0% | 2.775 | 33,579 | 54% |
| oracle (knows outcomes) | 0.601 | 4,016 | 8.0% | 0.011 | 695 | 30% |

L2 action mix: {'none': 0.462, 'fg': 0.207, 'prio': 0.136, 'fg+prio': 0.072, 'ship': 0.06, 'po10': 0.026, 'po10+fg+prio': 0.02, 'po5': 0.016}

## STRESS

| policy | lost (days of demand) | lost (units) | violation of L* | added inventory (days) | added inventory (EUR) | acted |
|---|---|---|---|---|---|---|
| players (no response) | 1.520 | 9,469 | 32.6% | 0.000 | 0 | 0% |
| always po5 | 1.446 | 9,136 | 31.9% | 5.000 | 68,060 | 100% |
| always po10 | 1.353 | 8,735 | 30.9% | 16.216 | 221,090 | 100% |
| always fg | 1.395 | 8,950 | 32.0% | 4.406 | 61,271 | 100% |
| always ship | 1.400 | 8,652 | 33.5% | -0.154 | -2,595 | 100% |
| always prio | 1.529 | 9,538 | 32.7% | 0.086 | 1,272 | 100% |
| always fg+prio | 1.433 | 9,268 | 32.9% | 4.601 | 63,996 | 100% |
| always po10+fg+prio | 1.383 | 9,008 | 32.2% | 20.268 | 276,186 | 100% |
| type-rule (Phase E table) | 1.294 | 8,016 | 29.9% | 7.460 | 102,250 | 100% |
| point-L2 (no conformal margin) | 1.286 | 7,833 | 30.1% | 0.606 | 6,857 | 36% |
| **L2 (conformal, risk-constrained)** | 1.301 | 7,896 | 31.0% | 1.802 | 24,418 | 58% |
| oracle (knows outcomes) | 1.021 | 6,467 | 25.5% | 0.552 | 6,597 | 32% |

L2 action mix: {'none': 0.423, 'ship': 0.218, 'fg': 0.132, 'prio': 0.102, 'fg+prio': 0.074, 'po10+fg+prio': 0.032, 'po5': 0.014, 'po10': 0.004}

## Transfer to another player team: remedies

| variant | test year | policy | lost (days) | violation | added inventory (EUR) | acted |
|---|---|---|---|---|---|---|
| LOYO (built on the other two years) | normal_2 | players (no response) | 1.934 | 22.3% | 0 | 0% |
| LOYO (built on the other two years) | normal_2 | best fixed action in hindsight (fg) | 1.866 | 22.9% | 61,939 | 100% |
| LOYO (built on the other two years) | normal_2 | type-rule | 1.933 | 22.3% | 185,102 | 100% |
| LOYO (built on the other two years) | normal_2 | L2 | 1.976 | 22.4% | 54,922 | 50% |
| LOYO (built on the other two years) | normal_2 | oracle | 1.602 | 16.5% | 3,328 | 34% |
| LOYO (built on the other two years) | fraud_2 | players (no response) | 1.432 | 20.9% | 0 | 0% |
| LOYO (built on the other two years) | fraud_2 | best fixed action in hindsight (po10) | 1.047 | 12.6% | 146,329 | 100% |
| LOYO (built on the other two years) | fraud_2 | type-rule | 1.310 | 17.7% | 111,307 | 100% |
| LOYO (built on the other two years) | fraud_2 | L2 | 1.460 | 21.4% | 12,586 | 19% |
| LOYO (built on the other two years) | fraud_2 | oracle | 1.042 | 12.2% | 9,049 | 29% |
| adapted (normal 2 + 400 target episodes) | fraud_2 | players (no response) | 1.401 | 21.1% | 0 | 0% |
| adapted (normal 2 + 400 target episodes) | fraud_2 | best fixed action in hindsight (po10) | 1.018 | 12.7% | 146,518 | 100% |
| adapted (normal 2 + 400 target episodes) | fraud_2 | type-rule | 1.115 | 14.1% | 144,041 | 100% |
| adapted (normal 2 + 400 target episodes) | fraud_2 | L2 | 1.191 | 16.4% | 59,679 | 52% |
| adapted (normal 2 + 400 target episodes) | fraud_2 | oracle | 1.013 | 12.2% | 9,256 | 29% |
| built on normal 2 (same 1,600 episodes) | fraud_2 | players (no response) | 1.401 | 21.1% | 0 | 0% |
| built on normal 2 (same 1,600 episodes) | fraud_2 | best fixed action in hindsight (po10) | 1.018 | 12.7% | 146,518 | 100% |
| built on normal 2 (same 1,600 episodes) | fraud_2 | type-rule | 1.278 | 17.7% | 110,660 | 100% |
| built on normal 2 (same 1,600 episodes) | fraud_2 | L2 | 1.439 | 21.6% | 27,148 | 35% |
| built on normal 2 (same 1,600 episodes) | fraud_2 | oracle | 1.013 | 12.2% | 9,256 | 29% |
| LOYO (built on the other two years) | fraud_3 | players (no response) | 0.659 | 9.1% | 0 | 0% |
| LOYO (built on the other two years) | fraud_3 | best fixed action in hindsight (po5) | 0.659 | 9.1% | 98,934 | 100% |
| LOYO (built on the other two years) | fraud_3 | type-rule | 0.659 | 9.1% | 291,118 | 100% |
| LOYO (built on the other two years) | fraud_3 | L2 | 0.656 | 8.5% | 116,516 | 59% |
| LOYO (built on the other two years) | fraud_3 | oracle | 0.601 | 8.0% | 695 | 30% |
| adapted (normal 2 + 400 target episodes) | fraud_3 | players (no response) | 0.663 | 8.9% | 0 | 0% |
| adapted (normal 2 + 400 target episodes) | fraud_3 | best fixed action in hindsight (none) | 0.663 | 8.9% | 0 | 0% |
| adapted (normal 2 + 400 target episodes) | fraud_3 | type-rule | 0.710 | 9.4% | 206,211 | 100% |
| adapted (normal 2 + 400 target episodes) | fraud_3 | L2 | 0.672 | 8.5% | 20,242 | 18% |
| adapted (normal 2 + 400 target episodes) | fraud_3 | oracle | 0.608 | 7.6% | 632 | 30% |
| built on normal 2 (same 1,600 episodes) | fraud_3 | players (no response) | 0.663 | 8.9% | 0 | 0% |
| built on normal 2 (same 1,600 episodes) | fraud_3 | best fixed action in hindsight (none) | 0.663 | 8.9% | 0 | 0% |
| built on normal 2 (same 1,600 episodes) | fraud_3 | type-rule | 0.710 | 9.4% | 206,211 | 100% |
| built on normal 2 (same 1,600 episodes) | fraud_3 | L2 | 0.688 | 8.7% | 32,477 | 53% |
| built on normal 2 (same 1,600 episodes) | fraud_3 | oracle | 0.608 | 7.6% | 632 | 30% |

## Sweep over the service limit L*

| L* | set | policy | lost (days) | violation | added inventory (EUR) | acted |
|---|---|---|---|---|---|---|
| 0.25 | normal 2 held-out | players | 2.264 | 34.0% | 0 | 0% |
| 0.25 | normal 2 held-out | L2 | 1.961 | 26.2% | 33,542 | 50% |
| 0.25 | normal 2 held-out | point-L2 | 1.949 | 25.5% | 16,944 | 38% |
| 0.25 | normal 2 held-out | oracle | 1.906 | 24.2% | 4,186 | 36% |
| 0.25 | fraud 2 | players | 1.432 | 28.9% | 0 | 0% |
| 0.25 | fraud 2 | L2 | 1.428 | 28.4% | 45,382 | 55% |
| 0.25 | fraud 2 | point-L2 | 1.465 | 29.1% | 27,929 | 44% |
| 0.25 | fraud 2 | oracle | 1.008 | 17.8% | 17,870 | 34% |
| 0.25 | fraud 3 | players | 0.659 | 11.2% | 0 | 0% |
| 0.25 | fraud 3 | L2 | 0.683 | 11.3% | 111,464 | 77% |
| 0.25 | fraud 3 | point-L2 | 0.668 | 10.8% | 40,932 | 58% |
| 0.25 | fraud 3 | oracle | 0.595 | 8.9% | 880 | 29% |
| 0.25 | STRESS | players | 1.520 | 37.7% | 0 | 0% |
| 0.25 | STRESS | L2 | 1.295 | 36.8% | 53,123 | 67% |
| 0.25 | STRESS | point-L2 | 1.296 | 36.6% | 20,287 | 57% |
| 0.25 | STRESS | oracle | 1.016 | 32.3% | 8,232 | 33% |
| 0.5 | normal 2 held-out | players | 2.264 | 29.0% | 0 | 0% |
| 0.5 | normal 2 held-out | L2 | 1.967 | 23.0% | 29,960 | 42% |
| 0.5 | normal 2 held-out | point-L2 | 1.955 | 22.2% | 13,318 | 31% |
| 0.5 | normal 2 held-out | oracle | 1.906 | 21.8% | 4,186 | 36% |
| 0.5 | fraud 2 | players | 1.432 | 25.6% | 0 | 0% |
| 0.5 | fraud 2 | L2 | 1.461 | 25.8% | 35,454 | 41% |
| 0.5 | fraud 2 | point-L2 | 1.480 | 25.8% | 20,479 | 30% |
| 0.5 | fraud 2 | oracle | 1.017 | 15.3% | 14,908 | 32% |
| 0.5 | fraud 3 | players | 0.659 | 10.2% | 0 | 0% |
| 0.5 | fraud 3 | L2 | 0.683 | 10.2% | 73,057 | 62% |
| 0.5 | fraud 3 | point-L2 | 0.668 | 9.7% | 26,998 | 38% |
| 0.5 | fraud 3 | oracle | 0.595 | 8.6% | 855 | 29% |
| 0.5 | STRESS | players | 1.520 | 35.9% | 0 | 0% |
| 0.5 | STRESS | L2 | 1.301 | 34.9% | 44,024 | 59% |
| 0.5 | STRESS | point-L2 | 1.295 | 34.4% | 13,143 | 46% |
| 0.5 | STRESS | oracle | 1.017 | 29.9% | 7,650 | 33% |
| 1.0 | normal 2 held-out | players | 2.264 | 24.8% | 0 | 0% |
| 1.0 | normal 2 held-out | L2 | 1.987 | 19.8% | 25,090 | 34% |
| 1.0 | normal 2 held-out | point-L2 | 1.974 | 19.5% | 12,066 | 26% |
| 1.0 | normal 2 held-out | oracle | 1.907 | 19.2% | 3,958 | 36% |
| 1.0 | fraud 2 | players | 1.432 | 20.9% | 0 | 0% |
| 1.0 | fraud 2 | L2 | 1.466 | 21.3% | 26,218 | 35% |
| 1.0 | fraud 2 | point-L2 | 1.495 | 21.4% | 13,382 | 21% |
| 1.0 | fraud 2 | oracle | 1.042 | 12.2% | 9,049 | 29% |
| 1.0 | fraud 3 | players | 0.659 | 9.1% | 0 | 0% |
| 1.0 | fraud 3 | L2 | 0.683 | 9.0% | 33,579 | 54% |
| 1.0 | fraud 3 | point-L2 | 0.667 | 8.8% | 15,852 | 24% |
| 1.0 | fraud 3 | oracle | 0.601 | 8.0% | 695 | 30% |
| 1.0 | STRESS | players | 1.520 | 32.6% | 0 | 0% |
| 1.0 | STRESS | L2 | 1.301 | 31.0% | 24,418 | 58% |
| 1.0 | STRESS | point-L2 | 1.286 | 30.1% | 6,857 | 36% |
| 1.0 | STRESS | oracle | 1.021 | 25.5% | 6,597 | 32% |
| 2.0 | normal 2 held-out | players | 2.264 | 18.8% | 0 | 0% |
| 2.0 | normal 2 held-out | L2 | 2.030 | 16.5% | 19,467 | 24% |
| 2.0 | normal 2 held-out | point-L2 | 2.030 | 16.8% | 10,516 | 18% |
| 2.0 | normal 2 held-out | oracle | 1.915 | 16.5% | 3,443 | 36% |
| 2.0 | fraud 2 | players | 1.432 | 15.6% | 0 | 0% |
| 2.0 | fraud 2 | L2 | 1.482 | 15.9% | 14,641 | 19% |
| 2.0 | fraud 2 | point-L2 | 1.499 | 16.2% | 11,708 | 16% |
| 2.0 | fraud 2 | oracle | 1.089 | 8.9% | 4,747 | 26% |
| 2.0 | fraud 3 | players | 0.659 | 7.3% | 0 | 0% |
| 2.0 | fraud 3 | L2 | 0.683 | 7.4% | 18,975 | 20% |
| 2.0 | fraud 3 | point-L2 | 0.670 | 7.1% | 13,135 | 17% |
| 2.0 | fraud 3 | oracle | 0.607 | 6.3% | 513 | 30% |
| 2.0 | STRESS | players | 1.520 | 25.1% | 0 | 0% |
| 2.0 | STRESS | L2 | 1.347 | 24.7% | 12,554 | 34% |
| 2.0 | STRESS | point-L2 | 1.421 | 25.6% | 720 | 9% |
| 2.0 | STRESS | oracle | 1.031 | 19.7% | 5,254 | 31% |
| 4.0 | normal 2 held-out | players | 2.264 | 15.0% | 0 | 0% |
| 4.0 | normal 2 held-out | L2 | 2.073 | 13.8% | 11,383 | 17% |
| 4.0 | normal 2 held-out | point-L2 | 2.068 | 13.8% | 7,879 | 14% |
| 4.0 | normal 2 held-out | oracle | 1.927 | 13.8% | 2,378 | 35% |
| 4.0 | fraud 2 | players | 1.432 | 10.5% | 0 | 0% |
| 4.0 | fraud 2 | L2 | 1.497 | 11.2% | 10,446 | 13% |
| 4.0 | fraud 2 | point-L2 | 1.499 | 11.2% | 10,291 | 13% |
| 4.0 | fraud 2 | oracle | 1.182 | 6.7% | 2,226 | 23% |
| 4.0 | fraud 3 | players | 0.659 | 5.0% | 0 | 0% |
| 4.0 | fraud 3 | L2 | 0.683 | 4.8% | 14,153 | 15% |
| 4.0 | fraud 3 | point-L2 | 0.670 | 4.8% | 10,735 | 13% |
| 4.0 | fraud 3 | oracle | 0.616 | 4.5% | 34 | 30% |
| 4.0 | STRESS | players | 1.520 | 15.3% | 0 | 0% |
| 4.0 | STRESS | L2 | 1.520 | 15.3% | 10 | 0% |
| 4.0 | STRESS | point-L2 | 1.520 | 15.3% | 0 | 0% |
| 4.0 | STRESS | oracle | 1.055 | 10.1% | 3,334 | 29% |
