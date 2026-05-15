"""Exception hierarchy for the Core Layer (Phase 04 surface).

All Core-Layer errors inherit from ``CoreError`` so higher layers can catch
one base type. Phase 04 ships:

* ``CoreError`` — base class.
* ``IdentityError`` (Phase 02) — duplicate / unknown id, registry conflicts.
* ``SchemaError`` (Phase 03 stub) — invariant violations in the model
  layer (e.g. an empty ``HyperEdge`` member set, ``remove_node(cascade=False)``
  while an edge still references the node).
* ``CypherError`` (Phase 03 — ADR-0021) — invalid Cypher identifier
  (load-bearing for the rel-type validation pass criterion).
* ``PropertyShapeError`` (Phase 04) — property bag violates the
  primitive-only / reserved-key rules (:func:`mindsos_core.schema.validation.validate_user_properties`)
  OR violates the per-type ``PropertyType`` map under a strict
  :class:`mindsos_core.schema.Schema` (:meth:`Schema.validate_node_properties` /
  :meth:`Schema.validate_edge_properties`).
* ``UnknownTypeError`` (Phase 04) — referenced ``NodeType`` / ``EdgeType``
  is not registered on the schema, OR an edge's source/target node
  type is not in the edge type's allowed set, OR a duplicate type
  registration.

The full hierarchy lives in the parent project at
``mindsos_core/exceptions.py`` and ports phase-by-phase.
"""

from __future__ import annotations


class CoreError(Exception):
    """Base class for every error raised by mindsos_core."""


# ── Identity (Phase 02) ──────────────────────────────────────────────────────


class IdentityError(CoreError):
    """Duplicate id, unknown id, or replace-with-conflict."""


# ── Schema invariants (Phase 03 stub; Phase 04 still raises this for
#    structural invariants — empty hyperedge member set, cascade=False
#    with incident edges. Property-shape and unknown-type now have their
#    own classes (PropertyShapeError / UnknownTypeError) and are raised
#    by the Phase 04 Schema machinery.) ────────────────────────────────


class SchemaError(CoreError):
    """Structural invariant violation in the model layer.

    Phase 03 / 04 raise sites:

    * ``HyperEdge.__post_init__`` when instantiated with an empty member set.
    * ``Graph.remove_node(cascade=False)`` when the node still has incident
      edges or hyperedges.

    Property-shape and unknown-type errors are raised as
    :class:`PropertyShapeError` / :class:`UnknownTypeError` respectively
    (Phase 04 split — both inherit from ``CoreError``, not from
    ``SchemaError``, to keep the structural-vs-semantic distinction
    catchable separately).
    """


# ── Cypher safety (Phase 03 — ADR-0021) ──────────────────────────────────────


class CypherError(CoreError):
    """Identifier unsafe to splice into a Cypher query.

    Raised by ``mindsos_core.cypher.identifiers.validate_edge_type_identifier``
    and ``validate_label_identifier`` when a string fails the conservative
    identifier-shape regex. Edge / relationship type names are validated by
    ``Graph.add_edge`` (Phase 03) and ``Schema.add_edge_type`` (Phase 04)
    before construction.
    """


# ── Schema machinery (Phase 04) ──────────────────────────────────────────────


class PropertyShapeError(CoreError):
    """Property bag violates the user-property contract.

    Phase 04 raise sites:

    * :func:`mindsos_core.schema.validation.validate_user_properties` when a
      key is reserved, a key prefix is reserved (``ov__``), a value is
      non-primitive, or a ``ref:*`` value is empty / non-string.
    * :meth:`mindsos_core.schema.Schema.validate_node_properties` /
      :meth:`mindsos_core.schema.Schema.validate_edge_properties` under
      ``strict=True`` when a property's value type does not match its
      declared ``PropertyType``, or a key is undeclared on a strict-typed
      type.
    """


