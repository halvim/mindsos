"""Typed capacity-invocation context + handle Protocols + decision verdicts.

ADR-0159 (capacity registration contract v2) replaces the legacy
``Optional[Mapping[str, Any]]`` invoke context with a typed, frozen
:class:`CapacityContext`. Capacity bodies read fields by attribute
(``context.kl``) rather than by dict key (``context["kl"]``).

**Import isolation (Phase 28 invariant).** This module ships inside
``mindsos_capacity`` and therefore may NOT import ``mindsos_knowledge``
or ``mindsos_instances`` — the layer-isolation test AST-walks every
``mindsos_capacity/*.py`` and forbids it. That is the whole reason the
KL / MM / CL surfaces are expressed as :class:`typing.Protocol`s with
``Any``-typed payloads: the body gets a typed handle without a hard
cross-layer import. The concrete classes (``KnowledgeLayer``,
``ElementInstance``, …) are named in docstrings only.

**Verdict types.** The ``decision.*`` family wraps bare-value returns in
canonical verdict dataclasses so the VERDICT family rule (ADR-0157)
applies uniformly. Fields whose concrete enum/type ships downstream
(``tier``, ``goal``) are typed ``Optional[Any]`` here; the IRI-bearing
verdicts use ``Optional[str]``.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Any,
    List,
    Mapping,
    Optional,
    Protocol,
    runtime_checkable,
)

if TYPE_CHECKING:  # pragma: no cover — typing-only; import isolation at runtime
    from .capacity import _CapacityBase


# ── Handle Protocols (ADR-0159) ────────────────────────────────────────


@runtime_checkable
class MMHandle(Protocol):
    """Mental-model read/instantiate surface exposed to capacity bodies.

    Concrete impl is the L4 substrate's MM handle (Phase 46); returns are
    ``ElementInstance`` / ``DataStateInstance`` / ``CapacityInstance``
    from ``mindsos_instances`` (named here only — not imported).
    """

    def get_or_instantiate(self, node_iri: str) -> Any: ...

    def find_instances_by_type(self, type_iri: str) -> List[Any]: ...

    def produces_of(self, capacity_instance: Any) -> List[Any]: ...

    def consumes_of(self, data_state_instance: Any) -> List[Any]: ...


@runtime_checkable
class KLHandle(Protocol):
    """Knowledge-layer read surface exposed to capacity bodies.

    ``read_at_version`` is declared per ADR-0159; its concrete KL
    implementation lands Phase 48 (L0-21 / `kl.read_at_version`). No v1
    capacity body calls it — write capacities use the Phase 34 write-
    handle methods, which conforming KL handles also expose.
    """

    def read_at_version(self, iri: str, version: int) -> Any: ...


@runtime_checkable
class CapacityLayerHandle(Protocol):
    """Capacity-layer registry surface (e.g. ``decision.should_replan``
    reads contract IRIs via ``context.cl.get_declaration(step_iri)``)."""

    def get_declaration(self, capacity_iri: str) -> "_CapacityBase": ...


@runtime_checkable
class CancelToken(Protocol):
    """Full cancellation token — held by the L4 substrate, never the body."""

    def is_set(self) -> bool: ...

    def request_cancel(self) -> None: ...


class CancelTokenView:
    """Read-only wrapper exposing only ``is_set()`` to a capacity body.

    Defense-in-depth: the body can poll cancellation but cannot request
    it (``request_cancel`` stays with the L4 substrate per ADR-0159).
    """

    __slots__ = ("_token",)

    def __init__(self, token: CancelToken) -> None:
        self._token = token

    def is_set(self) -> bool:
        return self._token.is_set()


# ── CapacityContext (ADR-0159 — 10 fields, frozen) ─────────────────────


@dataclass(frozen=True)
class CapacityContext:
    """Typed, frozen invocation context passed to a capacity body.

    ``version_snapshot`` is exposed read-only via ``MappingProxyType``
    (wrapped in ``__post_init__``); it is mutable L4-side but immutable
    to the body (Chat B D-B14 lazy-instantiation reality).
    """

    session_id: str
    user_id: str
    learned_parameters_snapshot: Mapping[str, Any]
    mm_handle: Optional[MMHandle] = None
    cancel_token: Optional[CancelTokenView] = None
    current_task_iri: Optional[str] = None
    current_pattern_iri: Optional[str] = None
    version_snapshot: Mapping[str, int] = MappingProxyType({})
    kl: Optional[KLHandle] = None
    cl: Optional[CapacityLayerHandle] = None

    def __post_init__(self) -> None:
        # Defense-in-depth read-only views (frozen dataclass → bypass via
        # object.__setattr__). Idempotent if already a MappingProxyType.
        if not isinstance(self.version_snapshot, MappingProxyType):
            object.__setattr__(
                self, "version_snapshot", MappingProxyType(dict(self.version_snapshot))
            )
        if not isinstance(self.learned_parameters_snapshot, MappingProxyType):
            object.__setattr__(
                self,
                "learned_parameters_snapshot",
                MappingProxyType(dict(self.learned_parameters_snapshot)),
            )


# ── Canonical decision verdict types (ADR-0159 + ADR-0157 VERDICT) ─────


@dataclass(frozen=True)
class TierVerdict:
    """``decision.*`` tier verdict. ``tier`` is the downstream TierEnum
    (typed ``Any`` here pending its owning family)."""

    tier: Optional[Any]
    rationale: str


@dataclass(frozen=True)
class GoalVerdict:
    """``decision.*`` goal verdict. ``goal`` is the downstream Goal type
    (typed ``Any`` here pending its owning family)."""

    goal: Optional[Any]
    rationale: str


@dataclass(frozen=True)
class PipelineFindVerdict:
    """``decision.*`` pipeline-selection verdict."""

    pipeline_iri: Optional[str]
    rationale: str


@dataclass(frozen=True)
class PromotionRuleVerdict:
    """``decision.*`` promotion-rule verdict."""

    rule_iri: Optional[str]
    rationale: str


@dataclass(frozen=True)
class ReplanVerdict:
    """``decision.should_replan`` verdict (Chat A R2)."""

    should_replan: bool
    rationale: str


__all__ = [
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
]
