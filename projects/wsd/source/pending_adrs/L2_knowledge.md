# L2 Knowledge Layer — Updates from WSD Goal-Finalization

**For:** Resuming the L2 Knowledge design chat with goal-finalization decisions loaded.
**Source:** `WSD_GOAL_FINALIZATION_OUTPUT.md` (project root). All items here are PROPOSED — ratification happens in the L2 design chat.

## How to use this file

Paste this file into the L2 design chat as loading context. Then work through:
- **§A** — ADRs to formalize.
- **§B** — schema / code changes to land in `mindsos_knowledge` and L2 storage.
- **§C** — interfaces L2 must expose to other layers.
- **§D** — open sub-questions to resolve before implementation.

---

## §A — Required ADRs

### A.1 — New `world-axioms` L2 sub-graph (v1 addition)

- New L2 sub-graph for axiom-style commonsense / world-knowledge rules ("birds usually fly," compliance rules, etc.).
- Distinct from `ontology` (DOLCE category hierarchy) and `concepts` (FrameNet frames).
- Initially populated by ConceptNet distillation; admin/end-user extensible.
- Schema: each axiom has conditions, outcome / consequent, priority, override-targets, provenance.

### A.2 — Promoted-pipelines storage as value-typed atomic-edge sequences (paths-of-paths, value-typed)

- Each promoted-pipeline node stores:
  - `path_id` — unique identifier.
  - `edge_sequence` — ordered list of capacity-edge IDs from L3 (the inlined atomic sequence).
  - `start_ds`, `end_ds` — endpoints inferable from the edge sequence.
  - `outcome_history` — measured metrics across uses; tagged by edge-versions in effect at measurement time.
  - `expression_metadata` — registration-time composition form (e.g. "P_new was registered as P1 + C") + currently-valid display abbreviations. Recomputable on graph updates.
  - `provenance` — promoted-by, promoted-when, promotion-rule capacity used, approving admin, rationale.
- **Paths are value-typed.** Composition shorthand is registration-time inlining only; no reference dependencies after registration.
- **No reference graph, no cascade re-evaluation.** Updates to one path do not invalidate dependent paths (because there are no dependents — paths are flat atomic-edge sequences).
- Equivalence detection at registration: matching atomic sequences either rejected as duplicate or linked.

### A.3 — Local↔Global update visibility

- Local additions (knowledge instances, capacity edges, paths) visible only within the user's session by default.
- Promotion to Global requires admin approval (eventually domain-specialized admin per L0-PROPOSAL-4 post-v1).
- Local paths referencing Global path content see Global state at registration time (inlining behavior); future Global updates do not affect already-registered Local paths.
- Cross-user Local sharing — post-v1.

### A.4 — Schema-bound knowledge addition

- Each L2 sub-graph has a queryable schema.
- Server layer (L0-PROPOSAL-2) enforces schema-conformance at user-add time.
- Failed validations route to a quarantine area for admin review; not silently dropped.
- Schemas themselves are admin-only.

### A.5 — Knowledge versioning + supersedes

- Every knowledge node carries an `add_timestamp` and version field.
- Updates use supersedes edges (`SUPERSEDES`) recorded in graph as first-class edges.
- Knowledge changes do not auto-flag dependent paths stale (paths are value-typed).
- Audit trail captures every modification.

### A.6 — Layered contradiction detection (option G)

- Cheap surface checks at add-time:
  - **E (source-disagreement):** if two knowledge items come from different sources and disagree (same key, different value), flag.
  - **F (local consistency):** for each new knowledge item, check existing knowledge "near" it (same lexicon entry, same concept, same domain) for conflict.
- Deeper checks in dream cycles:
  - **B (FOL contradiction):** run FOL inference over (existing ∪ new); flag P ∧ ¬P derivations.
  - **D (empirical):** re-evaluate against historical task outcomes; flag behavior-changing additions.
- Defeasible/default-logic detection (C) is post-v1 enhancement.
- Admin escalation for ambiguous cases.

### A.7 — Provenance metadata on every knowledge node

- `source` — dataset name / extraction pipeline ID / admin user / end-user.
- `source_version` — corpus version or pipeline timestamp.
- `extraction_pipeline_version` — which version of the distiller produced this.
- `add_timestamp` — when added.
- `confidence` / `trust_level` — initial confidence based on source quality.
- `superseded_by` (optional) — pointer if replaced.

### A.8 — v1 L2 sub-graph list

