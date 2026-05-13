"""MindsOS CLI — Phase 05c L1 IntergraphHyperEdge + IntergraphHyperEdgeType + replace-only update verb.

Phase 05c adds (per ADR-0148 amended + 4-round-locked PHASE_MAP §5 row
+ 2 new future-work entries filed in mindsos_future_plans.md):

* :class:`IntergraphHyperEdge` n-ary primitive with strict
  ``__setattr__`` immutability scope (P2-refined + P27 — anchors /
  members / properties / compositional all blocked on direct user
  mutation; factory bypasses via ``object.__setattr__`` for legitimate
  validated updates).
* :class:`IntergraphHyperEdgeType` schema vocabulary with role-based
  ``allowed_anchor_graphs`` / ``allowed_member_graphs`` and an
  ``ordered: bool = True`` flag (P18-A — permissive default; opt-in to
  set semantics via ``--unordered``).
* New ``mindsos metagraph add-intergraph-hyperedge``,
  ``remove-intergraph-hyperedge``, ``update-intergraph-hyperedge``
  (replace-only structural — P10-C), and ``list-intergraph-hyperedges``
  subcommands.
* New ``mindsos metagraph-schema add-intergraph-hyperedge-type``
  subcommand (P12-A schema-mutation footgun warning).
* 5-way mutex on ``mindsos metagraph set-prop`` (extends 05b's 4-way
  with ``--intergraph-hyperedge-id``).
* Metagraph state-file v=2 → v=3 cumulative one-way migration (adds
  ``intergraph_hyperedges`` array).
* MetagraphSchema state-file v=1 → v=2 cumulative one-way migration
  (adds ``intergraph_hyperedge_types`` array).
* ``RESERVED_PROPERTY_KEYS`` extended with ``intergraph_hyperedges``,
  ``intergraph_hyperedge_types``, ``anchors``, ``members``.
* P14-A 16-step validation order with canonicalization-BEFORE-cardinality.
* P19-A refusal of update calls that would collapse to 1-to-1
  cardinality (no in-place hyperedge→edge downgrade in 05c).
* P32 — cypher rel-type regex enforcement at factory inline AND
  ``__post_init__`` (belt-and-suspenders for direct-construction
  safety).

Out of scope (Phase 05d):
* :class:`MetaEdgeType` + :class:`MetaHyperEdgeType` vocabularies on
  :class:`MetagraphSchema` (deferred from 05b Pushback 1-C → 05c P1-B
  → 05d row stub).
"""

__version__ = "0.0.0+phase07"
