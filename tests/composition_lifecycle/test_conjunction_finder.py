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


# ── CORE-C3R1 — the two phase-2 cycle guards ─────────────────────────
#
# These assert BEHAVIOUR, not implementation. They are written to survive the
# bottom-up-fixpoint rewrite (confirmation_docs/CORE_CR_FINDER_AS_CAPACITIES.md)
# unchanged, and are that rewrite's acceptance bar. Do not rewrite them to match
# an implementation; if one fails, the implementation is wrong.
#
# Evidence for the numbers quoted in ConjunctionFinder's docstring:
# confirmation_docs/finder_variants_model.py


def _self_feeding_layer():
    """``out`` has one producer; its input ``x`` has a looping producer first.

    ``a_loop`` sorts before ``b_direct`` by IRI, so a phase 2 that discards the
    cycle stack selects ``a_loop`` — which needs ``out``, the thing being
    produced — and recurses to ``max_depth``. Phase 1 has already proved the
    route through ``b_direct`` exists, so the two phases disagree.
    """
    cl = layer("seed", "x", "out")
    cl.register_capacity(cap("make_out", ("x",), ("out",)))
    cl.register_capacity(cap("a_loop", ("out",), ("x",)))
    cl.register_capacity(cap("b_direct", ("seed",), ("x",)))
    return cl


def test_self_feeding_producer_is_refused():
    """D-B — phase 2 must honour phase 1's cycle guard.

    Pre-fix this raised ``max_depth=8 exceeded resolving 'a_loop'`` on a graph
    where phase 1 had already found a route.
    """
    dag = ConjunctionFinder().find(
        _self_feeding_layer(),
        start_datastates=(IRI("seed"),),
        target_datastate=IRI("out"),
    )

    names = [s.capacity_iri.split(":")[-1] for s in dag.steps]
    assert set(names) == {"b_direct", "make_out"}
    assert "a_loop" not in names
    assert incoming_datastates(dag, step_index(dag, "make_out")) == ["x"]


def test_composition_is_monotonic_in_the_start_set():
    """Widening the start set must never turn a success into a failure.

    With no starts the graph is honestly unsatisfiable. Adding ``seed`` opens a
    real route — and pre-fix that is exactly what moved the walk onto the
    defective path, so the *wider* start set failed while the narrower one gave
    a clean verdict.
    """
    with pytest.raises(PipelineNotFoundError):
        ConjunctionFinder().find(
            _self_feeding_layer(), start_datastates=(), target_datastate=IRI("out")
        )

    widened = ConjunctionFinder().find(
        _self_feeding_layer(),
        start_datastates=(IRI("seed"),),
        target_datastate=IRI("out"),
    )
    assert widened.steps  # the wider start set composes


def test_capacity_under_construction_is_not_selected():
    """D-E — a capacity mid-``fire`` must be refused as a producer.

    ``mk_out`` is being built when resolving ``mid`` leads back to ``out``. The
    ``fired`` memo is written only *after* construction, so ``mk_out`` is in
    neither ``fired`` nor the DataState stack, and a stack-only fix still admits
    it — returning a Pipeline whose steps are ``[mk_out, mk_mid, mk_out]``, with
    no error. ``execute_pipeline`` would then run ``mk_out`` twice and overwrite
    its own output, since the blackboard holds one value per DataState IRI.
    """
    cl = layer("seed", "gone", "mid", "out")
    cl.register_capacity(
        cap("mk_out", ("seed", "mid"), ("out",), INPUT_GROUP_ANY_OF)
    )
    cl.register_capacity(
        cap("mk_mid", ("gone", "out"), ("mid",), INPUT_GROUP_ANY_OF)
    )

    dag = ConjunctionFinder().find(
        cl, start_datastates=(IRI("seed"),), target_datastate=IRI("out")
    )

    iris = [s.capacity_iri for s in dag.steps]
    names = [i.split(":")[-1] for i in iris]
    # The invariant, not the shape: no capacity may appear as two steps.
    # (Deliberately NOT asserting the exact step list. The bottom-up-fixpoint
    # rewrite drops `mk_mid` entirely -- `out` is producible from `seed` alone,
    # and a stratum filter refuses a producer that only becomes satisfiable
    # after the DataState it would produce. That is a different, also-correct
    # DAG, and this test must not fail on it.)
    assert len(iris) == len(set(iris)), f"capacity duplicated in steps: {names}"
    assert names.count("mk_out") == 1
    assert dag.target_datastate == IRI("out")


def test_shared_upstream_is_one_step_not_two():
    """The memo's convergence claim, asserted rather than documented.

    ``ConjunctionFinder``'s docstring claims shared upstream producers fire
    once. D-E falsified that claim in the general case; this pins it for the
    diamond, which is the shape the claim was written about.
    """
    cl = layer("root", "a", "b", "out")
    cl.register_capacity(cap("mk_root", (), ("root",)))
    cl.register_capacity(cap("to_a", ("root",), ("a",)))
    cl.register_capacity(cap("to_b", ("root",), ("b",)))
    cl.register_capacity(
        cap("combine", ("a", "b"), ("out",), INPUT_GROUP_ALL_REQUIRED)
    )

    dag = ConjunctionFinder().find(cl, start_datastates=(), target_datastate=IRI("out"))

    iris = [s.capacity_iri for s in dag.steps]
    assert len(iris) == len(set(iris))
    ri = step_index(dag, "mk_root")
    # both consumers wire to the SAME step index for the shared upstream
    assert {e.producer for e in dag.edges if e.datastate == IRI("root")} == {ri}
