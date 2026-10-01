# Validation metrics: normal_2

50 seeds; demand, forecast and MRP days replayed; policy replay, push replay_deferred, DC split fixed, demand replay.

## V1 year totals (twin median vs recorded)
- sales: 1,383,973 vs 1,391,000 (-0.5%)
- production_f12: 1,391,000 vs 1,391,000 (+0.0%)
- transferred: 1,391,000 vs 1,391,000 (+0.0%)
- **PASS** (±10 %)

## V2-V4 monthly totals inside the 5-95 % band (pre-registered)

- V2 sales: 11 / 12 months; median band width 0.0% of the recorded month → **PASS**
- V3 production_f12: 6 / 12 months; median band width 0.0% of the recorded month → **FAIL**
- V4 transferred: 10 / 12 months; median band width 0.0% of the recorded month → **PASS**

## A1 cumulative-curve deviation (amendment 1, primary)
max over days of |twin cumulative (median seed) − recorded cumulative| / recorded year total

- sales: 0.5% → **PASS** (≤ 10 %)
- production_f12: 6.9% → **PASS** (≤ 10 %)
- transferred: 2.2% → **PASS** (≤ 10 %)

## V5 DC stock-out months
- recorded [1, 2, 3, 10, 11, 12], twin (≥ 50 % of seeds) [1, 2, 3, 10, 11, 12]; agreement 12 / 12 → **PASS**

## V6 forecast update (MRP) → production start (F12)
- twin median 6.0 days, recorded 5.0 → **PASS** (≤ 2 days apart)

## V7 F12 component stock-outs (steady months)
- AA-R02 5.8%, AA-R05 0.0%, AA-R06 0.0%, AA-P01 0.1%, AA-P02 0.0% → **FAIL** (each ≤ 5 %)

## V8 production pause (days 171-223) → DC stock-outs
- recorded stock-out months in/after the pause [10, 11, 12], twin [10, 11, 12] → **PASS**
