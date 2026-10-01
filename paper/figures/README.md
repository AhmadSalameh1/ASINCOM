# Paper figures

All figures are built by `make_figures.py` from the pipeline's result files; nothing is typed in by hand. To rebuild:

```bash
python make_figures.py            # all; --only 2 5 for some
```

- **Format:** PDF with embedded fonts (Times-metric) for the paper, and a PNG for preview. Page width is 17.4 cm (all figures here are page width).
- **Colour follows the entity in every figure:**
  - AI policy (L2 or tree): blue
  - players' own response: grey
  - per-type lookup rule: orange
  - oracle: hollow black star
  - fixed actions: light grey
  - years: always panels, never colours

  The palette passes the dataviz validator (colour-vision-deficiency separation and normal-vision floors). Aqua is below 3:1 contrast, so it is used only with a legend and direct labels.
- **Data behind each figure:** in `model/ai/results/`, `model/twin/disruptions/` and `model/uppaal/smc_mirror.csv` (the table view for each figure).

## Suggested selection for 6 pages
| Must | Optional (or as a table) |
|---|---|
| Fig. 1 framework, Fig. 5 L2 frontier, Fig. 6 tree, Fig. 7 certificates | Fig. 2 validation (or one sentence + the A1 numbers), Fig. 3 resilience (or a 3-row table), Fig. 4 L1 (or 4 numbers in the text) |

## Draft captions
**Fig. 1.** Evidence-first pipeline.
- Every model element is derived from the ERPsim SAP data of one game year (normal 2) and checked on two other years played by another team (fraud 2, fraud 3) on the same company.
- The Python twin and the UPPAAL model are generated from the same inputs and agree in 591 of 591 deterministic configurations.
- Disruptions are sampled within evidence bounds. The AI layers may use only the levers the players had.

**Fig. 2.** Validation (round 3): cumulative F12 sales and plant-to-DC transfers. The twin is shown as the median and 5–95 % band of 50 runs, with the players' recorded decisions replayed; it is compared with the recorded game. The maximum deviation is 0.5–1.0 % of the year total for sales and 2.1–3.6 % for transfers. The 5–95 % band is narrower than the line width.

**Fig. 3.** Same physics, different teams.
- **What is plotted:** the extra lost demand caused by each evidence-based disruption, for one month at a random time, vs the same-seed run without it (60 runs per level).
- **Main result:** a +19 % demand surge costs normal 2 a median of 28k units; fraud 2 6k; fraud 3 nothing. A 25-day stoppage costs 55k / 13k / 19k.
- **Upstream disruptions** (E1, E2) have a median extra loss of 0 in every year.

**Fig. 4.** L1 under shift.
- **(a) Prediction error.** Inside the build year, the plant state cuts the error of the notice-only model by a factor of 4. Under another team's policy it adds nothing.
- **(b) Coverage.** The coverage of the 90 % conformal upper bound decays from 88 % to 85 % / 79 %, with the worst disruption type at 60–66 %. Recalibrating the margin on 100 outcomes from the new setting restores 89–90 %.

**Fig. 5.** L2: lost demand (all products, 60 days, in days of demand) vs the added inventory capital of the response.
- **In the build year,** L2 is close to the oracle at €25k, while the per-type lookup rule spends €124k and loses more.
- **In the other teams' years,** L2 built on normal 2 does not transfer (hollow circle). Adapting it with 400 episodes of the target twin recovers a 15 % lower loss in fraud 2 (arrow). In fraud 3 there is little to gain, and the adapted L2 mostly does nothing.

**Fig. 6.** The certified policy (L3): L2 distilled into a depth-3 tree on planner-observable features at the disruption notice. Each leaf shows the share of episodes in the independent certification sample of normal 2 that reach it. The tree does nothing in 75 % of episodes.

**Fig. 7.** L4 certificates, with 95 % Clopper–Pearson intervals.
- **(a) Service:** the probability that the 60-day loss stays within one day of demand.
  - Shown for the players and the tree, in the build year and in the other years (adapted tree).
  - Filled markers are independent Python episodes. Hollow markers are the generated UPPAAL model's own random semantics (stochastic mirror; `verifyta` should reproduce them).
- **(b) Harm:** the probability that the tree makes things worse than the players' own plan by more than 0.05 days of demand.
