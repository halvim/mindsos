"""MetagraphSchema state-file migration chain (Phase 05b — P14 / NEW kind).

Versions:

* v=1 (Phase 05b) — initial shape; ``intergraph_edge_types`` array;
  ``strict: bool`` flag.

Future bumps (deferred to later phases per CASC-1):

* v=2 (Phase 05c) — adds ``meta_edge_types`` + ``meta_hyperedge_types``
  + ``intergraph_hyperedge_types`` arrays (3 new vocabularies in one
  bump per Pushback 1-C scope split).

The migration list is empty in 05b (no prior versions). Subsequent phases
append migration steps in their own row.
"""

from __future__ import annotations

from typing import Callable, Dict, List

CURRENT_VERSION = 1

#: ``MIGRATIONS[i]`` migrates v(i+1) → v(i+2). Empty in 05b.
MIGRATIONS: List[Callable[[Dict], Dict]] = []


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
