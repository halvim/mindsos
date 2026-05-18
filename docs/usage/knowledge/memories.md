---
last_confirmed_phase: 13
---

# Memories role schema

Per-user task-completion records. **1 NodeType, 2 EdgeTypes** at
`strict=False`. **Local** metagraph per user (ADR-0044).

## NodeType

- `Memory` — advisory: `task_id`, `task_type`, `user_id`,
  `completed_at`, `result`, `retention_policy`, optional
  `ref:problem_trace` (present when the task failed).

`user_id` is baked into `memory_iri` per Phase 12 PB-11 + ADR-0044
§amendment-1 (charset `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`).

## EdgeTypes

- `USED_CAPACITY` — Memory → capacity-IRI (via ref-resolution).
- `PART_OF_PIPELINE` — Memory → Pipeline in Global `promoted-pipelines`
  (cross-metagraph ref via `ref:global_promoted_pipelines` property +
  Phase 09 XRef machinery).

## Where it's used

L4 (Intelligence) writes memories on task completion. Phase 16
promotion machinery aggregates patterns across users' memories into
Global `task-patterns` / `promoted-pipelines` — memories themselves
stay Local.

## Strict-tighten status

`strict=False` (ADR-0149).
