"""Client wrapper that raises on the N-th call (Phase 07 — P20 B → P41 B).

Used to exercise the WAL "whole-batch refused" path (P82 A rename).
Per P41 B — the wrapper sits at the Client surface, NOT inside
``run_batch``. N counts whole ``run_batch`` invocations.

Per P82 A — the test that consumes this wrapper is named
``test_whole_batch_refused`` (NOT ``test_mid_batch_crash``). Real
mid-batch fidelity testing requires a subprocess-crash fixture
(deferred to Phase 11).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from mindsos_core.exceptions import PersistenceError
from mindsos_core.persistence.client import Client, QueryResult


class RaisesOnNthCall:
    """Wrap a real :class:`Client` and raise on the N-th call.

    Counts ``run_query`` + ``run_batch`` calls combined. When the
    incremented counter equals ``n``, raises
    :class:`PersistenceError` instead of forwarding to the inner
    client. Earlier calls forward; later calls also raise (once
    triggered, the wrapper stays in error state until reset).
    """

    def __init__(self, real: Client, *, n: int) -> None:
        if n < 1:
            raise ValueError("n must be ≥ 1")
        self._real = real
        self._n = n
        self._count = 0

    def reset(self) -> None:
        """Reset the call counter to 0 (re-arm the wrapper)."""
        self._count = 0

    @property
    def count(self) -> int:
        return self._count

    def _tick(self) -> None:
        self._count += 1
        if self._count >= self._n:
            raise PersistenceError(
                f"RaisesOnNthCall: triggered on call #{self._count} (n={self._n})"
            )

    def run_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        self._tick()
        return self._real.run_query(query, params)

    def run_batch(
        self, statements: Sequence[Tuple[str, Dict[str, Any]]]
    ) -> List[QueryResult]:
        self._tick()
        return self._real.run_batch(statements)

    def close(self) -> None:
        self._real.close()
