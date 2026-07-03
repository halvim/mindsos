"""MindsOS Knowledge Layer — Phase 14 surface.

L2 IRI vocabulary + REF_TYPES + role constants + ref-key helpers
(Phase 12) + the 8 role-graph schemas + the alignment parametric
schema + ``schema_for_role`` dispatch (Phase 13) + ``KnowledgeLayer``
class + ``MetagraphView`` read-only wrapper + ``ensure_*_role_graph``
bootstrap helpers + ``install_local_metagraph`` / ``extract_local_
metagraph`` hooks per ADR-0042 + §amendment-1 (Phase 14). Pure
library; no L1 mutation in KL methods, no metagraph persistence, no
file-I/O — ADR-0043 honoured. KL writes are relocated to L3
capacities per ADR-0138 Proposed (honoured by absence in Phase 14
per PB-6; ADR not flipped Accepted).

Phase 12 shipped:

* IRI builders covering ADR-0045: 7 seed-role builders ported from
  the v3 `mindsos_knowledge/identifiers.py` (DOLCE / OEWN / FrameNet)
  plus 7 upper-layer builders (`pipeline_iri`, `pipeline_step_iri`,
  `task_pattern_iri`, `subgoal_template_iri`, `episode_iri`,
  `memory_composite_iri`, `problem_trace_iri`, `capacity_snapshot_iri`).
  Per ADR-0044 §amendment-3 + ADR-0146 §amendment-3 (Phase 39), the
  pre-rename upper-layer memory builder was split into two minters
  under multi-NodeType dispatch (`ROLE_EPISODIC_MEMORIES` × {Episode,
  Memory}); pre-rename identifier-surface details are recorded in the
  ADR amendments + Phase 39 design log.
* `alignment_role(role_a, role_b)` — graph-name helper for alignment
  metagraphs. NOT a version-qualified IRI (PB-4 lock).
* `parse_iri` + `is_version_qualified_iri` + `ParsedIri` — table-driven
  decomposition keyed on `_PREFIXES` + `_KINDS_PER_ROLE`.
* `REF_TYPES` frozenset + extension-recipe per ADR-0047.
* Ref-key helpers: `global_ref_key`, `local_ref_key`, `REF_TYPE_KEY`.
* Role constants: 3 seed + 5 upper-layer + 3 frozensets.
* Exceptions: `KnowledgeError` (base) + `RefFormatError`.

Phase 13 added:

* 9 schema builders under `mindsos_knowledge.schemas`:
  4 seed (`ontology` / `lexicon` / `concepts` / `alignment` —
  v3 ports with ontology HyperEdgeType lift) + 5 upper-layer
  (`promoted_pipelines` / `task_patterns` / `episodic_memories` /
  `problem_trace` / `capacity_state` — NET-NEW at strict=False;
  `episodic_memories` renamed from `memories` at Phase 39 per
  ADR-0044 §am-3 + ADR-0150 §am-4).
* `schema_for_role(role)` dispatch function — handles the
  alignment-prefix branch and raises `UnknownRoleError` on miss.
* `UnknownRoleError` exception class.

Phase 14 adds:

* `KnowledgeLayer` class — entry point with Global + per-user Local
  lifecycle. Constructor parameter for Global per ADR-0042
  §amendment-1 (Phase 14 PB-7); `bootstrap()` classmethod for fresh
  install. No write API (ADR-0138 Proposed honoured per PB-6).
* `MetagraphView` — whitelist read-only wrapper (PB-3); no
  `follow_ref` overlay (PB-10).
* `ensure_global_role_graph` / `ensure_local_role_graph` — module-
  level bootstrap helpers (PB-4 two-method split + ADR-0044
  enforcement). Alignment is Global-only at v1 per ADR-0150
  §amendment-1 (PB-8).
* `install_local_metagraph` / `extract_local_metagraph` hooks per
  ADR-0042 (PB-5). Lazy `local_metagraph(user_id)` auto-creates
  with `episodic_memories` + `capacity-state` ensured (PB-9;
  Phase 39 rename per ADR-0044 §am-3).
* `AlreadyInstalledError` + `NotInstalledError` exception classes.

Phase 36 adds:

* `validators.py` semantic-invariant module — 5 pure-function
  validators + `ValidationResult` dataclass + `_VALIDATORS_BY_ROLE`
  per-role adapter registry (2 entries: episodic_memories +
  problem-trace; Phase 39 rename per ADR-0044 §am-3).
  ADR-0139 flipped Proposed → Accepted via §amendment-1.
* `SemanticValidationError` — raised by L3 write capacities on
  validator failure; carries `.result: ValidationResult`.
* `KLWriteHandle.validate_node(...)` body wired via the per-role
  adapter; `validate_xref(...)` STAYS raising
  `WriteHandleNotWiredError` (deferred per-flow alongside the first
  XRef-writing capacity per ADR-0139 §amendment-1 clause 3 carry-
  forward).

Deferred to later phases:

* Per-edge alignment-anchor IRI builder → Phase 15 (Phase 14 PB-1).
* MetagraphSchema scanner → Phase 15 (Phase 14 PB-1).
* `follow_ref` cross-metagraph helper → Phase 25 / first L3 capacity.
* `step()` `version=` kwarg → VACATED at Phase 17 retirement
  (2026-05-20) per ADR-0150 §amendment-3 (one graph per role; no
  active-version dispatch). Phase 14 PB-15 closure recorded in
  `confirmation_docs/PHASE_14_DESIGN_LOG.md`.
* CLI verbs over KL → Phase 14 PB-13 partially closed at Phase 17
  retirement (`mindsos knowledge versions` shipped;
  `active-version` dropped per PB-15 vacuum).
* Importers (DOLCE / OEWN / FrameNet / Alignments) → Phase 15.
* Promotion machinery → Phase 24 (Phase 16 PB-1c reframe).
* Versioning enumerator → SHIPPED at Phase 17 retirement
  (`MetagraphView.versions_in_role` + `mindsos knowledge versions`
  CLI verb). PROMOTED-breadcrumb reader → Phase 33 per ADR-0146
  symmetric write contract (Phase 16's `list_candidates` exclude
  is the only L2 reader needed before then).
* REF_TYPES parity test against L3 → Phase 27 (ADR-0067).
* Per-builder inverse field helpers → per-consumer phase.
* Schema strict-tightening (per-role) → first-consumer phase after
  the 2-week-no-edit observation period per ADR-0149.
* `KL.bootstrap` relocation to `mindsos_server` per ADR-0140 → Phase 37.
"""

