# Disruption impact (open loop, decisions replayed): normal_2

60 seeds; each seed draws its own start day uniformly over the steady months (days 63-152); episode 20 days; KPIs from the start day on, each run paired with the baseline run of the same seed.

| disruption | severity | evidence | lost demand from start (units, median [5 %, 95 %]) | extra lost vs same-seed baseline: median [95 %] | share of seeds with any extra loss | fill rate next 60 d | DC stock-out days after start | days of excess loss after the episode ends |
|---|---|---|---|---|---|---|---|---|
| baseline | none | - | 24,058 [20,858, 24,058] | +0 [+0] | 0% | 100.0% | 48 | 0 |
| E1 supplier delay | median late shipment (+0.12 x lead) | USAID SCMS q50 | 24,058 [20,858, 44,858] | +0 [+24,000] | 48% | 100.0% | 48 | 12 |
| E1 supplier delay | severe (+0.75 x lead) | USAID SCMS q90 | 56,858 [23,898, 79,658] | +32,800 [+58,800] | 73% | 98.6% | 57 | 56 |
| E1 supplier delay | extreme (+1.0 x lead) | USAID SCMS q95 | 57,658 [23,898, 79,658] | +33,600 [+58,800] | 80% | 98.2% | 58 | 62 |
| E2 quality loss | wheat receipts: 4.1 % blocked, +2 d | ERPsim Q2 max, Q1 | 24,058 [20,858, 57,658] | +3,200 [+36,000] | 52% | 100.0% | 48 | 36 |
| E2 quality loss | all food receipts: 4.1 % blocked, +2 d | ERPsim Q2 max, applied widely | 48,058 [20,858, 59,458] | +24,000 [+38,440] | 77% | 99.0% | 57 | 51 |
| E2 quality loss | STRESS all food receipts: 25 % blocked, +2 d | beyond evidence | 46,458 [20,858, 59,458] | +24,000 [+38,440] | 78% | 98.8% | 57 | 50 |
| E3 line stoppage | 3 days | short breakdown (assumed) | 51,258 [20,858, 63,258] | +27,200 [+39,200] | 63% | 98.5% | 57 | 43 |
| E3 line stoppage | 10 days | between | 104,658 [24,058, 143,658] | +80,600 [+122,800] | 92% | 92.4% | 63 | 71 |
| E3 line stoppage | 25 days | shortest observed pause (B17, fraud 3) | 207,658 [158,858, 256,658] | +183,600 [+235,800] | 100% | 72.0% | 77 | 86 |
| E4 demand | surge +19 % for a month | max steady month, normal 2 | 51,422 [39,392, 57,764] | +28,300 [+36,599] | 100% | 97.9% | 58 | 86 |
| E4 demand | STRESS surge +50 % for a month | beyond evidence | 97,255 [69,272, 117,717] | +74,475 [+96,312] | 100% | 91.6% | 64 | 86 |
| E5 transit delay | +1 day | DataCo q50 (semi-synthetic) | 24,058 [20,858, 24,058] | +0 [+0] | 0% | 100.0% | 48 | 0 |
| E5 transit delay | +4 days | DataCo q95 (semi-synthetic) | 24,058 [20,858, 29,454] | +0 [+5,396] | 27% | 100.0% | 48 | 0 |
