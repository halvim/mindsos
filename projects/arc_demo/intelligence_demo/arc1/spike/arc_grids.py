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

#: ARC colour palette (0-9) → canonical name. Used for object colour suffixes in
#: the solve viewer (e.g. ``O1.red``).
COLOR_NAMES = ["black", "blue", "red", "green", "yellow",
               "grey", "magenta", "orange", "cyan", "brown"]


def color_name(c: int) -> str:
    """Name of an ARC colour int (0-9); falls back to ``c<n>`` out of range."""
    return COLOR_NAMES[c] if 0 <= c < len(COLOR_NAMES) else f"c{c}"


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


def _bbox_area(o: dict) -> int:
    """Area of an Object/Shape bounding box (h × w). D4-invariant (rotation
    swaps h↔w; reflection preserves both)."""
    if "bbox" in o:
        r0, c0, r1, c1 = o["bbox"]
        return (r1 - r0 + 1) * (c1 - c0 + 1)
    h, w = o["dims"]                      # Shape carries dims, not bbox
    return h * w


def same_cell_count(a: dict, b: dict) -> bool:
    """same_cell_count PROFILER: two Objects/Shapes share the same cell count
    (``size``). D4-invariant — a rotation/reflection never adds or removes
    cells, so ``rotated``/``reflected`` ⟹ same_cell_count (used as their cheap
    pre-filter). Implied by ``same_shape`` (identical shape ⇒ identical count)."""
    return a["size"] == b["size"]


def same_bbox_area(a: dict, b: dict) -> bool:
    """same_bbox_area PROFILER: two Objects/Shapes share the same bounding-box
    area (h × w). D4-invariant (see ``_bbox_area``), so ``rotated``/``reflected``
    ⟹ same_bbox_area. Independent of ``same_cell_count`` (different shapes can
    share an area at a different count, or a count at a different area). Implied
    by ``same_shape``."""
    return _bbox_area(a) == _bbox_area(b)


def same_cell_count_pairs(gin: dict, gout: dict) -> List[dict]:
    """in→out Object pairs sharing a cell count (inter-grid). Near-universal as a
    task token; its value is as a ``rotated``/``reflected`` pre-filter + the
    ``same_shape ⟹ same_cell_count`` display implication."""
    return [{"in": i, "out": j}
            for i, a in enumerate(gin["objects"])
            for j, b in enumerate(gout["objects"]) if same_cell_count(a, b)]


def same_bbox_area_pairs(gin: dict, gout: dict) -> List[dict]:
    """in→out Object pairs sharing a bbox area (inter-grid). See
    ``same_cell_count_pairs``."""
    return [{"in": i, "out": j}
            for i, a in enumerate(gin["objects"])
            for j, b in enumerate(gout["objects"]) if same_bbox_area(a, b)]


def _same_normalized_shape(a: dict, b: dict) -> bool:
    """Private pure helper (GF-2): two *objects* share an identical
    translation-normalized point-set. Shared by ``moved`` — NOT a call into
    the ``same_shape`` capacity (the §0 invariant bans cap-invokes-cap *via
    the layer*, not shared pure helpers)."""
    return shape_key(normalize_shape(a)) == shape_key(normalize_shape(b))


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
    if _same_normalized_shape(a, b):  # GF-2: shared pure helper, not the cap
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


def verify_background(grid: Grid) -> dict:
    """Background-colour HYPOTHESIS for one grid — never an assumed fact.

    The solver has no validated way to identify the background yet (that is the
    D4 / CORPUS-ANALYSIS work), so this returns a *flagged candidate*, not a
    known value: the most-frequent colour as the candidate, a rough confidence
    (its share of cells), and ``verified=False``. Per RULES §7, consumers MUST
    treat an unverified background as "don't know" (abstain) — they may not
    silently trust the candidate.

    This is the sanctioned seam where a real detector/reconciler
    (``detect_background_frequency`` / ``reconcile_background``) will plug in. It
    is intentionally NOT wired into any capacity yet: after the ``inside`` ray
    rewrite no shipped capacity consumes a background (consumer discipline).

    Returns ``{"candidate": int|None, "confidence": float, "verified": bool,
    "method": str}``.
    """
    from collections import Counter
    cnt: Counter = Counter()
    total = 0
    for row in grid:
        cnt.update(row)
        total += len(row)
    if not total:
        return {"candidate": None, "confidence": 0.0, "verified": False, "method": "frequency"}
    color, freq = cnt.most_common(1)[0]
    return {"candidate": color, "confidence": freq / total,
            "verified": False, "method": "frequency"}


