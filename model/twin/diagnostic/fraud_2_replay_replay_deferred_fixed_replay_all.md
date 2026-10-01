# Validation metrics: fraud_2

50 seeds; demand, forecast and MRP days replayed; policy replay, push replay_deferred, DC split fixed, demand replay_all.

## V1 year totals (twin median vs recorded)
- sales: 1,086,873 vs 1,094,931 (-0.7%)
- production_f12: 1,116,000 vs 1,100,000 (+1.5%)
- transferred: 1,100,000 vs 1,100,000 (+0.0%)
- **PASS** (±10 %)

## V2-V4 monthly totals inside the 5-95 % band (pre-registered)

- V2 sales: 8 / 12 months; median band width 0.0% of the recorded month → **FAIL**
- V3 production_f12: 2 / 12 months; median band width 0.0% of the recorded month → **FAIL**
- V4 transferred: 10 / 12 months; median band width 0.0% of the recorded month → **PASS**

## A1 cumulative-curve deviation (amendment 1, primary)
max over days of |twin cumulative (median seed) − recorded cumulative| / recorded year total

- sales: 1.0% → **PASS** (≤ 10 %)
- production_f12: 8.9% → **PASS** (≤ 10 %)
- transferred: 3.6% → **PASS** (≤ 10 %)

## V5 DC stock-out months
- recorded [1, 4, 5, 11, 12], twin (≥ 50 % of seeds) [1]; agreement 8 / 12 → **FAIL**

## V6 forecast update (MRP) → production start (F12)
- twin median 7.0 days, recorded 5.0 → **PASS** (≤ 2 days apart)

## V7 F12 component stock-outs (steady months)
- AA-R02 0.0%, AA-R05 0.3%, AA-R06 0.4%, AA-P01 0.0%, AA-P02 0.0% → **PASS** (each ≤ 5 %)

## V8 production pause (days 23-83) → DC stock-outs
- recorded stock-out months in/after the pause [4, 5], twin [] → **FAIL**
