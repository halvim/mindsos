"""composition-lifecycle — ConjunctionFinder structural conformance.

Validates the sound multi-input finder (ADR-0071 §amendment-2, part 2)
against the three input-group shapes ARC documented (PB-A: *structural*
conformance — the finder produces the DAG shape; ARC composes via an L4
sweep and never executes these DAGs):

* ``all_required`` — AND over inputs (ARC: ``touching_delta`` / ``selector``)
* ``any_of``       — optional-union   (ARC: ``build_correspondence``)
* ``fold``         — aggregate over N producers (ARC: ``reconcile_background``)

Plus the OR-over-producers selection, diamond convergence (shared
upstream fires once), and the not-found path.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import ConjunctionFinder, Pipeline, PipelineNotFoundError

from tests.composition_lifecycle._fixtures import (
    IRI,
    cap,
    incoming_datastates,
    layer,
    step_index,
)

from mindsos_capacity import (
    INPUT_GROUP_ALL_REQUIRED,
    INPUT_GROUP_ANY_OF,
    INPUT_GROUP_FOLD,
)


def test_all_required_ands_over_inputs():
    """A consumer of (a, b) wires BOTH inputs — the unsoundness BFS had."""
    cl = layer("a", "b", "out")
    cl.register_capacity(cap("mk_a", (), ("a",)))
    cl.register_capacity(cap("mk_b", (), ("b",)))
    cl.register_capacity(cap("combine", ("a", "b"), ("out",), INPUT_GROUP_ALL_REQUIRED))

    dag = ConjunctionFinder().find(cl, start_datastates=(), target_datastate=IRI("out"))

    assert isinstance(dag, Pipeline)
    ci = step_index(dag, "combine")
    assert incoming_datastates(dag, ci) == ["a", "b"]
    # both producers present, combine after them (topological order)
    names = [s.capacity_iri.split(":")[-1] for s in dag.steps]
    assert set(names) == {"mk_a", "mk_b", "combine"}
    assert names.index("combine") == 2


def test_all_required_missing_input_raises():
    """If a required input has no producer, the whole compose fails."""
    cl = layer("a", "b", "out")
    cl.register_capacity(cap("mk_a", (), ("a",)))  # no producer for b
    cl.register_capacity(cap("combine", ("a", "b"), ("out",), INPUT_GROUP_ALL_REQUIRED))

    with pytest.raises(PipelineNotFoundError):
        ConjunctionFinder().find(cl, start_datastates=(), target_datastate=IRI("out"))


def test_any_of_wires_only_producible_inputs():
    """``any_of`` composes with the producible subset (b unreachable)."""
    cl = layer("a", "b", "out")
    cl.register_capacity(cap("mk_a", (), ("a",)))  # b has no producer
    cl.register_capacity(cap("anyc", ("a", "b"), ("out",), INPUT_GROUP_ANY_OF))

    dag = ConjunctionFinder().find(cl, start_datastates=(), target_datastate=IRI("out"))

    ai = step_index(dag, "anyc")
    assert incoming_datastates(dag, ai) == ["a"]


def test_fold_fans_in_all_producers():
    """``fold`` consumes from EVERY producer of its folded input."""
    cl = layer("d", "out")
    for i in range(3):
        cl.register_capacity(cap(f"gen_{i}", (), ("d",)))
    cl.register_capacity(cap("reduce", ("d",), ("out",), INPUT_GROUP_FOLD))

    dag = ConjunctionFinder().find(cl, start_datastates=(), target_datastate=IRI("out"))

    ri = step_index(dag, "reduce")
    fold_edges = [e for e in dag.edges if e.consumer == ri]
    assert len(fold_edges) == 3
    assert all(e.datastate == IRI("d") for e in fold_edges)
    # three distinct producers
    assert len({e.producer for e in fold_edges}) == 3


def test_start_datastate_is_a_root():
    """An available start datastate satisfies an input without a step."""
    from mindsos_capacity.pipeline import START

    cl = layer("a", "b", "out")
    cl.register_capacity(cap("mk_b", (), ("b",)))
    cl.register_capacity(cap("combine", ("a", "b"), ("out",), INPUT_GROUP_ALL_REQUIRED))

    dag = ConjunctionFinder().find(
        cl, start_datastates=(IRI("a"),), target_datastate=IRI("out")
    )
    ci = step_index(dag, "combine")
    # a comes from START (no producing step), b from mk_b
    a_edge = next(e for e in dag.edges if e.consumer == ci and e.datastate == IRI("a"))
    assert a_edge.producer == START
    assert incoming_datastates(dag, ci) == ["a", "b"]
    assert {s.capacity_iri.split(":")[-1] for s in dag.steps} == {"mk_b", "combine"}


def test_diamond_shared_upstream_fires_once():
    """A producer shared by two consumers appears as a single step."""
    cl = layer("root", "a", "b", "out")
    cl.register_capacity(cap("mk_root", (), ("root",)))
    cl.register_capacity(cap("to_a", ("root",), ("a",)))
    cl.register_capacity(cap("to_b", ("root",), ("b",)))
    cl.register_capacity(cap("combine", ("a", "b"), ("out",), INPUT_GROUP_ALL_REQUIRED))

    dag = ConjunctionFinder().find(cl, start_datastates=(), target_datastate=IRI("out"))

    names = [s.capacity_iri.split(":")[-1] for s in dag.steps]
    assert names.count("mk_root") == 1  # fired once, not once per consumer
    assert set(names) == {"mk_root", "to_a", "to_b", "combine"}


def test_target_already_available_is_empty():
    cl = layer("out")
    dag = ConjunctionFinder().find(
        cl, start_datastates=(IRI("out"),), target_datastate=IRI("out")
    )
    assert dag.steps == ()
    assert dag.edges == ()


def test_no_producer_raises():
    cl = layer("out")
    with pytest.raises(PipelineNotFoundError):
        ConjunctionFinder().find(cl, start_datastates=(), target_datastate=IRI("out"))