def _first_diff(grid: Grid, r: int, c: int, dr: int, dc: int,
                color: int, H: int, W: int):
    """Walk from ``(r, c)`` along ``(dr, dc)``; return the first cell whose
    colour differs from ``color``, or ``None`` if the grid edge is reached
    first (the ray escaped — nothing walls ``(r, c)`` off on that side)."""
    r += dr
    c += dc
    while 0 <= r < H and 0 <= c < W:
        if grid[r][c] != color:
            return (r, c)
        r += dr
        c += dc
    return None


def inside_pairs(objects: List[dict], points: List[dict],
                 dims: Tuple[int, int], grid: Grid) -> List[dict]:
    """Intra-grid enclosure (``a`` inside ``b``) by a 4-ray test — NO background
    assumption. We do not yet know the background colour, so every Object of any
    colour is a candidate container ``b`` (only ``b != a`` is required; a Point
    cannot be a container).

    ``a`` is inside ``b`` iff for EVERY cell of ``a``, a ray cast up / down /
    left / right until the colour changes lands on a cell that belongs to ``b``
    in ALL four directions. A ray that runs off the grid edge before any colour
    change means ``a`` can escape that side → not enclosed. Requiring every wall
    cell to belong to the *same* object ``b`` enforces "all the same colour and
    all belonging to ``b``".

    NOTE (no-bg consequence): an object floating in the ambient field is walled
    on four sides by that field, so it is reported inside the (large) field
    Object. Background-detection (D4) filters these later.

    Object-to-object relation::

        {"a": {"kind":"O"|"P","idx":int}, "b": {"kind":"O","idx":int}}
    """
    H, W = dims
    comps = [("O", i, o) for i, o in enumerate(objects)] + \
            [("P", i, p) for i, p in enumerate(points)]
    bsets = [{tuple(c) for c in o["cells"]} for o in objects]
    out: List[dict] = []
    for k, ai, a in comps:
        acolor = a["color"]
        walls: set = set()
        escaped = False
        for cell in a["cells"]:
            r, c = cell
            for dr, dc in _ORTHOGONAL:
                hit = _first_diff(grid, r, c, dr, dc, acolor, H, W)
                if hit is None:           # ray escaped to the border on this side
                    escaped = True
                    break
                walls.add(hit)
            if escaped:
                break
        if escaped:
            continue
        # a is inside b iff every wall cell belongs to the one object b (b != a)
        for bj, bset in enumerate(bsets):
            if k == "O" and ai == bj:
                continue
            if walls and walls <= bset:
                out.append({"a": {"kind": k, "idx": ai},
                            "b": {"kind": "O", "idx": bj}})
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


# ── transform GENERATORS (present tense; produce a transformed Object/Shape) ──
def recolor(obj: dict, color: int) -> dict:
    """Generator: an Object with every cell set to ``color`` (shape/position kept)."""
    return {"color": int(color), "cells": list(obj["cells"]),
            "bbox": tuple(obj["bbox"]), "size": obj["size"]}


def _renorm(pts):
    mr = min(r for r, c in pts)
    mc = min(c for r, c in pts)
    return sorted((r - mr, c - mc) for r, c in pts)


def _rotate_pts(points, deg):
    if deg == 90:
        pts = [(c, -r) for (r, c) in points]
    elif deg == 180:
        pts = [(-r, -c) for (r, c) in points]
    elif deg == 270:
        pts = [(-c, r) for (r, c) in points]
    else:
        pts = list(points)
    return _renorm(pts)


def _reflect_pts(points, direction):
    if direction == "horizontal":
        pts = [(-r, c) for (r, c) in points]
    elif direction == "vertical":
        pts = [(r, -c) for (r, c) in points]
    else:
        pts = list(points)
    return _renorm(pts)


def rotate_shape(shape: dict, transform) -> dict:
    """Generator: rotate a Shape by ``transform`` ∈ {90,180,270} (CW), re-normalized."""
    pts = [tuple(p) for p in shape["points"]]
    return {"points": _rotate_pts(pts, int(transform)), "size": shape.get("size", len(pts))}


