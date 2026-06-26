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


def _changes(ctx: dict):
    """Recompute the per-pair state-change (ref tuples) from profile + bg."""
    return [arc_solver.touching_changes(pr, ctx["bg"], exclude_bg=True)
            for pr in ctx["profile"]["train"]]


# ── step bodies: fn(ctx, dataset) -> one-line result string (mutates ctx) ──
def step_input(ctx, dataset):
    raw = arc_grids.get_task(dataset, "train", ctx["task_id"])
    ctx["raw"] = raw
    g = raw["train"][0]["input"]
    return f"train = {len(raw['train'])} pairs · test = {len(raw['test'])} · input grid {len(g)}×{len(g[0])}"


def step_perceive(ctx, dataset):
    grids = []
    for p in ctx["raw"]["train"]:
        gin = arc_profile.grid_summary(p["input"])
        grids.append({"n_objects": gin["n_objects"], "n_points": gin["n_points"],
                      "dims": list(gin["dims"]), "palette": gin["palette"]})
    ctx["perceived"] = grids
    g0 = grids[0]
    return (f"demo1.in: {g0['n_objects']} objects · {g0['n_points']} points · "
            f"dims {g0['dims'][0]}×{g0['dims'][1]} · palette {sorted(g0['palette'])}")


def step_profile(ctx, dataset):
    prof = arc_profile.build_profile(dataset, "train", ctx["task_id"])
    ctx["profile"] = prof
    toks = set(arc_search.task_tokens(prof))
    bools = [k for k in ("same_object", "same_shape", "same_point", "moved",
                         "touching", "inside", "recolored", "rotated", "reflected") if k in toks]
    dim = next((t.split(":", 1)[1] for t in toks if t.startswith("compare_grid_dimension:")), "?")
    pal = next((t.split(":", 1)[1] for t in toks if t.startswith("compare_palette:")), "?")
    return f"fires: {' '.join(bools) or '(none)'} · dim={dim} palette={pal}"


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


#: (n, name, scope, fn, engine, produces)
STEPS = [
    (1, "Input", GENERAL, step_input, "inline · arc_grids.get_task", "raw (train pairs + test)"),
    (2, "Perceive", GENERAL, step_perceive, "layer-discovered · executed inline (arc_grids)",
     "per-grid objects · points · shapes · palette · dims"),
    (3, "Profile / Match", GENERAL, step_profile, "inline · arc_profile.match_pair · arc_grids.*",
     "profile: match · touching/inside · transforms · deltas"),
    (4, "Background + state-change", GENERAL_STAR, step_background,
     "inline · arc_solver._bg_color · touching_changes", "bg · changes (gained/lost/maintained)"),
    (5, "Roles", SEMI, step_roles, "inline · arc_solver._moved_in · role classify", "stage1 (roles)"),
    (6, "Persistence + combo", SPECIMEN, step_persistence, "inline · arc_solver",
     "stage2 (persistence ∀demo + verdict)"),
    (7, "Selectors", SEMI, step_selectors, "inline · arc_solver._selectors_for", "stage3 (selectors)"),
    (8, "Rule", SPECIMEN, step_rule, "inline · arc_solver (hardcoded)", "stage4 (rule)"),
    (9, "Verify", SPECIMEN, step_verify, "inline · arc_solver.apply_rule (demos)", "stage5 (per-demo match)"),
    (10, "Apply test → ANSWER", SPECIMEN, step_apply, "inline · arc_solver.apply_rule (test)",
     "stage6 + answer grid"),
]


#: PROPOSED future home for each step's inline engine/uses — the real MindsOS
#: feature + location it should map to. Aspirational (the demo runs D3-inline
#: today; only step 2 actually discovers through the layer). Rows 3/5/6 unsettled.
STEP_TARGETS = {
    1: "L4 task intake → TaskRun (L3 comprehend_task binds) · mindsos_intelligence/orchestrator.py + mindsos_capacity",
    2: "L3 perceive chain via cl.invoke, composed by find_pipeline · mindsos_capacity/pipeline.py",
    3: "L4 phase_1 sweep over L3 comparators/profilers · mindsos_intelligence/builtins/phase1_v0.py + mindsos_capacity",
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
    1: "Load the raw task — the train demonstration pairs and the withheld test input.",
    2: "Per grid, perceive the entities — objects (8-connected, ≥2 cells), points, shapes, palette, dims.",
    3: "Per demo pair, run the profilers and comparators — same_object/shape/point, moved, touching, inside, recolored/rotated/reflected, and dim/palette deltas.",
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
