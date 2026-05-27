---
title: L3 Capacity — write-capacity per-flow tracker
last_confirmed_phase: 34
---

# L3 Capacity — write-capacity per-flow tracker

Per ADR-0147 §Implementation criterion (b). Tracks the 5+ L3 write
capacities ADR-0145 enumerates, the L4 flow each serves, and the phase
each ships in. Updated each phase that lights up a new capacity.

## Status table

| Category | Capacity IRI | Target role | Scope | Serves L4 flow | Status | Phase |
|---|---|---|---|---|---|---|
| `consolidate` | `capacity:consolidate:mm` | `memories` | Local | Consolidation flow (TBD) | **wired** | 33→34 |
| `trace` | `capacity:trace:problem` | `problem-trace` | Global | Trace flow (TBD) | **wired** | 33→34 |
| `promote` | `capacity:promote:pipeline` | promotion path | per server | Pipeline-finder flow (TBD) | deferred | TBD |
| `promote` | `capacity:promote:pattern` | promotion path | per server | Pipeline-finder flow (TBD) | deferred | TBD |
| `author` | `capacity:author:concept` | `concepts` | Local | Author flow (TBD) | deferred | TBD |
| `author` | `capacity:author:lexicon-entry` | `lexicon` | Local | Author flow (TBD) | deferred | TBD |
| `author` | `capacity:author:alignment` | alignment pair-graph | Local | Author flow (TBD) | deferred | TBD |
| `state` | `capacity:state:capture` | `capacity-state` | Local | State-capture flow (TBD) | deferred | TBD |

## Status legend

- **stub-shipped** — capacity declaration registered + invocable via
  `CapacityLayer.invoke`; body raises `WriteHandleNotWiredError` per
  ADR-0146 §amendment-1 clause 1 (Phase 33). Phase 34 wires the
  working body.
- **deferred** — capacity declaration not yet shipped; waits for the
  L4 flow that will consume it to close design (ADR-0147 per-flow
  build discipline). When the L4 flow closes, the capacity ships in
  the same PR or immediately preceding it.

## How to use this tracker

- **Before shipping a new L3 write capacity**, find the row + verify
  the L4 flow that consumes it has closed design. If not, the
  per-flow discipline says don't build.
- **When lighting up a deferred row**, edit this file in the same PR
  as the capacity ship; flip `Status` from `deferred` to either
  `stub-shipped` (if the handle wiring lags) or `wired` (full body).
  Update the phase column.
- **When wiring a stub-shipped row at Phase 34+**, flip `Status` to
  `wired` and update the phase column. Move the §amendment-1
  carve-out from ADR-0146 to "closed" state if all stub-shipped
  capacities have moved to `wired`.

## See also

- ADR-0145, ADR-0146, ADR-0143, ADR-0147.
- `docs/dev/internals/capacity.md` — internals doc with the
  stub-phase carve-out details.
- Historical: `/Layered Intelligence/docs/dev/coordinated-changes/L3-capacity.md`
  (frozen 2026-04-22) documents the L0 server-seam refactor that ran
  Phase 18+; not the write-capacity scope.
