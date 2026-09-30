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

## 4. Purchasing: accepted with a three-product MRP replica (`data/mrp_replica.py`)
Component purchasing is shared by all products, so the replica plans **F12, F16 and F15 together**, each from its own recorded forecast history. Each rule is an SAP mechanism found in the data; none is a fitted parameter.

| Rule | Mechanism | Evidence that made it necessary |
|---|---|---|
| R1 | Open forecast = last PLNMG − sales **since that update** | ENTMG is not always equal to cumulative sales (F16), so consumption must be counted from the update |
| R2–R3 | Product net requirement and lot-for-lot with MARC min/max/rounding | Section 3 |
| R4a | Component need of open production orders = **reserved** quantity (RESB) until the final issue is posted | An F16 order reserved 14,400 kg but issued 7,200; MRP kept buying the open 7,200, a constant offset in six consecutive runs |
| R4b | Planned orders use the **BOM in force** (the recipe of the next converted order) | The F16 recipe changed mid-game; POs match the new recipe exactly |
| R4c | Direct forecasts on packaging (100,000 boxes and bags) add to requirements | PBHI entries for AA-P01 and AA-P02 |
| R5 | **Blocked stock** (INSMK `3`, from scrap events) is not available | Constant offsets of 100 kg (R01) and 1,000 (P02) matched blocked stock in MARD exactly |
| R6 | PO = net rounded to the MARC rounding value | MARC |

**Result (normal 2): 29 of 37 MRP runs reproduced exactly for every component** (191 of 245 component-run pairs).
- The 8 runs not reproduced: 5 are in the **last 21 minutes of the game**, where end-of-game buying departs from MRP.
- 3 (139, 62 and 56 minutes before the end) show the same relative error on every component, so the planned product quantity differs, most likely through manual planned-order edits that aren't in the data.

**Conclusion:** the players' purchasing is SAP MRP driven by their forecasts, reproduced exactly in 78 % of runs, with every miss localised. Together with Section 3, **the whole nominal policy is SAP logic plus recorded forecasts**. The only fitted element left is the DC push rule.

### Side result: measured quality-loss size (ledger Q2)
Scrap events set part of a receipt aside: as blocked stock (normal 2), or as quality-inspection stock that is never released (fraud 2, fraud 3). Across the 6 events in the three years, **0.2 % to 4.1 % of the affected receipt is lost**, and the receipt arrives later than normal (Q1). This sets the evidence-based range for the quality-loss disruption in Phase E.

## 4b. First purchasing test (superseded)
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
