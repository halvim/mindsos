"""Integration — InstanceLoader two-pass + RR-3 A override-allow-list + RR-4 B orphan."""

from __future__ import annotations

import logging

import pytest

pytestmark = pytest.mark.integration


def test_instance_loader_two_pass_element_then_composite(falkor_client) -> None:
    """Pass 1 element instances → Pass 2 composites populate via registry.add()."""
    from mindsos_core.models.graph import Graph
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_core.reconstruction import load_metagraph
    from mindsos_instances import attach_registry
    from mindsos_instances.models.element_instance import (
        CompositeInstance,
        NodeInstance,
    )

    mg = Metagraph(name="two-pass", identity=IdentityRegistry())
    g = Graph(name="g1", role="lex", identity=mg.identity)
    g.add_node(value="x", type_name="T", node_id="n1", _validate=False)
    g.add_node(value="y", type_name="T", node_id="n2", _validate=False)
    mg.add_graph(g)
    registry = attach_registry(mg)
    inst1 = NodeInstance(
        metagraph_id=mg.metagraph_id, template_id="n1", _registry=registry,
    )
    registry.add(inst1)
    inst2 = NodeInstance(
        metagraph_id=mg.metagraph_id, template_id="n2", _registry=registry,
    )
    registry.add(inst2)
    comp = CompositeInstance(
        metagraph_id=mg.metagraph_id, _registry=registry,
    )
    comp.add_member(inst1)
    comp.add_member(inst2)
    registry.add(comp)

    MetagraphRepository(falkor_client).persist(mg)

    # Reload — observer fires InstanceLoader, both element + composite
    # land in the new registry.
    mg2 = load_metagraph(falkor_client, mg.metagraph_id)
    registry2 = attach_registry(mg2)
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

    assert inst1.id in registry2
    assert inst2.id in registry2
    assert comp.id in registry2


def test_instance_loader_orphan_template_logs_and_skips(
    falkor_client, caplog
) -> None:
    """RR-4 B — orphan template at load: log WARNING + skip."""
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_core.reconstruction import load_metagraph
    from mindsos_instances import attach_registry

    mg = Metagraph(name="orphan-test", identity=IdentityRegistry())
    MetagraphRepository(falkor_client).persist(mg)

    # Seed a substrate-side orphan ElementInstance row whose
    # source_id refers to a node that does NOT exist in mg.graphs.
    falkor_client.run_query(
        "CREATE (i:ElementInstance:NodeInstance {"
        "  id: 'orphan-i', kind: 'node', metagraph_id: $mid, "
        "  source_id: 'missing-node', source_graph_id: 'missing-graph', "
        "  label: 'orphan' "
        "}) ",
        {"mid": mg.metagraph_id},
    )

    caplog.set_level(
        logging.WARNING,
        logger="mindsos_instances.reconstruction.instance_loader",
    )
    mg2 = load_metagraph(falkor_client, mg.metagraph_id)
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

    # Orphan instance NOT added; warning logged.
    assert "orphan-i" not in mg2.element_registry
    assert any(
        "orphan instance" in rec.message.lower() for rec in caplog.records
    )
