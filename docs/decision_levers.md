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
  - `ReplayController`: the players' recorded decisions. Verified to reproduce `policy="replay"` exactly.
  - `BufferController(k)`: the players' decisions plus extra POs that keep each component's available + on-order stock at ≥ k days of recent consumption (lever 2 only).
- The MRP replica (accepted policy model) remains available as `policy="mrp"`. The shipping rule `lag1` is **not accepted** as a model of the players (`docs/validation_report.md`). Shipping is therefore treated as a **decision for the AI layer**, not as a fixed model.

## First closed-loop comparison
`model/twin/policy_comparison.py`; results in `model/twin/policies/`. 40 seeds, randomised start days, common random numbers. Lost demand is from the start day on (median).

**normal 2 (the fragile year):**
| Disruption | players | + buffer 2 d | + buffer 5 d | + buffer 10 d |
|---|---|---|---|---|
| none | 24,058 | 20,858 | 20,858 | 20,858 |
| E1 supplier delay q90 | 56,858 | 57,658 | **20,858** | 20,858 |
| E2 quality 4.1 % all food | 52,458 | 29,858 | **20,858** | 20,858 |
| E3 stoppage 3 d | 51,258 | 51,258 | 51,258 | 51,258 |
| E3 stoppage 10 d | 104,658 | 104,658 | 104,658 | 104,658 |
| E4 demand +19 % | 51,202 | 49,562 | 49,074 | 49,074 |
| mean component stock (baseline) | 398,881 | 481,117 | 613,194 | 884,109 |

**fraud 2:** effects are small and **not monotonic** (e.g. under quality loss: 13,051 / 33 / 13,051 / 33 lost for 0 / 2 / 5 / 10 days of buffer). Extra POs change which orders can start when, through the full-batch start rule and the FIFO line.

## Findings for the paper
1. **Levers must match disruptions.** A component buffer (lever 2) fully neutralises upstream disruptions (supplier delay, quality loss) in the fragile year at +54 % component stock. It does nothing against a line stoppage or a demand surge, which call for finished-goods or DC stock (levers 1 and 3).
2. **Simple fixed rules are unreliable.** Their effect can be non-monotonic, because of the line's full-batch and FIFO mechanics. This argues for a decision layer that is **state- and disruption-aware** (L2) and whose recommendations are **checked on the twin before use** (L4, certification).
3. **The trade-off is explicit:** lost demand vs inventory held. L2's objective will be stated on these two quantities (plus stock-out days).

## Next (for L2)
- A DC-transfer controller (lever 3) and a finished-goods buffer via conversions (lever 1).
- L2 searches over state-dependent combinations of the three levers, and is evaluated with this same protocol (randomised timing, common random numbers, three years).