def reflect_shape(shape: dict, direction: str) -> dict:
    """Generator: reflect a Shape over the horizontal / vertical axis, re-normalized."""
    pts = [tuple(p) for p in shape["points"]]
    return {"points": _reflect_pts(pts, direction), "size": shape.get("size", len(pts))}


# ── transform COMPARATORS (past tense; detect the transform across in→out) ──
def recolored(a: dict, b: dict):
    """recolor Transform between two Objects: same normalized shape AND same
    bbox-origin (position) AND **different** colour → ``{"kind":"recolor",...}``
    else ``None``. (recolor ⟹ same_shape.)"""
    if a["color"] == b["color"]:
        return None
    if tuple(a["bbox"][:2]) != tuple(b["bbox"][:2]):
        return None
    if not _same_normalized_shape(a, b):
        return None
    return {"kind": "recolor", "from": a["color"], "to": b["color"]}


def rotated(sa: dict, sb: dict):
    """rotate Transform between two Shapes: ``sb`` is a non-identity 90/180/270
    rotation of ``sa`` (and a different normalized shape) → ``{"kind":"rotate","deg":d}``
    else ``None``."""
    src = sorted(tuple(p) for p in sa["points"])
    tgt = sorted(tuple(p) for p in sb["points"])
    if tgt == src:
        return None
    for deg in (90, 180, 270):
        if _rotate_pts([tuple(p) for p in sa["points"]], deg) == tgt:
            return {"kind": "rotate", "deg": deg}
    return None


def reflected(sa: dict, sb: dict):
    """reflect Transform between two Shapes: ``sb`` is a horizontal/vertical
    reflection of ``sa`` (and a different normalized shape) → ``{"kind":"reflect","axis":d}``
    else ``None``."""
    src = sorted(tuple(p) for p in sa["points"])
    tgt = sorted(tuple(p) for p in sb["points"])
    if tgt == src:
        return None
    for d in ("horizontal", "vertical"):
        if _reflect_pts([tuple(p) for p in sa["points"]], d) == tgt:
            return {"kind": "reflect", "axis": d}
    return None


def inset(a: dict, b: dict) -> bool:
    """``a inset b``: ``a``'s cell-set is a subset of ``b``'s cell-set
    (positional, literal — no translation, no bbox). Reflexive:
    ``inset(x, x)`` is True → ``same_object ⟹ inset``."""
    bset = {(c[0], c[1]) for c in b["cells"]}
    return all((c[0], c[1]) in bset for c in a["cells"])


def subdivisions(gin: dict, gout: dict) -> List[dict]:
    """Input objects (B) partitioned by ≥2 disjoint output insets (objects +
    points) whose cell-union == B. Records ``{"in": i, "parts": [("O"|"P", j),
    ...]}``. Points are included (a single-cell part counts). Built on ``inset``
    (single source of the cell-subset test)."""
    parts_pool = [("O", j, o) for j, o in enumerate(gout["objects"])] + \
                 [("P", j, p) for j, p in enumerate(gout.get("points", []))]
    res: List[dict] = []
    for i, B in enumerate(gin["objects"]):
        Bc = {(c[0], c[1]) for c in B["cells"]}
        parts = [(k, j, o) for (k, j, o) in parts_pool if inset(o, B)]
        if len(parts) < 2:
            continue
        cov: set = set()
        tot = 0
        for (_, _, o) in parts:
            cs = {(c[0], c[1]) for c in o["cells"]}
            cov |= cs
            tot += len(cs)
        if cov == Bc and tot == len(Bc):            # disjoint cover == B
            res.append({"in": i, "parts": [(k, j) for (k, j, _) in parts]})
    return res


def union(a: dict, b: dict) -> dict:
    """Object OPERATOR (combination — dual of decomposition): combine two
    cell-sets into one **Region** (positional cell-union). The result is a
    Region (arbitrary cell-set), NOT necessarily a valid Object (it may be
    multi-colour and/or disconnected) — that is why its output DataState is
    ``DS_REGION``, not ``DS_OBJECT``.

    Algebraic identity (the registered inference): ``C = union(A, B)`` ⟹
    ``inset(A, C) ∧ inset(B, C)`` — both operands are cell-subsets of the
    union. Operators are L4-called when needed; this is the compute body."""
    cells = {(c[0], c[1]) for c in a["cells"]} | {(c[0], c[1]) for c in b["cells"]}
    return {"cells": sorted([r, c] for (r, c) in cells), "size": len(cells)}


