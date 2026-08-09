"""composition-lifecycle — Finder seam + BFS degenerate-linear DAG.

ADR-0071 §amendment-2 parts 1+4: ``Finder`` is the L3 interface, BFS is
one strategy, the result is a ``Pipeline``. BFS emits a
*degenerate-linear* DAG (PB-F) and wires only the ``via`` input.

**CORE-C3R1 changed what that means.** Wiring one input is still true of the
steps BFS emits, but it no longer *emits* a step it cannot run: a capacity
whose other declared inputs are not already on the path is refused, and the
answer is an honest no-route rather than a pipeline that raises at dispatch
(defect D-A). The rule is `mindsos_capacity.admission.unavailable_inputs`
and its own tests are in `test_step_admission.py`.
"""

from __future__ import annotations

from mindsos_capacity import (
    BFSFinder,
    ConjunctionFinder,
    Finder,
    Pipeline,
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
    dag = find_pipeline(cl, start_datastate=IRI("in"), target_datastate=IRI("out")).pipeline
    assert isinstance(dag, Pipeline)
    assert [s.capacity_iri.split(":")[-1] for s in dag.steps] == ["s1", "s2"]


def test_bfs_emits_degenerate_linear_edges():
    cl = layer("in", "mid", "out")
    cl.register_capacity(cap("s1", ("in",), ("mid",)))
    cl.register_capacity(cap("s2", ("mid",), ("out",)))
    dag = BFSFinder().find(
        cl, start_datastates=(IRI("in"),), target_datastate=IRI("out")
    ).pipeline
    # one edge per step, chained: START->0 (in), 0->1 (mid)
    assert [(e.producer, e.consumer, e.datastate.split(".")[-1]) for e in dag.edges] == [
        (START, 0, "in"),
        (0, 1, "mid"),
    ]


def test_bfs_refuses_a_multi_input_capacity_it_cannot_wire():
    """What this test used to pin **is** defect D-A, and it is now closed.

    Before CORE-C3R1 this asserted that BFS fired ``two_in`` off the one
    ``via`` datastate and left ``side`` unwired — a route that composed,
    reported success, and raised ``InputContractError(missing_required)`` one
    dispatch later. arc1 measured twelve capacities in that class. The walk
    now refuses the capacity and answers no-route.

    The assertion is inverted rather than deleted: the old expectation is the
    defect, and a later reader should be able to see that it was chosen away.
    """
    cl = layer("in", "side", "out")
    cl.register_capacity(cap("two_in", ("in", "side"), ("out",)))
    verdict = BFSFinder().find(
        cl, start_datastates=(IRI("in"),), target_datastate=IRI("out")
    )
    assert not verdict.found
    assert verdict.pipeline is None


def test_bfs_still_wires_only_the_via_input_where_it_admits():
    """The degenerate-linear shape (PB-F) is unchanged wherever BFS admits.

    With ``side`` produced on the path, ``two_in`` is admitted; the step
    records both declared inputs and BFS still draws an edge for the ``via``
    input only. That edge incompleteness is inert today — ``execute_pipeline``
    reads the blackboard, not ``DAGEdge`` — and is flagged for whichever item
    builds the pipeline store, which reads edges as the composition links.
    """
    cl = layer("in", "side", "out")
    cl.register_capacity(cap("mk_side", ("in",), ("side",)))
    cl.register_capacity(cap("two_in", ("in", "side"), ("out",)))
    dag = BFSFinder().find(
        cl, start_datastates=(IRI("in"),), target_datastate=IRI("out")
    ).pipeline
    ti = step_index(dag, "two_in")
    assert set(dag.steps[ti].input_datastates) == {IRI("in"), IRI("side")}
    wired = [e.datastate for e in dag.edges if e.consumer == ti]
    assert wired == [IRI("side")]
