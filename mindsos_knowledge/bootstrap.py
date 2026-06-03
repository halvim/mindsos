"""L2 KL bootstrap helpers — role-graph ensure functions (Phase 14).

Two pure module-level functions plus the two scope-set constants
they dispatch on:

* ``ensure_global_role_graph(metagraph, role, *, extra_edge_types=())``
  — idempotent; accepts the 6 Global-named roles + the
  ``alignment:<a>:<b>`` prefix (per ADR-0150 §amendment-1, alignment
  is Global-only at v1).
* ``ensure_local_role_graph(metagraph, role)`` — idempotent; accepts
  the 2 Local-named roles (``episodic_memories`` + ``capacity-state``)
  per ADR-0044 (§am-3 renamed ``memories`` → ``episodic_memories``).

Both functions:

1. Validate the role belongs to their scope set; raise
   :class:`KnowledgeError` (or :class:`UnknownRoleError` if the role
   isn't known anywhere).
2. Look up existing role-graph in the metagraph; if present, return it
   (idempotent no-op — does NOT re-verify schema match; Phase 14 PB-10
   calibration).
3. Otherwise: build the role's schema via Phase 13's
   :func:`mindsos_knowledge.schemas.schema_for_role` and create a fresh
   :class:`mindsos_core.Graph` with the schema attached, add to the
   metagraph, return.

Per Phase 14 round-1 PB-2 calibration, these are **module-level**
functions, not :class:`KnowledgeLayer` methods — they're pure
operations on a metagraph + role, with no KL state needed. The
:class:`KnowledgeLayer` class composes them.

Per ADR-0149, schemas ship at ``strict=False`` by default. Callers
that need ``strict=True`` for testing pass it through to
``schema_for_role(role, strict=True)`` separately and then call the
ensure function — at the moment, the ensure functions always default
to ``strict=False``.

Per Phase 14 PB-8 + ADR-0150 §amendment-1: alignment is Global-only.
``ensure_local_role_graph`` rejects alignment prefixes with
:class:`KnowledgeError`.
"""

from __future__ import annotations

from typing import Optional, Tuple

from mindsos_core import Graph
from mindsos_core.models.metagraph import Metagraph

from .exceptions import KnowledgeError, UnknownRoleError
from .identifiers import (
    ALL_ROLES,
    ROLE_CAPACITY_STATE,
    ROLE_CONCEPTS,
    ROLE_EPISODIC_MEMORIES,
    ROLE_LEXICON,
    ROLE_ONTOLOGY,
    ROLE_PROBLEM_TRACE,
    ROLE_PROMOTED_PIPELINES,
    ROLE_TASK_PATTERNS,
)
from .schemas import build_alignment_schema, schema_for_role


#: Roles that live in Global metagraph per ADR-0044 (episodic_memories
#: + capacity-state are Local) + ADR-0150 §amendment-1 (alignment is
#: Global-only at v1).
_GLOBAL_NAMED_ROLES: frozenset[str] = frozenset({
    ROLE_ONTOLOGY,
    ROLE_LEXICON,
    ROLE_CONCEPTS,
    ROLE_PROMOTED_PIPELINES,
    ROLE_TASK_PATTERNS,
    ROLE_PROBLEM_TRACE,
})

#: Roles that live in Local-per-user metagraph per ADR-0044
#: (§am-3 renamed ``memories`` → ``episodic_memories``).
_LOCAL_NAMED_ROLES: frozenset[str] = frozenset({
    ROLE_EPISODIC_MEMORIES,
    ROLE_CAPACITY_STATE,
})

#: Alignment role-prefix per ADR-0150. Per §amendment-1 (Phase 14
#: PB-8), alignment is Global-only at v1.
_ALIGNMENT_PREFIX: str = "alignment:"


__all__ = [
    "ensure_global_role_graph",
    "ensure_local_role_graph",
    "_GLOBAL_NAMED_ROLES",
    "_LOCAL_NAMED_ROLES",
    "_ALIGNMENT_PREFIX",
]


def _find_role_graph(metagraph: Metagraph, role: str) -> Optional[Graph]:
    """Return the first contained Graph whose ``role`` matches, or None.

    Per Phase 14's MetagraphView lookup pattern. L1 ships no
    ``graphs_by_role`` helper; the iteration lives at the KL layer.
    """
    for g in metagraph.graphs.values():
        if g.role == role:
            return g
    return None


