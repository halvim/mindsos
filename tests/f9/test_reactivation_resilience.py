"""F9 — re-activation resilience (ADR-0183 §am-2, extended to reactivation).

Boot must not die because a durable ``learned-parameters`` descriptor
carries a ``reactivation_key`` whose factory is not registered in this
process. Resilient at boot (``strict=False``); strict on explicit call
(``strict=True``, the default — pre-existing callers byte-identical).
Loud: a skip logs a WARNING naming the key, so a missing factory
registration is surfaced, not swallowed.

All in-memory (bootstrapped KL) — no live FalkorDB, so these run in the
normal suite, unlike the ``@pytest.mark.integration`` durable round-trip.
"""

from __future__ import annotations

import logging

import pytest

from mindsos_capacity import (
    CATEGORY_PERCEPTION,
    CapacityLayer,
    ReactivationError,
    reactivate_from_descriptors,
    register_reactivation_factory,
    unregister_reactivation_factory,
)
from mindsos_knowledge import KnowledgeLayer

from ._fixtures import DuckSession, raw_ds, taught_descriptor, taught_factory, tokens_ds


@pytest.fixture
def factory_registered():
    register_reactivation_factory("taught", taught_factory, if_exists="upsert")
    yield
    unregister_reactivation_factory("taught")


def _fresh_layer() -> CapacityLayer:
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    cl.register_datastate(raw_ds())
    cl.register_datastate(tokens_ds())
    return cl


class TestReactivateFromDescriptors:
    def test_missing_factory_skipped_when_not_strict(self, caplog) -> None:
        cl = _fresh_layer()
        desc = taught_descriptor(reactivation_key="no-such-factory")
        with caplog.at_level(logging.WARNING):
            got = reactivate_from_descriptors(
                cl, [desc], session=DuckSession("alice"), strict=False
            )
        assert got == []
        assert any("not re-activated" in r.getMessage() for r in caplog.records)

    def test_missing_factory_raises_when_strict(self) -> None:
        cl = _fresh_layer()
        desc = taught_descriptor(reactivation_key="no-such-factory")
        with pytest.raises(ReactivationError):
            reactivate_from_descriptors(cl, [desc], session=DuckSession("alice"))

    def test_good_survives_alongside_bad(self, factory_registered, caplog) -> None:
        cl = _fresh_layer()
        good = taught_descriptor()
        bad = taught_descriptor(reactivation_key="no-such-factory")
        with caplog.at_level(logging.WARNING):
            got = reactivate_from_descriptors(
                cl, [good, bad], session=DuckSession("alice"), strict=False
            )
        assert got == ["capacity:perception:text.demo"]


class TestDepOrderResilience:
    def test_unbuildable_dropped_when_not_strict(self, factory_registered, caplog) -> None:
        from mindsos_server.local_boot import _dep_order_descriptors

        good = taught_descriptor()
        bad = taught_descriptor(reactivation_key="no-such-factory")
        with caplog.at_level(logging.WARNING):
            ordered = _dep_order_descriptors([good, bad], strict=False)
        assert good in ordered
        assert bad not in ordered
        assert any("could not be built" in r.getMessage() for r in caplog.records)

    def test_unbuildable_raises_when_strict(self, factory_registered) -> None:
        from mindsos_server.local_boot import _dep_order_descriptors

        good = taught_descriptor()
        bad = taught_descriptor(reactivation_key="no-such-factory")
        with pytest.raises(ReactivationError):
            _dep_order_descriptors([good, bad], strict=True)


class TestReactivateLocalCapacities:
    def _write(self, kl, user, desc):
        from mindsos_knowledge import (
            ROLE_LEARNED_PARAMETERS,
            ensure_local_role_graph,
            learned_parameter_iri,
        )
        from mindsos_knowledge.schemas.learned_parameters import NODE_LEARNED_PARAMETER

        local_mg = kl.local_metagraph(user)
        g = ensure_local_role_graph(local_mg, ROLE_LEARNED_PARAMETERS)
        g.add_node(
            dict(desc),
            NODE_LEARNED_PARAMETER,
            properties={"parameter_set_iri": f"taught:{desc['capability']}", "confidence": 1.0},
            node_id=learned_parameter_iri("v1", desc["capability"]),
        )

    def test_boot_survives_factoryless_descriptor(self, caplog) -> None:
        from mindsos_server.local_boot import reactivate_local_capacities

        kl = KnowledgeLayer.bootstrap()
        cl = _fresh_layer()
        user = "alice"
        self._write(kl, user, taught_descriptor(reactivation_key="no-such-factory"))
        with caplog.at_level(logging.WARNING):
            got = reactivate_local_capacities(
                cl, kl, user, session=DuckSession(user), strict=False
            )
        assert got == []
        assert any("not re-activated" in r.getMessage() for r in caplog.records)

    def test_boot_raises_when_strict(self) -> None:
        from mindsos_server.local_boot import reactivate_local_capacities

        kl = KnowledgeLayer.bootstrap()
        cl = _fresh_layer()
        user = "bob"
        self._write(kl, user, taught_descriptor(reactivation_key="no-such-factory"))
        with pytest.raises(ReactivationError):
            reactivate_local_capacities(cl, kl, user, session=DuckSession(user))
