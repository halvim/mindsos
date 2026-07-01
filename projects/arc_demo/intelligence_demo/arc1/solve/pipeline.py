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
                                       "part_color": Cp, "kind": k, "pidx": j})
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
    # INPUT-ONLY enclosure sub-pieces (bg → outer + enclosed pockets), the
    # cell-level analogue of `inside`. Computed here so phases after 3 CONSUME
    # them without re-deriving; bg per grid from the already-advanced bg_cand
    # (unresolved → no enclosure). Phase 8's recolor rule fills these.
    bc = ctx.get("bg_cand")
    ctx["enclosed"] = {
        "train": [arc_grids.enclosed_bg_cells(
                      pr["input"]["cells"],
                      bc["train"][i]["input"]["bg"] if bc else None)
                  if bc and bc["train"][i]["input"]["bg"] is not None else []
                  for i, pr in enumerate(prof["train"])],
        "test": [arc_grids.enclosed_bg_cells(
                     t["input"]["cells"],
                     bc["test"][i]["input"]["bg"] if bc else None)
                 if bc and bc["test"][i]["input"].get("bg") is not None else []
                 for i, t in enumerate(prof.get("test", []))],
    }
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
            # sub-piece and the object it covers share cells by construction, so a
            # colour change is a RECOLOR (a subdivision sub-piece is a full object).
            rel = ("same_object" if (kept and part["kind"] == "O")
                   else "same_point" if kept else "recolored")
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
    res = arc_solver.task_patterns(ctx["profile"], ctx.get("bg_cand"),
                                   ctx.get("recomparison"))
    ctx["patterns"] = res
    suffix = "" if res["bg_resolved"] else " · bg not resolved"
    lines = [f"{p['name']} ✓{suffix}" for p in res["patterns"] if p["matched"]]
    return _block("Pattern Hypothesis:", lines or ["(none)"])


def _hyp_order() -> list:
    """Phase-5 comparator order — the canonical ``comparator_names()`` with the
    intra-grid ``touching`` shown as the ``touching_delta`` state-change. Driven
    by the registry, so future comparators flow in automatically."""
    return ["touching_delta" if c == "touching" else c
            for c in arc_search.comparator_names()]


# ── phase-5 perception: per-comparator per-pair param + ∀ conclusion ─────
# A "pair context" (pc) carries the FULL demo pair + the grid bgs `bg_advance`
# resolved + the phase-4 recomparison findings. Transforms run over the full
# grids (no bg exclusion); `touching`/`touching_delta` exclude the bg colour ONLY
# when that grid's bg is resolved; `inside` is the ray-based containment
# comparator `arc_grids.contained_pairs` (a inside b iff every ray from every
# cell of a hits object b; a bg-coloured object is a valid container only if it
# is itself contained — the ambient bg is excluded, an enclosed pocket kept).
# `recolored` also fires off
# subdivision sub-pieces (a sub-piece is a full object). Each comparator reports
# its per-pair parameter(s): the value when the pair's instances AGREE, else
# ``multi`` (PB-l). ``inside`` has no parameter → bare.
_MULTI = "multi"


def _pair_ctx(ctx, i, d) -> dict:
    bc = ctx.get("bg_cand")
    return {
        "d": d,
        "bg_in": bc["train"][i]["input"]["bg"] if bc else None,
        "bg_out": bc["train"][i]["output"]["bg"] if bc else None,
        "findings": [f for f in (ctx.get("recomparison") or []) if f["pair"] == i + 1],
    }


def _pair_bg_excl(pc):
    """(bg, exclude?) for touching_delta — exclude only when both grids resolved
    to the same colour."""
    bi, bo = pc["bg_in"], pc["bg_out"]
    return (bi, True) if (bi is not None and bi == bo) else (0, False)


def _inside_present(pc) -> bool:
    """`inside` over each grid = ray-based containment (`arc_grids.contained_pairs`):
    `a inside b` iff every ray from every cell of `a` hits object `b`; a
    bg-coloured object is a valid container only if it is itself contained
    (ambient bg excluded, enclosed pocket kept). Nested containment (O1⊃O2⊃P0) is
    captured, unlike the first-diff `inside_pairs`."""
    d = pc["d"]
    for side, bg in (("input", pc["bg_in"]), ("output", pc["bg_out"])):
        if arc_grids.contained_pairs(d[side], bg, bg_resolved=bg is not None):
            return True
    return False


def _hyp_pair_set(pc) -> set:
    """The comparators triggering on one demo pair (phase-5 rules): transforms
    over the full grids; `recolored` also from sub-pieces; `inside` and
    `touching_delta` exclude the bg colour when resolved."""
    d = pc["d"]
    s = {c for c in ("moved", "recolored", "rotated", "reflected")
         if arc_search._PAIR_PRED[c](d)}
    if any(p["rel"] == "recolored" for f in pc["findings"] for p in f["parts"]):
        s.add("recolored")
    if _inside_present(pc):
        s.add("inside")
    bg, excl = _pair_bg_excl(pc)
    ch = arc_solver.touching_changes(d, bg, exclude_bg=excl)
    if ch["gained"] or ch["lost"]:
        s.add("touching_delta")
    return s


