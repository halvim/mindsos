"""tests/_shared/raises_on_nth_call.py contract tests."""

from __future__ import annotations

import pytest

from mindsos_core.exceptions import PersistenceError
from mindsos_core.persistence import InMemoryClient
from tests._shared.raises_on_nth_call import RaisesOnNthCall


def test_invalid_n_rejected() -> None:
    with pytest.raises(ValueError):
        RaisesOnNthCall(InMemoryClient(), n=0)


def test_raises_on_exactly_the_nth_call() -> None:
    real = InMemoryClient()
    real.script([{"a": 1}])  # only the 1st call gets a scripted result.
    wrap = RaisesOnNthCall(real, n=3)
    wrap.run_query("A")
    wrap.run_query("B")
    with pytest.raises(PersistenceError):
        wrap.run_query("C")


def test_run_batch_counts_as_one_tick() -> None:
    """P41 B — wrapper at Client surface; N counts whole run_batch events."""
    real = InMemoryClient()
    wrap = RaisesOnNthCall(real, n=1)
    with pytest.raises(PersistenceError):
        wrap.run_batch([("Q", {})])


def test_reset_re_arms_the_wrapper() -> None:
    real = InMemoryClient()
    wrap = RaisesOnNthCall(real, n=1)
    with pytest.raises(PersistenceError):
        wrap.run_query("Q")
    wrap.reset()
    assert wrap.count == 0


def test_close_forwards_to_real() -> None:
    real = InMemoryClient()
    wrap = RaisesOnNthCall(real, n=99)
    wrap.close()
    assert real.closed is True
