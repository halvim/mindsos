---
title: MM resolution + instantiation layer
status: Accepted
date: 2026-06-08
accepted_date: 2026-06-08
layer: L4
related: [0165, 0164, 0156, 0132]
---

# ADR-0166: MM resolution + instantiation layer

**Status:** Accepted

**Date:** 2026-06-08

**Related:** ADR-0165 (three-sub-MM composition — the target of instantiation), ADR-0164 (MM RWLock — instantiation writes take the writer lock), ADR-0156 (bipartite topology — capacity-MM instances carry produces/consumes edges), ADR-0132 (instance vocabulary — `mindsos_instances`).

## Context

Chat B D-B13/D-B14 settled how the MM is populated: L4 reads only from the MM, and on cache-miss it resolves the requested IRI against L2/L3, instantiates a single node into the right sub-MM, and reads it back. Instantiation is **lazy** (one node at a time, on demand), **monotone** (the MM only grows during a task), and **pinned** (each instance records the source version, so the task sees a stable snapshot even as KL advances). The R0 probe confirmed `mindsos_instances` ships `IntergraphEdgeInstance` + `IntergraphHyperEdgeInstance` but their `materialise` was deferred to this phase (PB-24).

## Decision

### 1. IRI-namespace dispatch (D-B13)

The resolver is the concrete **`MMHandle`** the Phase 42 `context.py` Protocol named as "the L4 substrate's MM handle (Phase 46)" — it implements `get_or_instantiate` / `find_instances_by_type` / `produces_of` / `consumes_of`. `mindsos_intelligence/mm_resolver.py` resolves an IRI by its namespace prefix to the owning sub-MM and source layer:

- `ontology:` / `lexicon:` / `concept:` / `alignment:` / episodic IRIs → knowledge-MM, source = KL (L2).
- `capacity:` / `datastate:` → capacity-MM, source = CapacityLayer (L3).
- L4 chain-artifact IRIs (HintSet…TaskRun) → intelligence-MM, authored in-place (no external source).

### 2. Lazy single-node instantiation (D-B13)

On cache-miss for an IRI, the resolver fetches the source node at its current resolvable version, constructs the matching `*Instance` (via `mindsos_instances`), inserts it into the target sub-MM under the MM writer lock (ADR-0164), and returns it. Exactly one node per miss — no eager subgraph expansion.

### 3. Monotone-grow (D-B13)

Within a task the MM only grows; instances are never evicted mid-task. (Retention/eviction is a completion-time + dream concern, not a resolution concern.)

### 4. Pin-at-instantiation (D-B14)

Each instance stores its source reference as an `(iri, version_int)` tuple captured at instantiation. The task reads that pinned version for its lifetime regardless of later KL writes. **Lazy inline-on-retire** — materialising a pinned version's content when KL *releases* that version (distinct from deprecate-flagging) — is the D'1 mechanism and lands **Phase 48** (it needs `kl.read_at_version` / `kl.retire_version`, deferred to Phase 48 per ADR-0161). Phase 46 ships the pin (the tuple); not the inline-on-retire.

### 5. `materialise` on the intergraph instance subclasses (PB-24)

`IntergraphEdgeInstance` and `IntergraphHyperEdgeInstance` (shipped Phase 42) gain `materialise` here — their first consumer is capacity-MM instantiation (produces/consumes edges between `CapacityInstance` and `DataStateInstance`), which is exactly this resolver. This closes the Phase 42 PB-24 deferral.

## Rationale

- **Lazy + monotone + pinned** is the minimum that makes a task's view of knowledge stable and reproducible (a prerequisite for dream-as-live re-execution against the *same* pinned state).
- **IRI-namespace dispatch** keeps resolution a pure switch — no type-sniffing — because the three sub-MMs are layer-aligned (ADR-0165).
- **`materialise` here, not at Phase 42**, honours consumer discipline: Phase 42 had no instantiation consumer; Phase 46 does.

## Consequences

- New `mindsos_intelligence/mm_resolver.py`; depends on `mindsos_instances` + KL/CL read APIs.
- `mindsos_instances` `IntergraphEdgeInstance`/`IntergraphHyperEdgeInstance` gain `materialise` (small additive change to a shipped package).
- Phase 48 adds inline-on-retire (D'1) atop the pin shipped here.

## Alternatives considered

1. **Eager subgraph instantiation.** Rejected — violates lazy single-node; instantiates state the task may never read.
2. **Version-float (read KL's latest each access).** Rejected — breaks reproducibility + dream-as-live; D-B14 pins.
3. **Ship inline-on-retire now.** Rejected — needs `kl.read_at_version`/`retire_version` (Phase 48 per ADR-0161); no consumer at 46.

## §v2-reservations

- (none beyond the Phase-48 inline-on-retire, which is scheduled, not reserved.)

## §Implementation (Phase 46 — convergence; pending ship)

PR-A: `mindsos_intelligence/mm_resolver.py` + `materialise` on the two `mindsos_instances` intergraph subclasses. Test `tests/phase_46/test_mm_resolver.py` (lazy single-node + monotone-grow + IRI-namespace dispatch + pin-at-instantiation). Inline-on-retire deferred to Phase 48.
