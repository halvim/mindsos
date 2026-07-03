"""M1 spike entry point.

1. Stands up a live in-memory CapacityLayer, registers the arc-realm
   DataStates + perceive/profile capacities.
2. Proves find_pipeline DISCOVERS the perceive chain (no router).
3. Builds the TaskProfile for every train task and writes the debug data
   the human interface (arc_debug.html) renders.

Usage (via the launcher):
    ./run_spike [N]
where N = number of train tasks to dump (default: all 400).
"""

from __future__ import annotations

if __package__ in (None, ""):
    import os as _os
    import runpy as _runpy
    import sys as _sys
    _pkg_root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", ".."))
    _repo_root = _os.path.abspath(_os.path.join(_pkg_root, "..", ".."))
    for _p in (_repo_root, _pkg_root):
        if _p not in _sys.path:
            _sys.path.insert(0, _p)
    _runpy.run_module("intelligence_demo.arc1.spike.run_spike", run_name="__main__")
    _sys.exit(0)

import datetime as _dt
import json
import os
import sys

from mindsos_capacity.exceptions import PipelineNotFoundError
from mindsos_capacity.identifiers import capacity_iri
from mindsos_capacity.pipeline import find_pipeline

from . import arc_capacities as ac
from . import arc_gates, arc_grids, arc_metagraph, arc_profile, arc_search, arc_solver

_HERE = os.path.dirname(os.path.abspath(__file__))
_OUT_JS = os.path.join(_HERE, "arc_debug_data.js")


# ── (GF-6) find_pipeline soundness conformance ──────────────────────────
def _discover(cl, start, target):
    """The Pipeline find_pipeline yields, or None if no chain exists."""
    try:
        return find_pipeline(cl, start_datastate=start, target_datastate=target)
    except PipelineNotFoundError:
        return None


def _path_is_sound(pipe, start) -> bool:
    """A pipeline is SOUND iff every step's FULL declared input set is
    available (start, or produced by an earlier step) before it fires.
    BFS only secures the single ``via`` datastate, so a multi-input cap
    whose other inputs are never produced on the path is unsound."""
    available = {start}
    for step in pipe.steps:
        if not set(step.input_datastates) <= available:
            return False
        available.update(step.output_datastates)
    return True


def _conformance_check(cl) -> None:
    """GF-6 — make the find_pipeline soundness drift executable:

      (a) the linear perceive chains are SOUNDLY BFS-composed;
      (b) the multi-input reason caps are FOUND-but-UNSOUND — BFS fires on
          one reachable input and silently drops the rest (the §4 probe);
      (c) every registered reason cap's PRODUCES/CONSUMES edges equal its
          declared inputs/outputs (registration topology == body-canonical).
    """
    # (a) linear perceive chains — sound
    for start, target in ((ac.DS_RAW_TASK, ac.DS_SHAPE),
                          (ac.DS_RAW_TASK, ac.DS_PALETTE)):
        pipe = _discover(cl, start, target)
        assert pipe is not None and _path_is_sound(pipe, start), \
            f"perceive chain {start} -> {target} must be soundly composable"

    # (b) multi-input reason caps — BFS returns a path, but it is UNSOUND
    for target in (ac.DS_STATE_CHANGE, ac.DS_SELECTOR, ac.DS_CORRESPONDENCE):
        pipe = _discover(cl, ac.DS_GRID, target)
        assert pipe is not None, \
            f"BFS is expected to (unsoundly) return a path to {target}"
        assert not _path_is_sound(pipe, ac.DS_GRID), \
            f"{target} must NOT be soundly BFS-composable (multi-input drift)"

    # (c) registered reason edges == declared (body-canonical) deps
    view = cl.global_view()
    for cap in ac._reason_capacities():
        iri = capacity_iri(cap.category, cap.name)
        assert set(view.inputs_of(iri)) == set(cap.inputs), \
            f"{cap.name}: registered CONSUMES != declared inputs"
        assert set(view.outputs_of(iri)) == set(cap.outputs), \
            f"{cap.name}: registered PRODUCES != declared outputs"

    print("  [ok] conformance (GF-6): perceive chains sound; reason caps "
          "found-but-unsound; registered edges == declared deps.")


