"""R4-11 A + RR-5 B — MetagraphLoader constructor + load_metagraph dual."""

from __future__ import annotations

import inspect

from mindsos_core.persistence import InMemoryClient
from mindsos_core.reconstruction import MetagraphLoader, load_metagraph


def test_metagraph_loader_minimal_constructor() -> None:
    """R4-11 A — MetagraphLoader(client) takes only the client."""
    c = InMemoryClient()
    loader = MetagraphLoader(c)
    assert loader is not None
    # Per-call kwargs live on .load and .refresh.
    sig = inspect.signature(loader.load)
    params = list(sig.parameters.keys())
    assert "metagraph_id" in params
    assert "batch_size" in params
    assert "identity" in params
    assert "schema" in params


def test_load_metagraph_function_dual_to_class() -> None:
    """RR-5 B — module function ships alongside class form."""
    sig = inspect.signature(load_metagraph)
    params = list(sig.parameters.keys())
    assert params[0] == "client"
    assert params[1] == "metagraph_id"
    assert "batch_size" in sig.parameters
    assert "identity" in sig.parameters
    assert "schema" in sig.parameters


def test_class_and_function_share_implementation() -> None:
    """load_metagraph(c, m, ...) returns MetagraphLoader(c).load(m, ...)."""
    # Without a working DB we just verify the function calls into the
    # class — both should fail identically on anchor lookup.
    from mindsos_core.exceptions import PersistenceError
    import pytest

    c1 = InMemoryClient()
    c1.script([])  # WAL recover (no replayer) — empty.
    c1.script([])  # Empty anchor.

    c2 = InMemoryClient()
    c2.script([])  # WAL recover.
    c2.script([])  # Empty anchor.

    with pytest.raises(PersistenceError, match="No :Metagraph row"):
        load_metagraph(c1, "ghost-mid")
    with pytest.raises(PersistenceError, match="No :Metagraph row"):
        MetagraphLoader(c2).load("ghost-mid")
