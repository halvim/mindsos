"""
Study-2 generator (v2) for PERCEPTION_LEAF_VALIDATION_PREREG.md.

Pure numpy (sandbox-safe). Produces, deterministically from a seed:
  - main dataset: shapes x 2 substrates (outline + filled/anti-aliased) x noise x scale x rotation,
    with atom-level ground truth (vertices, segments, vertex angles, per-pixel curvature flag).
  - H6 adversarial set: occluded / partial-non-closure / rescue-positive / pure-noise / ambiguous
    / borderline-bowed (near-miss band swept fine->coarse), each labelled shape | not_a_shape and
    completable=True/False (disjoint scoring OR the AM-15 mixed stream can be assembled from these).

Splits are document-disjoint by seed (atom_train / shape_train / cal / test).

This is the frozen substrate per AM-8 (power), AM-10 (atoms+shapes), AM-14 (two substrates).
Bump N_* for the real run; defaults here are a smoke-test size.
"""
import numpy as np

GRID = 64
SS = 2               # supersample factor for anti-aliased fill
EPS = 1e-9

# AM-10 frozen sequence (+ optional crescent/arrow left out of v2 core)
SHAPES = ["triangle", "rectangle", "square", "pentagon", "hexagon",
          "circle", "star", "ellipse", "cross"]
CURVED = {"circle", "ellipse"}
NOISE = [0.0, 0.05, 0.1, 0.2]
SCALE_RANGE = (0.6, 1.6)

# ----- geometry -------------------------------------------------------------

def _rot(pts, ang, cx, cy):
    c, s = np.cos(ang), np.sin(ang)
    x, y = pts[:, 0] - cx, pts[:, 1] - cy
    return np.stack([c * x - s * y + cx, s * x + c * y + cy], axis=1)

def regular_polygon(n, cx, cy, r, rot):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False) + rot
    return np.stack([cx + r * np.cos(a), cy + r * np.sin(a)], axis=1)

def star_poly(cx, cy, r_out, r_in, rot, points=5):
    a = np.linspace(0, 2 * np.pi, 2 * points, endpoint=False) + rot
    rad = np.where(np.arange(2 * points) % 2 == 0, r_out, r_in)
    return np.stack([cx + rad * np.cos(a), cy + rad * np.sin(a)], axis=1)

def ellipse_poly(cx, cy, a, b, rot, n=96):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    pts = np.stack([cx + a * np.cos(t), cy + b * np.sin(t)], axis=1)
    return _rot(pts, rot, cx, cy)

def cross_polys(cx, cy, r, rot):
    # plus sign as union of two bars; junction at center. Return list of 4-vertex quads.
    w = r * 0.34
    hbar = np.array([[cx - r, cy - w], [cx + r, cy - w], [cx + r, cy + w], [cx - r, cy + w]])
    vbar = np.array([[cx - w, cy - r], [cx + w, cy - r], [cx + w, cy + r], [cx - w, cy + r]])
    return [_rot(hbar, rot, cx, cy), _rot(vbar, rot, cx, cy)]

def shape_vertices(shape, cx, cy, r, rot, aspect=1.0):
    """Return (list_of_polys, corner_vertices_or_None, curved_bool)."""
    if shape == "triangle":
        v = regular_polygon(3, cx, cy, r, rot); return [v], v, False
    if shape == "pentagon":
        v = regular_polygon(5, cx, cy, r, rot); return [v], v, False
    if shape == "hexagon":
        v = regular_polygon(6, cx, cy, r, rot); return [v], v, False
    if shape == "square":
        v = regular_polygon(4, cx, cy, r, rot); return [v], v, False
    if shape == "rectangle":
        v = regular_polygon(4, cx, cy, r, rot)
        v = _rot(_rot(v, -rot, cx, cy) * np.array([1.5, 0.7]) + np.array([cx * (1 - 1.5), cy * (1 - 0.7)]), rot, cx, cy)
        return [v], v, False
    if shape == "star":
        v = star_poly(cx, cy, r, r * 0.42, rot); return [v], v, False
    if shape == "circle":
        v = ellipse_poly(cx, cy, r, r, rot); return [v], None, True
    if shape == "ellipse":
        v = ellipse_poly(cx, cy, r * 1.3, r * 0.75, rot); return [v], None, True
    if shape == "cross":
        return cross_polys(cx, cy, r, rot), None, False
    raise ValueError(shape)

