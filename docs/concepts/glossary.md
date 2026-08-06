---
title: Glossary
last_confirmed_phase: 38
---

# Glossary

Terms-of-art used throughout the MindsOS docs and source. Definitions
are operational, not philosophical — what the term means inside this
codebase. Each definition cross-links to the page(s) that elaborate.

## A — D

**ADR (Architecture Decision Record).** A versioned decision document
under `docs/decisions/adr/`. ADRs carry a Status (Proposed →
Accepted → Superseded / Withdrawn) and §amendment-N blocks for
non-overriding clarifications. ADRs live in the parent project tree
per Model C; halvim references them by number.

**Alignment.** An L2 role-graph that records cross-source links
between concepts and lexical units (e.g., FrameNet frame → WordNet
synset). Shipped Phase 15a via the `AlignmentsImporter`. See
[Alignment schema](../usage/knowledge/alignment.md).

**Audit.** A structured-JSON append-only log of every server action
(login, logout, admin write, release ship, promotion, …). Each row
carries `actor_user_id`, `action`, `extra_json`, timestamp, and
declared invariants. Shipped Phase 21.

**Bootstrap.** The act of constructing a layer's initial state. KL
ships a `KnowledgeLayer.bootstrap()` classmethod that auto-ensures
the 6 Global role-graphs. CapacityLayer "bootstrap" is the
constructor (`CapacityLayer()`); Local metagraphs are created lazily
on first access per Phase 14 PB-9.

**Capacity.** A registered L3 function with inputs (DataState IRIs),
outputs (DataState IRIs), a category, and a Python implementation.
Capacities are *fixed-not-learned*; state lives in L2. See
[Capacity overview](../usage/capacity/overview.md).

**Capacity Layer (L3).** The layer that holds Capacities + DataStates
+ Constraints + Discovery + the pipeline finder + invoke runtime +
problem-trace. Shipped Phases 27–31. See
[Intelligence Layer](intelligence-layer.md) for the L4/L5 conceptual
content.

**CapacityLayer.** The Python class that owns the L3 dual metagraph
(`ds_graph` + `_capacity_index`). Constructor takes an optional
`KnowledgeLayer` for write-capacity bodies to consume via
`context["kl"]`.

**Category.** One of 13 L3 functional categories
(perception, comprehension, derivation, decomposition, combination,
retrieval, scoring, trace, signalling, interaction,
learning-methods, **consolidate**, …). Frozen vocabulary; new
categories ship via ADR.

**Cookbook.** A docs subsection (under `docs/usage/cookbook/`)
holding end-to-end vertical slices that stitch multiple layers. The
[text-realm cookbook](../usage/cookbook/text-realm.md) is the only
shipped cookbook at Phase 38.

**Core (L1).** The bottom domain layer: Graph + Node + Edge +
HyperEdge primitives, metagraphs (graphs-as-nodes) + MetaEdges +
MetaHyperEdges, IntergraphEdges (cross-graph), identity, schema,
persistence, reconstruction. No reasoning. See
[Graphs and metagraphs](graphs-and-metagraphs.md).

**DataState.** A typed slot in an L3 pipeline. Capacities consume
and produce DataStates. IRIs follow `datastate:<realm>.<name>`. See
[Data states](../usage/capacity/data-states.md).

## E — K

**Group DataState.** A DataState whose value is a set/list of
individually-addressable members (`group=True` + `member_ds`). A distinct
type from its member — the finder never bridges them; L4 owns the unpack
loop (ADR-0199).

**Edge.** A binary, intra-graph link between two Nodes; carries a
`rel_type` plus properties. See [Building graphs](../usage/core/building-graphs.md).

**Element.** A common-superclass referent for Graphs, Nodes, Edges,
HyperEdges, Metagraphs, MetaEdges, MetaHyperEdges, IntergraphEdges,
IntergraphHyperEdges — anything that participates in instancing per
ADR-0132. Lives in `mindsos_instances`.

**FalkorDB.** The graph database backing L1 + L2 persistence. Pinned
by SHA256 digest; sidecar in docker-compose.

**Global.** The shared knowledge metagraph — one per MindsOS
instance, admin-curated, released in discrete versions per
ADR-0118. Contrast with **Local**. See
[Global + Local metagraphs](global-local.md).

