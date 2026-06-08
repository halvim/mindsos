---
title: L3 dream family — 3 v1 dream capacities + execution-policy contracts
status: Accepted
date: 2026-06-07
accepted_date: 2026-06-07
layer: L3
related: [0157, 0159, 0156, 0044, 0145]
---

# ADR-0162: L3 dream family — 3 v1 dream capacities + execution-policy contracts

**Status:** Accepted

**Date:** 2026-06-07

**Related:** ADR-0157 (family-specific dont-know contracts — `dream` resolves to OPTIONAL_RETURN), ADR-0159 (capacity registration contract v2), ADR-0156 (bipartite topology — dream capacities emit PRODUCES/CONSUMES edges), ADR-0044 (episodic_memories — the corpus dreams replay), ADR-0145 (consolidate family — build-pattern precedent).

## Context

L5 closed at Chat B (2026-05-31) with **dream-as-live** (D-B5): a dream loads an episode, materialises a fresh MM by deep-copy, and **re-executes the pipeline as if live**; ALS signals fire during re-execution per normal mechanics. There is no separate dream-learning track — dream is a corpus-replay mechanism feeding the same ALS pipeline.

Chat B locked the v1 dream catalog (D-B6), per-capacity execution policy (D-B8), entry-point (D-B7), and privacy (D-B9). The L1/L3 reframe chat ratified the `dream.*` family contract (L3-51: OPTIONAL_RETURN dont-know; `concurrent=True`) but deferred concrete capacity authoring to "the first dream consumer triggers chat" (this one). Phase 45 (Rail D) ratifies and ships the L3 contract.

**Consumer split (the load-bearing scope boundary).** The dream capacities have **no v1 L3 consumer**. Their consumer is the L4 dream-cycle loop (Phase 46 substrate) and the L5 dream-pipeline hookup (Phase 48). The actual MM deep-copy, live re-execution, and ALS signal firing are L4/L5. This ADR ships the **L3 contract ahead of that consumer** — the same pattern as `iter_monitors` (ADR-0155 / Phase 41), the bipartite walk (ADR-0156 / Phase 42), and `CapacityContext` (ADR-0159 / Phase 42). L4 orchestration/scheduling is explicitly **out of scope** here.

## Decision

### 1. Three v1 dream capacities (D-B6)

Registered in `mindsos_capacity/builtins/dream.py` under category `dream` (IRIs `capacity:dream:maintenance` / `:exploration` / `:retry`):

| Capacity | `execution_policy` | Intent |
|---|---|---|
| `dream.maintenance` | `replay_recorded` | Regression check — replay recorded chain artifacts under pinned state; no generative re-invocation. |
| `dream.exploration` | `re_execute_capacities` | Drift detection vs current L2/L3; alt-strategy probe. |
| `dream.retry` | `re_execute_capacities` (+ replan-injection) | Re-execute a **failed** episode against current state. |

All three operate at the **TaskRun level** (re-execute the whole task from the selected chain entry). Cross-level variants (sub-Milestone, hint re-extraction) are v2+.

### 2. Execution policy (D-B8)

`DreamExecutionPolicy` is a 2-value enum: `replay_recorded`, `re_execute_capacities`. The `hybrid` (partial) policy named in D-B8 has **no v1 assignee** and is a v2 reservation (§v2-reservations) — it is intentionally not a member (consumer discipline; no dead enum members).

The policy is a declared field on the `DreamCapacity` declaration (a `_CapacityBase` subclass alongside `Monitor`/`Adapter`), persisted onto the registered Core node via `to_properties()`. The L4 dream loop reads it off the node to decide replay-vs-re-execute.

### 3. Entry-point (D-B7)

Each dream capacity declares an `entry_point` field at registration. v1 = `latest_active_taskrun` for all three. v2 adds specific PipelineRun / Milestone / replan-point entries.

### 4. Directive-emitter body contract

Each capacity body is a pure **directive-emitter**: it consumes a `dream.task_ref` DataState (`{source_episode_iri, task_run_iri, failed}`) and returns a `DreamDirective` describing the dream action — or `None` (dont-know, OPTIONAL_RETURN) when it cannot produce one (missing source episode; or `dream.retry` over a non-failed episode). The body performs no re-execution; the L4 loop reads the directive and drives the mechanism.

