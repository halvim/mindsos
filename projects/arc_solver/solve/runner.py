"""solve(task, step) — run the pipeline up to `step`, in-memory.

`solve(t, s)` recomputes phases 1..s from scratch on every invocation (no
checkpoints). Invoke via the `solve` script: `./solve 8 4`.
"""
from __future__ import annotations

import sys
from typing import Any, Dict

from arc_solver.spike import arc_grids, arc_capacities, arc_solver
from arc_solver.solve import pipeline

_TTY = sys.stdout.isatty()


def _c(code, s):
    return f"\033[{code}m{s}\033[0m" if _TTY else s


def _resolve_task(dataset, arg):
    ids = sorted(dataset["train"])
    if str(arg).isdigit():
        i = int(arg)
        if not (1 <= i <= len(ids)):
            raise SystemExit(f"task index {i} out of range (1..{len(ids)})")
        return ids[i - 1]
    if arg not in dataset["train"]:
        raise SystemExit(f"unknown task id {arg!r}")
    return arg


def _scope_tag(scope, task_id):
    if scope == pipeline.SPECIMEN:
        extra = "" if task_id == arc_solver.TASK8 else " — not general for this task"
        return _c("33", f"⚑ specimen-specific (#8){extra}")
    return _c("2", f"[{scope}]")


def _print_instance(cl, task_id):
    cat = arc_capacities.ordered_catalog()
    by_phase: Dict[str, list] = {}
    for r in cat:
        by_phase.setdefault(r["phase"], []).append(r["name"])
    print(_c("1", "mindsos-arc-solve") + _c("2", "  · in-process instance (no docker)"))
    print(_c("2", f"  CapacityLayer — {len(cat)} capacities installed"))
    for ph, names in by_phase.items():
        print(_c("2", f"    {ph:<14}") + _c("36", " ".join(names)))


def _print_step(n, name, scope, functions, uses_prefix, produces, result, task_id):
    bar = "─" * max(4, 60 - len(name))
    print()
    print(_c("1", f"── STEP {n} · {name} ") + _c("2", bar) + "  " + _scope_tag(scope, task_id))
    print(_c("2", "   about    ") + _c("2", pipeline.STEP_DESC.get(n, "")))
    print(_c("2", "   uses     ") + _c("2", uses_prefix + " · ") + functions)
    print(_c("2", "   → future ") + _c("36", pipeline.STEP_TARGETS.get(n, "—")))
    print(_c("2", "   produces ") + produces)
    print(_c("2", "   result   ") + _c("32" if "ANSWER" in result or "✓" in result else "0", result))


def _bg_fmt_set(cand) -> str:
    """A candidate set as colour names: bare for a singleton (no braces), else
    ``{a, b, …}``."""
    names = [arc_grids.color_name(c) for c in cand]
    return names[0] if len(names) == 1 else "{" + ", ".join(names) + "}"


def _bg_line(bg_cand) -> str:
    """Per-grid Background Color line. A pair collapses to ``Pair{i}.bg=X`` only
    when one side resolved to X AND X is a candidate on the other side
    (consistency-guarded propagation, option C); otherwise the two sides show
    their candidate sets. The test grid always shows its own set."""
    segs = []
    for i, g in enumerate(bg_cand["train"], 1):
        ic, oc = g["input"]["cand"], g["output"]["cand"]
        ib, ob = g["input"]["bg"], g["output"]["bg"]
        pair_bg = None
        if ib is not None and ob is not None and ib == ob:
            pair_bg = ib
        elif ib is not None and ob is None and ib in oc:
            pair_bg = ib
        elif ob is not None and ib is None and ob in ic:
            pair_bg = ob
        if pair_bg is not None:
            segs.append(f"Pair{i}.bg={arc_grids.color_name(pair_bg)}")
        else:
            segs.append(f"In{i}.bg={_bg_fmt_set(ic)}")
            segs.append(f"Out{i}.bg={_bg_fmt_set(oc)}")
    segs.append(f"test.bg={_bg_fmt_set(bg_cand['test'][0]['input']['cand'])}")
    return " · ".join(segs)


def _print_bg(bg_cand) -> None:
    print(_c("2", "   Background Color  ") + _bg_line(bg_cand))


def solve(task_arg, step):
    dataset = arc_grids.load_dataset()
    task_id = _resolve_task(dataset, task_arg)
    cl = arc_capacities.fresh_layer()  # the instance (perceive caps live here)
    _print_instance(cl, task_id)
    print(_c("2", f"  task {task_id} · {len(dataset['train'][task_id]['train'])} train pairs + "
                  f"{len(dataset['train'][task_id]['test'])} test"))

    ctx: Dict[str, Any] = {"task_id": task_id}
    for (n, name, scope, fn, functions, produces) in pipeline.STEPS[:step]:
        uses_prefix = "task input" if n == 1 else f"step-{n-1} ctx"
        result = fn(ctx, dataset)
        # foundational rule 2 — after each phase, mutate the PERSISTENT
        # ctx['bg_state'] for that phase and reapply all the rules.
        if n >= 1 and "raw" in ctx:
            arc_solver.bg_advance(ctx, n)
        _print_step(n, name, scope, functions, uses_prefix, produces, result, task_id)
        if n >= 2 and "bg_cand" in ctx:
            _print_bg(ctx["bg_cand"])

    print(_c("2", "═" * 71))
    ans = ctx.get("answer")
    nph = len(pipeline.STEPS)
    if step >= nph and ans is not None:
        print(_c("1", f" solved {task_id}") + _c("2", f" · steps 1–{nph} · ") +
              _c("32", f"answer {len(ans)}×{len(ans[0])}"))
    else:
        print(_c("2", f" {task_id} · ran through step {step}"))


def phases():
    nphases = len(pipeline.STEPS)
    print(_c("1", f"arc solve — {nphases} pipeline phases"))
    print()
    for (n, name, scope, fn, engine, produces) in pipeline.STEPS:
        tag = _c("33", "⚑ #8") if scope == pipeline.SPECIMEN else _c("2", f"[{scope}]")
        print(_c("1", f"  {n:>2}  ") + _c("36", f"{name:<26}") + " " + tag)
        print(_c("2", "      " + pipeline.STEP_DESC.get(n, "")))
        print()


def inferences():
    from arc_solver.spike import arc_search
    inf = arc_search.inferences()
    print(_c("1", "arc — declared inference edges"))

    def show(edges):
        for parent, children in edges:
            print("  " + _c("36", parent) + _c("2", " ⟹ ") + ", ".join(children))

    note = {
        ("inside",): "sound 0/400",
        ("same_object",): "sound 0/400 (same_shape token includes identical objects)",
        ("union",): "sound 0/400 (operands ⊆ union; operator skip)",
    }
    print()
    print(_c("2", "wired (drives skip):"))
    for parent, children in inf["wired"]:
        line = "  " + _c("36", parent) + _c("2", " ⟹ ") + ", ".join(children)
        tag = note.get((parent,))
        if tag:
            line += _c("2", "   " + tag)
        print(line)
    print()
    print(_c("2", "requires (cross-phase demand):"))
    show(inf["requires"])
    print()
    print(_c("2", "display-only (not wired):"))
    show(inf["display"])


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--phases":
        phases()
        return
    if len(sys.argv) >= 2 and sys.argv[1] == "--inferences":
        inferences()
        return
    if len(sys.argv) < 3:
        raise SystemExit("usage: solve <task#|task_id> <step 1-10>  ·  "
                         "solve --phases  ·  solve --inferences")
    solve(sys.argv[1], int(sys.argv[2]))


if __name__ == "__main__":
    main()
