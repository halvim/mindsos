# L1 Core Layer — Updates from WSD Goal-Finalization

**For:** Resuming the L1 Core design chat with goal-finalization decisions loaded.
**Source:** `WSD_GOAL_FINALIZATION_OUTPUT.md` (project root). All items here are PROPOSED — ratification happens in the L1 design chat.

## How to use this file

Paste this file into the L1 design chat as loading context. Then work through:
- **§A** — ADRs to formalize.
- **§B** — schema / code changes to land in `mindsos_core`.
- **§C** — interfaces L1 must expose to other layers.
- **§D** — open sub-questions to resolve before implementation.

---

## §A — Required ADRs

### A.1 — Path-engine-handled inter-graph traversal (decision B)

- L1 exposes inter-graph traversal as a **path-executor-level** primitive, not a capacity-level one.
- The path specification can encode `hop_to_graph(metaedge_id, datastate)` steps between capacity invocations.
- The path executor resolves the metaedge, transitions DataState's graph context from source graph to target graph, and continues.
- **Capacities themselves stay graph-agnostic** — they consume their typed input DS and produce their typed output DS.

### A.2 — Capacities as hyperedges in the L3 capacity graph

- Capacities consuming multiple input DSes are **hyperedges** with multiple source endpoints.
- Capacities producing multiple output DSes are also hyperedges (multiple target endpoints).
- L1 already has hyperedge primitives — L3's capacity graph piggybacks on them.

### A.3 — DS modification + capacity-edge replacement protocol (three-phase migration)

The graph grows monotonically by default. Modifying an existing DS or replacing an existing capacity-edge in place is rare and admin-approved. When required:

**Phase 1 — Pre-flight audited validation.**
- Enumerate the cascade: every capacity-edge producing/consuming the target DS, every path traversing the target capacity-edge.
- Type-compatibility check across all affected edges.
- Representative-task-set replay against the proposed modified graph for behavioral-regression detection.
- Admin reviews enumeration + replay results in the Server-layer admin UI; approves or rejects.

**Phase 2 — Coexistence rollout with `fallback`-property runtime fallback.**
- Both DS2 and DS2' (or both B and B') exist in the graph simultaneously.
- DS2' carries an internal `fallback` property populated with the DS2-form of the same data. Every capacity producing DS2' is contracted to populate this property (see L3-PROPOSAL-3 contract).
- Conflict trigger = **semantic conflict only** (structural caught at pre-flight).
- The signal is a `conflict-marker` emitted by the consuming capacity when DS2'-form is semantically mismatched.
- **Per-invocation runtime fallback:** when `conflict-marker` fires, consuming capacity (or path executor) reads `DS2'.fallback` and uses the DS2-form for that invocation.
- **Aggregate rollback** is separate: admin monitors aggregate fallback frequency + metric regressions; can roll back the whole migration (L4-PROPOSAL-7).

**Phase 3 — Deprecation.**
- After N stable cycles or M tasks with fallback frequency below threshold, DS2 / B retired.
- The `fallback` property removed from DS2' (itself a trivial DS modification by then).
- All paths confirmed migrated.
- Audit trail preserves the deprecated version permanently.

**Decided sub-rules:**
- **No nested fallback chains.** Maximum one fallback per DS at any time. If a second migration is required before the first deprecates, the new target replaces the prior intermediate; the new DS''.fallback points to the original DS, not to the prior DS'.
- **`fallback` storage representation = embedded copy.** DS2' instances carry inline DS2-form data; producing capacity computes both forms at production time, frozen thereafter. Reference-pointer and recipe alternatives rejected for v1 (indirection complexity / correctness risk).
- **Versioned-binding option** during coexistence: paths can pin to either version per-path configuration.

### A.4 — Provenance metadata + knowledge versioning

- Every node and edge carries: `source`, `source_version`, `extraction_pipeline_version`, `add_timestamp`, `confidence` / `trust_level`, `superseded_by` (optional).
- Versioning supports supersedes (in-place updates retain version history).
- Schema-level migration follows §A.3 protocol.

---

## §B — Required schema / code changes in `mindsos_core`

### B.1 — Path-executor support for inter-graph hops

- Add path-step types: capacity invocation + inter-graph hop.
- Add `hop_to_graph(metaedge_id, datastate)` resolver on the path executor.
- DataState envelope tracks current graph context (explicit field or path-executor state-machine).
- Typed error model for metaedge-resolution failures (metaedge not present, target graph not loaded).

### B.2 — Hyperedge-based capacity edges

- Existing hyperedge primitives must support typed multi-source / multi-target edges with role-labeled endpoints (one endpoint per input DS, optionally multiple output endpoints).
- Edge metadata: capacity ID, input DS roles, output DS role, version.

### B.3 — DS modification protocol implementation

- Cascade enumeration: graph traversal that lists all edges/paths touching a target DS or capacity-edge.
- Replay harness invocation hook (admin-approved).
- Coexistence storage: both versions of a DS/edge live simultaneously with version metadata.
- `fallback`-property storage: embedded-copy serialization within DS instances.
- Cycle prevention: registration must reject any path/edge that would create a self-reference.

### B.4 — Provenance + versioning schema

- Node and edge schemas extended with provenance + version metadata.
- Supersedes edges (`SUPERSEDES`) recorded in graph as first-class edges.
- Audit trail captures every modification with full before/after.

### B.5 — Reproducibility primitives

- Deterministic path execution: same input + same path + same parameter snapshot → same output.
- Fixed-seed support for capacities marked stochastic.

### B.6 — Named-DS registry support

- L1 must support named-node identity layered on top of structural type info (the L3 named-DS registry will use this).
- Two nodes with structurally identical shapes but different names are distinct.

---

## §C — Interfaces L1 exposes to other layers

- **To L2:** node + edge + hyperedge + metaedge CRUD with versioning + supersedes; cascade enumeration query; cycle-detection on registration.
- **To L3:** capacity-edge registration with hyperedge support; named-DS registry primitives.
- **To L4:** path-executor invocation with inter-graph hop support; reproducibility infrastructure.
- **To L0:** persistence orchestration via FalkorDB (graphs) + SQLite (non-graph state) per ADR-0121.

---

## §D — Open sub-questions for L1 design chat

1. DataState envelope graph-context — explicit field vs path-executor state-machine.
2. Cross-graph DS validation — when a path expects DS_X from graph G1 vs G2, does the validator distinguish?
3. Concrete cascade enumeration algorithm + cost characterization (graph traversal complexity).
4. Cascade size cap heuristics — modifications affecting >K edges or >M paths may be too risky for in-place migration; admin should consider building DS2' / B' as a fresh-graph addition instead.
5. Aggregate fallback signal thresholds — concrete N (cycles), M (tasks), fallback-frequency threshold.
6. Audit trail durability + retention.
7. Compatibility of hyperedge primitives with existing FalkorDB schema (per ADR-0121).
8. Versioned-binding option implementation — per-path version-pin metadata.

---

**End of L1 updates.**
