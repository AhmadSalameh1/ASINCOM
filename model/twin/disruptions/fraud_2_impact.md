# Disruption impact (open loop, decisions replayed): fraud_2

60 seeds; each seed draws its own start day uniformly over the steady months (days 23-159); episode 20 days; KPIs from the start day on, each run paired with the baseline run of the same seed.

| disruption | severity | evidence | lost demand from start (units, median [5 %, 95 %]) | extra lost vs same-seed baseline: median [95 %] | share of seeds with any extra loss | fill rate next 60 d | DC stock-out days after start | days of excess loss after the episode ends |
|---|---|---|---|---|---|---|---|---|
| baseline | none | - | 0 [0, 13,363] | +0 [+0] | 0% | 100.0% | 0 | 0 |
| E1 supplier delay | median late shipment (+0.12 x lead) | USAID SCMS q50 | 0 [0, 13,363] | +0 [+0] | 0% | 100.0% | 0 | 0 |
| E1 supplier delay | severe (+0.75 x lead) | USAID SCMS q90 | 0 [0, 13,363] | +0 [+0] | 2% | 100.0% | 0 | 0 |
| E1 supplier delay | extreme (+1.0 x lead) | USAID SCMS q95 | 0 [0, 13,363] | +0 [+0] | 2% | 100.0% | 0 | 0 |
| E2 quality loss | wheat receipts: 4.1 % blocked, +2 d | ERPsim Q2 max, Q1 | 0 [0, 5,669] | +0 [+5,406] | 20% | 100.0% | 0 | 0 |
| E2 quality loss | all food receipts: 4.1 % blocked, +2 d | ERPsim Q2 max, applied widely | 0 [0, 13,363] | +0 [+13,363] | 13% | 100.0% | 0 | 0 |
| E2 quality loss | STRESS all food receipts: 25 % blocked, +2 d | beyond evidence | 0 [0, 13,363] | +0 [+13,363] | 13% | 100.0% | 0 | 0 |
| E3 line stoppage | 3 days | short breakdown (assumed) | 0 [0, 13,363] | +0 [+0] | 0% | 100.0% | 0 | 0 |
| E3 line stoppage | 10 days | between | 0 [0, 13,363] | +0 [+0] | 3% | 100.0% | 0 | 0 |
| E3 line stoppage | 25 days | shortest observed pause (B17, fraud 3) | 13,363 [0, 48,407] | +13,363 [+44,197] | 83% | 93.0% | 5 | 22 |
| E4 demand | surge +19 % for a month | max steady month, normal 2 | 6,254 [0, 22,556] | +5,915 [+12,040] | 92% | 100.0% | 21 | 68 |
| E4 demand | STRESS surge +50 % for a month | beyond evidence | 38,653 [8,235, 49,587] | +36,399 [+49,293] | 100% | 96.9% | 31 | 91 |
| E5 transit delay | +1 day | DataCo q50 (semi-synthetic) | 0 [0, 13,363] | +0 [+0] | 0% | 100.0% | 0 | 0 |
| E5 transit delay | +4 days | DataCo q95 (semi-synthetic) | 0 [0, 13,363] | +0 [+0] | 0% | 100.0% | 0 | 0 |
