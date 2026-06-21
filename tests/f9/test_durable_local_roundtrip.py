"""F9 — durable Local round-trip across a simulated restart (the gate).

Integration: persist a Local carrying a descriptor-driven learned
capability through ``FalkorDBLocalPersister`` → construct a FRESH
KL/CL (empty declarations/index, simulating a process restart) →
``boot_local`` (load_or_mint + reactivate) → ``invoke`` returns the live
result WITHOUT re-registering the capability from code.

Marked ``@pytest.mark.integration``; auto-skipped when no live FalkorDB
sidecar is reachable (the cumulative Linux gate provides one).
"""

from __future__ import annotations

import pytest

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401 — fixture

pytestmark = pytest.mark.integration


def _write_descriptor(kl, user_id, descriptor):
    from mindsos_knowledge import (
        ROLE_LEARNED_PARAMETERS,
        ensure_local_role_graph,
        learned_parameter_iri,
    )
    from mindsos_knowledge.schemas.learned_parameters import NODE_LEARNED_PARAMETER

    local_mg = kl.local_metagraph(user_id)
    g = ensure_local_role_graph(local_mg, ROLE_LEARNED_PARAMETERS)
    node_iri = learned_parameter_iri("v1", descriptor["capability"])
    g.add_node(
        dict(descriptor),
        NODE_LEARNED_PARAMETER,
        properties={
            "parameter_set_iri": f"taught:{descriptor['capability']}",
            "confidence": 1.0,
        },
        node_id=node_iri,
    )
    return local_mg


def test_durable_local_roundtrip_reactivates_capability(falkor_client):
    from mindsos_capacity import (
        CapacityLayer,
        CATEGORY_PERCEPTION,
        register_reactivation_factory,
        unregister_reactivation_factory,
    )
    from mindsos_knowledge import KnowledgeLayer
    from mindsos_server.local_boot import boot_local
    from mindsos_server.persistence import FalkorDBLocalPersister
    from mindsos_server.session import Session

    from ._fixtures import raw_ds, taught_descriptor, taught_factory, tokens_ds

    user_id = "alice"
    persister = FalkorDBLocalPersister(falkor_client)

    # ── Pre-restart: write the durable descriptor into the KL Local + persist ──
    kl1 = KnowledgeLayer.bootstrap()
    local_mg = _write_descriptor(kl1, user_id, taught_descriptor())
    persister.save(user_id, local_mg)

    # ── Simulated restart: fresh KL/CL with empty declarations/index ──
    kl2 = KnowledgeLayer.bootstrap()
    cl2 = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    cl2.register_datastate(raw_ds())      # Global bootstrap re-mints these
    cl2.register_datastate(tokens_ds())
    register_reactivation_factory("taught", taught_factory, if_exists="upsert")
    try:
        session = Session.for_testing(user_id)
        mg, minted, reactivated = boot_local(
            cl2, kl2, persister, user_id, session=session
        )
        assert minted is False  # loaded from the persister, not minted
        assert reactivated == ["capacity:perception:text.demo"]

        # invoke works with NO code registration of the capability.
        res = cl2.invoke(
            "capacity:perception:text.demo",
            {raw_ds().iri: "hello"},
            session=session,
        )
        assert res.success
        assert res.outputs[tokens_ds().iri] == "HELLO"
    finally:
        unregister_reactivation_factory("taught")
        persister.delete(user_id)


def test_cold_start_mints_and_reactivates_nothing(falkor_client):
    from mindsos_capacity import CapacityLayer, CATEGORY_PERCEPTION
    from mindsos_knowledge import KnowledgeLayer
    from mindsos_server.local_boot import boot_local
    from mindsos_server.persistence import FalkorDBLocalPersister
    from mindsos_server.session import Session

    persister = FalkorDBLocalPersister(falkor_client)
    kl = KnowledgeLayer.bootstrap()
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    mg, minted, reactivated = boot_local(
        cl, kl, persister, "nobody", session=Session.for_testing("nobody")
    )
    assert minted is True
    assert reactivated == []
