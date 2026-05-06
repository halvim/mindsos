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