# ----- rasterization --------------------------------------------------------

def _points_in_poly(px, py, verts):
    inside = np.zeros(px.shape, bool)
    n = len(verts); j = n - 1
    for i in range(n):
        xi, yi = verts[i]; xj, yj = verts[j]
        cond = ((yi > py) != (yj > py)) & (px < (xj - xi) * (py - yi) / (yj - yi + EPS) + xi)
        inside ^= cond; j = i
    return inside

_GRID_CACHE = {}
def _fill_binary(polys, size):
    g = _GRID_CACHE.get(size)
    if g is None:
        ys, xs = np.mgrid[0:size, 0:size].astype(float)
        g = (xs + 0.5, ys + 0.5); _GRID_CACHE[size] = g
    xs, ys = g
    m = np.zeros((size, size), bool)
    for v in polys:
        m |= _points_in_poly(xs, ys, v)
    return m

def render(polys, curved, substrate, thickness=1):
    """Return float image in [0,1]. substrate in {'outline','filled'}."""
    fill_ss = _fill_binary([p * SS for p in polys], GRID * SS)
    if substrate == "filled":
        img = fill_ss.reshape(GRID, SS, GRID, SS).mean(axis=(1, 3))
        return img.astype(np.float32)
    # outline: boundary of the 64-res fill, optionally dilated for thickness
    fill = fill_ss.reshape(GRID, SS, GRID, SS).mean(axis=(1, 3)) > 0.5
    er = fill.copy()
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        er &= np.roll(fill, (dy, dx), axis=(0, 1))
    edge = fill & ~er
    for _ in range(thickness - 1):
        d = edge.copy()
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            d |= np.roll(edge, (dy, dx), axis=(0, 1))
        edge = d
    return edge.astype(np.float32)

def curvature_map(polys, curved):
    if not curved:
        return np.zeros((GRID, GRID), np.uint8)
    return (render(polys, curved, "outline") > 0).astype(np.uint8)

# ----- atom ground truth ----------------------------------------------------

def vertex_angles(v):
    n = len(v); ang = []
    for i in range(n):
        a, b, c = v[(i - 1) % n], v[i], v[(i + 1) % n]
        u, w = a - b, c - b
        cos = np.dot(u, w) / (np.linalg.norm(u) * np.linalg.norm(w) + EPS)
        ang.append(float(np.degrees(np.arccos(np.clip(cos, -1, 1)))))  # UNSIGNED (AM-10)
    return np.array(ang, np.float32)

def atom_gt(shape, corner_v, polys, curved):
    if corner_v is not None:
        segs = np.stack([corner_v, np.roll(corner_v, -1, axis=0)], axis=1)  # (k,2,2)
        return dict(vertices=corner_v.astype(np.float32),
                    vertex_angles=vertex_angles(corner_v),
                    segments=segs.astype(np.float32), n_vertices=len(corner_v))
    return dict(vertices=np.zeros((0, 2), np.float32),
                vertex_angles=np.zeros((0,), np.float32),
                segments=np.zeros((0, 2, 2), np.float32), n_vertices=0)

# ----- noise ----------------------------------------------------------------

def add_noise(img, sigma, rng):
    if sigma <= 0:
        return img
    return np.clip(img + rng.normal(0, sigma, img.shape), 0, 1).astype(np.float32)

# ----- one sample -----------------------------------------------------------

