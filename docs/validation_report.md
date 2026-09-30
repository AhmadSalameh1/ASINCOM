# Validation report (Phase D, round 1)

The protocol and its amendment (`docs/validation_protocol.md`) were committed before this run (commits `e381b96`, `7e5949f`). Configuration frozen on normal 2. The run used 50 seeds with demand, forecasts and MRP days replayed. Per-year details are in `model/twin/validation/`.

## Verdict: **NOT VALIDATED** (round 1)
| | V1 year totals | A1 sales | A1 production | A1 transfers | V5 stock-out months | V6 update → start | V7 components | V8 pause propagation | Other failures |
|---|---|---|---|---|---|---|---|---|---|
| normal 2 (calibration, reference) | ✅ | ✅ 3.7 % | ✅ 9.2 % | ❌ 17.1 % | ❌ 9/12 | ✅ 7 vs 5 | ❌ | ✅ | 3 |
| **fraud 2** | ✅ (sales −4.8 %) | ✅ 4.7 % | ❌ 17.3 % | ❌ 17.3 % | ✅ 10/12 | ❌ 8 vs 5 | ❌ | ✅ | **4 (> 2)** |
| **fraud 3** | ❌ (production −12.9 %) | ✅ 9.3 % | ❌ 14.5 % | ❌ 14.5 % | ✅ 11/12 | ✅ 7 vs 5 | ❌ | ❌ | **core fails** |

V2–V4 (pre-registered, reported but not part of the verdict per Amendment 1):
- V2 sales months 7 / 10 / 8
- V3 production months 7 / 6 / 2
- V4 transfers months 4 / 8 / 3

## What generalises to the unseen years
- **Customer-side dynamics:** cumulative sales stay within 5–9 % of the record in both validation years (A1-sales), and year sales within −4.8 % / −9.3 %.
- **Stock-out timing:** the months with DC stock-outs agree in 10 / 12 and 11 / 12 months (V5).
- **Propagation of the real production pause:** in fraud 2, the recorded pause (days 23–83) produces DC stock-outs in the same months as recorded (V8). In fraud 3 the recorded month-5 stock-out is not reproduced.

## What does not: one root mechanism
**Component supply timing.** In every year, including the calibration year, the twin's food components (blueberries, wheat, oats) end 15–24 % of steady days at zero stock, against ≈ 0 recorded (V7). Production then waits for deliveries, so it falls short or late (A1-production, and V1 in fraud 3), and transfers, which follow production one day later, inherit the error (A1-transfers).

Diagnosis on the calibration year (normal 2, wheat R05, days 61–100):
- **Quantities agree:** cumulative receipts by day 120 are 620 k in the twin vs 634 k recorded (−2 %).
- **Timing does not:** recorded receipts arrive 2–7 days earlier relative to consumption. Mean steady wheat stock is **26 k in the twin vs 45 k recorded**, a gap of about 2 days of full-speed consumption (8,400 kg/day). The recorded stock never reaches zero.

The cause is **not yet established**. Candidates, to be tested on normal 2 only:
1. **Receipt-day convention.** The twin receives a PO on day d + L after deciding on day d. The recorded lead L is counted from the first tick after PO creation, so a one-day misalignment is possible.
2. **When purchases for planned orders are made.** In the record, POs are created seconds after a forecast update. Conversion into production orders follows minutes later, which is several game days, since one game day is about 58 s. The twin buys on the recorded MRP days using its own state at that moment.
3. **Purchases for planned orders that were later reduced** (for example the superseded update 4: components bought for 41,000 units that were never produced). These leave a real buffer that the twin, planning on the latest forecast, does not build.

## Consequences
- The twin is **not yet fit** for claims about production or component-level disruptions (supplier delay, shortage, quality loss). These are exactly the mechanisms that fail.
- It is closer to fit for claims about **demand-side behaviour and stock-out timing**, but the protocol's overall verdict still stands.
- Any fix found on normal 2 and re-tested on fraud 2 and fraud 3 is a **second validation round on years that have already been seen**. It has weaker evidential value and will be reported as such.
