"""composition-lifecycle — composite-persistence residual (L3 half).

The DAG serializes into a ``learned-parameters`` descriptor
(``composite_dag`` key, ADR-0182 codec) and the in-batch dependency
extraction (:func:`composite_dependencies`) the server uses to dep-order
re-activation. (The ``kahn_sort`` ordering itself lives in
``mindsos_server.local_boot`` — see ``test_dep_ordered_reactivation`` —
because ``mindsos_capacity`` may not import ``mindsos_knowledge``.)
"""

from __future__ import annotations

from mindsos_capacity import (
    COMPOSITE_DAG,
    DAGEdge,
    DAGStep,
    PipelineDAG,
    composite_dependencies,
)
from mindsos_capacity.pipeline import START


def _composite_dag() -> PipelineDAG:
    return PipelineDAG(
        start_datastates=("datastate:t.in",),
        target_datastate="datastate:t.out",
        steps=(
            DAGStep("capacity:perception:leaf_a", ("datastate:t.in",), ("datastate:t.mid",)),
            DAGStep("capacity:perception:leaf_b", ("datastate:t.mid",), ("datastate:t.out",)),
        ),
        edges=(
            DAGEdge(START, 0, "datastate:t.in"),
            DAGEdge(0, 1, "datastate:t.mid"),
        ),
    )


def test_dag_dict_roundtrip_is_codec_safe():
    dag = _composite_dag()
    d = dag.to_dict()
    # ADR-0182 codec carries lists + primitives only.
    assert isinstance(d["steps"], list) and isinstance(d["edges"], list)
    assert isinstance(d["start_datastates"], list)
    assert PipelineDAG.from_dict(d) == dag


def test_composite_dependencies_reads_step_iris():
    descriptor = {COMPOSITE_DAG: _composite_dag().to_dict()}
    assert composite_dependencies(descriptor) == {
        "capacity:perception:leaf_a",
        "capacity:perception:leaf_b",
    }


def test_composite_dependencies_empty_for_non_composite():
    assert composite_dependencies({"capability": "x", "steps": []}) == set()
    assert composite_dependencies({COMPOSITE_DAG: "not-a-dict"}) == set()
