"""The 10-step solver pipeline, decomposed so each step runs independently.

Steps 1–3 (general) are perceive/profile over `arc_profile`/`arc_grids`; steps
4–10 drive the `arc_solver.stage_*` functions. A run carries one accumulating
``ctx`` dict in-memory; each step reads it and adds its piece. The whole
pipeline is recomputed from scratch on every invocation (no checkpoints). See
STEPS.md for the sub-steps.
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


def step_subdivision(ctx, dataset):
    """Phase 3 — subdivision: a disjoint cover holds in EITHER direction
    (bg-AGNOSTIC, points included): `split` = an INPUT object = ≥2 OUTPUT insets;
    `assemble` = an OUTPUT object = ≥2 INPUT insets (arc_grids.subdivisions both
    ways). Holds-∀-demo (either direction per pair) = the task is a subdivision.
    Display/hypothesis."""
    prof = ctx["profile"]
    def ref(side, p, kind, j, g):
        if kind == "O":
            return f"{side}{p}.O{j}.{arc_grids.color_name(g['objects'][j]['color'])}"
        return f"{side}{p}.P{j}"
    per_pair, holds, findings = [], [], []
    for i, pr in enumerate(prof["train"]):
        p = i + 1
        gi, go = pr["input"], pr["output"]
        hit = False
        for direction, whole_g, part_g, w_side, p_side in (
                ("split", gi, go, "In", "Out"),       # whole=input, parts=output
                ("assemble", go, gi, "Out", "In")):   # whole=output, parts=input
            for s in arc_grids.subdivisions(whole_g, part_g):
                hit = True
                w_base = f"{w_side}{p}.O{s['in']}"            # e.g. In1.O1
                w_color = arc_grids.color_name(whole_g["objects"][s["in"]]["color"])
                B = f"{w_base}.{w_color}"                     # whole ref: In1.O1.grey
                Cw = whole_g["objects"][s["in"]]["color"]
                # PHASE 3 = subdivision ONLY (cover). NO same_* here — the
                # colour comparison is phase 4. Store enough for phase 4 to
                # compute it: the sub-label, the part ref, the part colour+kind.
                part_items, part_refs, kids = [], [], []
                for kk, (k, j) in enumerate(s["parts"]):
                    pref = ref(p_side, p, k, j, part_g)
                    Cp = (part_g["objects"][j]["color"] if k == "O"
                          else part_g["points"][j]["color"])
                    sub = f"{w_base}.sub{kk + 1}.{w_color}"   # In1.O1.sub1.grey
                    part_items.append({"sub": sub, "ref": pref,
                                       "part_color": Cp, "kind": k})
                    part_refs.append(pref)
                    kids.append(sub)
                parts = ", ".join(part_refs)
                per_pair.append(f"Pair {p} [{direction}]: {B} → {{{parts}}}")
                per_pair.append(f"         {B} → {', '.join(kids)}")
                findings.append({"pair": p, "direction": direction, "whole": B,
                                 "whole_color": Cw, "whole_idx": s["in"],
                                 "parts": part_items})
        holds.append(hit)
    allhold = all(holds) and len(holds) > 0
    ctx["subdivision"] = {"holds_all": allhold, "n": len(holds), "findings": findings}
    head = f"subdivision — {'yes' if allhold else 'no'} (∀demo {sum(holds)}/{len(holds)})"
    return _block(head, per_pair)


def step_objcomp(ctx, dataset):
    """Phase 4 — component re-comparison: this is where the same_* comparison
    happens (NOT phase 3, which is subdivision only). Each subdivision sub-piece
    is compared with the component it covers; cells match by construction, so the
    relation is same_object / same_point when the colour is kept, else same_shape
    (colour changed); each line tagged [from split]/[from assemble]. Publishes
    `ctx['recomparison']` (the per-sub-piece relations) — the phase-4 output the
    bg rules consume (arc_solver.bg_advance phase 4 removes colour-kept
    sub-pieces from the component lists)."""
    findings = ctx.get("subdivision", {}).get("findings", [])
    recomp, by_pair, n = [], {}, 0
    for f in findings:
        parts_rel = []
        for part in f["parts"]:
            kept = part["part_color"] == f["whole_color"]
            rel = ("same_object" if (kept and part["kind"] == "O")
                   else "same_point" if kept else "same_shape")
            parts_rel.append({**part, "rel": rel})
            n += 1
            by_pair.setdefault(f["pair"], []).append(
                f"{rel} {part['sub']} = {part['ref']}  [from {f['direction']}]")
        recomp.append({"pair": f["pair"], "direction": f["direction"],
                       "whole_idx": f["whole_idx"], "whole_color": f["whole_color"],
                       "parts": parts_rel})
    ctx["recomparison"] = recomp
    lines = []
    for p in sorted(by_pair):
        lines.append(f"Pair {p}:")
        lines.extend("  " + ln for ln in by_pair[p])
    head = f"component re-comparison — {n} sub-piece correspondence(s)"
    return _block(head, lines)


def step_task_pattern(ctx, dataset):
    """Phase 6 — Task Patterns: the patterns whose filter holds on EVERY demo
    pair (∀), over the phase-2/4 ``same_*`` match results. Background comes only
    from ``bg_cand``; when a grid's bg is unresolved the firing lines are
    prefixed ``bg not resolved``. Bare ``{name} ✓`` per matching pattern.
    Display/hypothesis only; not consumed downstream."""
    res = arc_solver.task_patterns(ctx["profile"], ctx.get("bg_cand"))
    ctx["patterns"] = res
    prefix = "" if res["bg_resolved"] else "bg not resolved  "
    lines = [f"{prefix}{p['name']} ✓" for p in res["patterns"] if p["matched"]]
    return _block("Pattern Hypothesis:", lines or ["(none)"])


def _hyp_order() -> list:
    """Phase-5 comparator order — the canonical ``comparator_names()`` with the
    intra-grid ``touching`` shown as the ``touching_delta`` state-change. Driven
    by the registry, so future comparators flow in automatically."""
    return ["touching_delta" if c == "touching" else c
            for c in arc_search.comparator_names()]


def _drop_bg_grid(gs, bg):
    """A copy of a grid summary with the bg-colour objects/points removed and the
    intra-grid relations (touching/inside) recomputed over what remains."""
    objs = [o for o in gs["objects"] if o["color"] != bg]
    pts = [p for p in gs["points"] if p["color"] != bg]
    g2 = dict(gs)
    g2["objects"], g2["points"] = objs, pts
    g2["n_objects"], g2["n_points"] = len(objs), len(pts)
    g2["shapes"] = [arc_grids.normalize_shape(o) for o in objs]
    return arc_profile.attach_relations(g2)


def _hyp_pair_d(d, bg_in=None, bg_out=None) -> dict:
    """The demo-pair dict the phase-5 hypothesis runs over. If the grid's bg is
    resolved by phase 5, the bg-colour objects are dropped first (and match +
    relations recomputed over the non-bg components) so they don't participate;
    otherwise the original profile pair is used unchanged."""
    if bg_in is None and bg_out is None:
        return d
    gin = _drop_bg_grid(d["input"], bg_in) if bg_in is not None else d["input"]
    gout = _drop_bg_grid(d["output"], bg_out) if bg_out is not None else d["output"]
    return {"input": gin, "output": gout, "match": arc_profile.match_pair(gin, gout)}


def _hyp_pair_set(d) -> set:
    """The comparators triggering on one (already bg-resolved) demo pair: the
    registry atom runs ALL comparators, with the intra-grid ``touching`` swapped
    for the ``touching_delta`` state-change."""
    s = arc_search._pair_comparators(d)            # all registered comparators
    s.discard("touching")
    ch = arc_solver.touching_changes(d, 0, exclude_bg=False)   # forget bg
    if ch["gained"] or ch["lost"]:
        s.add("touching_delta")
    return s


# ── phase-5 perception: per-comparator per-pair param + ∀ conclusion ─────
# Each transform-family comparator (+ touching_delta) reports, per demo pair,
# the parameter of its instance(s): the actual value when the pair's instances
# AGREE, else the token ``multi`` (PB-l: multi = real within-pair disagreement,
# so a uniform many-object transform still reads constant). The line then states
# a ∀ conclusion over the per-pair values. ``inside`` has no parameter → bare.
_MULTI = "multi"


def _moved_params(d):
    return [tuple(m["transform"]["vector"])
            for g in d["match"]["shape_groups"] for m in g.get("moves", [])]


def _rotated_params(d):
    return [t["transform"]["deg"]
            for t in arc_grids.rotated_pairs(d["input"], d["output"])]


def _reflected_params(d):
    return [t["transform"]["axis"]
            for t in arc_grids.reflected_pairs(d["input"], d["output"])]


def _recolored_params(d):
    return [(t["transform"]["from"], t["transform"]["to"])
            for t in arc_grids.recolored_pairs(d["input"], d["output"])]


def _touching_delta_params(d):
    ch = arc_solver.touching_changes(d, 0, exclude_bg=False)
    return ["gained"] * len(ch["gained"]) + ["lost"] * len(ch["lost"])


#: comparator -> per-pair parameter extractor. A comparator absent here renders
#: bare (``inside``). Registry-shaped: a new transform comparator flows into the
#: phase-5 perception by registering an extractor + a ``_render_param`` arm.
_PAIR_PERCEPTION = {
    "moved": _moved_params,
    "rotated": _rotated_params,
    "reflected": _reflected_params,
    "recolored": _recolored_params,
    "touching_delta": _touching_delta_params,
}


def _render_param(comp, p) -> str:
    if comp == "moved":
        return f"({p[0]},{p[1]})"
    if comp == "rotated":
        return str(p)
    if comp == "reflected":
        return "H-axis" if p == "horizontal" else "V-axis"
    if comp == "recolored":
        return f"{arc_grids.color_name(p[0])}→{arc_grids.color_name(p[1])}"
    if comp == "touching_delta":
        return p                                   # 'gained' / 'lost'
    return str(p)


def _pair_value(params):
    """One pair's value: the agreed parameter if all the pair's instances match
    (PB-l b), else ``multi``. Empty (shouldn't occur for a ∀ comparator) → multi."""
    uniq = set(params)
    return next(iter(uniq)) if len(uniq) == 1 else _MULTI


def _conclusion(comp, values) -> str:
    """∀ conclusion over the per-pair values (a parameter or ``multi``). Any
    ``multi`` (within-pair disagreement) ⟹ ``varies``; else, per family:
    constant (all equal) → directional → varies."""
    if _MULTI in values:
        return "varies"
    if comp == "moved":
        if len(set(values)) == 1:
            return "constant"
        if all(dc == 0 for (_dr, dc) in values):
            return "all vertical: (X,0)"
        if all(dr == 0 for (dr, _dc) in values):
            return "all horizontal: (0,Y)"
        return "varies"
    if comp == "reflected":
        if len(set(values)) == 1:
            return "all H-axis" if values[0] == "horizontal" else "all V-axis"
        return "varies"
    if comp == "touching_delta":
        if len(set(values)) == 1:
            return "all gained" if values[0] == "gained" else "all lost"
        return "varies"
    # rotated, recolored: constant / varies
    return "constant" if len(set(values)) == 1 else "varies"


def _comparator_line(comp, pair_ds) -> str:
    """Phase-5 line for one ∀-firing comparator: bare ``✓`` for a parameter-less
    comparator (``inside``), else ``{comp} → {item} | … → {conclusion}``."""
    if comp not in _PAIR_PERCEPTION:
        return f"{comp} ✓"
    extract = _PAIR_PERCEPTION[comp]
    values = [_pair_value(extract(d)) for d in pair_ds]
    items = [_MULTI if v == _MULTI else _render_param(comp, v) for v in values]
    return f"{comp} → {' | '.join(items)} → {_conclusion(comp, values)}"


def step_comparators_hypothesis(ctx, dataset):
    """Phase 5 — Comparators Hypothesis: the comparators that trigger on EVERY
    demo pair (∀), running ALL registered comparators (comparator_names()), with
    ``touching_delta`` shown instead of the intra-grid ``touching``. If the bg is
    resolved by phase 5 (``ctx['bg_cand']``), bg-colour objects are excluded from
    the checks. Each firing comparator reports its per-pair parameter(s) + a ∀
    conclusion (``inside`` stays bare). Display/hypothesis only; the ∃ task_tokens
    (gate) are untouched."""
    bc = ctx.get("bg_cand")
    pair_ds = []
    for i, d in enumerate(ctx["profile"]["train"]):
        bg_in = bc["train"][i]["input"]["bg"] if bc else None
        bg_out = bc["train"][i]["output"]["bg"] if bc else None
        pair_ds.append(_hyp_pair_d(d, bg_in, bg_out))
    per = [_hyp_pair_set(d) for d in pair_ds]
    comps = arc_search.forall_comparators(per, _hyp_order())
    lines = [_comparator_line(c, pair_ds) for c in comps]
    return _block("Comparators Hypothesis:", lines or ["(none)"])


def step_background(ctx, dataset):
    bg = arc_solver._resolve_solver_bg(ctx.get("bg_cand"))
    b = arc_solver.stage_background(ctx["profile"], bg)
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
    (3, "Subdivision", GENERAL_STAR, step_subdivision,
     "arc_grids.subdivisions(inset) — input object partitioned by ≥2 output insets",
     "subdivision partitions (B → B1,B2,…)"),
    (4, "Component Re-Comparison", GENERAL_STAR, step_objcomp,
     "step-3 findings · same_object/same_point/same_shape(sub-piece, component) per sub-piece",
     "sub-piece ↔ component correspondences"),
    (5, "Comparators Hypothesis", GENERAL, step_comparators_hypothesis,
     "arc_search.forall_comparators over per-pair sets — touching_delta (arc_solver.touching_changes, bg-forgotten) replaces intra-grid touching; ∀ all pairs, add-only",
     "comparator hypothesis (∀-pair comparators)"),
    (6, "Task Patterns", GENERAL_STAR, step_task_pattern,
     "arc_solver.task_patterns over phase-2/4 same_* matches (addition/subtraction/recoloring/moving/rotation/reflection; ∀ pairs; bg from bg_cand)",
     "task-pattern hypothesis"),
    (7, "Background + state-change", GENERAL_STAR, step_background,
     "arc_solver.stage_background(bg from bg_cand, touching_changes(_correspondence, _touch_set))",
     "bg · changes (gained/lost/maintained)"),
    (8, "Roles", SEMI, step_roles,
     "arc_solver.stage_roles(_moved_in, _touch_set, _comp)", "stage1 (roles)"),
    (9, "Persistence + combo", SPECIMEN, step_persistence,
     "arc_solver.stage_persistence(_moved_in, _lbl)", "stage2 (persistence ∀demo + verdict)"),
    (10, "Selectors", SEMI, step_selectors,
     "arc_solver.stage_selectors(_selectors_for(_comp, _base_shape))", "stage3 (selectors)"),
    (11, "Rule", SPECIMEN, step_rule, "arc_solver.stage_rule (static)", "stage4 (rule)"),
    (12, "Verify", SPECIMEN, step_verify,
     "arc_solver.stage_verify(apply_rule(_shape_roles, _move_direction, _slide, _render))",
     "stage5 (per-demo match)"),
    (13, "Apply test → ANSWER", SPECIMEN, step_apply,
     "arc_solver.stage_apply(apply_rule)", "stage6 + answer grid"),
]


