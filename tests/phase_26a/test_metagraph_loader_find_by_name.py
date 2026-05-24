"""Phase 26a — MetagraphLoader.find_by_name (R5-PB-4 (a))."""

from __future__ import annotations

from mindsos_core.persistence.client import InMemoryClient, QueryResult
from mindsos_core.reconstruction.metagraph_loader import MetagraphLoader


def test_find_by_name_returns_metagraph_id_on_hit() -> None:
    client = InMemoryClient()
    client.script_result(
        QueryResult(rows=[{"metagraph_id": "mg-uuid-12345"}])
    )
    loader = MetagraphLoader(client)
    result = loader.find_by_name("mindsos_global")
    assert result == "mg-uuid-12345"


def test_find_by_name_returns_none_on_miss() -> None:
    client = InMemoryClient()
    # No script call → run_query returns empty QueryResult by default
    loader = MetagraphLoader(client)
    result = loader.find_by_name("mindsos_global")
    assert result is None


def test_find_by_name_binds_name_parameter() -> None:
    """Query binds the name as ``$name`` (Cypher parameter)."""
    client = InMemoryClient()
    loader = MetagraphLoader(client)
    loader.find_by_name("mindsos_global")
    assert len(client.calls) == 1
    query, params = client.calls[0]
    assert "MATCH (m:Metagraph {name: $name})" in query
    assert params == {"name": "mindsos_global"}


def test_find_by_name_query_uses_limit_1() -> None:
    """Lookup is single-row; query asserts the LIMIT clause."""
    client = InMemoryClient()
    loader = MetagraphLoader(client)
    loader.find_by_name("any")
    query, _ = client.calls[0]
    assert "LIMIT 1" in query
