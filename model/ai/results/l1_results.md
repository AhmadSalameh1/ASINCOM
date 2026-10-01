# L1 results: disruption impact prediction

Built on normal 2 (1200 train, 400 calibration episodes). Target: extra lost demand over 60 days, in days of demand. Upper bound: one-sided, nominal coverage 90 %.

## Accuracy

| set | n | share_any_loss | mean_extra_days | MAE_days | MAE_type_mean_days | spearman | AUC | Brier |
|---|---|---|---|---|---|---|---|---|
| normal 2 held-out (interior) | 400 | 33.5% | 1.020 | 0.221 | 1.203 | 0.799 | 0.993 | 0.040 |
| fraud 2 (policy shift) | 2000 | 8.6% | 0.138 | 0.777 | 0.860 | 0.382 | 0.895 | 0.168 |
| fraud 3 (policy shift) | 2000 | 12.2% | 0.169 | 0.513 | 0.823 | 0.478 | 0.874 | 0.147 |
| STRESS, all years (severity shift) | 1800 | 36.2% | 1.383 | 1.123 | 1.211 | 0.714 | 0.901 | 0.124 |

## Upper bound: coverage (target 90 %) and mean bound (days of demand)

| set | cov_cqr | cov_cqr_worst_type | upper_cqr_mean_days | cov_mondrian | cov_mondrian_worst_type | upper_mondrian_mean_days | cov_weighted | inf_weighted | upper_weighted_mean_days | cov_recal | cov_recal_worst_type | upper_recal_mean_days |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal 2 held-out (interior) | 88.0% | 83.1% | 1.44 | 87.2% | 75.0% | 1.45 | 88.0% | 0.0% | 1.44 | 89.7% | 85.5% | 1.69 |
| fraud 2 (policy shift) | 84.9% | 65.8% | 1.02 | 84.1% | 62.8% | 1.03 | 100.0% | 100.0% | 0.31 | 88.7% | 72.2% | 1.02 |
| fraud 3 (policy shift) | 79.0% | 59.8% | 0.93 | 77.7% | 56.6% | 0.94 | 100.0% | 100.0% | inf | 89.9% | 80.4% | 0.94 |
| STRESS, all years (severity shift) | 61.2% | 52.4% | 1.14 | 59.2% | 52.5% | 1.16 | 77.5% | 49.2% | 1.22 | 87.2% | 74.5% | 3.63 |

## Ablation: what the predictor needs to see

| model | normal 2 held-out (interior) | fraud 2 (policy shift) | fraud 3 (policy shift) | STRESS, all years (severity shift) |
|---|---|---|---|---|
| gbm (notice+state) | 0.221 | 0.777 | 0.513 | 1.123 |
| gbm-notice | 0.940 | 0.774 | 0.707 | 1.165 |
| gbm-state | 1.459 | 1.439 | 1.067 | 1.764 |
| ridge (notice+state) | 1.190 | 2.408 | 3.388 | 2.999 |

(MAE in days of demand)


## Supplement: leave-one-year-out

| set | n | share_any_loss | mean_extra_days | MAE_days | MAE_type_mean_days | spearman | AUC | Brier |
|---|---|---|---|---|---|---|---|---|
| LOYO test normal_2 | 2000 | 32.8% | 0.905 | 0.769 | 0.887 | 0.527 | 0.831 | 0.239 |
| LOYO test fraud_2 | 2000 | 8.6% | 0.138 | 0.535 | 0.518 | 0.373 | 0.898 | 0.129 |
| LOYO test fraud_3 | 2000 | 12.2% | 0.169 | 0.457 | 0.477 | 0.480 | 0.874 | 0.107 |


| set | cov_cqr | cov_cqr_worst_type | upper_cqr_mean_days | cov_mondrian | cov_mondrian_worst_type | upper_mondrian_mean_days | cov_weighted | inf_weighted | upper_weighted_mean_days | cov_recal | cov_recal_worst_type | upper_recal_mean_days |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LOYO test normal_2 | 70.2% | 34.0% | 0.38 | 71.5% | 35.6% | 0.39 | 100.0% | 100.0% | inf | 91.6% | 65.5% | 1.99 |
| LOYO test fraud_2 | 85.7% | 68.8% | 0.82 | 84.0% | 63.4% | 0.82 | 86.9% | 56.0% | 0.94 | 86.5% | 70.6% | 0.81 |
| LOYO test fraud_3 | 93.9% | 86.8% | 0.77 | 92.5% | 85.5% | 0.77 | 99.2% | 77.5% | 1.08 | 92.9% | 84.1% | 0.77 |
