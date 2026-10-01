# Robustness: AI results under plain transfer replay (pessimistic shipping)


## deferred replay (nominal)

| test set | L1 coverage (90 % bound) | policy | lost (days) | violation of L* | added inventory (EUR) | acted |
|---|---|---|---|---|---|---|
| normal 2 held-out | 88.0% | players (no response) | 2.264 | 24.8% | 0 | 0% |
| normal 2 held-out | 88.0% | best fixed action in hindsight (fg) | 2.187 | 26.2% | 62,653 | 100% |
| normal 2 held-out | 88.0% | type-rule | 2.110 | 20.0% | 124,406 | 100% |
| normal 2 held-out | 88.0% | L2 | 1.987 | 19.8% | 25,090 | 34% |
| normal 2 held-out | 88.0% | oracle | 1.907 | 19.2% | 3,958 | 36% |
| fraud 2 | 84.9% | players (no response) | 1.432 | 20.9% | 0 | 0% |
| fraud 2 | 84.9% | best fixed action in hindsight (po10) | 1.047 | 12.6% | 146,329 | 100% |
| fraud 2 | 84.9% | type-rule | 1.310 | 17.7% | 111,307 | 100% |
| fraud 2 | 84.9% | L2 | 1.466 | 21.3% | 26,218 | 35% |
| fraud 2 | 84.9% | oracle | 1.042 | 12.2% | 9,049 | 29% |
| fraud 3 | 79.0% | players (no response) | 0.659 | 9.1% | 0 | 0% |
| fraud 3 | 79.0% | best fixed action in hindsight (po5) | 0.659 | 9.1% | 98,934 | 100% |
| fraud 3 | 79.0% | type-rule | 0.707 | 9.7% | 203,005 | 100% |
| fraud 3 | 79.0% | L2 | 0.683 | 9.0% | 33,579 | 54% |
| fraud 3 | 79.0% | oracle | 0.601 | 8.0% | 695 | 30% |

## plain replay

| test set | L1 coverage (90 % bound) | policy | lost (days) | violation of L* | added inventory (EUR) | acted |
|---|---|---|---|---|---|---|
| normal 2 held-out | 89.5% | players (no response) | 4.387 | 50.5% | 0 | 0% |
| normal 2 held-out | 89.5% | best fixed action in hindsight (ship) | 2.379 | 30.2% | -13,661 | 100% |
| normal 2 held-out | 89.5% | type-rule | 2.379 | 30.2% | -13,661 | 100% |
| normal 2 held-out | 89.5% | L2 | 2.367 | 30.8% | 202 | 59% |
| normal 2 held-out | 89.5% | oracle | 2.295 | 30.2% | -9,959 | 70% |
| fraud 2 | 94.8% | players (no response) | 3.906 | 48.4% | 0 | 0% |
| fraud 2 | 94.8% | best fixed action in hindsight (ship) | 1.500 | 29.0% | -20,592 | 100% |
| fraud 2 | 94.8% | type-rule | 1.500 | 29.0% | -20,592 | 100% |
| fraud 2 | 94.8% | L2 | 1.626 | 31.6% | -12,560 | 73% |
| fraud 2 | 94.8% | oracle | 1.489 | 29.0% | -19,182 | 70% |
| fraud 3 | 94.4% | players (no response) | 1.098 | 15.8% | 0 | 0% |
| fraud 3 | 94.4% | best fixed action in hindsight (ship) | 0.530 | 7.6% | -4,615 | 100% |
| fraud 3 | 94.4% | type-rule | 0.530 | 7.6% | -4,615 | 100% |
| fraud 3 | 94.4% | L2 | 0.626 | 10.1% | 14,977 | 58% |
| fraud 3 | 94.4% | oracle | 0.530 | 7.6% | -5,265 | 66% |
