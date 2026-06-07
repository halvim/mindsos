"""Phase 28 — CapacityLayer.register_capacity."""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    Adapter,
    Capacity,
    CapacityLayer,
    CATEGORY_PERCEPTION,
    CapacityRegistrationError,
    EDGE_CONSUMES,
    EDGE_PRODUCES,
    Monitor,
    NODE_TYPE_ADAPTER,
    NODE_TYPE_CAPACITY,
    NODE_TYPE_MONITOR,
    RESERVED_PROPERTY_KEYS,
)
from mindsos_server.session import Session

from ._fixtures import (
    text_demo_capacity,
    text_raw_datastate,
    text_tokens_datastate,
)


def _new_layer() -> CapacityLayer:
    return CapacityLayer(categories=(CATEGORY_PERCEPTION,))


def _bootstrap_datastates(cl: CapacityLayer, *, session=None) -> None:
    cl.register_datastate(text_raw_datastate(), session=session)
    cl.register_datastate(text_tokens_datastate(), session=session)


def test_register_capacity_happy_path_global():
    cl = _new_layer()
    _bootstrap_datastates(cl)
    cap = text_demo_capacity()
    node = cl.register_capacity(cap)
    assert node.node_id == cap.iri
    assert node.type_name == NODE_TYPE_CAPACITY
    # ADR-0156 (Phase 42): inputs/outputs are no longer node properties;
    # they become PRODUCES/CONSUMES IntergraphEdges emitted at register time.
    assert "inputs" not in node.properties
    assert "outputs" not in node.properties
    gmg = cl.global_metagraph()
    produces = {
        (ie.source_node_id, ie.target_node_id)
        for ie in gmg.iter_intergraph_edges()
        if ie.type_name == EDGE_PRODUCES
    }
    consumes = {
        (ie.source_node_id, ie.target_node_id)
        for ie in gmg.iter_intergraph_edges()
        if ie.type_name == EDGE_CONSUMES
    }
    assert (cap.iri, text_tokens_datastate().iri) in produces
    assert (text_raw_datastate().iri, cap.iri) in consumes
    assert cap.iri in cl._capacity_index[gmg.metagraph_id]
    assert cl.get_declaration(cap.iri) is cap


def test_register_monitor_happy_path():
    cl = _new_layer()
    _bootstrap_datastates(cl)
    raw = text_raw_datastate()
    mon = Monitor(
        name="text.watch",
        category=CATEGORY_PERCEPTION,
        inputs=(raw.iri,),
        outputs=(raw.iri,),
        subscribes_to=(raw.iri,),
        emits=(raw.iri,),
        implementation=lambda **kw: kw,
    )
    node = cl.register_capacity(mon)
    assert node.type_name == NODE_TYPE_MONITOR
    assert node.properties["subscribes_to"] == [raw.iri]
    assert node.properties["emits"] == [raw.iri]


def test_register_adapter_happy_path():
    cl = _new_layer()
    _bootstrap_datastates(cl)
    raw = text_raw_datastate()
    tokens = text_tokens_datastate()
    ad = Adapter(
        name="text.adapt",
        category=CATEGORY_PERCEPTION,
        inputs=(raw.iri,),
        outputs=(tokens.iri,),
        implementation=lambda **kw: {tokens.iri: kw[raw.iri].split()},
    )
    node = cl.register_capacity(ad)
    assert node.type_name == NODE_TYPE_ADAPTER
    assert node.properties["is_adapter"] is True


def test_register_capacity_rejects_unknown_datastate():
    cl = _new_layer()
    with pytest.raises(CapacityRegistrationError, match="unknown DataState"):
        cl.register_capacity(text_demo_capacity())


def test_register_capacity_rejects_non_capacity_base():
    cl = _new_layer()
    _bootstrap_datastates(cl)
    with pytest.raises(CapacityRegistrationError, match="Expected a Capacity"):
        cl.register_capacity("not a capacity")


def test_register_capacity_duplicate_rejected():
    cl = _new_layer()
    _bootstrap_datastates(cl)
    cl.register_capacity(text_demo_capacity())
    with pytest.raises(CapacityRegistrationError, match="already registered"):
        cl.register_capacity(text_demo_capacity())


def test_register_capacity_with_user_session_routes_local():
    cl = _new_layer()
    sess = Session.for_testing("alice", is_admin=False)
    _bootstrap_datastates(cl, session=sess)
    cap = text_demo_capacity()
    node = cl.register_capacity(cap, session=sess)
    assert node.properties["created_by"] == "alice"
    alice_mg = cl.local_metagraph("alice")
    assert cap.iri in cl._capacity_index[alice_mg.metagraph_id]


def test_ref_to_global_without_session_rejected():
    cl = _new_layer()
    _bootstrap_datastates(cl)
    cap = text_demo_capacity()
    cl.register_capacity(cap)
    with pytest.raises(CapacityRegistrationError, match="only meaningful for Local"):
        cl.register_capacity(
            text_demo_capacity(),
            ref_to_global=cap.iri,
            ref_type="SPECIALISES",
        )


def test_ref_to_global_without_ref_type_rejected():
    cl = _new_layer()
    sess = Session.for_testing("alice", is_admin=False)
    _bootstrap_datastates(cl, session=sess)
    with pytest.raises(CapacityRegistrationError, match="supplied together"):
        cl.register_capacity(
            text_demo_capacity(),
            session=sess,
            ref_to_global="capacity:perception:text.demo",
        )


@pytest.mark.parametrize("key", sorted(RESERVED_PROPERTY_KEYS))
def test_reserved_property_keys_rejected_in_extra_properties(key):
    cl = _new_layer()
    _bootstrap_datastates(cl)
    with pytest.raises(CapacityRegistrationError, match="Reserved property key"):
        cl.register_capacity(
            text_demo_capacity(),
            extra_properties={key: "rejected"},
        )
