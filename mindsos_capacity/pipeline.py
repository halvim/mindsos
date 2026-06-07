"""Pipeline-finder primitives (Phase 30; ADR-0071).

The vertical slice ships a single datastate-keyed BFS walker:

    raw_datastate ──[capacity_A]──▶ intermediate_datastate
                                    ──[capacity_B]──▶ target_datastate

Given a ``start_datastate`` IRI and a ``target_datastate`` IRI, BFS
steps forward through the L3 metagraph's bipartite PRODUCES/CONSUMES
edge set and returns the first pipeline it discovers (= shortest by
capacity count, since BFS expands frontiers by hop). That's enough to
prove the vertical slice — L4's real pipeline-finder will extend this
with cost, learned confidence, and promoted-path lookup.

**Algorithm shape.** Frontier is keyed on **DataState IRIs**, NOT on
Capacity IRIs. ``view.consumers_of(datastate)`` returns candidate
capacities that consume the current datastate (via CONSUMES edges);
``view.outputs_of(capacity)`` (via PRODUCES edges) pushes the next
frontier. Under ADR-0156 the bipartite edge set is the explicit
structural substrate emitted at ``register_capacity`` time; the BFS
does not call ``successors_of`` (capacity-to-capacity walk).

**Constraints are deliberately ignored** here per ADR-0071. L4 does
the post-hoc filtering pass via ``iter_constraints``.

**No learned confidence** at this layer — that's L4 on purpose.

**Adapter synthesis is NOT performed.** Adapters that already exist in
L3 participate as ordinary capacities.

Halvim Phase 30 divergences from parent reference:
- ``find_pipeline`` takes ``session: SessionArg = None`` (halvim Phase
  28 R1 PB-14 lock) where parent has ``user_id: Optional[str] = None``.
- The ``build_bfs_capacity_declaration`` scaffolding factory is
  OMITTED at Phase 30 (Phase 27 R3 PB-26 "no scaffolding without
  consumer" precedent). Phase 31 ships the registered builtin form
  directly per PHASE_MAP §31 "install pathfinding".
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Deque, List, Optional, Set, Tuple

from .exceptions import PipelineNotFoundError
from .types import SessionArg

if TYPE_CHECKING:  # pragma: no cover — circular-import guard (R2 PB-28(a))
    from .capacity_layer import CapacityLayer


# ── Pipeline result shape ─────────────────────────────────────────────


@dataclass(frozen=True)
class PipelineStep:
    """One invocation in a pipeline.

    Attributes:
        capacity_iri: The capacity to run at this step.
        input_datastates: DataState IRIs the capacity consumes.
        output_datastates: DataState IRIs the capacity produces.
        via_datastate: The DataState IRI linking this step into the
            current path (i.e., which of the previous step's outputs
            this step consumes). ``None`` for the first step in a
            pipeline that starts from ``start_datastate`` directly.
    """

    capacity_iri: str
    input_datastates: Tuple[str, ...]
    output_datastates: Tuple[str, ...]
    via_datastate: Optional[str] = None


@dataclass(frozen=True)
class Pipeline:
    """A chain of capacities producing ``target_datastate`` from
    ``start_datastate``.

    An empty ``steps`` tuple means ``start_datastate == target_datastate``
    (no-op pipeline; the requested target is already present).
    """

    start_datastate: str
    target_datastate: str
    steps: Tuple[PipelineStep, ...]

    def __iter__(self):
        return iter(self.steps)

    def __len__(self) -> int:
        return len(self.steps)


# ── The BFS itself (ADR-0071) ────────────────────────────────────────


def find_pipeline(
    capacity_layer: "CapacityLayer",
    *,
    session: SessionArg = None,
    start_datastate: str,
    target_datastate: str,
    max_depth: int = 8,
) -> Pipeline:
    """Find the shortest capacity chain from ``start_datastate`` to
    ``target_datastate``.

    Walks forward only; no adapter synthesis (adapters that already
    exist in L3 participate like any other capacity).

    Args:
        capacity_layer: The :class:`CapacityLayer` to walk.
        session: Optional :class:`SessionProtocol`-conforming object.
            When supplied, BFS walks the per-user Local metagraph view;
            when ``None``, BFS walks the Global metagraph view.
        start_datastate: DataState IRI to start from.
        target_datastate: DataState IRI to reach.
        max_depth: Maximum path length (capacity count). BFS abandons
            any frontier whose path length has reached this bound.

    Raises:
        PipelineNotFoundError: If no chain exists from start to target
            within ``max_depth`` steps.

    Returns:
        A :class:`Pipeline` whose ``steps`` form the shortest-by-
        capacity-count chain. ``steps`` is empty when start == target.
    """
    # Inline session→user_id resolution (R3 PB-44(a) — net-new API has
    # no legacy `user_id=` kw to deprecate; bypass _resolve_session_arg).
    target_uid = session.user_id if session is not None else None
    view = (
        capacity_layer.global_view()
        if target_uid is None
        else capacity_layer.local_view(target_uid)
    )

    if start_datastate == target_datastate:
        return Pipeline(
            start_datastate=start_datastate,
            target_datastate=target_datastate,
            steps=(),
        )

    # BFS frontier: queue entries are (current_datastate, path_of_steps).
    queue: Deque[Tuple[str, Tuple[PipelineStep, ...]]] = deque()
    queue.append((start_datastate, ()))
    visited: Set[str] = {start_datastate}

    while queue:
        current_ds, path = queue.popleft()
        if len(path) >= max_depth:
            continue

        consumers = view.consumers_of(current_ds)
        for cap in consumers:
            outputs = tuple(view.outputs_of(cap.node_id))
            step = PipelineStep(
                capacity_iri=cap.node_id,
                input_datastates=tuple(view.inputs_of(cap.node_id)),
                output_datastates=outputs,
                via_datastate=current_ds,
            )
            for out in outputs:
                if out == target_datastate:
                    return Pipeline(
                        start_datastate=start_datastate,
                        target_datastate=target_datastate,
                        steps=path + (step,),
                    )
                if out not in visited:
                    visited.add(out)
                    queue.append((out, path + (step,)))

    raise PipelineNotFoundError(
        f"No pipeline found from {start_datastate!r} to "
        f"{target_datastate!r} (max_depth={max_depth})"
    )


__all__ = [
    "Pipeline",
    "PipelineStep",
    "find_pipeline",
]
