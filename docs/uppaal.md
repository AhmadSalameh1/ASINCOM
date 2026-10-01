# C: the UPPAAL V12 model, with the levers and the certified tree

Code:
- `model/uppaal/generate_uppaal.py`: the generator
- `model/uppaal/crosscheck.py`: the checks
- `model/ai/export_tree.py`: the trees as arrays (`model/ai/results/tree_*.json`)

## 1. Principle: one spec, one data source, two implementations
The UPPAAL model is **generated** from the same input files as the Python twin (`model/twin/inputs/<run>.json`) and from the exported certified trees. No number is typed in by hand. It implements the same spec (`docs/model_spec.md`) with the same day order:

[notice day: observe the plant, choose the response] → transit arrivals → supplier receipts → production (erpsim line rule) → plant → DC transfers → sales → other products' sales → decisions

- **Decisions:** the players' recorded decisions (policy replay; transfers deferred, validation Amendment 3). From the disruption notice on, a response is added using **the players' three levers**, exactly as `ResponseController` in `model/twin/controllers.py` does it:

| Lever | UPPAAL | Python |
|---|---|---|
| component buffer (POs) | `decide()`: POs up to `ACT_PO` days of 20-day consumption, rounded to the MARC step | `po_days` |
| extra F12 batch (conversion) | `decide()`: a 24,000-unit order with the recipe in force, plus lot-for-lot POs | `fg_units` |
| F12 line priority (conversions) | `decide()`: other products' conversions held while F12 waits, for 20 days | `prio` |
| DC rebalancing (transfers) | `push()` + `water_fill()`: plant stock left after the owed transfers, split by days of cover | `ship` |

- **The certified tree** (`docs/ai_layers.md`, L3/L4) is embedded as arrays (`TREE_F/T/L/R/A`). It is evaluated by `tree_action()` on **the same 34 features as in Python**, which `observe()` computes inside the model at the start of the notice day: component cover, queue, plant, DC cover, recent losses, transfer backlog, and the notice.
  - Each year's model embeds its own certified tree: normal 2's, and the adapted trees for fraud 2 and fraud 3.
  - Evaluating the arrays in double precision agrees with scikit-learn on all 9,800 episodes.
- **The other products** (planning level, DR-2) are included: their stock and replayed sales. The certified property counts their lost sales, because the priority lever moves loss onto them.

### Configuration constants
| Constant | Values |
|---|---|
| `SCEN_MODE` | 0 = the switches (`EN_*`, the earlier switchable style, no notice); 1 = one fixed disruption (`FIX_*`); 2 = **one disruption sampled at t = 0 within its evidence bounds**, at a start day drawn uniformly over the steady months: exactly the AI-episode population (`model/ai/episodes.py`) |
| `CTRL_MODE` | 0 = players only; 1 = fixed action `ACT_FIXED`; 2 = certified tree |
| `LEAD_MODE` | 0 = sampled lead times; 1 = PMF medians (deterministic) |

### Files
| File | Configuration | Use |
|---|---|---|
| `V12_<run>.xml` | switches, players, sampled leads | disruption studies in the earlier style |
| `V12_<run>_ai_tree.xml` / `_ai_players.xml` | SCEN 2, tree / players | **the SMC certificate**: query 2, `Pr[<=H](<> win_done && win_ok)` |
| `V12_<run>_crosscheck.xml` | switches, players, median leads | deterministic check of the physics |
| `V12_<run>_crosscheck_tree.xml` | one disruption, tree, median leads | deterministic check of features + tree + levers |
| `V12_<run>_crosscheck_levers.xml` / `_ship.xml` | one disruption, actions po10+fg+prio / ship | deterministic check of every lever |

### Property
`win_ok`: the lost demand of all products over the 60 days from the notice is at most `L_STAR` = 1 day of demand (the 20-day mean before the notice). This is the same property as in L4.

