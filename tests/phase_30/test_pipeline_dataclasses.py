"""Phase 30 / composition-lifecycle — PipelineDAG result-type shape.

The linear ``Pipeline``/``PipelineStep`` were retired by ADR-0071
§amendment-2 (they cannot represent a converging DAG) and replaced by
``PipelineDAG`` + ``DAGStep`` + ``DAGEdge``. This locks the new frozen
shapes, the ``len``/iter convenience over ``steps``, and the
``to_dict``/``from_dict`` round-trip used by the composite-persistence
residual.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import START, DAGEdge, DAGStep, PipelineDAG


def test_dag_step_frozen_dataclass():
    step = DAGStep(
        capacity_iri="capacity:perception:test.echo",
        input_datastates=("datastate:test.input",),
        output_datastates=("datastate:test.output",),
    )
    assert step.capacity_iri == "capacity:perception:test.echo"
    assert step.input_datastates == ("datastate:test.input",)
    assert step.output_datastates == ("datastate:test.output",)

    with pytest.raises(Exception):  # FrozenInstanceError; type varies across releases
        step.capacity_iri = "other"  # type: ignore[misc]


def test_dag_edge_start_sentinel():
    edge = DAGEdge(producer=START, consumer=0, datastate="datastate:test.input")
    assert edge.producer == START == -1
    assert edge.consumer == 0
    assert edge.datastate == "datastate:test.input"


def test_pipeline_dag_empty_steps():
    dag = PipelineDAG(
        start_datastates=("datastate:a",),
        target_datastate="datastate:a",
        steps=(),
    )
    assert len(dag) == 0
    assert list(dag) == []
    assert dag.edges == ()


def test_pipeline_dag_len_and_iter():
    s1 = DAGStep("cap:a", ("ds:in",), ("ds:mid",))
    s2 = DAGStep("cap:b", ("ds:mid",), ("ds:out",))
    dag = PipelineDAG(
        start_datastates=("ds:in",),
        target_datastate="ds:out",
        steps=(s1, s2),
        edges=(
            DAGEdge(START, 0, "ds:in"),
            DAGEdge(0, 1, "ds:mid"),
        ),
    )
    assert len(dag) == 2
    assert list(dag) == [s1, s2]


def test_pipeline_dag_dict_roundtrip():
    dag = PipelineDAG(
        start_datastates=("ds:in", "ds:other"),
        target_datastate="ds:out",
        steps=(
            DAGStep("cap:a", ("ds:in",), ("ds:mid",)),
            DAGStep("cap:b", ("ds:mid", "ds:other"), ("ds:out",)),
        ),
        edges=(
            DAGEdge(START, 0, "ds:in"),
            DAGEdge(0, 1, "ds:mid"),
            DAGEdge(START, 1, "ds:other"),
        ),
    )
    restored = PipelineDAG.from_dict(dag.to_dict())
    assert restored == dag
