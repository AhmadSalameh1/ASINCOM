# Validation metrics: fraud_2

50 seeds; demand, forecast and MRP days replayed; push lag1, DC split fixed.

## V1 year totals (twin median vs recorded)
- sales: 1,042,365 vs 1,094,931 (-4.8%)
- production_f12: 1,065,000 vs 1,100,000 (-3.2%)
- transferred: 1,065,000 vs 1,100,000 (-3.2%)
- **PASS** (±10 %)

## V2-V4 monthly totals inside the 5-95 % band (pre-registered)

- V2 sales: 10 / 12 months; median band width 0.0% of the recorded month → **PASS**
- V3 production_f12: 6 / 12 months; median band width 77.8% of the recorded month → **FAIL**
- V4 transferred: 8 / 12 months; median band width 69.1% of the recorded month → **FAIL**

## A1 cumulative-curve deviation (amendment 1, primary)
max over days of |twin cumulative (median seed) − recorded cumulative| / recorded year total

- sales: 4.7% → **PASS** (≤ 10 %)
- production_f12: 17.3% → **FAIL** (≤ 10 %)
- transferred: 17.3% → **FAIL** (≤ 10 %)

## V5 DC stock-out months
- recorded [1, 4, 5, 11, 12], twin (≥ 50 % of seeds) [1, 4, 5]; agreement 10 / 12 → **PASS**

## V6 forecast update (MRP) → production start (F12)
- twin median 8.0 days, recorded 5.0 → **FAIL** (≤ 2 days apart)

## V7 F12 component stock-outs (steady months)
- AA-R02 19.4%, AA-R05 15.2%, AA-R06 15.9%, AA-P01 0.0%, AA-P02 0.0% → **FAIL** (each ≤ 5 %)

## V8 production pause (days 23-83) → DC stock-outs
- recorded stock-out months in/after the pause [4, 5], twin [4, 5] → **PASS**
