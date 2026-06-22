"""composition-lifecycle — Finder seam + BFS degenerate-linear DAG.

ADR-0071 §amendment-2 parts 1+4: ``Finder`` is the L3 interface, BFS is
one strategy, the result is a ``PipelineDAG``. BFS emits a
*degenerate-linear* DAG (PB-F) and retains its single-input semantics
(only the ``via`` input is wired).
"""

from __future__ import annotations

from mindsos_capacity import (
    BFSFinder,
    ConjunctionFinder,
    Finder,
    PipelineDAG,
    find_pipeline,
)
from mindsos_capacity.pipeline import START

from tests.composition_lifecycle._fixtures import IRI, cap, layer, step_index


def test_strategies_are_finders():
    assert issubclass(BFSFinder, Finder)
    assert issubclass(ConjunctionFinder, Finder)


def test_find_pipeline_returns_pipeline_dag():
    cl = layer("in", "mid", "out")
    cl.register_capacity(cap("s1", ("in",), ("mid",)))
    cl.register_capacity(cap("s2", ("mid",), ("out",)))
    dag = find_pipeline(cl, start_datastate=IRI("in"), target_datastate=IRI("out"))
    assert isinstance(dag, PipelineDAG)
    assert [s.capacity_iri.split(":")[-1] for s in dag.steps] == ["s1", "s2"]


def test_bfs_emits_degenerate_linear_edges():
    cl = layer("in", "mid", "out")
    cl.register_capacity(cap("s1", ("in",), ("mid",)))
    cl.register_capacity(cap("s2", ("mid",), ("out",)))
    dag = BFSFinder().find(
        cl, start_datastates=(IRI("in"),), target_datastate=IRI("out")
    )
    # one edge per step, chained: START->0 (in), 0->1 (mid)
    assert [(e.producer, e.consumer, e.datastate.split(".")[-1]) for e in dag.edges] == [
        (START, 0, "in"),
        (0, 1, "mid"),
    ]


def test_bfs_only_wires_via_input_not_other_declared_inputs():
    """BFS retains its single-input behaviour: a multi-input capacity is
    fired off the one ``via`` datastate; its other declared inputs are
    recorded on the step but NOT wired. (ConjunctionFinder is the sound
    path — see test_conjunction_finder.)"""
    cl = layer("in", "side", "out")
    cl.register_capacity(cap("two_in", ("in", "side"), ("out",)))
    dag = BFSFinder().find(
        cl, start_datastates=(IRI("in"),), target_datastate=IRI("out")
    )
    ti = step_index(dag, "two_in")
    # full declared inputs recorded on the step…
    assert set(dag.steps[ti].input_datastates) == {IRI("in"), IRI("side")}
    # …but only the `via` input ("in") is wired as an edge.
    wired = [e.datastate for e in dag.edges if e.consumer == ti]
    assert wired == [IRI("in")]