def _invoke_biting_check(cl, prof8, raw8) -> None:
    """D3 one-specimen spike — execute `touching_delta` THROUGH the layer for #8.

    Unlike GF-6(c) (which only checks declared == registered, and so can't see
    the body), this BITES: it runs the real body via ``cl.invoke`` and proves
      (1) it executes and **matches** the inline solver's state-change, and
      (2) the DECLARED inputs are **neither necessary nor sufficient** — the
          body reads PAIR+BACKGROUND, so feeding it the declared (touching,
          correspondence) inputs yields nothing. The registered CONSUMES
          topology is fiction relative to the executable body.
    """
    iri = capacity_iri(ac.CATEGORY_DETECTOR, "touching_delta")
    bg = arc_solver._resolve_solver_bg(arc_solver.resolve_bg(prof8, raw8))
    pair = prof8["train"][0]
    expected = arc_solver.touching_changes(pair, bg)

    # (1) real inputs the body consumes -> executes + matches the inline solver
    res = cl.invoke(iri, inputs={ac.DS_PAIR: pair, ac.DS_BACKGROUND: bg})
    assert res.success, f"touching_delta invoke failed: {getattr(res, 'error', None)!r}"
    assert res.outputs[ac.DS_STATE_CHANGE] == expected, \
        "invoked touching_delta != inline solver state-change"

    # (2) DECLARED inputs only -> body can't run (it reads PAIR/BACKGROUND)
    res2 = cl.invoke(iri, inputs={ac.DS_TOUCHING: True, ac.DS_CORRESPONDENCE: {}})
    assert res2.success and res2.outputs[ac.DS_STATE_CHANGE] is None, \
        "declared CONSUMES (touching, correspondence) should be insufficient to run the body"

    print("  [ok] D3 spike: touching_delta executes through the layer and matches "
          "#8; declared CONSUMES is neither necessary nor sufficient.")


def _gate_invariant_check(tasks) -> None:
    """The locked invariant: a comparator's gate is enabled iff its Search token
    fires — ``enabled == (cap in task_tokens)`` for all 6 comparators, every
    task. Demands (rotated/reflected ⊃ cells,area) never break it because the
    comparator firing implies its D4-invariant demands."""
    comps = arc_search.comparator_names()
    for t in tasks:
        toks = set(arc_search.task_tokens(t))
        en = t["gates"]["enabled"]
        for c in comps:
            assert en.get(c) == (c in toks), \
                f"gate invariant broken: {t['task_id']} {c} enabled={en.get(c)} token={c in toks}"
    print(f"  [ok] gate invariant: enabled == Search token for all "
          f"{len(comps)} comparators across {len(tasks)} tasks.")


def _evaluate_discrepancy_check(tasks) -> None:
    """./evaluate applies each comparator via an independent code path and
    cross-checks it against the Search token; assert ZERO discrepancies."""
    from intelligence_demo.arc1.solve import evaluate as ev
    comps = arc_search.comparator_names()
    bad = [(t["task_id"], c) for t in tasks for c in comps
           if ev._apply(c, t)["discrepancy"]]
    assert not bad, f"./evaluate discrepancies vs Search: {bad[:8]}"
    print(f"  [ok] ./evaluate: 0 discrepancies vs Search "
          f"({len(comps)} comparators × {len(tasks)} tasks).")


def _inference_soundness_check(tasks) -> None:
    """The wired token skip ``same_object ⟹ same_shape`` must be 0/400: every task
    that fires same_object must also fire same_shape (identical cells ⇒ identical
    shape_key). Makes the skip's soundness executable."""
    bad = []
    for t in tasks:
        toks = set(arc_search.task_tokens(t))
        if "same_object" in toks and "same_shape" not in toks:
            bad.append(t["task_id"])
    assert not bad, f"same_object ⟹ same_shape unsound (skip wired): {bad[:8]}"
    n = sum(1 for t in tasks if "same_shape" in set(arc_search.task_tokens(t)))
    print(f"  [ok] inference: same_object ⟹ same_shape sound 0/{len(tasks)} "
          f"(same_shape token now {n}/{len(tasks)}).")


