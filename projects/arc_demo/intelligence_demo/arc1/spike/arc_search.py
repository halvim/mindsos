"""Search/filter index — the per-task availability dictionary.

The Search panel filters the task list by **capability tokens**. Each task gets
a token list, derived **from the already-computed `match`/profile data** (no
re-derivation — single source of truth, per the design review):

- boolean tokens → bare name when they fire on >=1 demo pair. These are
  PROFILERS (``same_object`` / ``same_shape`` / ``same_point`` /
  ``same_cell_count`` / ``same_bbox_area`` — sameness facts about the task) and
  COMPARATORS (``moved`` / ``recolored`` / ``rotated`` / ``reflected`` /
  ``touching`` / ``inside`` — the 6 capacities). See the taxonomy section at the
  foot of this module (``is_comparator`` / ``demands`` / ``comparator_parents``).
- multi-result tokens → ``name:category`` (every task always gets exactly one):
  ``compare_grid_dimension:<preserved|grew|shrank|mixed|varies>`` and
  ``compare_palette:<preserved|added|removed|added+removed|varies>`` (profilers).

Non-deterministic extractors (``extract_objects``/``extract_points``) and the
trivial perceive caps are deliberately excluded — they aren't usable filters.

Adding a future discriminating capacity = add a FACET entry + a clause in
``task_tokens``; the dict repopulates on the next ``run_spike``.
"""

from __future__ import annotations

from typing import Dict, List

from . import arc_grids

#: Filterable facets the Search panel renders, split into two **divisions** —
#: inter-grid (compare input↔output) and intra-grid (relations within one grid)
#: — then sub-grouped: profile (multi-result) · atoms (sameness predicates) ·
#: object_comparator (transform detectors) · touching (intra-grid positional).
FACETS = [
    {"name": "compare_grid_dimension", "kind": "multi", "phase": "profile",
     "division": "inter-grid", "group": "profile",
     "results": ["preserved", "grew", "shrank", "mixed", "varies"]},
    {"name": "compare_palette", "kind": "multi", "phase": "profile",
     "division": "inter-grid", "group": "profile",
     "results": ["preserved", "added", "removed", "added+removed", "varies"]},
    {"name": "same_object", "kind": "bool", "phase": "induce",
     "division": "inter-grid", "group": "atoms", "implies": ["same_shape"]},
    # same_object ⟹ same_shape (identical cells ⇒ identical normalized shape) — a
    # DISPLAY implication (shown indented in Search/structure). NOTE it is unsound
    # at the TOKEN level for a per-task skip: `same_shape` fires only among
    # NON-identical objects, so 120/400 fire same_object without same_shape. It is
    # therefore NOT used to mark same_shape "implied-true" in the gates answer
    # (gates only skip-evaluates Phase-4 capacity implications, e.g. inside⟹touching).
    # same_shape ⟹ same_cell_count AND same_bbox_area (identical shape ⇒ identical
    # cell count + identical bbox area). Both are PROFILERS (not comparators) —
    # D4-invariant shape facts, near-universal as tokens, used as the
    # rotated/reflected demand + a display implication (indented in Search).
    {"name": "same_shape", "kind": "bool", "phase": "induce",
     "division": "inter-grid", "group": "atoms",
     "implies": ["same_cell_count", "same_bbox_area"]},
    {"name": "same_cell_count", "kind": "bool", "phase": "induce",
     "division": "inter-grid", "group": "atoms"},
    {"name": "same_bbox_area", "kind": "bool", "phase": "induce",
     "division": "inter-grid", "group": "atoms"},
    {"name": "same_point", "kind": "bool", "phase": "induce",
     "division": "inter-grid", "group": "atoms"},
    {"name": "moved", "kind": "bool", "phase": "induce",
     "division": "inter-grid", "group": "object_comparator",
     "requires_label": "⊃ shape, colour", "requires": ["same_shape"], "implies": ["same_shape"]},
    {"name": "recolored", "kind": "bool", "phase": "induce",
     "division": "inter-grid", "group": "transform",
     "requires_label": "⊃ shape", "requires": ["same_shape"], "implies": ["same_shape"]},
    {"name": "reflected", "kind": "bool", "phase": "induce",
     "division": "inter-grid", "group": "transform",
     "requires_label": "⊃ cells, area", "requires": ["same_cell_count", "same_bbox_area"]},
    {"name": "rotated", "kind": "bool", "phase": "induce",
     "division": "inter-grid", "group": "transform",
     "requires_label": "⊃ cells, area", "requires": ["same_cell_count", "same_bbox_area"]},
    {"name": "touching", "kind": "bool", "phase": "intra-grid",
     "division": "intra-grid", "group": ""},
    {"name": "inside", "kind": "bool", "phase": "intra-grid",
     "division": "intra-grid", "group": "", "implies": ["touching"]},
]