def _moved_params(pc):
    d = pc["d"]
    return [tuple(m["transform"]["vector"])
            for g in d["match"]["shape_groups"] for m in g.get("moves", [])]


def _rotated_params(pc):
    d = pc["d"]
    return [t["transform"]["deg"]
            for t in arc_grids.rotated_pairs(d["input"], d["output"])]


def _reflected_params(pc):
    d = pc["d"]
    return [t["transform"]["axis"]
            for t in arc_grids.reflected_pairs(d["input"], d["output"])]


def _recolored_params(pc):
    d = pc["d"]
    out = [(t["transform"]["from"], t["transform"]["to"])
           for t in arc_grids.recolored_pairs(d["input"], d["output"])]
    for f in pc["findings"]:                        # sub-piece recolors
        for p in f["parts"]:
            if p["rel"] == "recolored":
                out.append((f["whole_color"], p["part_color"]))
    return out


def _touching_delta_params(pc):
    bg, excl = _pair_bg_excl(pc)
    ch = arc_solver.touching_changes(pc["d"], bg, exclude_bg=excl)
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


def _comparator_line(comp, pcs) -> str:
    """Phase-5 line for one ∀-firing comparator: bare ``✓`` for a parameter-less
    comparator (``inside``), else ``{comp} → {item} | … → {conclusion}``."""
    if comp not in _PAIR_PERCEPTION:
        return f"{comp} ✓"
    extract = _PAIR_PERCEPTION[comp]
    values = [_pair_value(extract(pc)) for pc in pcs]
    items = [_MULTI if v == _MULTI else _render_param(comp, v) for v in values]
    return f"{comp} → {' | '.join(items)} → {_conclusion(comp, values)}"


def step_comparators_hypothesis(ctx, dataset):
    """Phase 5 — Comparators Hypothesis: the comparators that trigger on EVERY
    demo pair (∀), with ``touching_delta`` shown instead of the intra-grid
    ``touching``. Transforms run over the full grids; ``touching``/``inside``/
    ``touching_delta`` exclude the bg colour only when that grid's bg is resolved;
    ``recolored`` also fires off subdivision sub-pieces. Each firing comparator
    reports its per-pair parameter(s) + a ∀ conclusion (``inside`` stays bare).
    Display/hypothesis only; the ∃ task_tokens (gate) are untouched."""
    pcs = [_pair_ctx(ctx, i, d) for i, d in enumerate(ctx["profile"]["train"])]
    per = [_hyp_pair_set(pc) for pc in pcs]
    comps = arc_search.forall_comparators(per, _hyp_order())
    lines = [_comparator_line(c, pcs) for c in comps]
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


def step_motivations(ctx, dataset):
    """Phase 7 — Motivations: per generator, the goals/reasons that hold on EVERY
    demo pair (∀ add-only), built from the phase-5 detector conclusions + the
    predicates and TESTED by applying the generator. Discrete generators get
    reasons only (`recolor yellow`, `rotate 180`, `… if touching`); the continuous
    `move` gets a reason (`move (dr,dc)`) and/or a goal (`move … until touching`).
    Display/hypothesis only; combined into rules in a later phase."""
    mot = arc_solver.motivations(ctx["profile"], ctx.get("bg_cand"),
                                 ctx.get("recomparison"))
    ctx["motivations"] = mot
    lines = [m for g in ("move", "recolor", "rotate", "reflect")
             for m in mot.get(g, [])]
    return _block("Motivations:", lines or ["(none)"])


