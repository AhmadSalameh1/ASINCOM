# Response to the mock review panel (INCOM 2027 draft)

Each point of the meta-review is answered below in its priority order. Every point gives what was checked, what changed in `paper/main.tex` and where the numbers come from. New statistics are in `model/ai/results/revision_stats.md` (script `model/ai/revision_stats.py`) and `model/ai/results/rollout_baseline.md` (script `model/ai/rollout_baseline.py`).

## 1. UPPAAL execution contradiction (all reviewers): accepted
The reviewers are right. Both the 591/591 deterministic agreement and the hollow markers in Fig. 4 come from a Python execution of the generated model's semantics (`model/uppaal/crosscheck.py`). UPPAAL itself has not run.
- **Removed:** the SMC claims from the abstract, contribution (i) and the conclusion, and "generated identically".
- **Fig. 1 and Fig. 4 captions, §3.4 and §6:** now say exactly what produced the numbers ("Python execution of the generated model's random semantics, not yet run in UPPAAL").
- **§3.4:** states what UPPAAL contributes: an independent implementation from the same inputs, plus access to SMC and Stratego. Dense time is not used (R3.4).
- **Distributional comparison (R3.3):** two-proportion tests between the Python episodes and the mirror give p ≥ 0.11 for all six populations. The paper adds that this supports the implementation but is not independent evidence of validity (R2.8).
- **Query definition (R3.3, R4.4):** `ok`, `done` and `T` are defined in §5.5.
- **Open:** run `verifyta` (commands in `docs/uppaal.md` §3) and replace the mirror values with UPPAAL's output, including the version, the queries, ε/α and the number of runs.

## 2. Abstract compares two lower bounds: accepted
- **Abstract:** now gives the observed values and a paired test: 77.6 → 80.0 %, paired difference +2.5 points (bootstrap 95 % CI 1.8–3.1). In §6 the discordant pairs are 50 / 1, exact McNemar p = 4.6e-14.
- **§5.5:** states that the bounds are the ends of two-sided 95 % Clopper–Pearson intervals. Each one-sided statement therefore holds at 97.5 %, and the service and harm statements hold jointly at 95 % (Bonferroni, R3.5).
- **Harm in the abstract:** 1.4 % (≤ 2.0 %).

## 3. "One player group" vs "other teams": accepted, the reviewer is right
The dataset article confirms that normal 2, fraud 2 and fraud 3 were all played by the same group of five students, one of whom acted as a fraudster in the fraud runs.
- Every "team" or "other team's year" is now "later runs of the same group with different decisions".
- The runs are renamed Y1 / Y2 / Y3, with the mapping to the dataset names given in §3.1.
- The transfer claim is restated as a change of the decision policy, not of the organisation.

## 8. E5 conflicts with "instantaneous transfers": accepted
- **E5:** now labelled as an extension beyond the validated physics, kept because its effect is small (median impact zero in every run).
- **E1:** the assumption behind transferring lateness ratios is stated.
- **E3:** the cap of 25 days is explained as the shortest of the three recorded pauses (25, 52 and 60 days), so every sampled stoppage is shorter than one the game produced.
- **Sampling distributions (R1.4, R3.2, R3.Q3):** stated in full.
  - The type is drawn uniformly over the five types.
  - The severity is drawn uniformly within its range; E1 uses inverse sampling of the empirical quantiles up to q95.
  - The notice day is drawn uniformly over the steady months.
- Disruptions are single, which is listed as a limitation.
- **Table 1:** defines ℓ, and E2's "the accepted part arrives 2 days late" is clarified.

## 5. Certificate assumptions unstated: accepted
§5.5 now states:
- i.i.d. draws from the stated episode distribution
- a guarantee that holds within the twin only, saying nothing about real disruptions, other severity mixes or the twin's error
- two-sided 95 % intervals
- the joint confidence of the service and harm statements

