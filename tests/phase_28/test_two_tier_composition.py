"""Phase 28 — two-tier composition: a one-step Local override composes inside
an otherwise-Global pipeline (CORE_CR step 3, LocalPreferringView).

Global chain A -> B -> C (start->m1->m2->target). Override the middle step B
Locally (same IRI, different impl). The owner's find composes A(Global) ->
B'(Local) -> C(Global) in a single search (before the union view, a
session-scoped find saw only the Local drawer and could not reach start->target
through the Global A and C). A sessionless find composes the all-Global chain.
"""

from __future__ import annotations

from mindsos_capacity import (
    Capacity,
    CapacityLayer,
    CATEGORY_PERCEPTION,
    DataState,
    ShapeDescriptor,
)
from mindsos_capacity.pipeline import find_pipeline
from mindsos_server.session import Session


def _ds(name):
    return DataState(name=name, shape=ShapeDescriptor.scalar("str", opaque_tag=name))


def _cap(name, src, dst, impl):
    return Capacity(
        name=name,
        category=CATEGORY_PERCEPTION,
        inputs=(src.iri,),
        outputs=(dst.iri,),
        implementation=impl,
    )


def _global_chain():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    start, m1, m2, target = (
        _ds("text.start"), _ds("text.m1"), _ds("text.m2"), _ds("text.target"),
    )
    for d in (start, m1, m2, target):
        cl.register_datastate(d)
    a = _cap("chain.a", start, m1, lambda **k: {m1.iri: k[start.iri]})
    b = _cap("chain.b", m1, m2, lambda **k: {m2.iri: "GLOBAL"})
    c = _cap("chain.c", m2, target, lambda **k: {target.iri: k[m2.iri]})
    for cap in (a, b, c):
        cl.register_capacity(cap)
    return cl, (start, m1, m2, target), (a, b, c)


def _override_b_local(cl, gcap_b, m1, m2, user):
    sess = Session.for_testing(user, is_admin=False)
    b2 = _cap("chain.b", m1, m2, lambda **k: {m2.iri: "LOCAL"})
    cl.register_capacity(
        b2, session=sess, ref_to_global=gcap_b.iri, ref_type="SPECIALISES"
    )
    return b2


def test_local_override_composes_inside_global_pipeline():
    cl, (start, m1, m2, target), (a, b, c) = _global_chain()
    b2 = _override_b_local(cl, b, m1, m2, "alice")
    alice = Session.for_testing("alice", is_admin=False)

    pipe = find_pipeline(
        cl, session=alice, start_datastate=start.iri, target_datastate=target.iri
    )
    assert [s.capacity_iri for s in pipe.steps] == [a.iri, b.iri, c.iri]
    assert cl.resolve_declaration(b.iri, session=alice) is b2
    assert cl.resolve_declaration(b.iri, session=None) is b


def test_global_pipeline_unchanged_for_non_owner():
    cl, (start, m1, m2, target), (a, b, c) = _global_chain()
    _override_b_local(cl, b, m1, m2, "alice")

    pipe = find_pipeline(
        cl, session=None, start_datastate=start.iri, target_datastate=target.iri
    )
    assert [s.capacity_iri for s in pipe.steps] == [a.iri, b.iri, c.iri]
    assert cl.resolve_declaration(b.iri, session=None) is b
