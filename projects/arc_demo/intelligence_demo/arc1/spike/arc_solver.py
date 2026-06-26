"""Solver pipeline (read-only run viewer, option A) — scoped to task #8.

Stages built so far (the cheap deterministic core):
  1. states · transitions · changes — per-grid `touching` (built) + `moved`/
     `same_object` (built) + the **state-change detector** (un-parked P6):
     touching gained/lost across a pair, over correspondence
     (`same_object` ∪ 1:1 `moved`), with a **background** flag.
  2. hypothesis formation — features persistent across all pairs, then the
     `(transition, state-change)` combination test (same object within a pair,
     existential across pairs).

Stages 3–6 (selector / rule / verify / apply) **are built** for #8 (`stage3`…
`stage6`, `"pending": []`); stage6 reports `matches_withheld`. Per the locked
boundary this module only *computes*; any decision the machine cannot make
alone is recorded as a **flag** (the human answers in chat → rerun; option A).
Build is grounded on task #8 `05f2a901`.

**Layering note (D3 evidence).** This solver is *self-contained*: it imports
only ``arc_grids`` and takes ``(profile, raw_task)`` — it never touches the
``CapacityLayer`` or ``find_pipeline``. The registered reason topology
(``arc_capacities``) and this executable solver are **disjoint artifacts**; the
"grounding" is a hand-maintained mirror, not an execution path (see
``PIPELINE_DECISIONS.md`` §4, 2026-06-21 D3-spike entry).
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, List, Tuple

from . import arc_grids

#: The end-to-end use-case task (PIPELINE.md "Reason-stage design").
TASK8 = "05f2a901"

Ref = Tuple[str, int]  # ("O"|"P", index into the per-grid objects/points list)


def _ref(d: dict) -> Ref:
    return (d["kind"], d["idx"])


def _lbl(r: Ref) -> str:
    return f"{r[0]}{r[1]}"


def _comp(gs: dict, r: Ref) -> dict:
    return gs["objects"][r[1]] if r[0] == "O" else gs["points"][r[1]]


def _bg_color(profile: dict) -> int:
    """The **degenerate reconcile-background policy** (GF-4): pool the demo
    inputs and take the single most-frequent colour. This is the v1 stand-in
    for the per-grid detect → reconcile fold (ONTOLOGY #3 is per-grid; there is
    NO Task-level background). Pooling is the policy, NOT the model — the real
    reconcile policy is pending CORPUS-ANALYSIS.
    """
    cnt: Counter = Counter()
    for pr in profile["train"]:
        for row in pr["input"]["cells"]:
            cnt.update(row)
    return cnt.most_common(1)[0][0]


def _correspondence(pr: dict) -> Dict[Ref, Ref]:
    """C: input ref → output ref, from the unambiguous subset only —
    `same_object` (exact) ∪ 1:1 `moved` ∪ `same_point`. Ambiguous (duplicate)
    cases are left out (P3); pairs touching an uncorresponded object are skipped.
    """
    C: Dict[Ref, Ref] = {}
    for e in pr["match"]["equal"]:
        C[("O", e["in"])] = ("O", e["out"])
    for g in pr["match"]["shape_groups"]:
        for mv in g.get("moves", []):
            C[("O", mv["in"])] = ("O", mv["out"])
    for e in pr["match"]["point_equal"]:
        C[("P", e["in"])] = ("P", e["out"])
    return C


def _moved_in(pr: dict) -> set:
    s = set()
    for g in pr["match"]["shape_groups"]:
        for mv in g.get("moves", []):
            s.add(("O", mv["in"]))
    return s


def _touch_set(gs: dict) -> set:
    return set(frozenset([_ref(p["a"]), _ref(p["b"])]) for p in gs["touching"])


def touching_changes(pr: dict, bg: int, exclude_bg: bool = True) -> dict:
    """State-change detector (P6): touching transitions across one pair.

    Reports pairs in **input refs** (so labels match the input-side O-index).
    ``gained`` = touching in output, not in input; ``lost`` = the reverse;
    ``maintained`` = touching both sides. Background objects are dropped when
    ``exclude_bg`` (the dominant background touches nearly everything).
    """
    gin, gout = pr["input"], pr["output"]
    C = _correspondence(pr)
    Cinv = {v: k for k, v in C.items()}
    Tin, Tout = _touch_set(gin), _touch_set(gout)

    def keep(refs, gs) -> bool:
        if not exclude_bg:
            return True
        return not any(_comp(gs, r)["color"] == bg for r in refs)

    gained: List[tuple] = []
    lost: List[tuple] = []
    maintained: List[tuple] = []
    for pair in Tin:
        a, b = tuple(pair)
        if not keep((a, b), gin) or a not in C or b not in C:
            continue
        out_pair = frozenset([C[a], C[b]])
        (maintained if out_pair in Tout else lost).append((a, b))
    for pair in Tout:
        u, v = tuple(pair)
        if not keep((u, v), gout) or u not in Cinv or v not in Cinv:
            continue
        in_pair = frozenset([Cinv[u], Cinv[v]])
        if in_pair not in Tin:
            gained.append((Cinv[u], Cinv[v]))
    return {"gained": gained, "lost": lost, "maintained": maintained}


def _pair_lbl(pair: tuple) -> str:
    return "·".join(sorted(_lbl(r) for r in pair))


def _base_shape(gs: dict, r: Ref):
    return arc_grids.base_shape_name(gs["shapes"][r[1]]) if r[0] == "O" else None


def _selectors_for(roledemos: List[tuple]) -> List[str]:
    """Single-attribute selectors that hold for the role object in EVERY demo and
    distinguish it from the other non-background objects there. `roledemos` =
    [(gs, role_ref, [other_refs]), ...]. Each survivor is an equal-minimal
    (length-1) description; >1 survivor = the selector tie.
    """
    cands: List[str] = []
    cols = {_comp(gs, role)["color"] for gs, role, others in roledemos}
    if len(cols) == 1:
        c = next(iter(cols))
        if all(all(_comp(gs, o)["color"] != c for o in others)
               for gs, role, others in roledemos):
            cands.append(f"colour = {c}")
    if all(others and _comp(gs, role)["size"] > max(_comp(gs, o)["size"] for o in others)
           for gs, role, others in roledemos):
        cands.append("largest non-background")
    if all(others and _comp(gs, role)["size"] < min(_comp(gs, o)["size"] for o in others)
           for gs, role, others in roledemos):
        cands.append("smallest non-background")
    shps = {_base_shape(gs, role) for gs, role, others in roledemos}
    if len(shps) == 1 and next(iter(shps)) is not None:
        nm = next(iter(shps))
        if all(all(_base_shape(gs, o) != nm for o in others)
               for gs, role, others in roledemos):
            cands.append(f"shape = {nm}")
    elif all(_base_shape(gs, role) is None for gs, role, others in roledemos) \
            and all(others and any(_base_shape(gs, o) is not None for o in others)
                    for gs, role, others in roledemos):
        cands.append("no base shape (irregular)")
    return cands


# ── apply: greedy move generator + minimal serializer (stages 5–6) ──────
_NBRS = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]


def _touch_cells(a: List[tuple], b: List[tuple]) -> bool:
    bset = {tuple(c) for c in b}
    for (r, c) in a:
        for dr, dc in _NBRS:
            if (r + dr, c + dc) in bset:
                return True
    return False


def _move_direction(mover: dict, target: dict):
    """Slide axis: mover and target overlap on one axis → move along the
    perpendicular toward the target. Returns a unit (dr, dc) or None (ambiguous)."""
    mr0, mc0, mr1, mc1 = mover["bbox"]
    tr0, tc0, tr1, tc1 = target["bbox"]
    col_ov = not (mc1 < tc0 or tc1 < mc0)
    row_ov = not (mr1 < tr0 or tr1 < mr0)
    if col_ov and not row_ov:
        return (1, 0) if tr0 > mr1 else (-1, 0)
    if row_ov and not col_ov:
        return (0, 1) if tc0 > mc1 else (0, -1)
    return None


def _slide(dims, mover_cells, target_cells, dirn):
    """Greedy: translate one cell/step toward target until touching, or abstain
    (mover would leave the grid). Budget = grid bound (structural)."""
    H, W = dims
    dr, dc = dirn
    cells = [tuple(c) for c in mover_cells]
    for step in range(1, H + W + 1):
        nxt = [(r + dr, c + dc) for (r, c) in cells]
        if any(not (0 <= r < H and 0 <= c < W) for (r, c) in nxt):
            return None, step - 1
        cells = nxt
        if _touch_cells(cells, target_cells):
            return cells, step
    return None, H + W


def _shape_roles(gs: dict, bg: int):
    """Locked selector = shape: mover = the (unique) irregular non-bg object,
    target = the (unique) square non-bg object."""
    mover = target = None
    for i, o in enumerate(gs["objects"]):
        if o["color"] == bg:
            continue
        bs = arc_grids.base_shape_name(gs["shapes"][i])
        if bs is None and mover is None:
            mover = (i, o)
        elif bs == "square" and target is None:
            target = (i, o)
    return mover, target


def _render(dims, placed, bg):
    H, W = dims
    g = [[bg] * W for _ in range(H)]
    for cells, color in placed:
        for (r, c) in cells:
            if 0 <= r < H and 0 <= c < W:
                g[r][c] = color
    return g


def apply_rule(gs: dict, bg: int):
    """Run the assembled rule on one grid → produced grid (+ step count), or None
    (abstain) if roles/direction/slide fail. Minimal serializer: bg fill + every
    non-mover object at origin + mover at its slid position (no overlap for #8)."""
    mover, target = _shape_roles(gs, bg)
    if not mover or not target:
        return None
    mi, mo = mover
    _, to = target
    dirn = _move_direction(mo, to)
    if dirn is None:
        return None
    new_cells, steps = _slide(gs["dims"], mo["cells"], to["cells"], dirn)
    if new_cells is None:
        return None
    placed = [(o["cells"], o["color"]) for i, o in enumerate(gs["objects"])
              if o["color"] != bg and i != mi]
    placed.append((new_cells, mo["color"]))
    placed += [(p["cells"], p["color"]) for p in gs["points"]]
    return {"grid": _render(gs["dims"], placed, bg), "steps": steps}


# ── solver stages (decomposed so arc1/solve can run them step-by-step) ──
def stage_background(profile: dict) -> dict:
    """Step 4 — background + state-change: bg (pooled most-frequent, v1) + the
    per-pair touching_changes (gained/lost/maintained)."""
    demos = profile["train"]
    bg = _bg_color(profile)
    changes = [touching_changes(pr, bg, exclude_bg=True) for pr in demos]
    return {"bg": bg, "changes": changes, "n": len(demos)}


def stage_roles(profile: dict, bg: int, changes: list) -> dict:
    """Step 5 — roles (demo 1, representative): mover / target / background."""
    demos = profile["train"]
    n = len(demos)
    pr0, gin0 = demos[0], demos[0]["input"]
    moved0 = _moved_in(pr0)
    movers0, targets0 = set(), set()
    for (a, b) in changes[0]["gained"]:
        for r in (a, b):
            (movers0 if r in moved0 else targets0).add(r)
    roles = []
    bg_labels = []
    for i, o in enumerate(gin0["objects"]):
        ref = ("O", i)
        if o["color"] == bg:
            role = "background"
            bg_labels.append(_lbl(ref))
        elif ref in movers0:
            role = "mover"
        elif ref in targets0:
            role = "target"
        else:
            role = "—"
        roles.append({"ref": _lbl(ref), "role": role,
                      "color": o["color"], "size": o["size"]})

    def disp(gs, excl):
        pairs = _touch_set(gs)
        if excl:
            pairs = {p for p in pairs
                     if not any(_comp(gs, r)["color"] == bg for r in p)}
        return [_pair_lbl(p) for p in sorted(pairs, key=_pair_lbl)]

    gained0 = [_pair_lbl(frozenset((a, b))) for (a, b) in changes[0]["gained"]]
    n_gained = sum(1 for c in changes if c["gained"])
    return {
        "roles_demo1": roles,
        "touching_in_excl": disp(gin0, True),
        "touching_out_excl": disp(pr0["output"], True),
        "touching_in_full": disp(gin0, False),
        "touching_out_full": disp(pr0["output"], False),
        "gained_demo1": gained0,
        "change": {"state": "touching", "kind": "gained",
                   "persists": f"{n_gained}/{n}"},
        "background": {"color": bg, "objects": bg_labels,
                       "note": "optional — excluded by default; the gained signal is unaffected"},
    }


def stage_persistence(profile: dict, bg: int, changes: list) -> dict:
    """Step 6 — persistence ∀demo + the (move, touching) combination test."""
    demos = profile["train"]
    n = len(demos)
    n_gained = sum(1 for c in changes if c["gained"])
    persistent = [
        ["moved", f"{sum(1 for pr in demos if _moved_in(pr))}/{n}"],
        ["same_object", f"{sum(1 for pr in demos if pr['match']['equal'])}/{n}"],
        ["same_shape", f"{sum(1 for pr in demos if pr['match']['shape_groups'])}/{n}"],
        ["touching-gained", f"{n_gained}/{n}"],
    ]
    per_demo, objs = [], []
    for pr, ch in zip(demos, changes):
        moved = _moved_in(pr)
        sat = [r for (a, b) in ch["gained"] for r in (a, b) if r in moved]
        per_demo.append("✓" if sat else "✗")
        objs.append(_lbl(sat[0]) if sat else "—")
    verdict = "candidate" if all(x == "✓" for x in per_demo) else "no"
    return {
        "persistent": persistent,
        "excluded_static": ["same_object", "same_shape"],
        "combos": [{"combo": "(move, touching)", "per_demo": per_demo,
                    "objects": objs, "verdict": verdict}],
    }


def stage_selectors(profile: dict, bg: int, changes: list):
    """Step 7 — minimal discriminative selector per role (mover / target)."""
    demos = profile["train"]
    mover_rd, target_rd, ok = [], [], True
    for pr, ch in zip(demos, changes):
        moved = _moved_in(pr)
        mover = target = None
        for (a, b) in ch["gained"]:
            for r in (a, b):
                if r in moved:
                    mover = r
                elif _comp(pr["input"], r)["color"] != bg:
                    target = r
        if mover is None or target is None:
            ok = False
            break
        nonbg = [("O", i) for i, o in enumerate(pr["input"]["objects"])
                 if o["color"] != bg]
        mover_rd.append((pr["input"], mover, [r for r in nonbg if r != mover]))
        target_rd.append((pr["input"], target, [r for r in nonbg if r != target]))
    if not ok:
        return None
    mc, tc = _selectors_for(mover_rd), _selectors_for(target_rd)
    tie = len(mc) > 1 or len(tc) > 1

    def _shape_pick(cands):
        for c in cands:
            if "shape" in c or "irregular" in c:
                return c
        return cands[0] if cands else None

    return {
        "mover": {"candidates": mc},
        "target": {"candidates": tc},
        "tie": tie,
        "selected": "shape",
        "mover_selected": _shape_pick(mc),
        "target_selected": _shape_pick(tc),
        "note": "3-way tie — all candidates resolve the same objects on the "
                "#8 test; locked = shape (owner). The choice is a "
                "generalization prior, not part of #8's answer.",
    }


def stage_rule() -> dict:
    """Step 8 — rule assembly. **#8-specific (hardcoded).**"""
    return {
        "rule": "(move, touching)",
        "mover_sel": "no base shape (irregular)",
        "target_sel": "shape = square",
        "policy": "slide mover toward target along the shared-axis perpendicular "
                  "until touching; budget = grid bound",
        "dag": "mover → target (target invariant) — grounded",
    }


def stage_verify(profile: dict, bg: int) -> dict:
    """Step 9 — verify: apply_rule on each demo, exact-match output."""
    per_demo = []
    all_match = True
    for i, pr in enumerate(profile["train"]):
        res = apply_rule(pr["input"], bg)
        m = res is not None and res["grid"] == pr["output"]["cells"]
        per_demo.append({"demo": i + 1,
                         "steps": res["steps"] if res else None, "match": m})
        all_match = all_match and m
    return {"per_demo": per_demo, "all_match": all_match,
            "verdict": "sufficient — consistent with all demos" if all_match
                       else "insufficient — a demo mismatched"}


def stage_apply(profile: dict, bg: int, raw_task: dict = None):
    """Step 10 — apply to the test input → answer (test output withheld)."""
    if not profile["test"]:
        return None
    tin = profile["test"][0]["input"]
    res = apply_rule(tin, bg)
    out = res["grid"] if res else None
    matches = None
    if raw_task and raw_task.get("test"):
        matches = (out == raw_task["test"][0]["output"])
    return {"input": tin["cells"], "output": out,
            "steps": res["steps"] if res else None, "matches_withheld": matches}


def build_solver(profile: dict, raw_task: dict = None) -> dict:
    """Read-only solver run (stages 1–6). Thin orchestrator over the stage
    functions above — arc1/solve drives the same stages one at a time."""
    b = stage_background(profile)
    bg, changes = b["bg"], b["changes"]
    return {
        "task_id": profile["task_id"],
        "n_demos": b["n"],
        "background": {"color": bg, "proposed": f"exclude objects of colour {bg}"},
        "stage1": stage_roles(profile, bg, changes),
        "stage2": stage_persistence(profile, bg, changes),
        "stage3": stage_selectors(profile, bg, changes),
        "stage4": stage_rule(),
        "stage5": stage_verify(profile, bg),
        "stage6": stage_apply(profile, bg, raw_task),
        "pending": [],
    }
