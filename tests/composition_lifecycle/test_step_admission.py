"""CORE-C3R1 — step admission, and the ``already_held`` verdict shape.

**D-A, the half a finder can close.** ``BFSFinder`` fires each capacity off the
one ``via`` DataState it arrived on and wires only that input, while
``DAGStep.input_datastates`` still lists every declared input. Nothing between
the finder and the executor can see the gap: ``execute_pipeline`` builds
``{ds: blackboard[ds] for ds in step.input_datastates if ds in blackboard}``
and never consults ``DAGEdge``, so the missing operand surfaces as
``InputContractError(kind="missing_required")`` at dispatch. arc1 measured
twelve capacities in that class on its own catalog and executed three.

**Why availability and not reachability.** The rule was first stated as *are
the other declared inputs reachable from the starts*. :func:`
test_reachable_but_not_on_this_path_is_still_refused` is the case that
separates the two: the missing input has a producer, so it is reachable, but
it was never produced on the branch the walk is on — and a route admitted on
reachability composes and dies at dispatch exactly as before.

**What must not change.** ``ConjunctionFinder`` answers the same case by
*wiring* the missing input as another step, so the rule is ``BFSFinder``-local;
:func:`test_conjunction_still_wires_what_bfs_now_refuses` pins that, because
applying it to both finders would delete routes Conjunction correctly builds.
"""

from __future__ import annotations

from mindsos_capacity import BFSFinder, ConjunctionFinder, Pipeline
from mindsos_capacity.admission import unavailable_inputs
from mindsos_capacity.pipeline import find_pipeline

from tests.composition_lifecycle._fixtures import IRI, cap, incoming_datastates, layer


# ── the rule itself, callable without a finder ────────────────────────────


def test_single_input_is_never_refused():
    """The walk arrives on that input, so it is available by construction."""
    assert unavailable_inputs(("a",), {"a"}) == ()


def test_missing_operand_is_named_in_declaration_order():
    assert unavailable_inputs(("z", "a", "m"), {"a"}) == ("z", "m")


def test_all_operands_present_admits():
    assert unavailable_inputs(("a", "b"), {"a", "b"}) == ()


def test_empty_declaration_admits():
    assert unavailable_inputs((), set()) == ()


# ── BFSFinder behaviour ───────────────────────────────────────────────────


def _two_input_catalog():
    """``combine(a, b) -> out``; ``b`` is produced from an unrelated start."""
    cl = layer("a", "b", "seed", "out")
    cl.register_capacity(cap("mk_b", ("seed",), ("b",)))
    cl.register_capacity(cap("combine", ("a", "b"), ("out",)))
    return cl


def test_bfs_refuses_a_capacity_whose_other_input_is_not_on_the_path():
    """Starting at ``a`` alone, ``combine`` would dispatch without ``b``."""
    verdict = BFSFinder().find(
        _two_input_catalog(), start_datastates=(IRI("a"),), target_datastate=IRI("out")
    )
    assert not verdict.found
    assert verdict.pipeline is None


def test_reachable_but_not_on_this_path_is_still_refused():
    """The case that distinguishes availability from reachability.

    ``b`` has a producer, so it is reachable from the catalog. It is not on
    the walk's path from ``a``, and a route admitted on reachability alone
    would compose and then raise at dispatch.
    """
    cl = _two_input_catalog()
    reachable = ConjunctionFinder().find(
        cl, start_datastates=(IRI("a"), IRI("seed")), target_datastate=IRI("out")
    )
    assert reachable.found, "b IS producible — the catalog is not the problem"

    verdict = BFSFinder().find(
        cl, start_datastates=(IRI("a"),), target_datastate=IRI("out")
    )
    assert not verdict.found


