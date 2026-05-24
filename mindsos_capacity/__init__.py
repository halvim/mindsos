"""MindsOS Intellectual Capacity Layer — L3 public API (Phase 27 slim).

Phase 27 ships the L3 read-side definitions only:

- DataStates (``DataState`` + ``ShapeDescriptor`` + structural-shape
  helpers ``strict_compatible`` / ``list_of_compat`` / ``validate_
  datastate``).
- Capacity / Monitor / Adapter dataclasses with stable IRI form
  ``capacity:<category>:<name>`` (ADR-0066) and
  ``_CapacityBase.validate_for_registration``.
- Vocabulary: 12 functional categories, 4 node types, 4 node kinds,
  4 edge types, 5 constraint kinds, 5 ref keys, REF_TYPES (6-member
  subset of L2 per ADR-0067 §amendment-1).

Excluded from Phase 27 (defer per PHASE_MAP):

- ``CapacityLayer`` registry + bootstrap (Phase 28).
- Discovery / TYPE_COMPAT (Phase 29).
- Pipeline finder + invocation runtime + ``InvocationResult`` /
  ``call_capacity`` exports (Phase 30). NOTE: the dataclass +
  function live in ``capacity.py`` already, but are NOT exported
  via this ``__init__.py`` until Phase 30.
- Residents + builtins (Phase 31).
- Write capacities + ``SessionProtocol`` / ``SessionArg`` typing
  surface (Phases 33–35).

See ``confirmation_docs/PHASE_27_DESIGN_LOG.md`` for the full design
rounds + picks.
"""

from __future__ import annotations

from .capacity import (
    Adapter,
    Capacity,
    CapacityCallable,
    Monitor,
    _CapacityBase,
)
from .datastate import (
    DataState,
    ShapeDescriptor,
    list_of_compat,
    strict_compatible,
    validate_datastate,
)
from .exceptions import (
    CapacityLayerError,
    CapacityRegistrationError,
    DataStateError,
)
from .identifiers import (
    CATEGORY_COMBINATION,
    CATEGORY_COMPREHENSION,
    CATEGORY_DECOMPOSITION,
    CATEGORY_DERIVATION,
    CATEGORY_INTERACTION,
    CATEGORY_LEARNING_METHODS,
    CATEGORY_PATH_FINDING,
    CATEGORY_PERCEPTION,
    CATEGORY_RETRIEVAL,
    CATEGORY_SCORING,
    CATEGORY_SIGNALLING,
    CATEGORY_TRACE,
    CONSTRAINT_KINDS,
    CONSTRAINT_MANDATORY_BEFORE,
    CONSTRAINT_MUTUALLY_EXCLUSIVE,
    CONSTRAINT_RATE_LIMIT,
    CONSTRAINT_REQUIRES_APPROVAL,
    CONSTRAINT_REQUIRES_L2_VERSION,
    EDGE_CONSTRAINT,
    EDGE_CONSUMES,
    EDGE_PRODUCES,
    EDGE_TYPE_COMPAT,
    FUNCTIONAL_CATEGORIES,
    GLOBAL_FALKOR_GRAPH,
    GLOBAL_METAGRAPH_NAME,
    KIND_ADAPTER,
    KIND_DATASTATE,
    KIND_REACTIVE,
    KIND_RESIDENT,
    LOCAL_FALKOR_GRAPH_FMT,
    LOCAL_METAGRAPH_NAME_FMT,
    NODE_KINDS,
    NODE_TYPE_ADAPTER,
    NODE_TYPE_CAPACITY,
    NODE_TYPE_DATASTATE,
    NODE_TYPE_MONITOR,
    NODE_TYPES,
    REF_CAPACITY,
    REF_DATASTATE,
    REF_GLOBAL_CAPACITY,
    REF_GLOBAL_DATASTATE,
    REF_TYPE_KEY,
    REF_TYPES,
    RESERVED_PROPERTY_KEYS,
    ROLE_DATASTATES,
    capacity_iri,
    category_role,
    datastate_iri,
    falkor_graph_name,
    parse_capacity_iri,
    parse_datastate_iri,
    slugify_user_id,
)


__all__ = [
    # Node declarations (dataclasses)
    "Capacity",
    "Monitor",
    "Adapter",
    "_CapacityBase",
    "CapacityCallable",
    "DataState",
    "ShapeDescriptor",
    # Compatibility helpers
    "strict_compatible",
    "list_of_compat",
    "validate_datastate",
    # Exceptions (base + 2 raisers; remaining 4 ship Phase 28-31)
    "CapacityLayerError",
    "CapacityRegistrationError",
    "DataStateError",
    # Identifiers — names + builders
    "GLOBAL_METAGRAPH_NAME",
    "LOCAL_METAGRAPH_NAME_FMT",
    "GLOBAL_FALKOR_GRAPH",
    "LOCAL_FALKOR_GRAPH_FMT",
    "ROLE_DATASTATES",
    "slugify_user_id",
    "falkor_graph_name",
    "capacity_iri",
    "datastate_iri",
    "parse_capacity_iri",
    "parse_datastate_iri",
    "category_role",
    # Identifiers — vocabulary
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
    "EDGE_TYPE_COMPAT",
    "EDGE_CONSTRAINT",
    "EDGE_PRODUCES",
    "EDGE_CONSUMES",
    "CONSTRAINT_KINDS",
    "CONSTRAINT_MANDATORY_BEFORE",
    "CONSTRAINT_MUTUALLY_EXCLUSIVE",
    "CONSTRAINT_RATE_LIMIT",
    "CONSTRAINT_REQUIRES_APPROVAL",
    "CONSTRAINT_REQUIRES_L2_VERSION",
    "REF_GLOBAL_CAPACITY",
    "REF_GLOBAL_DATASTATE",
    "REF_CAPACITY",
    "REF_DATASTATE",
    "REF_TYPE_KEY",
    "REF_TYPES",
    "RESERVED_PROPERTY_KEYS",
]

__version__ = "0.0.0+phase27"