Confirmed sub-graphs for v1:

- `ontology` (DOLCE)
- `lexicon` (theoretical OEWN + empirical SemCor + OntoNotes + FrameNet + VerbNet + SemLink + GlossTag)
- `concepts` (FrameNet frames + frame relations)
- `alignments` (VerbNet, SemLink cross-resource maps)
- `memories` (historical task outputs)
- `promoted-pipelines` (per A.2)
- `task-patterns` (task-shape recognizers; hand-crafted seeds for v1)
- `problem-trace`
- `capacity-state`
- `sense-correlations`
- `learned-parameters` (initial defaults; updated by ALS)
- **`world-axioms` (new)** (per A.1)

---

## §B — Required schema / code changes in `mindsos_knowledge`

### B.1 — `world-axioms` sub-graph implementation

- New schema with axiom node type: conditions (structured), outcome/consequent, priority, override-targets, provenance.
- Initial bootstrap: ConceptNet distillation pipeline (see B.6).
- Querying: given an entity instance, return matching axioms in priority order.

### B.2 — Promoted-pipelines storage schema

- Node type: `PromotedPipeline` with fields per A.2.
- `edge_sequence` is a list of capacity-edge IDs from L3.
- Equivalence detection at registration: atomic-sequence comparison.
- Expression-metadata recomputation on path-graph updates.

### B.3 — Provenance metadata on every knowledge node

- Schema extended: every node + edge carries provenance fields per A.7.

### B.4 — Versioning + supersedes

- `SUPERSEDES` edge type as first-class.
- Version-history queries: "give me the version of node N at time T."
- All sub-graphs honor versioning, not just `learned-parameters`.

### B.5 — Schema-conformance validation hooks

- Each sub-graph exposes its schema (for L0 to query during validation).
- Server-driven validation calls into L2 to verify a proposed addition is schema-conformant.
- Quarantine staging area: separate L2 area for failed validations awaiting admin review.

### B.6 — Bootstrap distillation pipelines

- One distillation pipeline per source corpus:
  - OEWN → `lexicon` (theoretical layer).
  - SemCor + OntoNotes + GlossTag → `lexicon` (empirical layer) with multi-metric edges (Resnik + PMI + cond-prob).
  - FrameNet → `concepts`.
  - VerbNet + SemLink → `alignments`.
  - DOLCE → `ontology`.
  - ConceptNet → `world-axioms`.
- Each pipeline tagged with `extraction_pipeline_version`.
- Re-runnable when corpus updates or extraction bug fixes apply.

### B.7 — Layered contradiction-detection implementation

- E + F at add-time (synchronous on user-add path).
- B + D in dream cycles (asynchronous, batched).
- Admin queue surface for unresolved conflicts.

### B.8 — `fallback`-property storage support

- DS instances stored in L2 carry the `fallback` property when the DS is in coexistence migration (per L1-PROPOSAL-3).
- Embedded-copy storage (per L1 decision).

---

## §C — Interfaces L2 exposes to other layers

- **To L3:** read access to all sub-graphs as data sources for capacities; named-DS registry support.
- **To L4:** read/write to `learned-parameters`, `memories`, `task-patterns`, `promoted-pipelines`, `capacity-state`, `problem-trace`, `sense-correlations`, `world-axioms`.
- **To L0:** schema queries for validation; quarantine area read access; provenance + version-history queries; supersedes write API.
- **To L1:** persistence layer (FalkorDB graphs + SQLite non-graph state per ADR-0121).

---

## §D — Open sub-questions for L2 design chat

1. ConceptNet → `world-axioms` distillation specifics — which CN relations map to which axiom shapes; CC-BY-SA legal review for commercial release.
2. Empirical lexicon multi-metric edge schema — exact structure of Resnik + PMI + cond-prob storage.
3. Quarantine workflow specifics — staging area schema, admin notification, re-validation after schema updates.
4. Composed-knowledge atomic transactions — should multi-node user additions (e.g., concept + sense correlations + lexicon edges in one go) be all-or-nothing.
5. Cross-corpus alignment — when ConceptNet's "Paris" and a Wikidata-derived "Paris" coexist, alignment edges or DS-merging?
6. `world-axioms` priority/override semantics — how is priority encoded; how do override-targets reference other axioms.
7. Bootstrap pipeline performance — full bootstrap may take hours; incremental update support.
8. Knowledge-node confidence/trust scoring — initial values per source; updates through ALS.

---

**End of L2 updates.**
