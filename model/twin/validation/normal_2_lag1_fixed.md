# Validation metrics: normal_2

50 seeds; demand, forecast and MRP days replayed; push lag1, DC split fixed.

## V1 year totals (twin median vs recorded)
- sales: 1,342,088 vs 1,391,000 (-3.5%)
- production_f12: 1,361,000 vs 1,391,000 (-2.2%)
- transferred: 1,361,000 vs 1,391,000 (-2.2%)
- **PASS** (±10 %)

## V2-V4 monthly totals inside the 5-95 % band (pre-registered)

- V2 sales: 7 / 12 months; median band width 1.2% of the recorded month → **FAIL**
- V3 production_f12: 7 / 12 months; median band width 8.5% of the recorded month → **FAIL**
- V4 transferred: 4 / 12 months; median band width 2.1% of the recorded month → **FAIL**

## A1 cumulative-curve deviation (amendment 1, primary)
max over days of |twin cumulative (median seed) − recorded cumulative| / recorded year total

- sales: 3.7% → **PASS** (≤ 10 %)
- production_f12: 9.2% → **PASS** (≤ 10 %)
- transferred: 17.1% → **FAIL** (≤ 10 %)

## V5 DC stock-out months
- recorded [1, 2, 3, 10, 11, 12], twin (≥ 50 % of seeds) [1, 2, 8, 9, 10, 11, 12]; agreement 9 / 12 → **FAIL**

## V6 forecast update (MRP) → production start (F12)
- twin median 7.0 days, recorded 5.0 → **PASS** (≤ 2 days apart)

## V7 F12 component stock-outs (steady months)
- AA-R02 6.7%, AA-R05 18.1%, AA-R06 18.8%, AA-P01 0.1%, AA-P02 0.2% → **FAIL** (each ≤ 5 %)

## V8 production pause (days 171-223) → DC stock-outs
- recorded stock-out months in/after the pause [10, 11, 12], twin [9, 10, 11, 12] → **PASS**
