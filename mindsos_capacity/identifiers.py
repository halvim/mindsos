"""Stable identifiers, role conventions, and vocabulary for L3.

The Intellectual Capacity Layer is structured as two Core Metagraphs
(Global + Local, §3.1). Each metagraph contains:

- One shared :data:`ROLE_DATASTATES` graph with every ``DataState`` node.
- One graph per functional category (``capacity:<category>``) holding
  the ``Capacity`` / ``Monitor`` / ``Adapter`` nodes of that category.

This module owns:

- The role-name constants that name those graphs.
- The DataState- and capacity-id builders that produce stable IRIs
  (analogous to :mod:`mindsos_knowledge.identifiers`).
- The node-kind, edge-type, and constraint-kind vocabularies.
- The ``ref:*`` property keys used to reference across metagraphs.

Phase 27 ships the full vocabulary + IRI builders. ADR-0066
§Implementation footer documents the staging: Phase 27 ships the IRI
form + parser; Phase 28 ships the registry-side collision detection
via ``CapacityLayer.register``.

ADR-0067 §amendment-1 documents the REF_TYPES contract: L3.REF_TYPES
is a 6-member subset of L2.REF_TYPES; the parity test asserts
``L3 ⊆ L2`` and ``L2 - L3 == {"PROMOTED"}``. ``PROMOTED`` is
L2-exclusive (no L3 promotion lifecycle).
"""

from __future__ import annotations

import re
from typing import FrozenSet


# ── Metagraph names ─────────────────────────────────────────────────────

GLOBAL_METAGRAPH_NAME = "global_capacity"
LOCAL_METAGRAPH_NAME_FMT = "local_capacity:{user_id}"

#: Conventional FalkorDB graph names (mirrors KL's §9.3 convention).
GLOBAL_FALKOR_GRAPH = "mindsos_capacity_global"
LOCAL_FALKOR_GRAPH_FMT = "mindsos_capacity_local_{user_slug}"

_USER_SLUG_RE = re.compile(r"[^A-Za-z0-9_-]")


def slugify_user_id(user_id: str) -> str:
    """Sanitise ``user_id`` for use in a FalkorDB graph name."""
    if not isinstance(user_id, str) or not user_id:
        raise ValueError(f"user_id must be a non-empty string, got {user_id!r}")
    return _USER_SLUG_RE.sub("_", user_id)


def falkor_graph_name(user_id=None) -> str:
    """FalkorDB graph name for Global (``user_id=None``) or Local."""
    if user_id is None:
        return GLOBAL_FALKOR_GRAPH
    return LOCAL_FALKOR_GRAPH_FMT.format(user_slug=slugify_user_id(user_id))


# ── Functional-category role names ──────────────────────────────────────

#: The shared DataState graph — its role.
ROLE_DATASTATES = "capacity:datastates"


def category_role(category: str) -> str:
    """Return the role string for a functional category (``capacity:<category>``)."""
    if not isinstance(category, str) or not category:
        raise ValueError(f"category must be a non-empty string, got {category!r}")
    if category.startswith("capacity:"):
        return category
    return f"capacity:{category}"


# The twelve functional categories called out in the L3 plan §3.1.
CATEGORY_PERCEPTION = "perception"
CATEGORY_COMPREHENSION = "comprehension"
CATEGORY_DERIVATION = "derivation"
CATEGORY_DECOMPOSITION = "decomposition"
CATEGORY_COMBINATION = "combination"
CATEGORY_PATH_FINDING = "path-finding"
CATEGORY_RETRIEVAL = "retrieval"
CATEGORY_SCORING = "scoring"
CATEGORY_TRACE = "trace"
CATEGORY_SIGNALLING = "signalling"
CATEGORY_INTERACTION = "interaction"
CATEGORY_LEARNING_METHODS = "learning-methods"

#: Functional categories recognised by the default Global L3 bootstrap.
FUNCTIONAL_CATEGORIES: FrozenSet[str] = frozenset({
    CATEGORY_PERCEPTION,
    CATEGORY_COMPREHENSION,
    CATEGORY_DERIVATION,
    CATEGORY_DECOMPOSITION,
    CATEGORY_COMBINATION,
    CATEGORY_PATH_FINDING,
    CATEGORY_RETRIEVAL,
    CATEGORY_SCORING,
    CATEGORY_TRACE,
    CATEGORY_SIGNALLING,
    CATEGORY_INTERACTION,
    CATEGORY_LEARNING_METHODS,
})