from __future__ import annotations

__version__ = "0.0.0+phase50"

from .bootstrap import (
    ensure_global_role_graph,
    ensure_local_role_graph,
)
from .exceptions import (
    AlreadyInstalledError,
    KnowledgeError,
    MutationDisciplineError,
    NotInstalledError,
    RefFormatError,
    SemanticValidationError,
    UnknownRoleError,
)
from .knowledge_layer import KnowledgeLayer
from .metagraph_view import MetagraphView
from .validators import ValidationResult
from .write_handle import KLWriteHandle
from .identifiers import (
    ALL_ROLES,
    REF_TYPE_KEY,
    REF_TYPES,
    ROLE_CAPACITY_GAPS,
    ROLE_CAPACITY_STATE,
    ROLE_CONCEPTS,
    ROLE_EPISODIC_MEMORIES,
    ROLE_INSTALLED_SKILLS,
    ROLE_LEARNED_PARAMETERS,
    ROLE_LEXICON,
    ROLE_ONTOLOGY,
    ROLE_PARAMETER_STAGING,
    ROLE_PENDING_PROMOTIONS,
    ROLE_PROBLEM_TRACE,
    ROLE_PROMOTED_PIPELINES,
    ROLE_SUBMINDS,
    ROLE_TASK_PATTERNS,
    SEED_ROLES,
    UPPER_LAYER_ROLES,
    ParsedIri,
    alignment_role,
    capacity_gap_iri,
    capacity_snapshot_iri,
    dolce_iri,
    framenet_fe_iri,
    framenet_frame_iri,
    framenet_lu_iri,
    global_ref_key,
    episode_iri,
    is_version_qualified_iri,
    learned_parameter_iri,
    local_ref_key,
    memory_composite_iri,
    oewn_lemma_iri,
    oewn_sense_iri,
    oewn_synset_iri,
    parse_iri,
    pending_promotion_iri,
    pipeline_iri,
    pipeline_step_iri,
    problem_trace_iri,
    skill_install_record_iri,
    staged_evidence_iri,
    subgoal_template_iri,
    submind_definition_iri,
    task_pattern_iri,
)

from .schemas import (
    _ROLE_SCHEMA_BUILDERS,
    Discipline,
    L2Schema,
    StorageMode,
    build_alignment_schema,
    build_capacity_gaps_schema,
    build_capacity_state_schema,
    build_concepts_schema,
    build_episodic_memories_schema,
    build_installed_skills_schema,
    build_learned_parameters_schema,
    build_lexicon_schema,
    build_ontology_schema,
    build_parameter_staging_schema,
    build_pending_promotions_schema,
    build_problem_trace_schema,
    build_promoted_pipelines_schema,
    build_subminds_schema,
    build_task_patterns_schema,
    schema_for_role,
)

