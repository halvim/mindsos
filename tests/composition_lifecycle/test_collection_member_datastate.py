"""ADR-0199 (C4) — group / member DataState attribute.

``group=True`` + ``member_ds`` type the L3→L4 iteration seam. Group and
member stay distinct DataState types; the coherence invariant is that the
two travel together. Absent = today's behaviour. Attributes are emitted to
node props for inspectability.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import DataState, ShapeDescriptor
from mindsos_capacity.datastate import validate_datastate
from mindsos_capacity.exceptions import DataStateError


DS_MEMBER_IRI = "datastate:test.object"


def _group() -> DataState:
    return DataState(
        name="test.objects",
        shape=ShapeDescriptor.list_of("object"),
        group=True,
        member_ds=DS_MEMBER_IRI,
    )


def _member() -> DataState:
    return DataState(name="test.object", shape=ShapeDescriptor.scalar("object"))


# ── happy path ────────────────────────────────────────────────────────


def test_group_declaration_validates():
    validate_datastate(_group())


def test_group_attributes_emitted_to_props():
    props = _group().to_properties()
    assert props["group"] is True
    assert props["member_ds"] == DS_MEMBER_IRI


def test_member_is_plain_non_group():
    m = _member()
    validate_datastate(m)
    props = m.to_properties()
    assert "group" not in props
    assert "member_ds" not in props


# ── coherence invariant ───────────────────────────────────────────────


def test_group_without_member_rejected():
    bad = DataState(
        name="test.bad", shape=ShapeDescriptor.scalar("x"), group=True
    )
    with pytest.raises(DataStateError):
        validate_datastate(bad)


def test_member_without_group_rejected():
    bad = DataState(
        name="test.bad2",
        shape=ShapeDescriptor.scalar("x"),
        member_ds=DS_MEMBER_IRI,
    )
    with pytest.raises(DataStateError):
        validate_datastate(bad)


# ── finder does not bridge (distinct IRIs, unchanged behaviour) ───────


def test_group_and_member_are_distinct_iris():
    assert _group().iri != _member().iri
