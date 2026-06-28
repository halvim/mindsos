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
     "division": "inter-grid", "group": "atoms",
     "implies": ["same_shape"], "skip": ["same_shape"]},
    # same_object ⟹ same_shape (identical cells ⇒ identical normalized shape).
    # WIRED as a token skip (``skip`` field): when same_object fires the same_shape
    # TOKEN is taken true without a separate test (task_tokens OR-s ``equal`` into
    # same_shape). Sound 0/400 because identical cells ⇒ identical shape_key. The
    # phase-2 *display* still shows same_shape only for shape_groups (non-identical
    # reuse), so token (267/400) deliberately diverges from display (option A); the
    # divergence is documented by ``./arc solve --inferences``.
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
    same_obj = any(d["match"]["equal"] for d in demos)
    if same_obj:
        toks.append("same_object")
    # same_shape token = different objects share a shape (shape_groups) OR an
    # identical object exists (same_object ⟹ same_shape, wired skip — see the
    # same_object facet ``skip`` field). Sound 0/400: identical cells ⇒ identical
    # shape_key. Note the phase-2 *display* still shows same_shape only for
    # shape_groups (non-trivial reuse); token deliberately diverges (option A).
    if same_obj or any(d["match"]["shape_groups"] for d in demos):
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


# ── operators (./evaluate show-only; NOT comparators, NOT Search facets) ──
# ``inset`` and ``union`` are registered capacities that carry NO Search token
# (inset is near-universal; union is an OPERATOR, not a bool comparator). They
# appear in ./evaluate as occurrence + demands only — no token cross-check, so
# they never enter the gate's 6-comparator discrepancy/enabled invariants.
# Operator inference: union ⟹ inset (C=union(A,B) ⟹ inset(A,C) ∧ inset(B,C)) —
# when a union occurs, inset is known-true and its check is skipped.
OPERATOR_NAMES = ["inset", "union"]
OPERATOR_DEMANDS: Dict[str, List[str]] = {"inset": [], "union": ["inset"]}
OPERATOR_INFERENCES: List[tuple] = [("union", ["inset"])]  # parent ⟹ children


def operator_names() -> List[str]:
    """The non-comparator ./evaluate targets (operators/near-universal
    predicates): inset, union. Show-only (occurrence + demands)."""
    return list(OPERATOR_NAMES)


def operator_demands(op: str) -> List[str]:
    return list(OPERATOR_DEMANDS.get(op, []))


def inferences() -> Dict[str, List[tuple]]:
    """All declared inference edges, grouped by how each is used. Single source:
    the FACET table (``requires`` / ``implies`` / ``skip``). Each edge is a
    ``(parent, [children])`` tuple.

    - ``wired``       — drives a skip (the child is taken true when the parent
                        fires, not re-tested): comparator skips (inside ⟹ touching)
                        and token skips (same_object ⟹ same_shape).
    - ``requires``    — a comparator's profiler DEMANDS (cross-phase gate edge).
    - ``display``     — true but not wired (e.g. same_shape ⟹ cell/bbox).
    """
    wired: List[tuple] = []
    requires: List[tuple] = []
    display: List[tuple] = []
    for f in FACETS:
        name, reqs = f["name"], f.get("requires", [])
        if reqs:
            requires.append((name, list(reqs)))
        skip = list(f.get("skip", []))
        if skip:
            wired.append((name, skip))
        # comparator→comparator implies in the same division = a wired skip
        cap_skip = [im for im in f.get("implies", [])
                    if is_comparator(f) and is_comparator(_facet(im))
                    and f.get("division") == _facet(im).get("division")]
        if cap_skip:
            wired.append((name, cap_skip))
        # remaining implies (not a requires-dup, not a skip) = display-only
        disp = [im for im in f.get("implies", [])
                if im not in reqs and im not in skip and im not in cap_skip]
        if disp:
            display.append((name, disp))
    # operator-level inferences (union ⟹ inset) — wired skips, not FACET-derived.
    wired.extend(OPERATOR_INFERENCES)
    return {"wired": wired, "requires": requires, "display": display}
