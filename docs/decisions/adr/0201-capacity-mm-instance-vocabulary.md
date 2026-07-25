# ADR-0201 — capacity-MM instance vocabulary + minting (DQ-2)

**Status:** Accepted (decision ratified 2026-07-16; D-1/D-3/minting). Vocabulary SHIPPED as CR#4 Slice 0 (PR #59, e234914); the two-graph writer topology it specifies is exercised by Slice 2 (not yet built).
Prerequisite for CR#4 capacity writer (Slice 0). Additive.
**Ratification note:** the minting IRI form is revised from the first draft to clear a
core-validator blocker (`datastate_iri()` rejects `#`/`:`) — see §Minting.

---

## Context

capacity_mm was designed (ADR-0165) to hold "L3 CapacityInstance/DataStateInstance with
produces/consumes edges." Verified: **neither class exists.** `mindsos_instances` ships
`ElementInstance / NodeInstance / EdgeInstance / HyperEdgeInstance / SubGraphInstance /
GraphInstance / MetaEdge / MetaHyperEdge / CompositeInstance / Intergraph{Edge,HyperEdge}`.
`DataStateInstance` / `CapacityInstance` are design-doc names (`mm.py:4`, `context.py:55`,
`l5_..._design_notes:239`) — this ADR builds them. (`CompositeInstance` *does* exist,
`registry.py:33` — it is simply not the carrier we use.)

`execute_pipeline` currently threads values on a Python blackboard dict (`pipeline_execution.py:86`)
— a standing violation of `mm.py:1-8`'s "no shadow state outside the MM." The writer (separate
CR#4 slice) deletes it; this ADR defines what it writes.

**L3's on-disk shape is bipartite two-graph (verified), and drives the topology decision:**
- `ROLE_DATASTATES = "capacity:datastates"` — one shared graph, every DataState node
  (`mindsos_capacity/identifiers.py:6,64`); DataState/Capacity are plain typed Core nodes
  (`NODE_TYPE_DATASTATE="DataState"`, `NODE_TYPE_CAPACITY="Capacity"`, `identifiers.py:146,149`).
