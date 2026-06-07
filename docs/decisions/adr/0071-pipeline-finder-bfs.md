---
title: Pipeline-finder is BFS over TYPE_COMPAT and ignores constraints
status: Accepted
date: 2026-04-21
layer: L3
aliases: [capacity-ADR-012]
---

# ADR-0071: Pipeline-finder is BFS over TYPE_COMPAT; ignores constraints

**Status:** Accepted

**Date:** 2026-04-21

## Context

L4 needs a default "how do I get from DataState A to DataState B" answer. The finder has two failure modes if it tries to do too much: it either returns wrong paths (ignoring constraints silently) or it returns no paths at all (when a constraint is merely advisory).

## Decision

`find_pipeline` does breadth-first search over the auto-discovered TYPE_COMPAT graph and returns the shortest path by capacity count. It does not read `:CONSTRAINT` edges. Constraint filtering is L4's responsibility, as a post-hoc pass over `iter_constraints()`.

## Consequences

**Good:**
- Deterministic default; easy to reason about; fast.
- L4 carries the policy weight, which is correct — L3 has no notion of task urgency, budget, or user preference.

**Cost:**
- L4 must tread carefully with constraints (flagged in open-concerns C2).

## Alternatives considered

1. **Dijkstra with constraint-derived edge weights** — rejected (premature given the slice's scale).
2. **A pluggable scoring function** — rejected (the abstraction is L4's to own).

## §Implementation (2026-05-25, Phase 30)

Shipped 2026-05-25 in `mindsos_capacity/pipeline.py` (NEW module):

- `find_pipeline(capacity_layer, *, session=None, start_datastate, target_datastate, max_depth=8) -> Pipeline` — free function. Raises `PipelineNotFoundError` when BFS exhausts without reaching `target_datastate`; returns `Pipeline(steps=())` when `start_datastate == target_datastate`.
- `Pipeline(start_datastate, target_datastate, steps: Tuple[PipelineStep, ...])` + `PipelineStep(capacity_iri, input_datastates, output_datastates, via_datastate: Optional[str])` — frozen dataclasses.
- `PipelineNotFoundError(CapacityLayerError)` — new raiser in `mindsos_capacity/exceptions.py`.

**BFS shape — datastate-keyed, not capacity-keyed.** The §Decision phrase "auto-discovered TYPE_COMPAT graph" is the structural substrate built by Phase 29's discovery hooks. The BFS implementation walks via `view.consumers_of(datastate_iri)` (Phase 29 view API; returns `List[Node]`), reading `cap.properties.get("outputs")` to push the next frontier. The implementation does NOT use `successors_of` (capacity-keyed walk; also Phase 29) — that primitive expresses the same TYPE_COMPAT graph in a capacity-to-capacity shape that doesn't fit a datastate-keyed BFS.

**Halvim divergences from parent reference:**
1. `find_pipeline` takes `session: SessionArg = None` (halvim Phase 28 R1 PB-14 lock; no legacy `user_id=` kw) where parent has `user_id: Optional[str] = None`.
2. The `build_bfs_capacity_declaration` scaffolding factory (parent ships it raising `NotImplementedError` for "phase-2 wrapping") is OMITTED at Phase 30 per Phase 27 R3 PB-26 precedent (no scaffolding without consumer). Phase 31 ships the registered builtin form directly when it lands.

**Shortest-by-capacity-count invariant** is locked by `tests/phase_30/test_find_pipeline_shortest_by_capacity_count.py` against a branching-capacity fixture (capacity with multiple outputs where capacity-count and edge-count diverge).

**Constraints remain ignored at the finder layer.** Phase 28's `:CONSTRAINT` edges exist but are not read by `find_pipeline`. L4 will do the post-hoc filtering pass.

Status remains Accepted.

## §Implementation (2026-05-25, Phase 31)

Pathfinding-as-registered-builtin formally retires at Phase 31.

The parent reference (`mindsos_capacity/builtins/pathfinding.py`) shipped a `build_bfs_capacity_declaration()` factory that raised `NotImplementedError` with the comment "phase-2 scaffolding — use find_pipeline() directly in the vertical slice." Halvim Phase 30 already omitted this stub per Phase 30 §Implementation halvim divergence #2 ("no scaffolding without consumer"). Phase 31's PHASE_MAP §31 line "install pathfinding" is narrowed inline to "expose for use" (recorded in `halvim_mindsos/notes-phase-31.md` §1) — `find_pipeline` (function-form, shipped Phase 30) is the canonical pipeline-finder surface at L3.

**Why retire rather than ship the registered form**: the registered form requires DataStates for `start_datastate` / `target_datastate` / `pipeline` whose `ShapeDescriptor` is genuinely synthetic — an IRI string is not a domain DataState, it is a *reference*. The parent's NotImplementedError stub admits this circular bootstrap problem. Inventing those DataStates at L3 to register a "pathfinding capacity" that wraps `find_pipeline` would (a) leak synthetic shapes into the DataState vocabulary, (b) have no consumer at Phase 31, and (c) preempt design choices L4's pipeline-planner will want to make about how it models pipelines internally. Phase 32+'s integration scenarios (Integration B) may surface a real consumer; if so, the registered form ships then with a properly-motivated DataState set. If not, the function-form is permanent.

**Halvim Phase 31 ship**:
- No code change at `mindsos_capacity/pipeline.py` (function-form intact).
- `mindsos_capacity/builtins/__init__.py` (NEW; first subpackage under `mindsos_capacity/`) intentionally does NOT re-export `Pipeline` / `PipelineStep` / `find_pipeline`; users continue importing those from `mindsos_capacity` (top-level) per Phase 30 shipping pattern.
- `build_bfs_capacity_declaration` is **never to be reintroduced** at any L3 phase without a concrete L4 consumer.

Status remains Accepted.

## §Amendment (Phase 42 — ADR-0156)

The BFS now walks the bipartite `PRODUCES`/`CONSUMES` edges (`consumers_of` via CONSUMES, `outputs_of` via PRODUCES) instead of the retired TYPE_COMPAT graph. Reachability is identical; the per-frontier hop count doubles (datastate→capacity→datastate). `find_pipeline` signature + `Pipeline` shape unchanged.
