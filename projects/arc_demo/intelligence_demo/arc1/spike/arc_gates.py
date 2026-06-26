"""Capacity gate system — phased comparison → result → gate → capacity.

The capability gate data is **derived from the Search facets in the spike**
(same source as Search availability): a facet is a CAPACITY iff it has
``requires`` or is intra-grid (moved / touching / inside), gated by its own
``fires`` + each ``requires`` — so a capacity is enabled iff its Search token
fires. The component/profiling comparisons are the full palette of conditions
available to gate against (every comparison is shown in the panel; the facet
multi/bool ones plus the derived profiling ones).

Box positions for the Gates panel may be saved to ``gates_layout.json`` (written
from the panel's Save button); it is loaded here and emitted as ``layout`` so a
committed layout is reused by future regenerations.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from . import arc_search

_DASH = "—"
_HERE = os.path.dirname(os.path.abspath(__file__))
_LAYOUT_JSON = os.path.join(_HERE, "gates_layout.json")

_MULTI = [f for f in arc_search.FACETS if f["kind"] == "multi"]
_BOOL = [f for f in arc_search.FACETS if f["kind"] == "bool"]

#: derived profiling comparisons (computed from the grids, not Search facets) —
#: extra conditions available to gate against. Constant-valued profilers carry
#: zero information across the 400-task corpus and were removed: ``colour_count``
#: (multicolor 400/400 — 0 monochrome tasks), ``object_presence`` (present
#: 400/400), ``component_presence`` (present 400/400). Only the discriminating
#: ones remain: ``point_presence`` (absent 58/400), ``object_count``
#: (single 6/400).
_DERIVED_PROFILING = [
    {"key": "point_presence", "results": ["present", "absent"]},
    {"key": "object_count", "results": ["none", "single", "multiple"]},
]


def _is_capacity(f: dict) -> bool:
    """A bool facet is a Phase-4 comparison CAPACITY (comparator) iff it is not a
    sameness profiler. Single source: ``arc_search.is_comparator``."""
    return arc_search.is_comparator(f)


def _build_comparisons() -> List[Dict[str, Any]]:
    """Phase 1 profiling (multi) · Phase 2 components (sameness atoms) · Phase 4
    comparison capacities (the other bool facets, split inter/intra). Each carries
    its ``division``, ``implies`` and ``requires`` so the panel can place + indent
    them. The derived profiling comparisons are NOT shown in the panel."""
    comps: List[Dict[str, Any]] = []
    for f in _MULTI:                          # PHASE 1 · profiling
        comps.append({"key": f["name"], "label": f["name"], "phase": "profiling",
                      "results": list(f["results"]), "division": f.get("division")})
    for f in _BOOL:
        entry = {"key": f["name"], "label": f["name"], "results": ["fires", _DASH],
                 "division": f.get("division"), "implies": f.get("implies", []),
                 "requires": f.get("requires", [])}
        entry["phase"] = "capacity" if _is_capacity(f) else "components"
        comps.append(entry)
    return comps


def _build_capacities() -> List[Dict[str, Any]]:
    caps: List[Dict[str, Any]] = []
    for f in _BOOL:
        if _is_capacity(f):
            clauses = [{"op": "is", "cmp": f["name"], "result": "fires"}]
            for req in f.get("requires", []):
                clauses.append({"op": "is", "cmp": req, "result": "fires"})
            caps.append({"key": f["name"], "guard": {"op": "and", "args": clauses}})
    return caps


COMPARISONS: List[Dict[str, Any]] = _build_comparisons()
CAPACITIES: List[Dict[str, Any]] = _build_capacities()

#: capacity implication parents (child -> implier) — same capacity phase + division.
#: When the parent tests positive the child is known-true and is NOT re-tested
#: (sound only for capacity-phase implications, e.g. inside ⟹ touching).
_CAP_BY_KEY = {c["key"]: c for c in COMPARISONS if c.get("phase") == "capacity"}
_CAP_PARENT: Dict[str, str] = {}
for _c in COMPARISONS:
    if _c.get("phase") != "capacity":
        continue
    for _im in _c.get("implies", []):
        _ch = _CAP_BY_KEY.get(_im)
        if _ch and _ch.get("division") == _c.get("division"):
            _CAP_PARENT[_im] = _c["key"]


# ── per-task evaluation ─────────────────────────────────────────────────
def _grids(profile: dict) -> List[dict]:
    out: List[dict] = []
    for pr in profile.get("train", []):
        out.append(pr["input"])
        if "output" in pr:
            out.append(pr["output"])
    return out


def eval_comparisons(profile: dict) -> Dict[str, Any]:
    """The single result that holds for each comparison, for one task. Facet
    comparisons come straight off ``arc_search.task_tokens``; the (discriminating)
    derived profiling comparisons are computed from the grids."""
    toks = set(arc_search.task_tokens(profile))
    grids = _grids(profile)
    holds: Dict[str, Any] = {}
    for f in _MULTI:
        cat = None
        for t in toks:
            if t.startswith(f["name"] + ":"):
                cat = t.split(":", 1)[1]
                break
        holds[f["name"]] = cat
    holds["point_presence"] = "present" if any(g.get("n_points", 0) > 0 for g in grids) else "absent"
    mx = max((g.get("n_objects", 0) for g in grids), default=0)
    holds["object_count"] = "none" if mx == 0 else "single" if mx == 1 else "multiple"
    for f in _BOOL:
        holds[f["name"]] = "fires" if f["name"] in toks else _DASH
    return holds


def eval_guard(node: Dict[str, Any], holds: Dict[str, Any]) -> bool:
    op = node["op"]
    if op == "is":
        return holds.get(node["cmp"]) == node["result"]
    if op == "and":
        return all(eval_guard(a, holds) for a in node["args"])
    if op == "or":
        return any(eval_guard(a, holds) for a in node["args"])
    raise ValueError(f"unknown guard op: {op!r}")


def gate_report(profile: dict) -> Dict[str, Any]:
    """Per-task gate evaluation, with the implication skip:

    1. test the comparisons (``holds``);
    2. test each capacity's gate (``enabled``);
    3. for an implied capacity whose **parent tested positive**, take it as
       known-true WITHOUT re-testing and record it in ``implied`` (child ->
       parent). Sound because the only capacity-phase implication is the
       verified ``inside ⟹ touching`` (0/400) — so ``enabled`` is unchanged,
       the test is simply skipped.
    """
    holds = eval_comparisons(profile)
    enabled = {c["key"]: eval_guard(c["guard"], holds) for c in CAPACITIES}
    implied: Dict[str, str] = {}
    for child, parent in _CAP_PARENT.items():
        if enabled.get(parent):
            implied[child] = parent       # known-true via parent; not re-tested
            enabled[child] = True
    return {"holds": holds, "enabled": enabled, "implied": implied}


# ── catalog ─────────────────────────────────────────────────────────────
def capacity_gate_spec(cap_key: str) -> Dict[str, Any]:
    """One capacity's table: every comparison with its results + gate value
    (false if not part of the gate). What the editable ``{ } json`` shows."""
    cap = next((c for c in CAPACITIES if c["key"] == cap_key), None)
    gated: Dict[str, str] = {}
    if cap:
        def walk(n):
            if n["op"] == "is":
                gated[n["cmp"]] = n["result"]
            else:
                for a in n.get("args", []):
                    walk(a)
        walk(cap["guard"])
    comparisons: Dict[str, Any] = {}
    for c in COMPARISONS:
        comparisons[c["key"]] = {"results": c["results"], "gate": gated.get(c["key"], False)}
    return {"capacity": cap_key, "comparisons": comparisons}


def _load_layout() -> Dict[str, Any]:
    """Saved box positions for the Gates panel (optional)."""
    if os.path.exists(_LAYOUT_JSON):
        try:
            with open(_LAYOUT_JSON, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}
    return {}


def gate_catalog() -> Dict[str, Any]:
    caps = [{"key": c["key"], "guard": c["guard"], "spec": capacity_gate_spec(c["key"])}
            for c in CAPACITIES]
    return {"comparisons": COMPARISONS, "capacities": caps, "layout": _load_layout()}
