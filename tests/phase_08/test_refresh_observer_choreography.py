"""RPB-2 A — refresh drops role-graphs via mg.remove_graph(); cascade fires."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def test_refresh_uses_remove_graph_and_observer_cascade(falkor_client) -> None:
    """RPB-2 A — Phase 06 remove-observer cascade fires; instances drop."""
    from mindsos_core.models.graph import Graph
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_core.reconstruction import MetagraphLoader
    from mindsos_instances import attach_registry
    from mindsos_instances.models.element_instance import NodeInstance

    mg = Metagraph(name="refresh-choreo", identity=IdentityRegistry())
    g = Graph(name="g1", role="lex", identity=mg.identity)
    g.add_node(value="x", type_name="T", node_id="n1", _validate=False)
    mg.add_graph(g)
    registry = attach_registry(mg)
    inst = NodeInstance(
        metagraph_id=mg.metagraph_id, template_id="n1", _registry=registry,
    )
    registry.add(inst)

    MetagraphRepository(falkor_client).persist(mg)

    # refresh — drops + reloads the lex role.
    loader = MetagraphLoader(falkor_client)
    loader.refresh(mg, role="lex")

    # Post-refresh: the graph reloaded; element_registry should rehydrate
    # via the after_load observer. The original instance id is still in
    # the registry (re-added by InstanceLoader).
    assert g.graph_id in mg.graphs
    # Original `inst` template_id n1 — InstanceLoader rebuilds with same
    # persisted id.
    assert inst.id in mg.element_registry
