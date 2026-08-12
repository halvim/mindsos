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

#: Phase 33 (ADR-0145) — first per-target write category lit. ``consolidate``
#: capacities write to the Local ``memories`` role-graph (MM →
#: ConsolidatedMemory). Promote / author / state categories from ADR-0145
#: §Decision are deferred to their L4-flow phases per ADR-0147 per-flow
#: build discipline; Phase 33 ships ``consolidate`` only (R0 PB-6 narrow
#: lock).
CATEGORY_CONSOLIDATE = "consolidate"

#: Phase 45 (ADR-0162) — the ``dream.*`` family category. Deliberately
#: NOT a member of ``FUNCTIONAL_CATEGORIES``: like ``text.*``, the dream
#: family is an opt-in installable builtin whose category graph is
#: created lazily by ``ensure_category_graph`` at first register, not
#: pre-bootstrapped by ``create_global``. The constant exists for symbol
#: hygiene + ``builtins/dream.py`` consumption.
CATEGORY_DREAM = "dream"

#: Phase 47 (ADR-0171/0172) — L4-orchestrator support families. Like
#: ``dream.*``/``text.*`` these are opt-in installable builtins whose
#: category graphs are created lazily by ``ensure_category_graph`` at
#: first register, NOT pre-bootstrapped by ``create_global`` and NOT
#: members of ``FUNCTIONAL_CATEGORIES`` (the count invariant stays 13).
#: Phase 47 ships them as placeholder v0 catalogs (``placeholder=True``);
#: CORE-C4R4 / C4R8 / C4R9 replace them with real catalogs (RULES §8).
CATEGORY_PLANNING = "planning"
CATEGORY_PROCESS = "process"
CATEGORY_HINT = "hint"
CATEGORY_DECISION = "decision"
CATEGORY_PREDICATE = "predicate"
CATEGORY_PHASE6 = "phase6"

#: Reduction family (ADR-0204) — L4-support selection decisions
#: (argmin/argmax/top_k/majority_vote). Like ``decision``/``planning`` this is
#: an opt-in installable family (``install_reduction_v0``) whose category graph
#: is created lazily by ``ensure_category_graph`` at first register, NOT
#: pre-bootstrapped by ``create_global`` and NOT a member of
#: ``FUNCTIONAL_CATEGORIES`` (the count invariant stays 13). Real bodies
#: (``placeholder=False``), not a placeholder catalog.
CATEGORY_REDUCTION = "reduction"

#: Functional categories recognised by the default Global L3 bootstrap.
#:
#: Phase 33 extends to 13 (was 12 through Phase 32) per R0 PB-6 +
#: ADR-0145 §Implementation (Phase 33). Adding a new category is a
#: bootstrap-default change: ``create_global()`` now produces 14
#: contained graphs (13 categories + ``capacity:datastates``).
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
    CATEGORY_CONSOLIDATE,
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
#: ``KIND_MONITOR`` (value ``"monitor"``) replaces the Phase 31 monitor
#: node_kind constant (value ``"resident"``) per ADR-0155 (Phase 41) —
#: monitor lifecycle relocated to the L4 substrate; the node_kind triad
#: is now REACTIVE / MONITOR / ADAPTER.
KIND_REACTIVE = "reactive"
KIND_MONITOR = "monitor"
KIND_ADAPTER = "adapter"
KIND_DATASTATE = "datastate"

NODE_KINDS: FrozenSet[str] = frozenset({
    KIND_REACTIVE, KIND_MONITOR, KIND_ADAPTER, KIND_DATASTATE,
})