#: PROPOSED future home for each step's inline engine/uses — the real MindsOS
#: feature + location it should map to. Aspirational (the demo runs D3-inline
#: today; only step 2 actually discovers through the layer). Rows 3/5/6 unsettled.
STEP_TARGETS = {
    1: "L4 task intake → TaskRun + L3 perceive chain via cl.invoke (find_pipeline) · mindsos_intelligence/orchestrator.py + mindsos_capacity/pipeline.py",
    2: "L4 phase_1 sweep — L3 profilers (compare_*, same_*) · mindsos_intelligence/builtins/phase1_v0.py + mindsos_capacity",
    3: "L3 derivation — subdivision (inset partition) over the profile · mindsos_capacity (→ L4 induce/learner)",
    4: "L3 reasoning — re-compare derived sub-pieces against perceived components (same_*) · mindsos_capacity (→ L4 induce/learner)",
    5: "L4 phase_1 sweep — L3 comparators/predicates (moved/touching/inside/transforms) · mindsos_intelligence/builtins/phase1_v0.py + mindsos_capacity",
    6: "L3 comprehension — task-pattern hypothesis from the profile · mindsos_capacity (→ L4 induce/learner)",
    7: "L3 derivation+reasoning (detect/reconcile background; touching_delta) via invoke · mindsos_capacity",
    8: "L3 reasoning — role assignment over state-change · mindsos_capacity",
    9: "L4 induction — agrees-across-demos hypotheses fold · mindsos_intelligence (orchestrator/learner)",
    10: "L3 reasoning/scoring — synthesize_selector via invoke · mindsos_capacity",
    11: "L4 plan construction → Plan/Pipeline chain artifact · mindsos_intelligence/chain_artifacts.py",
    12: "L4 sufficiency — sufficient_predicate / replan_check · mindsos_intelligence/orchestrator.py",
    13: "L4 execution (PipelineRun) + L5 consolidation → Episode/Memory · mindsos_intelligence/consolidation.py",
}


