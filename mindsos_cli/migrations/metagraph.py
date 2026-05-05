"""Metagraph state-file migration chain (Phase 05a — P14).

Versions:

* v=1 (Phase 05a) — initial shape; ``contained_graphs``, ``metaedges``,
  ``metahyperedges``, ``properties``.

Future bumps (deferred to later phases per CASC-1):

* v=2 (Phase 05b) — ``intergraph_edges`` array + optional ``schema_name``.
* v=3 (Phase 05c) — ``intergraph_hyperedges`` array.
* v=4 (Phase 10) — soft-delete fields on metaedges/metahyperedges
  (ADR-0133 substrate landed uniformly across all 4 edge variants).

The migration list is empty in 05a (no prior versions). Subsequent phases
append migration steps in their own row.
"""

from __future__ import annotations

from typing import Callable, Dict, List

CURRENT_VERSION = 1

#: ``MIGRATIONS[i]`` migrates v(i+1) → v(i+2). Empty in 05a.
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
