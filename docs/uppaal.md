# C: the UPPAAL V12 model

Code: `model/uppaal/generate_uppaal.py` (generator), `model/uppaal/crosscheck.py` (checks). Models: `model/uppaal/V12_<run>.xml` (stochastic) and `V12_<run>_crosscheck.xml` (deterministic).

## 1. Principle: one spec, one data source, two implementations
The UPPAAL model is **generated** from the same input files as the Python twin (`model/twin/inputs/<run>.json`, built by `data/build_twin_inputs.py`). No number is typed into it by hand. It implements the same spec (`docs/model_spec.md`) with the same day order:

transit arrivals → supplier receipts → production (erpsim line rule) → plant → DC transfers → sales → decisions

- Decisions are the players' recorded decisions (policy replay), as in validation round 2.
- Disruptions are switchable constants (`EN_*`), as in the earlier switchable STA model. They use the Phase E mechanisms and default levels (`docs/disruptions.md`).
- The only stochastic element is the supplier lead time, drawn from the recorded PMFs with `random()`.

## 2. Model structure
- **Time:** one template `Day` with a clock `x`. A deterministic edge every time unit calls `step()`, one game day (DR-1). The automaton moves to `End` after day `LAST` and keeps ticking there without effect, so no query hits a time-lock.
- **Quantities:** UPPAAL `double`s. The model is used only for statistical model checking, which supports doubles. So the arithmetic is the same IEEE arithmetic as in the twin: no scaling, no rounding differences, no 32-bit overflow.
- **Demand** is aggregated per DC and day. This is exact: clipping a day's orders one by one to the DC stock sells min(total demand, stock), the same as clipping the total.
- **Evidence:** the generated declaration cites the evidence IDs (B2–B4, B11–B14, B16, L3, L4, M6, R5, DR-1).

| Switch | Mechanism | Default level | Evidence |
|---|---|---|---|
| `EN_SUPPLIER_DELAY` | POs created in the window arrive ⌈0.75 × lead⌉ days later | USAID q90 | E1 |
| `EN_QUALITY` | receipts lose 4.1 % (blocked), the rest arrives 2 days late, the blocked quantity is re-ordered (R5) | ERPsim Q2 max | E2 |
| `EN_LINE_DOWN` | the line stops on days 101–110 | 10 days | E3 |
| `EN_DEMAND` | demand × 1.19 on days 101–120 | normal 2 max steady month | E4 |
| `EN_TRANSIT` | shipments on days 101–120 arrive 4 days late | DataCo q95 | E5 |

Window and level constants sit next to each switch.

Queries in the XML:
1. `simulate` cross-check trace
2. `E[max lost_total]`
3. `E[max stockout_days]`
4. `Pr(lost_total > 50,000)`

## 3. Verification: how we know the UPPAAL model is the twin
With `LEAD_MODE = 1`, every lead time is fixed at its PMF median (the same rule as the twin's `lead_mode="median"`). The model is then deterministic, so it must reproduce the twin **day by day**. There are two checks:

| Check | What it proves | Status |
|---|---|---|
| **Mirror** (`crosscheck.py mirror`) | The generated XML's own constants (parsed from the file) and a line-by-line Python transcription of its functions reproduce the twin. This proves the data export and the day-aggregated formulation. | **Passed.** 3 years × 17 daily series (sales, lost demand, cumulative lost demand, stock-out days, 3 DC stocks, plant, F12 output, 8 component stocks): difference 0. Also passes with each disruption switched on and with all five together (max difference 4e-11 units, from the demand factor). Every disruption branch changes the trace. |
| **verifyta** (`crosscheck.py compare`) | UPPAAL itself executes the model as intended (syntax, semantics). | **To run locally**: UPPAAL is not available in the build environment. The parser has been tested on output in verifyta's `simulate` format, and it detects a single wrong value on the right day. |

The day-by-day comparison uses a tolerance of 0.5 units + 1e-6 relative, because verifyta may print fewer digits.

## 4. How to run it locally (UPPAAL 5)
```bash
cd model/uppaal
# 1. deterministic cross-check (must print RESULT: MATCH)
verifyta -q -s V12_normal_2_crosscheck.xml > out_normal_2.txt
python crosscheck.py compare V12_normal_2_crosscheck.xml ../twin/inputs/normal_2.json out_normal_2.txt
# repeat for fraud_2 and fraud_3
# 2. stochastic analysis: open V12_<run>.xml, set EN_* switches, run queries 2-4
```
If verifyta reports a syntax error, the error is in the generator's text template (`generate_uppaal.py`). Fix it there and regenerate; never edit the XML by hand. `python crosscheck.py expected ...` writes the twin's expected trace as CSV, for inspection in the UPPAAL simulator.

## 5. Scope and next steps
- The model reproduces the **validated open-loop physics** (round 2, decisions replayed). Controllers (L2) and the certification layer (L4) will be added as templates on top of the same `step()`: a controller template on controllable edges that sets the three levers (conversions, POs, transfers; `docs/decision_levers.md`).
- The shipping rule is not a fixed model (`docs/validation_report.md`). In UPPAAL it therefore stays replayed, with deferral as in the twin (validation Amendment 3), until L2 supplies it.
