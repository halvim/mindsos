---
last_confirmed_phase: 39
---

# Episodic-memories role schema

Per-user task-completion records. **Renamed from `memories` at Phase 39
per ADR-0044 §amendment-3 + ADR-0150 §amendment-4.** Two NodeTypes
(skeleton only at Phase 39) at `strict=False`. **Local** metagraph per
user (ADR-0044 invariant unchanged).

## NodeTypes (Phase 39 skeleton)

- `Episode` — per-task entry; frozen full mental-model snapshot +
  outcome classification. Immutable externally; lazy
  inline-on-retire is the only permitted internal mutation
  (L2_CHAT_DECISIONS D-L2-3 `append_only_with_lazy_inline`
  discipline; full discipline body lands Phase 43 / ADR-0153).
- `Memory` — clustering composite over Episodes, keyed by
  `task_pattern_iri`. Materializes on first episode of a task-
  pattern; subsequent episodes attach via `memory_contains_episode`
  IntergraphEdge (Phase 43 schema-v2 ship).

`user_id` is baked into both IRI builders (`episode_iri` and
`memory_composite_iri`) per Phase 12 PB-11 + ADR-0044 §amendment-1
(charset `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`; unchanged at §am-3).

## EdgeTypes

**None at Phase 39** (Phase 13 vestigial `USED_CAPACITY` +
`PART_OF_PIPELINE` dropped per Phase 39 design log PB-R1-A; Phase 43
may re-add on `Episode` atomically with the full D-L2-17 ship).

## Advisory property frozensets

**None at Phase 39** (Phase 13 `MEMORY_PROPS` dropped per Phase 39
design log PB-R1-B; properties land Phase 43 alongside
`CONTENT_FIELDS` / `METADATA_FIELDS` / `mutation_discipline` apparatus
per ADR-0153 / ADR-0152).

## Where it's used

L4 (Intelligence) writes `Episode` entries on task completion.
`Memory`-composite materializes per task-pattern on first episode.
Phase 16 promotion machinery aggregates patterns across users'
episodes into Global `task-patterns` / `promoted-pipelines` —
episodic memories themselves stay Local.

The `consolidate:mm` L3 capacity (Phase 33 ship) targets this
role-graph; Phase 48 retargets the write to write `Episode` per the
D-L2-17 semantic shape (Phase 39 keeps interim `type_="Memory"`
writing — interim tech debt for two phases; see
`mindsos_capacity/builtins/consolidate.py` `NOTE(phase-48-retarget)`).

## Strict-tighten status

`strict=False` (ADR-0149).

## Forward references

- L5 mental-model docs ship at Phase 48; the Episode/Memory-composite
  consumption surface (per-task semantics + clustering algorithm)
  lands there.
- Full mutation-discipline body (`append_only_with_lazy_inline`) lands
  at Phase 43 ADR-0153 ship.
- `memory_contains_episode` IntergraphEdge lands at Phase 43.
