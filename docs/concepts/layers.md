# The five layers (Phase 48)

MindsOS is a five-layer intelligence system on FalkorDB metagraphs, plus an
orthogonal Server layer. Each layer composes strictly on the one below; no
layer imports upward.

| Layer | Package | Responsibility |
|---|---|---|
| **L0 — Server** | `mindsos_server` | Auth, sessions, capability-based authorization, audit, persistence orchestration. Orthogonal to the L1–L5 composition axis. |
| **L1 — Core** | `mindsos_core` | Graphs, metagraphs, nodes, edges, hyperedges, schemas, persistence primitives. No reasoning. |
| **L2 — Knowledge** | `mindsos_knowledge` | A metagraph of role-graphs (ontology, lexicon, concepts, alignment, `episodic_memories`, …). Global + per-user Local. |
| **L3 — Capacity** | `mindsos_capacity` | Fixed-not-learned algorithms (perception, derivation, retrieval, scoring, consolidate, trace, dream, …) organised into functional families. |
| **L4 — Intelligence** | `mindsos_intelligence` | Per-session orchestrator + substrate: the six-phase task lifecycle, the Mental-Model working memory, dispatch, dreaming, crash recovery. **L4 = substrate + control flow only; every decision is an L3 capacity invocation.** |
| **L5 — Mental Model** | (in L4 + L2) | Per-task working memory (three sub-MMs + a 6-level chain of artifacts) that consolidates into retained **Episodes** in L2 at task completion. |

## How L4 and L5 fit together

A task runs through six lifecycle phases on a worker thread. As it reasons, L4
writes a **chain of artifacts** into the intelligence sub-MM — HintSet →
MappingResult → Plan (+ Milestones) → Pipeline → PipelineRun → TaskRun. Every
reasoning step is an L3 capacity dispatched through the L4 dispatcher, which
also carries the pre-authorized write capability a capacity needs to write to
L2 (the gate travels with the capability, not the layer).

At completion — success, failure, or abort — L4 **freezes the Mental Model**
and writes it as an **Episode** in the user's L2 `episodic_memories` role-graph
(retain-by-default). Episodes cluster into **Memory** composites by
task-pattern. A background **dream cycle** replays Episodes to regression-check,
detect drift, and retry past failures, feeding the same learning pipeline live
execution uses.

## The write boundary

L3 capacities are the write surface for L2, but they hold no principal: L4 (or
the CLI, for direct invocation) injects a pre-authorized, scope-aware
`writeable` capability onto the capacity context. Local writes need no special
capability; Global writes require `CAN_WRITE_GLOBAL`. The capacity body never
makes an authorization decision — it simply uses the capability it was handed.

## Retention and recovery

Episodes reference L2/L3 nodes by version-pinned `(iri, version)` tuples pinned
at instantiation. When a version is retired, affected Episodes inline the
retired content lazily on next read (the D'1 retention model). If a session
crashes mid-task, a startup scan turns the leftover checkpoint into a
crash-marked Episode so no in-flight task is silently lost.