def make_sample(shape, sigma, substrate, rng):
    r = 22 * rng.uniform(*SCALE_RANGE) / 1.1
    cx = cy = GRID / 2 + rng.uniform(-4, 4)
    rot = rng.uniform(0, 2 * np.pi)
    polys, corner_v, curved = shape_vertices(shape, cx, cy, r, rot)
    img = add_noise(render(polys, curved, substrate), sigma, rng)
    gt = atom_gt(shape, corner_v, polys, curved)
    gt["junctions"] = np.array([[cx, cy]], np.float32) if shape == "cross" else np.zeros((0, 2), np.float32)
    gt["n_junctions"] = int(len(gt["junctions"]))
    return img, curvature_map(polys, curved), gt, curved

# ----- adversarial (H6) -----------------------------------------------------

def _bow_edges(v, f, rng):
    """Replace each straight edge with a shallow arc bowing out by fraction f (near-miss band)."""
    out = []
    n = len(v)
    for i in range(n):
        a, b = v[i], v[(i + 1) % n]
        mid = (a + b) / 2
        d = b - a; L = np.linalg.norm(d) + EPS
        nrm = np.array([-d[1], d[0]]) / L
        for t in np.linspace(0, 1, 6, endpoint=False):
            p = a + t * (b - a) + nrm * f * L * np.sin(np.pi * t)
            out.append(p)
    return np.array(out)

def make_adversarial(kind, rng, f=None):
    """Return img (outline), label, completable(bool), kind, f."""
    r = 20; cx = cy = GRID / 2; rot = rng.uniform(0, 2 * np.pi)
    base = rng.choice(["triangle", "rectangle", "pentagon"])
    v = shape_vertices(base, cx, cy, r, rot)[1]
    if kind == "occluded":                       # true shape, one edge erased -> recoverable
        img = render([v], False, "outline")
        a, b = v[0], v[1]
        yy, xx = np.mgrid[0:GRID, 0:GRID]
        mask = ((np.abs(xx - (a[0] + b[0]) / 2) < 8) & (np.abs(yy - (a[1] + b[1]) / 2) < 8))
        img[mask] = 0
        return add_noise(img, 0.05, rng), base, True, kind, None
    if kind == "partial":                        # 2 disconnected segments, genuinely not a shape
        img = np.zeros((GRID, GRID), np.float32)
        for i in [0, 2]:
            seg = render([np.array([v[i], v[(i + 1) % len(v)], v[i]])], False, "outline")
            img = np.maximum(img, seg)
        return add_noise(img, 0.05, rng), "not_a_shape", False, kind, None
    if kind == "rescue":                          # full shape, one edge buried in strong local noise
        img = render([v], False, "outline")
        a, b = v[0], v[1]; yy, xx = np.mgrid[0:GRID, 0:GRID]
        band = ((np.abs(xx - (a[0] + b[0]) / 2) < 9) & (np.abs(yy - (a[1] + b[1]) / 2) < 9))
        img = img.copy(); img[band] = np.clip(img[band] + rng.normal(0, 0.5, img[band].shape), 0, 1)
        return add_noise(img, 0.05, rng), base, True, kind, None
    if kind == "noise":
        return np.clip(rng.normal(0.15, 0.2, (GRID, GRID)), 0, 1).astype(np.float32), "not_a_shape", False, kind, None
    if kind == "ambiguous":                       # near-square rectangle (square vs rectangle)
        vv = regular_polygon(4, cx, cy, r, rot)
        vv = _rot(_rot(vv, -rot, cx, cy) * np.array([1.08, 1.0]), rot, cx, cy)
        return add_noise(render([vv], False, "outline"), 0.05, rng), "ambiguous_quad", None, kind, None
    if kind == "borderline":                      # bowed edges, near-miss f swept
        vb = _bow_edges(v, f, rng)
        img = render([vb], True, "outline")
        completable = f <= 0.06                    # low bow = still the polygon; high bow = genuinely curved
        lab = base if completable else "curved_not_polygon"
        return add_noise(img, 0.05, rng), lab, completable, kind, float(f)
    raise ValueError(kind)