def _operator_inference_check(tasks) -> None:
    """The operator inference ``union ⟹ inset`` must be 0/400: every task where a
    union occurs must also have inset occur (C=union(A,B) ⟹ inset(A,C)∧inset(B,C),
    so the operands are cell-subsets of the union — sound by construction). Makes
    the union→inset skip's soundness executable."""
    bad = [t["task_id"] for t in tasks
           if arc_solver.union_occurs(t) and not arc_solver.inset_occurs(t)]
    assert not bad, f"union ⟹ inset unsound (skip wired): {bad[:8]}"
    n_u = sum(1 for t in tasks if arc_solver.union_occurs(t))
    print(f"  [ok] inference: union ⟹ inset sound 0/{len(tasks)} "
          f"(union occurs {n_u}/{len(tasks)}).")


def _inside_layer_conformance(cl, tasks) -> None:
    """MindsOS wiring step 1 — the `inside` predicate now has a REAL body invoked
    THROUGH the layer (`cl.invoke`), not a stub. Prove the layer-invoked cap
    reproduces the inline perception result (`attach_relations` ->
    `contained_pairs`, bg_resolved=False) for EVERY perceived grid across the 400
    tasks — i.e. the registered cap IS the executed compute, no shadow."""
    iri = capacity_iri(ac.CATEGORY_PREDICATE, "inside")
    n_grids = 0
    for t in tasks:
        grids = [pair["input"] for pair in t["train"]] + \
                [pair["output"] for pair in t["train"]] + \
                [tg["input"] for tg in t["test"]]
        for gs in grids:
            res = cl.invoke(iri, inputs={ac.DS_PERCEIVED_GRID: gs})
            assert res.success, \
                f"inside invoke failed on {t['task_id']}: {getattr(res, 'error', None)!r}"
            assert res.outputs[ac.DS_INSIDE] == gs["inside"], \
                f"invoked inside != inline attach_relations on {t['task_id']}"
            n_grids += 1
    print(f"  [ok] wiring: inside real body invoked through the layer matches "
          f"inline perception across {n_grids} grids / {len(tasks)} tasks.")


def _l4_intake_check(cl, tasks) -> None:
    """MindsOS wiring step 2 — the L4 intake slice. Dispatch the perceive
    extractors through the REAL L4 choke point (`L4Dispatcher` -> runtime.invoke)
    for every grid and prove L4->L3 dispatch reproduces the inline perception;
    then emit a real L5 `TaskRun` chain artifact into an in-memory MentalModel.
    Proves the boundary end-to-end: L4 orchestrates, L3 computes, L5 stores."""
    from . import arc_l4
    disp = arc_l4.dispatcher(cl)
    n_grids = 0
    for t in tasks:
        grids = [p["input"] for p in t["train"]] + \
                [p["output"] for p in t["train"]] + \
                [tg["input"] for tg in t["test"]]
        for gs in grids:
            got = arc_l4.perceive_grid(disp, gs["cells"])
            assert got["objects"] == gs["objects"], \
                f"L4-dispatched extract_objects != inline on {t['task_id']}"
            assert got["points"] == gs["points"], \
                f"L4-dispatched extract_points != inline on {t['task_id']}"
            n_grids += 1
    tr = arc_l4.emit_task_run(arc_solver.TASK8)
    assert getattr(tr, "iri", None), "L5 TaskRun emit produced no artifact"
    print(f"  [ok] wiring: L4Dispatcher dispatches perceive (L3) matching inline "
          f"across {n_grids} grids; L5 TaskRun emitted for #8.")


