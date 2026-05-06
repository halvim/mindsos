"""Metagraph state-file migration chain (Phase 05a + Phase 05b — P14).

Versions:

* v=1 (Phase 05a) — initial shape; ``contained_graphs``, ``metaedges``,
  ``metahyperedges``, ``properties``.
* v=2 (Phase 05b — Pushback 18-A) — adds ``intergraph_edges`` array and
  ``schema_name: str | null`` reference to a MetagraphSchema state file.

Future bumps (deferred to later phases per CASC-1):

* v=3 (Phase 05c) — ``intergraph_hyperedges`` array.
* v=4 (Phase 10) — soft-delete fields on metaedges/metahyperedges/intergraph_edges
  (ADR-0133 substrate landed uniformly across all 4 edge variants).

Subsequent phases append migration steps; never edit a prior step.
"""

from __future__ import annotations

from typing import Callable, Dict, List

CURRENT_VERSION = 2


def _v1_to_v2(state: Dict) -> Dict:
    """Phase 05a → Phase 05b: introduce ``intergraph_edges`` + ``schema_name``.

    Per Pushback 18-A, both new top-level fields default to empty/null
    on migration: existing 05a metagraph state files have no
    intergraph_edges to carry over and no schema attached. The defaults
    are idempotent on re-migration.
    """
    state["intergraph_edges"] = state.get("intergraph_edges") or []
    state["schema_name"] = state.get("schema_name")  # default None
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
