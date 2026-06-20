"""ARC grid algorithm — pure Python, no MindsOS dependency.

The *would-be capacity bodies* for the perceive chain live here as plain
functions so they can be (a) wired as `Capacity.implementation` callables in
``arc_capacities.py`` and (b) called directly to compute debug data. M1 keeps
these honest and dependency-free; M-later routes them through ``invoke``.

Object model (ONTOLOGY §2.2, locked):
- Object = monochrome connected component (one color), under a chosen
  connectivity. EVERY color is extracted (no background special-case).
- Shape = colorless, translation-normalized point-set of an Object.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Tuple

Grid = List[List[int]]

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(_HERE, "..", "arc1.json")

# 4-neighbourhood (orthogonal, rank 1) and 8-neighbourhood (adds diagonal).
_ORTHOGONAL = ((-1, 0), (1, 0), (0, -1), (0, 1))
_DIAGONAL = ((-1, -1), (-1, 1), (1, -1), (1, 1))


# ── dataset ────────────────────────────────────────────────────────────

def load_dataset(path: str = _DATA) -> dict:
    with open(path) as fh:
        return json.load(fh)


def get_task(dataset: dict, split: str, task_id: str) -> dict:
    """Return the raw task ``{"train": [...], "test": [...]}``."""
    return dataset[split][task_id]


# ── derivations (capacity bodies) ───────────────────────────────────────

def dimension(grid: Grid) -> Tuple[int, int]:
    """(H, W). ONTOLOGY Dimension."""
    return (len(grid), len(grid[0]) if grid else 0)


def palette(grid: Grid) -> List[int]:
    """Sorted set of colors present (per-grid). ONTOLOGY Palette."""
    return sorted({c for row in grid for c in row})


def _components(grid: Grid) -> List[dict]:
    """All monochrome connected components under **8-connectivity** (ONTOLOGY
    §4 #1b), every color, no background special-case. Each::

        {"color": int, "cells": [(r, c), ...], "bbox": (r0, c0, r1, c1),
         "size": int}

    Deterministic order: bbox origin then color.
    """
    nbrs = _ORTHOGONAL + _DIAGONAL
    h, w = dimension(grid)
    seen = [[False] * w for _ in range(h)]
    comps: List[dict] = []
    for r in range(h):
        for c in range(w):
            if seen[r][c]:
                continue
            color = grid[r][c]
            stack = [(r, c)]
            seen[r][c] = True
            cells: List[Tuple[int, int]] = []
            while stack:
                cr, cc = stack.pop()
                cells.append((cr, cc))
                for dr, dc in nbrs:
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < h and 0 <= nc < w and not seen[nr][nc] \
                            and grid[nr][nc] == color:
                        seen[nr][nc] = True
                        stack.append((nr, nc))
            rs = [p[0] for p in cells]
            cs = [p[1] for p in cells]
            comps.append({
                "color": color,
                "cells": sorted(cells),
                "bbox": (min(rs), min(cs), max(rs), max(cs)),
                "size": len(cells),
            })
    comps.sort(key=lambda o: (o["bbox"][0], o["bbox"][1], o["color"]))
    return comps


def extract_objects(grid: Grid) -> List[dict]:
    """Objects = monochrome 8-connected components of **size ≥ 2**.

    A single cell is a Point (``extract_points``), NOT an Object — Points are
    neither Objects nor Shapes (ONTOLOGY §2.2 / §4).
    """
    return [c for c in _components(grid) if c["size"] >= 2]


def extract_points(grid: Grid) -> List[dict]:
    """Points = monochrome components of **size 1** (single cells). Same dict
    shape as objects (color, cells=[(r,c)], bbox, size=1). No Shape is derived;
    ``same_object``/``same_shape`` never apply to Points — only ``same_point``.
    """
    return [c for c in _components(grid) if c["size"] == 1]


def same_point(a: dict, b: dict) -> bool:
    """same_point: two Points equal iff **same colour AND same position**."""
    return a["color"] == b["color"] and a["cells"] == b["cells"]


def same_object(a: dict, b: dict) -> bool:
    """same_object (ONTOLOGY §3; was is_equal): two Objects equal iff **same
    color AND same position** — identical color and identical cell set. A moved
    object is NOT equal. Compares absolute cells, so it runs regardless of grid
    dims (different-dim grids simply rarely produce a match).
    """
    return a["color"] == b["color"] and a["cells"] == b["cells"]


def shape_key(shape: dict):
    """Hashable identity of a normalized Shape (its point-set)."""
    return tuple(map(tuple, shape["points"]))


def same_shape(sa: dict, sb: dict) -> bool:
    """same_shape: two Shapes equal iff identical translation-normalized
    point-set. Translation-only — NO rotation/reflection (ONTOLOGY §4 #1/#7).
    Position- and dims-independent (shapes are normalized to their bbox).
    """
    return shape_key(sa) == shape_key(sb)


def moved(a: dict, b: dict):
    """moved (transform detector; ONTOLOGY §4 #10): the **move Transform**
    between two objects — the bbox-origin translation Δ = (Δr, Δc) = b - a.

    Self-checking (total): returns ``None`` unless the full precondition holds —
    **same colour AND same shape (identical normalized point-set) AND displaced**.
    Safe to call on any object pair; incompatible pairs yield ``None``, never a
    bogus vector. Returns the move Transform ``{"kind": "translate",
    "vector": [dr, dc]}`` otherwise.
    """
    if a["color"] != b["color"]:
        return None
    if same_shape(normalize_shape(a), normalize_shape(b)):
        ar, ac = a["bbox"][0], a["bbox"][1]
        br, bc = b["bbox"][0], b["bbox"][1]
        dr, dc = br - ar, bc - ac
        if dr == 0 and dc == 0:
            return None
        return {"kind": "translate", "vector": [dr, dc]}
    return None


def touching(a: dict, b: dict) -> bool:
    """touching (intra-grid positional predicate; ONTOLOGY §3 / §4 #16): two
    components touch iff they are **different colour** AND share an 8-neighbour
    (any cell of ``a`` is 8-adjacent to any cell of ``b``).

    Total (NO_DONT_KNOW). Operand is Region/PointSet — works for Object×Object,
    Object×Point, Point×Point (each is a ``cells`` set). Same-colour pairs return
    ``False`` by definition (and never arise from 8-connected extraction anyway).
    """
    if a["color"] == b["color"]:
        return False
    bcells = {tuple(c) for c in b["cells"]}
    nbrs = _ORTHOGONAL + _DIAGONAL
    for (r, c) in a["cells"]:
        for dr, dc in nbrs:
            if (r + dr, c + dc) in bcells:
                return True
    return False


def touching_pairs(objects: List[dict], points: List[dict]) -> List[dict]:
    """All intra-grid touching pairs among a grid's components (objects + points),
    deduped + unordered (each pair once). Participants are addressed by kind +
    index into the per-grid ``objects``/``points`` lists::

        {"a": {"kind": "O"|"P", "idx": int}, "b": {"kind": "O"|"P", "idx": int}}

    Deterministic order (the combined O…P… sequence, i < j).
    """
    parts = [("O", i, o) for i, o in enumerate(objects)] + \
            [("P", i, p) for i, p in enumerate(points)]
    out: List[dict] = []
    for x in range(len(parts)):
        kx, ix, cx = parts[x]
        for y in range(x + 1, len(parts)):
            ky, iy, cy = parts[y]
            if touching(cx, cy):
                out.append({"a": {"kind": kx, "idx": ix},
                            "b": {"kind": ky, "idx": iy}})
    return out


def base_shape_name(shape: dict):
    """Recognize a Shape as a named base shape (ONTOLOGY §4 #9), parametric by
    size: ``square`` (filled n×n), ``vertical``/``horizontal`` (1-wide lines),
    ``diagonal`` (main or anti, 8-conn). Returns the name or ``None``. Single
    points (size ≤ 1) are not base shapes.
    """
    h, w = shape["dims"]
    n = shape["size"]
    if n <= 1:
        return None
    pts = set(map(tuple, shape["points"]))
    if w == 1 and n == h:
        return "vertical"
    if h == 1 and n == w:
        return "horizontal"
    if h == w and n == h * w:
        return "square"
    if h == w and n == h:
        if all((i, i) in pts for i in range(h)) or \
                all((i, h - 1 - i) in pts for i in range(h)):
            return "diagonal"
    return None


def normalize_shape(obj: dict) -> dict:
    """Colorless, translation-normalized point-set of an Object.

    ONTOLOGY §4 #1: Shape = colorless, translation-normalized (NOT
    rotation/reflection normalized).
    """
    r0, c0, r1, c1 = obj["bbox"]
    points = sorted((r - r0, c - c0) for (r, c) in obj["cells"])
    return {
        "points": points,
        "dims": (r1 - r0 + 1, c1 - c0 + 1),
        "size": obj["size"],
    }
