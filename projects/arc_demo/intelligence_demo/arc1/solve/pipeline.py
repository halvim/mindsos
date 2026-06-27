"""The 10-step solver pipeline, decomposed so each step runs independently.

Steps 1–3 (general) are perceive/profile over `arc_profile`/`arc_grids`; steps
4–10 drive the `arc_solver.stage_*` functions. A run carries one accumulating
``ctx`` dict; each step reads it and adds its piece. Non-serialisable
intermediates (the per-pair ``changes``, which hold ref tuples) are NOT stored —
they are recomputed from the checkpointed ``profile`` + ``bg`` so JSON
round-tripping is safe. See STEPS.md for the sub-steps.
"""
from __future__ import annotations

from typing import Any, Dict

from intelligence_demo.arc1.spike import arc_grids, arc_profile, arc_solver, arc_search

GENERAL, GENERAL_STAR, SEMI, SPECIMEN = "general", "general*", "semi", "#8"

#: continuation-line indent so a multi-line ``result`` aligns under the runner's
#: "result" column (``"   result   "`` = 12 chars).
_RESULT_INDENT = " " * 12


def _block(header: str, lines: list) -> str:
    """A multi-line result: ``header`` on the result line, ``lines`` indented."""
    if not lines:
        return header
    return header + "\n" + "\n".join(_RESULT_INDENT + ln for ln in lines)


def _changes(ctx: dict):
    """Recompute the per-pair state-change (ref tuples) from profile + bg."""
    return [arc_solver.touching_changes(pr, ctx["bg"], exclude_bg=True)
            for pr in ctx["profile"]["train"]]


# ── step bodies: fn(ctx, dataset) -> one-line result string (mutates ctx) ──
def _perceive_line(p, gi_raw, go_raw):
    """One ``Pair p: In … → Out …`` perceive line (dims · palette · obj [· pt])."""
    def fmt(grid):
        s = arc_profile.grid_summary(grid)
        d = f"{s['dims'][0]}×{s['dims'][1]}"
        pal = "pal[" + ",".join(str(c) for c in sorted(s["palette"])) + "]"
        body = f"{s['n_objects']} obj"
        if s["n_points"] > 0:                 # only show points when present
            body += f" {s['n_points']} pt"
        return f"{d} {pal} · {body}"
    return f"Pair {p}: In {fmt(gi_raw)}  →  Out {fmt(go_raw)}"


def step_setup(ctx, dataset):
    """Phase 1 — input + perceive (collapsed); per-pair perceive summary."""
    raw = arc_grids.get_task(dataset, "train", ctx["task_id"])
    ctx["raw"] = raw
    g0 = arc_profile.grid_summary(raw["train"][0]["input"])
    ctx["perceived"] = {"n_objects": g0["n_objects"], "n_points": g0["n_points"],
                        "dims": list(g0["dims"]), "palette": sorted(g0["palette"])}
    lines = [_perceive_line(i + 1, pr["input"], pr["output"])
             for i, pr in enumerate(raw["train"])]
    header = f"{len(raw['train'])} train pairs · {len(raw['test'])} test"
    return _block(header, lines)


def _oref(side, p, idx, color):
    return f"{side}{p}.O{idx}.{arc_grids.color_name(color)}"


def _group_ref(side, p, idxs, objs):
    """Object-group ref; brackets only when the side has >1 object."""
    refs = [_oref(side, p, i, objs[i]["color"]) for i in idxs]
    return refs[0] if len(refs) == 1 else "[" + ", ".join(refs) + "]"


