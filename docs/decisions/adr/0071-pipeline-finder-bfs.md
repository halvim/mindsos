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

## §amendment-2 (feat/composition-lifecycle — 2026-06-21): pluggable finder seam; conjunction/fold finder; DAG result type

**Context.** A live probe (ARC reason-layer, `projects/arc_demo/.../PIPELINE_DECISIONS.md` §4) plus a code read confirm a latent correctness defect: the §Decision BFS fires a capacity from **one** reachable input (`via_datastate`) and never checks the capacity's other declared inputs. For any multi-input capacity it composes unsoundly (fires on one input, drops the rest; a fold is taken as a singleton). The defect is latent — `find_pipeline` has no production caller today — so the first real multi-input-composition consumer hits it. ARC is the motivating-but-non-pinning consumer (it ships provenance-only); it also **documented the resolution semantics** (three input-group cases), which size the fix.

**What changes.**

1. **Finder is pluggable (reverses the §Alternatives "a pluggable scoring function — rejected, the abstraction is L4's to own").** A `Finder` **interface** plus each concrete **algorithm** (BFS, conjunction/fold) live in **L3** — they are computation, and `find_pipeline` already lives at L3. *Which* strategy fires is an **L4** policy call. This splits the concern 0071 originally assigned wholesale to L4: L4 keeps **selection**, L3 owns the **interface + algorithms**. (No L4 "real finder" exists to extend — `plan_construction.py` is a v0 stub — so conjunction is net-new at L3, not an extension of an L4 owner.) BFS becomes one registered strategy; its result construction changes to emit the new DAG type (degenerate-linear DAG).

2. **Conjunction/fold finder.** A hyperpath search whose per-capability resolution is driven **per input-group** — `{all_required (AND) | any_of (optional-union) | fold (aggregate over producers)}` — crossed with **OR over the producers** of each consumed DataState. Explicitly **not** "AND over all inputs" (that mis-composes `any_of`/`fold`). The input-group typing is supplied by the ADR-0159 §amendment (declaration field); this finder *reads* it. Returns a converging DAG. Validated for **structural conformance** against ARC's three documented cases — `all_required` (`touching_delta`/`selector`), `any_of` (`build_correspondence`), `fold` (`reconcile_background`); structural because ARC composes those via an L4 sweep and will not execute the finder's DAGs.

3. **DAG result type replaces the linear `Pipeline`.** `Pipeline`/`PipelineStep` (linear `Tuple[PipelineStep]`) cannot represent a converging DAG. Replace — not additive — is safe: `Pipeline` has **zero production consumers** (verified: no L4/Server/L2/L0 import; the L5-chain `Pipeline` in `chain_artifacts.py` is an unrelated dataclass; the L2 `promoted_pipelines` persistence schema has no live writer). The conjunction finder is the DAG type's first producer.

**Scope held to consumer discipline.** The **promoted-path-lookup** strategy (named as a sibling in the original §Implementation intent) is **not** built — `promoted-pipelines` has no writer (verified). The seam ships with two real strategies (BFS + conjunction). The **graph** form of the input-group (a type-layer typed hyperedge + a hyperedge-aware view walk) is **deferred** to ADR-0156 §am until a graph-walking consumer exists; the finder reads the input-group from the declaration registry meanwhile.

**Supersedes.** The §Alternatives rejection of a pluggable finder, and the §Implementation note "L4's real pipeline-finder will extend this." Status remains Accepted; this records the seam + multi-input soundness fix. Companion: ADR-0159 §amendment (typed input-group field); design record `confirmation_docs/COMPOSITION_LIFECYCLE_DESIGN_LOG.md`.
