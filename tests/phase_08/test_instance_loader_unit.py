"""Unit assertions for InstanceLoader Cypher emit shape (RPB-13 B)."""

from __future__ import annotations

from mindsos_core.persistence import InMemoryClient


def test_fetch_element_instances_query_filters_metagraph_id() -> None:
    """The element-instance fetch matches :ElementInstance + metagraph_id."""
    from mindsos_instances.reconstruction.instance_loader import InstanceLoader

    c = InMemoryClient()
    loader = InstanceLoader(c)

    # Drive the read directly; no metagraph object needed for query shape.
    c.script([])  # No rows.
    loader._fetch_element_instances("mid-X")
    q, p = c.calls[-1]
    assert "MATCH (i:ElementInstance" in q
    assert "metagraph_id: $mid" in q
    assert p == {"mid": "mid-X"}


def test_fetch_composite_instances_query_filters_metagraph_id() -> None:
    from mindsos_instances.reconstruction.instance_loader import InstanceLoader

    c = InMemoryClient()
    loader = InstanceLoader(c)
    c.script([])
    loader._fetch_composite_instances("mid-X")
    q, p = c.calls[-1]
    assert "MATCH (c:CompositeInstance" in q
    assert "metagraph_id: $mid" in q


def test_fetch_composite_members_traverses_has_member_rel() -> None:
    from mindsos_instances.reconstruction.instance_loader import InstanceLoader

    c = InMemoryClient()
    loader = InstanceLoader(c)
    c.script([])
    loader._fetch_composite_members("comp-1")
    q, p = c.calls[-1]
    assert "HAS_MEMBER" in q
    assert "CompositeInstance {id: $cid}" in q
    assert p == {"cid": "comp-1"}
