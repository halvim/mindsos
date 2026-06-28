#!/usr/bin/env python3
"""
Leaf-Learning NOVELTY — deterministic shape generator (PERCEPTION_LEAF_NOVELTY_PREREG.md §1).

64x64 grid, OUTLINE-rendered shapes from a known atom hierarchy with ground truth at every level:
    pixel(intensity) -> point -> line-segment -> polygon{rectangle, triangle}   + circle (curved/withholdable)

Controls baked in (frozen pre-reg §1/§4):
  - noise sweep  sigma in {0, .05, .1, .2}
  - scale sweep  s in [0.6, 1.6]
  - near-miss (PB-5): superellipse between polygon and circle, curvature swept fine->coarse,
    so the genuine (sub-tolerance) blind-spot regime is present, not only clean circles.
  - arc-withholding control is a CONSUMER-side flag (the generator always knows the truth;
    the chain is denied the circle leaf) -- so the generator can grade fabrication.

Determinism: seed -> identical float32 arrays on ANY machine (numpy only). The frozen test set is
serialized to .npz so the MindsOS chain (in-sandbox + Linux) and the torch CNN baseline (Linux)
consume the IDENTICAL data -> P0 parity is comparable (AM/PB-G).

Run:
    python leaf_novelty_generator.py            # writes leaf_novelty_data.npz + prints a summary
"""
import json, numpy as np

GRID = 64
SIGMAS = [0.0, 0.05, 0.1, 0.2]
SCALE_RANGE = (0.6, 1.6)
CLASSES = ["triangle", "rectangle", "circle"]          # in-vocab shape set
CLS_IDX = {c: i for i, c in enumerate(CLASSES)}
STROKE = 1.1                                            # gaussian stroke sigma (px)

# near-miss curvature levels: superellipse exponent p. p=2 -> circle; p->inf -> square.
# We bow a SQUARE's edges outward by fraction f instead (cleaner "near-polygon").
# f=0 -> exact square (polygon); f large -> rounded/curved. Swept fine so sub-tolerance exists.
NEARMISS_F = [0.04, 0.08, 0.15, 0.30]                   # bow fraction of half-width


# ----------------------------- rasterization -----------------------------
def _blank():
    return np.zeros((GRID, GRID), np.float32)


def _stamp(img, xs, ys):
    """Add a gaussian stroke at sub-pixel sample locations (vectorized over a 3x3 nbhd)."""
    xi, yi = np.round(xs).astype(int), np.round(ys).astype(int)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            px, py = xi + dx, yi + dy
            m = (px >= 0) & (px < GRID) & (py >= 0) & (py < GRID)
            d2 = (px - xs) ** 2 + (py - ys) ** 2
            w = np.exp(-d2 / (2 * STROKE ** 2))
            np.add.at(img, (py[m], px[m]), w[m])
    return img


