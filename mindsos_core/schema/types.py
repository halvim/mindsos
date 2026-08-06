"""Schema type declarations.

``NodeType`` and ``EdgeType`` record the *shape* of a type in the
schema: its name, optional property-type map, and (for edges) permitted
source/target node types.

``HyperEdgeType`` (Phase 04-v2 — ADR-0017 / MC-2 / HET-1) records the
shape of an n-ary edge type: name, ``allowed_member_types`` (every
member's ``type_name`` must be in the set; no cardinality bounds; empty
list permitted per AME-1, mirroring ``EdgeType`` precedent), property
type map, and description.

``PropertyType`` enumerates the primitive property value types that
Schema can enforce when ``strict=True``. Lists of primitives are also
allowed (Redis/FalkorDB stores them natively).

Phase 04 ships the full 8-variant vocabulary verbatim from the parent
project. Splitting (e.g. shipping only primitives in Phase 04, lists in
Phase 05) was rejected — the variants are paired in one Enum and
removing them later creates Phase 04→05 forward debt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, Optional


class PropertyType(str, Enum):
    """Primitive property value kinds recognised by strict schemas."""

    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    LIST_STRING = "list[string]"
    LIST_INT = "list[int]"
    LIST_FLOAT = "list[float]"
    LIST_BOOL = "list[bool]"


@dataclass(frozen=True)
class NodeType:
    """Declaration of a node type."""

    name: str
    #: Optional property-name -> expected PropertyType. Used when the
    #: owning Schema has ``strict=True``. When empty the node type
    #: accepts any primitive properties.
    property_types: Dict[str, PropertyType] = field(default_factory=dict)
    description: Optional[str] = None

    def __repr__(self) -> str:
        return f"NodeType({self.name!r})"


@dataclass(frozen=True)
class EdgeType:
    """Declaration of an edge (relationship) type.

    ``allowed_sources`` / ``allowed_targets`` restrict which node types
    may appear on each end. An empty set means "any". The edge type
    ``name`` is used verbatim as the Cypher relationship identifier, so
    it MUST match ``^[A-Z][A-Z0-9_]{0,63}$`` (validated at registration
    time via :func:`mindsos_core.cypher.identifiers.validate_edge_type_identifier`).
    """

    name: str
    allowed_sources: FrozenSet[str] = field(default_factory=frozenset)
    allowed_targets: FrozenSet[str] = field(default_factory=frozenset)
    property_types: Dict[str, PropertyType] = field(default_factory=dict)
    description: Optional[str] = None

    def __repr__(self) -> str:
        return f"EdgeType({self.name!r})"


@dataclass(frozen=True)
class HyperEdgeType:
    """Declaration of an n-ary hyperedge type (Phase 04-v2 — ADR-0017 / MC-2 / HET-1).

    ``allowed_member_types`` restricts which node types may appear as
    members of a hyperedge of this type. An empty set (``frozenset()``)
    means "any" — mirrors ``EdgeType``'s ``allowed_sources`` /
    ``allowed_targets`` precedent (AME-1 lock). The hyperedge type
    ``name`` is used verbatim as the Cypher relationship identifier, so
    it MUST match ``^[A-Z][A-Z0-9_]{0,63}$`` (validated at registration
    time via :func:`mindsos_core.cypher.identifiers.validate_edge_type_identifier`;
    SENT-1 sentinel ``"UNSPECIFIED"`` is a deliberate fit for this regex).

    Symmetric across all members — no cardinality bounds (HET-1 lock);
    no per-position role constraints. Tester wanting "exactly N
    members of type X" must enforce in higher-layer code.
    """

    name: str
    allowed_member_types: FrozenSet[str] = field(default_factory=frozenset)
    property_types: Dict[str, PropertyType] = field(default_factory=dict)
    description: Optional[str] = None

    def __repr__(self) -> str:
        return f"HyperEdgeType({self.name!r})"


@dataclass(frozen=True)
class IntergraphEdgeType:
    """Declaration of a binary intergraph edge type (Phase 05b — ADR-0148).

    Used by :class:`MetagraphSchema` to validate ``IntergraphEdge``
    instances at metagraph factory time. Mirrors :class:`EdgeType`'s
    constraint surface (allowed sources/targets) but adds a second axis:
    *role-based graph constraints* via ``allowed_source_graphs`` /
    ``allowed_target_graphs``. Per Pushback 4-A (round-1 Phase 05b lock)
    the graph constraints check ``Graph.role`` (not ``Graph.name``), so
    a constraint like ``allowed_source_graphs=frozenset({"lexicon"})``
    matches any contained graph with ``role="lexicon"``.

    Empty frozenset on any allowed-* field means "any" — mirrors
    :class:`EdgeType` and :class:`HyperEdgeType` empty-set semantics.
    Per Pushback 4-A note: ``Graph.role=None`` is unmatchable when the
    constraint is non-empty (Python set membership: ``None not in
    frozenset({"lexicon"})``).

    The type ``name`` is used as the Cypher relationship identifier, so
    it MUST match ADR-0021's ``^[A-Z][A-Z0-9_]{0,63}$`` regex (validated
    at registration time via
    :func:`mindsos_core.cypher.identifiers.validate_edge_type_identifier`).

    Per Pushback 5-A, ``property_types`` enforcement gates only when the
    owning :class:`MetagraphSchema` has ``strict=True``; in non-strict
    mode types are registered but property values are not type-checked
    (parity with Phase 04 :class:`Schema` strict semantics).
    """

    name: str
    allowed_source_types: FrozenSet[str] = field(default_factory=frozenset)
    allowed_target_types: FrozenSet[str] = field(default_factory=frozenset)
    allowed_source_graphs: FrozenSet[str] = field(default_factory=frozenset)
    allowed_target_graphs: FrozenSet[str] = field(default_factory=frozenset)
    property_types: Dict[str, PropertyType] = field(default_factory=dict)
    description: Optional[str] = None

    def __repr__(self) -> str:
        return f"IntergraphEdgeType({self.name!r})"


@dataclass(frozen=True)
class IntergraphHyperEdgeType:
    """Declaration of an n-ary intergraph hyperedge type (Phase 05c — ADR-0148 amended).

    Used by :class:`MetagraphSchema` to validate
    :class:`IntergraphHyperEdge` instances at metagraph factory time.
    Mirrors :class:`IntergraphEdgeType`'s constraint surface (role-based
    graph constraints + node-type constraints + property-type map) but
    adds an ``ordered: bool`` flag controlling list-vs-set semantics for
    the ``anchors`` / ``members`` fields:

    * ``ordered=True`` (default per P18-A; permissive list semantics):
      preserve insertion order; allow duplicates within a side. The
      cat=c+a+t case requires this — word "letter" has
      ``members=[(lg,l), (lg,e), (lg,t), (lg,t), (lg,e), (lg,r)]`` with
      repeated characters.
    * ``ordered=False`` (opt-in via CLI ``--unordered``): canonicalize
      at construction (sort lexicographically by ``(graph_id, node_id)``
      then dedup). Set semantics. **Legal alongside ``compositional=True``
      since CORE-C2R2** — the P8-A refusal at the factory's validation
      step 10 is retired (ADR-0205 §amendment-3.1). Note the dedup runs
      BEFORE the cardinality check, so a set collapsing to 1-1 still
      refuses; use ``IntergraphEdge`` for the binary case.

    Per P9-A (no-schema default): when no MetagraphSchema is attached
    OR no IntergraphHyperEdgeType is registered for the ``type_name``,
    the factory treats as ``ordered=True`` (permissive list semantics; no
    canonicalization). Re-attach with conflicting ``ordered`` setting
    refuses per Pushback 7-A eager-validation contract.

    Empty frozenset on any allowed-* field means "any" — same convention
    as :class:`IntergraphEdgeType`. Per Pushback 4-A precedent,
    ``Graph.role=None`` is unmatchable when the role constraint is
    non-empty. The type ``name`` is the Cypher relationship identifier
    (ADR-0021 regex enforced at registration).

    Per Pushback 5-A precedent, ``property_types`` enforcement gates
    only when the owning :class:`MetagraphSchema` has ``strict=True``.
    """

    name: str
    allowed_anchor_types: FrozenSet[str] = field(default_factory=frozenset)
    allowed_member_types: FrozenSet[str] = field(default_factory=frozenset)
    allowed_anchor_graphs: FrozenSet[str] = field(default_factory=frozenset)
    allowed_member_graphs: FrozenSet[str] = field(default_factory=frozenset)
    ordered: bool = True  # P18-A — permissive default; opt-in to set semantics.
    property_types: Dict[str, PropertyType] = field(default_factory=dict)
    description: Optional[str] = None

    def __repr__(self) -> str:
        return f"IntergraphHyperEdgeType({self.name!r})"


@dataclass(frozen=True)
class MetaEdgeType:
    """Declaration of a binary meta-edge type (Phase 05d — ADR-0014 third amendment).

    Used by :class:`MetagraphSchema` to validate :class:`MetaEdge`
    instances at metagraph factory time. Connects GRAPHS within a
    metagraph (not nodes). Mirrors :class:`IntergraphEdgeType`'s
    constraint surface MINUS ``allowed_*_types`` because metaedge
    primitives connect graphs (not nodes).

    Per round-7 P44 A (mirror real 05b precedent), ``add_metaedge``
    validation order: containment → source≠target → properties bag → (if
    schema) ``require_meta_edge_type`` → ``validate_meta_edge`` →
    ``validate_meta_edge_properties`` (strict only) → register-and-construct
    (cypher regex via ``__post_init__``).

    Empty frozenset on any allowed-* field means "any" (mirrors
    :class:`EdgeType` / :class:`IntergraphEdgeType` precedent).
    ``Graph.role=None`` is unmatchable when the constraint is non-empty
    (Python set membership semantics).

    The type ``name`` is the Cypher relationship identifier (ADR-0021
    regex enforced at registration in :class:`MetagraphSchema`).

    Per Pushback 5-A precedent, ``property_types`` enforcement gates
    only when the owning :class:`MetagraphSchema` has ``strict=True``.
    """

    name: str
    allowed_source_graphs: FrozenSet[str] = field(default_factory=frozenset)
    allowed_target_graphs: FrozenSet[str] = field(default_factory=frozenset)
    property_types: Dict[str, PropertyType] = field(default_factory=dict)
    description: Optional[str] = None

    def __repr__(self) -> str:
        return f"MetaEdgeType({self.name!r})"


@dataclass(frozen=True)
class MetaHyperEdgeType:
    """Declaration of an n-ary meta-hyperedge type (Phase 05d — ADR-0014 third amendment).

    Used by :class:`MetagraphSchema` to validate :class:`MetaHyperEdge`
    instances at metagraph factory time. Connects N≥2 GRAPHS within a
    metagraph (graph-set semantics: uniqueness enforced at
    ``MetaHyperEdge.__post_init__`` line 194).

    **Deliberately omits ``ordered`` field (P1 C lock).** The 05c P18-A
    rationale (cat=c+a+t case requires duplicate node membership)
    applies ONLY to :class:`IntergraphHyperEdgeType` because its members
    are nodes (which can repeat). :class:`MetaHyperEdge` graph_ids are
    set-unique at construction; no duplicate-preservation use case
    exists. See memory ``reference_mindsos_four_edge_primitives.md``.

    **Deliberately omits ``allowed_member_types``** because metahyperedge
    primitives connect graphs (not nodes). Cardinality (n≥2) is enforced
    at the primitive (``metagraph.py:188-192``); type vocab adds role +
    property constraints only.

    Empty frozenset on ``allowed_member_graphs`` means "any" (mirrors
    sibling vocab precedent). ``Graph.role=None`` is unmatchable when
    non-empty.

    The type ``name`` is the Cypher relationship identifier (ADR-0021
    regex enforced at registration).
    """

    name: str
    allowed_member_graphs: FrozenSet[str] = field(default_factory=frozenset)
    property_types: Dict[str, PropertyType] = field(default_factory=dict)
    description: Optional[str] = None

    def __repr__(self) -> str:
        return f"MetaHyperEdgeType({self.name!r})"
