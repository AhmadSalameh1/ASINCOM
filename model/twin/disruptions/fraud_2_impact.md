# Disruption impact (open loop, decisions replayed): fraud_2

60 seeds; each seed draws its own start day uniformly over the steady months (days 23-159); episode 20 days; KPIs from the start day on, each run paired with the baseline run of the same seed.

| disruption | severity | evidence | lost demand from start (units, median [5 %, 95 %]) | extra lost vs same-seed baseline: median [95 %] | share of seeds with any extra loss | fill rate next 60 d | DC stock-out days after start | days of excess loss after the episode ends |
|---|---|---|---|---|---|---|---|---|
| baseline | none | - | 10,252 [33, 43,032] | +0 [+0] | 0% | 100.0% | 20 | 0 |
| E1 supplier delay | median late shipment (+0.12 x lead) | USAID SCMS q50 | 12,760 [33, 43,032] | +0 [+0] | 2% | 100.0% | 23 | 0 |
| E1 supplier delay | severe (+0.75 x lead) | USAID SCMS q90 | 13,051 [33, 43,032] | +0 [+0] | 3% | 100.0% | 23 | 0 |
| E1 supplier delay | extreme (+1.0 x lead) | USAID SCMS q95 | 13,051 [33, 43,032] | +0 [+400] | 5% | 100.0% | 25 | 0 |
| E2 quality loss | wheat receipts: 4.1 % blocked, +2 d | ERPsim Q2 max, Q1 | 13,051 [33, 32,565] | +0 [+13,018] | 8% | 100.0% | 25 | 0 |
| E2 quality loss | all food receipts: 4.1 % blocked, +2 d | ERPsim Q2 max, applied widely | 14,493 [33, 43,032] | +0 [+14,018] | 23% | 100.0% | 27 | 0 |
| E2 quality loss | STRESS all food receipts: 25 % blocked, +2 d | beyond evidence | 13,366 [33, 43,032] | +0 [+13,367] | 23% | 100.0% | 25 | 0 |
| E3 line stoppage | 3 days | short breakdown (assumed) | 10,252 [33, 43,032] | +0 [+0] | 0% | 100.0% | 20 | 0 |
| E3 line stoppage | 10 days | between | 23,774 [33, 44,830] | +0 [+36,498] | 22% | 93.0% | 30 | 0 |
| E3 line stoppage | 25 days | shortest observed pause (B17, fraud 3) | 71,373 [22,051, 126,051] | +46,018 [+126,018] | 98% | 84.5% | 48 | 114 |
| E4 demand | surge +19 % for a month | max steady month, normal 2 | 27,935 [17,599, 53,712] | +17,365 [+22,253] | 100% | 96.8% | 30 | 66 |
| E4 demand | STRESS surge +50 % for a month | beyond evidence | 60,546 [42,015, 77,589] | +48,932 [+61,725] | 100% | 91.5% | 36 | 66 |
| E5 transit delay | +1 day | DataCo q50 (semi-synthetic) | 10,252 [33, 43,032] | +0 [+0] | 0% | 100.0% | 20 | 0 |
| E5 transit delay | +4 days | DataCo q95 (semi-synthetic) | 10,252 [33, 43,032] | +0 [+0] | 0% | 100.0% | 20 | 0 |
