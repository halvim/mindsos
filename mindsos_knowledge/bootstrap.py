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

from typing import Iterable, Mapping, Optional, Tuple

from mindsos_core import Graph
from mindsos_core.models.metagraph import Metagraph

from .exceptions import BootstrapCycleError, KnowledgeError, UnknownRoleError
from .identifiers import (
    ALL_ROLES,
    DATASET_ROLE_PREFIX,
    ROLE_CAPACITY_GAPS,
    ROLE_CAPACITY_STATE,
    ROLE_CONCEPTS,
    ROLE_EPISODIC_MEMORIES,
    ROLE_INSTALLED_CAPACITIES,
    ROLE_INSTALLED_SKILLS,
    ROLE_LEARNED_PARAMETERS,
    ROLE_LEARNED_PIPELINES,
    ROLE_LEXICON,
    ROLE_ONTOLOGY,
    ROLE_PARAMETER_STAGING,
    ROLE_PENDING_PROMOTIONS,
    ROLE_PROBLEM_TRACE,
    ROLE_PROMOTED_PIPELINES,
    ROLE_SUBMINDS,
    ROLE_REQUEST_PATTERNS,
)
from .schemas import (
    build_alignment_schema,
    build_learned_parameters_schema,
    schema_for_role,
)


#: Roles that live in Global metagraph per ADR-0044 (episodic_memories
#: + capacity-state are Local) + ADR-0150 §amendment-1 (alignment is
#: Global-only at v1) + ADR-0150 §amendment-5 (Phase 43 — 3 of the 4
#: new role-graphs have a Global form: pending-promotions, capacity-gaps,
#: learned-parameters; parameter-staging is Local-only).
_GLOBAL_NAMED_ROLES: frozenset[str] = frozenset({
    ROLE_ONTOLOGY,
    ROLE_LEXICON,
    ROLE_CONCEPTS,
    ROLE_PROMOTED_PIPELINES,
    ROLE_REQUEST_PATTERNS,
    ROLE_PROBLEM_TRACE,
    # Phase 43 (ADR-0150 §am-5) — Global-form role-graphs.
    ROLE_PENDING_PROMOTIONS,
    ROLE_CAPACITY_GAPS,
    ROLE_LEARNED_PARAMETERS,
    # Phase 50 (ADR-0150 §am-6) — skill-install state; Global-only.
    ROLE_INSTALLED_SKILLS,
    # feat/subminds (ADR-0150 §am-7) — SubMind definition records. The
    # role is Global+Local by design; Slice 1 bootstraps the Global form
    # only (authored, admin-gated endowment). The Local form lands with
    # the taught-endowment slice.
    ROLE_SUBMINDS,
})

#: Roles that live in Local-per-user metagraph per ADR-0044
#: (§am-3 renamed ``memories`` → ``episodic_memories``) + ADR-0150
#: §amendment-5 (Phase 43 — 3 of the 4 new role-graphs have a Local
#: form: parameter-staging, pending-promotions, learned-parameters;
#: capacity-gaps is Global-only) + ADR-0150 §amendment-8 (request-patterns
#: gains a Local form — dual-scope like pending-promotions /
#: learned-parameters: per-user patterns are authored/learned Local and
#: promoted to the shared Global form; discipline is
#: ``immutable_successor`` so new pattern nodes are addable Local)
#: + ADR-0150 §amendment-11 (CORE-C2R1 — ``installed-skills`` gains a Local
#: form so a user installs a Skill into their own realm and an admin
#: promotes it to Global; the §am-6 Global form is untouched).
_LOCAL_NAMED_ROLES: frozenset[str] = frozenset({
    ROLE_EPISODIC_MEMORIES,
    ROLE_CAPACITY_STATE,
    # Phase 43 (ADR-0150 §am-5) — Local-form role-graphs.
    ROLE_PARAMETER_STAGING,
    ROLE_PENDING_PROMOTIONS,
    ROLE_LEARNED_PARAMETERS,
    # feat/phase1-seam (ADR-0150 §am-8) — request-patterns is now dual-scope.
    ROLE_REQUEST_PATTERNS,
    # feat/learned-pipeline-persistence (ADR-0203) — Local-only taught
    # pipelines; immutable_successor append-ordinal.
    ROLE_LEARNED_PIPELINES,
    # ADR-0183 §am-5 — Local-only installed-skill capability descriptors.
    ROLE_INSTALLED_CAPACITIES,
    # CORE-C2R1 (ADR-0150 §am-11) — installed-skills is now dual-scope.
    # A user installs Local; an admin promotes to the Global form added
    # by §am-6. Same ``append_only`` schema serves both scopes — the
    # record is an action record either way, only its realm differs.
    ROLE_INSTALLED_SKILLS,
})