def ensure_global_role_graph(
    metagraph: Metagraph,
    role: str,
    *,
    extra_edge_types: Tuple[str, ...] = (),
) -> Graph:
    """Ensure a Global-scoped role-graph exists in ``metagraph``.

    Idempotent: if a Graph with ``role`` already exists in the
    metagraph, returns it unchanged (does NOT re-verify schema match
    per Phase 14 PB-10 calibration). Otherwise creates a fresh
    :class:`mindsos_core.Graph` with the schema from
    :func:`mindsos_knowledge.schemas.schema_for_role` attached and
    adds it.

    Accepts:

    * The 6 Global-named roles (``ontology``, ``lexicon``, ``concepts``,
      ``promoted-pipelines``, ``task-patterns``, ``problem-trace``).
    * ``alignment:<role-a>:<role-b>`` prefixed roles (per ADR-0150
      §amendment-1).

    Rejects:

    * Local-scoped roles (``episodic_memories``, ``capacity-state``) per
      ADR-0044 (§am-3 rename) — raises :class:`KnowledgeError`.
    * Unrecognised roles — raises :class:`UnknownRoleError` (mirrors
      Phase 13's ``schema_for_role`` UnknownRoleError shape; see
      Phase 13 PB-11).

    Args:
        metagraph: The Global :class:`Metagraph` to ensure into.
        role: One of the 6 Global-named roles OR an
            ``alignment:<a>:<b>``-prefixed role string.
        extra_edge_types: Tuple of edge-type name strings (matching
            ADR-0021 Cypher rel-type regex). Forwarded to
            :func:`mindsos_knowledge.schemas.build_alignment_schema`
            when ``role`` starts with ``"alignment:"``; ignored for
            non-alignment roles. Phase 14 calibration: forward-
            compatible with Phase 15's Alignments importer.

    Returns:
        The existing or newly-added :class:`Graph` whose
        ``role == role``.

    Raises:
        KnowledgeError: ``role`` is a Local-scoped role.
        UnknownRoleError: ``role`` is not in
            :data:`mindsos_knowledge.identifiers.ALL_ROLES` and does
            not start with ``"alignment:"``.
    """
    # Step 1 — scope rejection: Local-only roles are not creatable here.
    if role in _LOCAL_NAMED_ROLES:
        raise KnowledgeError(
            f"Role {role!r} is Local-scoped per ADR-0044; cannot create "
            f"in a Global metagraph via ensure_global_role_graph. Use "
            f"ensure_local_role_graph instead."
        )

    # Step 2 — accept alignment-prefixed branch (per ADR-0150
    # §amendment-1, alignment is Global-only at v1).
    if role.startswith(_ALIGNMENT_PREFIX):
        schema = build_alignment_schema(
            strict=False, extra_edge_types=extra_edge_types
        )
    elif role in _GLOBAL_NAMED_ROLES:
        # Step 3 — non-alignment Global-named: dispatch via schema_for_role.
        # extra_edge_types is alignment-only; silently ignore for these.
        schema = schema_for_role(role, strict=False)
    else:
        # Step 4 — unknown role. Mirrors schema_for_role's error message.
        valid = sorted(ALL_ROLES)
        raise UnknownRoleError(
            f"Unknown role {role!r}. Valid roles: {valid}. "
            f"For alignment graphs, use the 'alignment:<role_a>:<role_b>' "
            f"form."
        )

    # Step 5 — idempotent lookup.
    existing = _find_role_graph(metagraph, role)
    if existing is not None:
        return existing

    # Step 6 — mint a new Graph with the schema attached.
    graph = Graph(name=role, role=role, schema=schema)
    metagraph.add_graph(graph)
    return graph


def ensure_local_role_graph(
    metagraph: Metagraph,
    role: str,
) -> Graph:
    """Ensure a Local-scoped role-graph exists in ``metagraph``.

    Idempotent: if a Graph with ``role`` already exists in the
    metagraph, returns it unchanged. Otherwise creates a fresh
    :class:`mindsos_core.Graph` with the schema from Phase 13's
    :func:`schema_for_role` attached.

    Accepts:

    * The 2 Local-named roles per ADR-0044 (§am-3 rename):
      ``episodic_memories``, ``capacity-state``.

    Rejects:

    * Global-scoped roles — raises :class:`KnowledgeError`.
    * Alignment-prefixed roles — raises :class:`KnowledgeError` per
      ADR-0150 §amendment-1 (alignment is Global-only at v1).
    * Unrecognised roles — raises :class:`UnknownRoleError`.

    Args:
        metagraph: The Local :class:`Metagraph` (per-user) to ensure
            into.
        role: ``episodic_memories`` or ``capacity-state``.

    Returns:
        The existing or newly-added :class:`Graph` whose
        ``role == role``.

    Raises:
        KnowledgeError: ``role`` is Global-scoped or alignment-prefixed.
        UnknownRoleError: ``role`` is not in
            :data:`mindsos_knowledge.identifiers.ALL_ROLES` and does
            not start with ``"alignment:"``.
    """
    # Step 1 — alignment rejection (ADR-0150 §amendment-1).
    if role.startswith(_ALIGNMENT_PREFIX):
        raise KnowledgeError(
            f"Role {role!r} is alignment-prefixed; alignment is Global-only "
            f"at v1 per ADR-0150 §amendment-1. Use "
            f"ensure_global_role_graph instead."
        )

    # Step 2 — scope rejection: Global-only roles are not creatable here.
    if role in _GLOBAL_NAMED_ROLES:
        raise KnowledgeError(
            f"Role {role!r} is Global-scoped; cannot create in a Local "
            f"metagraph via ensure_local_role_graph. Use "
            f"ensure_global_role_graph instead."
        )

    # Step 3 — Local-named branch.
    if role in _LOCAL_NAMED_ROLES:
        schema = schema_for_role(role, strict=False)
    else:
        # Step 4 — unknown role.
        valid = sorted(ALL_ROLES)
        raise UnknownRoleError(
            f"Unknown role {role!r}. Valid roles: {valid}. "
            f"For alignment graphs, use the 'alignment:<role_a>:<role_b>' "
            f"form."
        )

    # Step 5 — idempotent lookup.
    existing = _find_role_graph(metagraph, role)
    if existing is not None:
        return existing

    # Step 6 — mint a new Graph with the schema attached.
    graph = Graph(name=role, role=role, schema=schema)
    metagraph.add_graph(graph)
    return graph
