# INCOM 2027 paper draft

- `main.tex`: the manuscript, written for the IFAC conference class (`ifacconf.cls` / `ifacconf.bst`).
- `references.bib`: the bibliography.
- `figures/`: built by `figures/make_figures.py` from the result files (see `figures/README.md`).
- `tools/check_build.sh`: a local check build with a stand-in class (`tools/ifacconf-standin.cls`, IFAC-like layout: A4, 10 pt Times, two columns, 17.4 cm). It catches LaTeX errors and undefined references and gives an approximate page count. The current draft compiles cleanly to **6 pages** with it.

  **Submit with the official IFAC template** (e.g. the IFAC conference template on Overleaf): copy `main.tex`, `references.bib` and `figures/` into it.

## Before submission (checklist)
1. **Authors**, affiliations, e-mails, acknowledgements and funding (marked `TODO` in `main.tex`).
2. **References: verified on 2026-10-01** (table below). Two items are left for you:
   - Confirm with Sara how the fourth author of her SOHOMA paper is printed: "Marie Duflot" (as DBLP has it) or "Duflot-Kremer".
   - Check the official `ifacconf.bst` output once.
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

## Reference verification (2026-10-01)
Each entry was checked against the record found by web search. Direct access to Crossref and DOI resolvers is blocked in the build environment, so publisher, arXiv, DBLP, NeurIPS proceedings and dataset pages were used instead. DOIs are kept in the non-printing field `verified_doi`.

| Key | Check | Correction |
|---|---|---|
| tritscher2022openerp | [arXiv:2206.04460](https://arxiv.org/abs/2206.04460) | none |
| leger2006erpsim | JISE 17(4):441–447 ([ERPsim research page](https://erpsim.hec.ca/en/research)) | none |
| ivanov2021digitaltwin | PPC 32(9):775–788, doi 10.1080/09537287.2020.1768450 ([Semantic Scholar](https://www.semanticscholar.org/paper/A-digital-supply-chain-twin-for-managing-the-risks-Ivanov-Dolgui/fd278d4f858188ea7563f07defdda80704349dbc)) | DOI added |
| hosseini2019resilience | TRE 125:285–307, doi 10.1016/j.tre.2019.03.001 ([HAL](https://hal.science/hal-02097333v1)) | DOI added |
| baryannis2019scrm | IJPR 57(7):2179–2202, doi 10.1080/00207543.2018.1530476 ([EconPapers](https://econpapers.repec.org/RePEc:taf:tprsxx:v:57:y:2019:i:7:p:2179-2202)) | DOI added |
| sargent2013vv | J. Simulation 7:12–24, doi 10.1057/jos.2012.20 ([Springer](https://link.springer.com/article/10.1057/jos.2012.20)) | DOI added |
| vovk2005alrw | Springer 2005, ISBN 978-0387001524 ([Google Books](https://books.google.com/books/about/Algorithmic_Learning_in_a_Random_World.html?id=pEXc4C1ymakC)) | none |
| romano2019cqr | NeurIPS 32 ([proceedings](https://papers.nips.cc/paper/8613-conformalized-quantile-regression)) | none |
| angelopoulos2023gentle | FnT ML 16(4):494–591 ([Google Books](https://books.google.com/books/about/Conformal_Prediction.html?id=3gK8zwEACAAJ)) | none |
| tibshirani2019covariateshift | NeurIPS 32 ([proceedings](http://papers.neurips.cc/paper/8522-conformal-prediction-under-covariate-shift)) | none |
| gibbs2021aci | NeurIPS 34:1660–1672 ([proceedings](https://proceedings.neurips.cc/paper/2021/hash/0d441de75945e5acbc865406fc9a2559-Abstract.html)) | pages added |
| bastani2017extraction | [arXiv:1705.08504](https://arxiv.org/abs/1705.08504) | none |
| rudin2019stop | Nat. Mach. Intell. 1:206–215 ([Nature](https://www.nature.com/articles/s42256-019-0048-x)) | DOI added |
| ashok2020dtcontrol | HSCC '20, art. 30, doi 10.1145/3365365.3383468 ([ACM](https://dl.acm.org/doi/abs/10.1145/3365365.3383468)) | **author list corrected** (Jagtap and Zamani, not Weinhuber and Yadav) |
| legay2010smc | RV 2010, LNCS 6418:122–135 ([Springer](https://link.springer.com/chapter/10.1007/978-3-642-16612-9_11)) | DOI added |
| david2015uppaalsmc | STTT 17(4):397–415 ([AAU portal](https://vbn.aau.dk/en/publications/uppaal-smc-tutorial/)) | DOI added |
| david2015stratego | TACAS 2015, LNCS 9035:206–211 ([DBLP](https://dblp.org/rec/conf/tacas/DavidJLMT15.html)) | DOI added |
| himmiche2018smc | SOHOMA 2017, SCI 762:345–357, 2018 ([DBLP SOHOMA 2017](https://dblp.org/db/conf/sohoma/sohoma2017.html)) | pages added; author printed as "Duflot" per DBLP (confirm) |
| lundberg2017shap | NeurIPS 30:4768–4777 ([ACM](https://dl.acm.org/doi/10.5555/3295222.3295230)) | pages added |
| clopper1934 | Biometrika 26(4):404–413 ([Semantic Scholar](https://www.semanticscholar.org/paper/THE-USE-OF-CONFIDENCE-OR-FIDUCIAL-LIMITS-IN-THE-OF-Clopper-Pearson/166c42895882039e4252f7c943efa13d0505109f)) | DOI added |
| ke2017lightgbm | NeurIPS 30:3146–3154 ([proceedings](https://proceedings.neurips.cc/paper/6907-lightgbm-a-highly-efficient-gradient-boosting-decision-tree.pdf)) | pages added |
| dataco2019 | Mendeley Data V3, doi 10.17632/8gx2fvg2k6.3 ([Mendeley](https://data.mendeley.com/datasets/8gx2fvg2k6/3)) | version and DOI fixed |
| usaid_scms | data.usaid.gov dataset a3rc-nmf6, 10,324 shipments 2006–2015 ([USAID](https://2012-2017.usaid.gov/data/dataset/0162a542-4f2e-4fe2-ad5d-8f6ed2344056)) | title, ID and update date fixed |