# ── Typed input-group vocabulary (ADR-0159 §amendment-1) ───────────────
#
# How a capacity's multiple declared inputs resolve when a finder
# composes it. Read off the declaration (``_CapacityBase.input_group``);
# no graph-layer structure is emitted for this field at v1 (Decision 8 —
# the type-layer hyperedge form defers to ADR-0156 §am). Scalar /
# capacity-wide at v1 (ARC's three cases are each capacity-wide); a
# structured per-subset form is the documented extension if a capacity
# ever needs mixed groups.
INPUT_GROUP_ALL_REQUIRED = "all_required"   # AND over inputs (the sound default)
INPUT_GROUP_ANY_OF = "any_of"               # optional-union over inputs
INPUT_GROUP_FOLD = "fold"                   # aggregate over N producers of an input

INPUT_GROUPS: FrozenSet[str] = frozenset({
    INPUT_GROUP_ALL_REQUIRED, INPUT_GROUP_ANY_OF, INPUT_GROUP_FOLD,
})


# ── Core edge-type vocabulary ──────────────────────────────────────────

#: Constraint edge — admin-authored restriction on pipelines.
EDGE_CONSTRAINT = "CONSTRAINT"
#: Bipartite topology edges (ADR-0156). ``PRODUCES`` (capacity→DataState),
#: ``CONSUMES`` (DataState→capacity). Uppercase per the ADR-0021 rel-type
#: regex enforced on IntergraphEdge.type_name; the lowercase form in
#: ADR-0156's body is the Chat B D-B46 instance-layer label convention.
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


# ── Instance-IRI vocabulary (ADR-0201 — capacity_mm instance layer) ─────
#
# capacity_mm holds per-invocation *instances* of L3 DataState / Capacity
# *types*. An instance IRI is deliberately NOT a type IRI: it carries a
# task-scoped ``#`` fragment that is OUT of ``_DATASTATE_NAME_RE`` /
# ``_CAPACITY_NAME_RE``, so it can never be produced by or registered
# through :func:`datastate_iri` / :func:`capacity_iri` — a structural
# type-vs-instance guard (ADR-0201 §Minting), not an accident. Instances
# keep the ``datastate:`` / ``capacity:`` prefix ONLY so ``sub_mm_for_iri``
# routes them by prefix; the type is recovered from the instance node's
# ``datastate_type`` / ``capacity`` property, never by parsing the IRI.
#
# These builders compose the node_id directly and MUST NOT call the type
# builders. Instances are live-only (never persisted or registered).

#: Separator between a type IRI and its per-invocation instance fragment.
#: Out-of-charset by design → an instance IRI is unregisterable as a type.
_INSTANCE_SEP = "#"

_PIPELINERUN_PREFIX = "pipelinerun:"

#: ``type_name`` markers carried by capacity_mm instance nodes. Deliberately
#: NOT members of :data:`NODE_TYPES`: those are the Core-schema type-node
#: kinds, whereas instances are live-only and materialise with a free-form
#: ``type_name`` (``Graph.add_node`` does not constrain node ``type_name``).
NODE_TYPE_DATASTATE_INSTANCE = "DataStateInstance"
NODE_TYPE_CAPACITY_INSTANCE = "CapacityInstance"

#: Property key on an instance node holding its *type* IRI, so the type is
#: recoverable without parsing the instance IRI (feeds the writer's
#: run-local type→instance index; ADR-0201 §Minting).
PROP_DATASTATE_INSTANCE_TYPE = "datastate_type"
PROP_CAPACITY_INSTANCE_TYPE = "capacity"

# ── Run-stopped vocabulary (L-2) ───────────────────────────────────────
#
# ``execute_pipeline`` used to write to ``capacity_mm`` ONLY on a successful
# step: the cancelled / needs_input / failed returns all preceded
# ``writer.record``. So a capacity failure left NO node in the grounding
# graph, and a Decision Record renders from that graph and nothing else —
# every refusal that is not a *reading* refusal was structurally
# unrenderable. These are the vocabulary for the terminal node that closes
# it. Like the instance markers above they are live-only and free-form:
# ``capacity_mm`` carries no schema, so nothing here is type-registered.

#: ``type_name`` marker for the terminal node a non-success run writes.
NODE_TYPE_RUN_STOPPED = "RunStopped"

