"""MindsOS Intellectual Capacity Layer — L3 public API (through Phase 31).

Phase 27 shipped the L3 read-side definitions; Phase 28 shipped the
registry + bootstrap + Local-wins lookup + capability gate; Phase 29's
type-compatibility auto-discovery was superseded by the ADR-0156
bipartite topology (Phase 42 — explicit PRODUCES/CONSUMES edges +
edge-sourced successor/producer/consumer walks); Phase 30 shipped
the invocation runtime + BFS pipeline finder + problem-trace primitives
+ first ``mindsos capacity`` CLI verbs. Phase 31 ships residents
(descriptive; per-layer registry) + text builtins (opt-in
``install_text_capacities``) + the ``mindsos capacity invoke`` CLI verb
(hybrid exit codes). Cumulative surface as of Phase 31:

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
- ``CapacityLayerView`` — read-only accessors + edge-sourced
  successor / producer / consumer walks (``successors_of`` /
  ``producers_of`` / ``consumers_of`` / ``inputs_of`` / ``outputs_of``)
  over an L3 metagraph (Phase 28 accessors + ADR-0156 bipartite walks).
- ``ConstraintViolationError`` — admin CONSTRAINT edge enforcement —
  Phase 28.
- Bipartite topology (ADR-0156, Phase 42): ``register_capacity`` emits
  explicit ``PRODUCES`` / ``CONSUMES`` IntergraphEdges; the Phase 29
  type-compatibility auto-discovery module + ``SuccessorHop`` +
  ``rediscover`` + the discovery write-failure exception were retired.
- ``InvocationResult`` + ``call_capacity`` — invocation envelope +
  callable dispatch (shipped to ``capacity.py`` since Phase 27 for
  layout parity; public re-export lifted at Phase 30 per ADR-0066
  §Implementation Phase-30 footer) — Phase 30.
- ``invoke`` (free function) + ``CapacityLayer.invoke`` (method) —
  reactive invocation with ADR-0072 envelope semantics (never raises
  for implementation errors; raises only for L3 invariants like unknown
  IRI). ADR-0072 §amendment-1 records the field rename
  (``success: bool`` + ``error`` vs original §Decision's ``failed``
  + ``exception``) — Phase 30.
- ``ProblemTraceRecord`` + ``ProblemTraceSink`` + ``emit_problem_trace``
  — in-memory anomaly sink per ADR-0074. One sink per ``CapacityLayer``
  instance (``self.problem_trace``); multi-tenant provenance via the
  payload dict; L4 drains and persists to L2 ``problem-trace``
  role-graph — Phase 30.
- ``Pipeline`` + ``PipelineStep`` + ``find_pipeline`` — datastate-keyed
  BFS over the bipartite PRODUCES/CONSUMES edge set (ADR-0071 +
  ADR-0156). Shortest-by-capacity-count; raises ``PipelineNotFoundError``
  on exhaustion; ignores constraints (L4 filters post-hoc) — Phase 30.
  Pathfinding-as-registered-builtin retires at Phase 31 per ADR-0071
  §Implementation (Phase 31) footer; ``find_pipeline`` (function-form)
  is canonical.
- ``PipelineNotFoundError`` + ``ProblemTraceError`` — Phase 30 raisers.
- Monitor lifecycle (the Phase 31 descriptive subscription handle +
  per-layer registry + lifecycle methods) **relocated to the L4
  substrate in Phase 41** per ADR-0155. L3 now ships only the
  ``Monitor`` declaration + ``CapacityLayer.iter_monitors()``
  enumeration producer (consumed by the L4 ``MonitorSubscriptionRegistry``
  at Phase 46) — Phase 41.
- ``mindsos_capacity.builtins`` (subpackage) — first builtins family:
  text DataStates (``text.raw`` / ``text.tokens`` / ``text.sentences``)
  + capacities (``text.space_split`` / ``text.sentence_split``) +
  ``install_text_capacities`` (idempotent with partial-state detection
  per R1 PB-12). NOT re-exported at this top level per R0 PB-5; users
  import from ``mindsos_capacity.builtins`` directly — Phase 31.
- ``mindsos capacity invoke`` CLI verb (hybrid exit codes per R0 PB-7:
  ``--json`` always exits 0; ``--human`` exits 0/1/3 by envelope state)
  — Phase 31.

Excluded (defer):

- ``add_type_compat`` admin API — retired entirely with the Phase 29
  type-compatibility substrate per ADR-0156 (Phase 42).
- Pathfinding-as-registered-builtin Capacity (parent's
  ``build_bfs_capacity_declaration`` stub) — RETIRED at Phase 31
  per ADR-0071 §Implementation (Phase 31) + PHASE_MAP §31 inline
  amendment. ``find_pipeline`` function-form is canonical.
- Write capacities + per-flow validators + KLWriteHandle — Phases 33-35.
- L4 problem-trace drain + persistence to L2 ``problem-trace``
  role-graph — out of scope (L4 in design per PHASE_MAP §1).
- L4 resident scheduling / state-snapshot lifecycle per ADR-0099 —
  L4-owned; L3 ships only the descriptive contract.
- ``include_deprecated`` parameter discipline across L3 walks —
  deferred to L4 follow-up plan per Phase 38 R4-PB-D (was: "Phase
  30+ when soft-delete becomes a real L4 concern").
- Per-user (Local-scoped) ProblemTraceSink dict — deferred to L4 per
  R2 PB-29(a) lock.
- Falkor-backed L3 bootstrap + state-file serialization — deferred
  to L4 follow-up plan per Phase 38 R4-PB-D + R3-PB-A (was: "Phase
  32+ per Phase 30 R2 PB-27(a) carry-forward"; depends on
  ``FalkorDBLocalPersister``, unshipped at Phase 36).
- ``--session-token`` CLI flag — deferred to L4 follow-up plan per
  Phase 38 R4-PB-D + R3-PB-B (was: "Phase 32+ per Phase 30 R2
  PB-30(a) carry-forward").
- ``--install-builtins=<family,...>`` CLI flag on ``invoke`` —
  deferred to L4 follow-up plan per Phase 38 R4-PB-D (was: "Phase
  32+ when a second builtins family ships per R3 PB-29 lock").

See ``confirmation_docs/PHASE_28_DESIGN_LOG.md`` +
``PHASE_29_DESIGN_LOG.md`` + ``PHASE_30_DESIGN_LOG.md`` for the full
design rounds + picks (Phase 31 design pre-R0 through R5 documented in
``confirmation_docs/PHASE_31_CONFIRMED.md`` tester_notes).
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
    DreamCapacity,
    InvocationResult,
    Monitor,
    _CapacityBase,
    call_capacity,
)
from .capacity_layer import CapacityLayer
from .datastate import (
    DataState,
    ShapeDescriptor,
    list_of_compat,
    strict_compatible,
    validate_datastate,
)
from .exceptions import (
    CapabilityDeniedError,
    CapacityLayerError,
    CapacityRegistrationError,
    ConstraintViolationError,
    DataStateError,
    PipelineNotFoundError,
    ProblemTraceError,
    WriteHandleNotWiredError,
)
from .family_rules import (
    DS_UNHANDLED_INPUT,
    FAMILY_RULES,
    FamilyDontKnowShape,
    family_rule_for,
)
from .pipeline import Pipeline, PipelineStep, find_pipeline
from .runtime import (
    ProblemTraceRecord,
    ProblemTraceSink,
    emit_problem_trace,
    invoke,
)
from .schemas import (
    build_category_schema,
    build_datastates_schema,
    schema_for_role,
)
from .context import (
    CancelToken,
    CancelTokenView,
    CapacityContext,
    CapacityLayerHandle,
    GoalVerdict,
    KLHandle,
    MMHandle,
    PipelineFindVerdict,
    PromotionRuleVerdict,
    ReplanVerdict,
    TierVerdict,
)
from .types import SessionArg, SessionProtocol
from .views import CapacityLayerView
from .write_outcome import WriteOutcome, WriteResult
from .builtins.consolidate import (
    DS_MM_COMPOSITE_INSTANCE,
    build_consolidate_mm,
    install_consolidate_capacities,
    mm_composite_datastates,
)
from .builtins.trace import (
    DS_PROBLEM_TRACE_RECORD,
    build_trace_problem,
    install_trace_capacities,
    problem_trace_datastates,
)
from .identifiers import (
    CATEGORY_COMBINATION,
    CATEGORY_COMPREHENSION,
    CATEGORY_CONSOLIDATE,
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
    FUNCTIONAL_CATEGORIES,
    GLOBAL_FALKOR_GRAPH,
    GLOBAL_METAGRAPH_NAME,
    KIND_ADAPTER,
    KIND_DATASTATE,
    KIND_MONITOR,
    KIND_REACTIVE,
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
    "DreamCapacity",
    "_CapacityBase",
    "CapacityCallable",
    "DataState",
    "ShapeDescriptor",
    # Compatibility helpers
    "strict_compatible",
    "list_of_compat",
    "validate_datastate",
    # Exceptions (base + 8 raisers; monitor-lifecycle exception retired
    # Phase 41 per ADR-0155)
    "CapacityLayerError",
    "CapacityRegistrationError",
    "ConstraintViolationError",
    "DataStateError",
    "PipelineNotFoundError",
    "ProblemTraceError",
    "WriteHandleNotWiredError",
    "CapabilityDeniedError",
    # Phase 28 — CapacityLayer registry + views
    "CapacityLayer",
    "CapacityLayerView",
    # Phase 42 — typed CapacityContext + handle Protocols + verdicts (ADR-0159)
    "CapacityContext",
    "MMHandle",
    "KLHandle",
    "CapacityLayerHandle",
    "CancelToken",
    "CancelTokenView",
    "TierVerdict",
    "GoalVerdict",
    "PipelineFindVerdict",
    "PromotionRuleVerdict",
    "ReplanVerdict",
    # Phase 30 — invocation runtime (ADR-0072) + problem-trace (ADR-0074)
    "InvocationResult",
    "call_capacity",
    "invoke",
    "ProblemTraceRecord",
    "ProblemTraceSink",
    "emit_problem_trace",
    # Phase 30 — pipeline finder (ADR-0071)
    "Pipeline",
    "PipelineStep",
    "find_pipeline",
    # Phase 33 — write-outcome substrate (ADR-0146 §amendment-1)
    "WriteResult",
    "WriteOutcome",
    # Phase 33 — consolidate-family builtins (ADR-0145 §Impl; consolidate
    # category lit; promote/author/state deferred per ADR-0147)
    "DS_MM_COMPOSITE_INSTANCE",
    "mm_composite_datastates",
    "build_consolidate_mm",
    "install_consolidate_capacities",
    # Phase 33 — trace-family write builtins (existing CATEGORY_TRACE,
    # first write occupant)
    "DS_PROBLEM_TRACE_RECORD",
    "problem_trace_datastates",
    "build_trace_problem",
    "install_trace_capacities",
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
    "CATEGORY_CONSOLIDATE",
    "FUNCTIONAL_CATEGORIES",
    "NODE_TYPE_CAPACITY",
    "NODE_TYPE_MONITOR",
    "NODE_TYPE_ADAPTER",
    "NODE_TYPE_DATASTATE",
    "NODE_TYPES",
    "KIND_REACTIVE",
    "KIND_MONITOR",
    "KIND_ADAPTER",
    "KIND_DATASTATE",
    "NODE_KINDS",
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
    "FamilyDontKnowShape",
    "FAMILY_RULES",
    "family_rule_for",
    "DS_UNHANDLED_INPUT",
]

__version__ = "0.0.0+phase48"