__all__ = [
    # ── version ────────────────────────────────────────────────────
    "__version__",
    # ── exceptions ─────────────────────────────────────────────────
    "KnowledgeError",
    "RefFormatError",
    "UnknownRoleError",
    "AlreadyInstalledError",
    "NotInstalledError",
    "SemanticValidationError",
    "MutationDisciplineError",
    # ── role constants ─────────────────────────────────────────────
    "ROLE_ONTOLOGY",
    "ROLE_LEXICON",
    "ROLE_CONCEPTS",
    "ROLE_PROMOTED_PIPELINES",
    "ROLE_TASK_PATTERNS",
    "ROLE_EPISODIC_MEMORIES",
    "ROLE_PROBLEM_TRACE",
    "ROLE_CAPACITY_STATE",
    # Phase 43 role-graphs (ADR-0150 §am-5).
    "ROLE_PARAMETER_STAGING",
    "ROLE_PENDING_PROMOTIONS",
    "ROLE_CAPACITY_GAPS",
    "ROLE_LEARNED_PARAMETERS",
    # Phase 50 role-graph (ADR-0150 §am-6).
    "ROLE_INSTALLED_SKILLS",
    # feat/subminds role-graph (ADR-0150 §am-7).
    "ROLE_SUBMINDS",
    "SEED_ROLES",
    "UPPER_LAYER_ROLES",
    "ALL_ROLES",
    # ── alignment graph-name helper (NOT a version-qualified IRI) ──
    "alignment_role",
    # ── seed-role IRI builders (v3) ────────────────────────────────
    "dolce_iri",
    "oewn_synset_iri",
    "oewn_sense_iri",
    "oewn_lemma_iri",
    "framenet_frame_iri",
    "framenet_lu_iri",
    "framenet_fe_iri",
    # ── upper-layer IRI builders (ADR-0045) ────────────────────────
    "pipeline_iri",
    "pipeline_step_iri",
    "task_pattern_iri",
    "subgoal_template_iri",
    "episode_iri",
    "memory_composite_iri",
    "problem_trace_iri",
    "capacity_snapshot_iri",
    # Phase 43 IRI builders (ADR-0150 §am-5).
    "staged_evidence_iri",
    "pending_promotion_iri",
    "capacity_gap_iri",
    "learned_parameter_iri",
    # Phase 50 IRI builder (ADR-0150 §am-6).
    "skill_install_record_iri",
    # feat/subminds IRI builder (ADR-0150 §am-7).
    "submind_definition_iri",
    # ── parser ─────────────────────────────────────────────────────
    "ParsedIri",
    "parse_iri",
    "is_version_qualified_iri",
    # ── ref-key helpers ────────────────────────────────────────────
    "global_ref_key",
    "local_ref_key",
    "REF_TYPE_KEY",
    "REF_TYPES",
    # ── schemas (Phase 13) ─────────────────────────────────────────
    "build_ontology_schema",
    "build_lexicon_schema",
    "build_concepts_schema",
    "build_alignment_schema",
    "build_promoted_pipelines_schema",
    "build_task_patterns_schema",
    "build_episodic_memories_schema",
    "build_problem_trace_schema",
    "build_capacity_state_schema",
    # Phase 43 builders (ADR-0150 §am-5).
    "build_parameter_staging_schema",
    "build_pending_promotions_schema",
    "build_capacity_gaps_schema",
    "build_learned_parameters_schema",
    # Phase 50 builder (ADR-0150 §am-6).
    "build_installed_skills_schema",
    # feat/subminds builder (ADR-0150 §am-7).
    "build_subminds_schema",
    "schema_for_role",
    "_ROLE_SCHEMA_BUILDERS",
    # ── L2-private vocabulary (Phase 43 — ADR-0153 §am-1 + ADR-0151) ─
    "Discipline",
    "L2Schema",
    "StorageMode",
    # ── KL (Phase 14) ──────────────────────────────────────────────
    "KnowledgeLayer",
    "MetagraphView",
    "ensure_global_role_graph",
    "ensure_local_role_graph",
    # ── KLWriteHandle (Phase 33; ADR-0143 stub-only — ADR-0146 §am1) ─
    "KLWriteHandle",
    # ── Validators (Phase 36; ADR-0139 Accepted) ───────────────────
    "ValidationResult",
]