def step_profile(ctx, dataset):
    """Phase 2 — profilers: per-pair correspondence tiers (same_object →
    same_shape → same_point). same_shape shown only for non-identical
    shape_groups (the token also counts identical objects — see arc_search)."""
    prof = arc_profile.build_profile(dataset, "train", ctx["task_id"])
    ctx["profile"] = prof
    toks = set(arc_search.task_tokens(prof))
    ctx["tokens"] = sorted(toks)
    dim = next((t.split(":", 1)[1] for t in toks if t.startswith("compare_grid_dimension:")), "?")
    pal = next((t.split(":", 1)[1] for t in toks if t.startswith("compare_palette:")), "?")
    lines = []
    for i, pr in enumerate(prof["train"]):
        p = i + 1
        m, gi, go = pr["match"], pr["input"], pr["output"]
        tiers = []
        if m["equal"]:
            eqs = [f"{_oref('In', p, e['in'], gi['objects'][e['in']]['color'])} = "
                   f"{_oref('Out', p, e['out'], go['objects'][e['out']]['color'])}"
                   for e in m["equal"]]
            tiers.append(("same_object", ", ".join(eqs)))
        for g in m["shape_groups"]:           # same_shape = non-identical reuse only
            left = _group_ref("In", p, g["in"], gi["objects"])
            right = _group_ref("Out", p, g["out"], go["objects"])
            tiers.append(("same_shape", f"{left} = {right}"))
        if m["point_equal"]:
            pts = [f"In{p}.P{e['in']} = Out{p}.P{e['out']}" for e in m["point_equal"]]
            tiers.append(("same_point", ", ".join(pts)))
        if tiers:                             # omit pairs with no positives
            lines.append(f"Pair {p}:")
            lines.extend(f"  {lbl:<11}  {body}" for lbl, body in tiers)
    return _block(f"dims={dim} · palette={pal}", lines)


def step_comparators(ctx, dataset):
    """Phase 3 — comparators only (over the profile built in phase 2)."""
    toks = set(ctx.get("tokens") or arc_search.task_tokens(ctx["profile"]))
    comps = [c for c in arc_search.comparator_names() if c in toks]
    return f"comparators: {' '.join(comps) or '(none)'}"


def step_background(ctx, dataset):
    b = arc_solver.stage_background(ctx["profile"])
    ctx["bg"] = b["bg"]
    n_gained = sum(1 for c in b["changes"] if c["gained"])
    return f"bg = {b['bg']} (exclude colour {b['bg']}) · touching-gained persists {n_gained}/{b['n']}"


def step_roles(ctx, dataset):
    s1 = arc_solver.stage_roles(ctx["profile"], ctx["bg"], _changes(ctx))
    ctx["stage1"] = s1
    return " · ".join(f"{r['ref']}={r['role']}" for r in s1["roles_demo1"])


def step_persistence(ctx, dataset):
    s2 = arc_solver.stage_persistence(ctx["profile"], ctx["bg"], _changes(ctx))
    ctx["stage2"] = s2
    combo = s2["combos"][0]
    return (f"(move, touching): {' '.join(combo['per_demo'])} → verdict = {combo['verdict']} "
            f"· objects {','.join(combo['objects'])}")


def step_selectors(ctx, dataset):
    s3 = arc_solver.stage_selectors(ctx["profile"], ctx["bg"], _changes(ctx))
    ctx["stage3"] = s3
    if not s3:
        return "selectors: roles incomplete (no mover/target)"
    return f"mover = {s3['mover_selected']} · target = {s3['target_selected']} · tie→selected = {s3['selected']}"


def step_rule(ctx, dataset):
    s4 = arc_solver.stage_rule()
    ctx["stage4"] = s4
    return f"{s4['rule']} · {s4['policy']}"


def step_verify(ctx, dataset):
    s5 = arc_solver.stage_verify(ctx["profile"], ctx["bg"])
    ctx["stage5"] = s5
    marks = " ".join("✓" if d["match"] else "✗" for d in s5["per_demo"])
    return f"demos {marks} → {s5['verdict']}"


def step_apply(ctx, dataset):
    s6 = arc_solver.stage_apply(ctx["profile"], ctx["bg"], ctx.get("raw"))
    ctx["stage6"] = s6
    if not s6:
        return "no test grid"
    out = s6["output"]
    ctx["answer"] = out
    dims = f"{len(out)}×{len(out[0])}" if out else "—"
    m = s6["matches_withheld"]
    mtxt = "✓" if m else ("✗" if m is not None else "n/a")
    return f"ANSWER {dims} · {s6['steps']} slide steps · matches withheld test: {mtxt}"


