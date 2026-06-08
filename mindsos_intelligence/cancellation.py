"""Cooperative cancellation framework (ADR-0167).

Concrete :class:`CancelToken` is L4 substrate; it satisfies the L3
``mindsos_capacity.context.CancelToken`` Protocol (``is_set`` +
``request_cancel``). The read-only ``CancelTokenView`` stays L3 (body
side) and is re-exported here for L4 ergonomics — not redefined.
"""

from __future__ import annotations

import threading

from mindsos_capacity.context import CancelTokenView


class CancelToken:
    """Settable ``threading.Event``-backed token held by the L4 substrate."""

    __slots__ = ("_event",)

    def __init__(self) -> None:
        self._event = threading.Event()

    def is_set(self) -> bool:
        return self._event.is_set()

    def request_cancel(self) -> None:
        self._event.set()

    def view(self) -> CancelTokenView:
        """Read-only view handed to a capacity body (poll-only)."""
        return CancelTokenView(self)


__all__ = ["CancelToken", "CancelTokenView"]
