"""InstanceRepository unit tests + attach_registry observer wiring (P11 A + M9)."""

from __future__ import annotations

from mindsos_core.models.graph import Graph
from mindsos_core.models.metagraph import Metagraph
from mindsos_core.persistence import InMemoryClient, MetagraphRepository
from mindsos_instances import attach_registry
from mindsos_instances.models.element_instance import (
    CompositeInstance,
    NodeInstance,
)
from mindsos_instances.persistence import InstanceRepository


def _build_mg_with_instances() -> tuple[Metagraph, NodeInstance, CompositeInstance]:
    mg = Metagraph(name="mg")
    g = Graph(name="g")
    mg.add_graph(g)
    n = g.add_node("v", "T")
    registry = attach_registry(mg)
    ni = NodeInstance(metagraph_id=mg.metagraph_id, template_id=n.node_id, _registry=registry)
    registry.add(ni)
    ci = CompositeInstance(metagraph_id=mg.metagraph_id, _registry=registry)
    ci.add_member(ni, _registry=registry)
    registry.add(ci)
    return mg, ni, ci


def test_version_default_on_element_and_composite() -> None:
    """P11 A — _version: int = 1 on both subclasses."""
    mg, ni, ci = _build_mg_with_instances()
    assert ni._version == 1
    assert ci._version == 1


def test_persist_all_routes_via_isinstance() -> None:
    """persist_all dispatches NodeInstance → element builder, CompositeInstance → composite."""
    mg, ni, ci = _build_mg_with_instances()
    c = InMemoryClient()
    repo = InstanceRepository(c)
    repo.persist_all(mg.element_registry)
    queries = [q for q, _ in c.calls]
    assert any("ElementInstance" in q for q in queries)
    assert any("CompositeInstance" in q for q in queries)


def test_attach_registry_idempotent_no_double_subscribe() -> None:
    """Re-attach does not double-subscribe the persist observer."""
    mg = Metagraph(name="mg")
    r1 = attach_registry(mg)
    pre = len(mg._persist_observers)
    r2 = attach_registry(mg)
    r3 = attach_registry(mg)
    assert r1 is r2 is r3
    assert len(mg._persist_observers) == pre


def test_end_to_end_persist_fires_instance_writes() -> None:
    """M9 + P96 A — MetagraphRepository.persist triggers InstanceRepository via observer."""
    mg, ni, ci = _build_mg_with_instances()
    c = InMemoryClient()
    mrepo = MetagraphRepository(c)
    mrepo.persist(mg)
    queries = [q for q, _ in c.calls]
    assert any("ElementInstance" in q for q in queries)
    assert any("CompositeInstance" in q for q in queries)


def test_observer_skipped_when_persist_client_unset() -> None:
    """attach_registry's persist hook no-ops when no client attached."""
    mg = Metagraph(name="mg")
    g = Graph(name="g")
    mg.add_graph(g)
    n = g.add_node("v", "T")
    registry = attach_registry(mg)
    ni = NodeInstance(metagraph_id=mg.metagraph_id, template_id=n.node_id, _registry=registry)
    registry.add(ni)
    # Fire the observer directly without setting _persist_client.
    from mindsos_core._observers import _dispatch_after_persist
    _dispatch_after_persist(mg._persist_observers, mg)
    # No exception raised; the persist hook is a no-op when client absent.


def test_subgraph_instance_member_ids_passed_through() -> None:
    """P13 B — SubGraphInstance carries node_ids selection."""
    from mindsos_instances.models.element_instance import SubGraphInstance

    mg = Metagraph(name="mg")
    g = Graph(name="g")
    mg.add_graph(g)
    n1 = g.add_node("v1", "T")
    n2 = g.add_node("v2", "T")
    registry = attach_registry(mg)
    si = SubGraphInstance(
        metagraph_id=mg.metagraph_id,
        template_id=g.graph_id,
        overrides={"node_ids": frozenset([n1.node_id, n2.node_id])},
        _registry=registry,
    )
    registry.add(si)

    c = InMemoryClient()
    InstanceRepository(c).persist_all(registry)
    # SubGraphInstance kind label is :SubGraphInstance per builder.
    queries = [q for q, _ in c.calls]
    assert any(":ElementInstance:SubGraphInstance" in q for q in queries)
