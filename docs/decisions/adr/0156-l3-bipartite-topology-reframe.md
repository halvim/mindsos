---
title: L3 capacity-to-DataState topology reframed as explicit bipartite
status: Accepted
date: 2026-06-01
layer: L3
supersedes: [ADR-0069, ADR-0086]
amends: [ADR-0070, ADR-0071, ADR-0132]
aliases: [reframe-D38, L3-1, phase-27-reframe]
---

# ADR-0156: L3 capacity-to-DataState topology reframed as explicit bipartite

**Status:** Accepted

**Date:** 2026-06-01

## Context

Phase 27 (2026-05-12) shipped capacities as nodes in category graphs with `inputs: list[IRI]` and `outputs: list[IRI]` as **node properties**. Phase 29 shipped `TYPE_COMPAT` auto-discovery — implicit capacity→capacity edges derived from matching DataState types between one's output and another's input. ADR-0086 added admin `add_type_compat` API for manual TYPE_COMPAT authoring.

Chat B (2026-05-31) D-B40 locked the **instance layer** (capacity-MM) as bipartite: `CapacityInstance` nodes + `DataStateInstance` nodes + explicit binary `produces` (CI→DSI) + `consumes` (DSI→CI) edges. D-B46 locked these edge type names in the v1 edge catalog.

The type layer (L3 capacity graph) and instance layer (capacity-MM) are asymmetric under the shipped Phase 27 model — capacity-MM has `produces`/`consumes` edges with no type-graph antecedent; the type graph has only TYPE_COMPAT capacity→capacity transitive edges. Instantiation requires inferring produces/consumes from property lists. Asymmetry creates cognitive load + makes pipeline-finder reasoning unnecessarily indirect.

WSD `coordinated_change_L3` §A.1 proposes "capacities-as-hyperedges with DataStates as nodes." Chat A R6 (D38) ratified directional preference for the reframe. This ADR picks the specific shape.

## Decision

L3 type-graph adopts bipartite topology mirroring Chat B D-B40 instance layer:

- Capacities remain **nodes** in category graphs (ADR-0066 capacity-as-node primitive preserved).
- DataStates remain **nodes** in the DataState graph.
- New: explicit `IntergraphEdge` of type `produces` (capacity node → DataState node) and `consumes` (DataState node → capacity node) emitted at `register_capacity` time, walking `declaration.inputs` and `declaration.outputs`. Same metagraph, different graphs — `IntergraphEdge` (Phase 05b) is the correct primitive.
- TYPE_COMPAT retired. `discover_for_capacity`, `discover_for_datastate`, `rediscover_all` retire from `discovery.py`. The whole Phase 29 module deletes (~330 LOC).
- `views.successors_of` rewrites: was one-hop TYPE_COMPAT walk; becomes two-hop bipartite walk (capacity → produces → DataStates → consumes → successor capacities). Semantic-preserving.
- `pipeline.find_pipeline` BFS algorithm hops one extra step per frontier; reachability preserved.
- `EDGE_TYPE_COMPAT` constant retires from `identifiers.py`; two new constants `EDGE_PRODUCES = "produces"` + `EDGE_CONSUMES = "consumes"` ship. Names match Chat B D-B46 verbatim.
- `_CapacityBase.to_properties()` stops serializing `inputs`/`outputs` lists to node properties. The declaration fields stay for authoring; persistence moves to edges. Co-ship `views.inputs_of(iri)` + `views.outputs_of(iri)` helpers using two-source strategy (declaration registry primary; graph walk fallback for orphan capacity nodes).
- `_CapacityBase.inputs`/`outputs` properties stripped from node (single source of truth = edges).
- `CapacityLayer.rediscover()` method retires.
- `DiscoveryFailedError` retires from `exceptions.py`.
- ADR-0152 schema entries (the `EDGE_TYPE_COMPAT` EdgeType registration in `schemas.py`) drop.
- `register_capacity` gains `if_exists: Literal["raise", "upsert"] = "raise"` kwarg. Default preserves Phase 28 shipped behavior; `"upsert"` is the migrator + partial-state-recovery path with idempotent edge emission (checks edge existence before adding).
- Pre-validation before emission: `declaration.validate_for_registration(ds_graph.nodes.keys())` already validates DataState refs exist; ADR-0156 strengthens to validate all I/O IRI well-formedness before emission begins.
- DataStates are **append-only** at v1 (written invariant). Deletion path = future ADR.
- L3-19 (`include_deprecated` parameter discipline) folds into ADR-0156 scope.

