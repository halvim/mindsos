"""Graph state-file migration chain (Phase 05a — P14).

Versions:

* v=1 (Phase 03) — base shape; no ``schema_name``; no hyperedge ``type_name``;
  no ``metagraph_name``.
* v=2 (Phase 04) — adds optional ``schema_name`` field.
* v=3 (Phase 04-v2) — adds required ``type_name`` per hyperedge entry
  (legacy entries populated with ``"UNSPECIFIED"`` sentinel — SENT-1 lock).
* v=4 (Phase 05a) — adds optional ``metagraph_name`` back-pointer field.

Each migration step is a pure dict→dict function. Steps are idempotent if
the field is already present (defensive read of ``state.get(...)``).

Loaders in ``mindsos_cli.state`` call :func:`migrate` after reading raw JSON
and before handing the dict to ``_state_to_graph``.
"""

from __future__ import annotations

from typing import Callable, Dict, List

CURRENT_VERSION = 4


def _v1_to_v2(state: Dict) -> Dict:
    """Phase 03 → Phase 04: introduce ``schema_name`` (default ``None``)."""
    state["schema_name"] = state.get("schema_name")  # default None
    return state


def _v2_to_v3(state: Dict) -> Dict:
    """Phase 04 → Phase 04-v2: hyperedges receive ``type_name="UNSPECIFIED"``.

    SENT-1 sentinel literal (uppercase) satisfies ADR-0021 cypher rel-type
    regex. Tester recovery: ``mindsos graph update-hyperedge-type`` (UHT-1).
    """
    for h in state.get("hyperedges", []) or []:
        if not h.get("type_name"):
            h["type_name"] = "UNSPECIFIED"
    return state


def _v3_to_v4(state: Dict) -> Dict:
    """Phase 04-v2 → Phase 05a: introduce ``metagraph_name`` (default ``None``).

    The back-pointer is populated by ``mindsos metagraph add-graph`` when the
    graph joins a metagraph; ``None`` for standalone graphs.
    """
    state["metagraph_name"] = state.get("metagraph_name")  # default None
    return state


#: ``MIGRATIONS[i]`` migrates v(i+1) → v(i+2).
MIGRATIONS: List[Callable[[Dict], Dict]] = [
    _v1_to_v2,
    _v2_to_v3,
    _v3_to_v4,
]


def migrate(state: Dict) -> Dict:
    """Apply the migration chain forward from ``state["_state_version"]``.

    Args:
        state: Raw state-file dict. Must carry ``_state_version`` (int).

    Returns:
        The same dict, mutated in place, with ``_state_version`` set to
        :data:`CURRENT_VERSION`.

    Raises:
        ValueError: missing or non-int ``_state_version``, or version > current.
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
