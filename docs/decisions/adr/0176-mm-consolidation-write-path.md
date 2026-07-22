---
title: MM consolidation write path — L4 freeze+assemble, L3 Episode write, Memory materialize
status: Accepted
date: 2026-06-09
accepted_date: 2026-06-09
layer: L5
related: [0044, 0146, 0159, 0171, 0180]
---

# ADR-0176: MM consolidation write path — L4 freeze+assemble / L3 Episode write / Memory materialize

**Status:** Accepted

**Date:** 2026-06-09

**Related:** ADR-0044 (`episodic_memories` role-graph + Episode/Memory NodeTypes), ADR-0146 (L3 symmetric write contract — the write surface), ADR-0159 (CapacityContext), ADR-0171 (orchestrator — the Phase-5→complete seam this fills), ADR-0180 (the `context.writeable` capability the body writes through).

## Context

Chat B §4.2 fixed retain-by-default: on task completion (success / failure / abort), L4 freezes the live MM and writes it as an **Episode** entry in `L2.episodic_memories`, then releases the live instance. Phase 47 shipped the orchestrator's Phase-5→complete consolidation hook as a **stub seam** (ADR-0171 §4). Phase 48 fills it.

The PHASE_MAP lists both `mindsos_intelligence/consolidation.py` ("MM-freeze + Episode write path") and `consolidate.py` ("writes new Episode + Memory entry shape") — two modules apparently both owning "the write." The L4-vs-L3 strict line (Chat A) resolves the ambiguity. As shipped, `consolidate:mm` writes a single `type_="Episode"` node from `record["value"]`/`record["episode_id"]` (Phase-43 retarget); it does not assemble the 6-field D-B47 shape, walk the chain, or touch Memory.

## Decision

### 1. Division of labour (PB-1) — L4 freezes + assembles; L3 validates + writes

- **L4 `mindsos_intelligence/consolidation.py`** (data-structure mutation + dispatch — L4 per the strict line): acquire the MM-root writer lock; freeze the three-sub-MM root + outcome metadata (end-time, late bindings); walk the TaskRun chain to **assemble the Episode record** — `task_input_ref` (XRef), `mm_root_ref` (XRef → frozen MM root), `task_pattern_iri` (= last-active `MappingResult.selected_task_pattern_iri`), `outcome_classification` (from TaskRun), `consolidated_at`, `crash_marker` (None on the normal path; set by ADR-0179 on crash recovery); then **dispatch `capacity:consolidate:mm`** with that record as `DS_MM_COMPOSITE_INSTANCE.value`; on success, release the live L5 instance.
- **L3 `consolidate:mm`** (the write surface — ADR-0146 unchanged): `validate_node(value, type_="Episode")` then write through `context.writeable(role=ROLE_EPISODIC_MEMORIES, scope="local", version="v1")` (per ADR-0180 — pre-authorized capability replaces `kl.writeable(session, …)`).

`DS_MM_COMPOSITE_INSTANCE` keeps its `{"episode_id": str, "value": Any}` shape; the 6-field Episode dict rides in `value` (already `Any`). No DataState contract widening.

### 2. Episode authoring (D-B47 / D-L2-17)

The Episode is a frozen full MM — three sub-MMs + all chain artifacts + provenance + MSUR ledger + SCMS state + chain history (replanned artifacts marked `aborted_for_replan_at_level_L`), referenced via `mm_root_ref`. Episode content is the 6 fields above; `EPISODE_METADATA_FIELDS` stays empty (append-only externally per ADR-0153 §4). `outcome_classification` ∈ {succeeded, failed, low_confidence, asked_user, dont_know}.

### 3. Memory materialize-on-first-episode + edge (PB-6 / D-B47)

Inside `consolidate:mm`, after the Episode write: if no `Memory` exists for the Episode's `task_pattern_iri`, materialize one (`task_pattern_iri` content; `created_at` metadata); then add the `MEMORY_CONTAINS_EPISODE` EdgeType (Memory → Episode, regular EdgeType within the same `episodic_memories` Schema per the Phase-43 impl-time discovery — **not** an IntergraphEdge). Single capacity, single role-graph handle.

### 4. Idempotency (PB-5 interaction)

Consolidation is idempotent on `episode_id`: a crash *during* consolidation (after the Episode write, before the live-instance release) must not double-write on the ADR-0179 startup re-scan. The startup scan checks Episode-exists before emitting a crash tombstone.

## Rationale

- **Strict line.** Freeze + chain-walk + dispatch are data mutation + control flow (L4); the KL write stays the L3 surface (ADR-0146). `consolidate.py` remains the sole `episodic_memories` writer.
- **No DataState change.** `value: Any` already carries the assembled record; the schema's `validate_node(type_="Episode")` enforces the partition.
- **Memory in the capacity.** It already holds the role-graph write handle; one dispatch, one atomic-ish write sequence.

## Consequences

- `consolidation.py` is new L4; `consolidate:mm` body finalizes to the 6-field shape + Memory materialize (third touch on `consolidate.py` per the PB-Z reading-list — Phase 39 rename / Phase 43 retarget / Phase 48 finalize).
- External `consolidate:mm` body consumers update (the input is now the assembled Episode record).
- `MEMORY_CONTAINS_EPISODE` wiring exercised first at Phase 48.

## Alternatives considered

1. **L4 performs the KL write directly; retire `consolidate:mm`.** Rejected — violates ADR-0146 (L3 is the write surface); orphans a shipped capacity.
2. **`consolidate:mm` does freeze + assemble + write.** Rejected — freeze is a live-MM mutation under the MM writer lock, an L4 substrate concern the capacity has no lock handle for.
3. **Separate `consolidate:memory` capacity for Memory.** Rejected — two dispatches + two handles + cross-write ordering for no v1 benefit.

## Amendment 1 (2026-07-21) — Episode gains `capacity_root_ref` (CR reopen DQ-8, Slice B)

CR `confirmation_docs/CORE_CR_CAPACITY_MM_PERSIST_AND_SUBMIND.md` (APPROVED) adds a **7th** content
field to the assembled Episode record: `capacity_root_ref`, the pointer to this task's persisted
capacity-MM index graph (ADR-0202 am-1), mirroring `mm_root_ref` → the chain graph. It rides
**inside** the codec-encoded `value` dict alongside the existing six fields — `value` is already
`Any` (ADR-0182 `_value_json`), so there is **no `DS_MM_COMPOSITE_INSTANCE` shape change and no L2
`episodic_memories` schema change** (`EPISODE_METADATA_FIELDS` stays empty). L4
`consolidation.py` assembles it (`None` when no capacity graphs are supplied — the case today,
inert until out-of-CR Step 5); L3 `consolidate:mm` writes the dict unchanged. The §2 "6 fields"
count reads as **7** from this amendment on.

## §Implementation (Phase 48; pending ship)

`mindsos_intelligence/consolidation.py` (NEW); `mindsos_capacity/builtins/consolidate.py` (finalize body + Memory materialize); `mindsos_knowledge/schemas/episodic_memories.py` (Episode/Memory write helpers — S10); orchestrator Phase-5→complete seam wired (commit-group 3). Tests: `tests/phase_48/test_consolidation_write_path.py`, `test_memory_composite_materialization.py`, `test_memory_contains_episode_edge.py`, `test_consolidate_capacity_v2.py`.