`DreamDirective` carries `execution_policy`, `entry_point`, `source_episode_iri`, `task_run_iri`, and an optional `replan_injection`.

### 5. Replan-injection mechanism

`dream.retry`, on a **failed** episode, emits a `DreamDirective` whose `replan_injection` is a populated `ReplanInjectionDirective` (`replan_level` = `taskrun` at v1, `source_episode_iri`, `reason`). The L4 dream loop consumes it to perform the actual replan (invalidate the chain at/below `replan_level`, spawn new artifacts — Chat B D-B30). Phase 45 ships only the directive; the replan execution is L4 control flow. On a non-failed episode `dream.retry` returns `None`.

### 6. Provenance + privacy

Every directive carries `source_episode_iri` — the provenance the L4 loop propagates onto signals emitted during re-execution as `dream_source_episode_iri` (Chat B §5.2). **Live signal tagging lands Phase 48**; Phase 45 ships the field on the directive contract. Dream bodies write nothing to Global and touch no cross-user path (D-B9); directives are inert data, and the owning user's session drives execution at L4.

### 7. Dont-know + family placement

`dream` resolves to **OPTIONAL_RETURN** via `family_rules.FAMILY_RULES['dream']` (shipped Phase 42 / L3-57; category fall-through in `family_rule_for`). `concurrent=True` (L3-51). `dream` is **not** a member of `FUNCTIONAL_CATEGORIES` — like `text.*`, it is an opt-in installable builtin family whose category graph is created lazily at first register.

## Rationale

- **Directive-emitter, not thick body.** Re-execution needs the MM deep-copy + execution mechanism that the L4 substrate ships at Phase 46. Encoding the policy *decision* in L3 while leaving the *mechanism* to L4 honours the Chat A R1 boundary (L4 = substrate + control flow; decisions are L3 capabilities) and avoids pre-committing an L4 interface before Phase 46 R0 designs it.
- **Policy on the node, not in a side registry.** The L4 loop introspects registered capacities; co-locating the policy as a node property keeps the graph the single source of truth.
- **Ship 2 policies, reserve `hybrid`.** No v1 capacity uses `hybrid`; a dead enum member is consumer-less forward shape (Phase 40 PB-1 precedent).

## Consequences

- `mindsos_capacity.__all__` gains 1 export (`DreamCapacity`): 117 → 118.
- The `dream.*` family is invokable in isolation (directive emission) but inert end-to-end until the L4 dream loop (Phase 46) + L5 hookup (Phase 48) consume the directives.
- `family_rules.py`, `RESERVED_REALMS` (`REALM_DREAM`), and `FUNCTIONAL_CATEGORIES` need no edits — the family was pre-provisioned at Phases 40/42.

## Alternatives considered

1. **Thick bodies with an injected `DreamExecutionContext` Protocol.** Rejected — pre-commits the L4 dream interface from L3 before Phase 46 designs the substrate; high contract-mismatch risk; the test fake is dead weight once Phase 46 lands.
2. **`NotImplementedError` stubs.** Rejected — fails the "invokable" + "replan-injection executes per spec" pass criteria.
3. **Reuse `context.ReplanVerdict` for replan-injection.** Rejected — conflates a `decision.*` verdict with a dream directive (different family, different consumer).
4. **Add `dream` to `FUNCTIONAL_CATEGORIES`.** Rejected — churns every `create_global()` contained-graph count for a family that installs lazily anyway.

## §v2-reservations

- `hybrid` execution policy (partial replay).
- Cross-level entry-points (specific PipelineRun / Milestone / replan-point).
- Live `dream_source_episode_iri` signal tagging (Phase 48 hookup).

## §Implementation (Phase 45 — Rail D)

Shipped Phase 45 (`phase-45-confirmed`): `DreamCapacity` (`capacity.py`); `CATEGORY_DREAM` (`identifiers.py`, not in `FUNCTIONAL_CATEGORIES`); `builtins/dream.py` (`DreamExecutionPolicy` + `ReplanInjectionDirective` + `DreamDirective` + 2 DataStates + 3 factories + idempotent `install_dream_capacities`); `builtins/__init__.py` re-export; `tests/phase_45/` (5 files); 9-surface version bump 44 → 45; `docs/concepts/dream.md`. The L4 dream-cycle timer, MM deep-copy, live re-execution, and ALS wiring are deferred to Phase 46/47/48.
