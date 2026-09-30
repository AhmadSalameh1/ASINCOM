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

## Amendment 1 (made on the calibration year only, before any validation-year run in Phase D)
1. **Why:** with demand, forecasts and MRP days all replayed, the twin is nearly deterministic. On normal 2 the median width of the 5–95 % band is **0.2–0.8 %** of the recorded monthly sales and transfers. A one-day shift across a month boundary therefore fails V2–V4 even when the dynamics are right, so band inclusion is not a meaningful measure here.
2. **Added primary metric A1 (shift-tolerant):** for sales, production and transfers, the maximum over days of |twin cumulative (median seed) − recorded cumulative| divided by the recorded year total. **Pass if ≤ 10 %.** V2–V4 are still computed and reported as pre-registered.
3. **V6 measurement corrected to the protocol's own definition:** forecast update → production start. The first implementation measured conversion → start by mistake; conversion is a separate player step, see `docs/twin.md`.
4. **Verdict rule with A1:**
   - **Validated** if V1 and A1-sales pass in both years, and at most two of {A1-production, A1-transfers, V5, V6, V7, V8} fail per year, each with a diagnosis.
   - V2–V4 are reported but are not part of the verdict.

### Configuration frozen on normal 2
| Setting | Choice | Evidence (normal 2 only) |
|---|---|---|
| line rule | `erpsim` | full batch at start 78/78; one-day changeover on product switch |
| other products | `mrp` (planning level) | purchasing depends on all products' plans (rule R4) |
| MRP timing | `recorded` | orders are converted 2–5 days after forecast updates, in bursts right after the POs |
| push rule | `lag1` | transfers correlate 0.72 with the previous day's output, 0.12 with the same day's |
| DC split | `fixed` (fitted shares) | the cover-balancing split was tested and rejected: lost demand rose from 45k to 79k |

### Calibration-year result (normal 2, 20 seeds), for reference
- **Pass:** V1 (sales −3.2 %, production −1.7 %, transfers −1.7 %), A1-sales 3.2 %, A1-production 9.3 %, V6 (7 vs 5 days), V8.
- **Fail:**
  - A1-transfers 17.0 %
  - V5 9/12 months
  - V7: wheat and oats (R05, R06) end 18 % of steady days at zero stock, against ≈ 0 recorded

These known weaknesses are carried into the validation; they are not tuned away.

## Amendment 2: validation round 2 (made on normal 2 only, before the round-2 run on fraud 2 and fraud 3)
**Disclosure:** round 1 (`docs/validation_report.md`) has been run and its fraud 2 and fraud 3 results were seen. Round 2 therefore has weaker evidential value than round 1, and both rounds are reported.

**Design change (why round 1 was the wrong test):** DR-3 says the validation must replay each year's own policy, so that it tests the **physics**. Round 1 instead generated the player decisions with policy models (the MRP replica, the push rule). The normal 2 diagnosis showed that most failures came from those decisions, especially the just-in-time conversion of planned orders, not from the physics. Round 2 therefore separates the two:
- **Physics validation (round 2):** all recorded player decisions are replayed:
  - production-order conversions (day, product, quantity)
  - POs (day, material, quantity)
  - transfers per DC (day, DC, quantity, clipped to plant stock)

  Simulated: supplier lead times (sampled), the production line (`erpsim`, changeover 0.6 day), component consumption, the plant and DC stock paths, and sales clipped to DC stock.
- **Policy-model validation (separate):** the MRP replica is tested against the recorded decisions (`docs/policy_acceptance.md`: production 20/21, purchasing 29/37). The push rule `lag1` is tested against the recorded transfers given the recorded production: on normal 2 it gives **A1-transfers 17.6 %, a FAIL**, so the push policy model is not accepted.

**Two data-handling faults fixed (found on normal 2):**
1. Pre-start POs (game initialisation) had been dropped from the replay. Rule C4 was meant for lead-time statistics only, and these POs are real opening stock.
2. Replayed orders now consume what was **actually issued** (AUFM), not what was reserved.

**Changeover 0.6 day:** recorded idle time between producing days is 0.84 days across a product switch vs 0.25 without one, and output on the switch day is 16k vs 24k. Results on normal 2 are insensitive to it (0, 0.6 or 1 day).

**Metrics and verdict rule:** unchanged (Amendment 1). A1-transfers becomes weak under transfer replay (only the clipping can create a difference); it is reported with that caveat.

**Frozen round-2 configuration:** `policy=replay`, `push_rule=replay`, `line_rule=erpsim`, `changeover_days=0.6`, `demand_mode=replay`, 50 seeds.

**Normal 2 result under this configuration (20 seeds):**
- V1: sales −2.2 %, production 0.0 %
- A1: sales 2.2 %, production 7.1 %, transfers 2.2 %
- V5: 11/12; V6: 6 vs 5 days; V8: pass
- V7: blueberries (R02) 5.5 %, fail; all other components 0 %

## Output
`model/twin/validation/` holds one report per year. `docs/validation_report.md` gives the verdict.
