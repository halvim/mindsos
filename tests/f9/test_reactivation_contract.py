"""F9 — capacity re-activation contract (ADR-0185), pure-L3.

These exercise the descriptor → factory → register path without a live
DB or the server layer: a fresh ``CapacityLayer`` simulates a process
restart (empty ``_declarations`` / ``_capacity_index``).
"""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    CapacityLayer,
    CATEGORY_PERCEPTION,
    REACTIVATION_KEY,
    ReactivationError,
    build_declaration,
    is_reactivatable,
    reactivate_from_descriptors,
    register_reactivation_factory,
    unregister_reactivation_factory,
)

from ._fixtures import DuckSession, raw_ds, taught_descriptor, taught_factory, tokens_ds


@pytest.fixture
def factory_registered():
    register_reactivation_factory("taught", taught_factory, if_exists="upsert")
    yield
    unregister_reactivation_factory("taught")


def _fresh_layer():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    # Global bootstrap re-mints the Global DataStates each process.
    cl.register_datastate(raw_ds())
    cl.register_datastate(tokens_ds())
    return cl


def test_reactivate_then_invoke_without_code_registration(factory_registered):
    cl = _fresh_layer()
    alice = DuckSession("alice")
    iris = reactivate_from_descriptors(cl, [taught_descriptor()], session=alice)
    assert iris == ["capacity:perception:text.demo"]

    res = cl.invoke(iris[0], {raw_ds().iri: "hello"}, session=alice)
    assert res.success
    assert res.outputs[tokens_ds().iri] == "HELLO"


def test_negative_no_key_or_installer_is_not_reactivated(factory_registered):
    cl = _fresh_layer()
    no_key = taught_descriptor()
    no_key.pop(REACTIVATION_KEY)
    installer = taught_descriptor(reactivation_key="installer")
    got = reactivate_from_descriptors(cl, [no_key, installer], session=DuckSession("bob"))
    assert got == []


def test_is_reactivatable_predicate():
    assert is_reactivatable(taught_descriptor()) is True
    no_key = taught_descriptor()
    no_key.pop(REACTIVATION_KEY)
    assert is_reactivatable(no_key) is False
    assert is_reactivatable(taught_descriptor(reactivation_key="installer")) is False


def test_unknown_factory_key_raises(factory_registered):
    with pytest.raises(ReactivationError):
        build_declaration("does-not-exist", taught_descriptor())


def test_installer_sentinel_may_not_name_a_factory():
    with pytest.raises(ReactivationError):
        register_reactivation_factory("installer", taught_factory)


def test_reactivation_is_idempotent_and_rebinds_impl(factory_registered):
    cl = _fresh_layer()
    alice = DuckSession("alice")
    desc = taught_descriptor()
    reactivate_from_descriptors(cl, [desc], session=alice)

    # Re-bind the factory to a different impl, re-run → last wins (upsert).
    def lower_factory(d):
        out, inp = d["outputs"][0], d["inputs"][0]
        from mindsos_capacity import Capacity

        return Capacity(
            name=d["capability"],
            category=d["category"],
            inputs=tuple(d["inputs"]),
            outputs=tuple(d["outputs"]),
            implementation=lambda **kw: {out: kw[inp].lower()},
        )

    register_reactivation_factory("taught", lower_factory, if_exists="upsert")
    reactivate_from_descriptors(cl, [desc], session=alice)
    res = cl.invoke("capacity:perception:text.demo", {raw_ds().iri: "HeLLo"}, session=alice)
    assert res.outputs[tokens_ds().iri] == "hello"