#: ``RunStopped`` → ``CapacityInstance``. Read as *"this stop occurred at
#: this invocation"*. Absent on a cancellation, because the step never
#: dispatched and there is no invocation to point at — minting a
#: CapacityInstance there would claim a capacity executed when it did not,
#: which is exactly what guard G3 exists to catch.
EDGE_STOPPED_AT = "STOPPED_AT"

#: The step's body raised.
RUN_STOPPED_STEP_FAILED = "step_failed"
#: The cancel token was set; the step never dispatched.
RUN_STOPPED_CANCELLED = "cancelled"
#: ADR-0196 — the body ran and deliberately asked for clarification.
RUN_STOPPED_NEEDS_INPUT = "needs_input"

#: Closed set. Deliberately NOT the ``origin_v0`` refusal vocabulary: that
#: answers *why a value has no origin*, this answers *why a run stopped*.
RUN_STOPPED_REASONS = frozenset(
    {RUN_STOPPED_STEP_FAILED, RUN_STOPPED_CANCELLED, RUN_STOPPED_NEEDS_INPUT}
)

#: Free-form human detail (an exception message, a NeedsInput summary).
PROP_RUN_STOPPED_DETAIL = "stopped_detail"
#: On a cancellation only: the capacity IRI the run stopped *before*.
PROP_RUN_STOPPED_BEFORE = "stopped_before"


