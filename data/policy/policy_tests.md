# Policy acceptance tests (normal 2)

## MRP settings of AA-F12 (MARC)
MRP type PD, lot size EX, min lot 16000, max lot 48000, rounding 1000.

## Forecast history (PBHI)
- 21 forecast updates for AA-F12.
- ENTMG equals cumulative AA-F12 sales at the update in 18 of 21 (the rest differ only by orders posted in the same second): **ENTMG = forecast consumed by sales**.
- DBMNG equals previous PLNMG minus sales since then in 20 of 20: **DBMNG = open forecast before the update; PLNMG = new open forecast set by the player**.

## Production: MRP replica vs recorded production orders
net = open forecast - finished-goods stock (plant + DCs) - open production; lots per MARC.

- exact total and lot split: **16 of 21** updates
- no orders because the forecast was updated again within 15 min, before MRP was run: 4
- **explained: 20 of 21**

|   update |   open_forecast |   fg_stock |   open_production |    net | predicted_lots                      | actual_lots                         |   next_update_after_s | total_match   | lots_match   | superseded_before_mrp   |
|---------:|----------------:|-----------:|------------------:|-------:|:------------------------------------|:------------------------------------|----------------------:|:--------------|:-------------|:------------------------|
|        0 |           40000 |          0 |                 0 |  40000 | [40000]                             | [40000]                             |                  3305 | True          | True         | False                   |
|        1 |           34473 |      22580 |                 0 |  11893 | [16000]                             | [16000]                             |                   773 | True          | True         | False                   |
|        2 |          116000 |      20660 |                 0 |  95340 | [48000, 48000]                      | [48000, 48000]                      |                   998 | True          | True         | False                   |
|        3 |          150340 |      16000 |             80000 |  54340 | [16000, 48000]                      | [16000, 48000]                      |                  1129 | True          | True         | False                   |
|        4 |          173830 |      93490 |             40000 |  40340 | [41000]                             | []                                  |                   557 | False         | False        | True                    |
|        5 |          200061 |      84721 |             24000 |  91340 | [44000, 48000]                      | [44000, 48000]                      |                  3423 | True          | True         | False                   |
|        6 |          200641 |     106301 |             76000 |  18340 | [19000]                             | []                                  |                   234 | False         | False        | True                    |
|        7 |          376116 |     133776 |             24000 | 218340 | [27000, 48000, 48000, 48000, 48000] | [27000, 48000, 48000, 48000, 48000] |                   788 | True          | True         | False                   |
|        8 |          415395 |     169055 |            147000 |  99340 | [16000, 48000, 48000]               | [16000, 48000, 48000]               |                  1853 | True          | True         | False                   |
|        9 |          351839 |     239499 |             75000 |  37340 | [38000]                             | []                                  |                   195 | False         | False        | True                    |
|       10 |          374622 |     212282 |             75000 |  87340 | [40000, 48000]                      | [40000, 48000]                      |                   383 | True          | True         | False                   |
|       11 |          400830 |     225490 |            123000 |  52340 | [16000, 48000]                      | [16000, 48000]                      |                  2273 | True          | True         | False                   |
|       12 |          400178 |     313838 |             40000 |  46340 | [47000]                             | [47000]                             |                   263 | True          | True         | False                   |
|       13 |          450958 |     372618 |             23000 |  55340 | [16000, 48000]                      | [16000, 48000]                      |                   867 | True          | True         | False                   |
|       14 |          450927 |     400587 |                 0 |  50340 | [16000, 48000]                      | [16000, 35000]                      |                  4234 | False         | False        | False                   |
|       15 |          152044 |     102704 |                 0 |  49340 | [16000, 48000]                      | [16000, 48000]                      |                   354 | True          | True         | False                   |
|       16 |          219510 |      86170 |             48000 |  85340 | [38000, 48000]                      | [38000, 48000]                      |                   520 | True          | True         | False                   |
|       17 |          250131 |     102791 |             92000 |  55340 | [16000, 48000]                      | [16000, 48000]                      |                   658 | True          | True         | False                   |
|       18 |          232425 |     140516 |                 0 |  91909 | [44000, 48000]                      | []                                  |                   334 | False         | False        | True                    |
|       19 |          250411 |     106071 |                 0 | 144340 | [16000, 48000, 48000, 48000]        | [16000, 48000, 48000, 48000]        |                  2568 | True          | True         | False                   |
|       20 |           64000 |          0 |                 0 |  64000 | [16000, 48000]                      | [16000, 48000]                      |                   nan | True          | True         | False                   |

## Purchasing: packaging POs vs units of the next production-order burst
Packaging is 1 box per unit for every product, so this test does not depend on recipe changes.

- exact match: **8 of 32** PO bursts; the first 4 bursts all match
- later POs are smaller than the following production: consistent with MRP netting against component stock and with per-product MRP runs (F16 and F15 have their own forecast updates). **Not yet reproduced; see docs/policy_acceptance.md.**

|   burst |   boxes_ordered |   units_in_next_production_burst | match   |
|--------:|----------------:|---------------------------------:|:--------|
|       0 |           80000 |                            80000 | True    |
|       2 |           32000 |                            32000 | True    |
|       4 |          192000 |                           192000 | True    |
|       6 |          128000 |                           128000 | True    |
|       8 |           41000 |                            92000 | False   |
|       9 |           51000 |                            92000 | False   |
|      11 |           19000 |                           219000 | False   |
|      12 |          200000 |                           219000 | False   |
|      14 |          112000 |                           112000 | True    |
|      15 |          112000 |                           160000 | False   |
|      16 |          100000 |                            48000 | False   |
|      17 |           86000 |                           288000 | False   |
|      18 |           90000 |                           368000 | False   |
|      19 |          128000 |                           128000 | True    |
|      21 |           88000 |                           216000 | False   |
|      22 |          128000 |                           232000 | False   |
|      23 |           90000 |                            16000 | False   |
|      24 |           64000 |                           141000 | False   |
|      26 |           76000 |                            89000 | False   |
|      28 |          112000 |                           126000 | False   |
|      29 |           78000 |                           238000 | False   |
|      30 |           48000 |                           112000 | False   |
|      31 |           44000 |                           268000 | False   |
|      32 |          112000 |                           258000 | False   |
|      33 |          102000 |                           102000 | True    |
|      35 |           86000 |                           214000 | False   |
|      36 |          128000 |                           278000 | False   |
|      38 |          192000 |                           260000 | False   |
|      39 |           68000 |                           176000 | False   |
|      41 |           64000 |                            64000 | True    |
|      42 |               0 |                           254000 | False   |
|      43 |          174000 |                           190000 | False   |
