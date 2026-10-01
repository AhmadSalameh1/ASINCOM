# Controllers under disruption: normal_2

40 seeds, randomised start days over the steady months; values from the start day on.

| disruption | controller | lost demand (median) | lost 95 % | mean component stock (units) | mean DC stock (units) |
|---|---|---|---|---|---|
| baseline none | players (replay) | 7,023 | 7,023 | 398,881 | 110,602 |
| baseline none | players + component buffer 2 d | 0 | 7,023 | 481,117 | 110,601 |
| baseline none | players + component buffer 5 d | 0 | 0 | 613,194 | 110,666 |
| baseline none | players + component buffer 10 d | 0 | 0 | 884,109 | 110,666 |
| E1 supplier delay severe (+0.75 x lead) | players (replay) | 7,023 | 7,069 | 393,341 | 109,086 |
| E1 supplier delay severe (+0.75 x lead) | players + component buffer 2 d | 0 | 7,023 | 474,549 | 109,251 |
| E1 supplier delay severe (+0.75 x lead) | players + component buffer 5 d | 0 | 0 | 594,359 | 110,441 |
| E1 supplier delay severe (+0.75 x lead) | players + component buffer 10 d | 0 | 0 | 863,048 | 110,635 |
| E2 quality loss all food receipts: 4.1 % blocked, +2 d | players (replay) | 7,023 | 7,070 | 404,679 | 109,343 |
| E2 quality loss all food receipts: 4.1 % blocked, +2 d | players + component buffer 2 d | 0 | 7,023 | 482,561 | 109,817 |
| E2 quality loss all food receipts: 4.1 % blocked, +2 d | players + component buffer 5 d | 0 | 0 | 607,854 | 110,645 |
| E2 quality loss all food receipts: 4.1 % blocked, +2 d | players + component buffer 10 d | 0 | 0 | 876,837 | 110,666 |
| E3 line stoppage 3 days | players (replay) | 7,023 | 7,023 | 415,349 | 109,100 |
| E3 line stoppage 3 days | players + component buffer 2 d | 0 | 7,023 | 497,276 | 109,130 |
| E3 line stoppage 3 days | players + component buffer 5 d | 0 | 0 | 629,376 | 109,187 |
| E3 line stoppage 3 days | players + component buffer 10 d | 0 | 0 | 901,965 | 109,187 |
| E3 line stoppage 10 days | players (replay) | 7,023 | 39,685 | 502,834 | 108,262 |
| E3 line stoppage 10 days | players + component buffer 2 d | 7,023 | 36,548 | 584,755 | 108,477 |
| E3 line stoppage 10 days | players + component buffer 5 d | 0 | 36,548 | 719,552 | 108,460 |
| E3 line stoppage 10 days | players + component buffer 10 d | 0 | 36,548 | 997,178 | 108,460 |
| E4 demand surge +19 % for a month | players (replay) | 31,220 | 43,625 | 398,881 | 97,904 |
| E4 demand surge +19 % for a month | players + component buffer 2 d | 29,004 | 36,602 | 481,117 | 97,903 |
| E4 demand surge +19 % for a month | players + component buffer 5 d | 28,212 | 36,602 | 613,194 | 97,968 |
| E4 demand surge +19 % for a month | players + component buffer 10 d | 28,212 | 36,602 | 884,109 | 97,968 |
