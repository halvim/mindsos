---
title: IRI form - capacity:<category>:<name> and datastate:<name>
status: Accepted
date: 2026-04-21
layer: L3
aliases: [capacity-ADR-007]
---

# ADR-0066: IRI form - capacity:<category>:<name> and datastate:<name>

**Status:** Accepted

**Date:** 2026-04-21

## Context

Every capacity and DataState needs a stable, human-readable, parseable identifier that composes with KL's IRIs without colliding.

## Decision

Capacities: `capacity:<category>:<name>`. DataStates: `datastate:<name>`. Set at declaration time, never rewritten. Collisions within a metagraph raise `CapacityRegistrationError`; collisions across Global and Local mean "Local specialises Global".

## Consequences

**Good:**
- Log lines, audit entries, and admin tools can print IRIs verbatim.

**Bad:**
- Callers cannot rename a capacity after registration — they must deprecate the old IRI and register a new one.

## Alternatives considered

UUIDs — rejected because human-unreadable. Category-less IRIs — rejected because the category is load-bearing.

## §Implementation (2026-05-24, Phase 27 → Phase 28)

The §Decision is staged across two ship phases:

- **Phase 27 (shipped 2026-05-24)** ships the IRI form + parser (`capacity_iri`, `datastate_iri`, `parse_capacity_iri`, `parse_datastate_iri`) + `CapacityRegistrationError` exception class. The form is enforceable at declaration time on the `_CapacityBase.iri` property.
- **Phase 28 (shipped 2026-05-24)** ships the collision detection at registry write time via `CapacityLayer.register_datastate` and `CapacityLayer.register_capacity`. The "collisions within a metagraph raise `CapacityRegistrationError`" clause is enforced by per-metagraph `_capacity_index` dict checks; the "Local specialises Global" cross-metagraph semantics ship via `_resolve_declaration` Local-first lookup (see [[ADR-0061]] §Implementation). Both behaviors tested at `tests/phase_28/test_capacity_layer_register_*.py` + `test_capacity_layer_local_wins.py`.

Status remains Accepted; the staging was implementation phasing, not a contract change.

## §Implementation (2026-05-25, Phase 30 — InvocationResult + call_capacity export lift)

Closes the export-staging cross-cite recorded at `mindsos_capacity/capacity.py:21-22` ("NOT exported via `mindsos_capacity/__init__.py` until Phase 30 per ADR-0066 §Implementation footer staging"). Phase 30 lifts:

- `InvocationResult` (dataclass; shape per [[ADR-0072]] §amendment-1: `success: bool` + `error: Optional[BaseException]` + `outputs: Mapping[str, Any]` + `duration_ms: float` + `signals: Tuple[Any, ...]` + `trace: Mapping[str, Any]`).
- `call_capacity` (free function; raises `CapacityRegistrationError` for no-implementation-bound or output-shape-mismatch).

Both symbols ship from `mindsos_capacity.capacity` since Phase 27 for layout parity; only the public re-export from the package `__init__.py` is new at Phase 30. The capacity-IRI form and registry-time collision behaviour are unchanged from Phase 27/28.

Status remains Accepted.
