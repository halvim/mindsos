"""Exception hierarchy for the Core Layer (Phase 03 surface).

All Core-Layer errors inherit from ``CoreError`` so higher layers can catch
one base type. Phase 03 ships:

* ``CoreError`` — base class.
* ``IdentityError`` (Phase 02) — duplicate / unknown id, registry conflicts.
* ``SchemaError`` — invariant violations in the model layer (e.g. an empty
  ``HyperEdge`` member set, ``remove_node(cascade=False)`` while an edge
  still references the node). The Schema *machinery* itself (NodeType /
  EdgeType / strict validation) ships in Phase 04 — only the exception
  class lands in Phase 03 because the Phase 03 model code raises it.
* ``CypherError`` — invalid Cypher identifier (per ADR-0021); load-bearing
  for the rel-type validation pass criterion.

The full hierarchy lives in the parent project at
``mindsos_core/exceptions.py`` and ports phase-by-phase.
"""

from __future__ import annotations


class CoreError(Exception):
    """Base class for every error raised by mindsos_core."""


# ── Identity (Phase 02) ──────────────────────────────────────────────────────


class IdentityError(CoreError):
    """Duplicate id, unknown id, or replace-with-conflict."""


# ── Schema invariants (Phase 03 — class only; full Schema in Phase 04) ──────


class SchemaError(CoreError):
    """Invariant violation in the model layer.

    Phase 03 raises sites:

    * ``HyperEdge.__post_init__`` when instantiated with an empty member set.
    * ``Graph.remove_node(cascade=False)`` when the node still has incident
      edges or hyperedges.

    Phase 04+ extends this exception with property-shape validation and
    type-vocabulary mismatches via the ``Schema`` machinery.
    """


# ── Cypher safety (Phase 03 — ADR-0021) ──────────────────────────────────────


class CypherError(CoreError):
    """Identifier unsafe to splice into a Cypher query.

    Raised by ``mindsos_core.cypher.identifiers.validate_edge_type_identifier``
    and ``validate_label_identifier`` when a string fails the conservative
    identifier-shape regex. Edge / relationship type names are validated by
    ``Graph.add_edge`` (Phase 03) before construction.
    """
