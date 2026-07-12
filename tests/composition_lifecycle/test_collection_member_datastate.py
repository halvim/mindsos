"""ADR-0199 (C4) — collection / member DataState attribute.

``collection=True`` + ``member_ds`` type the L3→L4 iteration seam. Collection
and member stay distinct DataState types; the coherence invariant is that the
two travel together. Absent = today's behaviour. Attributes are emitted to
node props for inspectability.
"""

from __future__ import annotations

import warnings

import pytest

from mindsos_capacity import DataState, ShapeDescriptor
from mindsos_capacity.datastate import validate_datastate
from mindsos_capacity.exceptions import DataStateError


DS_MEMBER_IRI = "datastate:test.object"


def _collection() -> DataState:
    return DataState(
        name="test.objects",
        shape=ShapeDescriptor.list_of("object"),
        collection=True,
        member_ds=DS_MEMBER_IRI,
    )


def _member() -> DataState:
    return DataState(name="test.object", shape=ShapeDescriptor.scalar("object"))


# ── happy path ────────────────────────────────────────────────────────


def test_collection_declaration_validates():
    validate_datastate(_collection())


def test_collection_attributes_emitted_to_props():
    props = _collection().to_properties()
    assert props["collection"] is True
    assert props["member_ds"] == DS_MEMBER_IRI


def test_member_is_plain_non_collection():
    m = _member()
    validate_datastate(m)
    props = m.to_properties()
    assert "collection" not in props
    assert "member_ds" not in props


# ── coherence invariant ───────────────────────────────────────────────


def test_collection_without_member_rejected():
    bad = DataState(
        name="test.bad", shape=ShapeDescriptor.scalar("x"), collection=True
    )
    with pytest.raises(DataStateError):
        validate_datastate(bad)


def test_member_without_collection_rejected():
    bad = DataState(
        name="test.bad2",
        shape=ShapeDescriptor.scalar("x"),
        member_ds=DS_MEMBER_IRI,
    )
    with pytest.raises(DataStateError):
        validate_datastate(bad)


# ── finder does not bridge (distinct IRIs, unchanged behaviour) ───────


def test_collection_and_member_are_distinct_iris():
    assert _collection().iri != _member().iri


# ── deprecated group= constructor alias (ADR-0199 am-1 transition) ─────


def test_group_kwarg_alias_folds_into_collection_with_warning():
    with pytest.warns(DeprecationWarning):
        ds = DataState(
            name="test.objects",
            shape=ShapeDescriptor.list_of("object"),
            group=True,
            member_ds=DS_MEMBER_IRI,
        )
    assert ds.collection is True
    validate_datastate(ds)
    assert ds.to_properties()["collection"] is True
    # InitVar is not stored per-instance: ``.group`` reads the inert class
    # default (None), never the passed value — reads must use ``.collection``.
    assert getattr(ds, "group", None) is None


def test_no_group_kwarg_emits_no_warning():
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # any DeprecationWarning would raise
        DataState(name="test.object", shape=ShapeDescriptor.scalar("object"))
