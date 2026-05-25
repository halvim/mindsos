"""Phase 28 — CapacityLayer.register_datastate."""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    CapacityLayer,
    CATEGORY_PERCEPTION,
    CapacityRegistrationError,
    DataState,
    DataStateError,
    ROLE_DATASTATES,
    ShapeDescriptor,
)
from mindsos_server.session import Session

from ._fixtures import text_raw_datastate


def _new_layer() -> CapacityLayer:
    return CapacityLayer(categories=(CATEGORY_PERCEPTION,))


def _datastate_graph(mg):
    for g in mg.graphs.values():
        if g.role == ROLE_DATASTATES:
            return g
    raise AssertionError(f"No DataStates graph in {mg.name!r}")


def test_register_datastate_global_no_session_happy_path():
    cl = _new_layer()
    ds = text_raw_datastate()
    node = cl.register_datastate(ds)
    assert node.node_id == ds.iri
    assert node.type_name == "DataState"
    assert "created_by" not in node.properties
    assert ds.iri in _datastate_graph(cl.global_metagraph()).nodes


def test_register_datastate_with_user_session_routes_local():
    cl = _new_layer()
    sess = Session.for_testing("alice", is_admin=False)
    ds = text_raw_datastate()
    node = cl.register_datastate(ds, session=sess)
    assert node.properties["created_by"] == "alice"
    assert ds.iri in _datastate_graph(cl.local_metagraph("alice")).nodes
    assert ds.iri not in _datastate_graph(cl.global_metagraph()).nodes


def test_register_datastate_with_admin_session_routes_local():
    cl = _new_layer()
    sess = Session.for_testing("root", is_admin=True)
    ds = text_raw_datastate()
    node = cl.register_datastate(ds, session=sess)
    assert ds.iri in _datastate_graph(cl.local_metagraph("root")).nodes


def test_register_datastate_duplicate_rejected():
    cl = _new_layer()
    ds = text_raw_datastate()
    cl.register_datastate(ds)
    with pytest.raises(CapacityRegistrationError):
        cl.register_datastate(ds)


def test_register_datastate_malformed_shape_rejected():
    bad = DataState(name="", shape=ShapeDescriptor.scalar("str"))
    cl = _new_layer()
    with pytest.raises(DataStateError):
        cl.register_datastate(bad)


def test_register_datastate_node_kind_property_set():
    cl = _new_layer()
    ds = text_raw_datastate()
    node = cl.register_datastate(ds)
    assert node.properties["node_kind"] == "datastate"
