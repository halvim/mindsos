"""Two-tier Local-over-Global composition through the union finder view.

The defect this closes: ``pipeline._view_for`` returned the Global view OR
the user's Local view and never both, so a capacity a user registered
Locally could not compose with a pre-installed Global one. Teaching the
system one step cost you the entire shared catalog for that find.

The rule is **shadow**: a Local capacity at a colliding IRI hides the
Global capacity of that IRI entirely, node and PRODUCES/CONSUMES edges
together. It does not merge with it, and the finder's OR-over-producers
pick cannot reach back to the shadowed Global one.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    CATEGORY_PERCEPTION,
    Capacity,
    DataState,
    ShapeDescriptor,
    find_pipeline,
)
from mindsos_capacity.admission import declaration_refusals
from mindsos_capacity.views import LocalPreferringView

from tests.phase_30._fixtures import (
    DS_INPUT_IRI,
    DS_MID_IRI,
    DS_OUTPUT_IRI,
    build_linear_pipeline_layer,
    build_session,
    build_step1_capacity,
    build_step2_capacity,
)


def _mirror_datastates_local(cl, sess, *short_names: str) -> None:
    """Register the test DataStates into the session's Local realm.

    ``register_capacity`` needs its referenced DataStates present in the
    metagraph it writes to, so a Local capacity needs Local DataState nodes.
    """
    for short in short_names:
        full = f"test.{short}"
        cl.register_datastate(
            DataState(
                name=full, shape=ShapeDescriptor.scalar("str", opaque_tag=full)
            ),
            session=sess,
            allow_new_realm=True,
        )


def _local_step2_override():
    """Same name + category as the Global ``test.step2``, so the same IRI."""
    return Capacity(
        name="test.step2",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_MID_IRI,),
        outputs=(DS_OUTPUT_IRI,),
        implementation=lambda **kw: {DS_OUTPUT_IRI: kw[DS_MID_IRI] + "_LOCAL"},
    )


# ── the feature ────────────────────────────────────────────────────────


def test_local_override_composes_inside_an_otherwise_global_pipeline():
    """Global step1 → Local step2. Neither view alone can build this."""
    cl = build_linear_pipeline_layer()  # Global: step1, step2
    sess = build_session("alice")
    _mirror_datastates_local(cl, sess, "input", "mid", "output")

    override = _local_step2_override()
    cl.register_capacity(override, session=sess)

    verdict = find_pipeline(
        cl,
        session=sess,
        start_datastate=DS_INPUT_IRI,
        target_datastate=DS_OUTPUT_IRI,
    )

    assert verdict.found
    pipeline = verdict.pipeline
    assert len(pipeline) == 2
    assert pipeline.steps[0].capacity_iri == build_step1_capacity().iri
    assert pipeline.steps[1].capacity_iri == override.iri

    # Step 2's IRI is shared between the two realms, so identity has to be
    # asserted on the resolved declaration, not the IRI.
    resolved = cl.resolve_declaration(override.iri, session=sess)
    assert resolved.implementation is override.implementation


def test_the_shadowed_global_capacity_is_not_selectable():
    """A Local override at a colliding IRI hides the Global node AND edges."""
    cl = build_linear_pipeline_layer()
    sess = build_session("alice")
    _mirror_datastates_local(cl, sess, "input", "mid", "output")

    # Global test.step2 goes mid → output. This Local one at the SAME IRI
    # goes input → output, so if the Global edges were still visible the
    # union would offer BOTH a 1-step and a 2-step route.
    shadowing = Capacity(
        name="test.step2",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_INPUT_IRI,),
        outputs=(DS_OUTPUT_IRI,),
        implementation=lambda **kw: {DS_OUTPUT_IRI: kw[DS_INPUT_IRI]},
    )
    cl.register_capacity(shadowing, session=sess)

    view = LocalPreferringView(cl.global_view(), cl.local_view("alice"))

    # The Global step2's mid → output CONSUMES edge is gone with its node.
    assert [c.node_id for c in view.consumers_of(DS_MID_IRI)] == []
    assert view.inputs_of(shadowing.iri) == [DS_INPUT_IRI]

    verdict = find_pipeline(
        cl,
        session=sess,
        start_datastate=DS_INPUT_IRI,
        target_datastate=DS_OUTPUT_IRI,
    )
    assert verdict.found
    assert len(verdict.pipeline) == 1
    assert verdict.pipeline.steps[0].capacity_iri == shadowing.iri


def test_union_view_survives_declaration_refusals():
    """Regression: step admission calls iter_capacities + get_datastate.

    This is the call that made the first attempt at this view raise
    ``AttributeError`` on every session-scoped find. Asserted directly
    rather than only through ``find_pipeline`` so the failure names the
    real caller.
    """
    cl = build_linear_pipeline_layer()
    sess = build_session("alice")
    _mirror_datastates_local(cl, sess, "input", "mid", "output")
    cl.register_capacity(_local_step2_override(), session=sess)

    view = LocalPreferringView(cl.global_view(), cl.local_view("alice"))

    refusals = declaration_refusals(cl, view, session=sess)
    assert refusals == {}

    # The union must expose both realms' capacities exactly once each.
    iris = [n.node_id for n in view.iter_capacities()]
    assert len(iris) == len(set(iris))
    assert set(iris) == {build_step1_capacity().iri, build_step2_capacity().iri}


# ── the boundaries ─────────────────────────────────────────────────────


def test_sessionless_find_never_sees_local_capacities():
    """``session=None`` is the shared catalog and must stay Global-only."""
    cl = build_linear_pipeline_layer()
    sess = build_session("alice")
    _mirror_datastates_local(cl, sess, "input", "mid", "output")
    override = _local_step2_override()
    cl.register_capacity(override, session=sess)

    verdict = find_pipeline(
        cl,
        start_datastate=DS_INPUT_IRI,
        target_datastate=DS_OUTPUT_IRI,
    )

    assert verdict.found
    assert len(verdict.pipeline) == 2
    resolved = cl.resolve_declaration(override.iri, session=None)
    assert resolved.implementation is not override.implementation


def test_a_find_for_a_user_with_no_local_does_not_mint_one():
    """``_view_for`` guards on ``has_local``; ``local_view`` would create."""
    cl = build_linear_pipeline_layer()
    sess = build_session("bob")

    assert not cl.has_local("bob")

    verdict = find_pipeline(
        cl,
        session=sess,
        start_datastate=DS_INPUT_IRI,
        target_datastate=DS_OUTPUT_IRI,
    )

    assert verdict.found
    assert len(verdict.pipeline) == 2
    assert not cl.has_local("bob"), (
        "composing a pipeline lazily created an empty Local metagraph — a "
        "read must not create state (ADR-0183 §am-6)"
    )


# ── the override is authoritative even when it is broken (ADR-0071 §am-5) ──


class _FakeDispatcher:
    """``_compose_pipeline`` reads exactly two attributes off a dispatcher."""

    def __init__(self, capacity_layer, session) -> None:
        self.capacity_layer = capacity_layer
        self.session = session


def _refused_step2_override():
    """Same IRI as Global ``test.step2``, but unroutable by step admission.

    ``operand_arity`` of 2 on a SCALAR input can never be fed by route-finding
    — a producer supplies one value — so ``declaration_refusals`` refuses it.
    """
    return Capacity(
        name="test.step2",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_MID_IRI,),
        outputs=(DS_OUTPUT_IRI,),
        operand_arity={DS_MID_IRI: 2},
        implementation=lambda **kw: {DS_OUTPUT_IRI: kw[DS_MID_IRI]},
    )


def _layer_with_refused_override():
    cl = build_linear_pipeline_layer()  # Global: step1 in→mid, step2 mid→out
    sess = build_session("alice")
    _mirror_datastates_local(cl, sess, "input", "mid", "output")
    cl.register_capacity(_refused_step2_override(), session=sess)
    return cl, sess


def test_a_refused_local_override_is_not_papered_over_by_global():
    """The union reports no route rather than quietly using the Global step2."""
    cl, sess = _layer_with_refused_override()

    view = LocalPreferringView(cl.global_view(), cl.local_view("alice"))
    refusals = declaration_refusals(cl, view, session=sess)
    assert any(k.endswith("step2") for k in refusals)

    verdict = find_pipeline(
        cl,
        session=sess,
        start_datastate=DS_INPUT_IRI,
        target_datastate=DS_OUTPUT_IRI,
    )
    assert not verdict.found

    # ...while the Global catalog on its own still routes. That gap is exactly
    # what the retired second find() used to paper over.
    sessionless = find_pipeline(
        cl, start_datastate=DS_INPUT_IRI, target_datastate=DS_OUTPUT_IRI
    )
    assert sessionless.found


def test_compose_pipeline_raises_instead_of_retrying_global():
    """CORE-C3R1 D5's Local-then-Global retry is gone (ADR-0071 §am-5)."""
    from mindsos_intelligence.execution import (
        LeafPipelineNotFound,
        _compose_pipeline,
    )

    cl, sess = _layer_with_refused_override()
    dispatcher = _FakeDispatcher(cl, sess)

    with pytest.raises(LeafPipelineNotFound) as exc:
        _compose_pipeline(dispatcher, (DS_INPUT_IRI,), DS_OUTPUT_IRI, "bfs")

    # One verdict, not two — the old signature took (local, global_, ...).
    assert exc.value.verdict is not None
    assert not exc.value.verdict.found
    assert not hasattr(exc.value, "global_")
