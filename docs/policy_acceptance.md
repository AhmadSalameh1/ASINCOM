# Policy acceptance (Phase C, step 1)

**Question:** can the nominal policy be SAP's own MRP logic, fed the players' recorded forecast updates, instead of a rule we invent? This is the test DR-3 calls for.

Reproduce with `data/policy_tests.py`; the full tables are in `data/policy/policy_tests.md`. Run: normal 2.

## 1. What the players actually decide: the forecast (decoded)
| Field (PBHI) | Meaning | Evidence |
|---|---|---|
| `PLNMG` | **New open forecast set by the player** | the player's input at each update |
| `ENTMG` | Forecast consumed by sales = cumulative F12 sales | equal in 18 of 21 updates; the other 3 differ only by orders posted in the same second |
| `DBMNG` | Open forecast just before the update = previous PLNMG − sales since then | equal in **20 of 20** |

There are 21 F12 forecast updates in normal 2 (F16 has 23 and F15 has 5).

## 2. How SAP turns the forecast into orders (master data, MARC)
- F12: MRP type PD, lot-for-lot (EX), **minimum lot 16,000, maximum lot 48,000, rounding 1,000**. This explains the observed batch sizes (ledger M1): a requirement above 48k is split into 48k lots, and the remainder is raised to at least 16k.
- Components: purchased (F), planned delivery time 1 day, rounding 10 kg (food) or 1,000 (packaging), with no minimum or maximum.

## 3. Production: accepted
Replica: **net = open forecast − F12 stock (plant + DCs) − open production orders**, then lots per MARC.

| Result | Updates |
|---|---|
| Exact match of total **and** lot split | **16 of 21** |
| No orders because the forecast was changed again within 3–9 minutes, before MRP was run (only the last update counts) | 4 of 21 |
| **Explained** | **20 of 21** |
| Unexplained | 1 (update 14): replica 48k + 16k, recorded 16k + 35k. Most likely a manual edit. |

**Conclusion:** the production decisions of the normal 2 players are reproduced by SAP's documented MRP logic, driven only by their recorded forecasts. No parameter was fitted.

## 4. Purchasing: not yet accepted
- **Observed sequence:** at each MRP run the component POs are created first, and the planned orders are converted to production orders shortly afterwards.
- **Test** (packaging, 1 box per unit for all products, so recipe changes don't matter): box POs = units of the next production-order burst.
  - **8 of 32 PO bursts match exactly, including all of the first 4.**
  - Later POs are consistently **smaller** than the following production.
- Explanations consistent with the data, not yet tested:
  1. MRP nets component requirements against component stock on hand, which builds up later in the year.
  2. MRP runs per product: F16 and F15 have their own forecast updates, and the burst grouping mixes several runs.
- Also seen: the planned order of a superseded update (update 4: 41,000) **was** used to buy components (a 41,000-box PO), even though it was never converted into a production order.

**Next test:** a multi-product MRP replica (F12, F16 and F15, each with its own recorded forecast history), netting component requirements against component stock and open POs. Acceptance criterion: the same standard as production, with most PO bursts reproduced exactly and every miss explained.

**Fallback if it cannot be reproduced:** component stock does not constrain steady operation (K1 ≤ 0.8 %). The purchasing policy could then be represented as "POs = recipe × planned production, netted against stock". Its fit would be reported as an aggregate (component stock distribution, stock-out days) rather than PO by PO, and that weaker standard would be stated openly.
