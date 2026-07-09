---
title: What's new in v4
last_confirmed_phase: 38
---

# What's new in v4

MindsOS v4 is the L0–L3 release — Server, Core, Knowledge, and
Intellectual Capacity. L4 (Intelligence) and L5 (Mental Model) plus
FOL are explicitly out of scope; a separate follow-up plan covers
them.

This page is a terse summary of what the **38-phase rollout**
(Phase 00 → Phase 38, with Phase 37 retired) actually delivered.
For per-phase ship details consult `confirmation_docs/PHASE_MAP.md`
and `confirmation_docs/PHASE_<NN>_CONFIRMED.md`.

## Headlines

- **Five layers (1, 2, 3) shipped + the Server layer.** L1 Core
  (Phases 02–11), L2 Knowledge (Phases 12–17, 33–36), L3 Capacity
  (Phases 27–31), Server (Phases 18–25). Two integration phases
  (26 + 32) catch cross-layer regressions.
- **A new CLI:** `mindsos` (Typer-based) with subcommands per layer
  (`graph`, `schema`, `metagraph`, `instances`, `persistence`,
  `knowledge`, `capacity`, `server admin`, `server release`, …).
- **Single-image, single-sidecar distribution.** `docker compose
  up` ships the `mindsos` image plus a `falkordb` sidecar pinned by
  SHA256 digest; in-container tests are the canonical pass
  criterion.
- **Audit + capability gating from day one.** Every write goes
  through `mindsos_server.authz` with a capability roster of nine
  caps (`CAN_PROPOSE_MUTATION`, `CAN_APPROVE_RELEASE`,
  `CAN_HARD_DELETE_ARCHIVED`, …); every audit row is structured
  JSON with declared invariants.

## Layer-by-layer

### Server (L0)

User store + Argon2id auth + sessions + capability-based
authorization + structured audit + per-user transactional
promotion (admin-direct ATOM only at v1) + release-ship lock + a
diagnostic read-other-Local context manager. ADRs 0001–0013,
0040–0042, 0117–0120, 0136, 0137 govern.

### Core (L1)

Graphs / Nodes / Edges / HyperEdges; metagraphs (graphs as
nodes) + MetaEdges + MetaHyperEdges + IntergraphEdges (binary,
cross-graph) + IntergraphHyperEdges (n-ary, optionally ordered);
identity (IRIs), schema (`NodeType` + `EdgeType` +
`HyperEdgeType` + `IntergraphEdgeType` + …), persistence
(FalkorDB + WAL + indexes + OCC), reconstruction
(MetagraphLoader streaming), Snapshot + soft-delete +
RemovalImpact, XRef cross-metagraph references, Cypher
integrity scanner. ADRs 0014–0037, 0117–0137, 0148 govern.

### Knowledge (L2)

A metagraph of role-graphs: ontology, lexicon, concepts,
alignments, memories, problem-trace, capacity-state,
learned-parameters, sense-correlations, promoted-pipelines,
task-patterns. KnowledgeLayer + bootstrap (Global + lazy Local)
+ MetagraphView (read-only) + admin importers (DOLCE-DUL 4.1,
OEWN 2024, FrameNet 1.7) + admin similarity surface + KL
write-handle pattern + 5 semantic validators (Phase 36 hybrid
invariant home). ADRs 0038–0057, 0138–0150 govern.

### Capacity (L3)

13 functional categories (perception, comprehension, derivation,
decomposition, combination, path-finding, retrieval, scoring, trace,
signalling, interaction, learning-methods, consolidate),
DataStates + Capacities + dual metagraph (DataState graph +
Capacity graph) + capability gate + bipartite `produces`/`consumes`
edges (ADR-0156; superseded the earlier type-compat auto-discovery) +
constraint-driven pipeline finder + invoke runtime +
ProblemTraceRecord + residents + built-in text capacities + 2
wired write capacities (`capacity:consolidate:mm` +
`capacity:trace:problem`) with semantic-validator preconditions.
ADRs 0060–0100, 0143–0147 govern.

## Out of scope (L4/L5 follow-up plan)

The following carry-forward at Phase 38 ship and ship as a unit
with the L4 session orchestrator:

- `mindsos capacity invoke --session-token` CLI flag (Phase 30
  PB-30(a)).
- Falkor-backed L3 bootstrap; today's CLI uses a fresh-per-process
  in-memory `KnowledgeLayer.bootstrap()` (Phase 30 CF #3).
- `FalkorDBLocalPersister` + Local-write end-to-end CLI demo
  (Phase 25 + Phase 38 R3-PB-A).
- `include_deprecated` parameter discipline across L3 walks.
- `--install-builtins=<family>` CLI flag on `invoke` (waits for a
  second builtins family).
- `mkdocs build --strict` lift — depends on Model C remediation
  (Phase 38 R4-PB-A).
- 4 unconsumed L2 validators (`validate_local_to_global_ref`,
  `validate_alignment_role_naming`, `validate_ref_type`,
  `validate_promotion_candidate`) — await per-flow consumer
  capacities.
- `handle.validate_xref` body — wires alongside the first
  XRef-writing L3 capacity per ADR-0139 §amendment-1 clause 3.

## How to read further

- The [Text-realm cookbook](../usage/cookbook/text-realm.md) is the
  most concrete end-to-end walk.
- [Glossary](../concepts/glossary.md) covers the terms-of-art used
  throughout.
- `confirmation_docs/PHASE_MAP.md` is the authoritative rollout
  contract.
- Per-phase ship details live in `confirmation_docs/PHASE_<NN>_CONFIRMED.md`.
