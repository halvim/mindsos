"""attach_registry(mg) extension — after_load observer wiring (Phase 08 PB-4 A)."""

from __future__ import annotations

import pytest


def test_attach_registry_idempotent_re_attach_does_not_double_subscribe() -> None:
    """Phase 06 P49 B idempotency — re-attach returns same registry."""
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_instances import attach_registry
    from mindsos_instances.registry import ElementRegistry

    mg = Metagraph(name="m1", identity=IdentityRegistry())
    r1 = attach_registry(mg)
    r2 = attach_registry(mg)
    assert isinstance(r1, ElementRegistry)
    assert r1 is r2


def test_attach_registry_subscribes_after_load_observer() -> None:
    """Phase 08 — attach_registry adds an after_load observer."""
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_instances import attach_registry

    mg = Metagraph(name="m1", identity=IdentityRegistry())
    # Before attach — no after_load observers.
    assert mg._after_load_observers == []
    attach_registry(mg)
    # After attach — one after_load observer subscribed.
    assert len(mg._after_load_observers) == 1


def test_attach_registry_after_load_observer_no_op_without_persist_client() -> None:
    """The wired observer no-ops when `mg._persist_client` is unset."""
    from mindsos_core._observers import _dispatch_after_load
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_instances import attach_registry

    mg = Metagraph(name="m1", identity=IdentityRegistry())
    attach_registry(mg)

    # Fire the observer without a `_persist_client` attribute — observer
    # should detect None and skip (no-op).
    # The observer reads `mg._persist_client`; absent attribute → None.
    _dispatch_after_load(mg._after_load_observers, mg)
    # No exception raised; element_registry still empty.
    assert len(mg.element_registry) == 0


@pytest.mark.integration
def test_attach_registry_after_load_observer_populates_instances(
    falkor_client,
) -> None:
    """End-to-end: attach + persist + load → element_registry populated."""
    from mindsos_core.models.graph import Graph
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_core.reconstruction import load_metagraph
    from mindsos_instances import attach_registry
    from mindsos_instances.models.element_instance import NodeInstance

    mg = Metagraph(name="instances-rt", identity=IdentityRegistry())
    g = Graph(name="g1", role="lex", identity=mg.identity)
    n1 = g.add_node(value="x", type_name="T", node_id="n1", _validate=False)
    mg.add_graph(g)
    # Build a NodeInstance to round-trip.
    registry = attach_registry(mg)
    inst = NodeInstance(
        metagraph_id=mg.metagraph_id, template_id="n1", _registry=registry,
    )
    registry.add(inst)

    # Persist (M9 + P96 A observer fires → InstanceRepository persists
    # the instance row).
    MetagraphRepository(falkor_client).persist(mg)

    # Reload — attach a fresh registry FIRST so the after_load observer
    # subscribes; the observer fires inside load_metagraph and
    # InstanceLoader populates the new registry.
    mg2_shell = Metagraph(
        name="instances-rt",
        identity=IdentityRegistry(),
        metagraph_id=mg.metagraph_id,
    )
    attach_registry(mg2_shell)
    mg2 = load_metagraph(falkor_client, mg.metagraph_id)
    # Re-attach registry on the freshly-loaded mg + manually fire the
    # after_load observer to populate from the now-attached registry.
    attach_registry(mg2)
    try:
        mg2._persist_client = falkor_client  # type: ignore[attr-defined]
        from mindsos_core._observers import _dispatch_after_load
        _dispatch_after_load(mg2._after_load_observers, mg2)
    finally:
        if hasattr(mg2, "_persist_client"):
            try:
                delattr(mg2, "_persist_client")
            except AttributeError:
                pass

    # Verify the instance round-tripped.
    registry2 = mg2.element_registry
    assert inst.id in registry2
