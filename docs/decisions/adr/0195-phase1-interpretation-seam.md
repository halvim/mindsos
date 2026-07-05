---
title: Phase-1 interpretation seam — pluggable Phase1Profile
status: Accepted
date: 2026-07-02
layer: L4
amends: []
aliases: [Feature-A, phase1-seam]
---

# ADR-0195: Phase-1 interpretation seam

**Status:** Accepted (shipped on `feat/phase1-seam-and-needs-input`, Linux
gate green; pairs with [[ADR-0196]])

**Date:** 2026-07-02 (core-design chat; implemented 2026-07-02; first consumer
= arc-solver / mOS-AS)

## Context

L4 LifecyclePhase 1 (`mindsos_intelligence/phase_1.py`, ADR-0172) runs a
5-step interpretation flow (`receive → process → extract_hints → derive_goal
→ map_to_task_pattern`) by dispatching **fixed** capacity IRIs:
`capacity:hint:global` and `capacity:decision:map_to_task_pattern`. The only
bodies registered at those IRIs are the **v0 placeholders**
(`mindsos_capacity/builtins/phase1_v0.py`, `placeholder=True`): `hint.global
→ {}`, `map_to_task_pattern → {"task_pattern_iri":"task-pattern:v0:trivial",
"mapping_confidence":1.0}` regardless of input. There is no way for a consumer
to supply a real hint grammar or a real mapping without editing core.

Grounding (verified this chat):

- Phase 1 dispatches module-constant IRIs; `phase1_v0.install_phase1_v0`
  registers the placeholders into the **Global** metagraph.
- The mapping target registry ships: L2 `ROLE_TASK_PATTERNS` +
  `task_pattern_iri(version, pattern_id)` (`mindsos_knowledge/identifiers.py`).
- Goal-directed composition ships: bipartite `find_pipeline` over
  `PRODUCES`/`CONSUMES` (ADR-0156). It is **sound for linear single-input
  chains** (the known-unsound case is multi-input fold caps — out of scope
  here).
- `L4Dispatcher` (`mindsos_intelligence/dispatch.py`) already builds the typed
  `CapacityContext` (ADR-0159) per dispatch; it is the natural place to carry
  a per-consumer interpretation binding.
- **Scope-mix guard:** registering Global DataStates together with Local
  capacities in one metagraph raises (this already bit `arc_instance`). Any
  seam that lets a consumer supply Local bodies must NOT co-register mixed
  scopes.

Per CLAUDE.md RULES §8, the Phase-1 seam is **core-owned** generic mechanism;
WSD/FOL/arc-solver are consumers. The "v0 → real phase1 flip" is MindsOS
release code, not WSD-owned.

**First consumer (arc-solver, confirmed 2026-07-02):** adopts the seam for
**interpretation only** (`hint → map → [resolve?] → id8`), feeds `id8` into its
own bespoke solve driver, and does **not** run `run_lifecycle` or any core
planning/execution catalog.

## Decision

Introduce a **`Phase1Profile`** — a per-consumer selection of interpretation
bodies — bound at **`L4Dispatcher` construction**. **Four optional step slots**:
`process`, `hint`, `derive_goal`, `map`. Each slot holds a capacity IRI; an
unset slot falls back to the shipped v0 placeholder. Phase 1 dispatches
`profile.slot or <v0 default IRI>`.

Reference `resolve` is **not a fixed slot** — it is *composed* by the shipped
bipartite `find_pipeline` (ADR-0156) from the reference's DataState type to the
consumer-declared `resolve_target_datastate` (the fifth `Phase1Profile` field,
a DataState IRI, not a capacity IRI), then run via the shipped
`pipeline_execution` executor. A 1-capacity resolve is the degenerate 1-step
pipeline; an already-canonical reference composes a 0-step pipeline
(pass-through). This is the same "everything is a `find_pipeline` over a set,
even at cardinality 1" model the `map` step uses.

1. **Dispatcher-level binding, no metagraph scope-mix (hard constraint).** The
   profile is a **dispatch-time selection** of *which IRI to invoke*, held on
   the dispatcher — NOT a registration that co-locates Global DataStates with
   Local capacities in one metagraph. A consumer registers its real bodies into
   its **own scope** (Local for arc), using DataState IRIs of that same scope;
   the seam never mixes scopes in a single metagraph. `run_lifecycle`'s
   signature is unchanged.

2. **Standalone interpret surface.** Factor the interpretation flow into a
   callable `interpret(dispatcher, task_input) → InterpretationResult |
   NeedsInput` that is **decoupled from `run_lifecycle`**. `Orchestrator`
   Phase 1 becomes one caller; an interpretation-only consumer (arc) is
   another. `InterpretationResult` carries `{hints, task_pattern_iri,
   mapping_confidence, resolved_reference?}`.

