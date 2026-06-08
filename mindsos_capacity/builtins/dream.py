"""``dream.*`` family — L3 dream capacities (Phase 45; Rail D; ADR-0162).

Ships the three v1 dream capacities per Chat B D-B6 / L3-51:

- ``capacity:dream:maintenance`` — ``replay_recorded`` policy (regression
  check: replay recorded chain artifacts under pinned state).
- ``capacity:dream:exploration`` — ``re_execute_capacities`` policy (drift
  detection vs current L2/L3; alt-strategy probe).
- ``capacity:dream:retry`` — ``re_execute_capacities`` policy **with
  replan-injection** (re-execute a failed episode against current state).

**Directive-emitter contract (Phase 45 R0 S1).** Dream capacities have no
v1 L3 consumer — the consumer is the L4 dream-cycle loop (Phase 46) and
the L5 dream-pipeline hookup (Phase 48). So each body is a pure
*directive-emitter*: it validates its input (a reference to the episode /
TaskRun to dream over) and returns a :class:`DreamDirective` describing
the dream action. The L4 loop later reads the registered capacity's
``execution_policy`` + ``entry_point`` off the Core node, invokes the
body to obtain the directive, then performs the actual MM deep-copy +
live re-execution + ALS signal firing (all Phase 46/48 — **out of scope
here**). This is the same "ship the L3 contract ahead of its L4 consumer"
pattern as ``iter_monitors`` (Phase 41), the bipartite walk (Phase 42),
and ``CapacityContext`` (Phase 42).

**Dont-know contract.** OPTIONAL_RETURN (L3-51;
``family_rules.FAMILY_RULES['dream']`` resolves via the category
fall-through). A body returns ``None`` when it cannot produce a directive
(e.g. a missing source episode, or ``dream.retry`` over a non-failed
episode). ``call_capacity`` maps the single return value onto the sole
output DataState IRI; ``None`` flows through as the dont-know signal.

**Provenance.** Every directive carries ``source_episode_iri`` — the
provenance the L4 loop propagates onto signals emitted during
re-execution (``dream_source_episode_iri``, Chat B §5.2). Live signal
tagging lands Phase 48; Phase 45 ships the field on the directive.

**Privacy (D-B9).** Directives are inert data; no dream body writes to
Global or touches any cross-user path. The owning user's session drives
dream execution at the L4 layer.

**Build pattern.** Mirrors ``builtins/consolidate.py``: DataStates +
``DreamCapacity`` factories + an idempotent ``install_dream_capacities``
(DataStates-first per the ``_CapacityBase.validate_for_registration``
forward-ref rule). The ``dream`` category graph is created lazily by
``ensure_category_graph`` at register — ``dream`` is intentionally NOT in
``FUNCTIONAL_CATEGORIES`` (opt-in installable family, like ``text.*``).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional

from ..bootstrap import ensure_datastate_graph
from ..capacity import DreamCapacity
from ..datastate import DataState, ShapeDescriptor
from ..exceptions import CapacityRegistrationError
from ..identifiers import (
    CATEGORY_DREAM,
    capacity_iri,
    datastate_iri,
)


# ── Execution policy (Chat B D-B8) ─────────────────────────────────────


class DreamExecutionPolicy(str, Enum):
    """Per-capacity dream re-execution policy (Chat B D-B8).

    ``hybrid`` (partial replay) is named in D-B8 but has no v1 assignee;
    it is a v2 reservation documented in ADR-0162 §v2-reservations and is
    intentionally NOT a member here (consumer discipline — no dead enum
    members; Phase 40 PB-1 precedent).
    """

    REPLAY_RECORDED = "replay_recorded"
    RE_EXECUTE_CAPACITIES = "re_execute_capacities"


#: v1 entry-point for all three dream capacities (Chat B D-B7). Specific
#: PipelineRun / Milestone / replan-point entries are v2.
ENTRY_POINT_LATEST_ACTIVE_TASKRUN = "latest_active_taskrun"

#: v1 replan level — dream capacities operate at TaskRun level (D-B6):
#: a retry re-executes the whole task, so the injected replan invalidates
#: from the TaskRun root. Cross-level (sub-Milestone) replan is v2.
REPLAN_LEVEL_TASKRUN = "taskrun"


# ── Directive shapes (consumer-local; not top-level exported) ──────────


@dataclass(frozen=True)
class ReplanInjectionDirective:
    """Replan-injection payload emitted by ``capacity:dream:retry``.

    The L4 dream loop (Phase 46) consumes this to drive a replan
    (invalidate the chain at/below ``replan_level``, spawn new artifacts —
    Chat B D-B30). Phase 45 ships only the directive; the replan
    mechanism is L4 control flow.
    """

    replan_level: str
    source_episode_iri: str
    reason: str


@dataclass(frozen=True)
class DreamDirective:
    """The structured action a dream capacity emits (Phase 45 S1/S4).

    Attributes:
        execution_policy: The policy value the L4 loop applies
            (``replay_recorded`` | ``re_execute_capacities``).
        entry_point: The chain entry the re-execution starts from (v1
            ``latest_active_taskrun``).
        source_episode_iri: Provenance — the episode being dreamed over;
            propagated onto re-execution signals as
            ``dream_source_episode_iri`` at Phase 48.
        task_run_iri: The TaskRun the dream re-executes.
        replan_injection: Populated only by ``dream.retry`` on a failed
            episode; ``None`` otherwise.
    """

    execution_policy: str
    entry_point: str
    source_episode_iri: str
    task_run_iri: str
    replan_injection: Optional[ReplanInjectionDirective] = None


# ── DataState IRIs (record-shape per the consolidate precedent) ────────

DS_DREAM_TASK_REF = datastate_iri("dream.task_ref")
DS_DREAM_DIRECTIVE = datastate_iri("dream.directive")


def dream_datastates() -> List[DataState]:
    """Return the DataState(s) the ``dream.*`` family consumes/produces.

    Two shared DataStates across all three capacities: an input
    ``dream.task_ref`` (record naming the episode / TaskRun to dream over)
    and an output ``dream.directive`` (the emitted :class:`DreamDirective`,
    OPTIONAL_RETURN).
    """
    return [
        DataState(
            name="dream.task_ref",
            shape=ShapeDescriptor.record(
                {
                    "source_episode_iri": "str",
                    "task_run_iri": "str",
                    "failed": "bool",
                },
                opaque_tag="dream.task_ref",
            ),
            description=(
                "Reference to the episode / TaskRun a dream capacity "
                "re-executes over. ``source_episode_iri`` is the dreamed "
                "episode (provenance); ``task_run_iri`` is its TaskRun; "
                "``failed`` flags a failed episode (consumed by "
                "``dream.retry`` for replan-injection). Supplied by the "
                "L4 dream loop at Phase 46."
            ),
            provenance_category=CATEGORY_DREAM,
        ),
        DataState(
            name="dream.directive",
            shape=ShapeDescriptor.record(
                {
                    "execution_policy": "str",
                    "entry_point": "str",
                    "source_episode_iri": "str",
                    "task_run_iri": "str",
                    "replan_injection": "Any",
                },
                opaque_tag="dream.directive",
            ),
            description=(
                "The DreamDirective a dream capacity emits — the L3→L4 "
                "contract the dream loop consumes to drive MM deep-copy + "
                "re-execution. OPTIONAL_RETURN: ``None`` on dont-know."
            ),
            provenance_category=CATEGORY_DREAM,
        ),
    ]


# ── Capacity bodies (directive-emitters) ───────────────────────────────


def _require_task_ref(kwargs: Any) -> Optional[dict]:
    """Extract + minimally validate the task-ref record.

    Returns ``None`` (dont-know) when the source episode is absent — the
    OPTIONAL_RETURN family rule. Otherwise returns the record dict.
    """
    record = kwargs.get(DS_DREAM_TASK_REF)
    if not record or not record.get("source_episode_iri"):
        return None
    return record


def _dream_maintenance_impl(**kwargs: Any) -> Optional[DreamDirective]:
    """``capacity:dream:maintenance`` — ``replay_recorded`` regression check.

    Emits a directive instructing the L4 loop to replay the recorded
    chain artifacts under pinned state (no generative re-invocation).
    """
    record = _require_task_ref(kwargs)
    if record is None:
        return None
    return DreamDirective(
        execution_policy=DreamExecutionPolicy.REPLAY_RECORDED.value,
        entry_point=ENTRY_POINT_LATEST_ACTIVE_TASKRUN,
        source_episode_iri=record["source_episode_iri"],
        task_run_iri=record.get("task_run_iri", ""),
        replan_injection=None,
    )


def _dream_exploration_impl(**kwargs: Any) -> Optional[DreamDirective]:
    """``capacity:dream:exploration`` — ``re_execute_capacities`` drift probe.

    Emits a directive instructing the L4 loop to re-invoke generative
    capacities against current L2/L3 (drift detection / alt strategies).
    """
    record = _require_task_ref(kwargs)
    if record is None:
        return None
    return DreamDirective(
        execution_policy=DreamExecutionPolicy.RE_EXECUTE_CAPACITIES.value,
        entry_point=ENTRY_POINT_LATEST_ACTIVE_TASKRUN,
        source_episode_iri=record["source_episode_iri"],
        task_run_iri=record.get("task_run_iri", ""),
        replan_injection=None,
    )


def _dream_retry_impl(**kwargs: Any) -> Optional[DreamDirective]:
    """``capacity:dream:retry`` — ``re_execute_capacities`` + replan-injection.

    Re-executes a **failed** episode against current state. On a failed
    episode the emitted directive carries a populated
    :class:`ReplanInjectionDirective`; on a non-failed episode the
    capacity returns ``None`` (dont-know — retry only applies to failures).
    """
    record = _require_task_ref(kwargs)
    if record is None:
        return None
    if not record.get("failed"):
        # Retry only applies to failed episodes (D-B8). Non-failed input
        # is dont-know under OPTIONAL_RETURN.
        return None
    source = record["source_episode_iri"]
    return DreamDirective(
        execution_policy=DreamExecutionPolicy.RE_EXECUTE_CAPACITIES.value,
        entry_point=ENTRY_POINT_LATEST_ACTIVE_TASKRUN,
        source_episode_iri=source,
        task_run_iri=record.get("task_run_iri", ""),
        replan_injection=ReplanInjectionDirective(
            replan_level=REPLAN_LEVEL_TASKRUN,
            source_episode_iri=source,
            reason="dream.retry re-execution of failed episode",
        ),
    )


# ── Capacity factories ─────────────────────────────────────────────────


def _build_dream(
    name: str,
    *,
    policy: DreamExecutionPolicy,
    implementation: Any,
    description: str,
) -> DreamCapacity:
    """Construct one ``dream.*`` capacity declaration."""
    return DreamCapacity(
        name=name,
        category=CATEGORY_DREAM,
        inputs=(DS_DREAM_TASK_REF,),
        outputs=(DS_DREAM_DIRECTIVE,),
        implementation=implementation,
        description=description,
        execution_policy=policy.value,
        entry_point=ENTRY_POINT_LATEST_ACTIVE_TASKRUN,
        concurrent=True,  # L3-51 default
        cost_prior=3.0,
        latency_ms_prior=10.0,
    )


def build_dream_maintenance() -> DreamCapacity:
    """Build ``capacity:dream:maintenance`` (``replay_recorded``)."""
    return _build_dream(
        "maintenance",
        policy=DreamExecutionPolicy.REPLAY_RECORDED,
        implementation=_dream_maintenance_impl,
        description=(
            "Dream maintenance — replay recorded chain artifacts under "
            "pinned state for regression checking (Chat B D-B6/D-B8). "
            "Emits a DreamDirective; L4 performs the replay (Phase 46)."
        ),
    )


def build_dream_exploration() -> DreamCapacity:
    """Build ``capacity:dream:exploration`` (``re_execute_capacities``)."""
    return _build_dream(
        "exploration",
        policy=DreamExecutionPolicy.RE_EXECUTE_CAPACITIES,
        implementation=_dream_exploration_impl,
        description=(
            "Dream exploration — re-invoke generative capacities against "
            "current L2/L3 for drift detection / alt strategies (Chat B "
            "D-B6/D-B8). Emits a DreamDirective; L4 re-executes (Phase 46)."
        ),
    )


def build_dream_retry() -> DreamCapacity:
    """Build ``capacity:dream:retry`` (``re_execute_capacities`` + replan)."""
    return _build_dream(
        "retry",
        policy=DreamExecutionPolicy.RE_EXECUTE_CAPACITIES,
        implementation=_dream_retry_impl,
        description=(
            "Dream retry — re-execute a failed episode against current "
            "state with replan-injection (Chat B D-B6/D-B8). On a failed "
            "episode the directive carries a ReplanInjectionDirective; L4 "
            "performs the replan (Phase 46)."
        ),
    )


# ── Idempotent installer (consolidate / text precedent) ────────────────

_DREAM_MAINTENANCE_IRI = capacity_iri(CATEGORY_DREAM, "maintenance")
_DREAM_EXPLORATION_IRI = capacity_iri(CATEGORY_DREAM, "exploration")
_DREAM_RETRY_IRI = capacity_iri(CATEGORY_DREAM, "retry")

_DS_IRIS = (DS_DREAM_TASK_REF, DS_DREAM_DIRECTIVE)
_CAP_IRIS = (_DREAM_MAINTENANCE_IRI, _DREAM_EXPLORATION_IRI, _DREAM_RETRY_IRI)
_FAMILY_IRIS = _DS_IRIS + _CAP_IRIS


def install_dream_capacities(capacity_layer) -> None:
    """Register every ``dream`` family DataState + capacity on ``capacity_layer``.

    Idempotent with partial-state detection per ``install_text_capacities``
    / ``install_consolidate_capacities``. Targets Global (no ``session``
    argument; admin/bootstrap concern). DataStates first, then the three
    capacities.

    Raises:
        CapacityRegistrationError: Partial install state detected.
    """
    mg = capacity_layer.global_metagraph()
    cap_index = capacity_layer._capacity_index[mg.metagraph_id]
    ds_graph = ensure_datastate_graph(mg, strict=capacity_layer._strict)

    ds_present = {iri for iri in _DS_IRIS if iri in ds_graph.nodes}
    cap_present = {iri for iri in _CAP_IRIS if iri in cap_index}
    present_total = len(ds_present) + len(cap_present)

    if present_total == len(_FAMILY_IRIS):
        return  # all present — no-op
    if present_total > 0:
        raise CapacityRegistrationError(
            "install_dream_capacities: partial install state detected — "
            f"datastates_present={sorted(ds_present)}, "
            f"capacities_present={sorted(cap_present)}, "
            f"missing={sorted(set(_FAMILY_IRIS) - ds_present - cap_present)}"
        )
    # None present — install all members (DataStates first).
    for ds in dream_datastates():
        capacity_layer.register_datastate(ds)
    capacity_layer.register_capacity(build_dream_maintenance())
    capacity_layer.register_capacity(build_dream_exploration())
    capacity_layer.register_capacity(build_dream_retry())


__all__ = [
    "DreamExecutionPolicy",
    "ENTRY_POINT_LATEST_ACTIVE_TASKRUN",
    "REPLAN_LEVEL_TASKRUN",
    "ReplanInjectionDirective",
    "DreamDirective",
    "DS_DREAM_TASK_REF",
    "DS_DREAM_DIRECTIVE",
    "dream_datastates",
    "build_dream_maintenance",
    "build_dream_exploration",
    "build_dream_retry",
    "install_dream_capacities",
]
