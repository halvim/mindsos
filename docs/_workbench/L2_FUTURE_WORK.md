# L2 Knowledge — Future Discussions & Work

**Date:** 2026-06-01 (L2 chat closure)
**Status:** Living index. L2 chat closure (2026-06-01) marked items closed/dissolved/routed below.

---

## 1. Role-graphs not yet shipped

| # | Item | Source | Owner chat | Status |
|---|---|---|---|---|
| L2-1 | ~~`sense-correlations` role-graph~~ | R0-PB-9; FOL B10; WSD `coordinated_change_L2` §6 | — | **CLOSED — withdrawn per L2_CHAT_DECISIONS D-L2-2** (data lives in lexicon empirical layer; ALS subsystem #8 label preserved). |
| L2-2 | `learned-parameters` role-graph — single v1, opaque `parameter_set_iri` | Chat A R3 D9.5 + R5 D28 | L2 chat (ratified); FOL chat for 3-way split | **CLOSED v1 — single role-graph shipped per L2_CHAT_DECISIONS D-L2-15** (ADR-0152 §6). FOL chat re-opens if split needed. |
| L2-3 | `parameter-staging` role-graph (Local) | WSD `coordinated_change_L2` §6.1 | L2 chat | **CLOSED — shipped per L2_CHAT_DECISIONS D-L2-11** (ADR-0152 §3). |
| L2-4 | `pending-promotions` role-graph (Local + Global) | WSD `coordinated_change_L2` §6.2 | L2 chat | **CLOSED — shipped per L2_CHAT_DECISIONS D-L2-13** (ADR-0152 §4). |
| L2-5 | `capacity-gaps` role-graph (Global) | WSD `coordinated_change_L2` §6.3 | L2 chat | **CLOSED — shipped per L2_CHAT_DECISIONS D-L2-14** (ADR-0152 §5). |
| L2-6 | `world-axioms` role-graph | WSD `pending_adrs/L2_knowledge.md` §A.1 | WSD installation chat | **Open** — not added in ADR-0150 §amendment-4; WSD chat owns. |
| L2-7 | `training-runs` role-graph | FOL pushback #5 | FOL chat | **Open** — deferred per Chat A R5 D29; not in ADR-0150 §amendment-4. |
| L2-8 | `fol-rules` + `fol-ledger` role-graphs | FOL HANDOFF_latest §2.1 + B3 | FOL installation chat | **Open** — not in ADR-0150 §amendment-4. |
| **L2-28** | **`episodic_memories` role-graph (rename from `memories`; Episode + Memory entry types)** | Chat B D-B48 | L2 chat | **CLOSED — shipped per L2_CHAT_DECISIONS D-L2-16 + D-L2-17** (ADR-0044 §amendment-3 + ADR-0150 §amendment-4 + ADR-0152 §7). |

---

## 2. Phase 38 carry-forwards (L2-bucket)

| # | Item | Source | Owner chat | Status |
|---|---|---|---|---|
| L2-9 | `handle.validate_xref` body (ADR-0139 §am-1 clause 3) | PHASE_38_DESIGN_LOG §4 #8 | Maintenance chat or Chat C plan | **Open** |
| L2-10 | 4 unconsumed L2 validators — `validate_local_to_global_ref`, `validate_alignment_role_naming`, `validate_ref_type`, `validate_promotion_candidate` | PHASE_38_DESIGN_LOG §4 #9 | Maintenance chat | **Partially scoped** — `validate_alignment_role_naming` consumer is now ADR-0154 (canonical form check); `validate_promotion_candidate` consumer is ADR-0152 §4; `validate_mutation_discipline` ADDED as 5th L2 validator per ADR-0153 §3. |

---

## 3. Naming reconciliation

| # | Item | Source | Owner chat | Status |
|---|---|---|---|---|
| L2-11 | ~~Alignment role-graph naming — 3 conventions in flight~~ | HANDOFF §6.3 | L2 chat | **CLOSED — `alignment:<a>:<b>` colon canonical per L2_CHAT_DECISIONS D-L2-1 + ADR-0154**. Phase 36 test fix + `identifiers.py:303` one-line fix tracked as maintenance carry-forward. DWF chat inherits. |

---

## 4. DWF-driven additions (knowledge acquisition)

| # | Item | Source | Owner chat | Status |
|---|---|---|---|---|
| L2-12 | `AlignmentsImporter` body unshipped | DWF analysis | DWF installation chat (PRIORITY) | **Open** — DWF inherits ADR-0154 canonical form. |
| L2-13 | 6 new importers — SemCor, OntoNotes, VerbNet, SemLink, GlossTag, FrameNet-extended | WSD `coordinated_change_L2` | WSD installation chat | **Open** |

---

## 5. WSD-driven L2 additions

| # | Item | Source | Owner chat | Status |
|---|---|---|---|---|
| L2-14 | Lexicon "theoretical layers" via Schema-declared layers (depends on L1-2) | WSD C-L2-1; `coordinated_change_L2` §3 | L1/L3 reframe chat (gates), then WSD installation | **Open** — gated on L1/L3 reframe close. |
| L2-15 | Empirical-layer edge vocabulary | WSD `coordinated_change_L2` | WSD installation chat | **Open** |
| L2-16 | Cross-system mappings as InterGraphEdges (depends on L1-6 naming) | WSD `coordinated_change_L2` | WSD installation chat | **Open** — gated on L1 InterGraphEdge naming reconciliation. |

---

## 6. FOL-driven L2 additions

| # | Item | Source | Owner chat | Status |
|---|---|---|---|---|
| L2-17 | Parallel foundational ontologies (BFO / UFO / YAMATO) — currently DOLCE-only locked at Phase 15a | FOL pushback #11 | FOL installation chat | **Open** |

---

## 7. UC-surfaced L2 schema decisions (routed per Chat A Q2)

| # | Item | Source | Owner chat | Status |
|---|---|---|---|---|
| L2-18 | ~~Path-mutability decision~~ | UC-WSD-16; CHAT_A_L4_BASELINE D47 | L2 chat | **CLOSED — duplicate of L2-27**. |
| L2-19 | `domain_tag` on lexicon edges + per-domain class-generalization weights | UC-WSD-10; CHAT_A_L4_BASELINE D43 | L2 chat | **CLOSED — ratified per L2_CHAT_DECISIONS D-L2-20**. Domain-keyed entries in ALS subsystem #7; v1 baseline vocab. |
| L2-20 | Paths-of-paths value-typed inlined-at-registration schema | UC-WSD-16 | L2 chat | **CLOSED — ratified** matches WSD `pending_adrs` §A.2; `edge_sequence` immutable content per ADR-0152 §1. |
| L2-21 | Module glossary + project-specific code knowledge | UC-CODE-1/2; UC-X-1 | Code-skill installation chat | **Open** — routed out of L2 chat. |
| L2-22 | ~~Memory schema extension for per-segment provenance~~ | UC-WSD-15; CHAT_A_L4_BASELINE D45 | — | **DISSOLVED per L2_CHAT_DECISIONS D-L2-21** — per-segment provenance lives in Chat B's frozen MM (intelligence-MM ReplanRecord + chain artifacts); L2 owns container, not internals. |
| L2-23 | `parameter-staging` + `pending-promotions` schemas + `episodic_memories` schema | Chat A R3 D9.5 + Chat B D-B48 | L2 chat | **CLOSED — shipped per ADR-0152 §3 + §4 + §7**. |
| L2-24 | Bootstrap-importer suite checklist + topological order via `applies_after` | Chat A R3 Gap 4 + D51 + Chat B D-B49 | L2 chat | **CLOSED — order locked per L2_CHAT_DECISIONS D-L2-19**. 14-step v1 order; ADR-0152 + ADR-0150 §amendment-4 enumerate role-graphs covered. WSD installation chat ships per-importer bodies. |
| L2-25 | `promoted-pipelines` schema v2 — 5-state status + paired_pipelines + serves_task_types (latter eliminated) | Chat A R3 + PB-R3-21/22 + R4 | L2 chat | **CLOSED v2 PARTIAL** — ADR-0152 §1; `confidence` removed (ADR-0094 §amendment-1); `serves_task_types` cache eliminated (L2_CHAT_DECISIONS D-L2-7); HAS_STEP shape deferred to L1/L3 reframe close (§amendment-1 of ADR-0152 follows). |
| L2-26 | `task-patterns` schema v2 gains `relevant_hints`, `mapping_confidence_threshold`, `sufficient_predicate_iri`, `domain` | Chat A R3 hint system + R5 D43 | L2 chat | **CLOSED — flat 9-field schema shipped per L2_CHAT_DECISIONS D-L2-10** (ADR-0152 §2). |
| L2-27 | L2 path-mutability decision (D47) | Chat A R6 D47 | L2 chat | **CLOSED — per-role-graph `mutation_discipline` per L2_CHAT_DECISIONS D-L2-3 + D-L2-4 + D-L2-5** (ADR-0153). Reference-stability wording supersedes "immutability." |

---

## 8. Open coordination questions

| # | Question | Source | Status |
|---|---|---|---|
| L2-Q1 | If FOL #4 (L2-2 split) is accepted, WSD ALS subsystem registration's `parameter_set_iri` must encode which of 3 role-graphs holds the parameters. | Chat A reconciliation point | **RESOLVED for v1 per L2_CHAT_DECISIONS D-L2-12 — opaque IRI**. FOL chat may re-open if split lands. |
| L2-Q2 | ADR-0150 §am-1 role-graph bound expansion — single bulk ADR or many small? | Chat A or Chat C | **RESOLVED — single bulk ADR-0150 §amendment-4 per L2_CHAT_DECISIONS D-L2-26 (PB-D)**. |

---

## 9. New items opened by L2 chat (carry-forwards)

| # | Item | Source | Owner chat |
|---|---|---|---|
| **L2-29** | **`Schema.mutation_discipline` field implementation** — `mindsos_core.Schema` amendment to declare discipline at build time. | ADR-0153 §6 | Chat C plan-authoring (sequences impl phase) |
| **L2-30** | **L4 startup invariant: `KnowledgeLayer.bootstrap()` builds discipline dispatch table**. | ADR-0153 §2 | Chat C plan-authoring |
| **L2-31** | **`validate_mutation_discipline` validator implementation** + new `MutationDisciplineError` exception. | ADR-0153 §3 + §5 | Chat C plan-authoring (Phase 38 carry-forward #9 absorbs) |
| **L2-32** | **Per-field `CONTENT_FIELDS` / `METADATA_FIELDS` frozenset declarations on shipped Phase 13 schemas** — `promoted_pipelines.py` + `task_patterns.py` + post-rename `episodic_memories.py`. | ADR-0152 §1 + §2 + §7; ADR-0153 §3 | Chat C plan-authoring |
| **L2-33** | **`storage_mode` field declarations on schemas with large-payload fields** — `episodic_memories.Episode.task_input_ref`, `learned-parameters.LearnedParameter.value`. | ADR-0151 | Chat C plan-authoring |
| **L2-34** | **`memories` → `episodic_memories` atomic rename PR scope** — **CLOSED — shipped Phase 39 (2026-06-02).** All identifier surface advanced; legacy EdgeType + property frozenset drops landed per PB-R1-A/B (Phase 43 re-adds on Episode atomically with the full D-L2-17 ship). `tools/check_rename_state.py` detector ships. Cumulative gate clean at 3501 passed. | ADR-0044 §amendment-3 + L2_CHAT_DECISIONS D-L2-16 | **CLOSED — shipped Phase 39** |
| **L2-35** | **`alignment:<a>:<b>` shipped-code reconciliation** — **CLOSED — shipped Phase 39 (2026-06-02).** Separator switched from `<->` to `:` across `identifiers.py:303` body + lines 297/353 docstrings + `tests/phase_36/test_validators.py` body. | ADR-0154 + L2_CHAT_DECISIONS D-L2-1 | **CLOSED — shipped Phase 39** |
| **L2-36** | **L3 pipeline-finder task-pattern index** — runtime cache rebuilds `serves_task_types` lookup from `task-patterns.paired_pipelines`; status filter (`default status="active"`). | L2_CHAT_DECISIONS D-L2-7 + D-L2-8 | L1/L3 reframe chat or WSD installation |
| **L2-37** | **Bootstrap importer `applies_after: frozenset[IRI]` field on registration contract**. | L2_CHAT_DECISIONS D-L2-19 | Chat C plan-authoring |
| **L2-38** | **ADR-0152 §amendment-1 to lock `HAS_STEP` shape** post-L1/L3-reframe close. | L2_CHAT_DECISIONS D-L2-6; D38 | L1/L3 reframe chat closure trigger |
| **L2-39** | **`EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` audit constant + new capability distinct from generic `READ_OTHER_LOCAL`**. | L2_CHAT_DECISIONS D-L2-23 (PB-H) | L0 chat |
| **L2-40** | **`promoted-pipelines.confidence` maintenance migrator** — strip field from any shipped Local-Pipeline records (v1 production has none). | ADR-0094 §amendment-1; L2_CHAT_DECISIONS D-L2-24 | Chat C plan-authoring (absorbed into v2 schema deploy phase) |
| **L2-41** | **KL public API `kl.read_at_version(iri, version)` + `kl.retire_version(role, version)` hook** triggers lazy-inline marker for `episodic_memories`. | Chat B cascade + L2_CHAT_DECISIONS D-L2-18 | L0 chat (impl); L2 ratified API shape |

---

## 10. Items dissolved or moved into L0 / L3 / Chat C

| # | Item | Disposition |
|---|---|---|
| L2-22 | Memory schema extension for per-segment provenance | **Dissolved** — Chat B owns internals. |
| Chat A L4-12 (per-task-pattern mapping-confidence threshold) | **Absorbed into L2-26** (now `mapping_confidence_threshold` field on TaskPattern per ADR-0152 §2). |
| Chat A L0-12 (L0 admin-tooling library for Global ALS cycle) | Stays at L0 chat; L2 ships the `pending-promotions` role-graph (Global) that the cycle reads/writes. |

---

*L2 chat closed 2026-06-01. Carry-forward items L2-29 through L2-41 inherited by Chat C plan-authoring / L0 chat / WSD installation / L1/L3 reframe chat per Owner column.*

---

## 11. Chat C closure routing (2026-06-02)

Chat C plan-authoring closed 2026-06-02 (`confirmation_docs/POST_PHASE_38_PHASE_MAP.md`). Routing of open L2 items + final placement of L2-29 through L2-41:

| Item | Routed to | Notes |
|---|---|---|
| L2-6 (`world-axioms` role-graph) | **WSD_INSTALLATION_CHAT** | Per `projects/wsd/FUTURE_CHAT_PROMPT.md` §E. |
| L2-7 (`training-runs` role-graph) | **FOL_INSTALLATION_CHAT** | Per Chat A R5 D29 defer. |
| L2-8 (`fol-rules` + `fol-ledger`) | **FOL_INSTALLATION_CHAT** | — |
| L2-9 (`handle.validate_xref` body) | **Stream A (item A5)** or first XRef-writing capacity in WSD installation | — |
| L2-10 (1 remaining unconsumed validator) | **Stream A (item A6)** or Phase 44 absorb | `validate_local_to_global_ref` only; other 3 absorbed. |
| L2-12 (`AlignmentsImporter` body) | **DWF_INSTALLATION_CHAT** | PRIORITY per `projects/dwf_mapping/FUTURE_CHAT_PROMPT.md`. |
| L2-13 (6 new importers) | **WSD_INSTALLATION_CHAT** | — |
| L2-14 (lexicon theoretical layers) | **WSD_INSTALLATION_CHAT** | Gated on L1-2 (future L1 chat); WSD installation drives. |
| L2-15 (empirical-layer edge vocabulary) | **WSD_INSTALLATION_CHAT** | — |
| L2-16 (cross-system mappings as IntergraphEdges) | **WSD_INSTALLATION_CHAT** | L1 naming closed (IntergraphEdge shipped form). |
| L2-17 (parallel foundational ontologies) | **FOL_INSTALLATION_CHAT** | — |
| L2-21 (module glossary + code knowledge) | **CODE_SKILL_INSTALLATION_CHAT** | — |
| L2-29 (mutation_discipline field on schemas) | **CLOSED — shipped Phase 43 (2026-06-03)** | Reversed from L1 Schema amendment framing to L2Schema(Schema) subclass at `mindsos_knowledge.schemas._base.L2Schema` per ADR-0153 §amendment-1 (R0 N4 probe + PB-43-6). L1 `mindsos_core.Schema` unchanged. |
| L2-30 (`KL.bootstrap` discipline dispatch) | **CLOSED — shipped Phase 43 (2026-06-03)** | `KnowledgeLayer.discipline_for(metagraph, role)` + lazy per-Metagraph dispatch cache per ADR-0153 §2 startup invariant. |
| L2-31 (`validate_mutation_discipline` validator) | **CLOSED — shipped Phase 43 (2026-06-03)** | Pure function in `mindsos_knowledge/validators.py` per ADR-0153 §3 + §5 (`MutationDisciplineError`). Plus `validate_partition_invariant` companion. |
| L2-32 (`CONTENT_FIELDS`/`METADATA_FIELDS` frozensets) | **CLOSED — shipped Phase 43 (2026-06-03)** | Pipeline (5/11) + TaskPattern (5/8) + ProblemTraceEntry (7/0) + Episode (6/0) + Memory (1/3) partitions per ADR-0152 §1/§2/§7 + ADR-0153 §3. |
| L2-33 (`storage_mode` field declarations) | **CLOSED — shipped Phase 43 (2026-06-03)** | Per-NodeType placement (not per-role-graph; NPB8-1). `STORAGE_MODE_FIELDS = {"LearnedParameter": {"value"}}` in `learned_parameters.py` per ADR-0151 + ADR-0152 §6. `INLINE` / `FALKOR_BLOB` / `BLOB_REF` enum in `_base.py`. |
| L2-34 (`memories`→`episodic_memories` atomic rename PR) | **CLOSED — shipped Phase 39 (2026-06-02)** | Rail A first ship; rename atomic; detector tool replaces migration script per PB-8. |
| L2-35 (`alignment:<a>:<b>` shipped-code reconciliation) | **CLOSED — shipped Phase 39 (2026-06-02)** | Bundled into Phase 39 PR per IL-7. Separator `:` shipped. |
| L2-36 (L3 pipeline-finder task-pattern index) | **WSD_INSTALLATION_CHAT** | Per D-L2-7 D-L2-8 cache lives in L3. |
| L2-37(field) (`applies_after` bootstrap field) | **CLOSED — shipped Phase 43 (2026-06-03)** | Field-only at Phase 43 per NPB11-1; `_APPLIES_AFTER_BY_ROLE` 12 declarations + `applies_after` kwarg on both `ensure_*_role_graph` functions. Soft edge `episodic_memories ← {task-patterns}` per NPB6-6. |
| L2-37(consumer) (Kahn topological-sort scheduler) | **Phase 44** | Per L2-37 split. Phase 44 L0 substrate chat scope. |
| L2-38 (ADR-0152 §am-1 for `HAS_STEP` shape) | **Closed via Phase 42 X3** — bipartite picked; `HAS_STEP` stays Phase 13 form. No §am-1 needed. | — |
| L2-39 (`EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` constant + capability) | **Phase 44** | Per L0_SUBSTRATE_CHAT scope. |
| L2-40 (`promoted-pipelines.confidence` migrator) | **CLOSED — shipped Phase 43 (2026-06-03)** | Form changed from migrator to detector per R0 PB-43-10 + ADR-0094 §am-1 in-place edit. `tools/check_phase_43_confidence_state.py` ships; v1 production state empty (Chat C migration-script discipline = wipe-and-rebootstrap, not in-place strip). |
| L2-41 (KL `read_at_version` + `retire_version`) | **Phase 44** | Per L0_SUBSTRATE_CHAT scope. |
| L2-Q1 (FOL #4 parameter_set_iri encoding) | RESOLVED at D-L2-12 opaque v1; FOL chat may re-litigate. | — |
| L2-Q2 (ADR-0150 §am-N bulk-vs-many) | RESOLVED at D-L2-26 + refined by Chat C IL-3 split (§am-4 Phase 39; §am-5 Phase 43). | — |

---

*End of L2_FUTURE_WORK.md. Last updated 2026-06-03 post Phase 43 ship — L2-29/30/31/32/33/37(field)/40 closed; L2-37(consumer) + L2-39 + L2-41 routed to Phase 44.*