def _require_nonempty(value, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string, got {value!r}")
    return value


def _sanitize_run_ref(pipeline_run_ref: str) -> str:
    """Reduce a ``pipeline_run_ref`` to a fragment-safe token: strip the
    ``pipelinerun:`` prefix and replace any remaining ``:`` with ``-`` (a
    raw colon would corrupt the instance fragment). ADR-0201 §Minting."""
    _require_nonempty(pipeline_run_ref, "pipeline_run_ref")
    ref = pipeline_run_ref
    if ref.startswith(_PIPELINERUN_PREFIX):
        ref = ref[len(_PIPELINERUN_PREFIX) :]
    return ref.replace(":", "-")


def _datastate_type_name(type_iri: str) -> str:
    """The bare DataState type name for ``type_iri`` (accepts a full
    ``datastate:<name>`` IRI or a bare ``<name>``)."""
    _require_nonempty(type_iri, "type_iri")
    if type_iri.startswith("datastate:"):
        return type_iri[len("datastate:") :]
    return type_iri


def _capacity_type_name(cap_iri: str) -> str:
    """The ``<category>:<name>`` capacity type token for ``cap_iri`` (accepts
    a full ``capacity:<category>:<name>`` IRI or a bare ``<category>:<name>``)."""
    _require_nonempty(cap_iri, "cap_iri")
    if cap_iri.startswith("capacity:"):
        return cap_iri[len("capacity:") :]
    return cap_iri


def datastate_instance_iri(
    type_iri: str, request_id: str, pipeline_run_ref: str, seq: int
) -> str:
    """Return a per-invocation DataStateInstance node IRI (ADR-0201).

    Format: ``datastate:<type>#<request_id>.<run>.<seq>`` where ``<run>`` is
    the sanitized ``pipeline_run_ref``. Never routed through
    :func:`datastate_iri` — the ``#`` fragment is out of the type charset.
    """
    name = _datastate_type_name(type_iri)
    _require_nonempty(request_id, "request_id")
    run = _sanitize_run_ref(pipeline_run_ref)
    return f"datastate:{name}{_INSTANCE_SEP}{request_id}.{run}.{int(seq)}"


def capacity_instance_iri(
    cap_iri: str, request_id: str, pipeline_run_ref: str, seq: int
) -> str:
    """Return a per-invocation CapacityInstance node IRI (ADR-0201).

    Format: ``capacity:<category>:<name>#<request_id>.<run>.<seq>``.
    """
    name = _capacity_type_name(cap_iri)
    _require_nonempty(request_id, "request_id")
    run = _sanitize_run_ref(pipeline_run_ref)
    return f"capacity:{name}{_INSTANCE_SEP}{request_id}.{run}.{int(seq)}"


def run_stopped_iri(request_id: str, pipeline_run_ref: str) -> str:
    """Return the terminal ``RunStopped`` node IRI for a run (L-2).

    Format: ``runstopped:<request_id>.<run>``. **Deterministic and one per
    run**, which is what makes *"exactly one run-stopped node per run"*
    assertable structurally rather than by counting properties. Safe because
    ``execute_pipeline`` returns on the first non-success, so at most one can
    ever be written for a given run.

    Live-only, like the instance builders above: never registered, never
    routed through :func:`datastate_iri` or :func:`capacity_iri`.
    """
    _require_nonempty(request_id, "request_id")
    run = _sanitize_run_ref(pipeline_run_ref)
    return f"runstopped:{request_id}.{run}"


def datastate_instance_root_iri(type_iri: str, request_id: str) -> str:
    """Return the grounding-DAG root DataStateInstance IRI (ADR-0201 DQ-1):
    the distinguished ``raw_task`` ingress for a task.

    Format: ``datastate:<type>#<request_id>.root`` — no pipeline run / seq;
    the root is task-level, minted once before any pipeline run.
    """
    name = _datastate_type_name(type_iri)
    _require_nonempty(request_id, "request_id")
    return f"datastate:{name}{_INSTANCE_SEP}{request_id}.root"


REALM_CORE = "core"
REALM_MARKER = "marker"
REALM_BRIDGE = "bridge"
REALM_TEXT = "text"
REALM_MM = "mm"
REALM_PROBLEM_TRACE = "problem_trace"
REALM_NLU = "nlu"
REALM_CODE = "code"
REALM_DREAM = "dream"

RESERVED_REALMS: FrozenSet[str] = frozenset({
    REALM_CORE,
    REALM_MARKER,
    REALM_BRIDGE,
    REALM_TEXT,
    REALM_MM,
    REALM_PROBLEM_TRACE,
    REALM_NLU,
    REALM_CODE,
    REALM_DREAM,
})


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
    "CATEGORY_CONSOLIDATE",
    "CATEGORY_DREAM",
    "CATEGORY_PLANNING",
    "CATEGORY_PROCESS",
    "CATEGORY_HINT",
    "CATEGORY_DECISION",
    "CATEGORY_PREDICATE",
    "CATEGORY_PHASE6",
    "CATEGORY_REDUCTION",
    "FUNCTIONAL_CATEGORIES",
    # Node-type vocabulary
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
    # Edge-type vocabulary
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
    # Instance vocabulary (ADR-0201 — capacity_mm instance layer)
    "NODE_TYPE_DATASTATE_INSTANCE",
    "NODE_TYPE_CAPACITY_INSTANCE",
    "PROP_DATASTATE_INSTANCE_TYPE",
    "PROP_CAPACITY_INSTANCE_TYPE",
    "datastate_instance_iri",
    "capacity_instance_iri",
    # Run-stopped vocabulary (L-2)
    "NODE_TYPE_RUN_STOPPED",
    "EDGE_STOPPED_AT",
    "RUN_STOPPED_STEP_FAILED",
    "RUN_STOPPED_CANCELLED",
    "RUN_STOPPED_NEEDS_INPUT",
    "RUN_STOPPED_REASONS",
    "PROP_RUN_STOPPED_DETAIL",
    "PROP_RUN_STOPPED_BEFORE",
    "run_stopped_iri",
    "datastate_instance_root_iri",
    # Ref keys
    "REF_GLOBAL_CAPACITY",
    "REF_GLOBAL_DATASTATE",
    "REF_CAPACITY",
    "REF_DATASTATE",
    "REF_TYPE_KEY",
    "REF_TYPES",
    "RESERVED_PROPERTY_KEYS",
]
