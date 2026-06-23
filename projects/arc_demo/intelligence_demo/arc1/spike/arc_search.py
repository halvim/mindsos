"""Search/filter index — the per-task availability dictionary.

The Search panel filters the task list by **capability tokens**. Each task gets
a token list, derived **from the already-computed `match`/profile data** (no
re-derivation — single source of truth, per the design review):

- boolean caps → bare name when they fire on >=1 demo pair: ``same_object`` /
  ``same_shape`` / ``same_point``.
- multi-result caps → ``name:category`` (every task always gets exactly one):
  ``compare_grid_dimension:<preserved|grew|shrank|mixed|varies>`` and
  ``compare_palette:<preserved|added|removed|added+removed|varies>``.

Non-deterministic extractors (``extract_objects``/``extract_points``) and the
trivial perceive caps are deliberately excluded — they aren't usable filters.

Adding a future discriminating capacity = add a FACET entry + a clause in
``task_tokens``; the dict repopulates on the next ``run_spike``.
"""

from __future__ import annotations

from typing import Dict, List

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
     "division": "inter-grid", "group": "atoms"},
    {"name": "same_shape", "kind": "bool", "phase": "induce",
     "division": "inter-grid", "group": "atoms"},
    {"name": "same_point", "kind": "bool", "phase": "induce",
     "division": "inter-grid", "group": "atoms"},
    {"name": "moved", "kind": "bool", "phase": "induce",
     "division": "inter-grid", "group": "object_comparator",
     "requires_label": "⊃ shape, colour", "requires": ["same_shape"]},
    {"name": "touching", "kind": "bool", "phase": "intra-grid",
     "division": "intra-grid", "group": ""},
    {"name": "inside", "kind": "bool", "phase": "intra-grid",
     "division": "intra-grid", "group": ""},
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
    if any(any(g.get("moves") for g in d["match"]["shape_groups"]) for d in demos):
        toks.append("moved")
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
