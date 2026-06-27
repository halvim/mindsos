"""solve(task, step) — run the pipeline up to `step`, checkpointing each step.

`solve(t, s)` loads cached checkpoints for steps < s and (re)computes step s.
A missing earlier step is computed on the way. Checkpoints (full ctx) live in
``runs/<task_id>/step-<n>.json``. Invoke via the `solve` script: `./solve 8 4`.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict

from intelligence_demo.arc1.spike import arc_grids, arc_capacities, arc_solver
from intelligence_demo.arc1.solve import pipeline

_HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(_HERE, "runs")
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


def _ckpt(task_id, n):
    return os.path.join(RUNS, task_id, f"step-{n}.json")


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
    print(_c("1", "mindsos-arc-solve") + _c("2", "  · in-process instance (no docker)") +
          f"   run: runs/{task_id}/")
    print(_c("2", f"  CapacityLayer — {len(cat)} capacities installed"))
    for ph, names in by_phase.items():
        print(_c("2", f"    {ph:<14}") + _c("36", " ".join(names)))


def _print_step(n, name, scope, functions, uses_prefix, produces, result, status, task_id):
    bar = "─" * max(4, 60 - len(name))
    print()
    print(_c("1", f"── STEP {n} · {name} ") + _c("2", bar) + "  " + _scope_tag(scope, task_id))
    st = _c("32", "computed") if status == "computed" else _c("2", "cached ✓")
    tail = _c("2", f"→ step-{n}.json") if status == "computed" else _c("2", f"(step-{n}.json)")
    print(f"   status   {st}  {tail}")
    print(_c("2", "   uses     ") + _c("2", uses_prefix + " · ") + functions)
    print(_c("2", "   → future ") + _c("36", pipeline.STEP_TARGETS.get(n, "—")))
    print(_c("2", "   produces ") + produces)
    print(_c("2", "   result   ") + _c("32" if "ANSWER" in result or "✓" in result else "0", result))


def solve(task_arg, step):
    dataset = arc_grids.load_dataset()
    task_id = _resolve_task(dataset, task_arg)
    os.makedirs(os.path.join(RUNS, task_id), exist_ok=True)
    cl = arc_capacities.fresh_layer()  # the instance (perceive caps live here)
    _print_instance(cl, task_id)
    print(_c("2", f"  task {task_id} · {len(dataset['train'][task_id]['train'])} train pairs + "
                  f"{len(dataset['train'][task_id]['test'])} test"))

    ctx: Dict[str, Any] = {"task_id": task_id}
    for (n, name, scope, fn, functions, produces) in pipeline.STEPS[:step]:
        ck = _ckpt(task_id, n)
        uses_prefix = "task input" if n == 1 else f"step-{n-1} ctx"
        rkey, nkey = f"_result_{n}", f"_name_{n}"
        cached = False
        if n < step and os.path.exists(ck):
            with open(ck, encoding="utf-8") as fh:
                loaded = json.load(fh)
            # recompute if the checkpoint predates result/name stamping OR was
            # written under a different phase layout (name mismatch → stale).
            if rkey in loaded and loaded.get(nkey) == name:
                ctx = loaded
                _print_step(n, name, scope, functions, uses_prefix, produces, loaded[rkey], "cached", task_id)
                cached = True
        if not cached:
            result = fn(ctx, dataset)
            ctx[rkey], ctx[nkey] = result, name
            with open(ck, "w", encoding="utf-8") as fh:
                json.dump(ctx, fh)
            _print_step(n, name, scope, functions, uses_prefix, produces, result, "computed", task_id)

    print(_c("2", "═" * 71))
    ans = ctx.get("answer")
    nph = len(pipeline.STEPS)
    if step >= nph and ans is not None:
        print(_c("1", f" solved {task_id}") + _c("2", f" · steps 1–{nph} · ") +
              _c("32", f"answer {len(ans)}×{len(ans[0])}"))
    else:
        print(_c("2", f" {task_id} · ran through step {step} · checkpoints in runs/{task_id}/"))


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
    from intelligence_demo.arc1.spike import arc_search
    inf = arc_search.inferences()
    print(_c("1", "arc — declared inference edges"))

    def show(edges):
        for parent, children in edges:
            print("  " + _c("36", parent) + _c("2", " ⟹ ") + ", ".join(children))

    note = {
        ("inside",): "sound 0/400",
        ("same_object",): "sound 0/400 (same_shape token includes identical objects)",
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