class UnknownTypeError(CoreError):
    """Referenced ``NodeType`` / ``EdgeType`` is not registered, or an
    edge's source/target type is not in the edge type's allowed set, or
    a duplicate type registration was attempted.

    Phase 04 raise sites:

    * :meth:`mindsos_core.schema.Schema.add_node_type` / ``add_edge_type``
      on duplicate registration; ``add_edge_type`` also raises when an
      ``allowed_source`` / ``allowed_target`` is not a registered
      :class:`NodeType`.
    * :meth:`mindsos_core.schema.Schema.require_node_type` /
      ``require_edge_type`` when the type is not registered.
    * :meth:`mindsos_core.schema.Schema.validate_edge` when an edge's
      source or target node type is outside the edge type's
      ``allowed_sources`` / ``allowed_targets``.
    """


# ── Compositional immutability (Phase 05b — re-shipped after 05a R3-B strip) ──


class CompositionalImmutableError(CoreError):
    """Mutation refused on a ``compositional=True`` IntergraphEdge.

    Per ADR-0148 + INTERGRAPH_EDGES_DESIGN.md §4.3, an intergraph edge with
    ``compositional=True`` is identity-bearing — removing or mutating it
    would silently corrupt the composition's identity contract. The flag
    itself is also immutable post-create (Phase 05b Pushback 22-A
    ``__setattr__`` override on :class:`IntergraphEdge`).

    Phase 05b raise sites:

    * :meth:`mindsos_core.models.metagraph.Metagraph.remove_intergraph_edge`
      on a compositional edge.
    * :meth:`mindsos_core.models.metagraph.Metagraph.update_intergraph_edge_properties`
      on a compositional edge.
    * :meth:`mindsos_core.models.metagraph.Metagraph.remove_graph` atomic
      precheck (Pushback 17-A) when any incident intergraph_edge is
      compositional.
    * :meth:`mindsos_core.models.intergraph_edge.IntergraphEdge.__setattr__`
      on any post-init write to the ``compositional`` field.

    Tester recovery for a wedged metagraph: ``mindsos metagraph reset
    --name <MG> --force --yes`` (full destroy + rebuild). Per Pushback 6-A
    no demotion verb ships in 05b.

    R3-B context: 05a stripped this exception class from the slim port
    (no consumer in 05a after CompositionalMetaEdge was dropped per N3-D).
    05b re-ships it with the IntergraphEdge primitive that consumes it.
    Phase 09 / Phase 10 will re-ship :class:`XRefIntegrityError` /
    :class:`RemoveGraphBlockedError` respectively under the same pattern.
    """


# ── Persistence (Phase 07) ───────────────────────────────────────────────────
#
# Per P21 A amended P84 B — Phase 07 ships 4 persistence exceptions at L1.
# ``MissingExpectedVersionError`` (the Global-write policy exception) lives
# at L0/L2 with its raiser (the Global-policy repository wrapper), per
# ADR-0127 §Implementation references amendment.


class PersistenceError(CoreError):
    """Base class for any error raised by ``mindsos_core.persistence``.

    Raised directly on:

    * FalkorDB driver import failure (``FalkorClient.__init__``).
    * Connection failure on ``FalkorClient.__init__``.
    * Cypher query failure on ``Client.run_query`` / ``run_batch``.
    * ``_props_json`` write failures (narrow chained catch per P97 B) at
      :meth:`MetagraphRepository.persist`.
    * ``sync --replace`` refusal when uncommitted ``:WALEntry`` rows
      reference the target graph (P91 A).
    """


class IntegrityCheckError(PersistenceError):
    """Persist-time double-check (ADR-0123 §2) detected an invariant violation.

    Raised by ``MetagraphRepository.persist`` / ``GraphRepository.persist``
    after a batched MERGE when the post-write probe finds duplicate ids
    for any element label. Carries the offending ``(label, [ids])``
    pair so the caller can surface the data.

    Distinct from the cumulative scanner output
    (:class:`IntegrityReport`) returned by ``verify_invariants`` — that
    is a value object, not an exception.
    """


