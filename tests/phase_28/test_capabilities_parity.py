"""Phase 28 — CAN_WRITE_GLOBAL parity vs mindsos_server.capabilities (ADR-0078)."""

from __future__ import annotations

from mindsos_capacity import CAN_WRITE_GLOBAL as L3_CAN_WRITE_GLOBAL
from mindsos_server.capabilities import CAN_WRITE_GLOBAL as SERVER_CAN_WRITE_GLOBAL


def test_can_write_global_matches_server():
    assert L3_CAN_WRITE_GLOBAL == SERVER_CAN_WRITE_GLOBAL, (
        f"L3 CAN_WRITE_GLOBAL drift: L3={L3_CAN_WRITE_GLOBAL!r} vs "
        f"server={SERVER_CAN_WRITE_GLOBAL!r}. Update "
        "mindsos_capacity/capabilities.py."
    )
    assert L3_CAN_WRITE_GLOBAL == "CAN_WRITE_GLOBAL"
