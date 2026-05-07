"""MetagraphSchema state-file migration chain (Phase 05b + 05c — P14 / NEW kind).

Versions:

* v=1 (Phase 05b) — initial shape; ``intergraph_edge_types`` array;
  ``strict: bool`` flag.
* v=2 (Phase 05c — P14-A smaller-items fold) — adds
  ``intergraph_hyperedge_types`` array (default empty on migration).
  Per 05c P1-B scope split, ``meta_edge_types`` + ``meta_hyperedge_types``
  are NOT shipped in 05c — they defer to Phase 05d's v=2→v=3 bump.

Future bumps (deferred to later phases per CASC-1):

* v=3 (Phase 05d — locked stub) — adds ``meta_edge_types`` +
  ``meta_hyperedge_types`` arrays (defaults empty).

Subsequent phases append migration steps; never edit a prior step.
"""

from __future__ import annotations

from typing import Callable, Dict, List

CURRENT_VERSION = 2


def _v1_to_v2(state: Dict) -> Dict:
    """Phase 05b → Phase 05c: introduce ``intergraph_hyperedge_types``.

    Single-step migration mirroring the 05b ``_v1_to_v2`` pattern on the
    metagraph state file. Default empty list on migration; existing 05b
    metagraph-schema state files have no IntergraphHyperEdgeType
    declarations to carry over. Idempotent on re-migration.
    """
    state["intergraph_hyperedge_types"] = (
        state.get("intergraph_hyperedge_types") or []
    )
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