#: Alignment role-prefix per ADR-0150. Per §amendment-1 (Phase 14
#: PB-8), alignment is Global-only at v1.
_ALIGNMENT_PREFIX: str = "alignment:"

#: Phase 43 (ADR-0150 §am-5) introduces dual-scope role-graphs that
#: appear in BOTH ``_GLOBAL_NAMED_ROLES`` and ``_LOCAL_NAMED_ROLES``
#: (``pending-promotions`` + ``learned-parameters``). The pre-Phase-43
#: binary scope-rejection ("if role in _LOCAL_NAMED_ROLES: reject from
#: global ensure") breaks for these. Use the set-difference helpers
#: below to reject only the *exclusively-scoped* roles per direction.
_GLOBAL_ONLY_ROLES: frozenset[str] = (
    _GLOBAL_NAMED_ROLES - _LOCAL_NAMED_ROLES
)
_LOCAL_ONLY_ROLES: frozenset[str] = (
    _LOCAL_NAMED_ROLES - _GLOBAL_NAMED_ROLES
)


#: Per-role ``applies_after`` declarations per Phase 43 R0b §1.2 +
#: NPB6-6 + L2-37 split (NPB11-1 field-only at Phase 43; Phase 44 ships
#: the Kahn topological-sort scheduler that consumes these declarations).
#:
#: Soft edge: ``episodic_memories ← {request-patterns}`` per Chat B D-B47
#: (Episodes carry ``request_pattern_iri`` so request-patterns must exist
#: before episodes can reference). Since ADR-0150 §am-8 request-patterns is
#: dual-scope, this edge is now **within-Local-scope** too, so the Local
#: kahn_sort orders request-patterns before episodic_memories (previously
#: cross-scope / ignored). Other role-graphs are independent.
#:
#: Phase 43 declares the field shape only; consumers raise no errors
#: when ordering is violated. Phase 44 ships the scheduler that turns
#: violations into bootstrap-time errors.
_APPLIES_AFTER_BY_ROLE: dict[str, frozenset[str]] = {
    ROLE_ONTOLOGY: frozenset(),
    ROLE_LEXICON: frozenset(),
    ROLE_CONCEPTS: frozenset(),
    ROLE_PROMOTED_PIPELINES: frozenset(),
    ROLE_REQUEST_PATTERNS: frozenset(),
    ROLE_EPISODIC_MEMORIES: frozenset({ROLE_REQUEST_PATTERNS}),
    ROLE_PROBLEM_TRACE: frozenset(),
    ROLE_CAPACITY_STATE: frozenset(),
    ROLE_PARAMETER_STAGING: frozenset(),
    ROLE_PENDING_PROMOTIONS: frozenset(),
    ROLE_CAPACITY_GAPS: frozenset(),
    ROLE_LEARNED_PARAMETERS: frozenset(),
    # Phase 50 (ADR-0150 §am-6) — no bootstrap-order dependencies.
    ROLE_INSTALLED_SKILLS: frozenset(),
    # feat/subminds (ADR-0150 §am-7) — no bootstrap-order dependencies.
    ROLE_SUBMINDS: frozenset(),
    # feat/learned-pipeline-persistence (ADR-0203) — independent.
    ROLE_LEARNED_PIPELINES: frozenset(),
    # ADR-0183 §am-5 — independent.
    ROLE_INSTALLED_CAPACITIES: frozenset(),
}


__all__ = [
    "ensure_global_role_graph",
    "ensure_local_role_graph",
    "kahn_sort",
    "_GLOBAL_NAMED_ROLES",
    "_LOCAL_NAMED_ROLES",
    "_ALIGNMENT_PREFIX",
    "_APPLIES_AFTER_BY_ROLE",
]