### Modelling notes
- **Quantities are `double`s** (statistical model checking supports them), so the arithmetic is the twin's IEEE arithmetic. UPPAAL's plain `int` is 16-bit, so every quantity array is `double`. A script checks every generated file: no `int` constant is outside [−32768, 32767].
- **Rounding** uses `ceil_d` and `floor_d`. They are written to be correct whatever `fint`'s rounding mode is.

## 2. Verification
| Check | What it proves | Status |
|---|---|---|
| **Mirror suite** (`crosscheck.py suite`) | The XML's own constants, parsed from the file, together with a line-by-line Python transcription of its functions, reproduce the twin (`ResponseController` + `Observer` + `lead_mode="median"`). The trace is compared day by day; the 34 features and the chosen action are also compared. | **Passed: 591 / 591 configurations** (normal 2: 182, fraud 2: 227, fraud 3: 182). These cover every disruption type at 4–5 notice days, under each of the 8 actions and the tree, plus the switches. Notice days are chosen so that the ship and priority levers actually bite. Max trace difference 1e-10 units; feature difference 0; identical actions. |
| **Stochastic mirror** (`crosscheck.py smc`) | The XML's random semantics (lead-time and disruption sampling) give the same service rate as the independent Python episodes of L4. | **Passed**, within sampling error (table below). |
| **verifyta** (`crosscheck.py compare`) | UPPAAL itself executes the model as intended (syntax, semantics). | **To run locally**: UPPAAL is not available in the build environment. |

Service rate, P(60-day loss ≤ 1 day of demand), with 95 % intervals:

| | L4 (Python episodes) | stochastic mirror of the UPPAAL file (2,000 runs) |
|---|---|---|
| normal 2, players | 77.6% [75.7, 79.4] | 78.3 % [76.5, 80.1] |
| normal 2, tree | 80.0% [78.2, 81.8] | 80.0 % [78.2, 81.8] |
| fraud 2, players | 79.0% [77.2, 80.8] | 79.1 % [77.3, 80.9] |
| fraud 2, adapted tree | 85.9% [84.1, 87.5] | 87.7 % [86.2, 89.1] |
| fraud 3, players | 90.9% [89.6, 92.1] | 92.0 % [90.7, 93.1] |
| fraud 3, adapted tree | 91.4% [89.9, 92.7] | 91.3 % [90.0, 92.5] |

**These are the values `verifyta` should reproduce with query 2 on the `_ai_` files**, within its own confidence interval.

## 3. How to run it locally (UPPAAL 5)
```bash
cd model/uppaal
# 1. deterministic checks (each must print RESULT: MATCH)
for f in V12_normal_2_crosscheck V12_normal_2_crosscheck_tree V12_normal_2_crosscheck_levers V12_normal_2_crosscheck_ship; do
  verifyta -q -s $f.xml > $f.out
  python crosscheck.py compare $f.xml ../twin/inputs/normal_2.json $f.out
done
# repeat with fraud_2 and fraud_3
# 2. certificates: query 2 (Pr) on the AI models; compare with the table above
verifyta -q V12_normal_2_ai_tree.xml
verifyta -q V12_normal_2_ai_players.xml
```
- If verifyta reports a syntax error, it comes from the generator's text template (`generate_uppaal.py`). Fix it there and regenerate; never edit the XML by hand.
- `python crosscheck.py expected ...` writes the twin's expected trace as CSV.
- `python crosscheck.py smc <ai file>` gives the expected `Pr` value for that file.

## 4. Scope
- **Decisions and shipping:** the physics and the players' decisions are the validated round-3 configuration (decisions replayed, transfers deferred). The response is added only through the players' own levers.
- **The tree is a policy, not a strategy synthesised by UPPAAL Stratego.** UPPAAL's role here is to **certify it independently**: SMC on the same model class, with its own random semantics. Synthesising a Stratego strategy over the same levers is a possible extension. It would need the levers as controllable edges at the notice, and the tree as a baseline.