def _dim_category(v: dict) -> str:
    if v["agrees"] and v["common"] is None:
        return "preserved"
    if v["agrees"] and v["common"]:
        dr, dc = v["common"]["d"]
        if dr >= 0 and dc >= 0:
            return "grew"
        if dr <= 0 and dc <= 0:
            return "shrank"
        return "mixed"
    return "varies"


def _pal_category(v: dict) -> str:
    if v["agrees"] and v["common"] is None:
        return "preserved"
    if v["agrees"] and v["common"]:
        added = bool(v["common"]["added"])
        removed = bool(v["common"]["removed"])
        if added and removed:
            return "added+removed"
        if added:
            return "added"
        if removed:
            return "removed"
        return "preserved"
    return "varies"


def task_tokens(profile: dict) -> List[str]:
    """Tokens for one task (output of ``arc_profile.build_profile``)."""
    toks: List[str] = []
    demos = profile["train"]
    if any(d["match"]["equal"] for d in demos):
        toks.append("same_object")
    if any(d["match"]["shape_groups"] for d in demos):
        toks.append("same_shape")
    if any(d["match"]["point_equal"] for d in demos):
        toks.append("same_point")
    # same_cell_count / same_bbox_area — PROFILERS (shape invariants), fire when
    # ANY in→out object pair shares the count/area (near-universal). Sound under
    # same_shape ⟹ both, and rotated/reflected ⟹ both.
    if any(arc_grids.same_cell_count_pairs(d["input"], d["output"]) for d in demos):
        toks.append("same_cell_count")
    if any(arc_grids.same_bbox_area_pairs(d["input"], d["output"]) for d in demos):
        toks.append("same_bbox_area")
    if any(any(g.get("moves") for g in d["match"]["shape_groups"]) for d in demos):
        toks.append("moved")
    # transform comparators (inter-grid) — detected per demo pair over objects/shapes
    if any(arc_grids.recolored_pairs(d["input"], d["output"]) for d in demos):
        toks.append("recolored")
    if any(arc_grids.reflected_pairs(d["input"], d["output"]) for d in demos):
        toks.append("reflected")
    if any(arc_grids.rotated_pairs(d["input"], d["output"]) for d in demos):
        toks.append("rotated")
    # touching = intra-grid; fires when ANY demo has a touching pair in either
    # grid (input OR output). Demos only (test withheld).
    if any(d["input"].get("touching") or d["output"].get("touching") for d in demos):
        toks.append("touching")
    # inside = intra-grid; fires when ANY demo grid (input OR output) has an
    # (a inside b) enclosure pair. Demos only (test withheld).
    if any(d["input"].get("inside") or d["output"].get("inside") for d in demos):
        toks.append("inside")
    p = profile["profile"]
    toks.append("compare_grid_dimension:" + _dim_category(p["dimension_delta"]))
    toks.append("compare_palette:" + _pal_category(p["palette_delta"]))
    return toks


def build_availability(tasks: List[dict]) -> Dict[str, List[str]]:
    """{task_id: [tokens]} for every task — the search index."""
    return {t["task_id"]: task_tokens(t) for t in tasks}


# ── profiler / comparator taxonomy ──────────────────────────────────────
# PROFILERS describe a task (universal facts): the multi-result facets
# (compare_grid_dimension/compare_palette) + the sameness atoms (same_object,
# same_shape, same_point, same_cell_count, same_bbox_area). They are NOT
# capacities and are not ./evaluate targets.
# COMPARATORS are the 6 capacities: moved, recolored, rotated, reflected,
# touching, inside — bool facets outside the ``atoms`` group. Each carries
# ``requires`` (its profiler DEMANDS) and may be implied by another comparator.
def _facet(name: str) -> dict:
    return next((f for f in FACETS if f["name"] == name), {})


def is_comparator(facet: dict) -> bool:
    """A facet is a COMPARATOR (Phase-4 capacity) iff it is a bool facet outside
    the ``atoms`` (sameness profiler) group. Multi facets (profile) and atoms
    are profilers."""
    return facet.get("kind") == "bool" and facet.get("group") not in ("atoms",)


def comparator_names() -> List[str]:
    """The 6 comparator capacities (./evaluate targets), in facet order."""
    return [f["name"] for f in FACETS if is_comparator(f)]


def demands(cap: str) -> List[str]:
    """Profiler tokens that MUST fire for ``cap`` to apply (its ``requires``).
    Single source of truth for both the gate guard and ./evaluate."""
    return list(_facet(cap).get("requires", []))


def comparator_parents(cap: str) -> List[str]:
    """Comparators that imply ``cap`` (same division): when a parent fires,
    ``cap`` is known-true and need not be re-tested (e.g. inside ⟹ touching)."""
    child = _facet(cap)
    out: List[str] = []
    for f in FACETS:
        if is_comparator(f) and cap in f.get("implies", []) \
                and f.get("division") == child.get("division"):
            out.append(f["name"])
    return out