def _mindsos_instance_check() -> None:
    """MindsOS wiring step 3 — prove the LAYERS work together on a REAL in-process
    instance (option (a), prep for (b)). Stand up the shipped stack (bootstrapped
    KnowledgeLayer + CapacityLayer with the v0/consolidate/text/dream builtins)
    with the arc caps on top, then assert:
      * L4 — the six-phase lifecycle runs to `succeeded` (Orchestrator.run_lifecycle);
      * L5 — consolidation wrote an Episode we can read back from the user's Local;
      * L3 — an arc capacity dispatches on the same instance.
    The task content through the lifecycle is the shipped v0 smoke; routing ARC
    content through it is the later phase-8/9/10 wiring."""
    from . import arc_l4
    inst = arc_l4.build_instance()
    # L3 — arc cap dispatches on the real instance
    got = arc_l4.perceive_grid(inst.dispatcher, [[1, 1, 0], [0, 0, 2]])
    assert "objects" in got and "points" in got, "arc perceive did not dispatch on the instance"
    # L4 — six-phase lifecycle runs to completion
    outcome = inst.orch.run_lifecycle({"text": "the cat sat"}, task_id="arc-smoke")
    assert outcome.status == "succeeded", f"L4 lifecycle status={outcome.status!r}"
    # L5 — consolidation wrote an Episode; read it back
    eps = arc_l4.episodes(inst)
    assert len(eps) >= 1, "L5 consolidation wrote no Episode to the Local"
    print(f"  [ok] MindsOS instance: L4 six-phase lifecycle -> succeeded, L5 "
          f"consolidation Episode read-back ({len(eps)}), arc L3 dispatchable "
          f"on a bootstrapped KL/CapacityLayer.")


def _arc_solve_layer_check(cl, dataset) -> None:
    """MindsOS wiring step 4 — the arc SOLVE runs through the layer. An L4 driver
    sequences phases 8/9/10, dispatching each as a real L3 decision cap via
    L4Dispatcher; the dispatched answer must reproduce the inline solve AND match
    the withheld test output for #8/#2/#251. Proves solve DECISIONS (not just
    perceive) execute through L4->L3."""
    from . import arc_l4
    disp = arc_l4.dispatcher(cl)
    for tid in (arc_solver.TASK8, "00d62c1b", "a5313dff"):
        if tid not in dataset["train"]:
            continue
        dispatched, inline = arc_l4.solve_through_layer(disp, tid, dataset)
        assert dispatched is not None and inline is not None, f"no solve for {tid}"
        assert dispatched["output"] == inline["output"], \
            f"L4-dispatched solve != inline answer for {tid}"
        assert dispatched["matches_withheld"] is True, \
            f"L4-dispatched solve did not match withheld test for {tid}"
    print("  [ok] arc solve: phases 8/9/10 dispatched through L4->L3 reproduce the "
          "inline answer + match the withheld test (#8/#2/#251).")


def _arc_intake_check(dataset) -> None:
    """MindsOS wiring step 5 — the real "ask" front door. A user request
    ``"solve task <ref>"`` is interpreted through the shipped Phase-1 seam
    (ADR-0195) using arc's Local hint/map/resolve bodies:

      (1) cold-start index ``"solve task 8"`` -> ``NeedsInput`` proposing the id8
          (ADR-0196; arc-Local cold-start policy, caller-controlled);
      (2) re-submitting the canonical request resolves + solves #8 (the dispatched
          answer matches the withheld test — a real ask->solve, not a stub);
      (3) the user confirms -> the Local ordering marker is set (a persisted
          capacity-state node), and a FRESH index request resolves silently.
    """
    from . import arc_intake as ai
    from mindsos_capacity.needs_input import NeedsInput
    from mindsos_intelligence import InterpretationResult, interpret

    inst = ai.build_intake(dataset)
    assert not ai.ordering_established(inst), "fresh instance must be cold-start"
    r1 = ai.solve_task(inst, "solve task 8", dataset)          # (1) cold start asks
    assert isinstance(r1, NeedsInput) and r1.missing == ai.ARC_CANON_DS, \
        "cold-start index must return NeedsInput"
    resubmit = r1.choices["yes"]["text"]
    assert resubmit == "solve task 05f2a901", resubmit

    ai.confirm_ordering(inst)                                   # (2) user confirms -> marker set
    assert ai.ordering_established(inst), "confirm must set the Local marker"
    dispatched, inline = ai.solve_task(inst, resubmit, dataset)
    assert dispatched["matches_withheld"] and dispatched == inline, \
        "canonical re-submit must solve #8 through the layer"

    r3 = interpret(inst.dispatcher, "solve task 2")            # (3) fresh index now silent
    assert isinstance(r3, InterpretationResult) and r3.resolved_reference == "00d62c1b", \
        "after confirm, an index must resolve silently"

    print("  [ok] arc intake: 'solve task <ref>' through the Phase-1 seam -> cold-start "
          "NeedsInput, re-submit solves #8, confirm sets the Local marker -> index silent.")


