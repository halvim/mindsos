"""Pipeline-finder seam + DAG result type (ADR-0071 + §amendment-2).

L3 owns the ``Finder`` **interface** plus each concrete **algorithm**
(BFS, conjunction/fold) — they are computation, and ``find_pipeline``
already lives at L3. *Which* strategy fires is an **L4** selection
policy (ADR-0071 §amendment-2). No L4 "real finder" exists to extend
(``plan_construction.py`` is a v0 stub), so the conjunction finder is
net-new at L3.

**Result is a converging DAG (``PipelineDAG``).** The linear
``Pipeline``/``PipelineStep`` retired here cannot represent a converging
hyperpath (a capacity consuming several inputs each produced by a
different upstream path, or a fold over N producers of one type). The
replacement is safe — the linear type had **zero production consumers**
(verified: no L4/Server/L2/L0 import; the L5-chain ``Pipeline`` in
``chain_artifacts.py`` is an unrelated dataclass; the L2
``promoted_pipelines`` schema has no live writer).

**Two real strategies ship** (so the seam is not premature):

* :class:`BFSFinder` — the original ADR-0071 shortest-by-capacity-count
  walk, re-expressed to emit a *degenerate-linear* ``PipelineDAG``
  (ADR-0071 §am-2 PB-F). Single-input semantics retained: it fires a
  capacity off **one** reachable input (the ``via`` datastate) and does
  not resolve the capacity's other declared inputs — that latent
  multi-input unsoundness is exactly what the conjunction finder fixes.
* :class:`ConjunctionFinder` — the sound multi-input finder. A backward
  hyperpath search whose per-capacity resolution is driven **per typed
  input-group** (``_CapacityBase.input_group``, ADR-0159 §amendment-1):
  ``all_required`` (AND over inputs), ``any_of`` (optional-union), or
  ``fold`` (aggregate over **all** producers of an input) — each crossed
  with **OR over the producers** of a consumed DataState. Reads the
  input-group from the **declaration registry** (Decision 8 — no graph
  hyperedge at v1), mirroring ``views.inputs_of``'s declaration-primary
  read.

**Constraints are deliberately ignored** at this layer per ADR-0071;
L4 does the post-hoc filtering pass via ``iter_constraints``.

**Deferred (consumer discipline):** the promoted-path-lookup strategy
(``promoted-pipelines`` has no writer — verified) and the *graph* form of
the input-group (a type-layer typed hyperedge + a hyperedge-aware view
walk, ADR-0156 §am) are out of scope until their consumers land.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Deque,
    Dict,
    FrozenSet,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
)

from .exceptions import PipelineNotFoundError
from .identifiers import (
    INPUT_GROUP_ALL_REQUIRED,
    INPUT_GROUP_ANY_OF,
    INPUT_GROUP_FOLD,
)
from .types import SessionArg

if TYPE_CHECKING:  # pragma: no cover — circular-import guard
    from .capacity_layer import CapacityLayer
    from .views import CapacityLayerView


# ── DAG result type (ADR-0071 §amendment-2, part 4) ───────────────────

#: Edge ``producer`` sentinel: the datastate is a *start* datastate
#: (an available input to the whole pipeline), not the output of a step.
START: int = -1


@dataclass(frozen=True)
class DAGStep:
    """One capacity invocation (a node in the pipeline DAG).

    Attributes:
        capacity_iri: The capacity to run at this step.
        input_datastates: DataState IRIs the capacity consumes (its full
            declared input set — the finder records *all* of them, even
            for ``BFSFinder`` where only the ``via`` input is wired).
        output_datastates: DataState IRIs the capacity produces.
    """

    capacity_iri: str
    input_datastates: Tuple[str, ...]
    output_datastates: Tuple[str, ...]


@dataclass(frozen=True)
class DAGEdge:
    """A dataflow edge in the pipeline DAG.

    ``datastate`` produced by step index ``producer`` (or :data:`START`
    when it is a start datastate) is consumed by step index ``consumer``.
    A ``fold`` consumer has several edges sharing one ``datastate`` with
    distinct ``producer`` indices (fan-in); a converging consumer has
    edges with distinct ``datastate`` values.
    """

    producer: int
    consumer: int
    datastate: str


@dataclass(frozen=True)
class PipelineDAG:
    """A converging capacity DAG producing ``target_datastate`` from the
    available ``start_datastates``.

    ``steps`` are **topologically ordered**: every step appears after the
    steps that produce its consumed inputs. An empty ``steps`` tuple means
    the target is already among ``start_datastates`` (no-op).

    ``__iter__`` / ``__len__`` range over ``steps`` so callers that
    treated the retired linear ``Pipeline`` as a step sequence keep
    working.
    """

    start_datastates: Tuple[str, ...]
    target_datastate: str
    steps: Tuple[DAGStep, ...]
    edges: Tuple[DAGEdge, ...] = ()

    def __iter__(self):
        return iter(self.steps)

    def __len__(self) -> int:
        return len(self.steps)

    # ── serialization (composite-persistence residual, ADR-0182 codec) ──

    def to_dict(self) -> Dict[str, Any]:
        """Plain-``dict`` form for the ``learned-parameters`` descriptor.

        Round-trips through the ADR-0182 node-value codec (lists +
        primitives only). See :meth:`from_dict`.
        """
        return {
            "start_datastates": list(self.start_datastates),
            "target_datastate": self.target_datastate,
            "steps": [
                {
                    "capacity_iri": s.capacity_iri,
                    "input_datastates": list(s.input_datastates),
                    "output_datastates": list(s.output_datastates),
                }
                for s in self.steps
            ],
            "edges": [
                {
                    "producer": e.producer,
                    "consumer": e.consumer,
                    "datastate": e.datastate,
                }
                for e in self.edges
            ],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PipelineDAG":
        """Rebuild a :class:`PipelineDAG` from its :meth:`to_dict` form."""
        return cls(
            start_datastates=tuple(data["start_datastates"]),
            target_datastate=data["target_datastate"],
            steps=tuple(
                DAGStep(
                    capacity_iri=s["capacity_iri"],
                    input_datastates=tuple(s["input_datastates"]),
                    output_datastates=tuple(s["output_datastates"]),
                )
                for s in data["steps"]
            ),
            edges=tuple(
                DAGEdge(
                    producer=e["producer"],
                    consumer=e["consumer"],
                    datastate=e["datastate"],
                )
                for e in data.get("edges", ())
            ),
        )


# ── view resolution shared by the strategies ─────────────────────────


def _view_for(
    capacity_layer: "CapacityLayer", session: SessionArg
) -> "CapacityLayerView":
    """Resolve the Global or per-user Local view (R3 PB-44(a) inline)."""
    target_uid = session.user_id if session is not None else None
    return (
        capacity_layer.global_view()
        if target_uid is None
        else capacity_layer.local_view(target_uid)
    )


def _input_group_of(capacity_layer: "CapacityLayer", capacity_iri: str) -> str:
    """Read a capacity's ``input_group`` from the declaration registry.

    Decision 8: the finder reads the declaration, not the graph. Defaults
    to ``all_required`` when no declaration is registered (a graph-only
    node, e.g. a bare reference) — the sound-composer default.
    """
    try:
        decl = capacity_layer.get_declaration(capacity_iri)
    except Exception:  # noqa: BLE001 — missing declaration → default
        return INPUT_GROUP_ALL_REQUIRED
    return getattr(decl, "input_group", INPUT_GROUP_ALL_REQUIRED)


# ── Finder interface (ADR-0071 §amendment-2, part 1) ──────────────────


class Finder(ABC):
    """An L3 pipeline-finder strategy.

    The algorithm is L3 (computation); *which* strategy fires is an L4
    selection policy. Every strategy returns a :class:`PipelineDAG`.
    """

    @abstractmethod
    def find(
        self,
        capacity_layer: "CapacityLayer",
        *,
        session: SessionArg = None,
        start_datastates: Tuple[str, ...],
        target_datastate: str,
        max_depth: int = 8,
    ) -> PipelineDAG:
        """Return a DAG producing ``target_datastate`` from
        ``start_datastates``, or raise :class:`PipelineNotFoundError`."""
        raise NotImplementedError


# ── BFS strategy (original ADR-0071; degenerate-linear DAG, PB-F) ──────


class BFSFinder(Finder):
    """Shortest-by-capacity-count forward walk → degenerate-linear DAG.

    Identical reachability to the Phase 30/42 BFS: frontier is keyed on
    DataState IRIs; ``consumers_of`` advances by CONSUMES, ``outputs_of``
    by PRODUCES (ADR-0156). It fires each capacity off the **single**
    ``via`` datastate it arrived on and wires only that one input — the
    capacity's other declared inputs are recorded on the
    :class:`DAGStep` but left unwired. That single-input composition is
    the latent unsoundness :class:`ConjunctionFinder` exists to fix.
    """

    def find(
        self,
        capacity_layer: "CapacityLayer",
        *,
        session: SessionArg = None,
        start_datastates: Tuple[str, ...],
        target_datastate: str,
        max_depth: int = 8,
    ) -> PipelineDAG:
        view = _view_for(capacity_layer, session)

        if target_datastate in set(start_datastates):
            return PipelineDAG(
                start_datastates=tuple(start_datastates),
                target_datastate=target_datastate,
                steps=(),
                edges=(),
            )

        # Queue entries: (current_ds, steps, edges, producer_idx_of_current_ds)
        Entry = Tuple[str, Tuple[DAGStep, ...], Tuple[DAGEdge, ...], int]
        queue: Deque[Entry] = deque()
        visited: Set[str] = set()
        for sds in start_datastates:
            queue.append((sds, (), (), START))
            visited.add(sds)

        while queue:
            current_ds, steps, edges, prod_idx = queue.popleft()
            if len(steps) >= max_depth:
                continue
            for cap in view.consumers_of(current_ds):
                cap_iri = cap.node_id
                outputs = tuple(view.outputs_of(cap_iri))
                new_idx = len(steps)
                new_step = DAGStep(
                    capacity_iri=cap_iri,
                    input_datastates=tuple(view.inputs_of(cap_iri)),
                    output_datastates=outputs,
                )
                new_steps = steps + (new_step,)
                new_edges = edges + (
                    DAGEdge(producer=prod_idx, consumer=new_idx, datastate=current_ds),
                )
                for out in outputs:
                    if out == target_datastate:
                        return PipelineDAG(
                            start_datastates=tuple(start_datastates),
                            target_datastate=target_datastate,
                            steps=new_steps,
                            edges=new_edges,
                        )
                    if out not in visited:
                        visited.add(out)
                        queue.append((out, new_steps, new_edges, new_idx))

        raise PipelineNotFoundError(
            f"No pipeline found from {list(start_datastates)!r} to "
            f"{target_datastate!r} (max_depth={max_depth})"
        )


# ── Conjunction/fold strategy (ADR-0071 §am-2 part 2; ADR-0159 §am-1) ──


class ConjunctionFinder(Finder):
    """Sound multi-input finder over the typed input-groups.

    Backward hyperpath search from ``target_datastate``. To produce a
    datastate the finder selects a producer capacity (**OR over
    producers** — deterministic first-by-IRI; no backtracking on a deep
    failure at v1, ARC's three cases are unambiguous), then resolves that
    capacity's declared inputs by its ``input_group``:

    * ``all_required`` — every input must be producible (AND); one edge
      per input from the chosen upstream producer.
    * ``any_of`` — at least one input must be producible (optional-union);
      edges only for the producible inputs.
    * ``fold`` — each input is fanned-in from **all** of its satisfiable
      producers (aggregate); one edge per producer.

    A two-phase design avoids partial-DAG leaks: a pure
    ``_satisfiable`` reachability check runs first, then ``_fire`` only
    constructs over satisfiable producers. Shared upstream producers fire
    once (memoised), so diamonds and folds converge correctly.
    """

    def find(
        self,
        capacity_layer: "CapacityLayer",
        *,
        session: SessionArg = None,
        start_datastates: Tuple[str, ...],
        target_datastate: str,
        max_depth: int = 8,
    ) -> PipelineDAG:
        view = _view_for(capacity_layer, session)
        starts: FrozenSet[str] = frozenset(start_datastates)

        if target_datastate in starts:
            return PipelineDAG(
                start_datastates=tuple(start_datastates),
                target_datastate=target_datastate,
                steps=(),
                edges=(),
            )

        # ── phase 1: reachability (no mutation) ──
        def ds_reachable(ds: str, stack: FrozenSet[str]) -> bool:
            if ds in starts:
                return True
            if ds in stack:  # cycle — cannot rely on producing self
                return False
            nxt = stack | {ds}
            return any(
                cap_satisfiable(cap.node_id, nxt) for cap in view.producers_of(ds)
            )

        def cap_satisfiable(cap_iri: str, stack: FrozenSet[str]) -> bool:
            inputs = view.inputs_of(cap_iri)
            if not inputs:
                return True
            mode = _input_group_of(capacity_layer, cap_iri)
            if mode == INPUT_GROUP_ANY_OF:
                return any(ds_reachable(ds, stack) for ds in inputs)
            # all_required and fold both need every declared input producible
            return all(ds_reachable(ds, stack) for ds in inputs)

        if not any(
            cap_satisfiable(cap.node_id, frozenset())
            for cap in view.producers_of(target_datastate)
        ):
            raise PipelineNotFoundError(
                f"No pipeline found to {target_datastate!r} from "
                f"{list(start_datastates)!r} (no satisfiable producer)"
            )

        # ── phase 2: construct over satisfiable producers ──
        steps: List[DAGStep] = []
        edges: List[DAGEdge] = []
        fired: Dict[str, int] = {}  # capacity_iri -> step index

        def fire(cap_iri: str, depth: int) -> int:
            if cap_iri in fired:
                return fired[cap_iri]
            if depth > max_depth:
                raise PipelineNotFoundError(
                    f"max_depth={max_depth} exceeded resolving {cap_iri!r}"
                )
            inputs = tuple(view.inputs_of(cap_iri))
            outputs = tuple(view.outputs_of(cap_iri))
            mode = _input_group_of(capacity_layer, cap_iri)
            incoming: List[Tuple[int, str]] = []
            for ds in inputs:
                if ds in starts:
                    incoming.append((START, ds))
                    continue
                producers = sorted(
                    view.producers_of(ds), key=lambda n: n.node_id
                )
                satisfiable = [
                    p for p in producers if cap_satisfiable(p.node_id, frozenset())
                ]
                if mode == INPUT_GROUP_FOLD:
                    for p in satisfiable:  # fan-in: every producer
                        incoming.append((fire(p.node_id, depth + 1), ds))
                elif satisfiable:  # all_required / any_of: OR → first producer
                    incoming.append((fire(satisfiable[0].node_id, depth + 1), ds))
                elif mode == INPUT_GROUP_ALL_REQUIRED:
                    raise PipelineNotFoundError(
                        f"required input {ds!r} of {cap_iri!r} is unproducible"
                    )
                # any_of with no producible producer for this input: skip it

            step_idx = len(steps)
            steps.append(
                DAGStep(
                    capacity_iri=cap_iri,
                    input_datastates=inputs,
                    output_datastates=outputs,
                )
            )
            fired[cap_iri] = step_idx
            for prod_idx, ds in incoming:
                edges.append(
                    DAGEdge(producer=prod_idx, consumer=step_idx, datastate=ds)
                )
            return step_idx

        target_producers = sorted(
            (
                p
                for p in view.producers_of(target_datastate)
                if cap_satisfiable(p.node_id, frozenset())
            ),
            key=lambda n: n.node_id,
        )
        fire(target_producers[0].node_id, 0)

        return PipelineDAG(
            start_datastates=tuple(start_datastates),
            target_datastate=target_datastate,
            steps=tuple(steps),
            edges=tuple(edges),
        )


# ── back-compat free function (BFS strategy entry point) ──────────────


def find_pipeline(
    capacity_layer: "CapacityLayer",
    *,
    session: SessionArg = None,
    start_datastate: str,
    target_datastate: str,
    max_depth: int = 8,
) -> PipelineDAG:
    """Find the shortest capacity chain from ``start_datastate`` to
    ``target_datastate`` (the ADR-0071 BFS strategy).

    Back-compat entry point: keeps the singular ``start_datastate=``
    keyword and delegates to :class:`BFSFinder`, returning a
    degenerate-linear :class:`PipelineDAG`. For sound multi-input
    composition use :class:`ConjunctionFinder` directly (selected by L4).

    Raises:
        PipelineNotFoundError: no chain within ``max_depth`` steps.
    """
    return BFSFinder().find(
        capacity_layer,
        session=session,
        start_datastates=(start_datastate,),
        target_datastate=target_datastate,
        max_depth=max_depth,
    )


__all__ = [
    "START",
    "DAGStep",
    "DAGEdge",
    "PipelineDAG",
    "Finder",
    "BFSFinder",
    "ConjunctionFinder",
    "find_pipeline",
]
