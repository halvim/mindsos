"""MindsOS CLI — Phase 05b L1 IntergraphEdge + IntergraphEdgeType + MetagraphSchema container.

Phase 05b adds (per ADR-0148 first draft + 6-round-locked PHASE_MAP §5
row + 4 future-work entries filed in mindsos_future_plans.md):

* :class:`IntergraphEdge` primitive with ``compositional`` immutability
  flag (Pushback 22-A ``__setattr__`` enforcement).
* :class:`IntergraphEdgeType` schema vocabulary (role-based
  ``allowed_source_graphs`` / ``allowed_target_graphs`` per Pushback 4-A).
* :class:`MetagraphSchema` container (basename-keyed; reusable across N
  metagraphs per Pushback 11-A; one-attached-at-most per metagraph per
  Pushback 12-A).
* New top-level subapp ``mindsos metagraph-schema``.
* New 5 subcommands on ``mindsos metagraph``: add-intergraph-edge,
  remove-intergraph-edge, list-intergraph-edges, attach-schema,
  detach-schema (DMS-A unified command per Pushback 28-A).
* 4-way mutex on ``mindsos metagraph set-prop`` (Pushback 27-A extends
  05a's 3-way).
* Metagraph state-file v=1 → v=2 cumulative one-way migration (adds
  ``intergraph_edges`` array + ``schema_name`` reference).
* New ``metagraph-schema-<name>.json`` state-file kind (v=1).
* :class:`CompositionalImmutableError` re-shipped (R3-B in 05a stripped
  it; consumer = IntergraphEdge.compositional).
* :class:`Metagraph.mint_id` ADR-0131 helper landed (P7 carry-forward
  from 05a; consumer = IntergraphEdge factory's id-minting path).
* ``RESERVED_PROPERTY_KEYS`` extended with ``intergraph_edges``,
  ``schema_name``, ``_compositional`` (Pushbacks 18-A + 6).
"""

__version__ = "0.0.0+phase05b"
