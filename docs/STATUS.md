# Project status (INCOM 2027 paper): read this first

Branch `claude/incom-2027-paper-plan-1cll5u`. Paper plan: `INCOM2027_paper_plan.md`. Submission deadline: 14 Dec 2026.

## Idea
A trustworthy-AI paper (predict → decide → explain → certify) on a supply-chain twin whose **every part is backed by data**. The twin is built from ERPsim SAP data:
- calibration year: normal 2
- validation years: fraud 2 and fraud 3 (same company)

Disruptions are injected only once the physics is validated.

## Done (phase → artefact)
| Phase | What | Where |
|---|---|---|
| A cleaning + evidence ledger | every parameter with source, method, value in 3 years; cleaning rules C0–C5, C1a | `data/derive_calibration.py`, `data/calibration/` |
| Decisions | DR-0 data selection; DR-1 time unit = 1 game day; DR-2 F12 in detail + other products at planning level; DR-3 nominal policy = players' decisions | `docs/decision_records.md` |
| B structure proof | 17 structural claims tested in 3 years (lost sales, shared 24k/day line, instant plant→DC transfers, closed mass balance, empty start…) | `data/derive_structure.py`, `data/structure/` |
| C spec + policy | spec; the players' forecast is their only decision; MRP replica reproduces production 20/21 and purchasing 29/37; quality loss 0.2–4.1 % (Q2) | `docs/model_spec.md`, `docs/policy_acceptance.md`, `data/mrp_replica.py` |
| C twin | Python day-tick twin; modes: demand replay/sample, policy replay/mrp, push replay/lag1, line erpsim (full batch, 0.6-day changeover) | `model/twin/`, `docs/twin.md`, inputs `model/twin/inputs/*.json` via `data/build_twin_inputs.py` |
| D validation | pre-registered protocol + 2 amendments. Round 1 (policy models) not validated. Round 2 (decisions replayed): **fraud 2 passes every metric**; fraud 3 fails 4, diagnosed (fraud orders took 67,431 real units); a diagnostic run leaves 2 narrow failures. MRP replica accepted; **push rule not accepted** | `docs/validation_protocol.md`, `docs/validation_report.md`, `model/twin/validation/`, `model/twin/diagnostic/` |
| E disruptions | E1–E5 with evidence (USAID SCMS, ERPsim Q1/Q2, B17, DataCo), randomised timing, common random numbers, 3 years. Resilience is set by the players' policy (normal 2 fragile, fraud 2/3 robust) | `docs/disruptions.md`, `model/twin/disruptions.py`, `model/twin/disruptions/` |
| Levers | only the players' 3 levers (conversions, POs, DC transfers); controller interface; a 5-day component buffer neutralises upstream disruptions in normal 2 but not stoppages or surges; fixed rules act non-monotonically | `docs/decision_levers.md`, `model/twin/controllers.py`, `model/twin/policies/` |
| UPPAAL V12 | generated from the twin inputs; switchable disruptions; the deterministic mirror matches the twin exactly (3 years, all switches); **verifyta run pending (user, locally)** | `docs/uppaal.md`, `model/uppaal/` |

## Now
- **User:** run `verifyta` on `model/uppaal/V12_<run>_crosscheck.xml` and `crosscheck.py compare` (`docs/uppaal.md` §4).
- **Next:** AI layers on the validated twin:
  - L1 predicts the extra loss from the disruption plus the policy state.
  - L2 is a controller over the 3 levers.
  - L3 explains.
  - L4 certifies in UPPAAL.

## Working notes
- Raw data: `erp_fraud_data.zip` (Google Drive, user's). It is extracted in the session scratchpad, which is not in the repo, so re-download it to rerun the scripts.
- Python: a venv with pandas, openpyxl, scipy, tabulate. The system Python's cryptography package is broken, so use the venv.
- Never state "~7 h of data": the data covers one game year (12 × 20 days, played in about 6.5 h).
- The user does not want any mention that the earlier model was calibrated quickly or poorly.
