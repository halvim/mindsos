"""MindsOS Knowledge Layer — Phase 13 surface.

L2 IRI vocabulary + REF_TYPES + role constants + ref-key helpers
(Phase 12) + the 8 role-graph schemas + the alignment parametric
schema + ``schema_for_role`` dispatch (Phase 13). Pure library; no
L1 mutation, no metagraph, no persistence. KL writes are relocated to
L3 capacities per ADR M1 / L2 redesign locks 2026-04-27.

Phase 12 shipped:

* 14 IRI builders covering ADR-0045: 7 seed-role builders ported from
  the v3 `mindsos_knowledge/identifiers.py` (DOLCE / OEWN / FrameNet)
  plus 7 upper-layer builders (`pipeline_iri`, `pipeline_step_iri`,
  `task_pattern_iri`, `subgoal_template_iri`, `memory_iri`,
  `problem_trace_iri`, `capacity_snapshot_iri`).
* `alignment_role(role_a, role_b)` — graph-name helper for alignment
  metagraphs. NOT a version-qualified IRI (PB-4 lock).
* `parse_iri` + `is_version_qualified_iri` + `ParsedIri` — table-driven
  decomposition keyed on `_PREFIXES` + `_KINDS_PER_ROLE`.
* `REF_TYPES` frozenset + extension-recipe per ADR-0047.
* Ref-key helpers: `global_ref_key`, `local_ref_key`, `REF_TYPE_KEY`.
* Role constants: 3 seed + 5 upper-layer + 3 frozensets.
* Exceptions: `KnowledgeError` (base) + `RefFormatError`.

Phase 13 adds:

* 9 schema builders under `mindsos_knowledge.schemas`:
  4 seed (`ontology` / `lexicon` / `concepts` / `alignment` —
  v3 ports with ontology HyperEdgeType lift) + 5 upper-layer
  (`promoted_pipelines` / `task_patterns` / `memories` /
  `problem_trace` / `capacity_state` — NET-NEW at strict=False).
* `schema_for_role(role)` dispatch function — handles the
  alignment-prefix branch and raises `UnknownRoleError` on miss.
* `UnknownRoleError` exception class.

Deferred to later phases:

* `KnowledgeLayer` + `MetagraphView` + Global / Local bootstrap →
  Phase 14.
* L2 knowledge-addition lifecycle design (ADR-0150 + 3 lifecycle
  docs) → Phase 14a.
* Importers (DOLCE / OEWN / FrameNet / Alignments) → Phase 15.
* Promotion machinery → Phase 16.
* Versioning + breadcrumbs → Phase 17.
* REF_TYPES parity test against L3 → Phase 27 (ADR-0067).
* Per-builder inverse field helpers → per-consumer phase.
* Schema strict-tightening (per-role) → first-consumer phase after
  the 2-week-no-edit observation period per ADR-0149.
"""

from __future__ import annotations

__version__ = "0.0.0+phase13"

from .exceptions import KnowledgeError, RefFormatError, UnknownRoleError
from .identifiers import (
    ALL_ROLES,
    REF_TYPE_KEY,
    REF_TYPES,
    ROLE_CAPACITY_STATE,
    ROLE_CONCEPTS,
    ROLE_LEXICON,
    ROLE_MEMORIES,
    ROLE_ONTOLOGY,
    ROLE_PROBLEM_TRACE,
    ROLE_PROMOTED_PIPELINES,
    ROLE_TASK_PATTERNS,
    SEED_ROLES,
    UPPER_LAYER_ROLES,
    ParsedIri,
    alignment_role,
    capacity_snapshot_iri,
    dolce_iri,
    framenet_fe_iri,
    framenet_frame_iri,
    framenet_lu_iri,
    global_ref_key,
    is_version_qualified_iri,
    local_ref_key,
    memory_iri,
    oewn_lemma_iri,
    oewn_sense_iri,
    oewn_synset_iri,
    parse_iri,
    pipeline_iri,
    pipeline_step_iri,
    problem_trace_iri,
    subgoal_template_iri,
    task_pattern_iri,
)

from .schemas import (
    _ROLE_SCHEMA_BUILDERS,
    build_alignment_schema,
    build_capacity_state_schema,
    build_concepts_schema,
    build_lexicon_schema,
    build_memories_schema,
    build_ontology_schema,
    build_problem_trace_schema,
    build_promoted_pipelines_schema,
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
    # ── role constants ─────────────────────────────────────────────
    "ROLE_ONTOLOGY",
    "ROLE_LEXICON",
    "ROLE_CONCEPTS",
    "ROLE_PROMOTED_PIPELINES",
    "ROLE_TASK_PATTERNS",
    "ROLE_MEMORIES",
    "ROLE_PROBLEM_TRACE",
    "ROLE_CAPACITY_STATE",
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
    "memory_iri",
    "problem_trace_iri",
    "capacity_snapshot_iri",
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
    "build_memories_schema",
    "build_problem_trace_schema",
    "build_capacity_state_schema",
    "schema_for_role",
    "_ROLE_SCHEMA_BUILDERS",
]
