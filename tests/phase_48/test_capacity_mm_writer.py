"""CR#4 Slice 2 / CR: capacity_mm persist Slice A — the capacity-MM writer
grounds pipeline execution into ``capacity_mm`` (ADR-0201) as a **per-run**
grounding DAG: one graph per ``(task_id, pipeline_run_ref)`` holding both
CapacityInstance and DataStateInstance nodes, PRODUCES/CONSUMES **intra-graph**
edges, minted instance IRIs routing to capacity_mm. Slice A reshapes the origin
slice's two shared fixed-role graphs into one graph per run (D-A) and removes the
``run_ref = task_id`` default (replan collision). ``mm=None`` stays value-only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

import pytest

from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.pipeline_execution import execute_pipeline
from mindsos_intelligence.capacity_mm_writer import (
    CapacityMMWriter,
    RUN_GRAPH_ROLE_PREFIX,
    run_graph_role,
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

    def dispatch(self, capacity_iri, inputs, *, cancel_token=None, request_id=None, step_id=None):
        self.calls.append((capacity_iri, dict(inputs)))
        return _Result(success=True, outputs=dict(self._out.get(capacity_iri, {})))


def _mm() -> MentalModel:
    return MentalModel(session_id="s", user_id="u")


def _run_graph(mm: MentalModel, request_id: str, run_ref: str):
    """Find the single per-run instance graph for ``(task_id, run_ref)``."""
    role = run_graph_role(request_id, run_ref)
    for g in mm.capacity_mm.graphs.values():
        if g.role == role:
            return g
    return None


def _all_run_graphs(mm: MentalModel):
    return [
        g for g in mm.capacity_mm.graphs.values()
        if g.role.startswith(RUN_GRAPH_ROLE_PREFIX)
    ]


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
        request_id="t1", mm=mm, pipeline_run_ref="pipelinerun:t1:1",
    )
    assert res.success
    assert res.outputs["datastate:c"] == "C"

    # One per-run graph holds BOTH node-types (D-A).
    graphs = _all_run_graphs(mm)
    assert len(graphs) == 1
    graph = graphs[0]

    ds_nodes = [n for n in graph.nodes.values() if n.type_name == NODE_TYPE_DATASTATE_INSTANCE]
    cap_nodes = [n for n in graph.nodes.values() if n.type_name == NODE_TYPE_CAPACITY_INSTANCE]
    # 3 DataStateInstances (seed a, output b, output c); 2 CapacityInstances.
    assert len(ds_nodes) == 3
    assert len(cap_nodes) == 2

    # Grounding DAG: 2 CONSUMES (a->one, b->two) + 2 PRODUCES (one->b, two->c),
    # now INTRA-graph edges (not intergraph).
    edge_types = sorted(e.type_name for e in graph.edges.values())
    assert edge_types == [EDGE_CONSUMES, EDGE_CONSUMES, EDGE_PRODUCES, EDGE_PRODUCES]
    # And no intergraph edges are created by the per-run writer.
    assert len(mm.capacity_mm.intergraph_edges) == 0


def test_datastate_instance_carries_payload_and_type():
    mm = _mm()
    pipe, disp = _two_step()
    execute_pipeline(
        disp, pipe, {"datastate:a": "A"},
        request_id="t1", mm=mm, pipeline_run_ref="pipelinerun:t1:1",
    )
    graph = _run_graph(mm, "t1", "pipelinerun:t1:1")
    by_type = {
        n.properties[PROP_DATASTATE_INSTANCE_TYPE]: n.value
        for n in graph.nodes.values()
        if n.type_name == NODE_TYPE_DATASTATE_INSTANCE
    }
    assert by_type == {"datastate:a": "A", "datastate:b": "B", "datastate:c": "C"}


def test_minted_instance_iris_route_to_capacity_mm():
    mm = _mm()
    pipe, disp = _two_step()
    execute_pipeline(
        disp, pipe, {"datastate:a": "A"},
        request_id="t1", mm=mm, pipeline_run_ref="pipelinerun:t1:1",
    )
    graph = _run_graph(mm, "t1", "pipelinerun:t1:1")
    for node_id in graph.nodes:
        assert mm.sub_mm_for_iri(node_id) is mm.capacity_mm  # no KeyError, right room


def test_root_mints_grounding_root():
    mm = _mm()
    w = CapacityMMWriter(mm, "t1", "pipelinerun:t1:1")
    root_iri = w.root("datastate:arc.raw_task", {"grid": [[1]]})
    assert root_iri == "datastate:arc.raw_task#t1.root"
    assert w.index["datastate:arc.raw_task"] == root_iri
    assert mm.sub_mm_for_iri(root_iri) is mm.capacity_mm
    # The root lands in this run's graph.
    assert w.graph is not None
    assert root_iri in w.graph.nodes


def test_no_mm_is_value_only_and_leaves_rooms_empty():
    mm = _mm()
    pipe, disp = _two_step()
    res = execute_pipeline(disp, pipe, {"datastate:a": "A"}, request_id="t1")  # no mm
    assert res.success
    assert res.outputs["datastate:c"] == "C"
    # A fresh MM the run never touched stays empty (byte-identical old path).
    assert sum(len(g.nodes) for g in mm.capacity_mm.graphs.values()) == 0


def test_mm_present_without_run_ref_raises():
    """Slice A: the silent ``run_ref = task_id`` default is removed — an MM
    write without an explicit per-run ref is a programmer error, not a
    replan-colliding default."""
    mm = _mm()
    pipe, disp = _two_step()
    with pytest.raises(ValueError):
        execute_pipeline(disp, pipe, {"datastate:a": "A"}, request_id="t1", mm=mm)


def test_replan_second_run_does_not_overwrite_first():
    """Two runs under the SAME task_id with distinct run refs get distinct
    per-run graphs; the first run's nodes are untouched by the second (the
    replan collision the origin slice had)."""
    mm = _mm()

    pipe1, disp1 = _two_step()
    execute_pipeline(
        disp1, pipe1, {"datastate:a": "A"},
        request_id="t1", mm=mm, pipeline_run_ref="pipelinerun:t1:1",
    )
    pipe2, disp2 = _two_step()
    execute_pipeline(
        disp2, pipe2, {"datastate:a": "A2"},
        request_id="t1", mm=mm, pipeline_run_ref="pipelinerun:t1:2",
    )

    g1 = _run_graph(mm, "t1", "pipelinerun:t1:1")
    g2 = _run_graph(mm, "t1", "pipelinerun:t1:2")
    assert g1 is not None and g2 is not None
    assert g1.graph_id != g2.graph_id
    # Two disjoint per-run graphs; node ids are run-scoped so they never collide.
    assert set(g1.nodes).isdisjoint(set(g2.nodes))
    # First run intact: 3 DS instances + 2 cap instances, all run-1 scoped.
    assert len(g1.nodes) == 5
    assert len(g2.nodes) == 5
    assert all("t1-1" in nid for nid in g1.nodes)
    assert all("t1-2" in nid for nid in g2.nodes)


def test_distinct_tasks_get_distinct_graphs():
    """A submind resolver and a main-task solve writing the same MM land in
    disjoint per-run graphs (isolation, ADR-0201 composite scope)."""
    mm = _mm()
    pipe_a, disp_a = _two_step()
    execute_pipeline(
        disp_a, pipe_a, {"datastate:a": "A"},
        request_id="main-task", mm=mm, pipeline_run_ref="pipelinerun:main:1",
    )
    pipe_b, disp_b = _two_step()
    execute_pipeline(
        disp_b, pipe_b, {"datastate:a": "A"},
        request_id="submind-resolver-x-0", mm=mm, pipeline_run_ref="pipelinerun:sr:1",
    )
    assert len(_all_run_graphs(mm)) == 2
    ga = _run_graph(mm, "main-task", "pipelinerun:main:1")
    gb = _run_graph(mm, "submind-resolver-x-0", "pipelinerun:sr:1")
    assert ga is not None and gb is not None
    assert ga.graph_id != gb.graph_id


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
    execute_pipeline(
        disp, pipe, {"datastate:a": "A"},
        request_id="t1", mm=mm, pipeline_run_ref="pipelinerun:t1:1",
    )
    assert disp.held_at_dispatch == [False, False]
    # And the lock is free after the run.
    assert mm.lock._writer_active is False