# ── Core node-type vocabulary (types stored on every L3 node) ──────────

#: Node types the Core schema validates against.
NODE_TYPE_CAPACITY = "Capacity"
NODE_TYPE_MONITOR = "Monitor"
NODE_TYPE_ADAPTER = "Adapter"
NODE_TYPE_DATASTATE = "DataState"

NODE_TYPES: FrozenSet[str] = frozenset({
    NODE_TYPE_CAPACITY,
    NODE_TYPE_MONITOR,
    NODE_TYPE_ADAPTER,
    NODE_TYPE_DATASTATE,
})

#: ``node_kind`` property value — used by L4 to decide runtime handling.
KIND_REACTIVE = "reactive"
KIND_RESIDENT = "resident"
KIND_ADAPTER = "adapter"
KIND_DATASTATE = "datastate"

NODE_KINDS: FrozenSet[str] = frozenset({
    KIND_REACTIVE, KIND_RESIDENT, KIND_ADAPTER, KIND_DATASTATE,
})


# ── Core edge-type vocabulary ──────────────────────────────────────────

#: Type-compatibility edge — capacity→capacity flow edge.
EDGE_TYPE_COMPAT = "TYPE_COMPAT"
#: Constraint edge — admin-authored restriction on pipelines.
EDGE_CONSTRAINT = "CONSTRAINT"
#: Reifies "capacity produces/consumes this DataState" inside the flow graph.
EDGE_PRODUCES = "PRODUCES"
EDGE_CONSUMES = "CONSUMES"


# ── Constraint-kind vocabulary ─────────────────────────────────────────

CONSTRAINT_MANDATORY_BEFORE = "MANDATORY_BEFORE"
CONSTRAINT_MUTUALLY_EXCLUSIVE = "MUTUALLY_EXCLUSIVE"
CONSTRAINT_RATE_LIMIT = "RATE_LIMIT"
CONSTRAINT_REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
CONSTRAINT_REQUIRES_L2_VERSION = "REQUIRES_L2_VERSION"

CONSTRAINT_KINDS: FrozenSet[str] = frozenset({
    CONSTRAINT_MANDATORY_BEFORE,
    CONSTRAINT_MUTUALLY_EXCLUSIVE,
    CONSTRAINT_RATE_LIMIT,
    CONSTRAINT_REQUIRES_APPROVAL,
    CONSTRAINT_REQUIRES_L2_VERSION,
})


# ── Stable-IRI builders ────────────────────────────────────────────────

_CAPACITY_NAME_RE = re.compile(r"^[a-z][a-z0-9_.\-]*$")
_DATASTATE_NAME_RE = re.compile(r"^[a-z][a-z0-9_.\-]*$")


def capacity_iri(category: str, name: str) -> str:
    """Return the stable IRI for a capacity node.

    Format: ``capacity:<category>:<name>``.

    ``name`` follows the ``<family>.<subname>[.<variant>]`` convention,
    e.g. ``text.space_split``. The combined IRI is what L4 and MM
    instances dereference.
    """
    if category.startswith("capacity:"):
        category = category[len("capacity:") :]
    if not isinstance(category, str) or not category:
        raise ValueError(f"category must be a non-empty string, got {category!r}")
    if not isinstance(name, str) or not _CAPACITY_NAME_RE.match(name):
        raise ValueError(
            f"capacity name must match {_CAPACITY_NAME_RE.pattern!r}, got {name!r}"
        )
    return f"capacity:{category}:{name}"


def datastate_iri(name: str) -> str:
    """Return the stable IRI for a DataState node.

    Format: ``datastate:<name>``.
    """
    if not isinstance(name, str) or not _DATASTATE_NAME_RE.match(name):
        raise ValueError(
            f"datastate name must match {_DATASTATE_NAME_RE.pattern!r}, got {name!r}"
        )
    return f"datastate:{name}"


def parse_capacity_iri(iri: str):
    """Return ``(category, name)`` for a well-formed capacity IRI.

    Raises :class:`ValueError` on malformed input.
    """
    if not isinstance(iri, str) or not iri.startswith("capacity:"):
        raise ValueError(f"Not a capacity IRI: {iri!r}")
    rest = iri[len("capacity:") :]
    if ":" not in rest:
        raise ValueError(f"Capacity IRI missing category: {iri!r}")
    category, name = rest.split(":", 1)
    return category, name


