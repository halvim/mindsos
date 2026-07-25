"""Phase 28 — two-tier (Local-over-Global) resolution guarantee.

Global B and a same-IRI Local B' coexist as distinct objects: the owner
resolves B', a sessionless or other-user context resolves B (Global
preserved, no leak), and the outcome does not depend on registration
order. Locks the CORE_CR two-tier acceptance (supersedes the order-
dependent last-write behaviour the flat `_declarations` map gave).
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer, CATEGORY_PERCEPTION
from mindsos_server.session import Session

from ._fixtures import (
    text_demo_capacity,
    text_demo_v2_capacity,
    text_raw_datastate,
    text_tokens_datastate,
)


def _global_layer():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    cl.register_datastate(text_raw_datastate())
    cl.register_datastate(text_tokens_datastate())
    gcap = text_demo_capacity()
    cl.register_capacity(gcap)
    return cl, gcap


def _teach_local_override(cl, gcap, user):
    sess = Session.for_testing(user, is_admin=False)
    cl.register_datastate(text_raw_datastate(), session=sess)
    cl.register_datastate(text_tokens_datastate(), session=sess)
    local = text_demo_v2_capacity()
    cl.register_capacity(
        local, session=sess, ref_to_global=gcap.iri, ref_type="SPECIALISES"
    )
    return local


def test_owner_resolves_local_others_resolve_global():
    cl, gcap = _global_layer()
    local = _teach_local_override(cl, gcap, "alice")
    alice = Session.for_testing("alice", is_admin=False)
    bob = Session.for_testing("bob", is_admin=False)
    assert cl.resolve_declaration(gcap.iri, session=alice) is local
    assert cl.resolve_declaration(gcap.iri, session=None) is gcap
    assert cl.resolve_declaration(gcap.iri, session=bob) is gcap


def test_override_is_order_independent():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    alice = Session.for_testing("alice", is_admin=False)
    cl.register_datastate(text_raw_datastate(), session=alice)
    cl.register_datastate(text_tokens_datastate(), session=alice)
    local = text_demo_v2_capacity()
    cl.register_capacity(local, session=alice)
    cl.register_datastate(text_raw_datastate())
    cl.register_datastate(text_tokens_datastate())
    gcap = text_demo_capacity()
    cl.register_capacity(gcap)
    assert cl.resolve_declaration(gcap.iri, session=alice) is local
    assert cl.resolve_declaration(gcap.iri, session=None) is gcap
