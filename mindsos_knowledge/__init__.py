"""MindsOS Knowledge Layer — slim Phase 12 surface.

L2 IRI vocabulary + REF_TYPES + role constants + ref-key helpers. Pure
library; no L1 mutation, no metagraph, no persistence. KL writes are
relocated to L3 capacities per ADR M1 / L2 redesign locks 2026-04-27.

Phase 12 deliberately ships:

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
* Role constants: 3 seed (`ROLE_ONTOLOGY` / `ROLE_LEXICON` /
  `ROLE_CONCEPTS`) + 5 upper-layer (`ROLE_PROMOTED_PIPELINES` /
  `ROLE_TASK_PATTERNS` / `ROLE_MEMORIES` / `ROLE_PROBLEM_TRACE` /
  `ROLE_CAPACITY_STATE`) + 3 frozensets (`SEED_ROLES` /
  `UPPER_LAYER_ROLES` / `ALL_ROLES`).
* Exceptions: `KnowledgeError` (base) + `RefFormatError`.

Deferred to later phases:

* Schemas (alignment / lexicon / ontology / concepts) → Phase 13.
* `KnowledgeLayer` + `MetagraphView` + Global / Local bootstrap →
  Phase 14.
* Importers (DOLCE / OEWN / FrameNet / Alignments) → Phase 15.
* Promotion machinery → Phase 16.
* Versioning + breadcrumbs → Phase 17.
* REF_TYPES parity test against L3 → Phase 27 (ADR-0067).
* Per-builder inverse field helpers (capacity_snapshot, pipeline,
  task_pattern, memory, problem_trace) → per-consumer phase
  (Phase 16 / 28 / 30 etc.).
"""

from __future__ import annotations

__version__ = "0.0.0+phase12"

from .exceptions import KnowledgeError, RefFormatError
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

__all__ = [
    # ── version ────────────────────────────────────────────────────
    "__version__",
    # ── exceptions ─────────────────────────────────────────────────
    "KnowledgeError",
    "RefFormatError",
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
]
