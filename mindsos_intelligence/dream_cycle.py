"""L4 dream-cycle driver (ADR-0178; Chat B §5.2 dream-as-live).

Wires the Phase-46 ``DreamCycleTimer`` callback to the Phase-45 ``dream.*``
capacities: each tick pulls episode descriptors from the corpus, invokes the
three directive-emitting capacities, and (optionally) re-executes each emitted
``DreamDirective``. Signals/records carry ``dream_source_episode_iri``
provenance (Chat B §5.2).

v1 scope (PB-9, ADR-0178): the timer → capacity → directive → re-exec **wiring**
ships here, exercised over the real episode corpus. The faithful episode→MM
reconstruction (``fork_dream_mm`` of a rebuilt episode MM) and the
``replay_recorded`` vs ``re_execute_capacities`` behavioral differentiation +
real ALS signal firing are WSD-gated — v1 re-execution runs through the
provided ``re_executor`` hook with the directive's provenance.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from mindsos_capacity.builtins.dream import DS_DREAM_DIRECTIVE, DS_DREAM_TASK_REF
from mindsos_capacity.identifiers import CATEGORY_DREAM, capacity_iri

_DREAM_CAPACITY_IRIS = (
    capacity_iri(CATEGORY_DREAM, "maintenance"),
    capacity_iri(CATEGORY_DREAM, "exploration"),
    capacity_iri(CATEGORY_DREAM, "retry"),
)


def dream_task_ref(
    *, source_episode_iri: str, request_run_iri: str = "", failed: bool = False
) -> Dict[str, Any]:
    """Build the ``dream.task_ref`` record the dream capacities consume."""
    return {
        "source_episode_iri": source_episode_iri,
        "task_run_iri": request_run_iri,
        "failed": bool(failed),
    }


def invoke_dream_capacities(dispatcher: Any, request_ref: Dict[str, Any]) -> List[Any]:
    """Invoke the 3 ``dream.*`` capacities over ``task_ref``; return the emitted
    ``DreamDirective``s (dont-know ``None`` returns skipped). Each directive
    carries ``source_episode_iri`` provenance."""
    directives: List[Any] = []
    for iri in _DREAM_CAPACITY_IRIS:
        result = dispatcher.dispatch(iri, {DS_DREAM_TASK_REF: request_ref})
        if not getattr(result, "success", False):
            continue
        directive = result.outputs.get(DS_DREAM_DIRECTIVE)
        if directive is not None:
            directives.append(directive)
    return directives


def run_dream_cycle(
    dispatcher: Any,
    episodes: List[Dict[str, Any]],
    *,
    re_executor: Optional[Callable[[Any], None]] = None,
) -> List[Any]:
    """For each episode descriptor (``source_episode_iri`` / ``task_run_iri`` /
    ``failed``), invoke the dream capacities and re-execute each emitted
    directive via ``re_executor`` (if given). Returns all emitted directives."""
    all_directives: List[Any] = []
    for ep in episodes:
        request_ref = dream_task_ref(
            source_episode_iri=ep["source_episode_iri"],
            request_run_iri=ep.get("task_run_iri", ""),
            failed=ep.get("failed", False),
        )
        for directive in invoke_dream_capacities(dispatcher, request_ref):
            if re_executor is not None:
                re_executor(directive)
            all_directives.append(directive)
    return all_directives


class DreamDriver:
    """The ``IntelligenceLayer(dream_driver=...)`` callback (Phase-46 timer).

    ``episode_source()`` returns the episode descriptors (the dream corpus);
    ``re_executor(directive)`` optionally re-executes each emitted directive
    (the faithful re-exec + ALS firing land with WSD)."""

    def __init__(
        self,
        dispatcher: Any,
        episode_source: Callable[[], List[Dict[str, Any]]],
        *,
        re_executor: Optional[Callable[[Any], None]] = None,
    ) -> None:
        self._dispatcher = dispatcher
        self._episode_source = episode_source
        self._re_executor = re_executor

    def __call__(self) -> List[Any]:
        return run_dream_cycle(
            self._dispatcher,
            self._episode_source(),
            re_executor=self._re_executor,
        )


__all__ = ["dream_task_ref", "invoke_dream_capacities", "run_dream_cycle", "DreamDriver"]
