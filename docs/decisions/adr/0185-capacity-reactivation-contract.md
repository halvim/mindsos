---
title: Capacity re-activation contract (descriptor-of-record + factory registry)
status: Accepted
date: 2026-06-21
layer: L3
amends: [ADR-0156]
aliases: [F9-A]
---

# ADR-0185: Capacity re-activation contract

**Status:** Accepted

**Date:** 2026-06-21 (branch `feat/f9-durable-local`)

## Context

Capacities are per-process in-memory: `CapacityLayer._declarations` (IRI →
declaration, holding the bound `implementation`) and `_capacity_index`
(per-metagraph IRI → `(Node, Graph)`) are rebuilt by `register_capacity`
each process. ADR-0156's Cost § assumed "Locals are in-memory and
re-registered each session." F9 (durable per-device Local persistence,
ADR-0186) breaks that assumption: a taught (learned) capability must be
runnable via `invoke` after a process restart **without re-registering
from code**, and Python callables cannot be serialized.

A taught capability's durable footprint is already a Local
`learned-parameters` descriptor node whose value dict holds
`{capability, steps, requires_affordances, cache_key, source}`
(`robot_demo/backend/transfer.py`). The L3 capacity node's
`to_properties()` is deliberately lossy — it drops `inputs`/`outputs`
(those are `PRODUCES`/`CONSUMES` edges per ADR-0156) and the callable.

## Decision

**The durable artifact is the L2 `learned-parameters` descriptor; the L3
capacity node + its `implementation` are per-process and re-minted at
boot.** Reconstruction does NOT go through `_CapacityBase.from_properties()`
(lossy) — it walks the descriptor and rebuilds via a factory.

- **Factory registry** (`mindsos_capacity/reactivation.py`, pure-L3):
  `register_reactivation_factory(key, fn)` + `build_declaration(key,
  descriptor) -> _CapacityBase`. Factory signature `(descriptor: dict)
  -> _CapacityBase` returns a fully-built declaration with
  `implementation` bound. The factory owns ALL reconstruction (name,
  category, inputs, outputs, node_kind, impl), so this layer stays
  generic and never edge-walks or touches `to_properties`.
- **`reactivation_key`** — a field on the descriptor naming the factory.
  Absence, or the reserved value `"installer"`, marks the descriptor
  **not** Local-re-activatable (it re-activates by re-running its
  installer, ADR-0183 — the negative path; the two re-activation paths
  are kept separate per the design log §6).
- **Descriptor self-describes (PB-F).** The descriptor carries the full
  declaration spec (`category`, `inputs`, `outputs`, `node_kind`) so one
  generic factory suffices. DataState *definitions* are **not** carried —
  they resolve cross-scope per §A2′ below. The consumer (e.g. robot
  DM-8) writes the richer descriptor at teach time.
- **`reactivate_from_descriptors(cl, descriptors, *, session)`** —
  builds each re-activatable declaration via its factory and registers
  it on the Local (`session`-scoped) with `if_exists="upsert"`, so a
  re-run is idempotent and the ADR-0156 §amendment-1 rebind binds the
  freshly-minted `implementation`.
- **Callable non-serializability honored.** No `implementation` is ever
  pickled. Factories are registered fresh each process, closing over any
  live runtime handles (e.g. a demo's `run_step`) — exactly what cannot
  be serialized.
- **No `reindex_capacities` / no CL persistence (Model A).** The CL Local
  (`local_capacity:<user_id>`) is NOT persisted; on boot it is freshly
  minted (empty `_capacity_index`), so re-activation takes the
  fresh-registration branch. `if_exists="upsert"` is used defensively for
  idempotent re-runs. The reload→reindex→upsert path (Model B) is
  rejected — it would persist a node that must be rebuilt anyway.

### §A2′ — Local registration mirrors referenced Global DataStates

A taught composite chains Global builtin DataStates (e.g. the robot
composite is `inputs=(DS_POSE_TARGET,), outputs=(DS_MOTION_DONE,)`,
Global-registered). Both `validate_for_registration` and the ADR-0156
`PRODUCES`/`CONSUMES` `IntergraphEdge` emission are **Local-scoped** (the
edge's DataState endpoint must exist in the Local DataState graph;
`add_intergraph_edge` validates endpoint existence). So when registering
a capacity on a Local, `register_capacity` now **mirrors any referenced
Global-only DataState into the Local DataState graph** before validation
and edge emission (`_mirror_global_datastates`, copies the node
verbatim — value/type/properties/id). This mirrors the existing capacity
Local-wins+Global-fallback (`_resolve_declaration`) and makes both the
F9 boot walk and DM-8's teach-on-Local Just Work with no DataState step
in the descriptor or the walk. Idempotent: already-Local DataStates are
untouched; truly-unknown IRIs fall through to the existing validation
raise.

## Consequences

**Good:** taught caps survive restart with no code re-registration; the
descriptor is the single durable artifact; the bipartite topology is
valid Local-side; teach-on-Local (DM-8/PB-G) needs no demo-side DataState
copy code.

**Cost:** the descriptor must be enriched at write time (DM-8 dependency).
`register_capacity`'s Local path gains a mirror step (additive, idempotent;
no effect on Global registration or on Local registrations whose
DataStates were registered Local explicitly).

**Boundary:** the factory registry + `reactivate_from_descriptors` are
pure `mindsos_capacity` (test-enforced `mindsos_capacity ⇏
mindsos_knowledge`). The KL-walking glue
(`reactivate_local_capacities`) that reads `learned-parameters` nodes
lives in `mindsos_server` (ADR-0186), which may import both layers.

## Supersession / amendment trail
- Amends **ADR-0156** — supersedes its Cost-§ premise "Locals are
  in-memory and re-registered each session" (see ADR-0156 §amendment-2).
  Builds on ADR-0156 §amendment-1 (upsert re-binds the declaration).
- **Resilient re-activation at boot (2026-07-16)** — `reactivate_from_descriptors`
  gains an additive-inert `strict` flag (default `True`; every pre-existing caller
  byte-identical). At resident-brain boot the server passes `strict=False`: a descriptor
  whose factory is not registered in this process is skipped with a loud `log.warning`
  naming the `reactivation_key`, never silently. Contract + rationale in **ADR-0183 §am-2**.
