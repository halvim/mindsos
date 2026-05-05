"""Schema state-file migration chain (Phase 05a — P14).

Versions:

* v=1 (Phase 04) — base shape; ``node_types`` + ``edge_types`` only.
* v=2 (Phase 04-v2) — adds optional ``hyperedge_types`` field.

Phase 05a does not bump the schema state-file version. ``MetagraphSchema``
(introduced in 05b) is a separate state-file kind, not a schema bump.
"""

from __future__ import annotations

from typing import Callable, Dict, List

CURRENT_VERSION = 2


def _v1_to_v2(state: Dict) -> Dict:
    """Phase 04 → Phase 04-v2: introduce ``hyperedge_types`` (default ``[]``)."""
    state["hyperedge_types"] = state.get("hyperedge_types") or []
    return state


#: ``MIGRATIONS[i]`` migrates v(i+1) → v(i+2).
MIGRATIONS: List[Callable[[Dict], Dict]] = [
    _v1_to_v2,
]


def migrate(state: Dict) -> Dict:
    """Apply the migration chain forward from ``state["_state_version"]``.

    Mutates and returns ``state``; sets ``_state_version`` to current.
    """
    v = state.get("_state_version")
    if v is None:
        raise ValueError("missing required field '_state_version'")
    if not isinstance(v, int):
        raise ValueError(
            f"_state_version must be int, got {type(v).__name__}={v!r}"
        )
    if v > CURRENT_VERSION:
        raise ValueError(
            f"has _state_version={v}; this CLI supports v{CURRENT_VERSION}"
        )
    if v < 1:
        raise ValueError(f"_state_version must be >= 1, got {v}")
    while v < CURRENT_VERSION:
        state = MIGRATIONS[v - 1](state)
        v += 1
    state["_state_version"] = CURRENT_VERSION
    return state
