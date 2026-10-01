# L4 results: certificates (L* = 1.0 day of demand over 60 days; 95 % Clopper-Pearson)

Service: P(lost demand of all products over the 60 days after the notice <= L*), certified lower bound. Harm: P(loss > players' loss + 0.05 days), certified upper bound.

| set | policy | n | service rate | certified service >= | worst type: certified service >= | harm rate | certified harm <= | added inventory (EUR) |
|---|---|---|---|---|---|---|---|---|
| normal 2, independent certification sample | players (no response) | 2000 | 77.6% | 75.7% | E3: 20.1% | 0.0% | 0.2% | 0 |
| normal 2, independent certification sample | L2 (black box) | 2000 | 82.7% | 80.9% | E3: 20.8% | 2.3% | 3.1% | 18,752 |
| normal 2, independent certification sample | **tree (explainable, certified)** | 2000 | 80.0% | 78.2% | E3: 21.3% | 1.4% | 2.0% | 21,317 |
| fraud 2 | players (no response) | 2000 | 79.0% | 77.2% | E3: 40.9% | 0.0% | 0.2% | 0 |
| fraud 2 | L2 (black box) | 2000 | 78.6% | 76.8% | E3: 37.9% | 6.2% | 7.3% | 26,218 |
| fraud 2 | **tree (explainable, certified)** | 2000 | 78.8% | 77.0% | E3: 39.9% | 5.9% | 7.1% | 22,852 |
| fraud 3 | players (no response) | 2000 | 90.9% | 89.6% | E3: 48.1% | 0.0% | 0.2% | 0 |
| fraud 3 | L2 (black box) | 2000 | 91.0% | 89.7% | E3: 48.9% | 3.3% | 4.2% | 33,579 |
| fraud 3 | **tree (explainable, certified)** | 2000 | 91.0% | 89.6% | E3: 48.4% | 3.4% | 4.3% | 33,382 |
| STRESS (outside the evidence) | players (no response) | 1800 | 67.4% | 65.2% | E4: 34.3% | 0.0% | 0.2% | 0 |
| STRESS (outside the evidence) | L2 (black box) | 1800 | 69.0% | 66.8% | E4: 37.5% | 2.4% | 3.2% | 24,418 |
| STRESS (outside the evidence) | **tree (explainable, certified)** | 1800 | 67.9% | 65.7% | E4: 35.4% | 0.4% | 0.9% | -971 |
| fraud 2, other 1,600 episodes | players (no response) | 1600 | 78.9% | 76.9% | E3: 42.0% | 0.0% | 0.2% | 0 |
| fraud 2, other 1,600 episodes | tree built on normal 2 | 1600 | 78.6% | 76.5% | E3: 40.2% | 6.1% | 7.3% | 24,083 |
| fraud 2, other 1,600 episodes | **adapted tree** | 1600 | 85.9% | 84.1% | E3: 39.4% | 5.8% | 7.0% | 83,592 |
| fraud 3, other 1,600 episodes | players (no response) | 1600 | 91.1% | 89.6% | E3: 47.7% | 0.0% | 0.2% | 0 |
| fraud 3, other 1,600 episodes | tree built on normal 2 | 1600 | 91.3% | 89.8% | E3: 48.7% | 3.2% | 4.2% | 32,834 |
| fraud 3, other 1,600 episodes | **adapted tree** | 1600 | 91.4% | 89.9% | E3: 49.0% | 2.7% | 3.6% | 6,402 |

Reading: for disruptions drawn from the evidence-bounded catalogue at a random time in that year, the policy keeps the 60-day loss within L* with probability at least the certified service level, and makes things worse than the players' own plan with probability at most the certified harm level, both at 95 % confidence. The worst-type column bounds the service guarantee for every single disruption type.
