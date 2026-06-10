"""L2 role-graph schema catalogue (Phase 13).

Eight schema builders + a parametric alignment builder + a dispatch
function. Closes the L2 schema dispatch table per Phase 13 PB-1.

Public surface:

* ``build_ontology_schema``, ``build_lexicon_schema``,
  ``build_concepts_schema`` — seed roles (v3 verbatim ports).
* ``build_alignment_schema(strict=False, extra_edge_types=())`` —
  parametric; one builder per alignment-pair graph
  (`alignment:<a>:<b>`).
* ``build_promoted_pipelines_schema``, ``build_task_patterns_schema``,
  ``build_episodic_memories_schema``, ``build_problem_trace_schema``,
  ``build_capacity_state_schema`` — 5 upper-layer roles
  (Phase 13 NET-NEW; strict=False per ADR-0149; ``episodic_memories``
  renamed from ``memories`` at Phase 39 per ADR-0044 §am-3).
* ``schema_for_role(role: str) -> Schema`` — dispatch with
  alignment-prefix branch; raises ``UnknownRoleError`` on miss
  (Phase 13 PB-11).
* ``_ROLE_SCHEMA_BUILDERS`` — internal dispatch dict. Phase 14
  (KL bootstrap) uses this when wiring ``ensure_role_graph``.

All schemas ship at ``strict=False`` per ADR-0149 (2-week-no-edit
tightening rule documented in ADR §Revisions).
"""

from __future__ import annotations

from typing import Callable

from mindsos_core import Schema

from ._base import Discipline, L2Schema, StorageMode
from ..exceptions import UnknownRoleError
from ..identifiers import (
    ALL_ROLES,
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
    ROLE_TASK_PATTERNS,
)
from .alignment import build_alignment_schema
from .capacity_gaps import build_capacity_gaps_schema
from .capacity_state import build_capacity_state_schema
from .concepts import build_concepts_schema
from .installed_skills import build_installed_skills_schema
from .lexicon import build_lexicon_schema
from .episodic_memories import build_episodic_memories_schema
from .learned_parameters import build_learned_parameters_schema
from .ontology import build_ontology_schema
from .parameter_staging import build_parameter_staging_schema
from .pending_promotions import build_pending_promotions_schema
from .problem_trace import build_problem_trace_schema
from .promoted_pipelines import build_promoted_pipelines_schema
from .task_patterns import build_task_patterns_schema


#: Dispatch table — role → builder callable. Phase 14 (KL bootstrap)
#: consumes this directly when wiring ``ensure_role_graph``.
#: Alignment is NOT here — its dispatch is keyed on the
#: ``alignment:`` prefix, not a fixed role name (one schema serves
#: all role-pair alignment graphs).
_ROLE_SCHEMA_BUILDERS: dict[str, Callable[..., Schema]] = {
    ROLE_ONTOLOGY: build_ontology_schema,
    ROLE_LEXICON: build_lexicon_schema,
    ROLE_CONCEPTS: build_concepts_schema,
    ROLE_PROMOTED_PIPELINES: build_promoted_pipelines_schema,
    ROLE_TASK_PATTERNS: build_task_patterns_schema,
    ROLE_EPISODIC_MEMORIES: build_episodic_memories_schema,
    ROLE_PROBLEM_TRACE: build_problem_trace_schema,
    ROLE_CAPACITY_STATE: build_capacity_state_schema,
    # Phase 43 additions per ADR-0150 §am-5.
    ROLE_PARAMETER_STAGING: build_parameter_staging_schema,
    ROLE_PENDING_PROMOTIONS: build_pending_promotions_schema,
    ROLE_CAPACITY_GAPS: build_capacity_gaps_schema,
    ROLE_LEARNED_PARAMETERS: build_learned_parameters_schema,
    # Phase 50 addition per ADR-0150 §am-6.
    ROLE_INSTALLED_SKILLS: build_installed_skills_schema,
}


def schema_for_role(role: str, strict: bool = False) -> Schema:
    """Return the schema for ``role``.

    Handles the alignment-prefix branch (``alignment:<a>:<b>``) by
    returning the parametric alignment schema. Raises
    ``UnknownRoleError`` for any other unrecognised role.

    Args:
        role: One of ``ALL_ROLES``, or a string starting with
            ``"alignment:"``.
        strict: Forwarded to the builder. Default ``False`` per
            ADR-0149.

    Raises:
        UnknownRoleError: ``role`` is not in ``ALL_ROLES`` and does not
            start with ``"alignment:"``.
    """
    # PB-5 + legacy §3.3 — alignment prefix-match short-circuits the
    # dispatch dict. The parametric ``build_alignment_schema`` serves
    # any role-pair graph.
    if role.startswith("alignment:"):
        return build_alignment_schema(strict=strict)

    builder = _ROLE_SCHEMA_BUILDERS.get(role)
    if builder is None:
        valid = sorted(ALL_ROLES)
        raise UnknownRoleError(
            f"Unknown role {role!r}. Valid roles: {valid}. "
            f"For alignment graphs, use the 'alignment:<role_a>:<role_b>' form."
        )
    return builder(strict=strict)


__all__ = [
    # Per-role builders.
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
    # Dispatch surface.
    "schema_for_role",
    "_ROLE_SCHEMA_BUILDERS",
    # L2-private vocabulary (Phase 43 — ADR-0153 §am-1 + ADR-0151).
    "Discipline",
    "L2Schema",
    "StorageMode",
]
