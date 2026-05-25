"""Phase 30 — invoke() resolves Local presence first (ADR-0061).

Halvim's `_resolve_declaration` (capacity_layer.py:449) uses a
layer-wide `_declarations` dict keyed by IRI only — Local-wins is a
*presence* semantic (if a Local entry exists for the IRI in
`_capacity_index[local_mg.metagraph_id]`, use it; else fall back to
Global). For same-IRI overlap the registered Python declaration is the
most-recent registration on the layer (since `_declarations[iri]`
overwrites).

This test verifies the presence side: a capacity registered ONLY in
Local is reachable from a session-scoped invoke but NOT from a
session-less invoke.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    CATEGORY_PERCEPTION,
    Capacity,
    CapacityRegistrationError,
    DataState,
    ShapeDescriptor,
)

from tests.phase_30._fixtures import (
    DS_INPUT_IRI,
    DS_OUTPUT_IRI,
    build_min_layer,
    build_session,
)


def _register_input_output_in_local(cl, user_id: str) -> None:
    """Locals need DataState nodes too — register both DS's in the Local mg."""
    sess = build_session(user_id)
    cl.register_datastate(
        DataState(
            name="test.input",
            shape=ShapeDescriptor.scalar("str", opaque_tag="test.input"),
        ),
        session=sess,
    )
    cl.register_datastate(
        DataState(
            name="test.output",
            shape=ShapeDescriptor.scalar("str", opaque_tag="test.output"),
        ),
        session=sess,
    )


def test_session_scoped_invoke_reaches_local_only_capacity():
    """Local-only capacity is reachable via session-scoped invoke."""
    cl = build_min_layer()
    sess = build_session("alice")
    _register_input_output_in_local(cl, "alice")

    local_only = Capacity(
        name="local.only",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_INPUT_IRI,),
        outputs=(DS_OUTPUT_IRI,),
        implementation=lambda **kw: {DS_OUTPUT_IRI: "LOCAL:" + kw[DS_INPUT_IRI]},
    )
    cl.register_capacity(local_only, session=sess)

    res = cl.invoke(local_only.iri, inputs={DS_INPUT_IRI: "hi"}, session=sess)
    assert res.success is True
    assert res.outputs == {DS_OUTPUT_IRI: "LOCAL:hi"}


def test_session_less_invoke_cannot_reach_local_only_capacity():
    """Session=None invoke falls back to Global; Local-only IRI is unreachable."""
    cl = build_min_layer()
    sess = build_session("alice")
    _register_input_output_in_local(cl, "alice")

    local_only = Capacity(
        name="local.only",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_INPUT_IRI,),
        outputs=(DS_OUTPUT_IRI,),
        implementation=lambda **kw: {DS_OUTPUT_IRI: "LOCAL:" + kw[DS_INPUT_IRI]},
    )
    cl.register_capacity(local_only, session=sess)

    with pytest.raises(CapacityRegistrationError):
        cl.invoke(local_only.iri, inputs={DS_INPUT_IRI: "hi"})
