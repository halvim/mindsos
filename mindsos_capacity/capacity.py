"""Capacity declarations — Python wrappers registered with L3.

Three node kinds are recognised (§5):

- :class:`Capacity` — reactive, the default.
- :class:`Monitor` — resident, long-running.
- :class:`Adapter` — minimal capacity bridging near-compatible DataStates.

Each declaration pairs a graph-level node identity (``iri`` and
``category``) with a Python callable. The callable is what
:func:`CapacityLayer.invoke` runs; the graph node is what L4's
pipeline-finder reasons about.

These classes are intentionally thin. The :class:`CapacityLayer` owns
the authoritative registry that maps ``iri → declaration`` and the
Core nodes that mirror them.

Phase 27 ships the dataclasses + IRI form + ``_CapacityBase.validate_
for_registration`` only. ``InvocationResult`` + ``call_capacity`` are
present in this module for layout parity with parent, but are NOT
exported via ``mindsos_capacity/__init__.py`` until Phase 30 (per
ADR-0066 §Implementation footer staging + Phase 30 PHASE_MAP row).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Tuple,
    Union,
)

if TYPE_CHECKING:
    from .context import CapacityContext

from .exceptions import CapacityRegistrationError, InputContractError
from .needs_input import NeedsInput
from .identifiers import (
    INPUT_GROUP_ALL_REQUIRED,
    INPUT_GROUP_ANY_OF,
    INPUT_GROUP_FOLD,
    KIND_ADAPTER,
    KIND_MONITOR,
    KIND_REACTIVE,
    NODE_TYPE_ADAPTER,
    NODE_TYPE_CAPACITY,
    NODE_TYPE_MONITOR,
    capacity_iri,
)


# ── Helper: flatten a callable into a function-of-kwargs ───────────────

CapacityCallable = Callable[..., Any]
"""Python callable signature: ``(**inputs, context=...) -> output | dict``."""


# ── Base class ─────────────────────────────────────────────────────────

@dataclass
class _CapacityBase:
    name: str
    category: str
    inputs: Tuple[str, ...]           # DataState IRIs consumed
    outputs: Tuple[str, ...]          # DataState IRIs produced
    implementation: Optional[CapacityCallable] = None
    description: str = ""
    # Decision Records — the phrase a Record prints when it has to NAME this
    # capacity: "decided by the filing-requirement test", "stopped at
    # consulting the filing-threshold policy". Deliberately NOT ``description``:
    # a description answers *what does this do* for a developer and is written
    # as a question ("whether the stated income reaches the threshold in
    # force"), which renders as "decided by whether the stated income
    # reaches…". One field cannot be both. Optional, so every existing
    # capacity is unchanged; validated by ``register_capacity`` only when
    # supplied, against the same rule origin records use
    # (``mindsos_capacity.printable``). A run graph carries only a capacity's
    # IRI, so without this the Record has nothing to call it.
    printable_phrase: str = ""
    cost_prior: float = 1.0
    latency_ms_prior: float = 0.0
    node_type: str = NODE_TYPE_CAPACITY
    node_kind: str = KIND_REACTIVE
    is_adapter: bool = False
    concurrent: bool = True
    inline: bool = False
    max_latency_ms: Optional[int] = None
    precondition_iri: Optional[str] = None
    effect_iri: Optional[str] = None
    reads_mm: bool = False
    # ADR-0159 §amendment-1 — how the conjunction finder resolves this
    # capacity's multiple declared inputs: "all_required" (AND) | "any_of"
    # (optional-union) | "fold" (aggregate over N producers). The default
    # preserves every pre-amendment capacity (the implicit contract *was*
    # all-inputs-required for a sound composer; the BFS just never enforced
    # it). Read off the declaration by the finder; not emitted to the graph
    # at v1 (Decision 8).
    input_group: str = INPUT_GROUP_ALL_REQUIRED
    # ADR-0209 (shape (a)) — the reducer-side half of the member-refusal
    # contract. ``True`` declares this capacity's body DECODES in-band refusal
    # values (ADR-0208-shaped: a refusal value carrying its origin record) on
    # its list input, so a fold may hand it a member set whose ``member_ds``
    # is ``refusal_capable``. Read off the declaration by the plan-construction
    # decode check; like ``input_group`` (Decision 8) it is NOT emitted to the
    # graph — a registration-time fact, not run evidence. Default ``False``
    # keeps every existing capacity unchanged.
    decodes_refusals: bool = False
    # ADR-0198 (Part 5 / 5a) — same-type operand arity. Maps an input
    # DataState IRI to the number of operands of that type the body
    # consumes (``{DS_OBJECT: 2}`` for a binary comparator). Absent /
    # ``1`` = today's single-operand behaviour, so every pre-ADR-0198
    # capacity is unchanged. The operand *axis* rides this registration
    # field, not the graph topology — like ``input_group`` (Decision 8),
    # it is NOT emitted as N ``CONSUMES`` edges (ADR-0156 unchanged). The
    # operand *role* (from/to, container/contained) is read off list
    # position inside the body and never enters core.
    operand_arity: Mapping[str, int] = field(default_factory=dict)
    placeholder: bool = False

    @property
    def iri(self) -> str:
        return capacity_iri(self.category, self.name)

    def to_properties(self) -> Dict[str, Any]:
        """Build the property dict used when creating the Core node."""
        props: Dict[str, Any] = {
            "name": self.name,
            "category": self.category,
            "node_kind": self.node_kind,
            "is_adapter": self.is_adapter,
            "cost_prior": float(self.cost_prior),
            "latency_ms_prior": float(self.latency_ms_prior),
        }
        if self.description:
            props["description"] = self.description
        if self.printable_phrase:
            props["printable_phrase"] = self.printable_phrase
        if self.placeholder:
            props["placeholder"] = True
        return props

    def validate_for_registration(self, datastate_iris) -> None:
        """Check that every input/output DataState IRI is registered.

        Raises :class:`CapacityRegistrationError` on first missing IRI.
        """
        known = set(datastate_iris)
        missing = [ds for ds in self.inputs if ds not in known]
        missing += [ds for ds in self.outputs if ds not in known]
        if missing:
            raise CapacityRegistrationError(
                f"Capacity {self.iri!r}: unknown DataState IRIs "
                f"{sorted(set(missing))!r}"
            )
        # ADR-0198 (5a) — operand_arity keys must be declared inputs, so a
        # typo'd IRI fails loud at registration instead of silently skipping
        # the arity check at invoke. (Cannot regress existing capacities —
        # none declare operand_arity.)
        arity_keys = set(getattr(self, "operand_arity", None) or {})
        stray_arity = sorted(arity_keys - set(self.inputs))
        if stray_arity:
            raise CapacityRegistrationError(
                f"Capacity {self.iri!r}: operand_arity names non-input "
                f"DataState IRIs {stray_arity!r} (declared inputs: "
                f"{sorted(self.inputs)!r})"
            )
        if self.implementation is not None and not callable(self.implementation):
            raise CapacityRegistrationError(
                f"Capacity {self.iri!r}: implementation must be callable"
            )


# ── Reactive capacity ──────────────────────────────────────────────────

@dataclass
class Capacity(_CapacityBase):
    """A reactive capacity — invoked on-demand with concrete inputs."""

    def __post_init__(self) -> None:
        self.node_type = NODE_TYPE_CAPACITY
        self.node_kind = KIND_REACTIVE
        self.is_adapter = False


# ── Resident capacity (monitor) ────────────────────────────────────────

@dataclass
class Monitor(_CapacityBase):
    """A monitor capacity — watches DataStates and emits signals.

    ``subscribes_to`` and ``emits`` complement ``inputs``/``outputs``
    by naming the signal-level DataStates; the reactive-style lists
    are retained so that a monitor can be treated uniformly by the
    pipeline-finder when it acts in a reactive role.

    Monitor lifecycle (start/stop/dispatch) is owned by the L4 substrate
    per ADR-0155 (Phase 41); L3 ships only the declaration + the
    ``CapacityLayer.iter_monitors()`` enumeration producer.
    """

    subscribes_to: Tuple[str, ...] = ()
    emits: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.node_type = NODE_TYPE_MONITOR
        self.node_kind = KIND_MONITOR
        self.is_adapter = False

    def to_properties(self) -> Dict[str, Any]:
        props = super().to_properties()
        props["subscribes_to"] = list(self.subscribes_to)
        props["emits"] = list(self.emits)
        return props


# ── Adapter capacity ───────────────────────────────────────────────────

@dataclass
class Adapter(_CapacityBase):
    """A minimal capacity bridging near-compatible DataStates."""

    def __post_init__(self) -> None:
        # Adapters live under a dedicated naming slot ("adapter.*") but
        # functionally participate like reactive capacities.
        self.node_type = NODE_TYPE_ADAPTER
        self.node_kind = KIND_ADAPTER
        self.is_adapter = True


# ── Dream capacity (Phase 45 — Rail D, ADR-0162) ───────────────────────

@dataclass
class DreamCapacity(_CapacityBase):
    """A reactive capacity in the ``dream.*`` family (ADR-0162).

    Dream capacities are ordinary on-demand reactive capacities
    (``node_kind = KIND_REACTIVE``) that additionally declare two
    contract fields the L4 dream-cycle loop reads off the registered
    Core node (Phase 46+):

    - ``execution_policy`` — ``replay_recorded`` (replay recorded chain
      artifacts; no generative re-invocation) or ``re_execute_capacities``
      (re-invoke generative capacities against current L2/L3). Per Chat B
      D-B8. The ``hybrid`` policy is a v2 reservation (no v1 assignee).
    - ``entry_point`` — the chain entry the dream re-executes from. v1 is
      ``latest_active_requestrun`` for all three capacities (Chat B D-B7);
      specific PipelineRun / Milestone / replan-point entries are v2.

    The body itself is a **directive-emitter** (Phase 45 R0 S1): it
    validates its input and returns a ``DreamDirective`` describing the
    dream action. The actual MM deep-copy + live re-execution + ALS
    signal firing are owned by the L4 substrate (Phase 46) and the L5
    dream-pipeline hookup (Phase 48); this declaration ships the L3
    contract ahead of that consumer. Dont-know contract is
    OPTIONAL_RETURN (L3-51 / ``family_rules.FAMILY_RULES['dream']``):
    the body returns ``None`` when it cannot produce a directive.
    """

    execution_policy: str = ""
    entry_point: str = ""

    def __post_init__(self) -> None:
        self.node_type = NODE_TYPE_CAPACITY
        self.node_kind = KIND_REACTIVE
        self.is_adapter = False

    def to_properties(self) -> Dict[str, Any]:
        props = super().to_properties()
        props["execution_policy"] = self.execution_policy
        props["entry_point"] = self.entry_point
        return props


# ── Executor: one source of truth for calling a declaration ────────────
#
# Phase 27 ships these for parent-layout parity but does NOT export
# them from `mindsos_capacity/__init__.py`. Phase 30 (per PHASE_MAP §30
# "invoke returns InvocationResult") lifts the exports + adds the
# invocation-side tests. ADR-0066 §Implementation footer documents the
# capacity-IRI staging across 27/28; InvocationResult+call_capacity
# follow the same staging discipline.

@dataclass(frozen=True)
class InvocationResult:
    """Return shape of :meth:`CapacityLayer.invoke`.

    Attributes:
        outputs: Mapping of output-DataState IRI → produced value.
            EMPTY for write capacities (``outputs=()`` terminators);
            see :attr:`write_outcome`.
        duration_ms: Observed execution time.
        success: ``True`` if the callable returned without raising.
        error: ``None`` on success; an exception instance on failure.
        signals: Signals emitted during execution (reserved for
            future resident/reactive integration).
        trace: Auxiliary trace-record fields (free-form).
        write_outcome: Phase 34 (ADR-0146) — populated by write
            capacities (``outputs=()``); ``None`` for read capacities.
            Holds the typed ``WriteResult | ProblemTraceRecord`` the
            write body returned. ``runtime.invoke``'s bypass branch
            stashes it here; read paths leave ``None``.
        needs_input: ADR-0196 — the ``NeedsInput`` verdict a body returned
            to request user clarification (``None`` normally). Orthogonal
            to ``success`` (the body ran fine; it deliberately asked), so
            ``needs_input``-aware callers (``pipeline_execution``,
            ``phase_1.interpret``) must check this field explicitly.
    """

    outputs: Mapping[str, Any]
    duration_ms: float
    success: bool
    error: Optional[BaseException] = None
    signals: Tuple[Any, ...] = ()
    trace: Mapping[str, Any] = field(default_factory=dict)
    write_outcome: Optional[Any] = None  # WriteResult | ProblemTraceRecord
    needs_input: Optional[Any] = None  # NeedsInput (ADR-0196)


def _validate_inputs(
    declaration: _CapacityBase, inputs: Mapping[str, Any]
) -> None:
    """Validate ``inputs`` against the declaration's ``CONSUMES`` contract.

    Composition-lifecycle Slice 2 Part 6 (ADR-0072 §amendment-2). Checks
    the declaration's declared input set (declaration-primary, not the
    edge-sourced view), respecting ``input_group``:

    - ``all_required`` — every declared input must be present.
    - ``any_of`` — at least one declared input must be present.
    - ``fold`` — not enforced at v1; operand multiplicity is Part 5.

    Non-fold groups also reject keys absent from the declared inputs
    (no-unexpected). The ``context`` key is never an input and is
    ignored. Raises :class:`InputContractError` (``kind`` set); on the
    ``invoke`` path the caller envelopes it per ADR-0072.
    """
    declared = tuple(declaration.inputs)
    if declaration.input_group == INPUT_GROUP_FOLD:
        return
    declared_set = set(declared)
    present = {k for k in inputs if k != "context"}
    if declaration.input_group == INPUT_GROUP_ANY_OF:
        if declared and not (present & declared_set):
            raise InputContractError(
                f"Capacity {declaration.iri!r}: input_group=any_of requires at "
                f"least one of {sorted(declared_set)}; got {sorted(present)}",
                kind="missing_required",
            )
    else:
        missing = [ds for ds in declared if ds not in present]
        if missing:
            raise InputContractError(
                f"Capacity {declaration.iri!r}: missing required inputs "
                f"{missing!r} (declared CONSUMES; got {sorted(present)})",
                kind="missing_required",
            )
    unexpected = sorted(k for k in present if k not in declared_set)
    if unexpected:
        raise InputContractError(
            f"Capacity {declaration.iri!r}: unexpected inputs {unexpected!r} "
            f"not in declared CONSUMES {sorted(declared_set)}",
            kind="unexpected_input",
        )
    # ADR-0198 (5a) — same-type operand arity. For each declared input with
    # ``operand_arity[k] = N > 1``, the supplied value must be a length-N
    # list. Length only — core never inspects operand *value* types (the
    # per-slot role/type is the body's concern; cross-kind operands like
    # ``touching``'s region view are resolved consumer-side). Keys absent
    # from ``inputs`` are already handled by the missing/any_of checks
    # above; arity is validated only for present keys.
    arity = getattr(declaration, "operand_arity", None) or {}
    for key, n in arity.items():
        if n <= 1 or key not in present:
            continue
        value = inputs[key]
        if not isinstance(value, list) or len(value) != n:
            got = (
                f"list of length {len(value)}"
                if isinstance(value, list)
                else type(value).__name__
            )
            raise InputContractError(
                f"Capacity {declaration.iri!r}: input {key!r} declares "
                f"operand_arity {n}; expected a length-{n} list, got {got}",
                kind="operand_arity",
            )


def call_capacity(
    declaration: _CapacityBase,
    inputs: Mapping[str, Any],
    context: "Optional[Union[Mapping[str, Any], CapacityContext]]" = None,
) -> Mapping[str, Any]:
    """Invoke the Python callable bound to ``declaration``.

    ``context`` is threaded opaquely to the body. Phase 47 (ADR-0175)
    widens the type to accept either the legacy dict (the unmigrated
    ``capacity_layer.invoke`` write path) or a typed ``CapacityContext``
    (the new L4 ``dispatch`` read path). The read-path bodies migrated at
    Phase 47 access fields by attribute (``context.kl``); the write-path
    bodies (``consolidate``/``trace``) stay on dict access until Phase 48
    when consolidation is wired (their real consumer).

    The callable is called with ``**inputs, context=context``. The
    return value may be:

    - a single value → mapped to the sole output DataState IRI,
    - a mapping → validated against the declared output IRIs.

    Raises :class:`CapacityRegistrationError` if no implementation is
    bound, or if the return shape doesn't match the output signature.
    """
    if declaration.implementation is None:
        raise CapacityRegistrationError(
            f"Capacity {declaration.iri!r} has no implementation bound"
        )
    _validate_inputs(declaration, inputs)
    kwargs = dict(inputs)
    if context is not None:
        kwargs.setdefault("context", context)
    result = declaration.implementation(**kwargs)

    # ADR-0196 — a body may return the ``NeedsInput`` clarification verdict
    # instead of its declared outputs. Short-circuit output validation;
    # ``runtime.invoke`` envelopes it onto ``InvocationResult.needs_input``.
    if isinstance(result, NeedsInput):
        return result

    outputs = declaration.outputs
    if isinstance(result, Mapping):
        missing = [iri for iri in outputs if iri not in result]
        if missing:
            raise CapacityRegistrationError(
                f"Capacity {declaration.iri!r} returned mapping missing outputs {missing!r}"
            )
        return {iri: result[iri] for iri in outputs}
    if len(outputs) != 1:
        raise CapacityRegistrationError(
            f"Capacity {declaration.iri!r} returned a single value but declares "
            f"{len(outputs)} outputs; expected a mapping"
        )
    return {outputs[0]: result}


__all__ = [
    "CapacityCallable",
    "Capacity",
    "Monitor",
    "Adapter",
    "DreamCapacity",
    "InvocationResult",
    "call_capacity",
    "_CapacityBase",
]
