"""Phase 28 — B-26b-T5 §am5 Cypher closure sentinel."""

from __future__ import annotations

from mindsos_admin.promotion import _PROPOSE_MERGE_CYPHER
from mindsos_server.release import _RELEASE_MERGE_CYPHER


def test_release_merge_cypher_contains_in_graph_clause():
    assert ":IN_GRAPH" in _RELEASE_MERGE_CYPHER, (
        "_RELEASE_MERGE_CYPHER must MERGE :IN_GRAPH per ADR-0118 "
        "§amendment-5 (B-26b-T5 closure at Phase 28)."
    )
    assert "MATCH (g:Graph" in _RELEASE_MERGE_CYPHER


def test_propose_merge_cypher_contains_in_graph_clause():
    assert ":IN_GRAPH" in _PROPOSE_MERGE_CYPHER, (
        "_PROPOSE_MERGE_CYPHER must MERGE :IN_GRAPH per ADR-0118 "
        "§amendment-5 (B-26b-T5 closure at Phase 28)."
    )
    assert "MATCH (g:Graph" in _PROPOSE_MERGE_CYPHER
