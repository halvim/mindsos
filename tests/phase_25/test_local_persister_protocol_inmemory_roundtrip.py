"""
:class:`InMemoryLocalPersister` satisfies :class:`LocalPersister`
Protocol; roundtrip load → save → load → delete invariant.
"""

from __future__ import annotations

from mindsos_core import Metagraph

from mindsos_server.persistence import (
    InMemoryLocalPersister,
    LocalPersister,
)


def test_inmemory_satisfies_local_persister_protocol() -> None:
    """isinstance check against the runtime_checkable Protocol."""
    p = InMemoryLocalPersister()
    assert isinstance(p, LocalPersister)


def test_load_returns_none_when_no_dump_exists() -> None:
    p = InMemoryLocalPersister()
    assert p.load("alice") is None


def test_save_then_load_returns_same_metagraph() -> None:
    p = InMemoryLocalPersister()
    mg = Metagraph(name="local_knowledge:alice")
    p.save("alice", mg)
    assert p.load("alice") is mg


def test_delete_returns_true_when_dump_existed() -> None:
    p = InMemoryLocalPersister()
    mg = Metagraph(name="local_knowledge:alice")
    p.save("alice", mg)
    assert p.delete("alice") is True
    assert p.load("alice") is None


def test_delete_returns_false_when_no_dump() -> None:
    """Idempotent: missing user_id returns False without raising."""
    p = InMemoryLocalPersister()
    assert p.delete("alice") is False
