# ADR-0202 — per-task chain graphs, persisted at consolidation (DQ-8)

**Status:** Proposed (built + gate-green as CR#4 slice D8-B/3b, branch `fix/l5-per-task-chain-persist`, PR #52, full gate 4223/0 on live Falkor, 2026-07-17).

Relates to: ADR-0176/0180 (L5 consolidation), ADR-0165/0166 (three-room MM), ADR-0182 (value codec — worked around, not amended), ADR-0201 (capacity-MM vocabulary).

---

## Context

CR#4 (`confirmation_docs/CORE_CR_L5_KNOWLEDGE_AND_CAPACITY_MM_WRITERS.md`) resolved DQ-8 — "does the
MM persist at all?" The findings that forced this decision:

- Nothing persisted the MM. `Episode.mm_root_ref = intelligence_mm.metagraph_id`
  (`consolidation.py`) **dangled**, and the docstring's "persisted by the Phase-44 persister" claim
  was false (Phase 44 = KL Local only).
- The chain writer's scope was the orchestrator constant `"brain"` with `_seq` reset per
  `run_lifecycle`, so two tasks in one resident session minted identical chain IRIs
  (`taskrun:brain:1` …) into one shared chain graph → a node-id collision **and** an `episode_id`
  collision (consolidation is idempotent on `episode_id`, so task 2's Episode deduped task 1's).
- Core persist is pull/batch (`MetagraphRepository`/`GraphRepository.persist`; a full re-walk, no
  add-side dirty tracking); `_persist_client` write-through covers only soft-delete/xref, not
  `Graph.add_node`.

## Decision

Scope the chain **per task** and persist each task's chain graph at consolidation.

1. **Task-unique writer scope.** `Orchestrator._writer_scope(task_id)` yields
   `<task_scope>:<task_id>` when a `task_id` is supplied, else a per-orchestrator counter.
   `ChainArtifactWriter` mints under this scope and `_chain_graph(mm, scope)` finds-or-creates one
   chain graph per task (`chain:<scope>`). This alone removes the node-id and `episode_id`
   collisions.
2. **Per-task persist.** A narrow `MMPersister` (`mindsos_intelligence/mm_persister.py`,
   `persist(metagraph, graph)`) injected into the Orchestrator at `boot.py` on the durable path
   (`None`-no-op for ephemeral/`simplified`) persists **only this task's chain graph**: MERGE the
   metagraph anchor (`build_create_metagraph_anchor`, because `build_create_graph_anchor` links via
   `MATCH (m:Metagraph)`) then `GraphRepository.persist` that one graph. Consolidation stays O(this
   task), not a full-MM re-walk.
3. **`mm_root_ref` → the task's chain graph_id** — a real per-task pointer, not a session-shared
   blob or a dangling metagraph_id. The Episode's `mm_root_ref` is an opaque content field
   (`episodic_memories.py`), not dereferenced today, so repointing it is safe.
4. **Dict-snapshot for the codec.** Chain nodes hold dataclass values (HintSet, TaskRun, …) that the
   ADR-0182 value codec rejects (it takes primitives / dict / list only). The persister writes a
   snapshot of the chain graph with node values reduced via `dataclasses.asdict`, same `graph_id`,
   serialized at persist time so mutated fields (e.g. `TaskRun.status`) capture their final state.
   The live graph keeps its dataclasses for in-session readers. L4-local; no Core codec change.

`knowledge_mm` stays **live-only** — persistence deferred to WSD. (`capacity_mm`
was live-only under this decision too; **Amendment 1 (below) reverses that** —
the architect reopened DQ-8 on 2026-07-21 and `capacity_mm` now persists.)

## Consequences

- Fixes the cross-task collision (a correctness bug, independent of persistence) and makes
  `mm_root_ref` resolve.
- Persist is O(this task's chain), not O(session²) across a long resident session.
- Loaded chain nodes are dicts (WSD can rehydrate from `type_name`); no reader exists today.
- **Intentional asymmetry:** the chain uses per-task graphs (it is persisted and its writer IRIs are
  not task-scoped); `capacity_mm` uses session-shared graphs (live-only, and its IRIs are
  task-scoped via the ADR-0201 composite key). When WSD persists `capacity_mm`, it inherits the same
  growth and will want per-task graphs too.
- `deep_copy` independence (regenerate clone metagraph **and** graph ids) is a separate CR#4 slice;
  `mm_root_ref = graph_id` makes graph-id independence load-bearing there.

## Alternatives considered

- **D8-A — drop `mm_root_ref`, keep the chain live-only.** Rejected: forgoes the durable audit trail
  the 6-level chain exists to be; the shipped field would be deleted rather than made honest.
- **3a — persist the session-shared MM at each consolidation.** Rejected: `GraphRepository.persist`
  is a full re-walk (O(session²)) and `mm_root_ref` stays a shared blob, not a per-task snapshot.
- **Amend the ADR-0182 codec to encode dataclasses.** Rejected for this slice: a Core/L1 change to a
  shipped codec; the L4-local snapshot keeps the blast radius inside this CR.

## Status note

Built and gated as slice D8-B/3b. The remaining CR#4 slices — 0 (DQ-2 vocabulary, ADR-0201), 1
(deep_copy independence), 2 (capacity writer), 3 (knowledge writer + `mm_handle`) — are not built.

---

## Amendment 1 (2026-07-21) — capacity_mm persists (CR reopen DQ-8, Slice B)

CR `confirmation_docs/CORE_CR_CAPACITY_MM_PERSIST_AND_SUBMIND.md` (APPROVED) reopened DQ-8: the
architect pulled `capacity_mm` persistence forward from WSD. This amendment **reverses the
"`capacity_mm` … stay live-only — persistence deferred to WSD" clause** of the Decision above for
`capacity_mm` only. `knowledge_mm` is unchanged (still live-only, Slice 3 / later). The base
decision's chain-graph mechanism is untouched; the "Intentional asymmetry" consequence (chain
per-task/persisted vs capacity session-shared/live-only) is now **superseded** — Slice A already
made `capacity_mm` per-run, and this slice persists it.

What Slice B adds (built this CR):

1. **Per-run capacity graphs persist, edges included.** Slice A keys one grounding graph per
   `(task_id, pipeline_run_ref)` with intra-graph `PRODUCES`/`CONSUMES` edges (ADR-0201 am-2).
   `FalkorMMPersister.persist` — nodes-only before — now copies `graph.edges` too (PB-4).
   `GraphRepository.persist` already writes+reloads edges, so this is a small snapshot change, not
   a new persistence capability.
2. **Task-level index graph + `capacity_root_ref` (PB-2).** Replan yields N per-run graphs under
   one task; a task-level **index graph** (one `CapacityRunRef` node per run graph) is persisted and
   the Episode's `capacity_root_ref` points at it, mirroring `mm_root_ref` → the chain graph
   (ADR-0176 am-1). Reader: index → each run graph. No v1 reader yet (dangles like `mm_root_ref`;
   PB-5 accepted).
3. **Inspectable per-DataState encoding (PB-1).** A DataStateInstance's runtime value is an
   arbitrary domain object the ADR-0182 codec rejects unless already primitive/dict/list. An
   optional **`encode` hint on the `DataState` declaration** (brain-supplied) reduces it to an
   inspectable dict/list (D-C — never an opaque blob); core only *dispatches* on it
   (`mindsos_intelligence/capacity_persister.py`), default = require primitive/dict/list else
   `PersistenceError` at persist. ADR-0182's `_value_json` codec is used as-is (not amended); the
   `encode` hint feeds it a codec-safe value.

Inert until Step 5 (PB-3): no in-CR path threads run graphs into `consolidate_task` (the submind
never consolidates; the solve path's `execution.run` → `execute_pipeline` consolidation is
out-of-CR Step 5). Shipped behind synthetic phase-48 tests. Surfaces:
`mindsos_intelligence/{mm_persister,capacity_persister,consolidation}.py`,
`mindsos_capacity/datastate.py` (the `encode` field), `mindsos_capacity/builtins/consolidate.py`
(docstring). Confirm `confirmation_docs/L5_SLICE_B_CONFIRMED.md`. Slice C (submind wiring, D-B) is
next.
