"""
``InMemoryLocalPersister.fail_save_for`` raises
:class:`FlushFailedError`.

PB-33 fault-injection hook test. The hook is the only way to exercise
the future logout-flush + promotion-flush error path before its first
live consumer exists.
"""

from __future__ import annotations

import pytest

from mindsos_core import Metagraph

from mindsos_server.errors import FlushFailedError
from mindsos_server.persistence import InMemoryLocalPersister


def test_save_raises_when_user_id_in_fail_set() -> None:
    p = InMemoryLocalPersister()
    p.fail_save_for.add("alice")
    mg = Metagraph(name="local_knowledge:alice")
    with pytest.raises(FlushFailedError) as exc_info:
        p.save("alice", mg)
    assert exc_info.value.user_id == "alice"


def test_save_does_not_mutate_store_on_failure() -> None:
    p = InMemoryLocalPersister()
    p.fail_save_for.add("alice")
    mg = Metagraph(name="local_knowledge:alice")
    with pytest.raises(FlushFailedError):
        p.save("alice", mg)
    assert p.load("alice") is None


def test_save_succeeds_for_user_not_in_fail_set() -> None:
    p = InMemoryLocalPersister()
    p.fail_save_for.add("alice")
    mg_bob = Metagraph(name="local_knowledge:bob")
    p.save("bob", mg_bob)
    assert p.load("bob") is mg_bob
