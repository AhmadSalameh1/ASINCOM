# Validation metrics: fraud_3

50 seeds; demand, forecast and MRP days replayed; push lag1, DC split fixed.

## V1 year totals (twin median vs recorded)
- sales: 963,046 vs 1,061,267 (-9.3%)
- production_f12: 985,000 vs 1,131,000 (-12.9%)
- transferred: 985,000 vs 1,131,000 (-12.9%)
- **FAIL** (±10 %)

## V2-V4 monthly totals inside the 5-95 % band (pre-registered)

- V2 sales: 8 / 12 months; median band width 0.0% of the recorded month → **FAIL**
- V3 production_f12: 2 / 12 months; median band width 2.2% of the recorded month → **FAIL**
- V4 transferred: 3 / 12 months; median band width 4.6% of the recorded month → **FAIL**

## A1 cumulative-curve deviation (amendment 1, primary)
max over days of |twin cumulative (median seed) − recorded cumulative| / recorded year total

- sales: 9.3% → **PASS** (≤ 10 %)
- production_f12: 14.5% → **FAIL** (≤ 10 %)
- transferred: 14.5% → **FAIL** (≤ 10 %)

## V5 DC stock-out months
- recorded [1, 5, 10, 11, 12], twin (≥ 50 % of seeds) [1, 10, 11, 12]; agreement 11 / 12 → **PASS**

## V6 forecast update (MRP) → production start (F12)
- twin median 7.0 days, recorded 5.0 → **PASS** (≤ 2 days apart)

## V7 F12 component stock-outs (steady months)
- AA-R02 24.4%, AA-R05 22.2%, AA-R06 22.1%, AA-P01 0.0%, AA-P02 0.0% → **FAIL** (each ≤ 5 %)

## V8 production pause (days 100-125) → DC stock-outs
- recorded stock-out months in/after the pause [5], twin [] → **FAIL**