"Certify" becomes "bound" or "statistical guarantee" throughout, including the title. L\*, the tree depth, the 0.9 level and the 0.05-day harm threshold were all fixed on Y1 before the certification sample was generated. The independent sample comes from a separate random stream.

## 13. Numeric inconsistencies: accepted, all traced
- **Fraud 2, 1.43 vs 1.40 days:** two episode sets were mixed (all 2,000 vs the 1,600 test episodes). All Y2 comparisons now use the same 1,600 episodes: players 1.40, L2 built on Y1 1.44, adapted 1.19.
- **L2 at 10–12 k€ in Fig. 2 vs 25 k€ in the text:** a bug in `make_figures.py`. It selected the point-prediction variant of L2 (12 k€) by substring match. Fixed; the figure now plots the conformal L2 (25 k€).
- **Players' certified fraud 2 ≥ 77.2 % vs ≥ 76.9 %:** the 2,000 and the 1,600 sets, respectively. The text now uses the 1,600 set (≥ 76.9 % is not quoted; the paired test is).
- **"The advantage disappears":** this held for Y2 only. The text now says "disappears in Y2 (0.78 vs 0.77), shrinks in Y3 (0.51 vs 0.71)".
- **"84 % best in hindsight" vs the oracle's 19.2 % violation:** the two came from different samples (certification sample 83.3 %, held-out 80.8 %). On the held-out set they agree (80.8 % = 1 − 19.2 %), and the text now uses the held-out value.

## 7. L2 selection invalidates per-action coverage: accepted
- **§5.3:** now states that Eq. (1) holds for each fixed action but not for the selected one, so L2 is a heuristic and only L4 carries a guarantee.
- **Measured (`revision_stats.md` §4):** shares of the three branches of Eq. (2) and the coverage of the chosen action's bound:

  | Branch | Share | Coverage of the chosen bound |
  |---|---|---|
  | none | 68.2 % | 90.5 % |
  | cheapest feasible | 6.6 % | 91.6 % |
  | lowest bound | 25.3 % | 79.8 % |
  | overall | | 87.9 % |

- **Joint calibration (max over actions):** gives a correction of 0.12 days, against 0.00–0.02 per action. It is reported here, not adopted, because L4 already gives the guarantee on the deployed policy.

## 4. Validation wording: accepted
- **A1 and the verdict rule:** now defined in §3.3, with the 10 % threshold and the "≤ 2 secondary failures" rule. The failing metric is named per run.
- **"Pre-registered" removed:** the git history does not carry a public timestamp. The paper now says "fixed on Y1 before any validation run, and documented in the repository".
- **The three revisions:** described; the second and third are called post hoc.
- **Y3:** now described as a shift case with an invalid twin.
- **Y3's L4 and L2 results** (previously only in Fig. 4) are now in the text: no service gain, and a slight loss increase of +0.02 days (CI excludes 0).
- **"Round 3":** replaced by "revision" to avoid the clash with game rounds.
- **Fraud-exclusion bias:** quantified (67,431 units in Y3, 2,731 in Y2).

## 6. Uncertainty on differences: accepted
`revision_stats.md` §2 gives paired bootstrap 95 % CIs on every loss and service difference, plus exact McNemar tests. The paper quotes them where it makes a comparison:
- Y1 held-out, L2 vs players: −0.28 (−0.38, −0.18)
- Y2, adapted L2: −0.21 (−0.27, −0.15)
- Y2, adapted tree: +6.9 points (5.5–8.3)
- Y2, tree built on Y1: −0.4 points, p = 0.18
- explanation cost (L2 vs tree): 2.6 points (1.9–3.5)

