# Python reference twin (Phase C, step 2)

Code: `model/twin/twin.py` (simulator) and `model/twin/run_twin.py` (many seeds, compared with the recorded year). Inputs per game year: `model/twin/inputs/<run>.json`, built by `data/build_twin_inputs.py` from the SAP tables. The simulator itself knows nothing about SAP.

## Structure (docs/model_spec.md)
- **Time:** one step = one game day.
- **Within a day:** supplier receipts → production → plant-to-DC push → customer orders → decisions.
- **Decisions:** forecast updates trigger the three-product MRP (rules R1–R6 in `data/mrp_replica.py`).

## Modes
| Option | Values | Use |
|---|---|---|
| `forecast_mode` | `replay` | The players' recorded forecast updates. This is the only mode so far; a forecast rule for experiments comes later. |
| `demand_mode` | `replay` / `sample` | `replay` replays the recorded customer orders (day, customer, quantity). Sales are still clipped to the twin's own DC stock, which isolates the supply-side physics for validation. `sample` draws inter-order times and order sizes from ledger D1–D5, for experiments. |
| `line_rule` | **`erpsim`** (default) / `fifo_block` / `fifo_skip` | See below. |
| `others` | **`mrp`** (default) / `replay` | How the other products (F16, F15) are represented. See below. |
| `push_rule` | `replay_deferred` (nominal since validation Amendment 3) / `replay` / `lag1` / `fraction` | `replay_deferred` replays the recorded transfers; a part that cannot ship for lack of plant stock stays owed to its DC and ships as soon as stock allows. Plain `replay` strands that part at the plant (`docs/validation_report.md`, round 3). |
| `lead_mode` | **`sample`** (default) / `median` | `median` fixes every supplier lead time at its PMF median. The twin is then deterministic, which is used only for the day-by-day cross-check with the UPPAAL model (`docs/uppaal.md`). |

## Three rules that the build process forced, each with its evidence
1. **Customer orders hold several F12 lines.** 1,489 orders have 2,914 lines (1–5 lines per order). Demand is therefore the order total (mean 931), not the line size (477).
   - Ledger D3 was corrected accordingly, and D5 was added.
   - Before this fix the twin produced only 58 % of the year's sales.
2. **The other products must be planned, not only replayed.** Component purchasing depends on all products' plans (rule R4, `docs/policy_acceptance.md`).
   - `others = mrp` plans F16 and F15 from their own replayed forecasts and replayed sales, at the planning level only: total stock, no customers or DCs.
   - This is the risk DR-2 anticipated for shared components, now confirmed. See the DR-2 update.
3. **Production line rule `erpsim`.**
   - All **78 of 78** recorded orders had their **whole batch's components** in stock when they started.
   - The gap between consecutive orders has a median of **1 day on a product switch and 0 days otherwise**, so a product switch costs one day.
   - The raw postings show a **strictly serial line at 24,000 units/day**; an order ending mid-day hands over to the next.

   The rule is therefore: FIFO, start only with the full batch in stock, one changeover day on a product switch.

**Interpretation needed for validation.** The recorded order "creation" time is the moment a *planned* order was converted into a production order. The players converted just before the line reached the order. So the recorded creation → start time (median 2 days) is **not comparable** with the twin's MRP → start time. The comparable recorded measure is **forecast update (MRP run) → start: median 5 days, q75 7**. The twin gives median 7, q75 8, of which about 1 day is the day convention.

## Build check (20 seeds, demand replay; not yet the Phase D validation)
| | normal 2 (calibration) | fraud 2 | fraud 3 |
|---|---|---|---|
| Year sales, twin / recorded | 1.353M / 1.391M (97 %) | 1.045M / 1.095M (95 %) | 0.966M / 1.061M (91 %) |
| Months with recorded sales inside the 90 % band | 9 / 12 | 10 / 12 | 8 / 12 |
| Months with recorded production inside the band | 7 / 12 | 8 / 12 | 2 / 12 |
| Months with recorded transfers inside the band | 1 / 12 | 4 / 12 | 3 / 12 |

Year purchasing totals in normal 2 match the recorded POs within 1.4 % for every component, on 38 PO days against 37 recorded MRP runs.

## Open issues for Phase D (validation)
1. **Plant → DC transfers are the weakest part.** The recorded monthly transfers fall inside the band in only 1–4 of 12 months. The push rule (a daily fraction of plant stock with fixed DC shares) is the only fitted policy element, and it differs strongly by year (daily fraction 0.39 / 0.19 / 0.27). Candidate: model the push as event-driven, shipping 0–1 days after production output (47 of 64 recorded transfers).
2. **Component stock-outs.** The twin ends 20–50 % of steady days with zero stock of F16-only components (R01, R04), against ≈ 0 recorded (K1). Candidate: the players' just-in-time conversion of planned orders, which the twin doesn't model; the twin converts all planned orders at the MRP run.
3. **fraud 3 production timing** (2 / 12 months inside the band). Check its recipe change and its production pause (B17: 25 days).
4. **Queue time:** about 2 days longer than recorded (see the interpretation above). Compare distributions formally in Phase D.
