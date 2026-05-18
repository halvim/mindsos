---
last_confirmed_phase: 13
---

# Task-patterns role schema

System-wide task decomposition templates. **2 NodeTypes, 2 EdgeTypes**
at `strict=False`. **Global** metagraph.

## NodeTypes

- `TaskPattern` — advisory: `task_type`, `n_observations`, `confidence`.
- `SubgoalTemplate` — advisory: `subgoal_kind`, `ordering_hint`.

## EdgeTypes

- `DECOMPOSES_INTO`
- `PREREQUISITE_OF`

## Where it's used

Phase 16 (Promotion) is the first content consumer.

## Strict-tighten status

`strict=False` (ADR-0149).