- Capacities in a separate graph (`cap_gid`), distinct from the datastates graph (`ds_gid`).
- produces/consumes are `IntergraphEdge`s between them: `EDGE_PRODUCES` capability→DataState,
  `EDGE_CONSUMES` DataState→capability (`capacity_layer.py:411,418`; ":22 pipeline topology is now
  the explicit bipartite edge set"; ADR-0156).

capacity_mm is therefore the runtime **instance projection** of L3's static **type** catalog.

---

## Decision

### D-1 — Typed `NodeInstance` (not subclasses) · RATIFIED
`DataStateInstance` / `CapacityInstance` are plain `NodeInstance`s carrying
`type_name="DataStateInstance"/"CapacityInstance"`, not new `NodeInstance` subclasses.
- Mirrors L3 exactly: DataState/capacity are plain typed Core `Node`s (`NODE_TYPE_DATASTATE`/
  `CAPACITY`, `identifiers.py:146,149`), not bespoke classes.
- New subclasses would add loader-rehydrate ripple (`instance_loader.py:28` "Pass 1 — rehydrate
  every ElementInstance subclass") for no live-only benefit; plus `__all__` + doctor version-parity.
- `find_instances_by_type` already keys on the type marker. Revisit only if the two ever need
  distinct structure — which D-3 prevents by putting topology in edges, not node fields.

### D-2 — Granularity (settled by DQ-3)
One `DataStateInstance` per capacity **invocation-output**; payload = the produced value (a
2416-element collection is one node's payload, not 2416 nodes). One `CapacityInstance` per
invocation. The `raw_task` ingress is a distinguished `DataStateInstance` = the grounding-DAG root
(DQ-1/B).

### D-3 — Two-graph bipartite, mirroring L3 · RATIFIED
DataStateInstances in one graph, CapacityInstances in another, both within capacity_mm;
produces/consumes as `IntergraphEdgeInstance` between them — the same shape L3 uses.
- Buildable with shipped vocabulary: `IntergraphEdgeInstance`/`IntergraphHyperEdgeInstance` exist
  (`instance_loader.py:62-63,89-90`).
- **Preserve L3's format**, not flatten it. Single-graph would diverge from L3 and force a
  shape transform on instantiation, breaking `mm_resolver.produces_of/consumes_of` navigation
  parity.
- Directionality enforced structurally: PRODUCES = capacity→datastate, CONSUMES =
  datastate→capacity, as in `capacity_layer.py`.

### Mechanism — node+edge instancing (not whole-subgraph)
Mint individual DataStateInstance / CapacityInstance nodes + produces/consumes IntergraphEdges for
the **invoked slice only**, into the two-graph layout. A task never instantiates the whole L3
bipartite catalog — only the DataStates it produces and the capacities it invokes.
(`SubGraphInstance`/`GraphInstance` whole-subgraph instancing is the heavier alternative — see
Alternatives; not chosen.)

### Minting — composite scope + dedicated instance builder · RATIFIED (form revised)
Scope key = `(task_id, pipeline_run_ref)`. `task_id` alone collides on replan
(`orchestrator.py:178-196`); `pipeline_run_ref` alone orphans the task-level root.

**Type vs instance (load-bearing).** `datastate:arc.raw_task` is a *type*;
`datastate:arc.raw_task#…` is an *instance*. They share the `datastate:` prefix ONLY so
`sub_mm_for_iri` routes (a prefix check). Core's `datastate_iri()`/`capacity_iri()` build **types**
and validate the name against `_DATASTATE_NAME_RE`/`_CAPACITY_NAME_RE` = `^[a-z][a-z0-9_.\-]*$`
(`identifiers.py:223`) — which admits neither `#` nor `:`. **Instance IRIs therefore cannot go
through the type builders/validators.**

**Resolution — dedicated builders** `datastate_instance_iri()` / `capacity_instance_iri()`:
- Compose the node_id directly; **never** call `datastate_iri()`/`capacity_iri()`.
- Strip the `pipelinerun:` prefix from `pipeline_run_ref` and sanitize any remaining `:` → `-`
  (a raw colon-bearing run_ref would corrupt the fragment).
- `#` separates type from instance and is intentionally **out of the type charset** — an instance
  IRI cannot be mistaken for or registered as a type (a structural guard, not an accident).
- The instance node carries its type as a **property** (`datastate_type` / `capacity` = the type
  IRI), so the type is recoverable without parsing the IRI (feeds the run-local type→instance index
  directly).
- Instance IRIs never touch `datastate_iri` / `parse_datastate_iri` / `register_datastate`
  (which also forbids multi-dot, `capacity_layer.py:241-244` — irrelevant here since instances
  never register). **`_DATASTATE_NAME_RE` needs no change.**

Form (node_ids, minted by the dedicated builders; `run` = sanitized `pipeline_run_ref`):
```
DataStateInstance: datastate:<type>#<task_id>.<run>.<seq>
CapacityInstance:  capacity:<cap>#<task_id>.<run>.<seq>
grounding root:    datastate:arc.raw_task#<task_id>.root
```
Minting via the `ElementRegistry` already attached per sub-MM (`mm.py:54`); `seq` is
per-(scope, type) monotone. Composite scope survives replans (fresh generation per PipelineRun; old
generation persists as provenance, consistent with invalidate-at-and-below) and stays groupable by
task. `sub_mm_for_iri` routes by prefix regardless of the fragment.

### Provenance (DQ-1 / T2 / M1)
On the `raw_task` root only: nullable first-class `XRef` capacity_mm→knowledge_mm,
`ref_type=INSTANCE_OF`, target = the pinned corpus-entry instance in knowledge_mm (arc1) / `None`
(arc3). `XRef` is a metagraph-level row, not a routed node → no `sub_mm_for_iri` concern.
`validate_xref` (KL-scoped) is untouched.

---

## Consequences

- **Purely additive vocabulary:** no reader of capacity_mm today (reads_mm inert, verified). This
  ADR ships classes + builders only; the writer (blackboard deletion) is a separate CR#4 slice.
- `test_chain_artifact_emit.py:79-80` (rooms stay empty) flips when the **writer** lands — not this
  ADR. §0 gate is clean for the vocabulary, not for the writer.
- **Live-only:** capacity_mm instances are not persisted (DQ-8 persists only the per-task *chain*
  graphs; capacity/knowledge persistence deferred to WSD).
- **Shared-graph vs per-task asymmetry (intentional):** capacity_mm uses two graphs *shared* across
  a session — safe because its IRIs are task-scoped (the composite key → no collision) and it is
  live-only (no persist growth). The chain uses *per-task* graphs (DQ-8) because it is persisted and
  its writer IRIs are not task-scoped. When WSD persists capacity_mm, it inherits the same growth and
  will want per-task graphs too.
- **deep_copy dependency:** the raw_task provenance XRef makes the `deep_copy` independence bug
  live. Fixed in CR#4 **Slice 1** (its own slice — touches core element-key identity + graph ids),
  which must land **before** the capacity writer (Slice 2). Not this ADR.

---

## Alternatives considered

- **Single graph + `EdgeInstance`** — rejected: diverges from L3's verified two-graph shape;
  downgrades bipartiteness from structure to convention; breaks `mm_resolver` navigation parity.
- **`NodeInstance` subclasses** — rejected: loader/parity ripple (`instance_loader.py:28`) for no
  current behavioral need; L3 itself uses typed plain nodes.
- **Extend `_DATASTATE_NAME_RE` to admit `#`** — rejected: modifies a core type validator and
  weakens the type/instance distinction. The dedicated builder bypasses type validation instead, so
  `#` stays a guard and core is untouched.
- **In-charset separator** — rejected: unnecessary once the builder bypasses validation; `#`
  (out-of-charset) is the stronger choice because it makes an instance IRI unregisterable as a type.
- **Whole-subgraph instancing (`SubGraphInstance`/`GraphInstance`)** — deferred: heavier, and
  per-run dynamic instances only need the invoked slice.
- **Per-DataState-type nodes (type, not instance)** — rejected (DQ-2 core): one task produces many
  instances of one type (arc1: 8 grids, 2416 components).
- **Per-element explosion** — deferred: opt-in per DataState type when a consumer needs
  element-level MM addressing (none today).

---

## Dependencies

- CR#4 capacity writer (Slice 2) consumes this vocabulary; deep_copy independence (Slice 1) must
  precede it.
- DQ-1 provenance ruling (B / T2 / M1) — the XRef spec above.
- D8-B — orthogonal (persists intelligence_mm; these instances stay live-only).
- Amends ADR-0165/0166 (rooms now written). Does not touch ADR-0139 §am-1 (`validate_xref`).
