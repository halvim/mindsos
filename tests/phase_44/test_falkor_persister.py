"""Phase 44 PR1.2 — FalkorDBLocalPersister unit tests (InMemoryClient).

Real FalkorDB round-trip (save -> load through a live graph) and the
scoped-delete statement set are gate-verified; these assert Protocol
satisfaction, missing-key semantics, persist delegation, and the
FlushFailedError wrap without a live database.
"""

from __future__ import annotations

import pytest

from mindsos_core import Metagraph
from mindsos_core.exceptions import PersistenceError
from mindsos_core.persistence import InMemoryClient
from mindsos_server.errors import FlushFailedError
from mindsos_server.persistence.local_persister import (
    FalkorDBLocalPersister,
    LocalPersister,
)


def _persister() -> FalkorDBLocalPersister:
    return FalkorDBLocalPersister(InMemoryClient())


def test_satisfies_protocol() -> None:
    assert isinstance(_persister(), LocalPersister)


def test_load_missing_returns_none() -> None:
    assert _persister().load("alice") is None


def test_delete_missing_returns_false() -> None:
    assert _persister().delete("alice") is False


def test_save_delegates_to_persist() -> None:
    client = InMemoryClient()
    persister = FalkorDBLocalPersister(client)
    persister.save("alice", Metagraph(name="local_knowledge:alice"))
    assert client.calls


class _BoomClient:
    def run_query(self, query, params=None):
        raise PersistenceError("boom")

    def run_batch(self, statements):
        raise PersistenceError("boom")

    def close(self) -> None: ...


def test_save_wraps_persistence_error_as_flush_failed() -> None:
    persister = FalkorDBLocalPersister(_BoomClient())
    with pytest.raises(FlushFailedError):
        persister.save("alice", Metagraph(name="local_knowledge:alice"))