def _polyline(img, pts, closed=True, n=900):
    pts = np.asarray(pts, float)
    segs = list(range(len(pts)))
    edges = [(segs[i], segs[(i + 1) % len(pts)]) for i in range(len(pts) - (0 if closed else 1))]
    for a, b in edges:
        t = np.linspace(0, 1, max(8, n // len(edges)))
        xs = pts[a, 0] * (1 - t) + pts[b, 0] * t
        ys = pts[a, 1] * (1 - t) + pts[b, 1] * t
        _stamp(img, xs, ys)
    return img


def _vertices(shape, cx, cy, rad, rot):
    if shape == "triangle":
        k = 3
    elif shape == "rectangle":
        k = 4
    else:
        return None
    ang = rot + np.linspace(0, 2 * np.pi, k, endpoint=False)
    if shape == "rectangle":
        # axis-ish rectangle with mild aspect, rotated
        a = rad * np.array([1.0, 0.62, 1.0, 0.62])      # alternating radii -> rectangle
        ang = rot + np.array([0.25, 0.75, 1.25, 1.75]) * np.pi
        return np.stack([cx + a * np.cos(ang), cy + a * np.sin(ang)], 1)
    return np.stack([cx + rad * np.cos(ang), cy + rad * np.sin(ang)], 1)


def render(shape, cx, cy, rad, rot, nearmiss_f=0.0):
    img = _blank()
    if shape in ("triangle", "rectangle"):
        v = _vertices(shape, cx, cy, rad, rot)
        _polyline(img, v, closed=True)
        return img, {"vertices": v, "k": len(v)}
    if shape == "circle":
        t = np.linspace(0, 2 * np.pi, 900)
        _stamp(img, cx + rad * np.cos(t), cy + rad * np.sin(t))
        return img, {"vertices": None, "k": 0, "radius": rad}
    if shape == "nearmiss":
        # square with edges bowed outward by fraction f of half-width -> "near-polygon"/curved
        v = _vertices("rectangle", cx, cy, rad, rot)
        v = _vertices("rectangle", cx, cy, rad, rot)
        # use a true square for the near-miss base
        ang = rot + np.array([0.25, 0.75, 1.25, 1.75]) * np.pi
        v = np.stack([cx + rad * np.cos(ang), cy + rad * np.sin(ang)], 1)
        for i in range(4):
            a, b = v[i], v[(i + 1) % 4]
            t = np.linspace(0, 1, 260)
            mid = a * (1 - t)[:, None] + b * t[:, None]
            # outward normal
            edge = b - a
            nrm = np.array([-edge[1], edge[0]]); nrm = nrm / (np.linalg.norm(nrm) + 1e-9)
            # ensure outward
            if np.dot(nrm, (a + b) / 2 - np.array([cx, cy])) < 0:
                nrm = -nrm
            bow = nearmiss_f * rad * np.sin(np.pi * t)          # 0 at corners, max mid-edge
            mid = mid + bow[:, None] * nrm
            _stamp(img, mid[:, 0], mid[:, 1])
        return img, {"vertices": v, "k": 4, "nearmiss_f": nearmiss_f}
    raise ValueError(shape)


# ----------------------------- dataset -----------------------------
def _sample_one(g, shape, sigma, nearmiss_f=0.0):
    s = g.uniform(*SCALE_RANGE)
    rad = 11.0 * s
    margin = rad + 4
    cx = g.uniform(margin, GRID - margin)
    cy = g.uniform(margin, GRID - margin)
    rot = g.uniform(0, 2 * np.pi)
    img, gt = render(shape, cx, cy, rad, rot, nearmiss_f)
    img = img / (img.max() + 1e-9)
    img = img + g.normal(0, sigma, img.shape)
    img = np.clip(img, 0, 1).astype(np.float32)
    gt.update(dict(shape=shape, scale=float(s), cx=float(cx), cy=float(cy),
                   rad=float(rad), rot=float(rot), sigma=float(sigma)))
    return img, gt


def make_split(n_per_cell, seed, include_nearmiss=True):
    """Balanced over (class x sigma). Returns images, class labels, sigma, plus near-miss & circle
    probes for Claim 4. GT dicts kept for inspectability checks (C1)."""
    g = np.random.default_rng(seed)
    X, y, sig, kind, gts = [], [], [], [], []
    for shape in CLASSES:
        for sigma in SIGMAS:
            for _ in range(n_per_cell):
                img, gt = _sample_one(g, shape, sigma)
                X.append(img); y.append(CLS_IDX[shape]); sig.append(sigma)
                kind.append("invocab"); gts.append(gt)
    # near-miss probes (mandatory; report-only per AM-3): curved superellipses across f and sigma
    if include_nearmiss:
        for f in NEARMISS_F:
            for sigma in (0.0, 0.1):
                for _ in range(max(8, n_per_cell // 3)):
                    img, gt = _sample_one(g, "nearmiss", sigma, nearmiss_f=f)
                    X.append(img); y.append(-1); sig.append(sigma)
                    kind.append(f"nearmiss_f{f}"); gts.append(gt)
    return (np.stack(X), np.array(y), np.array(sig, np.float32),
            np.array(kind), gts)


def main():
    # TRAIN (fit thresholds), CAL (Platt), TEST (frozen, shared with the CNN baseline)
    Xtr, ytr, str_, ktr, gtr = make_split(40, seed=0, include_nearmiss=False)
    Xca, yca, sca, kca, gca = make_split(25, seed=1, include_nearmiss=False)
    Xte, yte, ste, kte, gte = make_split(60, seed=2, include_nearmiss=True)

    np.savez_compressed(
        "leaf_novelty_data.npz",
        Xtr=Xtr, ytr=ytr, sigma_tr=str_, kind_tr=ktr,
        Xca=Xca, yca=yca, sigma_ca=sca, kind_ca=kca,
        Xte=Xte, yte=yte, sigma_te=ste, kind_te=kte,
        classes=np.array(CLASSES), grid=GRID, sigmas=np.array(SIGMAS),
    )
    # GT (vertices/level truth) kept separately for the C1 inspectability check
    def gt_pack(gts):
        return [{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in d.items()} for d in gts]
    with open("leaf_novelty_gt.json", "w") as f:
        json.dump({"test": gt_pack(gte)}, f)

    summ = {
        "grid": GRID, "classes": CLASSES, "sigmas": SIGMAS, "scale_range": SCALE_RANGE,
        "nearmiss_f": NEARMISS_F,
        "train": {"n": int(len(Xtr))}, "cal": {"n": int(len(Xca))},
        "test": {"n": int(len(Xte)),
                 "invocab": int((kte == "invocab").sum()),
                 "nearmiss": int(np.char.startswith(kte.astype(str), "nearmiss").sum())},
        "intensity_range": [float(Xte.min()), float(Xte.max())],
        "fg_frac_mean": float((Xte > 0.5).mean()),
    }
    print(json.dumps(summ, indent=2))


if __name__ == "__main__":
    main()
