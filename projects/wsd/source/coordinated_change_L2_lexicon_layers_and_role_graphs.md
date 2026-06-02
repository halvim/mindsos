# Coordinated Change Handoff — L2 Knowledge: Lexicon Layers, New Importers, Role-Graph Additions

**Date:** 2026-04-29
**Origin:** WSD subsystem design conversation (Word Sense Disambiguation project, Henrique Alvim).
**Purpose:** Surface L2 Knowledge Layer extensions required by the WSD subsystem architecture. Multiple distinct change items grouped into one handoff because they all touch L2; the L2 chat may sequence them.
**Status:** Pre-implementation. Architectural specification only.
**Depends on:** `coordinated_change_L1_intergraph_and_layers.md` (L1 must ship `InterGraphEdge` primitive + Schema layer mechanism before this handoff is fully implementable).

---

## 0. How to use this document

Upload to the L2 design chat. Self-contained — does not require WSD-design-chat context. The L2 chat should:

1. Read §1 (motivation) and §2 (summary) to orient.
2. Read §3–§7 for each concrete change item.
3. Read §8 (coordinated implications across L0/L1/L3/L4) for ripple effects.
4. Read §9 (open questions) before designing internals.
5. Read §10 (phasing) for sequencing recommendation.
6. Read §11 (what this does NOT change) to bound scope.
7. Reference `WSD_ARCHITECTURE.md` (canonical architecture spec) if context on a design choice is needed.

L2 owns: schema decisions, role-graph design, importer interfaces, persistence patterns, version semantics. This handoff specifies *what* needs to land; *how* is L2's call.

---

## 1. Why this handoff exists

The WSD subsystem requires several extensions to L2:

  - **Lexicon graph schema gains two layers** — `theoretical` (existing OEWN edges) and `empirical` (new edges from corpus mining). Uses the new L1 schema-layer mechanism (per L1 handoff Change 2).
  - **Five new corpus and lexical-resource importers** to populate the empirical layer from SemCor, OntoNotes, FrameNet (extended), VerbNet, SemLink, and GlossTag.
  - **Three new role-graphs** — `parameter-staging` (Local), `pending-promotions` (Local + Global), `capacity-gaps` (Global, admin-visible) — supporting the ALS audited-learning subsystem.
  - **Cross-system ontology mappings** as InterGraphEdges (per L1 handoff Change 1) for class-generalization fusion.
  - **Updates to existing role-graphs in spec** (`task-patterns`, `promoted-pipelines`, `learned-parameters`).
  - **Removed from spec:** `sense-correlations` as a separate role-graph (now empirical layer of lexicon).

---

## 2. Summary of changes

