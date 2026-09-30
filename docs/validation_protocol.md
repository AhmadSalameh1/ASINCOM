# Validation protocol (Phase D)

This protocol is written and committed **before** any validation-year result is examined in Phase D. The Phase C build check (`docs/twin.md`) had already shown fraud 2 and fraud 3 year totals. That is disclosed here, and no model change was based on it.

## Rules
1. **Model changes use normal 2 only** (the calibration year, DR-0). Nothing is tuned on fraud 2 or fraud 3.
2. **Validation runs** use fraud 2 and fraud 3 with their own exogenous inputs, following DR-3 (policy replay):
   - recorded forecasts
   - recorded customer orders (demand replay)
   - their own recipes
   - their own fitted push parameters (the push rule's *form* is fixed on normal 2; only its parameters are re-estimated per year, because it is a player policy)
3. **Twin settings:** 50 seeds per year; `line_rule = erpsim`, `others = mrp`.
4. **Reporting:** every metric is reported for both years, including the ones that fail. A failure is followed by a diagnosis, never by tuning on the failing year.

## Metrics and pass thresholds
Here "band" means the 5–95 % range across seeds.

| ID | What | Recorded source | Pass if |
|---|---|---|---|
| V1 | Year totals: F12 sales, production, transfers | MSEG / VBAP | twin median within **±10 %** of recorded |
| V2 | Monthly F12 sales inside the band | VBAP by game day | **≥ 9 of 12** months |
| V3 | Monthly F12 production inside the band | MSEG 101 | **≥ 9 of 12** months |
| V4 | Monthly transfers to DCs inside the band | MSEG 301 | **≥ 9 of 12** months |
| V5 | DC stock-out timing: months with ≥ 1 zero-stock day at some DC | DC stock paths (ledger W1) | twin's modal month set matches the recorded set in **≥ 10 of 12** months |
| V6 | Planning-to-production delay: F12 forecast update (MRP) → production start | PBHI, AUFM | medians differ by **≤ 2 days** |
| V7 | Component stock-outs in steady months (F12 components) | ledger K1 | twin share **≤ 5 %** for each F12 component |
| V8 | Production-pause propagation: recorded pause (B17) and its DC stock-outs | B17, W1 | twin shows DC stock-outs in the same month(s) as recorded |

**Overall verdict:**
- **Validated** if V1 and V2 pass in both years and at most two of the other metrics fail per year, each with a diagnosis.
- Otherwise **not validated**, with the failing mechanisms named.

## Output
`model/twin/validation/` holds one report per year. `docs/validation_report.md` gives the verdict.