3. **`resolve` runs inside interpretation, composed via `find_pipeline`.**
   When the hint body reports an indirect `reference_kind` and the profile
   declares a `resolve_target_datastate`, `interpret` composes the resolve
   chain with `find_pipeline(start=reference_kind, target=resolve_target)` and
   runs it via `pipeline_execution` — *within interpret*, not via
   `execution.run`. Its clarification path (`NeedsInput`) surfaces from the
   `interpret` return. This uses the shipped composition + execution mechanisms
   (no bespoke direct-dispatch special case) while keeping the
   interpretation-only consumer decoupled from the orchestrator lifecycle.
   The `execution.run` halt+bubble (orchestrator mid-execution) remains the
   general/full-lifecycle path, deferred (L4-25).

4. **Hints = opaque dict + per-consumer schema; `reference_kind` is
   type-driving.** Core does not define a typed `HintSet`. The hint body
   returns a dict on the consumer's own schema, optionally carrying
   `reference_kind` (a DataState IRI naming the reference's **type** = the
   `find_pipeline` start) and `reference` (the raw value). Composition is driven
   by DataState type, not consumer-specific routing.

5. **`map` returns a real target.** The map body returns a
   `task_pattern_iri` that resolves in `ROLE_TASK_PATTERNS` (**Local→Global**,
   per the dual-scope task-patterns of ADR-0150 §am-8) plus a
   `mapping_confidence`. Core validates the IRI resolves and exposes a
   never-trip confidence threshold hook; **both checks are gated on a real
   `map` slot** so the all-v0 path (whose trivial pattern is not KL-registered)
   is unaffected. **No generic hints→pattern matcher ships at v1** — a real
   consumer supplies both `hint` and `map`; `process`/`derive_goal` default to
   v0. Multi-pattern disambiguation is deferred (L4-26).

**Scope:** consumer bodies + DataStates + task-patterns install into the
consumer's Local scope (task-patterns is dual-scope per ADR-0150 §am-8; a Local
capacity may reference Global DataStates via the ADR-0185 A2′ mirror, so the
resolve chain composes over the consumer's Local view). The v0 placeholders +
the generic fallback stay Global.

## Consequences

- **Enables the arc-solver worked example** without arc running the L4
  lifecycle: `interpret("solve task 8")` → hints `{reference_kind:<index DS>,
  reference:8}` → `map` (arc-solve pattern) → `find_pipeline(index→canonical)`
  composes `[resolve]` → run → `InterpretationResult{resolved_reference:id8}`
  (or `NeedsInput` on cold start, per [[ADR-0196]]). Note the composed chain is
  `[resolve]`, **not** `[resolve → solve]` — solve is arc's own downstream
  bespoke driver, outside interpretation.
- **`execution.run` step-result propagation is NOT on this ADR's critical
  path.** Because arc surfaces `NeedsInput` from `interpret`, the halt+bubble
  handling in `execution.run` (shared with `dont_know`) is the general/full-
  lifecycle path, deferred (L4-25).
- **Interpretation-only consumers opt out of MM / consolidation / Episode** —
  no core L5 audit trail for such runs. Documented, consumer's choice.
- **Build scope (S1):** a precursor S0.5 makes `task-patterns` dual-scope
  (ADR-0150 §am-8, so a consumer's map target resolves Local→Global); then
  factor a writer-free `interpret`; add `Phase1Profile` (4 slots +
  `resolve_target_datastate`); carry it on `L4Dispatcher`; compose `resolve`
  via `find_pipeline` + `pipeline_execution`; gate the map-resolution + confidence
  checks on a real `map` slot (v0 unaffected); version bump. The `NeedsInput`
  branch of `interpret` lands with [[ADR-0196]] (S2). Independently shippable
  from [[ADR-0196]] otherwise.

## Alternatives considered

- **Per-submission `application` arg on `run_lifecycle`** — rejected: pollutes
  the generic submit path; no consumer needs multi-application-per-dispatcher.
- **Global registry keyed by `application_id`** — rejected: hidden mutable
  global; harder to test-isolate.
- **Overwrite the fixed v0 IRIs (`capacity:hint:global`)** — rejected: a shared
  Global IRI collides the moment a second consumer exists; the profile
  indirection avoids it.
- **Typed core `HintSet` dataclass** — rejected: consumer hint shapes differ
  (arc vs WSD vs FOL); forces a base/subclass in core prematurely.
- **Co-register consumer bodies + phase1 DataStates in one metagraph** —
  rejected: trips the scope-mix guard (constraint above). Binding is a
  dispatch-time selection instead.

## Supersession / amendment trail
- Builds on **ADR-0172** (Phase-1 5-step control flow), **ADR-0156** (bipartite
  topology / `find_pipeline`), **ADR-0159** (capacity registration v2 /
  `CapacityContext`), **ADR-0171** (orchestrator). Amends none.
- **Pairs with [[ADR-0196]]** (the `needs_input` verdict `interpret` returns).
  The two are independently shippable.
- **Amended by [[ADR-0197]]** (modality-aware ingress): adds a runtime
  `{modality→Phase1Profile}` table over the construction-bound profile and
  de-hardcodes the interpretation DataState spine to environment-threaded.
- Future work: `L4_FUTURE_WORK.md` §6 / §6.2; deferred L4-25 (execution
  propagation + in-memory continuation), L4-26 (generic matcher).
