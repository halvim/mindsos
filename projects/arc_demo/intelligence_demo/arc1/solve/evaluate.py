"""evaluate(comparator, task) — apply a COMPARATOR capacity to a task (or all).

Two forms (driven by the ``evaluate`` script):

    ./evaluate <comparator>              # list its demands + implication parents
    ./evaluate <comparator> <task#|id>   # apply to one task
    ./evaluate <comparator> all          # apply to every task (bulk)

A comparator is one of the 6 capacities (``arc_search.comparator_names()``):
moved · recolored · rotated · reflected · touching · inside. Profilers
(same_object/shape/point/cell_count/bbox_area, compare_*) are NOT comparators
and are rejected.

Each application is **demand-gated**: every profiler the comparator ``requires``
must fire, else the result is FALSE (the unmet demand is printed). The result is
then cross-checked against the Search token (``arc_search.task_tokens``); a
mismatch is a DISCREPANCY (flagged + stored). A bulk run accumulates a
``capacities.json`` dict ``{task: {cap: bool}}`` and ``capacities_discrepancies.json``.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

from intelligence_demo.arc1.spike import arc_grids, arc_profile, arc_search, arc_capacities

_HERE = os.path.dirname(os.path.abspath(__file__))
CAP_JSON = os.path.join(_HERE, "capacities.json")
DISC_JSON = os.path.join(_HERE, "capacities_discrepancies.json")
_TTY = sys.stdout.isatty()


def _c(code: str, s: str) -> str:
    return f"\033[{code}m{s}\033[0m" if _TTY else s


# ── comparator application (independent of task_tokens — the "evaluate" path) ──
def _fires(cap: str, profile: dict) -> bool:
    """Apply ``cap`` over the demo pairs via the arc_grids detectors. This is a
    deliberately separate code path from ``arc_search.task_tokens`` (the Search
    index) so the two can be cross-checked for discrepancy."""
    demos = profile["train"]
    if cap == "moved":
        return any(any(g.get("moves") for g in d["match"]["shape_groups"]) for d in demos)
    if cap == "recolored":
        return any(arc_grids.recolored_pairs(d["input"], d["output"]) for d in demos)
    if cap == "rotated":
        return any(arc_grids.rotated_pairs(d["input"], d["output"]) for d in demos)
    if cap == "reflected":
        return any(arc_grids.reflected_pairs(d["input"], d["output"]) for d in demos)
    if cap == "touching":
        return any(d["input"].get("touching") or d["output"].get("touching") for d in demos)
    if cap == "inside":
        return any(d["input"].get("inside") or d["output"].get("inside") for d in demos)
    raise ValueError(f"not an applicable comparator: {cap!r}")


def _apply(cap: str, profile: dict) -> Dict[str, Any]:
    """One task: demand-gate, apply, cross-check vs Search. Returns a record."""
    toks = set(arc_search.task_tokens(profile))
    unmet = [d for d in arc_search.demands(cap) if d not in toks]
    fires = _fires(cap, profile)
    result = (not unmet) and fires
    search = cap in toks                      # the Search token (task_tokens)
    return {"task": profile["task_id"], "capacity": cap, "result": result,
            "fires": fires, "unmet_demands": unmet, "search": search,
            "discrepancy": result != search}


# ── persistence ─────────────────────────────────────────────────────────
def _load(path: str, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return default
    return default


def _store(cap: str, records: List[dict]) -> None:
    caps: Dict[str, Dict[str, bool]] = _load(CAP_JSON, {})
    disc: Dict[str, dict] = _load(DISC_JSON, {})
    for r in records:
        caps.setdefault(r["task"], {})[cap] = bool(r["result"])
        key = f"{r['task']}:{cap}"
        if r["discrepancy"]:
            disc[key] = {"task": r["task"], "capacity": cap,
                         "evaluate": r["result"], "search": r["search"],
                         "unmet_demands": r["unmet_demands"]}
        else:
            disc.pop(key, None)
    with open(CAP_JSON, "w", encoding="utf-8") as fh:
        json.dump(caps, fh, indent=2, sort_keys=True)
    with open(DISC_JSON, "w", encoding="utf-8") as fh:
        json.dump(disc, fh, indent=2, sort_keys=True)


# ── display ─────────────────────────────────────────────────────────────
def _demand_why(d: str) -> str:
    return {
        "same_shape": "same normalized shape present (in→out)",
        "same_cell_count": "equal cell count present (D4-invariant)",
        "same_bbox_area": "equal bbox area present (D4-invariant)",
    }.get(d, d)


def _list_demands(cap: str) -> None:
    print(_c("1", f"comparator {cap}") + _c("2", "  · capacity probe (in-process instance)"))
    dem = arc_search.demands(cap)
    par = arc_search.comparator_parents(cap)
    print(_c("2", "  demands  ") + (
        ", ".join(f"{_c('36', d)} ({_demand_why(d)})" for d in dem) if dem
        else _c("2", "(none)")))
    print(_c("2", "  implied by  ") + (
        ", ".join(_c("33", p) for p in par) + _c("2", "  (when it fires, this is known-true — not re-tested)")
        if par else _c("2", "(none)")))


def _print_one(r: dict) -> None:
    res = _c("32", "TRUE") if r["result"] else _c("0", "FALSE")
    line = f"  {r['task']:10} {res}"
    if r["unmet_demands"]:
        line += _c("33", f"  ⚑ demand unmet: {', '.join(r['unmet_demands'])}")
    if r["discrepancy"]:
        line += _c("31", f"  ✗ DISCREPANCY (search={r['search']})")
    print(line)


def _resolve_task(dataset: dict, arg: str) -> str:
    ids = sorted(dataset["train"])
    if str(arg).isdigit():
        i = int(arg)
        if not (1 <= i <= len(ids)):
            raise SystemExit(f"task index {i} out of range (1..{len(ids)})")
        return ids[i - 1]
    if arg not in dataset["train"]:
        raise SystemExit(f"unknown task id {arg!r}")
    return arg


def evaluate(cap: str, task_arg: Optional[str]) -> None:
    comparators = arc_search.comparator_names()
    if cap not in comparators:
        raise SystemExit(f"{cap!r} is not a comparator. choose one of: "
                         f"{', '.join(comparators)} (profilers are not ./evaluate targets)")
    if task_arg is None:                       # form 1: list demands + parents
        _list_demands(cap)
        return

    dataset = arc_grids.load_dataset()
    _list_demands(cap)
    if str(task_arg).lower() == "all":
        ids = sorted(dataset["train"])
        records = [_apply(cap, arc_profile.build_profile(dataset, "train", tid)) for tid in ids]
        _store(cap, records)
        n_true = sum(1 for r in records if r["result"])
        n_disc = sum(1 for r in records if r["discrepancy"])
        print(_c("2", "─" * 60))
        print(f"  {cap}: {_c('32', str(n_true))} true / {len(records)} tasks · "
              f"discrepancies {_c('31' if n_disc else '32', str(n_disc))}")
        if n_disc:
            for r in records:
                if r["discrepancy"]:
                    _print_one(r)
        print(_c("2", f"  → capacities.json ({len(records)} tasks) · capacities_discrepancies.json"))
    else:
        tid = _resolve_task(dataset, task_arg)
        r = _apply(cap, arc_profile.build_profile(dataset, "train", tid))
        print(_c("2", "─" * 60))
        _print_one(r)
        _store(cap, [r])
        print(_c("2", "  → capacities.json · capacities_discrepancies.json"))


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: evaluate <comparator> [task#|task_id|all]")
    cap = sys.argv[1]
    task_arg = sys.argv[2] if len(sys.argv) > 2 else None
    evaluate(cap, task_arg)


if __name__ == "__main__":
    main()