Instance layer (capacity-MM) per Chat B D-B40 + symmetry pressure:

- `mindsos_instances` Phase 06 amendment ships **two new subclasses** of `ElementInstance`: `IntergraphEdgeInstance` (driven by D38 = A symmetry) and `IntergraphHyperEdgeInstance` (driven by Chat B D-B41 Pipeline composition; Chat B cascade gap absorbed).

## Consequences

**Good:**

- Instance-layer / type-layer symmetry: same nouns, same edge names at both layers.
- `mindsos_instances` capacity-MM works under Chat B D-B40 without primitive mismatches.
- WSD installation authoring shape unchanged (`Capacity(name=..., inputs=[...], outputs=[...])` still public API; edge emission is invisible to authors).
- 50+ queued L3 capacities (L3-33 → L3-49 + L3-50 + L3-51) author against the unchanged constructor; bipartite emission is implementation detail.
- Phase 27–33 capacity migration is mechanical: one-pass migrator under ADR-0134 schema migration walks each capacity node, reads existing `inputs`/`outputs` lists, emits `produces`/`consumes` edges, optionally strips properties. Idempotent.
- Practical migration scope is Global metagraph only (per Phase 38 carry-forward #3: `FalkorDBLocalPersister` unshipped → Locals are in-memory and re-registered each session).

**Cost:**

- ADR-0069 + ADR-0086 retire entirely. ADR-0070 + ADR-0071 amend (algorithm changes, edges observed differ; reachability identical).
- Phase 29 test suite (~7 files) retires whole; Phase 28 schema test + Phase 30 `find_pipeline` tests + Phase 33 `test_outputs_terminator_discovery.py` need updates. Estimated test churn: 10-15 files.
- Public API hard-break: `SuccessorHop` dataclass + `EDGE_TYPE_COMPAT` constant retire from `__init__.py` `__all__`. Coordinated audit with ADR-0155's hard-break symbols (consolidated R0 audit pass).
- Phase 38 carry-forward #4 (`add_type_compat` admin API + bulk rediscover verb) retires entirely.
- Phase 38 carry-forward #10 (mkdocs `--strict` lift) grows by 8-12 docs surfaces (cookbook + concepts pages reference TYPE_COMPAT terminology). Bundled into ADR-0156 ship per PB-D38-6.
- Edge emission is per-edge sequential Falkor statements; mid-loop infra failure leaves partial state. Recovery via idempotent re-register with `if_exists="upsert"`.

## Alternatives considered

1. **B — Hyperedge at L3 type-graph** (capacity-as-IntergraphHyperEdge spanning DataState nodes) — rejected: creates type/instance asymmetry (hyperedge → bipartite expansion at instantiation); the runtime path `cl.invoke(iri, inputs)` never traverses type-graph hyperedge structure, so the authoring-time clarity is unpaid rent; `register_capacity` return type changes from Node to IntergraphHyperEdge (public API break). Variadic capacities (`planning.aggregate_outputs` with N children → 1 parent) are naturally encoded in bipartite via N consumes edges; hyperedge primitive is overkill.

2. **C — Status quo (no reframe)** — rejected: instance/type asymmetry persists; the implicit-property encoding doesn't catch malformed I/O at register-time; punts L3-Q2.

## Supersession trail

- Supersedes **ADR-0069** ("TYPE_COMPAT auto-discovery, Phase 29 ship").
- Supersedes **ADR-0086** ("Admin manual TYPE_COMPAT API + bulk rediscover").
- Amends **ADR-0070** ("Successor walk semantics") — algorithm changes from one-hop TYPE_COMPAT to two-hop bipartite; same reachability.
- Amends **ADR-0071** ("Pipeline finder BFS, Phase 30") — frontier expansion doubles hop count per step; performance acceptable at v1 scale.
- Amends **ADR-0132** ("Instancing moved to mindsos_instances") — Phase 06 catalog expands from 8 instance subclasses to 10 with new `IntergraphEdgeInstance` + `IntergraphHyperEdgeInstance`.

## Sequencing

Ship phase **X3** — atomic bundle with ADR-0159 (capacity registration contract v2) + Phase 27 audit deliverable (`confirmation_docs/PHASE_27_DONT_KNOW_AUDIT.md` per ADR-0157). Two ADRs on `_CapacityBase` → single phase ship for atomic schema change.

## R0 probe set (required before ship R1)

1. Test file count + line count of TYPE_COMPAT references (sizing).
2. Documentation surface count touched by terminology change (sizing).
3. `add_type_compat` external use sites — verify zero consumers (correctness).
4. Phase 30 `find_pipeline` test assertions on TYPE_COMPAT edge presence (sizing).
5. IntergraphEdge persistence pattern Phase 05b lock (Pattern A direct vs Pattern B anchor) — load-bearing for produces/consumes Cypher representation.
6. IntergraphEdgeInstance + IntergraphHyperEdgeInstance status confirmation re-probe.
7. `_has_edge` helper availability for `if_exists="upsert"` idempotency check.
8. `SuccessorHop` usage in problem-trace serialization.
9. ADR-0086 `add_type_compat` consumer count.

## Rationale

Per-decision rationale, 3-round saturation history (2 reversals R1, 1 reversal R2, 0 reversals R3), and the alternative-fork (Hyperedge vs Bipartite) analysis at `docs/_workbench/L1_L3_REFRAME_DECISIONS.md` §D38.

## §Implementation (Phase 42 — 2026-06-05)

Shipped (ADR-0156). `register_capacity` emits `PRODUCES` (capacity→DataState) + `CONSUMES` (DataState→capacity) IntergraphEdges from the declaration outputs/inputs (uppercase rel-type values per the ADR-0021 regex; the lowercase forms in the body above are the Chat B D-B46 instance-layer label convention). `discovery.py` deleted whole; TYPE_COMPAT / SuccessorHop / DiscoveryFailedError / rediscover retired; `views.successors_of` + `pipeline.find_pipeline` rewritten over the bipartite walk; `inputs_of`/`outputs_of` co-shipped; `if_exists="upsert"` idempotency. `mindsos_instances` catalog 8→10. Migration: a one-pass migrator would be dead code (CapacityLayer is in-memory-first, no persisted Global capacity state) → shipped a detector `tools/check_phase_42_bipartite_state.py` instead (PB-7).

## §amendment-1 (feat/upsert-rebind — 2026-06-21): upsert re-binds the in-memory declaration

**What changed.** `if_exists="upsert"` now re-assigns `self._declarations[declaration.iri] = declaration` in the reuse branch, in addition to its original idempotent edge re-emission. Before this amendment the upsert branch reused the existing node and back-filled missing `PRODUCES`/`CONSUMES` edges but never re-bound the declaration, so re-registering an IRI with a new `implementation` was a behavioural no-op — the previously-bound implementation stayed the one `invoke` resolved through `_resolve_declaration → _declarations`.

**Why the §Decision text scoped it to edges.** The original §Decision (line 43) framed upsert as "the migrator + partial-state-recovery path with idempotent edge emission." That migrator never shipped — the §Implementation above records it as dead code, replaced by a detector. So the only real consumers of `upsert` are same-process re-registration (e.g. re-teaching a learned composite with updated steps) and the F9 boot re-activation walk, both of which require the new declaration (and its `implementation`) to win. Edge-only idempotency had no surviving consumer that depended on the declaration being left untouched.

**Semantics: unconditional last-registration-wins.** The rebind is unconditional, mirroring the fresh-registration branch and the locked Local-wins `_declarations` semantic (`tests/phase_28/test_capacity_layer_local_wins.py::test_local_registration_overwrites_global_in_declarations`). A conditional "only rebind when `implementation is not None`" guard was **considered and rejected**: no caller upserts an implementation-less declaration to back-fill edges (grep: the sole upsert callers are one phase-42 test and out-of-tree demo code, both carrying a real implementation), so the guard would protect a non-existent consumer while diverging from the else-branch's unconditional assignment.

**Out of contract.** Upsert reuses the existing graph node; it does **not** rewrite the persisted node `properties` from the new declaration's `to_properties()`. A metadata-only re-registration (changed `cost_prior`, `description`, …) would therefore leave the persisted node and the in-memory declaration divergent. No caller does this; metadata-mutating upsert is out of contract and deferred to a future ADR if a consumer appears.

**Invoke resolution is unchanged.** `_resolve_declaration` still gates on `_capacity_index` presence and reads the implementation from `_declarations`. This amendment only corrects what upsert writes to `_declarations`; repopulating `_capacity_index` from a *reloaded* metagraph (the durable-Local boot path) is out of scope here and owned by the F9 re-activation work, which supersedes this ADR's "Locals are in-memory and re-registered each session" premise (Cost §, line 61).

**Surface.** No public-API or `__all__` change; behavioural broadening of an existing kwarg. Guarded by `tests/phase_42/test_upsert_rebinds_declaration.py`.
