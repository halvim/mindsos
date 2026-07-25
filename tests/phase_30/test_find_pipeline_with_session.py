"""Phase 30 — find_pipeline dispatches to Local view when session supplied."""

from __future__ import annotations

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
    )
    assert len(pipeline) == 2


def test_find_pipeline_unpopulated_session_local_falls_back_to_global():
    """Session with an empty Local composes the Global pipeline via the
    Local-preferring union view (CORE_CR step 3 — previously raised)."""
    cl = build_linear_pipeline_layer()  # Global has 2 caps
    sess = build_session("alice")  # alice has no Local capacities

    # Local DataState nodes present but no Local capacity: the union view
    # falls back to the Global producers, so the Global 2-cap chain composes.
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

    pipeline = find_pipeline(
        cl,
        session=sess,
        start_datastate=DS_INPUT_IRI,
        target_datastate=DS_OUTPUT_IRI,
    )
    assert len(pipeline) == 2


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
    )
    assert len(pipeline) == 1
    assert pipeline.steps[0].capacity_iri == direct.iri