class OptimisticConcurrencyConflict(PersistenceError):
    """OCC predicate (ADR-0127) failed: stale ``_version`` on update.

    Raised by ``GraphRepository.update_*_properties`` when the conditional
    MATCH on ``_version: $expected_version`` returns zero rows. Carries
    ``element_id``, ``expected_version``, and (when known) the
    ``actual_version`` for caller-side retry decisions.
    """

    def __init__(
        self,
        element_id: str,
        expected_version: int,
        actual_version: int | None = None,
    ) -> None:
        msg = (
            f"OCC conflict on element {element_id!r}: "
            f"expected _version={expected_version}"
        )
        if actual_version is not None:
            msg += f", actual={actual_version}"
        super().__init__(msg)
        self.element_id = element_id
        self.expected_version = expected_version
        self.actual_version = actual_version


class OptimisticConcurrencyExhausted(PersistenceError):
    """Retry loop wrapping :class:`OptimisticConcurrencyConflict` exceeded its budget.

    Phase 07 ships this as a definition-only exception class (P57 A —
    no raise-path at L1). L0/L2 retry wrappers raise it when their
    bounded retry attempts all fail with :class:`OptimisticConcurrencyConflict`.
    """


# Per Phase 08 R4-3 A — three new reconstruction-side exception classes.
# Phase 08 row PB-5 B / RPB-3 C / R4-2 D drive the raise paths.
# All inherit from ``PersistenceError`` so existing handlers continue to
# catch the broader category; no new ``ReconstructionError`` umbrella
# (R4-3 A — ``PersistenceError`` suffices).


class RefreshUnsafeError(PersistenceError):
    """``MetagraphLoader.refresh`` refused because the affected role has uncommitted in-memory mutations.

    ADR-0124 §Constraint. Phase 08 ships this as a **class-only** exception
    (per PB-5 B): no per-role mutation-flag tracking yet, so it is NOT
    raised in Phase 08. The class is importable and inherits from
    :class:`PersistenceError` so future-phase enforcement can switch on
    raise-paths without callers re-catching.

    .. note::

       Callers using ``refresh`` after in-memory mutations LOSE those
       mutations silently in Phase 08. Per-role mutation flag + enforcement
       is deferred (PB-5 B; documented loud risk in
       ``docs/usage/core/persistence.md``).
    """


class WALReplayerMissingError(PersistenceError):
    """No replayer registered for a WAL entry's ``kind`` during ``recover()``.

    Raised internally by :func:`mindsos_core.persistence.wal.recover` when
    an uncommitted :WALEntry row carries a ``kind`` that has no entry in
    the ``_REPLAYERS`` map. :func:`mindsos_core.reconstruction.load_metagraph`
    narrow-catches this on its initial ``recover()`` call (RPB-3 C) so a
    Phase 08 load with no registered replayers degrades to a silent no-op
    recovery; once L0/L2 (Phase 18+) register replayers the same call
    becomes meaningful.

    Driver-level errors during ``recover()`` continue to propagate as
    :class:`PersistenceError` per the locked narrow-catch contract.
    """


class RoleMismatchError(PersistenceError):
    """``MetagraphLoader.refresh`` saw a role drift between in-memory and DB state.

    Raised by :meth:`MetagraphLoader.refresh` when ``mg.graphs[gid].role``
    in memory differs from the persisted ``:Graph.role`` for the same
    ``graph_id`` (R4-2 D). Indicates substrate corruption — either an
    external write race or a manual DB edit since the last persist —
    rather than a user-recoverable error at runtime.

    Carries both roles in the message so operators can decide between
    a force-reset of the affected role and a deeper investigation.
    """

    def __init__(
        self,
        graph_id: str,
        in_memory_role: str | None,
        db_role: str | None,
    ) -> None:
        msg = (
            f"Role mismatch on graph {graph_id!r}: "
            f"in-memory role={in_memory_role!r}, DB role={db_role!r}"
        )
        super().__init__(msg)
        self.graph_id = graph_id
        self.in_memory_role = in_memory_role
        self.db_role = db_role
