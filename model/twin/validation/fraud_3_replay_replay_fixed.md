# Validation metrics: fraud_3

50 seeds; demand, forecast and MRP days replayed; policy replay, push replay, DC split fixed.

## V1 year totals (twin median vs recorded)
- sales: 1,049,502 vs 1,061,267 (-1.1%)
- production_f12: 1,179,000 vs 1,131,000 (+4.2%)
- transferred: 1,107,000 vs 1,131,000 (-2.1%)
- **PASS** (±10 %)

## V2-V4 monthly totals inside the 5-95 % band (pre-registered)

- V2 sales: 10 / 12 months; median band width 0.0% of the recorded month → **PASS**
- V3 production_f12: 1 / 12 months; median band width 0.0% of the recorded month → **FAIL**
- V4 transferred: 11 / 12 months; median band width 0.0% of the recorded month → **PASS**

## A1 cumulative-curve deviation (amendment 1, primary)
max over days of |twin cumulative (median seed) − recorded cumulative| / recorded year total

- sales: 1.1% → **PASS** (≤ 10 %)
- production_f12: 9.5% → **PASS** (≤ 10 %)
- transferred: 2.1% → **PASS** (≤ 10 %)

## V5 DC stock-out months
- recorded [1, 5, 10, 11, 12], twin (≥ 50 % of seeds) [1, 4]; agreement 7 / 12 → **FAIL**

## V6 forecast update (MRP) → production start (F12)
- twin median 8.0 days, recorded 5.0 → **FAIL** (≤ 2 days apart)

## V7 F12 component stock-outs (steady months)
- AA-R02 6.7%, AA-R05 5.2%, AA-R06 5.2%, AA-P01 0.0%, AA-P02 0.0% → **FAIL** (each ≤ 5 %)

## V8 production pause (days 100-125) → DC stock-outs
- recorded stock-out months in/after the pause [5], twin [] → **FAIL**