def test_bfs_admits_when_every_operand_is_on_the_path():
    """``mk_b`` runs first, so ``b`` is on the blackboard for ``combine``."""
    cl = layer("a", "b", "out")
    cl.register_capacity(cap("mk_b", ("a",), ("b",)))
    cl.register_capacity(cap("combine", ("a", "b"), ("out",)))

    verdict = BFSFinder().find(
        cl, start_datastates=(IRI("a"),), target_datastate=IRI("out")
    )
    assert verdict.found
    names = [s.capacity_iri.split(":")[-1] for s in verdict.pipeline.steps]
    assert names == ["mk_b", "combine"]


def test_single_input_chains_are_untouched():
    """The rule must not narrow the shape every shipped consumer uses."""
    cl = layer("a", "b", "out")
    cl.register_capacity(cap("a_to_b", ("a",), ("b",)))
    cl.register_capacity(cap("b_to_out", ("b",), ("out",)))

    verdict = find_pipeline(
        cl, start_datastate=IRI("a"), target_datastate=IRI("out")
    )
    assert verdict.found
    assert len(verdict.pipeline.steps) == 2


def test_conjunction_still_wires_what_bfs_now_refuses():
    """The rule is BFS-local. Conjunction fixes this case by construction."""
    cl = _two_input_catalog()
    verdict = ConjunctionFinder().find(
        cl, start_datastates=(IRI("a"), IRI("seed")), target_datastate=IRI("out")
    )
    assert verdict.found
    ci = next(
        i
        for i, s in enumerate(verdict.pipeline.steps)
        if s.capacity_iri.endswith("combine")
    )
    assert incoming_datastates(verdict.pipeline, ci) == ["a", "b"]


def test_refusal_narrows_reachability_deliberately():
    """A route the pre-CORE-C3R1 BFS returned is now a no-route.

    Pinned so the narrowing is a decision on the record rather than a
    regression someone later 'fixes'. What it removes is exactly the set that
    raised InputContractError one dispatch later.
    """
    cl = _two_input_catalog()
    steps_before = [
        c.node_id
        for c in cl.global_view().consumers_of(IRI("a"))
    ]
    assert any(s.endswith("combine") for s in steps_before), (
        "combine IS a consumer of a — the walk reaches it and chooses to refuse"
    )
    assert not BFSFinder().find(
        cl, start_datastates=(IRI("a"),), target_datastate=IRI("out")
    ).found


# ── already_held (coordination §29.2) ─────────────────────────────────────


def test_already_held_when_target_is_a_start():
    cl = layer("a")
    verdict = BFSFinder().find(
        cl, start_datastates=(IRI("a"),), target_datastate=IRI("a")
    )
    assert verdict.found
    assert verdict.already_held
    assert verdict.pipeline.steps == ()


def test_already_held_for_the_conjunction_finder_too():
    cl = layer("a")
    verdict = ConjunctionFinder().find(
        cl, start_datastates=(IRI("a"),), target_datastate=IRI("a")
    )
    assert verdict.found
    assert verdict.already_held


def test_already_held_is_false_for_a_real_route():
    cl = layer("a", "out")
    cl.register_capacity(cap("a_to_out", ("a",), ("out",)))
    verdict = find_pipeline(cl, start_datastate=IRI("a"), target_datastate=IRI("out"))
    assert verdict.found
    assert not verdict.already_held


def test_already_held_is_false_when_not_found():
    """Must not raise on ``pipeline is None`` — the property guards on found."""
    cl = layer("a", "out")
    verdict = find_pipeline(cl, start_datastate=IRI("a"), target_datastate=IRI("out"))
    assert not verdict.found
    assert not verdict.already_held


def test_already_held_is_derived_not_stored():
    """No field to disagree with the steps — ADR-0192's ground, and found's."""
    import dataclasses

    fields = {f.name for f in dataclasses.fields(Pipeline)}
    assert "already_held" not in fields
    from mindsos_capacity.pipeline import FindVerdict

    assert "already_held" not in {f.name for f in dataclasses.fields(FindVerdict)}
    assert isinstance(FindVerdict.already_held, property)
