---
title: Resident capacity granularity is fine-grained, matching reactive capacities
status: Accepted
date: 2026-04-21
layer: L3
aliases: [L3-Q5]
---

# ADR-0088: Fine-grained resident capacity granularity

**Status:** Accepted

**Date:** 2026-04-21

## Context

Resident (monitor) capacities watch for conditions and emit signals. The question is whether a resident should be a coarse "weather monitor" covering many conditions or a fine-grained watcher for a single input DataState, matching the granularity of reactive capacities.

## Decision

Residents are fine-grained. A resident watches for the input DataState of the first node of some potential pipeline; if that DataState arrives with the right shape, it signals a pipeline candidate. L4 decides whether to invest compute in running that pipeline. This mirrors reactive-capacity granularity and keeps the metagraph composable.

## Consequences

**Good:**
- Residents compose naturally with reactive capacities at the same scale.
- L4 retains full control over whether to act on a signal.
- The signal-handling path remains synchronous and testable.

**Cost:**
- Many monitors may fire on the same condition; L4 must deduplicate or prioritize signals.

## Alternatives considered

1. **Coarse monitors** — rejected (would create a separate, larger-grain system; hard to reason about composition with reactive capacities).
2. **Monitor for arbitrary predicates** — rejected (would require an event algebra in L3, moving policy into the capacity layer).

## §Implementation (2026-05-25, Phase 31)

Granularity validated at Phase 31 ship via two ship-time facts:

1. `Monitor.subscribes_to: Tuple[str, ...]` (`mindsos_capacity/capacity.py`, since Phase 27) carries the per-Monitor first-input-DataState set. `CapacityLayer.start_resident` reads `declaration.subscribes_to` unconditionally (per ADR-0073 §amendment-1 clause 2) — the declaration is the source of truth for what's watched. No coarsening API exists at L3.
2. `mindsos_capacity/builtins/text.py` (Phase 31 NEW; first builtins family) demonstrates the granularity in practice. The text family ships only reactive capacities — no Monitors — but the precedent for any future text Monitor would be one Monitor per watched first-input DataState (e.g. a `text.detect_eos` Monitor that watches `text.raw`), matching reactive granularity at the same scale.

L4's signal-handling path (when it lands) is responsible for deduplication when multiple Monitors fire on the same `text.raw` input; ADR-0088 §Cost row stands.

Status remains Accepted.