#: A synthetic 2-demo task for the phase-9 CONJUNCTION path: recolor to red the
#: object that is (biggest AND green). No corpus task needs a ≥2 conjunction with
#: today's condition vocabulary (probe 2026-07-01), so the ≥2 branch is gated here
#: on a constructed fixture until more comparators/predicates land.
_SYN_CONJ = {"train": {"SYN": {"train": [
    {"input":  [[3, 3, 3, 0, 0, 0, 0, 0], [3, 3, 3, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0], [3, 0, 0, 0, 0, 1, 1, 1],
                [3, 0, 0, 0, 0, 1, 1, 1], [0, 0, 0, 0, 0, 0, 0, 0]],
     "output": [[2, 2, 2, 0, 0, 0, 0, 0], [2, 2, 2, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0], [3, 0, 0, 0, 0, 1, 1, 1],
                [3, 0, 0, 0, 0, 1, 1, 1], [0, 0, 0, 0, 0, 0, 0, 0]]},
    {"input":  [[1, 1, 1, 0, 0, 0, 0, 0], [1, 1, 1, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0], [3, 3, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 3, 3, 3],
                [0, 0, 0, 0, 0, 3, 3, 3], [0, 0, 0, 0, 0, 0, 0, 0]],
     "output": [[1, 1, 1, 0, 0, 0, 0, 0], [1, 1, 1, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0], [3, 3, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 2, 2, 2],
                [0, 0, 0, 0, 0, 2, 2, 2], [0, 0, 0, 0, 0, 0, 0, 0]]}],
    "test": [{"input": [[0] * 8 for _ in range(8)],
              "output": [[0] * 8 for _ in range(8)]}]}}}


def _solve_pipeline_check(dataset, solver) -> None:
    """The arc1/solve 10-step GENERAL pipeline must solve #8 / #2 / #251 end to
    end — phase 9 selects a covering rule set and phase 10 applies it to the test
    input, matching the withheld output — and resolve the synthetic conjunction
    fixture at size 2. (The #8-specific stages 10–16 were retired 2026-07-01; the
    monolithic build_solver still runs for the arc_debug solver panel + D3 spike,
    but the pipeline no longer mirrors it.)"""
    from intelligence_demo.arc1.solve import pipeline
    for tid in (arc_solver.TASK8, "00d62c1b", "a5313dff"):
        if tid not in dataset["train"]:
            continue
        ctx = pipeline.run_all(tid, dataset)
        assert ctx["selection"] is not None, f"phase 9 found no rule set for {tid}"
        assert ctx.get("solve") and ctx["solve"]["matches_withheld"] is True, \
            f"phase 10 did not solve {tid} (test answer != withheld output)"
    # phase 9 — the ≥2 conjunction path (synthetic; no corpus consumer yet)
    sprof = arc_profile.build_profile(_SYN_CONJ, "train", "SYN")
    ssel = arc_solver.select_rules(sprof, arc_solver.rules(sprof))
    assert ssel is not None and ssel["size"] == 2, \
        f"phase-9 conjunction fixture did not resolve at size 2 ({ssel})"
    print("  [ok] arc1/solve: 10-step general pipeline solves #8/#2/#251 "
          "(phase 9 select + phase 10 apply to test) + a size-2 conjunction.")