def parse_datastate_iri(iri: str) -> str:
    """Return the DataState name for a well-formed datastate IRI."""
    if not isinstance(iri, str) or not iri.startswith("datastate:"):
        raise ValueError(f"Not a DataState IRI: {iri!r}")
    return iri[len("datastate:") :]


# ── Ref-property keys (mirrors KL conventions) ─────────────────────────

#: Property key on a Local capacity node referencing its Global counterpart.
REF_GLOBAL_CAPACITY = "ref:global_capacity"
#: Property key on a Local DataState node referencing its Global counterpart.
REF_GLOBAL_DATASTATE = "ref:global_datastate"
#: Property key on an MM instance / promoted-pipeline record referring back
#: to an L3 capacity node (intra-KL form used in L2 role-graphs).
REF_CAPACITY = "ref:capacity"
REF_DATASTATE = "ref:datastate"

#: ``ref_type`` key — re-uses KL's vocabulary.
#: ADR-0067 §amendment-1: L3.REF_TYPES is a 6-member subset of L2's
#: 7-member set; ``PROMOTED`` is L2-exclusive (L3 has no promotion
#: lifecycle).
REF_TYPE_KEY = "ref_type"
REF_TYPES: FrozenSet[str] = frozenset({
    "SPECIALISES",
    "INSTANCE_OF",
    "RENAMES",
    "EXTENDS",
    "CONTRADICTS",
    "PROXY",
})


# ── Reserved property keys (may not be supplied by callers) ────────────

#: Property keys L3 sets implicitly and rejects from ``properties``.
RESERVED_PROPERTY_KEYS: FrozenSet[str] = frozenset({
    REF_GLOBAL_CAPACITY,
    REF_GLOBAL_DATASTATE,
    REF_TYPE_KEY,
    "inputs",
    "outputs",
    "node_kind",
    "category",
    "shape_kind",
    "is_adapter",
})


__all__ = [
    # Metagraph names
    "GLOBAL_METAGRAPH_NAME",
    "LOCAL_METAGRAPH_NAME_FMT",
    "GLOBAL_FALKOR_GRAPH",
    "LOCAL_FALKOR_GRAPH_FMT",
    "slugify_user_id",
    "falkor_graph_name",
    # Role names
    "ROLE_DATASTATES",
    "category_role",
    # Categories
    "CATEGORY_PERCEPTION",
    "CATEGORY_COMPREHENSION",
    "CATEGORY_DERIVATION",
    "CATEGORY_DECOMPOSITION",
    "CATEGORY_COMBINATION",
    "CATEGORY_PATH_FINDING",
    "CATEGORY_RETRIEVAL",
    "CATEGORY_SCORING",
    "CATEGORY_TRACE",
    "CATEGORY_SIGNALLING",
    "CATEGORY_INTERACTION",
    "CATEGORY_LEARNING_METHODS",
    "FUNCTIONAL_CATEGORIES",
    # Node-type vocabulary
    "NODE_TYPE_CAPACITY",
    "NODE_TYPE_MONITOR",
    "NODE_TYPE_ADAPTER",
    "NODE_TYPE_DATASTATE",
    "NODE_TYPES",
    "KIND_REACTIVE",
    "KIND_RESIDENT",
    "KIND_ADAPTER",
    "KIND_DATASTATE",
    "NODE_KINDS",
    # Edge-type vocabulary
    "EDGE_TYPE_COMPAT",
    "EDGE_CONSTRAINT",
    "EDGE_PRODUCES",
    "EDGE_CONSUMES",
    # Constraints
    "CONSTRAINT_MANDATORY_BEFORE",
    "CONSTRAINT_MUTUALLY_EXCLUSIVE",
    "CONSTRAINT_RATE_LIMIT",
    "CONSTRAINT_REQUIRES_APPROVAL",
    "CONSTRAINT_REQUIRES_L2_VERSION",
    "CONSTRAINT_KINDS",
    # IRIs
    "capacity_iri",
    "datastate_iri",
    "parse_capacity_iri",
    "parse_datastate_iri",
    # Ref keys
    "REF_GLOBAL_CAPACITY",
    "REF_GLOBAL_DATASTATE",
    "REF_CAPACITY",
    "REF_DATASTATE",
    "REF_TYPE_KEY",
    "REF_TYPES",
    "RESERVED_PROPERTY_KEYS",
]
