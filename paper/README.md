# INCOM 2027 paper draft

- `main.tex`: the manuscript, written for the IFAC conference class (`ifacconf.cls` / `ifacconf.bst`).
- `references.bib`: the bibliography.
- `figures/`: built by `figures/make_figures.py` from the result files (see `figures/README.md`).
- `tools/check_build.sh`: a local check build with a stand-in class (`tools/ifacconf-standin.cls`, IFAC-like layout: A4, 10 pt Times, two columns, 17.4 cm). It catches LaTeX errors and undefined references and gives an approximate page count. The current draft compiles cleanly to **6 pages** with it.

  **Submit with the official IFAC template** (e.g. the IFAC conference template on Overleaf): copy `main.tex`, `references.bib` and `figures/` into it.

## Before submission (checklist)
1. **Authors**, affiliations, e-mails, acknowledgements and funding (marked `TODO` in `main.tex`).
2. **References.** Every entry in `references.bib` was written from memory and must be checked against the publisher's record. The entries marked `VERIFY` are the least certain: dtControl author list, Himmiche et al. (SOHOMA), DataCo version, USAID dataset year and URL.
3. **UPPAAL.**
   - Run `verifyta` on the `_crosscheck*.xml` files and confirm `RESULT: MATCH` (`docs/uppaal.md` §3).
   - Run query 2 on the `_ai_` files. Then replace "expected values" in the Discussion, and the hollow markers in Fig. 3 (`model/uppaal/smc_mirror.csv`), with the verifyta results.
4. **Compile with the official class** and check the page limit. With the stand-in class page 6 is completely full; if the official class runs over, drop the framework figure (Fig. 1) first. Not included for space: validation, resilience and L1 coverage (`figures/fig2–fig4`).

## Where each number comes from
| Paper section | Source |
|---|---|
| Data, structure, policy (§3.1–3.2) | `model/twin/inputs/*.json`, `data/structure/structure_evidence.md`, `docs/policy_acceptance.md`, `data/prices/prices.md` |
| Validation round 3 (§3.3) | `docs/validation_report.md` (round 3), `model/twin/validation/*_replay_deferred_*` |
| Mirror 591/591 (§3.4) | `model/uppaal/crosscheck_suite_*.csv` |
| Phase E impacts, Table 1 (§4) | `model/twin/disruptions/*_impact.md`, `docs/disruptions.md`, `data/open_data/open_data_evidence.json` |
| L1 (§6) | `model/ai/results/l1_results.md`, `l1_primary.csv`, `l1_ablation.csv`, `l1_loyo.csv` |
| L2, Fig. 1 (§6) | `model/ai/results/l2_results.md`, `l2_comparison.csv`, `l2_transfer.csv` |
| L3, Fig. 2 (§6) | `model/ai/results/l3_results.md`, `tree_normal_2.json` |
| L4, Fig. 3 (§6) | `model/ai/results/l4_results.md`, `l4_certificates.csv`, `model/uppaal/smc_mirror.csv` |
| Robustness (§6) | `model/ai/results/robustness.md` |