def step_rules(ctx, dataset):
    """Phase 8 — Rules: assemble each phase-7 motivation into a rule and
    generatively verify it reproduces every demo output (∀); abstain otherwise.
    Families: MOVE — `move [<mover>] to [<target>] until touching` (#8) /
    `move [<sel>] by (dr,dc)` (selector-bound, reuse `_slide`/`_render`); RECOLOR
    — `recolor [enclosed] {colour}` (fill the enclosed background region, #2).
    rotate/reflect deferred (no reliable in→out object correspondence).
    Display/hypothesis; the general precursor to the hardcoded #8 stages 9–15."""
    res = arc_solver.rules(ctx["profile"], ctx.get("bg_cand"),
                           ctx.get("recomparison"),
                           (ctx.get("enclosed") or {}).get("train"))
    ctx["rules"] = res
    lines = [f"{r['text']}   ✓∀ {r['n_ok']}/{r['n']}" for r in res["rules"]]
    return _block("Rules:", lines or ["(none)"])


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
    (7, "Motivations", GENERAL_STAR, step_motivations,
     "arc_solver.motivations — per generator, ∀-holding goals/reasons from the detector conclusions + predicates (recolor/rotate/reflect = reason; move = reason+goal)",
     "generator motivations (goal/reason)"),
    (8, "Rules", GENERAL_STAR, step_rules,
     "arc_solver.rules — assemble each motivation into a rule, generatively verify ∀ (move: _apply_move_goal/_apply_move_vector; recolor: fill the phase-3 enclosed regions ctx['enclosed']); abstain otherwise. move + recolor[enclosed] (rotate/reflect deferred)",
     "verified selector-bound rules (∀)"),
    (9, "Background + state-change", GENERAL_STAR, step_background,
     "arc_solver.stage_background(bg from bg_cand, touching_changes(_correspondence, _touch_set))",
     "bg · changes (gained/lost/maintained)"),
    (10, "Roles", SEMI, step_roles,
     "arc_solver.stage_roles(_moved_in, _touch_set, _comp)", "stage1 (roles)"),
    (11, "Persistence + combo", SPECIMEN, step_persistence,
     "arc_solver.stage_persistence(_moved_in, _lbl)", "stage2 (persistence ∀demo + verdict)"),
    (12, "Selectors", SEMI, step_selectors,
     "arc_solver.stage_selectors(_selectors_for(_comp, _base_shape))", "stage3 (selectors)"),
    (13, "Rule", SPECIMEN, step_rule, "arc_solver.stage_rule (static)", "stage4 (rule)"),
    (14, "Verify", SPECIMEN, step_verify,
     "arc_solver.stage_verify(apply_rule(_shape_roles, _move_direction, _slide, _render))",
     "stage5 (per-demo match)"),
    (15, "Apply test → ANSWER", SPECIMEN, step_apply,
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
    7: "L3 reasoning — generator motivations (goal/reason) tested by applying the generators · mindsos_capacity (→ L4 induce/learner)",
    8: "L4 plan construction — bind a selector to a motivation → a candidate rule, generatively verified ∀ demos (Plan/Pipeline chain artifact; apply = L3 generators via invoke) · mindsos_intelligence/chain_artifacts.py",
    9: "L3 derivation+reasoning (detect/reconcile background; touching_delta) via invoke · mindsos_capacity",
    10: "L3 reasoning — role assignment over state-change · mindsos_capacity",
    11: "L4 induction — agrees-across-demos hypotheses fold · mindsos_intelligence (orchestrator/learner)",
    12: "L3 reasoning/scoring — synthesize_selector via invoke · mindsos_capacity",
    13: "L4 plan construction → Plan/Pipeline chain artifact · mindsos_intelligence/chain_artifacts.py",
    14: "L4 sufficiency — sufficient_predicate / replan_check · mindsos_intelligence/orchestrator.py",
    15: "L4 execution (PipelineRun) + L5 consolidation → Episode/Memory · mindsos_intelligence/consolidation.py",
}


#: One-line description of what each phase does (for `./arc solve --phases`).
STEP_DESC = {
    1: "Load the raw task and perceive each grid — objects (8-connected, ≥2 cells), points, shapes, palette, dims.",
    2: "Run the profilers — same_object/shape/point, same_cell_count, same_bbox_area, and the dim/palette deltas.",
    3: "Detect subdivision — an input object split into ≥2 disjoint output insets (B1, B2, …) that cover it exactly.",
    4: "Re-compare each subdivision sub-piece against the component it covers — same_object/same_point if the colour is kept, else same_shape.",
    5: "List the comparators that trigger on EVERY demo pair (∀) — the comparator hypothesis (moved, touching_delta, inside, recolored, rotated, reflected); touching_delta = touching status change over correspondence, shown instead of intra-grid touching.",
    6: "Infer the task pattern from the profile — e.g. addition (dims + palette preserved, all non-bg inputs kept, a new object appears).",
    7: "Motivations — per generator, the goals/reasons that hold on every demo (recolor <c>, rotate <deg>, … if touching, move … until touching), tested by applying the generator.",
    8: "Rules — assemble each motivation into a rule and generatively verify it reproduces every demo output (∀); abstain otherwise. move (move <mover> to <target> until touching / move <sel> by (dr,dc)) + recolor (recolor [enclosed] <colour> — fill the enclosed background region). rotate/reflect deferred.",
    9: "Propose the background colour, build the in→out correspondence, and classify touching changes (gained/lost/maintained).",
    10: "Classify the changed objects into roles — mover, target, background.",
    11: "Test which capabilities persist across all demos and form the (move, touching) combination verdict.",
    12: "For each role, find the minimal selector that discriminates it across every demo (tie-break → shape).",
    13: "Assemble the transformation rule — slide the mover toward the target until touching (hardcoded for #8).",
    14: "Apply the rule to every demo and check it reproduces each output exactly.",
    15: "Apply the rule to the test input to produce the answer grid (test output withheld).",
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
