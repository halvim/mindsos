"""TaskProfile builder + find_pipeline discovery (M1).

Scope discipline: M1 profile = steps 1-3 only (grid size+variation, color
set+variation, object/shape sets) + the demo-delta sweep. Correspondence,
"equal objects", and remaining-object sets are M2 (induce-stage) and are
deliberately NOT computed here — putting them in preparation would re-cross
the locked boundary.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from mindsos_capacity.capacity_layer import CapacityLayer
from mindsos_capacity.pipeline import find_pipeline

from . import arc_capacities as ac
from . import arc_grids


# ── per-grid summary (the perceive output, materialized for the UI) ─────
def grid_summary(grid: List[List[int]]) -> dict:
    # Objects = 8-connected monochrome components of size >= 2 (ONTOLOGY §4 #1b);
    # Points = single cells (not Objects/Shapes).
    objects = arc_grids.extract_objects(grid)
    points = arc_grids.extract_points(grid)
    return {
        "cells": grid,
        "dims": list(arc_grids.dimension(grid)),
        "palette": arc_grids.palette(grid),
        "n_objects": len(objects),
        "objects": objects,
        "shapes": [arc_grids.normalize_shape(o) for o in objects],
        "n_points": len(points),
        "points": points,
        # intra-grid positional: touching pairs among this grid's components
        # (different-colour Object/Point pairs sharing an 8-neighbour; §4 #16).
        "touching": arc_grids.touching_pairs(objects, points),
        # intra-grid positional: (a inside b) — a enclosed by a single-colour
        # object b (cannot reach the border without crossing b; bg-excluded).
        "inside": arc_grids.inside_pairs(
            objects, points, arc_grids.dimension(grid),
            arc_grids.background_color(grid), grid),
    }


# ── profile comparators (run by the L4-style sweep, not find_pipeline) ──
def dimension_delta(a: List[List[int]], b: List[List[int]]) -> Optional[dict]:
    da, db = arc_grids.dimension(a), arc_grids.dimension(b)
    if da == db:
        return None
    return {"in": list(da), "out": list(db),
            "d": [db[0] - da[0], db[1] - da[1]]}


def palette_delta(a: List[List[int]], b: List[List[int]]) -> Optional[dict]:
    pa, pb = set(arc_grids.palette(a)), set(arc_grids.palette(b))
    if pa == pb:
        return None
    return {"added": sorted(pb - pa), "removed": sorted(pa - pb)}


def match_pair(gin: dict, gout: dict) -> dict:
    """Two-comparator fold (#4 fold) over a demo pair, producing three tiers:

      1. ``equal``        — same_object pairs (same colour + position), 1:1.
                            Runs regardless of dims (compares absolute cells).
      2. ``shape_groups`` — over the leftover (non-equal) objects, group by
                            identical Shape (same_shape). Single points excluded;
                            a group is kept only when present on BOTH sides.
                            Carries the base-shape name (or None) + cell size.
      3. ``*_rest``       — everything else (unique shape, one-sided, or points).

    All indices refer into the per-grid ``objects`` lists.
    """
    in_objs, out_objs = gin["objects"], gout["objects"]
    in_sh, out_sh = gin["shapes"], gout["shapes"]
    matched_in, matched_out = set(), set()

    # tier 1 — same_object (1:1)
    equal: List[dict] = []
    for i, a in enumerate(in_objs):
        for j, b in enumerate(out_objs):
            if j in matched_out:
                continue
            if arc_grids.same_object(a, b):
                equal.append({"in": i, "out": j})
                matched_in.add(i)
                matched_out.add(j)
                break

    # tier 2 — same_shape groups (points excluded; both sides required)
    in_by: Dict[Any, List[int]] = defaultdict(list)
    out_by: Dict[Any, List[int]] = defaultdict(list)
    for i, sh in enumerate(in_sh):
        if i not in matched_in and sh["size"] > 1:
            in_by[arc_grids.shape_key(sh)].append(i)
    for j, sh in enumerate(out_sh):
        if j not in matched_out and sh["size"] > 1:
            out_by[arc_grids.shape_key(sh)].append(j)

    shape_groups: List[dict] = []
    grouped_in, grouped_out = set(), set()
    for key in in_by:
        if key in out_by:
            ins, outs = in_by[key], out_by[key]
            # moved: per (input, output) pair, the displacement Δ (zero omitted).
            moves = []
            for i in ins:
                for j in outs:
                    # moved only relates same-colour objects (pre-skip; moved
                    # also self-guards). Stores the move Transform.
                    if in_objs[i]["color"] != out_objs[j]["color"]:
                        continue
                    mv = arc_grids.moved(in_objs[i], out_objs[j])
                    if mv is not None:
                        moves.append({"in": i, "out": j, "transform": mv})
            shape_groups.append({
                "name": arc_grids.base_shape_name(in_sh[ins[0]]),
                "size": in_sh[ins[0]]["size"],
                "in": ins,
                "out": outs,
                "moves": moves,
            })
            grouped_in.update(ins)
            grouped_out.update(outs)

    # tier 4 — same_point (1:1; points are not grouped)
    in_pts, out_pts = gin["points"], gout["points"]
    point_equal: List[dict] = []
    pmatched_in, pmatched_out = set(), set()
    for i, a in enumerate(in_pts):
        for j, b in enumerate(out_pts):
            if j in pmatched_out:
                continue
            if arc_grids.same_point(a, b):
                point_equal.append({"in": i, "out": j})
                pmatched_in.add(i)
                pmatched_out.add(j)
                break

    return {
        "equal": equal,
        "shape_groups": shape_groups,
        "input_rest": [i for i in range(len(in_objs))
                       if i not in matched_in and i not in grouped_in],
        "output_rest": [j for j in range(len(out_objs))
                        if j not in matched_out and j not in grouped_out],
        "point_equal": point_equal,
        "input_point_rest": [i for i in range(len(in_pts)) if i not in pmatched_in],
        "output_point_rest": [j for j in range(len(out_pts)) if j not in pmatched_out],
    }


def _agrees(deltas: List[Optional[dict]]) -> dict:
    """agrees_across_demos: same verdict + same Delta across all demos."""
    if all(d is None for d in deltas):
        return {"agrees": True, "common": None}      # "no change", consistently
    if any(d is None for d in deltas):
        return {"agrees": False, "common": None}     # some change, some not
    first = deltas[0]
    return {"agrees": all(d == first for d in deltas),
            "common": first if all(d == first for d in deltas) else None}


def profile_sweep(task: dict) -> dict:
    """The mandatory phase_1 sweep over demonstrations only (test withheld)."""
    demos = task["train"]
    dim_deltas = [dimension_delta(p["input"], p["output"]) for p in demos]
    pal_deltas = [palette_delta(p["input"], p["output"]) for p in demos]
    return {
        "dimension_delta_per_demo": dim_deltas,
        "dimension_delta": _agrees(dim_deltas),
        "palette_delta_per_demo": pal_deltas,
        "palette_delta": _agrees(pal_deltas),
    }


#: Induce capabilities tested for cross-pair persistence (NOT the profile-sweep
#: compare_* caps). Pair 1 is canonical: a capability is hypothesised only if it
#: fires in pair 1 AND in every other pair (agrees_across_demos = presence).
#: ``touching`` is intra-grid (a candidate constraint per pair = present in
#: either grid of the pair); the others are inter-grid (read off ``match``).
INDUCE_CAPS = ["same_object", "same_shape", "same_point", "moved", "touching", "inside"]


def _present(pr: dict, cap: str) -> bool:
    if cap == "touching":
        return bool(pr["input"].get("touching")) or \
            bool(pr["output"].get("touching"))
    if cap == "inside":
        return bool(pr["input"].get("inside")) or \
            bool(pr["output"].get("inside"))
    m = pr["match"]
    if cap == "same_object":
        return bool(m["equal"])
    if cap == "same_shape":
        return bool(m["shape_groups"])
    if cap == "same_point":
        return bool(m["point_equal"])
    if cap == "moved":
        return any(g.get("moves") for g in m["shape_groups"])
    return False


def hypotheses(train_grids: List[dict]) -> dict:
    """L4 hypothesis fold: pair-1 induce caps that persist across all demos.

    `agrees_across_demos` here = **present in every demo pair** (presence only;
    value/why deferred). A capability is a hypothesis iff it fired in pair 1 and
    in all pairs. compare_* (profile-sweep) is intentionally excluded.
    """
    n = len(train_grids)
    detail = []
    chosen = []
    for cap in INDUCE_CAPS:
        in1 = _present(train_grids[0], cap) if n else False
        fired = sum(1 for pr in train_grids if _present(pr, cap))
        agrees = in1 and fired == n          # in pair 1 + present in all pairs
        detail.append({"cap": cap, "in_pair1": in1, "fired": fired,
                       "of": n, "agrees": agrees})
        if agrees:
            chosen.append(cap)
    return {"list": chosen, "detail": detail}


def build_profile(dataset: dict, split: str, task_id: str) -> dict:
    """Full TaskProfile + materialized perceive output for the UI."""
    task = arc_grids.get_task(dataset, split, task_id)
    demos = task["train"]
    tests = task["test"]

    train_grids = []
    for p in demos:
        gin = grid_summary(p["input"])
        gout = grid_summary(p["output"])
        # both passes run regardless of dims (same_object compares absolute
        # cells; same_shape is translation-normalized).
        train_grids.append({"input": gin, "output": gout,
                            "match": match_pair(gin, gout)})
    # test output is WITHHELD (ONTOLOGY §4 #4) — input only.
    test_grids = [{"input": grid_summary(p["input"])} for p in tests]

    in_dims = [g["input"]["dims"] for g in train_grids]
    out_dims = [g["output"]["dims"] for g in train_grids]
    sweep = profile_sweep(task)

    profile = {
        "n_demos": len(demos),
        "n_tests": len(tests),
        # step 1 — grid size
        "dims_preserved": all(i == o for i, o in zip(in_dims, out_dims)),
        # step 2 — color set (per-demo, in vs out)
        "colors_preserved": all(
            g["input"]["palette"] == g["output"]["palette"] for g in train_grids
        ),
        # demo-delta sweep verdicts
        "dimension_delta": sweep["dimension_delta"],
        "palette_delta": sweep["palette_delta"],
    }
    return {
        "task_id": task_id,
        "split": split,
        "train": train_grids,
        "test": test_grids,
        "profile": profile,
        "sweep": sweep,
        "hypotheses": hypotheses(train_grids),
    }


# ── find_pipeline discovery (the dataflow proof — no router) ─────────────
def discover(cl: CapacityLayer, start: str, target: str) -> List[str]:
    pipe = find_pipeline(cl, start_datastate=start, target_datastate=target)
    return [step.capacity_iri for step in pipe]


def discovery_report(cl: CapacityLayer) -> Dict[str, List[str]]:
    """find_pipeline composes the perceive chain by PRODUCES/CONSUMES alone."""
    return {
        "raw_task -> shape": discover(cl, ac.DS_RAW_TASK, ac.DS_SHAPE),
        "raw_task -> palette": discover(cl, ac.DS_RAW_TASK, ac.DS_PALETTE),
        "grid -> object": discover(cl, ac.DS_GRID, ac.DS_OBJECT),
    }