## 16. Presentation: accepted
- **Notation paragraph (§3.1):** defines days of demand (about 7,700 units in Y1), cover, steady months, notice, EKPO/VBAP and the DC names. ℓ is defined in Table 1, and A1 and STRESS where they are introduced.
- **Y1/Y2/Y3 naming:** used throughout, including the figures.
- **Data and code availability statement:** added.
- **Fig. 2:** has a shared legend and larger labels; the caption notes the differing vertical scales.
- **Fig. 3:** the tree's edge labels are darker.
- **Fig. 4:** adds the non-adapted Y2 tree, and the harm axis is cut to 10 %.
- **Style:** "for ever" removed; "a UPPAAL" kept (correct form); "k€" macro checked; informal phrases removed ("gives fraud 2 nothing", "the artefact hid it").
- **Title:** now "Towards Trustworthy …".

## Remaining points
- **R2.3, leakage:** splits grouped by notice day were added (`revision_stats.md` §1, §5).
  - L1 MAE rises from 0.22 to 0.38, against 0.90 for the notice-only model and 1.18 for the per-type mean (`revision_stats.md` §5), so the plant state still matters. Held-out coverage is 87.3 %, and 93.2 % on the certification sample.
  - L2 still beats the players on held-out days (1.65 vs 1.98).
  - The certification sample is a separate random stream.
  - The paper reports both splits.
- **R2.2, R4.Q5, L1/L2 specification:**
  - L1 is one model for the players' plan; its target is the *extra* F12 loss.
  - L2 has one quantile model and one conformal correction per action; its target is the *total* loss of all products (the service quantity).
  - Ĉ_a is a per-action gradient-boosted point model. Its held-out MAE is 0.05–0.35 days of demand, against mean added capital of 2.8–12.7 days for the stocking actions (`revision_stats.md` §6).
- **R1.5, R4.5, oracle:** now defined as the cheapest action meeting L\* ex post, else the least loss. It minimises violations, not mean loss, which is why a fixed action can lose less on average.
- **R2.7, baselines:**
  - point-L2 is now in the text: same loss at half the spend, so the conformal margin adds caution, not value.
  - The twin-rollout baseline (sample-average approximation, K = 4 rollouts per action with fresh lead times after the notice) is in `rollout_baseline.md` and in §6.
  - Stratego synthesis with a dtControl export is named as the next baseline. It was not run, because UPPAAL is not available in the build environment.
- **R2.6, recalibration on a single draw:** now repeated over 200 resamples, evaluated on the remaining episodes. Y2 gives 90.4 % (SD 2.7, 85.9–94.8) and Y3 89.8 % (SD 3.1). Widths are reported: 1.04 / 0.95 days, against 1.02 / 0.93 for the build-run bound.
- **R1.7, managerial conclusion:** "a twin per team" is replaced by "recalibrate or adapt when the policy state shifts", with drift of L1's coverage as a detection signal (adaptive conformal inference).
- **R1.8, R4, related work:** six verified references added:
  - Dolgui et al. 2018 (ripple effect)
  - Ivanov 2023 (intelligent DT)
  - Simchi-Levi et al. 2015 (TTR/TTS)
  - Barber et al. 2023
  - Angelopoulos et al. 2024 (conformal risk control)
  - Lekeufack et al. 2024 (conformal decision theory)
- **R1.5, economics:** valued at the F12 margin, the avoided loss is about 3.8 k€ per disruption, against 25 k€ of capital tied up for 60 days. Holding rates and the other products' margins are listed as limitations.
- **R4.5, R4.Q4, stoppage actions:** the extra batch waits in the queue during a stoppage and runs first at restart. It shortens recovery but cannot replace lost line-days, which is why the certified service against stoppages stays between 20 and 49 %.
- **R3.Q (sub-day quantities):** the changeover of 0.6 line-day is deducted in units and carried over to the next day if needed.

## Not done (with reasons)
- **verifyta and Stratego:** need UPPAAL, which is not available in the build environment. They are to be run by the authors.
- **Mondrian CP, ACI comparison, f-divergence CP, ≥ 50 bootstrap refits, fidelity-vs-depth curve, L\* sweep in the paper:** not done, for page limits. The L\* sweep exists in `model/ai/results/l2_sweep.csv`.
- **STRESS for L2–L4:** in `l4_results.md`, not in the paper.
