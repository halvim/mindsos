"""In-memory boot harness — a standalone Local MindsOS instance (no Falkor).

Mirrors bongard_demo/arc1's ephemeral pattern: a fresh `CapacityLayer`
(Global auto-built) + a minimal Local-scoped session. v0 recognition is
read-only and needs no durable persistence; durable L2 (learned calibrate
params / taught references via `boot_brain` + FalkorDBLocalPersister) is v1.
"""

from __future__ import annotations

DEFAULT_USER = "nilm"


class DuckSession:
    """Minimal Local-scoped session (the Local invoke/register path reads only
    ``user_id``; ``.has()`` is the Global-write gate, never hit on Local)."""

    def __init__(self, user_id: str = DEFAULT_USER) -> None:
        self.user_id = user_id
        self.session_id = f"sess-{user_id}"

    def has(self, _cap) -> bool:  # pragma: no cover - never hit on Local path
        return False
