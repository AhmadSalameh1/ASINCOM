# Disruption impact (open loop, decisions replayed): fraud_3

60 seeds; each seed draws its own start day uniformly over the steady months (days 24-159); episode 20 days; KPIs from the start day on, each run paired with the baseline run of the same seed.

| disruption | severity | evidence | lost demand from start (units, median [5 %, 95 %]) | extra lost vs same-seed baseline: median [95 %] | share of seeds with any extra loss | fill rate next 60 d | DC stock-out days after start | days of excess loss after the episode ends |
|---|---|---|---|---|---|---|---|---|
| baseline | none | - | 0 [0, 1,932] | +0 [+0] | 0% | 100.0% | 0 | 0 |
| E1 supplier delay | median late shipment (+0.12 x lead) | USAID SCMS q50 | 0 [0, 1,932] | +0 [+0] | 0% | 100.0% | 0 | 0 |
| E1 supplier delay | severe (+0.75 x lead) | USAID SCMS q90 | 246 [0, 1,932] | +0 [+246] | 17% | 100.0% | 1 | 0 |
| E1 supplier delay | extreme (+1.0 x lead) | USAID SCMS q95 | 246 [0, 1,944] | +0 [+246] | 20% | 100.0% | 1 | 0 |
| E2 quality loss | wheat receipts: 4.1 % blocked, +2 d | ERPsim Q2 max, Q1 | 0 [0, 1,932] | +0 [+0] | 0% | 100.0% | 0 | 0 |
| E2 quality loss | all food receipts: 4.1 % blocked, +2 d | ERPsim Q2 max, applied widely | 0 [0, 1,932] | +0 [+0] | 0% | 100.0% | 0 | 0 |
| E2 quality loss | STRESS all food receipts: 25 % blocked, +2 d | beyond evidence | 0 [0, 1,932] | +0 [+0] | 0% | 100.0% | 0 | 0 |
| E3 line stoppage | 3 days | short breakdown (assumed) | 246 [0, 1,932] | +0 [+12] | 5% | 100.0% | 1 | 0 |
| E3 line stoppage | 10 days | between | 1,932 [0, 39,455] | +246 [+37,523] | 55% | 99.3% | 2 | 97 |
| E3 line stoppage | 25 days | shortest observed pause (B17, fraud 3) | 66,609 [0, 113,589] | +64,677 [+111,657] | 88% | 90.9% | 52 | 134 |
| E4 demand | surge +19 % for a month | max steady month, normal 2 | 0 [0, 9,353] | +0 [+7,421] | 47% | 100.0% | 0 | 0 |
| E4 demand | STRESS surge +50 % for a month | beyond evidence | 7,964 [1,552, 26,442] | +7,429 [+24,510] | 100% | 98.6% | 16 | 134 |
| E5 transit delay | +1 day | DataCo q50 (semi-synthetic) | 0 [0, 1,932] | +0 [+0] | 2% | 100.0% | 0 | 0 |
| E5 transit delay | +4 days | DataCo q95 (semi-synthetic) | 0 [0, 6,384] | +0 [+4,452] | 12% | 100.0% | 0 | 0 |
