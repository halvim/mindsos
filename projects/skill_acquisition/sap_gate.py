"""SAP regression gate + overfit signal — prototype (v0.1).

Loop steps 0 (pin task+test) and 5 (regression-gate). Generic: the skill's `solve_fn`
(input -> output) and `oracle_fn` (output, expected -> bool) are injected. The pinned tasks
ARE the suite; the oracle is each task's own expected output (no separate authoring).

Run: python3 sap_gate.py
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional


class Verdict(str, Enum):
    SOLVED = "solved"
    WRONG = "wrong"
    ABSTAINED = "abstained"


@dataclass
class TaskCase:
    id: str
    input: object
    expected: object                       # the oracle (K9 example / withheld answer)
    last: Optional[Verdict] = None         # verdict at last checkpoint


def run_suite(cases: List[TaskCase],
              solve_fn: Callable[[object], object],
              oracle_fn: Callable[[object, object], bool]) -> Dict[str, Verdict]:
    out: Dict[str, Verdict] = {}
    for c in cases:
        y = solve_fn(c.input)
        if y is None:
            out[c.id] = Verdict.ABSTAINED
        else:
            out[c.id] = Verdict.SOLVED if oracle_fn(y, c.expected) else Verdict.WRONG
    return out


def regressions(prev: Dict[str, Verdict], curr: Dict[str, Verdict]) -> List[str]:
    """Only solved -> not-solved counts. Abstain/wrong staying same is not a regression."""
    return [tid for tid, p in prev.items()
            if p is Verdict.SOLVED and curr.get(tid) is not Verdict.SOLVED]


def overfit_signal(newly_solved: int, capacities_added: int,
                   bootstrap: bool = False) -> str:
    # The first (seed) task pays for the whole pipeline — its ratio is meaningless.
    if bootstrap:
        return f"bootstrap (seed pipeline: {capacities_added} caps; ratio n/a)"
    if newly_solved == 0:
        return "no progress"
    if capacities_added == 0:
        return "GENERALIZING (new task solved with 0 new capacities → exit candidate)"
    r = capacities_added / newly_solved
    return f"caps/task={r:.2f} " + ("(overfit risk)" if r >= 1 else "(reusing)")


# ── smoke ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    cases = [TaskCase("t1", 2, 4), TaskCase("t2", 3, 9), TaskCase("t3", 4, 16)]
    prev = run_suite(cases, lambda x: x * x if x < 4 else None, lambda y, e: y == e)
    print("checkpoint:", {k: v.value for k, v in prev.items()})   # t3 abstains
    curr = run_suite(cases, lambda x: x * x, lambda y, e: y == e) # now t3 solves
    print("after add :", {k: v.value for k, v in curr.items()})
    print("regressions:", regressions(prev, curr))                # none
    print("signal    :", overfit_signal(newly_solved=1, capacities_added=0))