| # | Change | Section | L1 dependency? |
|---|---|---|---|
| 1 | Lexicon schema gains `theoretical` and `empirical` layer declarations | §3 | Yes — L1 Schema layer mechanism |
| 2 | New importers: SemCor, OntoNotes, VerbNet, SemLink, GlossTag; extended FrameNetImporter | §4 | No |
| 3 | Empirical-layer edge type vocabulary, multi-metric properties | §3.2, §3.3 | No |
| 4 | Cross-system mappings as InterGraphEdges | §5 | Yes — L1 InterGraphEdge primitive |
| 5 | New role-graph: `parameter-staging` (Local) | §6.1 | No |
| 6 | New role-graph: `pending-promotions` (Local + Global) | §6.2 | No |
| 7 | New role-graph: `capacity-gaps` (Global, admin-visible) | §6.3 | No |
| 8 | Updates to `task-patterns` role-graph spec | §6.4 | No |
| 9 | Updates to `promoted-pipelines` role-graph spec | §6.5 | No |
| 10 | `learned-parameters` updates (per FOL #4 split or single — open) | §6.6 | No |
| 11 | Withdraw separate `sense-correlations` role-graph from L2 §12 spec | §7 | No |

Some changes are independent and can ship in parallel; some have prerequisites. See §10 for phasing.

---

## 3. Lexicon schema — theoretical + empirical layers

### 3.1 Layer declarations (requires L1 schema layers)

The lexicon graph schema (built by `OewnImporter` and friends) declares two named layers:

```python
schema = build_lexicon_schema(strict=False)

# Existing edge types from OEWN
schema.add_edge_type(EdgeType("HYPERNYM_OF", ...))
schema.add_edge_type(EdgeType("HYPONYM_OF", ...))
schema.add_edge_type(EdgeType("SYNSET_MEMBER", ...))
schema.add_edge_type(EdgeType("ANTONYM_OF", ...))
schema.add_edge_type(EdgeType("MERONYM_OF", ...))
schema.add_edge_type(EdgeType("HOLONYM_OF", ...))
schema.add_edge_type(EdgeType("DERIVATIONALLY_RELATED", ...))
schema.add_edge_type(EdgeType("LEMMA_OF", ...))
# ... (full OEWN edge type list)

# New edge types for empirical layer
schema.add_edge_type(EdgeType("COOCCURS_SAMESENT", ...))
schema.add_edge_type(EdgeType("COOCCURS_DEPARC", ...))
schema.add_edge_type(EdgeType("COOCCURS_SAMECLAUSE", ...))
schema.add_edge_type(EdgeType("COOCCURS_SAMEFRAME", ...))
schema.add_edge_type(EdgeType("SUBJECT_OF", ...))
schema.add_edge_type(EdgeType("DOBJECT_OF", ...))
schema.add_edge_type(EdgeType("IOBJECT_OF", ...))
schema.add_edge_type(EdgeType("OBL_OF", ...))
schema.add_edge_type(EdgeType("AGENT_OF", ...))
schema.add_edge_type(EdgeType("PATIENT_OF", ...))
schema.add_edge_type(EdgeType("THEME_OF", ...))
schema.add_edge_type(EdgeType("INSTRUMENT_OF", ...))
schema.add_edge_type(EdgeType("LOCATION_OF", ...))
schema.add_edge_type(EdgeType("TIME_OF", ...))
schema.add_edge_type(EdgeType("IS_VALID_FILLER_FOR", ...))

# Layer declarations
schema.add_layer("theoretical", [
    "HYPERNYM_OF", "HYPONYM_OF", "SYNSET_MEMBER", "ANTONYM_OF",
    "MERONYM_OF", "HOLONYM_OF", "DERIVATIONALLY_RELATED", "LEMMA_OF",
    # ...
])
schema.add_layer("empirical", [
    "COOCCURS_SAMESENT", "COOCCURS_DEPARC", "COOCCURS_SAMECLAUSE",
    "COOCCURS_SAMEFRAME",
    "SUBJECT_OF", "DOBJECT_OF", "IOBJECT_OF", "OBL_OF",
    "AGENT_OF", "PATIENT_OF", "THEME_OF", "INSTRUMENT_OF",
    "LOCATION_OF", "TIME_OF",
    "IS_VALID_FILLER_FOR",
])
```

Both layers in the same lexicon graph. Layer membership is type-level (each edge type belongs to exactly one layer per L1's layer mechanism design).

### 3.2 Empirical-layer edge type vocabulary

Closed vocabulary in v1, admin-extended (matches KL's REF_TYPES discipline per L2 handoff §7 I4). Sub-types organized by relationship_type:

**Co-occurrence:**

  - `COOCCURS_SAMESENT` — both senses appear in the same sentence.
  - `COOCCURS_DEPARC` — connected via a single dependency arc.
  - `COOCCURS_SAMECLAUSE` — same clause.
  - `COOCCURS_SAMEFRAME` — both fillers of the same frame instance.

**Predicate-argument:**

  - `SUBJECT_OF` — sense_a is grammatical subject of sense_b (predicate).
  - `DOBJECT_OF` — direct object.
  - `IOBJECT_OF` — indirect object.
  - `OBL_OF` — oblique object (UD's `obl` relations).

**Frame-element (FrameNet FEs):**

  - `AGENT_OF`, `PATIENT_OF`, `THEME_OF`, `INSTRUMENT_OF`, `LOCATION_OF`, `TIME_OF` — sense_a fills the named FE role of frame-evoking sense_b.

**Class-restriction (VerbNet-derived):**

  - `IS_VALID_FILLER_FOR` — sense_a (or its class ancestors) is a valid filler for sense_b's argument slot per VerbNet class restrictions.

### 3.3 Edge properties (empirical layer)

Schema-validated properties:

- `evidence_count: int` — number of distinct observations supporting this edge.
- `confidence: float` — Beta-posterior reliability of metric estimates (0–1).
- `domain_tag: str` — domain label (`general | news | biomedical | conversational | ...`).
- `first_observed: datetime` — first observation.
- `last_observed: datetime` — most recent observation.
- `source_corpus_iris: list[str]` — provenance.
- **Per-metric properties** (one or more, depending on which metric capacities have computed):
  - `metric_resnik_strength: float`
  - `metric_pmi_strength: float`
  - `metric_conditional_prob: float`
  - `metric_lin_strength: float` (v2)
  - `metric_<name>_strength: float` (extensible — new metric = new property)

Multiple metrics on the same edge are stored as separate properties, not in a list. Readers query whichever metric they need.

### 3.4 Backward compatibility

Schemas without layer declarations work as today (layer mechanism is additive per L1 handoff §4.5). Existing OEWN-imported lexicon graphs continue working. Layer declarations get added when OewnImporter is updated (or via a migration step).

### 3.5 OEWN importer touch

OewnImporter needs minor extension to declare its existing edge types as `theoretical` layer membership during schema construction. No change to import logic itself.

---

## 4. New importers

Six importers (five new, one extension). Each is independent — no cross-importer calls. Shared utility libraries handle common concerns.

### 4.1 SemCorImporter

**Purpose:** Populate empirical layer from SemCor 3.0 — the canonical sense-tagged corpus.

**Input:** SemCor 3.0 distribution (Brown corpus tokens with WordNet sense annotations + parse trees).

**Layer contributions:** `empirical`. Specifically:

  - Co-occurrence sub-types: `COOCCURS_SAMESENT`, `COOCCURS_DEPARC`, `COOCCURS_SAMECLAUSE`.
  - Predicate-argument sub-types: `SUBJECT_OF`, `DOBJECT_OF`, `OBL_OF` via parse trees.

**Volume:** ~200k tokens, ~25k sense-tagged content words. Smaller than the others but high quality.

**Quality:** Gold (manually annotated).

**Genre:** 1960s general English (Brown corpus).

**Pre-requisites:** OewnImporter must have run first (to create lexicon sense nodes that SemCor edges target). Fail-fast if missing.

**Implementation pattern:** Follows existing `Importer` ABC per L2 handoff §3.2. `_parse(path) → ImporterResult` shape; provenance-stamps every edge.

### 4.2 OntoNotesImporter

**Purpose:** Populate empirical layer from OntoNotes 5.0 — the largest gold-tagged multi-genre corpus.

**Input:** OntoNotes 5.0 distribution (multi-layer annotations: POS, syntax, NER, coref, PropBank predicate-argument).

**Layer contributions:** `empirical`. Specifically:

  - Predicate-argument sub-types via PropBank → SemLink → FrameNet roles → WordNet senses: `SUBJECT_OF`, `DOBJECT_OF`, `IOBJECT_OF`, `OBL_OF`.
  - Co-occurrence sub-types from sentence and clause boundaries.
  - Frame-element sub-types via SemLink mapping where alignment exists.

**Volume:** ~2.5M words.

**Quality:** Gold.

**Genre:** Multi-genre (newswire, broadcast, web, telephone conversations).

**Pre-requisites:** OewnImporter + SemLinkImporter must be loaded. Fail-fast.

**Caveats:** OntoNotes uses coarser sense groups than WordNet; SemLink alignment is lossy (~40–60% of triples retained). Importer logs alignment-loss statistics.

### 4.3 VerbNetImporter

**Purpose:** Populate empirical layer + class-generalization knowledge from VerbNet.

**Input:** VerbNet distribution (~6,200 verbs in ~270 classes, with syntactic frames, theta roles, selectional restrictions).

**Layer contributions:** `empirical`, specifically:

  - Predicate-argument structural patterns at class level (one edge per class-frame-role combination).
  - `IS_VALID_FILLER_FOR` class-restriction edges.

**Volume:** Lexical resource (not corpus). ~6,200 verb entries.

**Quality:** Curated.

**Pre-requisites:** OewnImporter loaded (VerbNet has WordNet sense alignments for most entries). Fail-fast.

**Importer note:** VerbNet's data is structurally different from corpus annotations — it's a class-frame catalog. Importer extracts class hierarchy + frame patterns, generates class-level edges directly (no per-observation aggregation).

### 4.4 SemLinkImporter

**Purpose:** Load alignment graph between WordNet ↔ PropBank ↔ FrameNet ↔ VerbNet.

**Input:** SemLink distribution (manual mappings).

**Layer contributions:** Doesn't generate empirical-layer edges directly. Builds an alignment role-graph that other importers query via the `sense_iri_align` shared utility.

**Volume:** Manual mappings — small but critical.

**Pre-requisites:** OewnImporter, FrameNetImporter loaded. (VerbNetImporter not strictly required but recommended.) Fail-fast.

**Importer note:** Follows existing AlignmentsImporter pattern (per L2 handoff). May extend or be a sibling to it depending on whether the alignment shape fits AlignmentsImporter's existing schema.

### 4.5 GlossTagImporter

**Purpose:** Populate empirical layer (down-weighted) from WordNet glosses.

**Input:** WordNet GlossTag corpus (sense-tagged definitions).

**Layer contributions:** `empirical`, specifically `COOCCURS_SAMESENT`-style edges within definitional contexts.

**Volume:** ~120k glosses.

**Quality:** Gold (sense-tagged), but caveat per WSD handoff §4.2: dictionary text isn't natural argument structure. Edges from this importer carry a `source_quality_weight: float` property (e.g., 0.3) that consumers can use for weighting.

**Pre-requisites:** OewnImporter loaded. Fail-fast.

**Implementation note:** May be folded into OewnImporter as an optional extension rather than a separate importer; depends on L2 chat's preference.

### 4.6 FrameNetImporter (extended)

**Purpose:** Existing FrameNetImporter (per L2 handoff §3.2) populates the `concepts` role-graph with frame definitions. Extension to also populate the lexicon's empirical layer with frame-element edges.

**Input:** FrameNet 1.7 annotated example sentences.

**Layer contributions:** `empirical`, specifically frame-element sub-types: `AGENT_OF`, `PATIENT_OF`, `THEME_OF`, `INSTRUMENT_OF`, `LOCATION_OF`, `TIME_OF`.

**Volume:** ~200k annotated example sentences with FE role assignments.

**Quality:** Gold.

**Pre-requisites:** Existing FrameNetImporter functionality + OewnImporter loaded. SemLinkImporter recommended for sense alignment (FrameNet lex-units → WordNet senses). Fail-fast where alignment is required.

**Implementation note:** This may be a separate importer (`FrameNetEmpiricalImporter`) that runs after the existing FrameNetImporter, or an extension to the existing one. L2 chat decides.

### 4.7 Shared utility libraries

Stateless helpers callable from any importer:

- **`sense_iri_align(corpus_sense_id, source_inventory) → oewn_iri`** — converts cross-inventory sense IDs to canonical OEWN IRIs via SemLink graph. Raises `AlignmentError` if no mapping exists.
- **`class_generalize(sense_iri, target_hierarchy) → list[ancestor_iri]`** — computes ancestors in the named class hierarchy (DOLCE / WordNet hypernym / VerbNet / FrameNet inheritance). Used at import time for mandatory DOLCE-level edges; lazy at query time for WordNet hypernyms.
- **`metric_compute(observation_count, class_priors, metric_type) → float`** — computes Resnik / PMI / conditional / Lin / etc. Each metric is a separate L3 capacity; this helper invokes the appropriate one.
- **`mwe_segment(tokens, mwe_inventory) → list[mwe_unit | token]`** — recognizes MWEs from FrameNet MWE lexical units + WordNet collocations.

These utilities are L3 capacities or library functions called by importers. L2 chat decides the architectural shape.

### 4.8 Importer prerequisites — fail-fast policy

Importers raise on missing prerequisites:

  - SemCorImporter, OntoNotesImporter, VerbNetImporter, GlossTagImporter — require OewnImporter loaded.
  - OntoNotesImporter, FrameNetImporter (extended) — require SemLinkImporter loaded for alignment.
  - SemLinkImporter — requires OewnImporter + FrameNetImporter loaded.

Errors are clear (`PrerequisiteImporterMissing(<name>)`); admin sees what to load.

### 4.9 Idempotency

Re-running an importer is safe:

  - Find-or-update on existing edges (key = `(source_node, target_node, type_name, domain_tag)`).
  - Increment `evidence_count`, recompute metric properties, update `last_observed`.
  - No edge duplication.

### 4.10 Versioning

Each importer follows the existing `register_version_graph` + `activate_version` pattern per L2 handoff §3.3.

---

## 5. Cross-system mappings as InterGraphEdges (requires L1)

Class-generalization fusion needs cross-system mappings (e.g., WordNet synset ↔ DOLCE class). These live as **InterGraphEdges** (per L1 handoff Change 1) connecting nodes across role-graphs:

  - Lexicon graph (WordNet synsets) → Ontology graph (DOLCE classes): `InterGraphEdge` of type `MAPS_TO_DOLCE_CLASS`.
  - Lexicon graph (VerbNet classes, if represented as nodes) → Ontology graph (DOLCE classes): `MAPS_TO_DOLCE_CLASS`.
  - Concepts graph (FrameNet frames) → Ontology graph (DOLCE classes): `MAPS_TO_DOLCE_CLASS`.

v1 mappings are **hand-curated**, loaded by a new admin tool or extension to existing AlignmentsImporter. Coverage will be partial (~10–20% of WordNet synsets initially); the generalization mechanism handles unmapped senses gracefully.

InterGraphEdge schema-level constraints:

  - Source and target graph roles can be restricted at schema level (e.g., `MAPS_TO_DOLCE_CLASS` only between graph-roles `lexicon` and `ontology`).
  - Edge properties: `confidence`, `mapping_source` (manual / automated / future-LLM), `mapping_provenance` (which curator, when).

L2 hierarchy registration is **admin-only** in v1. Dream-time discovery of new mappings (and new hierarchies) is deferred to v2+.

---

## 6. New and updated role-graphs

### 6.1 New role-graph: `parameter-staging` (Local only)

**Purpose:** Live evidence accumulation for ALS subsystems. Each registered ALS subsystem writes evidence rows here as tasks complete; dream-time aggregation pulls from here.

**Scope:** Local only. Per-user training evidence stays private to the user's Local metagraph. No Global parameter-staging.

**Schema:**

  - Node type: `StagedEvidence`.
  - Properties:
    - `parameter_set_iri: str` — which subsystem owns this evidence.
    - `signal_source_iri: str` — which signal generated this row (S1/S2/S3/S6/S8/etc.).
    - `target_parameter_iri: str` — specific parameter being affected.
    - `target_value: float | dict` — the target/observation value.
    - `evidence_pointer: str` — IRI of source memory or task.
    - `signal_weight: float` — base signal weight from source.
    - `blame_weight: float` — Phase-6 blame attribution weight (1.0 if not failure-attributed).
    - `timestamp: datetime`.

**Lifecycle:** rows are created per-task; consumed by dream-aggregation; pruned after a configurable retention window (admin-tunable).

**Schema layer:** none (no theoretical/empirical distinction needed for staging).

### 6.2 New role-graph: `pending-promotions` (Local + Global)

**Purpose:** Audit queue for proposed parameter updates. Holds proposals that have passed validation but await admin approval.

**Scope:** Both Local and Global. Local instances per user; Global instance system-wide.

**Schema:**

  - Node type: `PendingPromotion`.
  - Properties:
    - `parameter_set_iri: str`.
    - `proposed_at: datetime`.
    - `scope: str` — `local | global`.
    - `proposer: str` — user_id (Local) or `system` (Global aggregation).
    - `audit_policy: str` — `auto-apply | batched-summary | individual-review`.
    - `validation_results: dict` — V1/V2/V3 outcomes.
    - `proposed_diff: dict` — parameter changes (per-parameter old_value / new_value / confidence).
    - `evidence_summary: dict` — # of contributing tasks, signal-source breakdown, examples.
    - `status: str` — `pending | approved | rejected | applied`.
    - `decision_at: datetime | None`.
    - `decided_by: str | None`.
    - `decision_notes: str | None`.

**Lifecycle:** created by ALS dream-aggregate phase; consumed by audit phase; persists as audit log after `applied` or `rejected`. Long-term archival policy admin-tunable.

### 6.3 New role-graph: `capacity-gaps` (Global, admin-visible)

**Purpose:** Records task shapes the system cannot solve due to missing capacity coverage. Admin-actionable queue.

**Scope:** Global only. (Admin operates at Global scope; Local capacity gaps are surfaced via task failure logs but tracked centrally.)

**Schema:**

  - Node type: `CapacityGap`.
  - Properties:
    - `task_shape_iri: str` — which task-shape failed path-finding.
    - `start_datastate_iri: str`.
    - `goal_datastate_iri: str`.
    - `attempted_searches: list[dict]` — which path-finding capacities were tried, what they returned.
    - `first_seen_at: datetime`.
    - `last_seen_at: datetime`.
    - `occurrence_count: int`.
    - `status: str` — `open | resolving | resolved | out_of_scope`.
    - `resolution: str | None` — `taught_capacity | added_adapter | scope_limit_documented | etc.`.
    - `resolved_at: datetime | None`.
    - `resolved_by: str | None`.

**Lifecycle:** created by L4 when path-finding fails; updated on subsequent occurrences; resolved when admin acts.

### 6.4 Updated `task-patterns` role-graph

Already in L2 §12 spec; refined:

**Purpose (corrected):** Sub-shape recognizers, not whole-task templates. A single task triggers multiple patterns; L4 composes a pipeline from the union of capacities those patterns reference.

**Schema additions/refinements:**

  - Node type: `TaskPattern`.
  - Properties:
    - `pattern_name: str` — e.g., `sense-disambiguation-needed`, `coreference-resolution-needed`.
    - `task_shape_recognizer: dict` — declarative match criteria (TBD: structural pattern over input DataState shape, predicate over DataState properties, etc.).
    - `required_capacities: list[capacity_iri]` — which capacities are needed to handle this sub-shape.
    - `sufficient_predicate: dict` — TBD shape; admin-authored predicate that determines when "this aspect of the task is sufficiently solved" (per task-end signal in WSD architecture §3.8).
    - `n_observations: int` — usage count.
    - `confidence: float`.
    - `provenance: str` — `admin_authored | system_discovered`.

**v1 admin-authored patterns (initial set; expand as needed):**

  - `sense-disambiguation-needed`
  - `coreference-resolution-needed`
  - `frame-fitting-needed`
  - `question-decomposition-needed`
  - `constraint-translation-needed`
  - `novel-lemma-encountered`
  - `cross-realm-bridge-needed`
  - `logical-coherence-required`
  - `multiple-choice-decision-needed`

System discovers more via dream-system pattern mining.

### 6.5 Updated `promoted-pipelines` role-graph

Already in L2 §12 spec; one important change:

**`promoted-pipelines` is now an ALS-trainable subsystem.** Its `confidence` property per `(pipeline, task_type)` record is updated via the ALS pipeline (signal sources S6 task-outcome + S8 replan-divergence). Currently L2 §12 says "L4 writes" — that L4 write goes through ALS staging + audit, not direct write.

Schema unchanged; semantic clarification on writer.

### 6.6 `learned-parameters` role-graph (open)

L2 §12 currently specifies a single `learned-parameters` role-graph. FOL handoff pushback #4 recommends splitting into three:

  - `learned-scalars` — small numeric params, thresholds, vectors.
  - `learned-policies` — decision trees, rule sets, FSCs.
  - `learned-models` — large model artefacts (deferred to v2 pending FOL #8 blob storage).

**Open decision for L2 chat:** stick with single `learned-parameters` (simpler v1) or implement the split now. Either works architecturally; ALS subsystem registration uses `parameter_set_iri` as the addressable key regardless of physical role-graph layout.

Recommendation: single `learned-parameters` for v1 (v1 doesn't ship M1 gradient descent or large model artifacts; M2/M3/M4 mechanisms produce small parameter values that fit the single graph). Revisit when M1 / large models become relevant.

### 6.7 Other role-graphs from L2 §12 — status

Per L2 §12 (knowledge handoff), seven new roles were proposed: `promoted-pipelines`, `task-patterns`, `memories`, `problem-trace`, `capacity-state`, `sense-correlations`, `learned-parameters`.

Status after this handoff:

  - `promoted-pipelines` — kept as designed; ALS-trainable.
  - `task-patterns` — kept; refined per §6.4 (sub-shape recognizers, not whole-task templates).
  - `memories` — kept as designed.
  - `problem-trace` — kept as designed.
  - `capacity-state` — kept as designed.
  - **`sense-correlations` — withdrawn as separate role-graph.** Now empirical layer of lexicon (per §3 of this handoff).
  - `learned-parameters` — kept; single or split per §6.6.

Plus three new role-graphs from this handoff:

  - `parameter-staging` (Local).
  - `pending-promotions` (Local + Global).
  - `capacity-gaps` (Global).

---

## 7. Withdraw `sense-correlations` from L2 §12 spec

L2 §12 currently lists `sense-correlations` as a separate role-graph with its own schema (`SenseCoOccurrence` node type, `lemma_a / sense_a / lemma_b / sense_b / correlation_strength / evidence_count`).

WSD design has settled on adding empirical edges directly to the lexicon graph in a schema-declared `empirical` layer (per §3 of this handoff). The separate `sense-correlations` role-graph is withdrawn from spec.

Action items for L2:

  - Update L2 §12 to remove the `sense-correlations` row from the role-graph table.
  - Replace with note: "Empirical-layer edges added to lexicon role-graph; see §3 of `coordinated_change_L2_lexicon_layers_and_role_graphs.md`."
  - Coordinated update to `layer4_intelligence_design_notes.md` (which referenced `sense-correlations` from FOL Layer design 2026-04-23).

---

## 8. Coordinated implications across other layers

### L0 — Server

  - **`user_settings` table for ALS training preferences** (per `coordinated_change_L0_user_settings.md`). Read by L4 via Session at start of dream training cycles.

### L1 — Core

  - **Schema layer mechanism** (Change 2 in L1 handoff) is required for §3 of this handoff.
  - **InterGraphEdge primitive** (Change 1 in L1 handoff) is required for §5 of this handoff (cross-system mappings).

### L3 — Capacity

  - Each importer relies on shared utility L3 capacities (`sense_iri_align`, `class_generalize`, `metric_compute`, `mwe_segment`).
  - Per-hierarchy ancestor-walk capacities (`class.ancestors_*`) per `coordinated_change_L3_capacities_and_monitors.md`.
  - Metric library capacities (`metric.resnik`, `metric.pmi`, `metric.conditional_probability`).

### L4 — Intelligence

  - ALS reads `parameter-staging`, writes `pending-promotions`, applies to `learned-parameters` after audit. All per `coordinated_change_L4_intelligence_and_als.md`.
  - Path-finding writes `capacity-gaps` on no-path outcomes.
  - L4 design notes need update to remove `sense-correlations` reference (now in lexicon empirical layer).

### L5 — Mental Model

  - No direct impact. MM continues to instantiate from L2 graphs as today; the empirical layer is just additional edges in lexicon, queryable via existing patterns.

---

## 9. Open questions for L2 chat

  1. **Single `learned-parameters` or three-way split** (per §6.6)? My recommendation: single in v1, split if measured to need it.

  2. **GlossTagImporter as separate importer or extension to OewnImporter** (per §4.5)?

  3. **FrameNetImporter extension as separate importer or in-place** (per §4.6)?

  4. **`task_shape_recognizer` schema for `task-patterns`** (per §6.4) — declarative match criteria shape needs detailed design. Options: structural pattern over DataState shape; predicate function reference; learned classifier reference. Probably hybrid; specify in L2 chat.

  5. **`sufficient_predicate` schema for `task-patterns`** — same question; admin-authorable shape.

  6. **Retention policies** for `parameter-staging` and `pending-promotions` (after-applied data retention, GC cadence, archival rules).

  7. **Importer phasing** — ship all 6 in v1, or stage subset (e.g., SemCor + OntoNotes + FrameNet-extension first; VerbNet + GlossTag in v1.5)? Either is acceptable; staging reduces v1 effort.

  8. **Cross-system mappings curation tool** — admin UI / file format / batch-import pattern for hand-curated DOLCE↔WordNet mappings.

  9. **Layer naming** — `theoretical` and `empirical` are recommended but L2 chat may prefer alternatives (`formal` / `observational`, `definitional` / `corpus-based`, etc.).

  10. **Schema validation strictness** — which of the new role-graphs ship with `strict=True` schemas? Recommended: all new role-graphs strict to catch authorial mistakes early.

  11. **Edge multiplicity in empirical layer** — same sense pair can have multiple edges (e.g., `COOCCURS_SAMESENT` + `SUBJECT_OF` + `AGENT_OF`). Confirm edge multiplicity handled correctly by Cypher writes / loads (per L1 invariants this is supported but worth verifying for the empirical-layer query patterns).

---

## 10. Phasing recommendation

Suggesting an order that minimizes risk:

  1. **Phase A — Schema layer declarations.** Smallest, additive. Requires L1 schema-layer mechanism. OewnImporter extension to declare existing edges as `theoretical` layer. New empirical-layer edge type vocabulary added to schema (no edges yet). Lays groundwork for Phase B.
  2. **Phase B — Audited Learning role-graphs.** `parameter-staging`, `pending-promotions`, `capacity-gaps`. Independent of L1 changes; can ship in parallel with Phase A. Required by L4's ALS implementation.
  3. **Phase C — Importers.** SemCorImporter + OntoNotesImporter + SemLinkImporter first (the largest gold-corpus stack). VerbNetImporter + GlossTagImporter + FrameNetImporter extension follow. Each importer is independent.
  4. **Phase D — Cross-system mappings.** Requires L1 InterGraphEdge primitive. Hand-curated DOLCE↔WordNet loaded as initial set; curation tool for admin extension.

Phases A + B can ship before L1 InterGraphEdge lands, since they only depend on the L1 schema-layer mechanism. Phase D blocks on InterGraphEdge.

---

## 11. What this does NOT change

To bound scope:

  - **Existing role-graphs untouched.** Lexicon, ontology, concepts, alignments, memories, problem-trace, capacity-state retain existing semantics. Lexicon gains layer declarations + new edge types only.
  - **OEWN importer logic unchanged.** Just declares existing edge types as `theoretical` layer.
  - **DolceImporter, AlignmentsImporter, original FrameNetImporter unchanged.** New importers / extensions are sibling additions.
  - **`ref:*` property mechanism (ADR-0016) unchanged.** Per L1 handoff, `ref:*` continues to work for cross-graph node references where typed-edge structure isn't needed.
  - **KL Local→Global proxy mechanism (L2 §7 I7) unchanged.** Per L1 handoff, possible v2+ migration to InterGraphEdge; not in scope here.
  - **Versioning, promotion, similarity-report machinery (L2 §12.5) unchanged.** All new role-graphs follow existing versioned-graph + active-pointer pattern.
  - **Schema-extension API unchanged** beyond the new layer-declaration methods L1 adds.

---

## 12. Summary checklist for the L2 chat

When this handoff is implemented, L2 should have:

  - [ ] Lexicon schema declaring `theoretical` and `empirical` layers with all edge types assigned.
  - [ ] Five new importers + one importer extension, each independent with fail-fast prerequisites.
  - [ ] Shared utility libraries (`sense_iri_align`, `class_generalize`, `metric_compute`, `mwe_segment`).
  - [ ] Cross-system mappings as InterGraphEdges (DOLCE↔WordNet hand-curated subset).
  - [ ] Three new role-graphs: `parameter-staging` (Local), `pending-promotions` (Local + Global), `capacity-gaps` (Global).
  - [ ] Updated `task-patterns` role-graph schema (sub-shape recognizers; admin-authored v1 set).
  - [ ] `promoted-pipelines` writer-side updated to flow through ALS audit.
  - [ ] `learned-parameters` decision (single or split) documented.
  - [ ] L2 §12 spec updated to remove `sense-correlations` row.
  - [ ] Coordinated update to `layer4_intelligence_design_notes.md` removing `sense-correlations` references.

---

**End of handoff.**

When L2 design settles these changes, please update this document or write a follow-up handoff so the WSD design chat can absorb the final API.
