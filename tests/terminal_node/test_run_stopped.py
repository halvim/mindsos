"""L-2 — a terminal node on every non-success, so a stopped run is renderable.

``execute_pipeline`` used to write to ``capacity_mm`` ONLY on a successful
step: the cancelled / needs_input / failed returns all preceded
``writer.record``. A capacity failure therefore left **no node in the
grounding graph**, and a Decision Record renders from that graph and nothing
else — so every refusal that was not a *reading* refusal (which the seam makes
an ordinary successful return carrying an empty value) was structurally
unrenderable. Blocks runs 3 and 4 and guard G4.

**The two shapes are deliberately different, and that is the point.**

* ``step_failed`` / ``needs_input`` — the body RAN. The invocation is real, so
  it is in the graph: CapacityInstance + CONSUMES, then
  ``RunStopped --STOPPED_AT--> CapacityInstance``. The CONSUMES edges are the
  load-bearing part; they hang the stop off the values that led to it.
* ``cancelled`` — the cancel check precedes ``dispatcher.dispatch``, so the
  step never ran. RunStopped is minted ALONE. Minting a CapacityInstance would
  claim a capacity executed when it did not, which is the exact class of claim
  guard G3 exists to refuse.

Every test here fails against the pre-L-2 writer, which had no such node.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

import pytest

from mindsos_capacity.identifiers import (
    EDGE_CONSUMES,
    EDGE_PRODUCES,
    EDGE_STOPPED_AT,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_DATASTATE_INSTANCE,
    NODE_TYPE_RUN_STOPPED,
    PROP_RUN_STOPPED_BEFORE,
    PROP_RUN_STOPPED_DETAIL,
    RUN_STOPPED_CANCELLED,
    RUN_STOPPED_NEEDS_INPUT,
    RUN_STOPPED_REASONS,
    RUN_STOPPED_STEP_FAILED,
    run_stopped_iri,
)
from mindsos_intelligence.capacity_mm_writer import CapacityMMWriter, run_graph_role
from mindsos_intelligence.capacity_persister import make_node_value_encoder
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.pipeline_execution import execute_pipeline

REQ = "t1"
RUN = "pipelinerun:t1:1"
CAP_ONE = "capacity:derivation:one"
CAP_TWO = "capacity:derivation:two"


# ── duck-typed fakes (no dispatcher / finder / FalkorDB needed) ───────────


@dataclass
class _Step:
    capacity_iri: str
    input_datastates: Tuple[str, ...]


@dataclass
class _Pipeline:
    steps: Tuple[_Step, ...]


@dataclass
class _Result:
    success: bool
    outputs: Mapping[str, Any] = field(default_factory=dict)
    needs_input: Any = None
    error: Any = None


@dataclass
class _NeedsInput:
    missing: str


class _Dispatcher:
    """Returns a scripted result per capacity."""

    def __init__(self, results: Mapping[str, _Result]) -> None:
        self._results = results
        self.calls: list = []

    def dispatch(self, capacity_iri, inputs, *, cancel_token=None,
                 request_id=None, step_id=None):
        self.calls.append(capacity_iri)
        return self._results[capacity_iri]


class _CancelToken:
    """Cancelled from the Nth check onward (0 = before the first step).

    ``_is_cancelled`` duck-types on ``is_set()``, not ``is_cancelled()``.
    """

    def __init__(self, after: int = 0) -> None:
        self._checks = 0
        self._after = after

    def is_set(self) -> bool:
        cancelled = self._checks >= self._after
        self._checks += 1
        return cancelled


def _mm() -> MentalModel:
    return MentalModel(session_id="s", user_id="u")


def _graph(mm: MentalModel):
    role = run_graph_role(REQ, RUN)
    for g in mm.capacity_mm.graphs.values():
        if g.role == role:
            return g
    return None


def _nodes(graph, type_name):
    return [n for n in graph.nodes.values() if n.type_name == type_name]


def _edges(graph, type_name):
    return [e for e in graph.edges.values() if e.type_name == type_name]


def _two_step():
    return _Pipeline(steps=(
        _Step(CAP_ONE, ("datastate:a",)),
        _Step(CAP_TWO, ("datastate:b",)),
    ))


def _run(disp, pipe, mm, cancel_token=None):
    return execute_pipeline(
        disp, pipe, {"datastate:a": "A"},
        request_id=REQ, mm=mm, pipeline_run_ref=RUN,
        cancel_token=cancel_token,
    )


# ── the body ran and raised ───────────────────────────────────────────────


def _failing_second_step(mm):
    disp = _Dispatcher({
        CAP_ONE: _Result(success=True, outputs={"datastate:b": "B"}),
        CAP_TWO: _Result(success=False, error=RuntimeError("boom")),
    })
    res = _run(disp, _two_step(), mm)
    return res, _graph(mm)


def test_a_failed_step_leaves_a_terminal_node():
    mm = _mm()
    res, graph = _failing_second_step(mm)
    assert res.success is False
    stops = _nodes(graph, NODE_TYPE_RUN_STOPPED)
    assert len(stops) == 1
    assert stops[0].value == RUN_STOPPED_STEP_FAILED
    assert "boom" in (stops[0].properties or {})[PROP_RUN_STOPPED_DETAIL]


def test_the_stop_is_wired_to_the_invocation_that_failed():
    """STOPPED_AT points at the CapacityInstance, and that instance carries
    CONSUMES from the value that led to it — which is the whole reason the
    refusal is renderable rather than a bare 'something failed'."""
    mm = _mm()
    _, graph = _failing_second_step(mm)
    stopped_at = _edges(graph, EDGE_STOPPED_AT)
    assert len(stopped_at) == 1
    edge = stopped_at[0]
    assert edge.source.type_name == NODE_TYPE_RUN_STOPPED
    assert edge.target.type_name == NODE_TYPE_CAPACITY_INSTANCE
    assert edge.target.value == CAP_TWO
    consumed_by_failed = [
        e for e in _edges(graph, EDGE_CONSUMES) if e.target is edge.target
    ]
    assert len(consumed_by_failed) == 1
    assert consumed_by_failed[0].source.value == "B"


def test_a_failed_step_produces_no_datastate_instance():
    """It produced nothing, so it must claim nothing. Two DataStateInstances
    (the seed and step one's output), never a third."""
    mm = _mm()
    _, graph = _failing_second_step(mm)
    assert len(_nodes(graph, NODE_TYPE_DATASTATE_INSTANCE)) == 2
    produces = _edges(graph, EDGE_PRODUCES)
    assert len(produces) == 1
    assert produces[0].source.value == CAP_ONE


# ── the body ran and asked ────────────────────────────────────────────────


def test_needs_input_leaves_a_terminal_node_naming_what_is_missing():
    mm = _mm()
    disp = _Dispatcher({
        CAP_ONE: _Result(success=True, outputs={"datastate:b": "B"}),
        CAP_TWO: _Result(success=True, needs_input=_NeedsInput(missing="datastate:z")),
    })
    res = _run(disp, _two_step(), mm)
    assert res.success is False and res.needs_input is not None
    graph = _graph(mm)
    stops = _nodes(graph, NODE_TYPE_RUN_STOPPED)
    assert len(stops) == 1
    assert stops[0].value == RUN_STOPPED_NEEDS_INPUT
    assert (stops[0].properties or {})[PROP_RUN_STOPPED_DETAIL] == "datastate:z"
    # ADR-0196: the body ran, so the invocation IS in the graph.
    assert len(_edges(graph, EDGE_STOPPED_AT)) == 1


# ── the step never ran ────────────────────────────────────────────────────


def test_a_cancelled_run_mints_no_capacity_instance():
    """The cancel check precedes dispatch. A CapacityInstance here would say a
    capacity executed when it did not — what G3 exists to refuse."""
    mm = _mm()
    disp = _Dispatcher({CAP_ONE: _Result(success=True, outputs={"datastate:b": "B"})})
    res = _run(disp, _two_step(), mm, cancel_token=_CancelToken(after=0))
    assert res.cancelled is True
    assert disp.calls == []
    graph = _graph(mm)
    stops = _nodes(graph, NODE_TYPE_RUN_STOPPED)
    assert len(stops) == 1
    assert stops[0].value == RUN_STOPPED_CANCELLED
    assert (stops[0].properties or {})[PROP_RUN_STOPPED_BEFORE] == CAP_ONE
    assert _nodes(graph, NODE_TYPE_CAPACITY_INSTANCE) == []
    assert _edges(graph, EDGE_STOPPED_AT) == []


def test_record_stopped_refuses_the_cancelled_reason():
    """The two shapes must not collapse into one method with a flag."""
    mm = _mm()
    writer = CapacityMMWriter(mm, REQ, RUN)
    with pytest.raises(ValueError, match="record_cancelled"):
        writer.record_stopped(CAP_ONE, (), RUN_STOPPED_CANCELLED)


def test_record_stopped_refuses_an_undeclared_reason():
    mm = _mm()
    writer = CapacityMMWriter(mm, REQ, RUN)
    with pytest.raises(ValueError, match="unknown run-stopped reason"):
        writer.record_stopped(CAP_ONE, (), "went_sideways")
    assert "went_sideways" not in RUN_STOPPED_REASONS


def test_record_stopped_refuses_the_empty_domain_reason():
    """ADR-0201 am-5: an empty fold domain means the reducer never
    dispatched, so record_stopped's CapacityInstance would be a false
    invocation — the record_cancelled argument verbatim (G3)."""
    from mindsos_capacity.identifiers import RUN_STOPPED_EMPTY_DOMAIN

    mm = _mm()
    writer = CapacityMMWriter(mm, REQ, RUN)
    with pytest.raises(ValueError, match="record_empty_domain"):
        writer.record_stopped(CAP_ONE, (), RUN_STOPPED_EMPTY_DOMAIN)


def test_record_empty_domain_mints_the_stop_alone():
    """RunStopped alone: no CapacityInstance, no STOPPED_AT edge, the
    stopped-before capacity carried as a property — record_cancelled's shape
    with the empty-domain reason (ADR-0201 am-5)."""
    from mindsos_capacity.identifiers import RUN_STOPPED_EMPTY_DOMAIN

    mm = _mm()
    writer = CapacityMMWriter(mm, REQ, RUN)
    writer.record_empty_domain(
        before_capacity_iri=CAP_ONE, detail="nothing to decide from"
    )
    graph = _graph(mm)
    stops = _nodes(graph, NODE_TYPE_RUN_STOPPED)
    assert len(stops) == 1
    assert stops[0].value == RUN_STOPPED_EMPTY_DOMAIN
    assert (stops[0].properties or {})[PROP_RUN_STOPPED_BEFORE] == CAP_ONE
    assert _nodes(graph, NODE_TYPE_CAPACITY_INSTANCE) == []
    assert _edges(graph, EDGE_STOPPED_AT) == []


# ── one per run, and none on success ──────────────────────────────────────


def test_a_successful_run_writes_no_terminal_node():
    mm = _mm()
    disp = _Dispatcher({
        CAP_ONE: _Result(success=True, outputs={"datastate:b": "B"}),
        CAP_TWO: _Result(success=True, outputs={"datastate:c": "C"}),
    })
    res = _run(disp, _two_step(), mm)
    assert res.success is True
    assert _nodes(_graph(mm), NODE_TYPE_RUN_STOPPED) == []


def test_the_terminal_node_iri_is_deterministic_per_run():
    """Which is what makes 'exactly one RunStopped node per run' a structural
    assertion (guard G4) rather than a property count."""
    mm = _mm()
    _, graph = _failing_second_step(mm)
    assert list(graph.nodes)  # sanity: the run wrote something
    expected = run_stopped_iri(REQ, RUN)
    assert _nodes(graph, NODE_TYPE_RUN_STOPPED)[0].node_id == expected
    assert run_stopped_iri(REQ, RUN) == run_stopped_iri(REQ, "t1:1")


# ── it costs the persister nothing ────────────────────────────────────────


def test_the_terminal_node_persists_with_the_default_encoder():
    """The node's value is the reason TOKEN, a primitive, so the Slice-B
    encoder — which dispatches only on DataStateInstance — takes it unchanged.
    This is why L-2 needed no persister change."""
    mm = _mm()
    _, graph = _failing_second_step(mm)
    encode = make_node_value_encoder({})
    node = _nodes(graph, NODE_TYPE_RUN_STOPPED)[0]
    assert encode(node) == RUN_STOPPED_STEP_FAILED


# ── the no-MM path is untouched ───────────────────────────────────────────


def test_no_mm_means_no_writes_and_no_crash():
    disp = _Dispatcher({
        CAP_ONE: _Result(success=True, outputs={"datastate:b": "B"}),
        CAP_TWO: _Result(success=False, error=RuntimeError("boom")),
    })
    res = execute_pipeline(
        disp, _two_step(), {"datastate:a": "A"}, request_id=REQ,
    )
    assert res.success is False
    assert res.capacity_graph is None


def test_every_node_a_stopped_run_leaves_routes_to_capacity_mm():
    """**Driven, because the prefix table agreeing with itself proves nothing.**

    ``runstopped:`` was a top-level prefix no sub-MM owned, so
    ``mm.sub_mm_for_iri`` raised ``KeyError`` on the terminal node this whole
    module is about — a node sitting in a capacity run graph that the router
    said belonged nowhere. It survived because nothing had ever asked: the
    equivalent guard in ``tests/phase_48/test_capacity_mm_writer.py`` only ever
    sees a SUCCESSFUL run, which by construction has no RunStopped in it.

    Found when the run manifest moved into ``execute_pipeline`` and reddened
    that guard for ``runmanifest:``; the sibling was one line away.
    """
    mm = _mm()
    _, graph = _failing_second_step(mm)
    assert _nodes(graph, NODE_TYPE_RUN_STOPPED), "the run must actually have stopped"
    for node_id in graph.nodes:
        assert mm.sub_mm_for_iri(node_id) is mm.capacity_mm, node_id
