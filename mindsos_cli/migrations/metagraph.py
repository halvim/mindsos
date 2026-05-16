"""Metagraph state-file migration chain (Phase 05a + 05b + 05c + 09 — P14 + P14-A + RR-12).

Versions:

* v=1 (Phase 05a) — initial shape; ``contained_graphs``, ``metaedges``,
  ``metahyperedges``, ``properties``.
* v=2 (Phase 05b — Pushback 18-A) — adds ``intergraph_edges`` array and
  ``schema_name: str | null`` reference to a MetagraphSchema state file.
* v=3 (Phase 05c — P14-A smaller-items fold) — adds
  ``intergraph_hyperedges`` array (default empty on migration; existing
  v=2 metagraph state files have no n-ary hyperedges to carry over).
* v=4 (Phase 09 — M10 + RR-7 + RR-12) — adds ``xrefs`` array (default
  empty on migration; existing v=3 metagraph state files have no XRef
  rows to carry over). XRef shape is the 8-field dict per Phase 09 P53
  (``target_stale`` + ``deprecated_at`` deferred to Phase 10).
* v=5 (Phase 10 — M11 + RR-7 + RR-12) — soft-delete fields land per
  ADR-0133. Per-metaedge / per-metahyperedge: ``deprecated_at: null`` +
  ``disputed_at: null`` defaults (M5). Per-xref: ``target_stale: false``
  + ``deprecated_at: null`` defaults (Phase 09 P53 reversal). Schema
  state-file stays v=3 per M11 (immutable since 05d). IntergraphEdge /
  IntergraphHyperEdge soft-delete is OUT per Phase 10 M5 + P83 (Phase 05b/c
  primitives not in scope for this row; revisit when KL consumer surfaces).

Subsequent phases append migration steps; never edit a prior step.
"""

from __future__ import annotations

from typing import Callable, Dict, List

CURRENT_VERSION = 5


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


def _v2_to_v3(state: Dict) -> Dict:
    """Phase 05b → Phase 05c: introduce ``intergraph_hyperedges``.

    Per the Phase 05c row's smaller-items fold (single-step migration
    pattern from 05b ``_v1_to_v2``), the new top-level field defaults
    to empty list on migration: existing 05b metagraph state files have
    no n-ary hyperedges to carry over. Idempotent on re-migration.
    """
    state["intergraph_hyperedges"] = state.get("intergraph_hyperedges") or []
    return state


def _v3_to_v4(state: Dict) -> Dict:
    """Phase 08 → Phase 09 (RR-7): introduce ``xrefs`` array.

    Single-step single-line migration mirroring the Phase 05c
    ``_v2_to_v3`` pattern. Existing v=3 metagraph state files have no
    XRef rows to carry over; default empty list. Idempotent on
    re-migration.
    """
    state["xrefs"] = state.get("xrefs") or []
    return state


def _v4_to_v5(state: Dict) -> Dict:
    """Phase 09 → Phase 10 (M11 + RPB-3 + RR-7): soft-delete fields land.

    Per ADR-0133 — every metaedge / metahyperedge gets
    ``deprecated_at: null`` + ``disputed_at: null`` defaults (active /
    not-disputed). Every xref gets ``target_stale: false`` +
    ``deprecated_at: null`` defaults (Phase 09 P53 reversal restores
    the inert fields).

    Explicit per-item walk per RPB-3 — idempotent on re-migration (the
    field-already-present case re-asserts the same defaults). Per RR-8 —
    ISO-8601 string for ``deprecated_at`` / ``disputed_at`` (None →
    JSON null on serialize); plain bool for ``target_stale``.

    IntergraphEdge / IntergraphHyperEdge are out of scope per Phase 10
    M5 + P83 (no soft-delete fields added to those state-file rows).
    """
    for me in state.get("metaedges", []) or []:
        if "deprecated_at" not in me:
            me["deprecated_at"] = None
        if "disputed_at" not in me:
            me["disputed_at"] = None
    for mhe in state.get("metahyperedges", []) or []:
        if "deprecated_at" not in mhe:
            mhe["deprecated_at"] = None
        if "disputed_at" not in mhe:
            mhe["disputed_at"] = None
    for x in state.get("xrefs", []) or []:
        if "target_stale" not in x:
            x["target_stale"] = False
        if "deprecated_at" not in x:
            x["deprecated_at"] = None
    return state


#: ``MIGRATIONS[i]`` migrates v(i+1) → v(i+2).
MIGRATIONS: List[Callable[[Dict], Dict]] = [
    _v1_to_v2,
    _v2_to_v3,
    _v3_to_v4,
    _v4_to_v5,
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