def _nonbg_items(gs: dict, bg: int) -> List[tuple]:
    """Non-background objects + points of a grid summary as
    ``("O"|"P", idx, comp)`` triples — the union part/whole pool."""
    objs = [("O", j, o) for j, o in enumerate(gs["objects"]) if o["color"] != bg]
    pts = [("P", j, p) for j, p in enumerate(gs.get("points", [])) if p["color"] != bg]
    return objs + pts


def _union_cover(whole_gs: dict, part_gs: dict, bg: int) -> List[dict]:
    """One direction of the union check: each non-bg WHOLE object (size ≥ 2) of
    ``whole_gs`` that is exactly the **disjoint union of ≥2 non-bg parts**
    (objects + points) of ``part_gs`` at identical absolute cells (positional
    ``inset``). Records ``{"whole": ("O", idx, color), "parts": [("O"|"P", j)]}``.
    Built on ``inset`` (single source of the cell-subset test). Background is
    **excluded** (locked: union disregards the background colour)."""
    pool = _nonbg_items(part_gs, bg)
    res: List[dict] = []
    for (wk, wj, W) in _nonbg_items(whole_gs, bg):
        if wk != "O" or W["size"] < 2:
            continue
        Wc = {(c[0], c[1]) for c in W["cells"]}
        chosen, cov, tot = [], set(), 0
        for (pk, pj, P) in pool:
            if inset(P, W):                       # P's cells ⊆ W's cells
                chosen.append((pk, pj))
                cov |= {(c[0], c[1]) for c in P["cells"]}
                tot += P["size"]
        if len(chosen) >= 2 and cov == Wc and tot == len(Wc):  # disjoint cover == W
            res.append({"whole": (wk, wj, W["color"]), "parts": chosen})
    return res


def union_in_pair(gin: dict, gout: dict, bg: int) -> dict:
    """Bidirectional bg-excluded union over one in→out pair (grid summaries):
    ``split``    = an INPUT object is the disjoint union of ≥2 OUTPUT parts
                   (whole=in, parts=out);
    ``assemble`` = an OUTPUT object is the disjoint union of ≥2 INPUT parts
                   (whole=out, parts=in).
    union *occurs* on the pair iff either side is non-empty. ``inset`` is the
    single primitive both directions call."""
    return {"split": _union_cover(gin, gout, bg),       # whole=in, parts=out
            "assemble": _union_cover(gout, gin, bg)}    # whole=out, parts=in


def recolored_pairs(gin: dict, gout: dict) -> List[dict]:
    out = []
    for i, a in enumerate(gin["objects"]):
        for j, b in enumerate(gout["objects"]):
            t = recolored(a, b)
            if t:
                out.append({"in": i, "out": j, "transform": t})
    return out


def rotated_pairs(gin: dict, gout: dict) -> List[dict]:
    """Same-colour objects whose out-Shape is a rotation of the in-Shape (a real
    rotation preserves colour — scanning all shapes over-fires)."""
    out = []
    for i, a in enumerate(gin["objects"]):
        for j, b in enumerate(gout["objects"]):
            if a["color"] != b["color"]:
                continue
            # (cell_count, bbox_area) pre-filter — both D4-invariant, so a real
            # rotation MUST preserve them; mismatches are pruned before the
            # expensive shape-rotation check (necessary, not sufficient).
            if a["size"] != b["size"] or _bbox_area(a) != _bbox_area(b):
                continue
            t = rotated(gin["shapes"][i], gout["shapes"][j])
            if t:
                out.append({"in": i, "out": j, "transform": t})
    return out


def reflected_pairs(gin: dict, gout: dict) -> List[dict]:
    """Same-colour objects whose out-Shape is a reflection of the in-Shape."""
    out = []
    for i, a in enumerate(gin["objects"]):
        for j, b in enumerate(gout["objects"]):
            if a["color"] != b["color"]:
                continue
            # (cell_count, bbox_area) pre-filter — both D4-invariant (see
            # rotated_pairs); prune before the shape-reflection check.
            if a["size"] != b["size"] or _bbox_area(a) != _bbox_area(b):
                continue
            t = reflected(gin["shapes"][i], gout["shapes"][j])
            if t:
                out.append({"in": i, "out": j, "transform": t})
    return out
