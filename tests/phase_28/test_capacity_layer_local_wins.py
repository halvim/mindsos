"""Phase 28 — ADR-0061 Local-wins lookup + R3 PB-36 Local-overwrites-Global doc."""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    CapacityLayer,
    CATEGORY_PERCEPTION,
    CapacityRegistrationError,
    REF_GLOBAL_CAPACITY,
    REF_TYPE_KEY,
)
from mindsos_server.session import Session

from ._fixtures import (
    text_demo_capacity,
    text_demo_v2_capacity,
    text_raw_datastate,
    text_tokens_datastate,
)


def _layer_with_global_capacity():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    cl.register_datastate(text_raw_datastate())
    cl.register_datastate(text_tokens_datastate())
    gcap = text_demo_capacity()
    cl.register_capacity(gcap)
    return cl, gcap


def test_resolve_returns_global_when_no_local_exists():
    cl, gcap = _layer_with_global_capacity()
    resolved = cl._resolve_declaration(gcap.iri, user_id=None)
    assert resolved is gcap


def test_resolve_falls_back_to_global_when_user_has_no_local_entry():
    cl, gcap = _layer_with_global_capacity()
    resolved = cl._resolve_declaration(gcap.iri, user_id="alice")
    assert resolved is gcap


def test_resolve_returns_local_when_local_exists():
    cl, gcap = _layer_with_global_capacity()
    alice = Session.for_testing("alice", is_admin=False)
    cl.register_datastate(text_raw_datastate(), session=alice)
    cl.register_datastate(text_tokens_datastate(), session=alice)
    local_cap = text_demo_v2_capacity()
    cl.register_capacity(
        local_cap,
        session=alice,
        ref_to_global=gcap.iri,
        ref_type="SPECIALISES",
    )
    resolved = cl._resolve_declaration(local_cap.iri, user_id="alice")
    assert resolved is local_cap
    resolved_no_local = cl._resolve_declaration(local_cap.iri, user_id=None)
    assert resolved_no_local is gcap


def test_resolve_unknown_capacity_raises():
    cl, _ = _layer_with_global_capacity()
    with pytest.raises(CapacityRegistrationError, match="No capacity registered"):
        cl._resolve_declaration("capacity:perception:nonexistent", user_id=None)


def test_cross_user_local_isolation():
    cl, gcap = _layer_with_global_capacity()
    alice = Session.for_testing("alice", is_admin=False)
    cl.register_datastate(text_raw_datastate(), session=alice)
    cl.register_datastate(text_tokens_datastate(), session=alice)
    cl.register_capacity(
        text_demo_v2_capacity(),
        session=alice,
        ref_to_global=gcap.iri,
        ref_type="SPECIALISES",
    )
    bob_resolved = cl._resolve_declaration(gcap.iri, user_id="bob")
    assert bob_resolved is not None
    bob_mg = cl.local_metagraph("bob")
    assert cl._capacity_index[bob_mg.metagraph_id] == {}


def test_local_registration_overwrites_global_in_declarations():
    cl, gcap = _layer_with_global_capacity()
    pre = cl._declarations[gcap.iri]
    assert pre is gcap
    alice = Session.for_testing("alice", is_admin=False)
    cl.register_datastate(text_raw_datastate(), session=alice)
    cl.register_datastate(text_tokens_datastate(), session=alice)
    local_cap = text_demo_v2_capacity()
    cl.register_capacity(
        local_cap,
        session=alice,
        ref_to_global=gcap.iri,
        ref_type="SPECIALISES",
    )
    post = cl._declarations[gcap.iri]
    assert post is local_cap
    assert post is not gcap
    alice_idx = cl._capacity_index[cl.local_metagraph("alice").metagraph_id]
    global_idx = cl._capacity_index[cl.global_metagraph().metagraph_id]
    assert gcap.iri in alice_idx
    assert gcap.iri in global_idx
    local_node, _, _ = alice_idx[gcap.iri]
    assert local_node.properties[REF_GLOBAL_CAPACITY] == gcap.iri
    assert local_node.properties[REF_TYPE_KEY] == "SPECIALISES"


def test_sessionless_get_declaration_never_returns_a_local():
    """ADR-0071 §am-5: a sessionless caller must not see any user's Local.

    ``_declarations`` is written on every registration regardless of realm, so
    a Local registration overwrites the Global entry at the same IRI. Reading
    that mirror from the sessionless ``get_declaration`` therefore leaked a
    user's Local declaration to callers asking about the shared catalog.
    The mirror is unchanged — only the lookup stops reading it.
    """
    cl, gcap = _layer_with_global_capacity()
    alice = Session.for_testing("alice", is_admin=False)
    cl.register_datastate(text_raw_datastate(), session=alice)
    cl.register_datastate(text_tokens_datastate(), session=alice)
    local_cap = text_demo_v2_capacity()
    cl.register_capacity(
        local_cap,
        session=alice,
        ref_to_global=gcap.iri,
        ref_type="SPECIALISES",
    )

    # The flat mirror still merges, Local-last — R3 PB-36, deliberately kept.
    assert cl._declarations[gcap.iri] is local_cap

    # ...but the sessionless public surface answers from Global only.
    assert cl.get_declaration(gcap.iri) is gcap

    # Scope-correct resolution is unchanged in both directions.
    assert cl.resolve_declaration(gcap.iri, session=None) is gcap
    assert cl.resolve_declaration(gcap.iri, session=alice) is local_cap
