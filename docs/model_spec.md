# V12 model specification (Phase C)

This is the single specification for both implementations:
- the **Python reference twin** (`model/twin/`), which runs anywhere and is used for Phase D validation;
- the **UPPAAL V12 model** (`model/uppaal/`), used for statistical model checking and Stratego.

Both must implement exactly what is written here. A cross-check script compares their outputs. Every element cites its evidence:
- `S*`, `D*`, `L*`, `M*`, … are rows of `data/calibration/evidence_ledger.md`;
- `B*` are checks in `data/structure/structure_evidence.md`;
- `DR-*` are entries in `docs/decision_records.md`.

---

## 1. Time
- Discrete time: **1 step = 1 game day** (DR-1). The horizon is one game year: 240 days, of which 229 are played in normal 2 (days 5–233).
- Order of events within a day (engine burst, W0):
  1. supplier receipts
  2. production output and component consumption
  3. customer orders and deliveries
  4. player decisions, which take effect at the next tick

  Receipts are posted just before the tick, and sales and production just after it (B3, W0).

## 2. Entities and state
| Entity | State | Evidence |
|---|---|---|
| 5 components c ∈ {R02, R05, R06, P01, P02} | stock `I_c`, open POs (qty, due day) | S3, B6–B8, B16 |
| Shared production line | queue of released orders (product, qty); remaining qty of the order in process | B12, B13, M6, M8, DR-2 |
| Plant finished-goods stock (F12) | `I_plant` | B14, B15 |
| 3 DCs d ∈ {North, South, West} | `I_d` | B5, B14, C1 |
| 71 customers k, each with a fixed DC d(k) | next order day | S1, S2, B5 |
| Other products (F16, F15) | planning level: open forecast, total stock, their orders on the shared line | DR-2 (updated), M8, rule R4 |

**Initial state:** all stocks 0, no open orders (B16).

## 3. Processes (one step)
### 3.1 Supplier receipts
- A PO for component c placed on day t arrives on day `t + L`, with `L ~` the empirical lead-time PMF (L3 for food, L4 for packaging). The full quantity arrives (B7).
- Split receipts occur only in scrap events (B8). They are a disruption mechanism, not part of nominal operation.

### 3.2 Production (shared line)
- Released orders are processed first-in, first-out on one serial line at up to **24,000 units per day** (M6, B12). An order ending mid-day hands over to the next.
- **An order starts only when components for its whole batch are in stock** (78 of 78 recorded starts), and **a product switch costs one idle day** (recorded gap between orders: median 1 day on a switch, 0 otherwise). This is line rule `erpsim` in the twin (`docs/twin.md`).
- On each production day, the F12 output `q` consumes `BOM_c × q` of each component c (S3, B11). If a component is short, output is limited to what the components allow.
  - This is never binding in steady operation (K1). It is kept so that material-shortage disruptions act correctly.
- Other products' orders occupy the line with their own batch sizes (M8). They consume no F12 components (DR-2). Adding their shared-component use is a switch for material-shortage scenarios.
- Finished F12 goes to `I_plant`, and the order is complete when its full quantity is out (B10).

### 3.3 Distribution
- Plant → DC transfers are instantaneous (B14). No DC → DC transfers and no returns.
- The quantity and timing of transfers is a **policy** (§4).

### 3.4 Customers and sales
- Each customer k orders F12 at intervals drawn from the inter-order distribution (D1, D2; steady months only, rule C2). The order size is drawn from D3.
- **Sale = min(order, I_d(k))**, delivered the same day (B2, B3). The excess is **lost**, with no backorder (B4). Lost demand is recorded as a KPI.

## 4. Nominal policy: the observed decision process of the normal 2 players (DR-3)
The Phase C analysis shows how the players decided:

| Decision | Finding | Evidence |
|---|---|---|
| Purchasing | Every PO copies an MRP-generated purchase requisition 1:1 (254 of 254 quantities identical). 98 % of requisitions become POs (B6). Planning is lot-for-lot (MARC: MRP type PD, lot size EX). | EBAN ↔ EKPO, MARC |
| Production | Production orders come from the same MRP run (planned orders → production orders). Lot-for-lot, with the batch sizes observed in M1. | AFKO, PLAF, MARC |
| What the players actually decide | The **sales forecast**: 21 recorded forecast updates for F12 in normal 2, about every 5–10 days. MRP turns the forecast into requirements. | PBHI + PBIMT |
| DC transfers | Push, not pull: 47 of 64 transfers happen 0–1 days after a production receipt, and 51 of 64 go to all three DCs. DC stock after a transfer is **not** constant (CV 0.3–0.5), so an order-up-to rule is rejected. | MSEG 301 |
| Rejected alternatives | Reorder-point rules for production and purchasing: the trigger levels vary too much (CV 0.5–0.8 of stock or position at decision time). | this analysis |

**Consequence:** the nominal policy is implemented as
1. **an MRP replica**: net requirement = forecast − (stock + open orders), lot-for-lot, exploded through the BOM for components. This is SAP's documented logic, so no parameter is invented;
2. **the forecast input**: replayed from PBHI for validation (Phase D), and a stated forecast rule (e.g. recent sales × cover) for experiments. The fit of that rule to the recorded forecasts will be reported;
3. **a push distribution rule** fitted to the MSEG 301 pattern (ship within 0–1 days of output, split across the DCs), with its fit reported.

**Policy acceptance status** (`docs/policy_acceptance.md`):
- PBHI decoded: PLNMG = the new open forecast set by the player.
- **Production: accepted.** The MRP replica, with MARC lot rules (min 16k, max 48k, rounding 1k), explains 20 of 21 recorded forecast updates exactly.
- **Purchasing: accepted.** A three-product MRP replica (`data/mrp_replica.py`, rules R1–R6) reproduces 29 of 37 MRP runs exactly for every component. Five of the 8 misses are in the last 21 minutes of the game.
- The twin's purchasing module **is** this replica. For experiments it runs on simulated state, with the other products' forecasts as background (DR-2).

## 5. Parameters
The values come from `calibration_normal_2.json`. Ensemble ranges come from the spread across the three runs (DR-0).

| Symbol | Meaning | Ledger |
|---|---|---|
| `IO` | customer inter-order PMF (days) | D1, D2 |
| `OQ` | order-size distribution | D3 |
| `LT_food`, `LT_pack` | lead-time PMFs | L3, L4 |
| `CAP` | line capacity = 24,000 units/day | M6 |
| `BOM` | per-unit component use | S3 (run-specific; B11) |
| `BATCH` | production batch sizes {16k, 48k, …} | M1 |
| `OTHER` | other products' orders (count, batch, gaps) | M8 |
| `DC(k)` | customer → DC map | S2 |

## 6. Outputs (KPIs), matching the existing 17-query battery where applicable
- service level (fill rate), lost demand, stock-out days per DC
- DC and plant stock
- line utilisation and queue time
- component stock and lead time realised
- recovery time after a disruption

## 7. Validation hooks (Phase D)
Run the twin with fraud 2's (then fraud 3's) own recipe (B11), forecast replay and policy, then compare with the recorded data:
- lead-time, inter-order, queue, processing and DC-stock distributions (KS tests, quantile coverage)
- monthly throughput
- the effect of the observed production pauses (B17) on DC stock-outs