#: One-line description of what each phase does (for `./arc solve --phases`).
STEP_DESC = {
    1: "Load the raw task and perceive each grid — objects (8-connected, ≥2 cells), points, shapes, palette, dims.",
    2: "Run the profilers — same_object/shape/point, same_cell_count, same_bbox_area, and the dim/palette deltas.",
    3: "Detect subdivision — an input object split into ≥2 disjoint output insets (B1, B2, …) that cover it exactly.",
    4: "Re-compare each subdivision sub-piece against the component it covers — same_object/same_point if the colour is kept, else same_shape.",
    5: "List the comparators that trigger on EVERY demo pair (∀) — the comparator hypothesis (moved, touching_delta, inside, recolored, rotated, reflected); touching_delta = touching status change over correspondence, shown instead of intra-grid touching.",
    6: "Infer the task pattern from the profile — e.g. addition (dims + palette preserved, all non-bg inputs kept, a new object appears).",
    7: "Propose the background colour, build the in→out correspondence, and classify touching changes (gained/lost/maintained).",
    8: "Classify the changed objects into roles — mover, target, background.",
    9: "Test which capabilities persist across all demos and form the (move, touching) combination verdict.",
    10: "For each role, find the minimal selector that discriminates it across every demo (tie-break → shape).",
    11: "Assemble the transformation rule — slide the mover toward the target until touching (hardcoded for #8).",
    12: "Apply the rule to every demo and check it reproduces each output exactly.",
    13: "Apply the rule to the test input to produce the answer grid (test output withheld).",
}


def run_all(task_id: str, dataset: dict) -> Dict[str, Any]:
    """Run all steps in-memory (no checkpoints) — used by the gate. Advances the
    persistent ``bg_state`` after each phase (same as the runner) so ``bg_cand``
    is available to the steps that read it (phase 6, the background stage)."""
    ctx: Dict[str, Any] = {"task_id": task_id}
    for (n, _name, _scope, fn, _eng, _prod) in STEPS:
        fn(ctx, dataset)
        if n >= 1 and "raw" in ctx:
            arc_solver.bg_advance(ctx, n)
    return ctx
