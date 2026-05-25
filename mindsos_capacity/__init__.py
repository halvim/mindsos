"""MindsOS Intellectual Capacity Layer — L3 public API (through Phase 29).

Phase 27 shipped the L3 read-side definitions; Phase 28 ships the
registry + bootstrap + Local-wins lookup + capability gate; Phase 29
ships TYPE_COMPAT auto-discovery + ``SuccessorHop`` + the
successors/producers/consumers walks + ``rediscover``. Cumulative
surface as of Phase 29:

- DataStates (``DataState`` + ``ShapeDescriptor`` + structural-shape
  helpers ``strict_compatible`` / ``list_of_compat`` /
  ``validate_datastate``) — Phase 27.
- Capacity / Monitor / Adapter dataclasses with stable IRI form
  ``capacity:<category>:<name>`` (ADR-0066) and
  ``_CapacityBase.validate_for_registration`` — Phase 27.
- Vocabulary: 12 functional categories, 4 node types, 4 node kinds,
  4 edge types, 5 constraint kinds, 5 ref keys, REF_TYPES (6-member
  subset of L2 per ADR-0067 §amendment-1) — Phase 27.
- ``CapacityLayer`` registry — register Capacity/Monitor/Adapter into
  Global or per-user Local metagraphs; Local-wins lookup
  (``_resolve_declaration``) per ADR-0061; collision detection per
  ADR-0066 §Implementation (Phase 28) — Phase 28.
- Bootstrap helpers — ``create_global`` (12 categories + DataStates per
  ADR-0064 + ADR-0065), ``create_local``, ``ensure_role_graph``,
  ``ensure_category_graph``, ``ensure_datastate_graph`` — Phase 28.
- Capability gate — ``CAN_WRITE_GLOBAL`` constant + parity test against
  ``mindsos_server.capabilities`` per ADR-0078 §amendment-1; ADR-0080
  bootstrap carve-out (``session=None`` permits Global writes) — Phase 28.
- ``SessionProtocol`` + ``SessionArg`` slim typing surface per
  ADR-0040 §amendment-2 — Phase 28.
- Schemas — ``schema_for_role`` + ``build_datastates_schema`` +
  ``build_category_schema`` per ADR-0064 + ADR-0065 — Phase 28.
- ``CapacityLayerView`` — read-only accessors + successor /
  producer / consumer walks over an L3 metagraph (Phase 28 accessors +
  Phase 29 walks).
- ``ConstraintViolationError`` — admin CONSTRAINT edge enforcement —
  Phase 28.
- ``SuccessorHop`` dataclass — one TYPE_COMPAT step (source +
  target + via_datastate + same_category + strictness +
  adapter_capacity) — Phase 29.
- ``discover_for_capacity`` / ``discover_for_datastate`` /
  ``rediscover_all`` — auto-discovery substrate per ADR-0069 +
  ADR-0086 — Phase 29. Wired internally by
  ``CapacityLayer.register_capacity`` / ``register_datastate`` /
  ``rediscover`` — exported as free functions for direct callers
  (admin tooling, tests).
- ``CapacityLayer.rediscover`` — drop auto edges + recompute (manual
  edges preserved per ADR-0086) — Phase 29.
- ``DiscoveryFailedError`` — sub of ``CapacityRegistrationError``;
  raised when auto-discovery writes fail mid-register or
  mid-rediscover (partial-write state observable to callers) —
  Phase 29.

Excluded (defer):

- Pipeline finder + invocation runtime + ``invoke`` + ``start_resident``
  + ``problem_trace`` + ``InvocationResult`` / ``call_capacity``
  exports — Phase 30. ``InvocationResult`` / ``call_capacity`` live in
  ``capacity.py`` already but are NOT exported from this ``__init__.py``
  until Phase 30 (sentinel test at
  ``tests/phase_28/test_invocation_not_exported.py`` enforces).
- ``mindsos capacity`` CLI Typer group + ``add_type_compat`` admin
  API + ``docs/usage/capacity/building.md`` substantive content —
  Phase 30.
- Residents + text builtins — Phase 31.
- Write capacities + per-flow validators — Phases 33-35 (full
  ``types.py`` deprecation shim may also land here if needed).
- L4 problem-trace persistence — out of scope (L4 in design per
  PHASE_MAP §1).

See ``confirmation_docs/PHASE_28_DESIGN_LOG.md`` +
``PHASE_29_DESIGN_LOG.md`` for the full design rounds + picks.
"""

from __future__ import annotations

from .bootstrap import (
    create_global,
    create_local,
    ensure_category_graph,
    ensure_datastate_graph,
    ensure_role_graph,
)
from .capabilities import CAN_WRITE_GLOBAL
from .capacity import (
    Adapter,
    Capacity,
    CapacityCallable,
    Monitor,
    _CapacityBase,
)
from .capacity_layer import CapacityLayer
from .datastate import (
    DataState,
    ShapeDescriptor,
    list_of_compat,
    strict_compatible,
    validate_datastate,
)
from .discovery import (
    discover_for_capacity,
    discover_for_datastate,
    rediscover_all,
)
from .exceptions import (
    CapacityLayerError,
    CapacityRegistrationError,
    ConstraintViolationError,
    DataStateError,
    DiscoveryFailedError,
)
from .schemas import (
    build_category_schema,
    build_datastates_schema,
    schema_for_role,
)
from .types import SessionArg, SessionProtocol
from .views import CapacityLayerView, SuccessorHop
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
    # Exceptions (base + 4 raisers as of Phase 29; remaining 3 ship Phase 30-31)
    "CapacityLayerError",
    "CapacityRegistrationError",
    "ConstraintViolationError",
    "DataStateError",
    "DiscoveryFailedError",
    # Phase 28 — CapacityLayer registry + views
    "CapacityLayer",
    "CapacityLayerView",
    # Phase 29 — TYPE_COMPAT auto-discovery + successor walks
    "SuccessorHop",
    "discover_for_capacity",
    "discover_for_datastate",
    "rediscover_all",
    # Phase 28 — bootstrap helpers
    "create_global",
    "create_local",
    "ensure_role_graph",
    "ensure_category_graph",
    "ensure_datastate_graph",
    # Phase 28 — capability gate + session typing
    "CAN_WRITE_GLOBAL",
    "SessionProtocol",
    "SessionArg",
    # Phase 28 — schema builders
    "schema_for_role",
    "build_datastates_schema",
    "build_category_schema",
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

__version__ = "0.0.0+phase29"
