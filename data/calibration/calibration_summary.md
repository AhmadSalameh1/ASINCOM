# Calibration derived from ERPsim

Calibration run: normal_2. Validation runs: fraud_2, fraud_3 (fraud-labelled documents excluded). Quantities in real units; model uses real / 100. Times in game days.

## Headline statistics across runs

|                            |   normal_2 |   fraud_2 |   fraud_3 |   cv_across_runs |
|:---------------------------|-----------:|----------:|----------:|-----------------:|
| customers                  |     71     |    71     |    71     |            0     |
| product_units_per_game_day |   5795.83  |  4562.21  |  4421.95  |            0.153 |
| product_share_of_units     |      0.476 |     0.364 |     0.336 |            0.189 |
| order_qty_mean             |    477.477 |   449.943 |   426.19  |            0.057 |
| inter_order_days_mean      |      9.824 |     9.598 |    10.419 |            0.043 |
| inter_order_days_median    |      8     |     8     |     9     |            0.069 |
| lead_time_days_median      |      3.138 |     3.08  |     2.978 |            0.026 |
| lead_time_days_q95         |      5.238 |     6.058 |     5.327 |            0.081 |
| food_po_qty_mean           |  23852     | 23634.3   | 35113.9   |            0.238 |
| production_batch_mean      |  37594.6   | 37200     | 38032.3   |            0.011 |
| production_days_median     |      4.183 |     3.992 |     2.984 |            0.173 |
| transfer_qty_mean          |   8306.2   |  7189.5   |  7048.4   |            0.092 |
