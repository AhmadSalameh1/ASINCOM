# B: decision levers and controllers

## Principle
The AI decision layer (L2) may only use the **levers the ERPsim players actually had**:
1. **Production-order conversions** (which planned orders, when, how much)
2. **Purchase orders** (material, when, how much)
3. **Transfers from the plant to each DC** (when, how much)

No invented levers (e.g. "emergency supplier", "surge capacity") are used unless they can be backed by the data.

## Implementation
- `model/twin/twin.py`: `policy="controller"` hands the three decisions to a controller object each day.
- `model/twin/controllers.py`:
  - `ReplayController`: the players' recorded decisions, with deferred transfers. Verified to reproduce `policy="replay", push_rule="replay_deferred"` exactly (validation Amendment 3).
  - `BufferController(k)`: the players' decisions plus extra POs that keep each component's available + on-order stock at ≥ k days of recent consumption (lever 2 only).
- The MRP replica (accepted policy model) remains available as `policy="mrp"`. The shipping rule `lag1` is **not accepted** as a model of the players (`docs/validation_report.md`). Shipping is therefore treated as a **decision for the AI layer**, not as a fixed model.

## First closed-loop comparison
`model/twin/policy_comparison.py`; results in `model/twin/policies/`. 40 seeds, randomised start days, common random numbers. Lost demand is from the start day on (median).

**normal 2** (re-run with deferred transfer replay, validation Amendment 3):
| Disruption | players | + buffer 2 d | + buffer 5 d | + buffer 10 d |
|---|---|---|---|---|
| baseline none | 7,023 | 0 | 0 | 0 |
| E1 supplier delay severe (+0.75 x lead) | 7,023 | 0 | 0 | 0 |
| E2 quality loss all food receipts: 4.1 % blocked, +2 d | 7,023 | 0 | 0 | 0 |
| E3 line stoppage 3 days | 7,023 | 0 | 0 | 0 |
| E3 line stoppage 10 days | 7,023 | 7,023 | 0 | 0 |
| E4 demand surge +19 % for a month | 31,220 | 29,004 | 28,212 | 28,212 |
| mean component stock (baseline) | 398,881 | 481,117 | 613,194 | 884,109 |

**fraud 2:** the median loss is 0 for every controller. The tails are **not monotonic** in the buffer size: under the quality loss, the 95th-percentile loss is 13,363 / 5,669 / 33,950 / 0 units for 0 / 2 / 5 / 10 days of buffer. Extra POs change which orders can start when, through the full-batch start rule and the FIFO line.

## Findings for the paper
1. **Levers must match disruptions.** In normal 2, a 2-day component buffer (lever 2) removes the median loss under every upstream disruption and short stoppage, at +21 % component stock. It barely moves the demand-surge loss (31,220 → 28,212), which calls for finished-goods or DC stock (levers 1 and 3).
2. **Simple fixed rules are unreliable.** Their effect can be non-monotonic, because of the line's full-batch and FIFO mechanics. This argues for a decision layer that is **state- and disruption-aware** (L2) and whose recommendations are **checked on the twin before use** (L4, certification).
3. **The trade-off is explicit:** lost demand vs inventory held. L2's objective will be stated on these two quantities (plus stock-out days).

## Next (for L2)
Done in `docs/ai_layers.md`:
- The action set covers all three levers: component buffer, an extra F12 batch, F12 priority on the line, and DC rebalancing.
- L2 chooses among them per disruption and state, under a service constraint, with the same protocol (randomised timing, common random numbers, three years).