def main(argv: list) -> int:
    limit = int(argv[1]) if len(argv) > 1 else None

    cl = ac.fresh_layer()

    # ── (2) dataflow proof ──────────────────────────────────────────────
    report = arc_profile.discovery_report(cl)
    print("find_pipeline discovery (PRODUCES/CONSUMES walk, no dispatcher):")
    for route, chain in report.items():
        print(f"  {route:24s} = {' -> '.join(c.split(':')[-1] for c in chain)}")

    # assertions: the chain is exactly the expected perceive composition
    assert report["raw_task -> shape"] == [
        ac.CAP_COMPREHEND, ac.CAP_BUILD_GRID,
        ac.CAP_EXTRACT_OBJECTS, ac.CAP_EXTRACT_SHAPES,
    ], report["raw_task -> shape"]
    assert report["raw_task -> palette"] == [
        ac.CAP_COMPREHEND, ac.CAP_BUILD_GRID, ac.CAP_EXTRACT_PALETTE,
    ], report["raw_task -> palette"]
    print("  [ok] discovered chains match the locked perceive composition.")

    # ── (2b) GF-6 conformance: find_pipeline soundness drift ────────────
    _conformance_check(cl)

    # ── (3) build profiles + dump debug data ────────────────────────────
    dataset = arc_grids.load_dataset()
    # Canonical ARC order = task IDs sorted ascending (matches arc_viewer.html).
    ids = sorted(dataset["train"])
    if limit is not None:
        ids = ids[:limit]
    tasks = [arc_profile.build_profile(dataset, "train", tid) for tid in ids]
    # Capacity gate evaluation per task (atom truth + per-cap enabled).
    for t in tasks:
        t["gates"] = arc_gates.gate_report(t)
    _gate_invariant_check(tasks)        # enabled == Search token (all comparators)
    _evaluate_discrepancy_check(tasks)  # ./evaluate agrees with Search (0 discrepancies)
    _inference_soundness_check(tasks)   # same_object ⟹ same_shape wired skip 0/400
    _operator_inference_check(tasks)    # union ⟹ inset operator skip 0/400
    _inside_layer_conformance(cl, tasks)  # wiring step 1: inside real body via cl.invoke
    _l4_intake_check(cl, tasks)           # wiring step 2: L4Dispatcher -> L3 perceive + L5 TaskRun
    _mindsos_instance_check()             # wiring step 3: real instance — L4 lifecycle + L5 consolidation
    _arc_solve_layer_check(cl, dataset)   # wiring step 4: arc solve (phases 8/9/10) dispatched L4->L3
    _arc_intake_check(dataset)            # wiring step 5: 'ask' front door — Phase-1 seam -> solve

    # Solver run (read-only, option A) — scoped to task #8 (the use case).
    solver = None
    if arc_solver.TASK8 in dataset["train"]:
        prof8 = next((t for t in tasks if t["task_id"] == arc_solver.TASK8), None)
        if prof8 is None:
            prof8 = arc_profile.build_profile(dataset, "train", arc_solver.TASK8)
        raw8 = arc_grids.get_task(dataset, "train", arc_solver.TASK8)
        solver = arc_solver.build_solver(prof8, raw_task=raw8)
        _invoke_biting_check(cl, prof8, raw8)  # D3 one-specimen spike
        _solve_pipeline_check(dataset, solver)  # arc1/solve step-pipeline parity

    payload = {
        "generated": _dt.datetime.now().isoformat(timespec="seconds"),
        "n_tasks": len(tasks),
        "discovery": report,
        "capacities": ac.ordered_catalog(),
        "search": {
            "facets": arc_search.FACETS,
            "availability": arc_search.build_availability(tasks),
        },
        "arc_metagraph": arc_metagraph.summary(),
        "gates": arc_gates.gate_catalog(),
        "solver": solver,
        "tasks": tasks,
    }
    with open(_OUT_JS, "w") as fh:
        fh.write("window.ARC_DATA = ")
        json.dump(payload, fh, separators=(",", ":"))
        fh.write(";\n")
    size_kb = os.path.getsize(_OUT_JS) // 1024
    print(f"  [ok] wrote {len(tasks)} task profiles -> "
          f"{os.path.basename(_OUT_JS)} ({size_kb} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