#: (n, name, scope, fn, functions, produces) — `functions` = the real call chain
#: (rendered on the `uses` line; the old `engine` field is dropped).
STEPS = [
    (1, "Input + Perceive", GENERAL, step_setup,
     "arc_grids.get_task · arc_profile.grid_summary(extract_objects, extract_points, normalize_shape, palette, dimension)",
     "raw task · per-grid objects · points · shapes · palette · dims"),
    (2, "Profile", GENERAL, step_profile,
     "arc_profile.build_profile(match_pair, profile_sweep, hypotheses) · arc_search.task_tokens(same_cell_count_pairs, same_bbox_area_pairs)",
     "profile · profiler tokens"),
    (3, "Comparators", GENERAL, step_comparators,
     "arc_search.task_tokens · arc_grids.touching_pairs, inside_pairs, moved, recolored_pairs, rotated_pairs, reflected_pairs",
     "comparator tokens"),
    (4, "Background + state-change", GENERAL_STAR, step_background,
     "arc_solver.stage_background(_bg_color, touching_changes(_correspondence, _touch_set))",
     "bg · changes (gained/lost/maintained)"),
    (5, "Roles", SEMI, step_roles,
     "arc_solver.stage_roles(_moved_in, _touch_set, _comp)", "stage1 (roles)"),
    (6, "Persistence + combo", SPECIMEN, step_persistence,
     "arc_solver.stage_persistence(_moved_in, _lbl)", "stage2 (persistence ∀demo + verdict)"),
    (7, "Selectors", SEMI, step_selectors,
     "arc_solver.stage_selectors(_selectors_for(_comp, _base_shape))", "stage3 (selectors)"),
    (8, "Rule", SPECIMEN, step_rule, "arc_solver.stage_rule (static)", "stage4 (rule)"),
    (9, "Verify", SPECIMEN, step_verify,
     "arc_solver.stage_verify(apply_rule(_shape_roles, _move_direction, _slide, _render))",
     "stage5 (per-demo match)"),
    (10, "Apply test → ANSWER", SPECIMEN, step_apply,
     "arc_solver.stage_apply(apply_rule)", "stage6 + answer grid"),
]


#: PROPOSED future home for each step's inline engine/uses — the real MindsOS
#: feature + location it should map to. Aspirational (the demo runs D3-inline
#: today; only step 2 actually discovers through the layer). Rows 3/5/6 unsettled.
STEP_TARGETS = {
    1: "L4 task intake → TaskRun + L3 perceive chain via cl.invoke (find_pipeline) · mindsos_intelligence/orchestrator.py + mindsos_capacity/pipeline.py",
    2: "L4 phase_1 sweep — L3 profilers (compare_*, same_*) · mindsos_intelligence/builtins/phase1_v0.py + mindsos_capacity",
    3: "L4 phase_1 sweep — L3 comparators/predicates (moved/touching/inside/transforms) · mindsos_intelligence/builtins/phase1_v0.py + mindsos_capacity",
    4: "L3 derivation+reasoning (detect/reconcile background; touching_delta) via invoke · mindsos_capacity",
    5: "L3 reasoning — role assignment over state-change · mindsos_capacity",
    6: "L4 induction — agrees-across-demos hypotheses fold · mindsos_intelligence (orchestrator/learner)",
    7: "L3 reasoning/scoring — synthesize_selector via invoke · mindsos_capacity",
    8: "L4 plan construction → Plan/Pipeline chain artifact · mindsos_intelligence/chain_artifacts.py",
    9: "L4 sufficiency — sufficient_predicate / replan_check · mindsos_intelligence/orchestrator.py",
    10: "L4 execution (PipelineRun) + L5 consolidation → Episode/Memory · mindsos_intelligence/consolidation.py",
}


#: One-line description of what each phase does (for `./arc solve --phases`).
STEP_DESC = {
    1: "Load the raw task and perceive each grid — objects (8-connected, ≥2 cells), points, shapes, palette, dims.",
    2: "Run the profilers — same_object/shape/point, same_cell_count, same_bbox_area, and the dim/palette deltas.",
    3: "Run the comparators — moved, touching, inside, recolored, rotated, reflected.",
    4: "Propose the background colour, build the in→out correspondence, and classify touching changes (gained/lost/maintained).",
    5: "Classify the changed objects into roles — mover, target, background.",
    6: "Test which capabilities persist across all demos and form the (move, touching) combination verdict.",
    7: "For each role, find the minimal selector that discriminates it across every demo (tie-break → shape).",
    8: "Assemble the transformation rule — slide the mover toward the target until touching (hardcoded for #8).",
    9: "Apply the rule to every demo and check it reproduces each output exactly.",
    10: "Apply the rule to the test input to produce the answer grid (test output withheld).",
}


def run_all(task_id: str, dataset: dict) -> Dict[str, Any]:
    """Run all 10 steps in-memory (no checkpoints) — used by the gate."""
    ctx: Dict[str, Any] = {"task_id": task_id}
    for (_n, _name, _scope, fn, _eng, _prod) in STEPS:
        fn(ctx, dataset)
    return ctx
