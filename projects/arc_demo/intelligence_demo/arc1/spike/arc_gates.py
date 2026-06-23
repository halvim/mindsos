"""Capacity gate system — phased comparison → result → gate → capacity.

The single source of truth for the Gates panel. Layout (locked):

  PHASE 1 · Profiling          PHASE 2 · Components Comparisons   GATE        CAPACITY
  comparison → result chips    comparison → result chips          AND / OR    moved, touching

A *comparison* yields exactly one *result* per task. A *capacity* is enabled
when its *guard* (a boolean over comparison:result pairs, composed with
AND/OR — mirroring core ``input_group`` {all_required | any_of}) passes.

Grounding: profiling categories come from ``arc_search`` (the shipped facet
index); component facets from ``arc_search.task_tokens``. The colour/object/
point-presence profiling comparisons are computed here (real, derivable —
not yet arc_search facets). The only *shipped* requires is ``moved ⊃
same_shape``; the other guard clauses are this panel's proposed gating.
"""

from __future__ import annotations

from typing import Any, Dict, List

from . import arc_search


# ── comparisons (phase + ordered result options) ───────────────────────
COMPARISONS: List[Dict[str, Any]] = [
    {"key": "compare_grid_dimension", "label": "compare_grid_dimension",
     "phase": "profiling", "results": ["preserved", "grew", "shrank", "mixed", "varies"]},
    {"key": "compare_palette", "label": "compare_palette",
     "phase": "profiling", "results": ["preserved", "added", "removed", "added+removed", "varies"]},
    {"key": "colour_count", "label": "colour count",
     "phase": "profiling", "results": ["multicolor", "monochrome"]},
    {"key": "object_presence", "label": "object presence",
     "phase": "profiling", "results": ["present", "absent"]},
    {"key": "point_presence", "label": "point presence",
     "phase": "profiling", "results": ["present", "absent"]},
    {"key": "object_count", "label": "object count",
     "phase": "profiling", "results": ["none", "single", "multiple"]},
    {"key": "same_object", "label": "same_object",
     "phase": "components", "results": ["fires", "—"]},
    {"key": "same_shape", "label": "same_shape",
     "phase": "components", "results": ["fires", "—"]},
    {"key": "same_point", "label": "same_point",
     "phase": "components", "results": ["fires", "—"]},
]

#: capacities + guards. Guard nodes:
#:   {"op":"is","cmp":k,"result":r[,"requires":True]} | {"op":"and"|"or","args":[...]}
CAPACITIES: List[Dict[str, Any]] = [
    {"key": "moved", "guard": {"op": "and", "args": [
        {"op": "is", "cmp": "same_shape", "result": "fires", "requires": True},
        {"op": "is", "cmp": "compare_grid_dimension", "result": "preserved"},
        {"op": "is", "cmp": "compare_palette", "result": "preserved"},
    ]}},
    {"key": "touching", "guard": {"op": "and", "args": [
        {"op": "is", "cmp": "colour_count", "result": "multicolor"},
        {"op": "or", "args": [
            {"op": "is", "cmp": "object_presence", "result": "present"},
            {"op": "is", "cmp": "point_presence", "result": "present"},
        ]},
    ]}},
    {"key": "inside", "guard": {"op": "and", "args": [
        {"op": "is", "cmp": "colour_count", "result": "multicolor"},
        {"op": "is", "cmp": "object_count", "result": "multiple"},
    ]}},
]


# ── per-task evaluation ─────────────────────────────────────────────────
def _grids(profile: dict) -> List[dict]:
    out: List[dict] = []
    for pr in profile.get("train", []):
        out.append(pr["input"])
        if "output" in pr:
            out.append(pr["output"])
    return out


def _distinct_component_colours(g: dict) -> int:
    cols = {o["color"] for o in g.get("objects", [])}
    cols |= {p["color"] for p in g.get("points", [])}
    return len(cols)


def eval_comparisons(profile: dict) -> Dict[str, str]:
    """The single result that holds for each comparison, for one task."""
    p = profile.get("profile", {})
    grids = _grids(profile)
    toks = set(arc_search.task_tokens(profile))
    holds = {
        "compare_grid_dimension": arc_search._dim_category(p["dimension_delta"]),
        "compare_palette": arc_search._pal_category(p["palette_delta"]),
        "colour_count": "multicolor" if any(_distinct_component_colours(g) >= 2 for g in grids) else "monochrome",
        "object_presence": "present" if any(g.get("n_objects", 0) > 0 for g in grids) else "absent",
        "point_presence": "present" if any(g.get("n_points", 0) > 0 for g in grids) else "absent",
        "object_count": (lambda mx: "none" if mx == 0 else "single" if mx == 1 else "multiple")(
            max((g.get("n_objects", 0) for g in grids), default=0)),
    }
    for cap in ("same_object", "same_shape", "same_point"):
        holds[cap] = "fires" if cap in toks else "—"
    return holds


def eval_guard(node: Dict[str, Any], holds: Dict[str, str]) -> bool:
    op = node["op"]
    if op == "is":
        return holds.get(node["cmp"]) == node["result"]
    if op == "and":
        return all(eval_guard(a, holds) for a in node["args"])
    if op == "or":
        return any(eval_guard(a, holds) for a in node["args"])
    raise ValueError(f"unknown guard op: {op!r}")


def gate_report(profile: dict) -> Dict[str, Any]:
    """Per-task: the holding result for each comparison + enabled per capacity."""
    holds = eval_comparisons(profile)
    enabled = {c["key"]: eval_guard(c["guard"], holds) for c in CAPACITIES}
    return {"holds": holds, "enabled": enabled}


def gate_catalog() -> Dict[str, Any]:
    """Static layout definitions emitted once into the payload."""
    return {"comparisons": COMPARISONS, "capacities": CAPACITIES}
