"""Phase 30 — find_pipeline dispatches to Local view when session supplied."""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    CATEGORY_PERCEPTION,
    Capacity,
    DataState,
    ShapeDescriptor,
    find_pipeline,
)

from tests.phase_30._fixtures import (
    DS_INPUT_IRI,
    DS_OUTPUT_IRI,
    build_linear_pipeline_layer,
    build_session,
)


def test_find_pipeline_no_session_walks_global():
    cl = build_linear_pipeline_layer()
    pipeline = find_pipeline(
        cl,
        start_datastate=DS_INPUT_IRI,
        target_datastate=DS_OUTPUT_IRI,
    ).pipeline
    assert len(pipeline) == 2


def test_find_pipeline_with_unpopulated_session_local_composes_global():
    """A session whose Local holds no capacities still gets the Global chain.

    **This assertion is inverted from what it was**, deliberately. It used to
    read ``assert not verdict.found``: ``_view_for`` returned the Local view
    *instead of* Global, so a user with an empty Local saw an empty catalog.
    With the Local-preferring union view, Local contributes nothing here and
    the Global 2-capacity pipeline composes — which is the whole point of the
    two-tier change. The old expectation was the defect, not the contract.
    """
    cl = build_linear_pipeline_layer()  # Global has 2 caps
    sess = build_session("alice")  # alice has no Local capacities

    # Registering Local DataStates is what mints alice's Local metagraph, so
    # `has_local` is True below and the union view (not the Global fallback)
    # is the path under test.
    cl.register_datastate(
        DataState(
            name="test.input",
            shape=ShapeDescriptor.scalar("str", opaque_tag="test.input"),
        ),
        session=sess,
        allow_new_realm=True,
    )
    cl.register_datastate(
        DataState(
            name="test.output",
            shape=ShapeDescriptor.scalar("str", opaque_tag="test.output"),
        ),
        session=sess,
        allow_new_realm=True,
    )

    verdict = find_pipeline(
        cl,
        session=sess,
        start_datastate=DS_INPUT_IRI,
        target_datastate=DS_OUTPUT_IRI,
    )
    assert cl.has_local("alice")
    assert verdict.found
    assert len(verdict.pipeline) == 2


def test_find_pipeline_with_local_capacity_succeeds():
    cl = build_linear_pipeline_layer()
    sess = build_session("alice")

    # Register Local DataStates + a single direct-jump capacity.
    cl.register_datastate(
        DataState(
            name="test.input",
            shape=ShapeDescriptor.scalar("str", opaque_tag="test.input"),
        ),
        session=sess,
        allow_new_realm=True,
    )
    cl.register_datastate(
        DataState(
            name="test.output",
            shape=ShapeDescriptor.scalar("str", opaque_tag="test.output"),
        ),
        session=sess,
        allow_new_realm=True,
    )
    direct = Capacity(
        name="local.direct",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_INPUT_IRI,),
        outputs=(DS_OUTPUT_IRI,),
        implementation=lambda **kw: {DS_OUTPUT_IRI: kw[DS_INPUT_IRI]},
    )
    cl.register_capacity(direct, session=sess)

    pipeline = find_pipeline(
        cl,
        session=sess,
        start_datastate=DS_INPUT_IRI,
        target_datastate=DS_OUTPUT_IRI,
    ).pipeline
    assert len(pipeline) == 1
    assert pipeline.steps[0].capacity_iri == direct.iri
