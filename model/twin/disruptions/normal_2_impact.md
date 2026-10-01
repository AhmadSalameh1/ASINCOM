# Disruption impact (open loop, decisions replayed): normal_2

60 seeds; each seed draws its own start day uniformly over the steady months (days 63-152); episode 20 days; KPIs from the start day on, each run paired with the baseline run of the same seed.

| disruption | severity | evidence | lost demand from start (units, median [5 %, 95 %]) | extra lost vs same-seed baseline: median [95 %] | share of seeds with any extra loss | fill rate next 60 d | DC stock-out days after start | days of excess loss after the episode ends |
|---|---|---|---|---|---|---|---|---|
| baseline | none | - | 7,023 [0, 7,023] | +0 [+0] | 0% | 100.0% | 33 | 0 |
| E1 supplier delay | median late shipment (+0.12 x lead) | USAID SCMS q50 | 7,023 [0, 7,023] | +0 [+0] | 0% | 100.0% | 33 | 0 |
| E1 supplier delay | severe (+0.75 x lead) | USAID SCMS q90 | 7,023 [0, 7,937] | +0 [+934] | 13% | 100.0% | 33 | 0 |
| E1 supplier delay | extreme (+1.0 x lead) | USAID SCMS q95 | 7,023 [0, 11,534] | +0 [+4,790] | 13% | 100.0% | 33 | 0 |
| E2 quality loss | wheat receipts: 4.1 % blocked, +2 d | ERPsim Q2 max, Q1 | 7,023 [0, 7,023] | +0 [+7,023] | 23% | 100.0% | 33 | 0 |
| E2 quality loss | all food receipts: 4.1 % blocked, +2 d | ERPsim Q2 max, applied widely | 7,023 [0, 7,023] | +0 [+7,023] | 27% | 100.0% | 33 | 0 |
| E2 quality loss | STRESS all food receipts: 25 % blocked, +2 d | beyond evidence | 7,023 [0, 7,023] | +0 [+7,023] | 27% | 100.0% | 33 | 0 |
| E3 line stoppage | 3 days | short breakdown (assumed) | 7,023 [0, 7,023] | +0 [+0] | 0% | 100.0% | 33 | 0 |
| E3 line stoppage | 10 days | between | 7,023 [0, 39,685] | +0 [+33,059] | 37% | 100.0% | 35 | 0 |
| E3 line stoppage | 25 days | shortest observed pause (B17, fraud 3) | 59,171 [45,895, 177,408] | +54,531 [+172,028] | 100% | 87.6% | 50 | 46 |
| E4 demand | surge +19 % for a month | max steady month, normal 2 | 31,239 [18,530, 40,576] | +28,296 [+36,595] | 100% | 98.2% | 51 | 86 |
| E4 demand | STRESS surge +50 % for a month | beyond evidence | 79,336 [48,770, 97,046] | +74,471 [+96,308] | 100% | 94.3% | 62 | 86 |
| E5 transit delay | +1 day | DataCo q50 (semi-synthetic) | 7,023 [0, 7,023] | +0 [+0] | 0% | 100.0% | 33 | 0 |
| E5 transit delay | +4 days | DataCo q95 (semi-synthetic) | 7,023 [0, 12,415] | +0 [+5,392] | 27% | 100.0% | 34 | 0 |
