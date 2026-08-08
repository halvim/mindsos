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

from mindsos_capacity import CapacityLayer

from tests.composition_lifecycle._fixtures import (
    IRI,
    cap,
    ds,
    incoming_datastates,
    layer,
)


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


# ── operand_arity — the shared declaration predicate ──────────────────────
#
# A capacity emits ONE value per output DataState, so a consumer declaring
# operand_arity[k] = N > 1 on a SCALAR input can never be fed by route-finding:
# whatever producer the walk picks supplies one value, _validate_inputs wants a
# length-N list, and the route composes and then raises
# InputContractError(kind="operand_arity"). arc3 measured 14 of 27 capacities in
# that class, arc1 16 of 45, on BOTH finders.
#
# The predicate is NOT "declares operand_arity". ADR-0205's shape-2 ruling keeps
# operand_arity on the input after the collection migration, where it means
# "this collection must carry N members" — a producer of a collection CAN
# satisfy that, and whether it does is a run-time property of the value. So the
# finder must hold no opinion there, or the rule would delete the migration's
# own target.

from mindsos_capacity import (
    CATEGORY_PERCEPTION,
    Capacity,
    DataState,
    ShapeDescriptor,
)
from mindsos_capacity.admission import arity_unroutable_inputs, declaration_refusals
from mindsos_capacity.exceptions import CapacityRegistrationError


def _collection_ds(short: str, member_short: str) -> DataState:
    full = f"t.{short}"
    return DataState(
        name=full,
        shape=ShapeDescriptor.scalar("str", opaque_tag=full),
        collection=True,
        member_ds=IRI(member_short),
    )


def _arity_cap(name, inputs, outputs, operand_arity):
    return Capacity(
        name=name,
        category=CATEGORY_PERCEPTION,
        inputs=tuple(IRI(i) for i in inputs),
        outputs=tuple(IRI(o) for o in outputs),
        operand_arity={IRI(k): v for k, v in operand_arity.items()},
        implementation=lambda **kw: {},
    )


# the rule itself

def test_arity_over_one_on_a_scalar_is_unroutable():
    assert arity_unroutable_inputs({"a": 2}, lambda ds: False) == ("a",)


def test_arity_over_one_on_a_collection_is_routable():
    """Shape 2's target. Refusing this would delete the migration's own goal."""
    assert arity_unroutable_inputs({"a": 2}, lambda ds: True) == ()


def test_arity_of_one_is_not_a_constraint():
    """_validate_inputs skips n <= 1, so the finder must not refuse on it."""
    assert arity_unroutable_inputs({"a": 1}, lambda ds: False) == ()


def test_no_arity_declared_is_routable():
    assert arity_unroutable_inputs({}, lambda ds: False) == ()


def test_only_the_scalar_operands_are_named():
    got = arity_unroutable_inputs(
        {"scalar": 2, "coll": 3}, lambda ds: ds == "coll"
    )
    assert got == ("scalar",)


# over a real catalog

def _form_b_catalog():
    """``pair_up(a) -> pair``; ``compare`` needs TWO of ``pair`` -> ``out``."""
    cl = layer("a", "pair", "out")
    cl.register_capacity(cap("pair_up", ("a",), ("pair",)))
    cl.register_capacity(_arity_cap("compare", ("pair",), ("out",), {"pair": 2}))
    return cl


def test_declaration_refusals_names_the_capacity_and_its_operand():
    cl = _form_b_catalog()
    refusals = declaration_refusals(cl, cl.global_view())
    key = next(k for k in refusals if k.endswith("compare"))
    assert refusals[key] == (IRI("pair"),)


def test_bfs_refuses_a_form_b_consumer():
    verdict = BFSFinder().find(
        _form_b_catalog(), start_datastates=(IRI("a"),), target_datastate=IRI("out")
    )
    assert not verdict.found


def test_conjunction_refuses_a_form_b_consumer_too():
    """The declaration half is SHARED — unlike path-availability."""
    verdict = ConjunctionFinder().find(
        _form_b_catalog(), start_datastates=(IRI("a"),), target_datastate=IRI("out")
    )
    assert not verdict.found


def test_a_form_b_consumer_does_not_make_its_output_look_reachable():
    """Refusal sits in cap_satisfiable, so phase 1 sees it too.

    If it sat only in ``eligible``, phase 1 would still report ``out`` as
    reachable and the verdict would name the wrong reason.
    """
    cl = _form_b_catalog()
    cl.register_datastate(ds("far"), allow_new_realm=True)
    cl.register_capacity(cap("out_to_far", ("out",), ("far",)))
    verdict = ConjunctionFinder().find(
        cl, start_datastates=(IRI("a"),), target_datastate=IRI("far")
    )
    assert not verdict.found


def test_a_collection_input_still_routes_after_the_migration():
    """`operand_arity` on a collection input must not be refused by either finder."""
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    for d in (ds("member"), _collection_ds("bag", "member"), ds("a"), ds("out")):
        cl.register_datastate(d, allow_new_realm=True)
    cl.register_capacity(cap("fill_bag", ("a",), ("bag",)))
    cl.register_capacity(_arity_cap("fold_bag", ("bag",), ("out",), {"bag": 2}))

    for finder in (BFSFinder(), ConjunctionFinder()):
        verdict = finder.find(
            cl, start_datastates=(IRI("a"),), target_datastate=IRI("out")
        )
        assert verdict.found, type(finder).__name__


def test_a_graph_only_node_with_no_declaration_is_not_refused():
    """Documented at `pipeline._input_group_of`: a bare reference is real.

    Refusing on a declaration we do not have would invent a constraint, and a
    broad `except` here would let the whole predicate go silently inert.
    """

    class _NoDeclarations:
        def resolve_declaration(self, iri, *, session=None):
            raise CapacityRegistrationError(f"No declaration registered for {iri!r}")

    cl = _form_b_catalog()
    assert declaration_refusals(_NoDeclarations(), cl.global_view()) == {}


def test_refusals_are_computed_once_not_per_candidate():
    """The declaration half must not be recomputed inside a walk.

    Pinned by counting resolutions: a view-wide pass resolves each capacity
    exactly once per find, where a per-candidate check would resolve the same
    capacity repeatedly as the walk revisits it.
    """
    cl = _form_b_catalog()
    calls = []
    real = cl.resolve_declaration

    def counting(iri, *, session=None):
        calls.append(iri)
        return real(iri, session=session)

    cl.resolve_declaration = counting
    declaration_refusals(cl, cl.global_view())
    assert len(calls) == len(set(calls)) == 2
