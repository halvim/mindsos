"""DOLCE + full-OWL ontology schema (Phase 13 PB-1 / PB-4).

Ports v3 ``mindsos_knowledge/schemas/ontology.py`` (10 NodeTypes + 13
EdgeTypes) and lifts v3's 7 hyperedge "label" constants to
``HyperEdgeType`` registrations per Phase 13 PB-4 — closes the v3
label-constants-only drift now that Phase 04-v2's ``HyperEdgeType`` ships
in ``mindsos_core``.

The schema is intentionally ``strict=False`` per Phase 13 PB-3 +
ADR-0149. OWL's property space is open — individual property nodes
carry arbitrary metadata (domains, ranges, characteristics) that
Phase 13 deliberately doesn't pin. Strict typing on core structural
props is enforced in higher-layer code (Phase 36 hybrid validators).

**Ordering note for hyperedges.** Phase 04-v2's ``HyperEdgeType`` has
no ``ordered`` field — every type is symmetric across members. The
ordering claim for ``PROPERTY_CHAIN`` (and the unordered-set claim for
``ALL_DISJOINT_CLASSES`` etc.) is preserved at the **instance** level:
``HyperEdge.members`` is a ``list`` whose insertion order is preserved.
The Schema doesn't pin ordering semantics — that's an importer
discipline (Phase 15).
"""

from __future__ import annotations

from mindsos_core import EdgeType, HyperEdgeType, NodeType

from ._base import Discipline, L2Schema


# ── Node types ─────────────────────────────────────────────────────────

NODE_CLASS = "Class"
NODE_INDIVIDUAL = "Individual"
NODE_OBJECT_PROPERTY = "ObjectProperty"
NODE_DATA_PROPERTY = "DataProperty"
NODE_ANNOTATION_PROPERTY = "AnnotationProperty"
NODE_RESTRICTION = "Restriction"
NODE_CLASS_EXPRESSION = "ClassExpression"
NODE_DATATYPE = "Datatype"
NODE_DATATYPE_RESTRICTION = "DatatypeRestriction"
NODE_AXIOM = "Axiom"

ONTOLOGY_NODE_TYPES: tuple[str, ...] = (
    NODE_CLASS,
    NODE_INDIVIDUAL,
    NODE_OBJECT_PROPERTY,
    NODE_DATA_PROPERTY,
    NODE_ANNOTATION_PROPERTY,
    NODE_RESTRICTION,
    NODE_CLASS_EXPRESSION,
    NODE_DATATYPE,
    NODE_DATATYPE_RESTRICTION,
    NODE_AXIOM,
)


# ── Edge types (binary) ────────────────────────────────────────────────

EDGE_SUBCLASS_OF = "SUBCLASS_OF"
EDGE_DISJOINT_WITH = "DISJOINT_WITH"
EDGE_EQUIVALENT_TO = "EQUIVALENT_TO"
EDGE_TYPE_OF = "TYPE_OF"
EDGE_DOMAIN = "DOMAIN"
EDGE_RANGE = "RANGE"
EDGE_INVERSE_OF = "INVERSE_OF"
EDGE_SUBPROPERTY_OF = "SUBPROPERTY_OF"
EDGE_SAME_AS = "SAME_AS"
EDGE_DIFFERENT_FROM = "DIFFERENT_FROM"
EDGE_RESTRICTS_PROPERTY = "RESTRICTS_PROPERTY"
EDGE_HAS_FILLER = "HAS_FILLER"
EDGE_ON_DATATYPE = "ON_DATATYPE"

ONTOLOGY_EDGE_TYPES: tuple[str, ...] = (
    EDGE_SUBCLASS_OF,
    EDGE_DISJOINT_WITH,
    EDGE_EQUIVALENT_TO,
    EDGE_TYPE_OF,
    EDGE_DOMAIN,
    EDGE_RANGE,
    EDGE_INVERSE_OF,
    EDGE_SUBPROPERTY_OF,
    EDGE_SAME_AS,
    EDGE_DIFFERENT_FROM,
    EDGE_RESTRICTS_PROPERTY,
    EDGE_HAS_FILLER,
    EDGE_ON_DATATYPE,
)


# ── Hyperedge types (Phase 13 PB-4 — lifted from v3 label constants) ───

HE_INTERSECTION_OF = "INTERSECTION_OF"
HE_UNION_OF = "UNION_OF"
HE_ONE_OF = "ONE_OF"
HE_PROPERTY_CHAIN = "PROPERTY_CHAIN"
HE_DISJOINT_UNION_OF = "DISJOINT_UNION_OF"
HE_ALL_DISJOINT_CLASSES = "ALL_DISJOINT_CLASSES"
HE_ALL_DIFFERENT = "ALL_DIFFERENT"

ONTOLOGY_HYPEREDGE_TYPES: tuple[str, ...] = (
    HE_INTERSECTION_OF,
    HE_UNION_OF,
    HE_ONE_OF,
    HE_PROPERTY_CHAIN,
    HE_DISJOINT_UNION_OF,
    HE_ALL_DISJOINT_CLASSES,
    HE_ALL_DIFFERENT,
)


def build_ontology_schema(strict: bool = False) -> L2Schema:
    """Construct the DOLCE/OWL ontology Schema (Phase 13 PB-1 + PB-4).

    Args:
        strict: Default ``False`` per PB-3 / ADR-0149. OWL property space
            is open — strict tightening is a follow-up PR with the
            inventory helper (deferred to first-consumer phase).
    """
    s = L2Schema(
        mutation_discipline=Discipline.ADMIN_AUTHORED, strict=strict
    )

    for nt in ONTOLOGY_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    # Edge constraints: sources/targets allow any node type, since
    # e.g. SUBCLASS_OF can target a Class, a Restriction, or a
    # ClassExpression. Structural endpoint typing only.
    any_node = frozenset(ONTOLOGY_NODE_TYPES)

    for et in ONTOLOGY_EDGE_TYPES:
        s.add_edge_type(EdgeType(et, any_node, any_node))

    # PB-4 — lift the 7 hyperedge labels to HyperEdgeType registrations.
    # ``allowed_member_types`` permits any ontology NodeType; ordering
    # semantics live at HyperEdge instance level (see module docstring).
    for het in ONTOLOGY_HYPEREDGE_TYPES:
        s.add_hyperedge_type(HyperEdgeType(het, any_node))

    return s