def kahn_sort(
    roles: Iterable[str],
    applies_after: Mapping[str, "frozenset[str]"],
) -> Tuple[str, ...]:
    """Deterministic topological bootstrap order over ``roles``.

    Each role is emitted only after every role named in its
    ``applies_after`` set that is also present in ``roles``. Cross-scope
    dependencies (a target outside ``roles``) are ignored — they are
    satisfied by Global-before-Local bootstrap sequencing, not by this
    within-scope sort. Among roles with no remaining dependency the
    alphabetically-smallest is emitted next, so independent roles keep
    the ``sorted(...)`` order the pre-Phase-44 bootstrap walk used.
    Missing ``applies_after`` entries default to no constraint
    (Phase 43 NPB11-1).

    Consumes the Phase-43 ``_APPLIES_AFTER_BY_ROLE`` declarations
    (L2-37 consumer split). With the v1 declarations the only edge
    (``episodic_memories ← request-patterns``) is cross-scope, so every
    single-scope sort reduces to alphabetical; the scheduler exists to
    enforce ordering for future within-scope edges and to reject cycles.

    Raises:
        BootstrapCycleError: the in-scope ``applies_after`` edges
            contain a cycle.
    """
    role_set = set(roles)
    remaining: dict[str, set[str]] = {
        role: set(applies_after.get(role, frozenset())) & role_set
        for role in role_set
    }
    ordered: list[str] = []
    while remaining:
        ready = sorted(role for role, deps in remaining.items() if not deps)
        if not ready:
            raise BootstrapCycleError(
                "applies_after cycle among roles: "
                + ", ".join(sorted(remaining))
            )
        nxt = ready[0]
        ordered.append(nxt)
        del remaining[nxt]
        for deps in remaining.values():
            deps.discard(nxt)
    return tuple(ordered)


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
    applies_after: frozenset[str] = frozenset(),
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
      ``promoted-pipelines``, ``request-patterns``, ``problem-trace``).
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
    # Phase 43 (ADR-0150 §am-5): dual-scope roles (in both
    # ``_GLOBAL_NAMED_ROLES`` and ``_LOCAL_NAMED_ROLES``) pass through;
    # only exclusively-Local roles are rejected.
    if role in _LOCAL_ONLY_ROLES:
        raise KnowledgeError(
            f"Role {role!r} is Local-only per ADR-0044; cannot create "
            f"in a Global metagraph via ensure_global_role_graph. Use "
            f"ensure_local_role_graph instead."
        )

    # Step 1b — dataset prefix is Local-only (ADR-0150 §am-9).
    if role.startswith(DATASET_ROLE_PREFIX):
        raise KnowledgeError(
            f"Role {role!r} is a dataset role; dataset graphs are Local-only "
            f"per ADR-0150 §am-9. Use ensure_local_role_graph instead."
        )

    # Step 2 — accept alignment-prefixed branch (per ADR-0150
    # §amendment-1, alignment is Global-only at v1).
    if role.startswith(_ALIGNMENT_PREFIX):
        schema = build_alignment_schema(
            strict=False, extra_edge_types=extra_edge_types
        )
    elif role == ROLE_LEARNED_PARAMETERS:
        # Phase 43 (ADR-0150 §am-5) per-scope discipline split per
        # ADR-0153 §1: Global uses ``admin_authored``; the default
        # schema_for_role dispatch returns the Local form
        # (``mutable_with_retention``). Special-case here.
        schema = build_learned_parameters_schema(strict=False, scope="global")
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
    *,
    applies_after: frozenset[str] = frozenset(),
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
    # Phase 43 (ADR-0150 §am-5): dual-scope roles pass through; only
    # exclusively-Global roles are rejected.
    if role in _GLOBAL_ONLY_ROLES:
        raise KnowledgeError(
            f"Role {role!r} is Global-only; cannot create in a Local "
            f"metagraph via ensure_local_role_graph. Use "
            f"ensure_global_role_graph instead."
        )

    # Step 3 — Local-named branch.
    if role == ROLE_LEARNED_PARAMETERS:
        # Phase 43 (ADR-0150 §am-5) per-scope discipline split per
        # ADR-0153 §1: Local uses ``mutable_with_retention``. The default
        # ``schema_for_role`` dispatch matches but we route explicitly
        # here for symmetry with the Global form in
        # ``ensure_global_role_graph``.
        schema = build_learned_parameters_schema(strict=False, scope="local")
    elif role in _LOCAL_NAMED_ROLES:
        schema = schema_for_role(role, strict=False)
    elif role.startswith(DATASET_ROLE_PREFIX):
        # ADR-0150 §am-9 — dataset prefix (Local-only). Schema comes from
        # the per-instance registry via ``schema_for_role``; an
        # unregistered dataset role raises ``UnknownRoleError`` there.
        schema = schema_for_role(role, strict=False)
    else:
        # Step 4 — unknown role.
        valid = sorted(ALL_ROLES)
        raise UnknownRoleError(
            f"Unknown role {role!r}. Valid roles: {valid}. "
            f"For alignment graphs, use the 'alignment:<role_a>:<role_b>' "
            f"form. For dataset graphs, use the 'dataset:<name>' form and "
            f"register the schema first (ADR-0150 §am-9)."
        )

    # Step 5 — idempotent lookup.
    existing = _find_role_graph(metagraph, role)
    if existing is not None:
        return existing

    # Step 6 — mint a new Graph with the schema attached.
    graph = Graph(name=role, role=role, schema=schema)
    metagraph.add_graph(graph)
    return graph