**Graph.** The L1 primitive — a named collection of Nodes + Edges +
HyperEdges with an identity guard. See
[Building graphs](../usage/core/building-graphs.md).

**HyperEdge.** An n-ary intra-graph link connecting any number of
Nodes (or other HyperEdges); carries a `rel_type` plus properties.

**Identity Registry.** Phase 02's `IdentityRegistry` —
deterministic IRI minting + collision detection, scoped per
metagraph or process. See [Identity](identity.md).

**Integration phase.** A phase that adds no new feature but runs a
scripted scenario across all prior-shipped layers (Phase 26
Integration A + Phase 32 Integration B). Convergence points for
cross-phase regression catch.

**IntergraphEdge.** A binary edge that connects a Node in graph G₁
to a Node in graph G₂, both belonging to the same metagraph.
Carries an immutable `compositional: bool` flag for
identity-bearing composition (cat = c + a + t). Shipped Phase 05b.
See [Intergraph edges](intergraph-edges.md).

**IntergraphHyperEdge.** N-ary cross-graph link; not 1-1; carries
both `compositional` and `ordered: bool` flags. Shipped Phase 05c.
`compositional=True` with `ordered=False` was refused at validation
step 10 (Phase 05c P8-A); that refusal is **lifted** at CORE-C2R2 —
see ADR-0205 §amendment-3.1. `ordered=False` **sorts and dedups** at
construction, and the dedup runs before the cardinality check, so a
set collapsing to 1-1 still refuses (use `IntergraphEdge`).
`ordered` is a property of the hyperedge **type**, not of the link.

**IRI.** Internationalized Resource Identifier. Every L2 / L3
entity (concept, capacity, datastate, alignment, memory, …) has a
stable, version-qualified IRI. See [Identity](identity.md) and the
[L2 identifiers concept](identifiers.md).

**KL (KnowledgeLayer).** The L2 entry-point class. Owns a
Metagraph of role-graphs + a per-user Local lookup +
install/extract hooks. Read-only at the public surface;
`KLWriteHandle` carries the write capability. See
[Knowledge overview](../usage/knowledge/overview.md).

**KLWriteHandle.** Per-(role, scope, version) write handle.
Capacities obtain one via `kl.writeable(session, role=..., scope=..., version=...)`.
Carries `mint_iri` + `write_and_validate` + `validate_node` +
`validate_xref`. Shipped Phase 33; semantic validators wired
Phase 36 (`validate_node`).

## L — Q

**Operand arity.** A capacity's `operand_arity={ds: N}` declaration for
consuming N operands of **one** DataState type. At invoke the key carries a
length-N list, read positionally by the body; core checks length only —
per-slot typing and roles stay body-side (ADR-0198).

**Layer.** One of the five domain layers (L1–L5) plus the
orthogonal Server layer. Layers compose downward: L3 imports L2
imports L1; Server imports all three.

**Lexicon.** An L2 role-graph holding lexical units (words,
multi-word expressions). Seeded via OEWN 2024 at Phase 15a.

**Local.** A per-user knowledge metagraph holding user-authored
state (memories, capacity-state, problem-trace) until promotion to
Global. Lazy-created on first access. Contrast with **Global**.

**Memory.** A `Memory` clustering-composite node in the user's Local
`episodic_memories` role-graph (Phase 39 rename per ADR-0044 §am-3),
written via `capacity:consolidate:mm`. IRI:
`episodic-memories-v1:memory:<user_id>:<memory_id>`. The role-graph
also hosts `Episode` per-task entries with IRI form
`episodic-memories-v1:episode:<user_id>:<episode_id>`.

**Metagraph.** A graph whose Nodes are themselves Graphs. Carries
MetaEdges + MetaHyperEdges (connecting graphs) and IntergraphEdges
(connecting Nodes across contained graphs). The MindsOS "5-layer
metagraph system" name comes from this structure.

**Model C.** The arrangement where ADRs + parent-tree
coordinated-changes live in `Layered Intelligence/`, separately
from halvim's git repo. Halvim references parent artifacts but
doesn't track them. See `[[feedback-docs-source-of-truth]]`.

