"""Unit tests for AsyncClient + ThreadPoolAsyncClient (Phase 07)."""

from __future__ import annotations

import asyncio

import pytest

from mindsos_core.persistence import (
    AsyncClient,
    InMemoryClient,
    ThreadPoolAsyncClient,
)


def test_threadpool_implements_async_protocol() -> None:
    c = ThreadPoolAsyncClient(InMemoryClient())
    assert isinstance(c, AsyncClient)


def test_async_run_query_forwards_to_sync() -> None:
    sync = InMemoryClient()
    c = ThreadPoolAsyncClient(sync)
    asyncio.run(c.run_query("FOO", {"a": 1}))
    assert sync.calls == [("FOO", {"a": 1})]


def test_async_run_batch_forwards_to_sync() -> None:
    sync = InMemoryClient()
    c = ThreadPoolAsyncClient(sync)
    asyncio.run(c.run_batch([("A", {}), ("B", {})]))
    assert sync.calls == [("A", {}), ("B", {})]


def test_async_close_forwards_to_sync() -> None:
    sync = InMemoryClient()
    c = ThreadPoolAsyncClient(sync)
    asyncio.run(c.close())
    assert sync.closed is True


def test_async_propagates_exceptions() -> None:
    """Exceptions raised by the sync client surface through to_thread."""
    class BadClient:
        def run_query(self, q, p=None):
            raise RuntimeError("boom")
        def run_batch(self, s):
            raise RuntimeError("boom-batch")
        def close(self):
            pass

    c = ThreadPoolAsyncClient(BadClient())  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(c.run_query("Q"))
    with pytest.raises(RuntimeError, match="boom-batch"):
        asyncio.run(c.run_batch([("Q", {})]))
