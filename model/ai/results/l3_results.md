# L3 results: explanations and their stability

## Distilled policy (fitted to L2's choices on the normal 2 build episodes)

| tree | leaves | features used | fidelity: normal 2 held-out | fidelity: fraud 2 | fidelity: fraud 3 | fidelity: STRESS |
|---|---|---|---|---|---|---|
| depth 3 | 8 | 6 | 77.0% | 68.5% | 56.1% | 49.9% |
| depth 4 | 13 | 8 | 80.5% | 68.6% | 58.3% | 63.2% |

**Depth-3 tree (the certified policy):**
```
|--- type_E3 <= 0.50
|   |--- e4_factor <= 1.09
|   |   |--- plant_days <= 11.05
|   |   |   |--- class: none
|   |   |--- plant_days >  11.05
|   |   |   |--- class: prio
|   |--- e4_factor >  1.09
|   |   |--- fg_cover <= 19.75
|   |   |   |--- class: ship
|   |   |--- fg_cover >  19.75
|   |   |   |--- class: none
|--- type_E3 >  0.50
|   |--- fg_cover <= 30.44
|   |   |--- queue_f12_days <= 0.43
|   |   |   |--- class: po10+fg+prio
|   |   |--- queue_f12_days >  0.43
|   |   |   |--- class: fg
|   |--- fg_cover >  30.44
|   |   |--- dc_cover_West <= 42.55
|   |   |   |--- class: po10
|   |   |--- dc_cover_West >  42.55
|   |   |   |--- class: fg
```

Outcome of the tree as a policy vs L2 (L* = 1 day):

| set | policy | lost (days) | violation | added inventory (EUR) | acted |
|---|---|---|---|---|---|
| normal 2 held-out | L2 | 1.987 | 19.8% | 25,090 | 34% |
| normal 2 held-out | tree depth 3 | 2.022 | 22.5% | 24,346 | 27% |
| normal 2 held-out | tree depth 4 | 1.987 | 19.8% | 21,455 | 33% |
| fraud 2 | L2 | 1.466 | 21.3% | 26,218 | 35% |
| fraud 2 | tree depth 3 | 1.453 | 21.1% | 22,852 | 31% |
| fraud 2 | tree depth 4 | 1.506 | 22.1% | 23,433 | 36% |
| fraud 3 | L2 | 0.683 | 9.0% | 33,579 | 54% |
| fraud 3 | tree depth 3 | 0.683 | 9.0% | 33,382 | 49% |
| fraud 3 | tree depth 4 | 0.677 | 9.2% | 28,105 | 55% |
| STRESS | L2 | 1.301 | 31.0% | 24,418 | 58% |
| STRESS | tree depth 3 | 1.403 | 32.1% | -971 | 20% |
| STRESS | tree depth 4 | 1.343 | 31.1% | -2,644 | 60% |

## Stability over 10 bootstrap refits of the whole pipeline

- root split feature: {'type_E3': 10} (reference tree: type_E3)
- Jaccard similarity of the feature set with the reference tree: median 0.50, min 0.22
- features in every bootstrap tree: ['e4_factor', 'type_E3']
- normal 2 held-out: bootstrap trees agree with the reference tree on 77.2% of episodes (median; min 68.5%)
- fraud 2: bootstrap trees agree with the reference tree on 73.2% of episodes (median; min 64.8%)
- fraud 3: bootstrap trees agree with the reference tree on 54.4% of episodes (median; min 45.5%)
- STRESS: bootstrap trees agree with the reference tree on 54.2% of episodes (median; min 47.6%)

## What drives the impact prediction (L1, mean |SHAP|, days of demand)

| feature | normal 2 held-out | fraud 2 | fraud 3 | STRESS |
|---|---|---|---|---|
| e3_days | 1.180 | 1.067 | 0.876 | 0.583 |
| fg_cover | 0.408 | 0.414 | 0.343 | 0.216 |
| dc_cover_North | 0.228 | 0.169 | 0.188 | 0.152 |
| e4_factor | 0.214 | 0.180 | 0.199 | 0.574 |
| type_E3 | 0.098 | 0.093 | 0.065 | 0.048 |
| dc_cover_West | 0.077 | 0.080 | 0.057 | 0.122 |
| cover_AA-R01 | 0.052 | 0.067 | 0.042 | 0.057 |
| type_E1 | 0.045 | 0.040 | 0.029 | 0.017 |
| plant_days | 0.041 | 0.031 | 0.054 | 0.031 |
| type_E2 | 0.036 | 0.039 | 0.028 | 0.059 |

Rank correlation of the importances with the build year (all features):
- fraud 2: Spearman 0.98
- fraud 3: Spearman 0.99
- STRESS: Spearman 0.96
