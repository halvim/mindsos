"""Phase 46 — MM resolution + instantiation (ADR-0166)."""

from __future__ import annotations

import pytest

from mindsos_capacity.context import MMHandle
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.mm_resolver import (
    InstantiatedNode,
    MMResolver,
    PinnedRef,
    SourceNode,
)


class FakeSource:
    def __init__(self):
        self._nodes = {}

    def add(self, iri, version, type_iri=None, produces=(), consumes=()):
        self._nodes[iri] = SourceNode(
            iri=iri,
            version=version,
            type_iri=type_iri,
            payload=None,
            produces=tuple(produces),
            consumes=tuple(consumes),
        )

    def bump(self, iri, version):
        n = self._nodes[iri]
        self._nodes[iri] = SourceNode(
            iri=iri,
            version=version,
            type_iri=n.type_iri,
            payload=n.payload,
            produces=n.produces,
            consumes=n.consumes,
        )

    def get_node(self, iri):
        return self._nodes[iri]


def _resolver():
    src = FakeSource()
    src.add(
        "capacity:x:do",
        version=3,
        type_iri="capacity",
        produces=["datastate:r.out"],
    )
    src.add("datastate:r.out", version=2, type_iri="datastate", consumes=["capacity:x:do"])
    mm = MentalModel(session_id="s1", user_id="u1")
    return MMResolver(mm, src), src


def test_satisfies_mmhandle_protocol():
    r, _ = _resolver()
    assert isinstance(r, MMHandle)


def test_lazy_single_node_and_monotone():
    r, _ = _resolver()
    assert r.instantiated_count() == 0
    a = r.get_or_instantiate("capacity:x:do")
    assert isinstance(a, InstantiatedNode)
    assert r.instantiated_count() == 1
    again = r.get_or_instantiate("capacity:x:do")
    assert again is a
    assert r.instantiated_count() == 1


def test_pin_at_instantiation_survives_source_bump():
    r, src = _resolver()
    a = r.get_or_instantiate("capacity:x:do")
    assert a.pin == PinnedRef("capacity:x:do", 3)
    src.bump("capacity:x:do", version=9)
    again = r.get_or_instantiate("capacity:x:do")
    assert again is a
    assert again.pin.version == 3


def test_iri_namespace_dispatch_rejects_unknown():
    r, src = _resolver()
    src.add("unknown:thing", version=1)
    with pytest.raises(KeyError):
        r.get_or_instantiate("unknown:thing")


def test_find_instances_by_type():
    r, _ = _resolver()
    r.get_or_instantiate("capacity:x:do")
    r.get_or_instantiate("datastate:r.out")
    caps = r.find_instances_by_type("capacity")
    assert [n.iri for n in caps] == ["capacity:x:do"]


def test_produces_and_consumes():
    r, _ = _resolver()
    cap = r.get_or_instantiate("capacity:x:do")
    produced = r.produces_of(cap)
    assert [n.iri for n in produced] == ["datastate:r.out"]
    ds = r.get_or_instantiate("datastate:r.out")
    consumers = r.consumes_of(ds)
    assert [n.iri for n in consumers] == ["capacity:x:do"]
