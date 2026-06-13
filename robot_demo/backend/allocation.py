"""DM-5 — order → (arm, cell) allocation + the Plan ▸ Resolve producer.

Replaces DM-4's fixed ``decide=("arm1","home")`` thin slice with the real
deterministic resolver (``ROBOT_DEMO_OPEN_QUESTIONS.md §2``): each
``lines[].pos`` clause narrows the per-arm 3×3 shelf (``9 → … → 1``), and the
narrowing is emitted as the WS-contract §5 ``resolve`` frame so the
Plan ▸ Resolve panel goes live. Pure / MuJoCo-free / sandbox-testable.

Cell-index space is the **UI** convention (``i = row*3 + col``, ``row 0`` =
TOP); the §4 motion step maps an index → ``geom_config.shelf_cell(arm, row,
col)`` with the sim's bottom-row-0 flip. The resolver stays UI-facing so the
``above/below`` semantics match what the participant sees.

Not a CSP solver (option C, deferred): clauses narrow a candidate set with a
fixed-order tie-break; an unsatisfiable clause set yields ``winner=None`` (the
caller routes it — the gate/replan loop, not a solver flex).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .feasibility import item_kind

# ── 3×3 named cells (the built-in seed vocabulary; teachable terms are DM-6) ──
#: term → the candidate cell indices it denotes (UI space, row 0 = top).
ABSOLUTE_TERMS: Dict[str, frozenset] = {
    "top-left": frozenset({0}), "top": frozenset({1}),
    "top-center": frozenset({1}), "top-right": frozenset({2}),
    "left": frozenset({3}), "center": frozenset({4}), "middle": frozenset({4}),
    "right": frozenset({5}),
    "bottom-left": frozenset({6}), "bottom": frozenset({7}),
    "bottom-center": frozenset({7}), "bottom-right": frozenset({8}),
    # row / column bands (broader terms — narrow to 3)
    "top-row": frozenset({0, 1, 2}), "middle-row": frozenset({3, 4, 5}),
    "bottom-row": frozenset({6, 7, 8}),
}

#: relation → (Δrow, Δcol) in UI space (row 0 = top, so "above" = row − 1).
REL_OFFSETS: Dict[str, Tuple[int, int]] = {
    "above": (-1, 0), "below": (1, 0), "under": (1, 0),
    "left": (0, -1), "right": (0, 1),
}

#: shelf id (order line) → arm device-id (scenario §1: L = suction, R = jaw).
_SHELF_TO_ARM: Dict[str, str] = {
    "a1": "arm1", "arm1": "arm1", "shelf_l": "arm1", "l": "arm1",
    "a2": "arm2", "arm2": "arm2", "shelf_r": "arm2", "r": "arm2",
}


def arm_for_shelf(shelf: Optional[str]) -> str:
    return _SHELF_TO_ARM.get(str(shelf or "").lower(), "arm1")


def cell_rc(i: int) -> Tuple[int, int]:
    return i // 3, i % 3


def rc_cell(r: int, c: int) -> Optional[int]:
    return r * 3 + c if 0 <= r < 3 and 0 <= c < 3 else None


def cell_target(i: int) -> str:
    """``4`` → ``"r1c1"`` — the move target token the arm receives."""
    r, c = cell_rc(i)
    return f"r{r}c{c}"


def _cells_map(cand: set, winner: Optional[int] = None) -> Dict[int, str]:
    if winner is not None:
        return {i: ("win" if i == winner else "out") for i in range(9)}
    return {i: ("cand" if i in cand else "out") for i in range(9)}


@dataclass
class ResolveResult:
    winner: Optional[int]
    tube: Optional[int]
    clause: str
    stages: List[Dict[str, Any]]
    feasible: bool
    reason: str = ""
    arm: Optional[str] = None
    item: Optional[str] = field(default=None)


def resolve_pos(clauses: List[dict], ref_cells: Dict[str, int]) -> ResolveResult:
    """Narrow the 3×3 by each clause. ``ref_cells`` maps an item-kind → the cell
    it currently occupies (for relational clauses). Returns the winner + the
    per-stage ``cells`` maps for the resolve frame."""
    cand: set = set(range(9))
    stages: List[Dict[str, Any]] = [
        {"cap": "all shelf cells (9)", "cells": _cells_map(cand)}
    ]
    labels: List[str] = []
    tube: Optional[int] = None
    reason = ""

    for clause in clauses or []:
        ctype = (clause or {}).get("type")
        if ctype == "shelf":
            term = str(clause.get("pos", "")).lower()
            narrowed = ABSOLUTE_TERMS.get(term)
            if narrowed is None:
                reason = f"don't know the term “{term}”"
                stages.append({"cap": reason, "cells": _cells_map(set())})
                cand = set()
                labels.append(f'term “{term}”')
                break
            cand &= set(narrowed)
            labels.append(f'term “{term}”')
        elif ctype == "rel":
            rel = str(clause.get("rel", "")).lower()
            obj = clause.get("obj")
            okind = item_kind(obj) or (str(obj).lower() if obj else None)
            ref = ref_cells.get(okind) if okind else None
            off = REL_OFFSETS.get(rel)
            if ref is None or off is None:
                reason = (
                    f"can't place {rel} {obj} — it isn't on the shelf yet"
                    if off else f"don't know the relation “{rel}”"
                )
                stages.append({"cap": reason, "cells": _cells_map(set())})
                cand = set()
                labels.append(f"{rel} {obj}")
                break
            if okind == "tube":
                tube = ref
            r, c = cell_rc(ref)
            tgt = rc_cell(r + off[0], c + off[1])
            cand &= ({tgt} if tgt is not None else set())
            labels.append(f"{rel} {obj}")
        else:
            continue
        stages.append({"cap": f"{labels[-1]} → {len(cand)}", "cells": _cells_map(cand)})

    winner = min(cand) if cand else None
    if winner is not None:
        stages.append({"cap": "tie-break → 1", "cells": _cells_map(cand, winner)})
    elif not reason:
        reason = "no cell satisfies the placement"
    clause_label = " + ".join(labels) if labels else "place"
    return ResolveResult(
        winner=winner, tube=tube, clause=clause_label, stages=stages,
        feasible=winner is not None, reason=reason,
    )


def allocate(order: dict, shelf_state: Dict[str, Dict[int, str]]) -> ResolveResult:
    """Allocate the order's first line to (arm, cell). ``shelf_state`` is the
    per-arm ``{cell_index: item_kind}`` occupancy (mutated on a feasible place).

    A line with no ``pos`` clauses defaults to the shelf centre (cell 4)."""
    lines = (order or {}).get("lines") or []
    if not lines:
        return ResolveResult(None, None, "no order line", [], False, "empty order")
    line = lines[0]
    arm = arm_for_shelf(line.get("shelf"))
    occupancy = shelf_state.setdefault(arm, {})
    ref_cells = {kind: ci for ci, kind in occupancy.items()}
    clauses = line.get("pos")
    if not clauses:  # bare line → centre
        clauses = [{"type": "shelf", "pos": "center"}]
    res = resolve_pos(clauses, ref_cells)
    res.arm = arm
    res.item = line.get("item")
    if res.feasible:
        occupancy[res.winner] = item_kind(line.get("item")) or "item"
    return res


def make_allocator(
    events: Any, shelf_state: Optional[Dict[str, Dict[int, str]]] = None
) -> Callable[[dict], Tuple[str, str]]:
    """Return a ``decide(order) -> (arm_device_id, target)`` for the manager
    flow that allocates AND emits the live ``resolve`` frame.

    ``target`` is the cell token (``"r1c1"``) on the feasible path, else
    ``"home"`` (the arm still parks; placement-infeasibility routing is DM-6)."""
    state: Dict[str, Dict[int, str]] = shelf_state if shelf_state is not None else {}

    def decide(order_arg: dict) -> Tuple[str, str]:
        order = (order_arg or {}).get("order") or order_arg or {}
        res = allocate(order, state)
        events.resolve(
            brain="mgr", clause=res.clause, stages=res.stages,
            winner=res.winner, item=res.item, tube=res.tube,
        )
        arm = res.arm or "arm1"
        target = cell_target(res.winner) if res.feasible else "home"
        return arm, target

    return decide


__all__ = [
    "ABSOLUTE_TERMS",
    "REL_OFFSETS",
    "arm_for_shelf",
    "cell_rc",
    "rc_cell",
    "cell_target",
    "resolve_pos",
    "allocate",
    "make_allocator",
    "ResolveResult",
]
