"""RPB-1 — replayer bodies bypass public setters; emit cypher via builders."""

from __future__ import annotations

from mindsos_core.persistence import InMemoryClient
from mindsos_core.persistence.bootstrap import register_all_l1_replayers


def _setup() -> InMemoryClient:
    client = InMemoryClient()
    register_all_l1_replayers(client)
    return client


def test_element_deprecate_replay_emits_set_cypher() -> None:
    client = _setup()
    client._replayers["element_deprecate"]({
        "element_id": "e1", "element_kind": "edge",
        "scope_id": "g1", "at": "2026-05-15T12:00:00+00:00",
    })
    q = client.calls[-1][0]
    assert "SET e.deprecated_at = $at" in q


def test_element_undeprecate_replay_emits_null_cypher() -> None:
    client = _setup()
    client._replayers["element_undeprecate"]({
        "element_id": "e1", "element_kind": "hyperedge", "scope_id": "g1",
    })
    q = client.calls[-1][0]
    assert "SET h.deprecated_at = NULL" in q


def test_element_dispute_metaedge_replay() -> None:
    client = _setup()
    client._replayers["element_dispute"]({
        "element_id": "me1", "element_kind": "metaedge",
        "scope_id": "mg1", "at": "2026-05-15T12:00:00+00:00",
    })
    q = client.calls[-1][0]
    assert "metagraph_id" in q
    assert "SET e.disputed_at = $at" in q


def test_xref_mark_stale_replay() -> None:
    client = _setup()
    client._replayers["xref_mark_stale"]({"xref_id": "x1"})
    q = client.calls[-1][0]
    assert ":XRef" in q
    assert "SET x.target_stale = true" in q


def test_xref_unmark_stale_replay() -> None:
    client = _setup()
    client._replayers["xref_unmark_stale"]({"xref_id": "x1"})
    q = client.calls[-1][0]
    assert "SET x.target_stale = false" in q


def test_xref_deprecate_replay() -> None:
    client = _setup()
    client._replayers["xref_deprecate"]({"xref_id": "x1", "at": "2026-05-15T12:00:00+00:00"})
    q = client.calls[-1][0]
    assert "SET x.deprecated_at = $at" in q


def test_xref_undeprecate_replay() -> None:
    client = _setup()
    client._replayers["xref_undeprecate"]({"xref_id": "x1"})
    q = client.calls[-1][0]
    assert "SET x.deprecated_at = NULL" in q