# ----- dataset assembly -----------------------------------------------------

def build(seed=0, n_per_cell=6, n_adv=8):
    rng = np.random.default_rng(seed)
    imgs, labels, subs, sigmas, curveds, nverts, njunc, curvmaps = [], [], [], [], [], [], [], []
    for shape in SHAPES:
        for sub in ["outline", "filled"]:
            for sig in NOISE:
                for _ in range(n_per_cell):
                    img, cm, gt, curved = make_sample(shape, sig, sub, rng)
                    imgs.append(img); labels.append(shape); subs.append(sub)
                    sigmas.append(sig); curveds.append(curved)
                    nverts.append(gt["n_vertices"]); njunc.append(gt["n_junctions"]); curvmaps.append(cm)
    main = dict(images=np.array(imgs, np.float32), labels=np.array(labels),
                substrate=np.array(subs), sigma=np.array(sigmas, np.float32),
                curved=np.array(curveds), n_vertices=np.array(nverts, np.int16),
                n_junctions=np.array(njunc, np.int16), curvature=np.array(curvmaps, np.uint8))
    # adversarial / H6
    a_img, a_lab, a_comp, a_kind, a_f = [], [], [], [], []
    for kind in ["occluded", "partial", "rescue", "noise", "ambiguous"]:
        for _ in range(n_adv):
            im, lab, comp, k, f = make_adversarial(kind, rng)
            a_img.append(im); a_lab.append(lab); a_comp.append(comp); a_kind.append(k); a_f.append(-1.0)
    for f in [0.02, 0.04, 0.08, 0.15, 0.30]:      # borderline band
        for _ in range(n_adv):
            im, lab, comp, k, ff = make_adversarial("borderline", rng, f=f)
            a_img.append(im); a_lab.append(lab); a_comp.append(comp); a_kind.append(k); a_f.append(ff)
    if a_img:
        adv = dict(images=np.array(a_img, np.float32), labels=np.array(a_lab),
                   completable=np.array([str(c) for c in a_comp]), kind=np.array(a_kind),
                   near_miss_f=np.array(a_f, np.float32))
    else:
        adv = dict(images=np.zeros((0, GRID, GRID), np.float32), labels=np.array([], dtype="<U16"),
                   completable=np.array([], dtype="<U8"), kind=np.array([], dtype="<U12"),
                   near_miss_f=np.zeros((0,), np.float32))
    return main, adv


if __name__ == "__main__":
    import os
    d = os.path.dirname(os.path.abspath(__file__))
    # frozen splits: (name, seed, n_per_cell, n_adv). test carries the adversarial/H6 set.
    import sys
    ALL = {"test": (1000, 40, 250), "cal": (2000, 20, 0), "atom_train": (3000, 60, 0),
           "shape_train": (4000, 100, 0), "dev": (5000, 24, 120)}   # dev carries its OWN adversarial set
    want = sys.argv[1:] or ["test", "cal", "atom_train"]
    CONFIGS = [(n, *ALL[n]) for n in want]
    for name, seed, npc, nadv in CONFIGS:
        main, adv = build(seed=seed, n_per_cell=npc, n_adv=nadv)
        path = os.path.join(d, f"leaf_v2_{name}.npz")
        np.savez_compressed(path, split=name, seed=seed,
                            **{f"main_{k}": v for k, v in main.items()},
                            **{f"adv_{k}": v for k, v in adv.items()})
        line = f"{name:11s} main {str(main['images'].shape):18s} adv {adv['images'].shape}"
        if name == "test":
            cnt = {c: int((adv['completable'] == c).sum()) for c in sorted(set(adv['completable']))}
            line += f"  adv-completable {cnt}"
        print(line)
    print("frozen: block GT = n_vertices, vertex_angles, segments, curvature map, n_junctions")
