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
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from .exceptions import CapacityRegistrationError
from .identifiers import (
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
    """

    outputs: Mapping[str, Any]
    duration_ms: float
    success: bool
    error: Optional[BaseException] = None
    signals: Tuple[Any, ...] = ()
    trace: Mapping[str, Any] = field(default_factory=dict)
    write_outcome: Optional[Any] = None  # WriteResult | ProblemTraceRecord


def call_capacity(
    declaration: _CapacityBase,
    inputs: Mapping[str, Any],
    context: Optional[Mapping[str, Any]] = None,
) -> Mapping[str, Any]:
    """Invoke the Python callable bound to ``declaration``.

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
    kwargs = dict(inputs)
    if context is not None:
        kwargs.setdefault("context", context)
    result = declaration.implementation(**kwargs)

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
    "InvocationResult",
    "call_capacity",
    "_CapacityBase",
]
