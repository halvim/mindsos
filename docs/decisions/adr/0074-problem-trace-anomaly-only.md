---
title: Problem-trace is in-memory, anomaly-only, drained by L4
status: Accepted
date: 2026-04-21
layer: L3
aliases: [capacity-ADR-015]
---

# ADR-0074: Problem-trace is in-memory, anomaly-only, drained by L4

**Status:** Accepted

**Date:** 2026-04-21

## Context

Every invocation could emit a record, but an emit-on-success firehose drowns the signal in noise. And if the sink grows forever in-memory it becomes a leak.

## Decision

`ProblemTraceSink` is in-memory on the `CapacityLayer` instance. It collects records only for actual failures and true anomalies — never successful invocations, never expected control-flow outcomes (e.g. "no adapter found"). L4's lifecycle process drains the sink periodically and writes entries into L2's `problem-trace` role-graph.

## Consequences

**Good:**
- Bounded memory; signal-dense; L4 chooses cadence and granularity of persistence.

**Cost:**
- A crash before L4 drains loses records — acceptable because problem-trace is operational forensics, not transactional state.

## Alternatives considered

1. **Write directly to KL on emit** — rejected (breaks the layer boundary).
2. **Ring-buffer with fixed capacity** — considered; may ship later (flagged in open-concerns B3).

## Enforced as

Invariant I11 in the L3 handoff.

## §Implementation (2026-05-25, Phase 30)

Shipped 2026-05-25 in `mindsos_capacity/runtime.py` (NEW module):

- `ProblemTraceRecord` (dataclass with frozen `entry_id`) — fields `task_id`, `error_kind`, `step_id: Optional[str]`, `mm_ref: Optional[str]` (L5-shape-forward; never populated at Phase 30 per PHASE_MAP §0 L5-out-of-scope), `capacity_iri: Optional[str]`, `payload: Mapping[str, Any]`, `timestamp: float`, `entry_id: str (uuid)`.
- `ProblemTraceSink` — in-memory list-backed; `emit(record)` + `records()` (read-only snapshot) + `drain()` + `__len__`. Per-`CapacityLayer` instance (single sink across all sessions; multi-tenant filtering is L4's concern via the `payload` dict). Bounded-memory variant ("ring-buffer with fixed capacity") in §Alternatives remains deferred per ADR open-concern B3.
- `emit_problem_trace(sink, *, task_id, error_kind, step_id=None, mm_ref=None, capacity_iri=None, payload=None) -> ProblemTraceRecord` — validates non-empty `task_id` and `error_kind` (raises `ProblemTraceError` otherwise); constructs record; calls `sink.emit`.

**L4 drain not implemented at Phase 30** — `ProblemTraceSink.drain()` is exposed as the L4-facing API but no L4 lifecycle process exists yet; the L2 `problem-trace` role-graph write path is L4 territory. Crash-before-drain trade-off in §Consequences is accepted as ADR-locked.

**CLI surface at Phase 30:** `mindsos capacity problem-trace tail [--limit N] [--json]` is peek-only (does not call `drain`). Drain semantics deferred until L4 ships a real lifecycle consumer.

Status remains Accepted.
