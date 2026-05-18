---
last_confirmed_phase: 13
---

# Problem-trace role schema

Failure-record archive. **1 NodeType, 0 EdgeTypes** at `strict=False`.
**Global** metagraph.

## NodeType

- `ProblemTraceEntry` — advisory: `capacity_iri`, `task_id`, `step_id`,
  `error_type`, `error_message`, `emitted_at`, `context`.

## Why no edges in v1

Failures are independent records linked back to the failing task via
the `task_id` property, not via in-graph edges. Cross-references to
capacity IRIs + task IDs are property-level, not edge-level.

## Where it's used

Phase 30 (L3 ProblemTraceRecord + sink) writes entries.

## Strict-tighten status

`strict=False` (ADR-0149).
