# Modelling decision records

Each decision is stated with the options considered, the evidence for the choice (with its evidence-ledger ID from `data/calibration/evidence_ledger.md`), the result that would overturn it, and the risk that remains. All numbers are reproducible with `data/derive_calibration.py`. Values are given as normal 2 / fraud 2 / fraud 3.

---

## DR-1: Time unit = 1 game day; decisions take effect at the next day tick

**Decision.** One model time unit is one ERPsim game day. A game year is 240 time units, of which 229 are played in normal 2 (days 5–233). Physical events (deliveries, production, transfers, sales) happen on day ticks. Player decisions made between ticks take effect at the next tick.

**Options considered**
| Option | Verdict |
|---|---|
| **1 game day** | Chosen |
| ¼ game day | Rejected: the data holds no physical information below one day (see evidence); a finer unit would only encode how fast players clicked within a ~58-second day, and it quadruples the model's state space. |
| 1 round (20 days) | Rejected: lead times are 1–6 days and production 1–2 days; a round would erase them. |

**Evidence**
- **W0:** 95.3 % / 90.5 % / 89.6 % of engine postings (goods receipts, component issues, transfers, sales issues) fall in a short burst (−6 s … +15 s) around a day tick. Goods receipts are posted 1–5 s before the tick; sales, production and transfer postings follow within seconds.
- **L3, L4:** measured in ticks, lead times are whole numbers, 1–6 days, with the same support in all three years.
- **M6:** the line produces exactly **24,000 units per processing day** in all three years, so capacity is defined per day.
- Purchase-order creation (a player action) is spread across the day (median 36 s after the tick), as expected for human decisions.

**Would be overturned by:** a large share of engine postings between ticks, or lead times that are not whole days. Neither is observed.

**Remaining risk:** the time players take to react inside a day is not modelled. It is below the resolution of every physical process, and it is irrelevant for the AI decision layer, which decides once per tick.

---

## DR-2: Product scope = AA-F12 in detail, plus the other products as background load on the shared line

**Decision.** Model AA-F12 end to end: its 71 customers, 3 DCs, 5 components, purchasing and production. Represent the other products (F16, F15, and F13 in fraud 2) only as production orders that occupy the **shared production line**, with their order count, batch size and release gaps taken from the data.

**Options considered**
| Option | Verdict |
|---|---|
| F12 only, with a fixed share of line capacity | Rejected: it cannot reproduce queueing behind other products' orders (M5) or show how a line stoppage hits F12 through the queue. |
| **F12 detailed + other products as line background load** | Chosen |
| All products in full detail | Rejected: shared components do not constrain steady operation (K1 ≤ 0.8 %), so modelling the other products' customers and materials adds state space without changing F12's behaviour under normal operation. |

**Evidence**
- **Shared line:** F12, F15 and F16 use the same work centre (routing operations on work centre 10000000). The line is busy on **93 % / 82 % / 89 %** of steady-month days (M7), and F12 orders wait a median **2 / 1 / 1 days** before they start (M5). Line contention is therefore real and must be modelled.
- **Shared components do not bind in steady operation:** in the steady months, F12 components end a day at zero stock on **0.8 % / 0 % / 0 %** of days (K1; in normal 2 a single packaging day). Zero-stock days occur only at game start, when stock starts empty until the first deliveries arrive, and at the end of the game (K2; normal 2 months 1–2, 4, 11–12). Competition for materials does not constrain production in normal operation.
- **Line rate:** 24,000 units per day in all three years (M6), so line occupancy per order is `batch / 24,000` days.
- **F12 is a major product:** 47 % / 35 % / 33 % of production orders (M4).

**Also supported by Phase B** (`data/structure/structure_evidence.md`): all products are routed to the same work centre (B13); output is at most 24,000 units per tick outside batched catch-up postings (B12); and the F12 network is closed, so produced = transferred = sold + closing stock with zero residual in all three years (B15).

**Would be overturned by:** Phase D validation failing to reproduce F12 queue and flow times on fraud 2 or fraud 3. If that happens, move to full multi-product detail.

**Remaining risk:** in a *material-shortage* disruption on a shared component (wheat, oats, packaging), other products' consumption can become binding. For those scenarios, add the other products' component consumption (their BOM × their production) as a second background load. The data supports this, since the BOMs of F15, F16 and F13 are known.

---

## DR-3: Nominal policy = the observed decisions of the normal 2 players

**Decision.** The model's nominal operating policy (when to reorder components and how much; when to start production and in what batch size; when and how much to transfer to DCs) is extracted from normal 2. Where the L2 decision layer acts, it replaces parts of this policy.

**Options considered**
| Option | Verdict |
|---|---|
| **Observed normal 2 policy** | Chosen: it is what the calibration year actually did. |
| A textbook optimised policy, e.g. an (s, Q) rule with optimised parameters | Rejected as the nominal policy: it would be an assumption, not evidence. It is kept as a *benchmark* for the L2 decision layer. |
| An average of the three years' policies | Rejected: it mixes three teams' strategies into a policy nobody played. |

**Evidence that these are policies, not physics:** these quantities vary strongly between years, while physical parameters do not.
- Reorder points (P2): e.g. packaging 216.5k / 212k / 234k; blueberries 21k / 32k / 51.5k.
- Batch mix (M1), production trigger stock (M3): 21k / 16k / 24k.
- Peak DC stock (C1): 132–144k / 67–77k / 44–81k.
- By contrast, the line rate (M6) is identical in all three years, and lead-time support (L3, L4) is the same.

**Validation design that follows from this:** the undisrupted model is validated on fraud 2 and fraud 3 **with each year's own policy parameters** (policy replay). A successful validation then tests the model's physics, not whether the players behaved the same.

**Would be overturned by:** a simple rule failing to reproduce normal 2's decision timing (to be tested in Phase C: extract reorder-point and batch rules, then measure how well they reproduce the PO and production-order days). If rules fit poorly, replay the recorded decision sequence instead of a rule.

**Remaining risk:** a single team's policy is one sample of behaviour. The ensemble and the L2 decision layer address this directly.

---

## Cleaning rules behind these numbers
Rules C0–C5 are listed with their effects in `data/calibration/cleaning_log.md`:
- **C0:** integrity checks
- **C1:** fraud-labelled documents removed
- **C2:** steady-state window (months with ≤ 5 % zero-stock days at every DC; normal 2: months 4–9)
- **C3:** promotion orders removed from baseline demand
- **C4:** POs created before the first trading tick (game initialisation) removed from lead times
- **C5:** scrap-labelled POs removed from lead times and kept as quality-event evidence

## Open items to resolve in Phase D
- fraud 2 has 3 food receipts with a lead time of 15 days and one of 0 days, which don't appear in the other years. Check them against the fraud labels (possibly unlabelled consequences of a labelled fraud) before using fraud 2's lead times for validation.
- Production processing time has a long tail (q95 ≈ 19–25 days). Check whether those orders overlap the production-stoppage months.
