"""MetagraphSchema state-file migration chain (Phase 05b + 05c + 05d).

Versions:

* v=1 (Phase 05b) — initial shape; ``intergraph_edge_types`` array;
  ``strict: bool`` flag.
* v=2 (Phase 05c — P14-A smaller-items fold) — adds
  ``intergraph_hyperedge_types`` array (default empty on migration).
* v=3 (Phase 05d — round-7 P31 A; only state-file bump that ships in
  05d) — adds ``meta_edge_types`` + ``meta_hyperedge_types`` arrays
  (defaults empty). The metagraph state file stays at v=3 (no
  fingerprint-based consent mechanism per round-7 P31 A).

Subsequent phases append migration steps; never edit a prior step.
"""

from __future__ import annotations

from typing import Callable, Dict, List

CURRENT_VERSION = 3


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


def _v2_to_v3(state: Dict) -> Dict:
    """Phase 05c → Phase 05d: introduce ``meta_edge_types`` + ``meta_hyperedge_types``.

    Single-step migration mirroring the 05b/05c additive pattern. Default
    empty lists on migration; existing 05b/05c metagraph-schema state
    files have no MetaEdgeType / MetaHyperEdgeType declarations to carry
    over. Idempotent on re-migration. Defensive null→[] normalization
    handles malformed inputs (e.g., ``"meta_edge_types": null``) — the
    field is normalized to empty list so downstream rehydration is
    unconditionally list-shaped.
    """
    state["meta_edge_types"] = state.get("meta_edge_types") or []
    state["meta_hyperedge_types"] = (
        state.get("meta_hyperedge_types") or []
    )
    return state


#: ``MIGRATIONS[i]`` migrates v(i+1) → v(i+2).
MIGRATIONS: List[Callable[[Dict], Dict]] = [
    _v1_to_v2,
    _v2_to_v3,
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
