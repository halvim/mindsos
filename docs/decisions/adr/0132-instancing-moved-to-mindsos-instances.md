---
title: Instancing vocabulary moved to mindsos_instances package
status: Proposed
date: 2026-04-27
layer: L1
supersedes: [0037]
---

# ADR-0132: Instancing vocabulary moved to `mindsos_instances` package

**Status:** Proposed

**Date:** 2026-04-27

**Supersedes:** ADR-0037 (instancing vocabulary lives in Core — flips to Superseded when this ADR's code lands).

**Related:** ADR-0117 (`CompositionalMetaEdge`, pivot — Reserved). The new compositional primitive lives in Core; this ADR is about the instancing primitives only.

## Context

`ElementInstance` and its seven concrete subclasses (`NodeInstance`, `EdgeInstance`, `HyperEdgeInstance`, `SubGraphInstance`, `GraphInstance`, `MetaEdgeInstance`, `MetaHyperEdgeInstance`), plus `CompositeInstance`, plus `InstanceRepository` and `InstanceLoader`, currently live in `mindsos_core/`. Architecturally these are Layer 5 (Mental Model) vocabulary by intent.

KL doesn't touch instancing. L3 doesn't touch instancing. L4 will use it (mental-model artefacts). L5 *is* the layer where instancing earns its keep.

Cost today:

- KL imports ~400 LOC of Core that it never uses.
- Layer 5 cannot extend the instancing model (e.g., add a new `ElementInstance` subclass for memory-as-instance) without a Core PR.
- Core's tests carry instancing tests that have no relevance to graphs/schemas/persistence.
- The "Core does data primitives only" stated in ADR-0001 is contradicted by 400 LOC of vocabulary that's specifically about templates-and-overrides — a Layer 5 concept.

ADR-0037 acknowledged this and deferred. The deferral explicitly named L5's start as the trigger to revisit. L5 design has not started yet, but the L1 redesign pass (2026-04-27) is the cheapest moment to move — before L4/L5 design imports from `mindsos_core` and locks in the assumption.

## Decision

Create a new sibling package `mindsos_instances/` that imports `mindsos_core`. Move from Core to the new package:

**Vocabulary moves:**

- `ElementInstance` (abstract base)
- `NodeInstance`, `EdgeInstance`, `HyperEdgeInstance`
- `SubGraphInstance`, `GraphInstance`
- `MetaEdgeInstance`, `MetaHyperEdgeInstance`
- `CompositeInstance`
- `ElementRegistry`

**Persistence moves:**

- `InstanceRepository` (the write-side orchestrator)
- `InstanceLoader` (the read-side reconstruction)
- The `_attach_instance` and `_attach_composite` private methods on `Metagraph` move to `mindsos_instances/extensions/metagraph_extension.py` and operate via a documented hook.

**Hook in Core:**

`mindsos_core.reconstruction.MetagraphLoader` gains a `register_attach_handler(label: str, handler: Callable)` extension point so that subclasses or sibling packages can plug in reconstruction for new element kinds without editing Core. `mindsos_instances` registers `:ElementInstance` and `:CompositeInstance` handlers via this hook on package import.

**Re-exports for one release:**

`mindsos_core/__init__.py` keeps the existing re-exports (`from mindsos_instances import ...` re-imported) for one release with a `DeprecationWarning` on import. Consumers update their imports during that release. Re-exports removed in the following release.

**Tests move:**

`tests/instances/` (new directory) for instancing tests. Persistence tests stay where they exercise Core-vs-instances integration — tagged accordingly.

**`mindsos_core/__init__.py` public API after move:**

```python
from mindsos_core import (
    Node, Edge, HyperEdge, Graph, MetaEdge, MetaHyperEdge, Metagraph,
    Schema, NodeType, EdgeType,
    FalkorConfig, FalkorClient, InMemoryClient,
    GraphRepository, MetagraphRepository,
    GraphLoader, MetagraphLoader,
    bootstrap,
    # Removed: NodeInstance, EdgeInstance, ..., CompositeInstance, ElementRegistry,
    #          InstanceRepository, InstanceLoader.
)
```

**`mindsos_instances/__init__.py` public API:**

```python
from mindsos_instances import (
    ElementInstance,
    NodeInstance, EdgeInstance, HyperEdgeInstance,
    SubGraphInstance, GraphInstance,
    MetaEdgeInstance, MetaHyperEdgeInstance,
    CompositeInstance,
    ElementRegistry,
    InstanceRepository, InstanceLoader,
)
```

## Rationale

The L1 redesign pass is the cheapest moment to move instancing out of Core because no L4/L5 code yet imports from Core for instancing. Move costs:

- ~400 LOC of code transfer (mechanical).
- One extension point added to `MetagraphLoader` (registration pattern, ~30 LOC).
- Re-export shim in `mindsos_core/__init__.py` for one release.
- Test directory move (mechanical).

Move benefits:

- Core shrinks to its stated scope (data primitives, schema, identity, persistence, reconstruction).
- KL no longer pays the import cost for unused vocabulary.
- L5 can extend instancing in its own package without touching Core.
- L4 imports from `mindsos_instances` from day one.
- The "Core depends on nothing above it" rule (ADR-0001) is restored.

Doing this after L4/L5 design starts means three rewrites: Core, L4, L5. Doing it now is one rewrite plus one release of deprecated re-exports.

## Consequences

**Good:**

- ADR-0001's stated layer boundary holds. Core does data primitives only.
- KL test runs faster (less code to import; tests unaffected).
- L5 design starts with a stable target package. Extension is local to L5.
- L4 design references `mindsos_instances` cleanly.
- The instancing test surface separates from Core's test surface; CI parallelism improves.

**Tradeoffs:**

- One extra package to install, document, version. Minimal — `mindsos_instances` is a thin sibling.
- Backward-compat re-exports in `mindsos_core/__init__.py` for one release. Adds noise; clean up next release.
- `MetagraphLoader` extension point is a new Core API. Modest ~30 LOC; documented in the developer guide.
- `Metagraph.instantiate_*` factory methods either move out (cleaner separation) or become thin wrappers that import from `mindsos_instances` (preserves `mg.instantiate_node(...)` usage). The factory methods stay as wrappers for one release, with `DeprecationWarning` redirecting users to `mindsos_instances.instantiate_node(mg, ...)`. Removed in next release.

**Coordinated changes:**

- ADR-0037 status flips to **Superseded** when this ADR's code lands.
- `mindsos_core/__init__.py`, `mindsos_core/models/instance.py` removed; replaced by `mindsos_instances/`.
- `mindsos_core/reconstruction/metagraph_loader.py` gains `register_attach_handler` extension point.
- KL imports unchanged (KL doesn't touch instancing). KL tests unchanged.
- Tests moved from `tests/unit/core/test_instances.py` to `tests/unit/instances/test_*.py`.
- `examples/demo.py` updated to `from mindsos_instances import ...` (or kept on Core re-exports for the deprecation window).
- `docs/api/core/` loses instance-related pages; they relocate to `docs/api/instances/`.
- `docs/concepts/instancing.md` updated to reference `mindsos_instances`.

## Alternatives considered

1. **Keep instancing in Core (ADR-0037 status quo).** Rejected — the stated cost (~400 LOC dead weight in KL imports; Layer 5 cannot extend without Core PR) compounds as more layers come online. The L1 redesign pass is the cheapest moment to move.
2. **Defer until L5 design starts (ADR-0037's original plan).** Rejected — by then KL/L3/L4 will have re-imported from Core for instancing in places, and the move costs three rewrites instead of one. Cheapest to do now.
3. **Inline directly into L5 when L5 starts (`mindsos_mental_model/instance.py`).** Rejected — L4 also uses instancing for MM artefacts, so the vocabulary needs a home above L5. A sibling `mindsos_instances` package matches the "vocabulary that multiple upper layers share" pattern.
4. **Split Core into `mindsos_core_data` + `mindsos_core_persistence` with instancing on a third tier.** Rejected — bigger architecture-shaped change than the problem requires; revisits ADR-0005's package-layout decision unnecessarily.

## Implementation references

- New package: `mindsos_instances/` with `__init__.py`, `models/`, `persistence/`, `extensions/`, `tests/`.
- Core changes: removal of `mindsos_core/models/instance.py`; addition of extension point in `mindsos_core/reconstruction/metagraph_loader.py`; updated `mindsos_core/__init__.py` with deprecation re-exports.
- KL: no changes. KL tests: no changes.
- Test directory: `tests/unit/instances/` for new home.
- Documentation: `docs/api/instances/` (new section), `docs/concepts/instancing.md` updated.

ADR moves from Proposed to Accepted when the corresponding code lands and at least one user-facing document (`docs/concepts/instancing.md` or the new `docs/api/instances/`) reflects the decision.