**Node.** The L1 primitive — a named record with `value` + `type` +
properties + identity, belonging to one Graph.

**Ontology.** An L2 role-graph holding upper-level concepts. Seeded
via DOLCE-DUL 4.1 at Phase 15a. Carries a HyperEdgeType-lifted
schema from Phase 13.

**ProblemTraceRecord (PTR).** A structured failure record emitted
by L3 capacity bodies + the invoke runtime. Persisted to L2's
`problem-trace` role-graph (drain logic L4-owned). See
[Problem trace schema](../usage/knowledge/problem-trace.md).

**Promotion.** The act of moving a Local-authored knowledge item
into Global via a release. Per-user transactional;
admin-direct-ATOM only at v1 (Phase 24). See
[Promotion bridge](promotion-bridge.md).

## R — Z

**reads_mm.** A capacity-declaration flag. When `True` the body receives the
mental-model read handle (`context.mm_handle`); when `False` (default) it gets
`None`, so read-data must arrive as declared inputs. Gated in L4 dispatch
(ADR-0200).

**Release.** A discrete versioned snapshot of Global. Admin curates,
proposes for promotion, releases via `mindsos server release ship`.
Carries pending mutations + audit gate + release-ship lock per
ADR-0118.

**Resident.** *(Term retired Phase 41 — ADR-0155.)* Shipped Phase 31 as
a long-running L3 Capacity modeled descriptively at L3 + scheduled at L4.
In Phase 41 the L3 lifecycle plumbing was retired and "resident"
collapsed into **Monitor**: L3 ships the `Monitor` declaration +
`cl.iter_monitors()`; the lifecycle (subscription registry, scheduling)
is owned by the L4 substrate.

**Role-graph.** A Graph inside the L2 metagraph holding state for
one knowledge role (e.g., `lexicon`, `ontology`, `concepts`,
`memories`). Lazy-bootstrapped or shipped via Importer.

**Schema.** L1's vocabulary of allowed types: `NodeType` +
`EdgeType` + `HyperEdgeType` (graph-scoped) +
`IntergraphEdgeType` + `MetaEdgeType` + `MetaHyperEdgeType`
(metagraph-scoped). Shipped Phases 04 → 05d.

**Server.** The orthogonal L0 layer. Auth, sessions, capability
gating, audit, persistence orchestration. Not on the
layer-composition axis; provides the runtime envelope every domain
consumer (CLI, future web UI, batch jobs) needs.

**Session.** A server-issued bearer of a user identity + capability
roster + TTL. Issued by `mindsos server login`; verified via
`session_from_token`.

**Soft-delete.** L1's tombstone discipline — instead of hard-removing
a Node/Edge, mark it `deprecated_at: <ts>` and keep it for audit
trail. Runtime filter is advisory; queries opt in. Shipped Phase 10.

**Snapshot.** An L1 `MetagraphSnapshot` captures a metagraph's state
for release-ship rollback. Narrowed to release-ship scope per
ADR-0129. Shipped Phase 10.

**SubMind (Mindlet).** An autonomous, no-reasoning reflex over one
self-state vital — a `sense → threshold → emit` loop that self-schedules
its own cadence and never deliberates. The single L4 Mind arbitrates all
SubMind outputs (Signal, deliberated; or Reflex, a queue-bypassing
emergency). Partially reverses ADR-0155: the self-firing loop returns as
an L4-owned scheduler, not the retired L3 `start_resident`. Runtime in
`mindsos_intelligence/submind*.py`; endowment record in the L2 `subminds`
role-graph. Slice 1 shipped (ADRs 0188–0190). See
[Society of Mind](society-of-mind.md).

**Tester.** The human who runs `mindsos confirm-phase` on the Linux
host, hand-edits the generated `PHASE_<NN>_CONFIRMED.md`, and
records ship metadata. See `confirmation_docs/PHASE_MAP.md` §1
"Two-machine workflow."

**WAL (Write-Ahead Log).** L1's append-only operation log used for
crash recovery. One WAL graph per metagraph. Shipped Phase 07
(ADR-0122).

**XRef.** A cross-metagraph reference. Replaces the legacy
`ref:global:...` IRI form with a typed XRef primitive carrying
source + target metagraph + edge type. Shipped Phase 09.
