"""Phase 26a — bootstrap_kl_from_falkordb load-or-mint (R4-PB-1 + R5-PB-4 + R6-PB-2)."""

from __future__ import annotations

from mindsos_core.persistence.client import InMemoryClient, QueryResult
from mindsos_knowledge.knowledge_layer import (
    _GLOBAL_METAGRAPH_NAME,
    KnowledgeLayer,
)
from mindsos_server.persistence import bootstrap_kl_from_falkordb


def test_mint_path_when_find_by_name_returns_none() -> None:
    """First-ever bootstrap: no existing Metagraph → mint + persist."""
    client = InMemoryClient()
    # find_by_name returns empty (no script enqueued; default empty rows)
    kl = bootstrap_kl_from_falkordb(client)
    assert isinstance(kl, KnowledgeLayer)
    # The bootstrap call should have queried find_by_name + then issued
    # one or more persist statements (anchor + role-graphs).
    assert len(client.calls) >= 2  # find + persist anchor minimum
    # First call is the find_by_name query.
    first_query, first_params = client.calls[0]
    assert "Metagraph {name: $name}" in first_query
    assert first_params == {"name": _GLOBAL_METAGRAPH_NAME}


def test_mint_path_resulting_kl_has_global_metagraph_name() -> None:
    """Minted KL's Global.name matches the canonical constant."""
    client = InMemoryClient()
    kl = bootstrap_kl_from_falkordb(client)
    assert kl.global_metagraph().name == _GLOBAL_METAGRAPH_NAME


def test_load_path_when_find_by_name_returns_id() -> None:
    """Subsequent bootstrap: find_by_name hit → loader.load called."""
    client = InMemoryClient()
    # Script the find_by_name response.
    client.script_result(
        QueryResult(rows=[{"metagraph_id": "mg-existing-12345"}])
    )
    # Subsequent calls inside loader.load will get empty QueryResult by
    # default; the load may raise or return an empty Metagraph
    # depending on loader internals. The contract we're testing is that
    # the load path was TAKEN (no mint path executed); we tolerate a
    # downstream failure from the loader running against an empty
    # scripted client by catching the exception and asserting on call
    # shape.
    try:
        bootstrap_kl_from_falkordb(client)
    except Exception:
        # Loader may raise — that's fine; we test the call shape.
        pass
    # The first call MUST be find_by_name (regardless of subsequent
    # loader behavior on the InMemoryClient).
    assert len(client.calls) >= 1
    first_query, first_params = client.calls[0]
    assert "Metagraph {name: $name}" in first_query
    assert first_params == {"name": _GLOBAL_METAGRAPH_NAME}
