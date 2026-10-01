# Twin-rollout baseline (K = 4 rollouts per action, lowest mean simulated loss; demand after the notice: resampled from the 20 days before (fair))

Realised outcomes on the same episodes for every policy (paired). L* = 1 day of demand.

| sample | policy | lost (days) | service (loss <= L*) | added inventory (EUR) | acted |
|---|---|---|---|---|---|
| Y1 certification sample (n=1000) | players (no response) | 1.822 | 77.9% | 0 | 0% |
| Y1 certification sample (n=1000) | L2 | 1.527 | 82.7% | 18,634 | 31% |
| Y1 certification sample (n=1000) | tree | 1.578 | 79.8% | 21,105 | 24% |
| Y1 certification sample (n=1000) | **twin rollout (SAA)** | 1.775 | 75.6% | 6,380 | 67% |
| Y1 certification sample (n=1000) | oracle | 1.466 | 83.2% | 3,069 | 32% |
| fraud 2, other episodes (L2/tree adapted) (n=1000) | players (no response) | 1.429 | 78.8% | 0 | 0% |
| fraud 2, other episodes (L2/tree adapted) (n=1000) | L2 | 1.219 | 82.8% | 58,561 | 53% |
| fraud 2, other episodes (L2/tree adapted) (n=1000) | tree | 1.139 | 85.3% | 83,280 | 51% |
| fraud 2, other episodes (L2/tree adapted) (n=1000) | **twin rollout (SAA)** | 1.239 | 81.9% | 61,344 | 61% |
| fraud 2, other episodes (L2/tree adapted) (n=1000) | oracle | 1.025 | 88.0% | 9,085 | 29% |
