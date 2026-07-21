"""CR#4 Slice 2 — the capacity-MM writer grounds pipeline execution into
``capacity_mm`` (ADR-0201): one CapacityInstance per invocation, one
DataStateInstance per output, PRODUCES/CONSUMES edges forming the grounding
DAG, minted instance IRIs routing to capacity_mm, and ``mm=None`` unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.pipeline_execution import execute_pipeline
from mindsos_intelligence.capacity_mm_writer import (
    CapacityMMWriter,
    DATASTATE_INSTANCE_GRAPH_ROLE,
    CAPACITY_INSTANCE_GRAPH_ROLE,
)
from mindsos_capacity.identifiers import (
    EDGE_CONSUMES,
    EDGE_PRODUCES,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_DATASTATE_INSTANCE,
    PROP_DATASTATE_INSTANCE_TYPE,
)


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


class _Dispatcher:
    """Returns each capacity's declared outputs from a fixed table."""

    def __init__(self, outputs_by_cap: Mapping[str, Mapping[str, Any]]) -> None:
        self._out = outputs_by_cap
        self.calls: list = []

    def dispatch(self, capacity_iri, inputs, *, cancel_token=None, task_id=None, step_id=None):
        self.calls.append((capacity_iri, dict(inputs)))
        return _Result(success=True, outputs=dict(self._out.get(capacity_iri, {})))


def _mm() -> MentalModel:
    return MentalModel(session_id="s", user_id="u")


def _graph(mm: MentalModel, role: str):
    for g in mm.capacity_mm.graphs.values():
        if g.role == role:
            return g
    return None


def _two_step():
    """a -(one)-> b -(two)-> c."""
    pipe = _Pipeline(steps=(
        _Step("capacity:derivation:one", ("datastate:a",)),
        _Step("capacity:derivation:two", ("datastate:b",)),
    ))
    disp = _Dispatcher({
        "capacity:derivation:one": {"datastate:b": "B"},
        "capacity:derivation:two": {"datastate:c": "C"},
    })
    return pipe, disp


# ── tests ─────────────────────────────────────────────────────────────────


def test_writes_grounding_dag_when_mm_present():
    mm = _mm()
    pipe, disp = _two_step()
    res = execute_pipeline(
        disp, pipe, {"datastate:a": "A"},
        task_id="t1", mm=mm, pipeline_run_ref="pipelinerun:t1:1",
    )
    assert res.success
    assert res.outputs["datastate:c"] == "C"

    ds_graph = _graph(mm, DATASTATE_INSTANCE_GRAPH_ROLE)
    cap_graph = _graph(mm, CAPACITY_INSTANCE_GRAPH_ROLE)
    # 3 DataStateInstances (seed a, output b, output c); 2 CapacityInstances.
    assert len(ds_graph.nodes) == 3
    assert len(cap_graph.nodes) == 2
    assert all(n.type_name == NODE_TYPE_DATASTATE_INSTANCE for n in ds_graph.nodes.values())
    assert all(n.type_name == NODE_TYPE_CAPACITY_INSTANCE for n in cap_graph.nodes.values())

    # Grounding DAG: 2 CONSUMES (a->one, b->two) + 2 PRODUCES (one->b, two->c).
    edge_types = sorted(e.type_name for e in mm.capacity_mm.intergraph_edges.values())
    assert edge_types == [EDGE_CONSUMES, EDGE_CONSUMES, EDGE_PRODUCES, EDGE_PRODUCES]


def test_datastate_instance_carries_payload_and_type():
    mm = _mm()
    pipe, disp = _two_step()
    execute_pipeline(disp, pipe, {"datastate:a": "A"}, task_id="t1", mm=mm)
    ds_graph = _graph(mm, DATASTATE_INSTANCE_GRAPH_ROLE)
    by_type = {
        n.properties[PROP_DATASTATE_INSTANCE_TYPE]: n.value
        for n in ds_graph.nodes.values()
    }
    assert by_type == {"datastate:a": "A", "datastate:b": "B", "datastate:c": "C"}


def test_minted_instance_iris_route_to_capacity_mm():
    mm = _mm()
    pipe, disp = _two_step()
    execute_pipeline(disp, pipe, {"datastate:a": "A"}, task_id="t1", mm=mm)
    ds_graph = _graph(mm, DATASTATE_INSTANCE_GRAPH_ROLE)
    cap_graph = _graph(mm, CAPACITY_INSTANCE_GRAPH_ROLE)
    for node_id in list(ds_graph.nodes) + list(cap_graph.nodes):
        assert mm.sub_mm_for_iri(node_id) is mm.capacity_mm  # no KeyError, right room


def test_root_mints_grounding_root():
    mm = _mm()
    w = CapacityMMWriter(mm, "t1", "pipelinerun:t1:1")
    root_iri = w.root("datastate:arc.raw_task", {"grid": [[1]]})
    assert root_iri == "datastate:arc.raw_task#t1.root"
    assert w.index["datastate:arc.raw_task"] == root_iri
    assert mm.sub_mm_for_iri(root_iri) is mm.capacity_mm


def test_no_mm_is_value_only_and_leaves_rooms_empty():
    mm = _mm()
    pipe, disp = _two_step()
    res = execute_pipeline(disp, pipe, {"datastate:a": "A"}, task_id="t1")  # no mm
    assert res.success
    assert res.outputs["datastate:c"] == "C"
    # A fresh MM the run never touched stays empty (byte-identical old path).
    assert sum(len(g.nodes) for g in mm.capacity_mm.graphs.values()) == 0


def test_lock_never_held_across_dispatch():
    mm = _mm()

    class _LockProbe(_Dispatcher):
        def __init__(self, outputs_by_cap, mm):
            super().__init__(outputs_by_cap)
            self._mm = mm
            self.held_at_dispatch: list = []

        def dispatch(self, capacity_iri, inputs, **kw):
            # RWLock is not reentrant; if the executor held the write lock
            # across the dispatch, this would be True (and a re-acquire would
            # deadlock). Assert it is free.
            self.held_at_dispatch.append(self._mm.lock._writer_active)
            return super().dispatch(capacity_iri, inputs, **kw)

    pipe, _ = _two_step()
    disp = _LockProbe(
        {
            "capacity:derivation:one": {"datastate:b": "B"},
            "capacity:derivation:two": {"datastate:c": "C"},
        },
        mm,
    )
    execute_pipeline(disp, pipe, {"datastate:a": "A"}, task_id="t1", mm=mm)
    assert disp.held_at_dispatch == [False, False]
    # And the lock is free after the run.
    assert mm.lock._writer_active is False
