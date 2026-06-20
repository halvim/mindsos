"""Software (no-GL) solid renderer over the exported body-local glTF meshes.

RECONSTRUCTED 2026-06-10 after an accidental deletion (the original was not in git;
see confirmation_docs/ROBOT_DEMO_STATE.md). API kept identical for render_all.py:
    load_geo() -> {body: (V, F, C)}          body-local verts/faces/per-vertex RGB
    world_tris(anim, geo, fi) -> (tris, cols) world-space triangles for frame fi
    render(tris, cols, eye, foc) -> HxWx3 uint8
Style matched to the existing 46 reference GIFs (painter's algorithm, fixed-light
lambert, dark backdrop, geometry supplies the floor); minor cosmetic drift vs the
original renderer is possible on NEW renders only.
"""
import os, sys, json, numpy as np, trimesh, mujoco
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "..", "web")
W, H = 600, 430
FOCAL = 640.0   # matched to the committed GIFs' framing
BG = (38, 43, 55)
LIGHT = np.array([0.35, 0.25, 1.0]); LIGHT = LIGHT / np.linalg.norm(LIGHT)


def load_geo(maxf=600):
    """Load each body mesh keeping PER-VERTEX colours (multi-colour bodies like the
    'world' body — floor + conveyor + housings — render with their real colours)."""
    mani = json.load(open(os.path.join(WEB, "manifest.json")))
    geo = {}
    for b in mani["bodies"]:
        path = os.path.join(WEB, b["file"])
        if not os.path.exists(path):
            continue
        g = trimesh.load(path, force="mesh")
        v, f = np.array(g.vertices, float), np.array(g.faces, int)
        vc = getattr(g.visual, "vertex_colors", None)
        if vc is not None and len(vc) == len(v):
            c = np.array(vc, float)[:, :3] / 255.0
        else:
            c = np.full((len(v), 3), 0.6)
        geo[b["body"]] = (v, f, c)
    return geo


def _q2m(q):
    m = np.zeros(9); mujoco.mju_quat2Mat(m, np.asarray(q, float)); return m.reshape(3, 3)


def world_tris(anim, geo, fi):
    bs = anim["bodies"]; fr = np.array(anim["frames"][fi])
    tris = []; cols = []
    for name, (v, f, c) in geo.items():
        if name not in bs:
            continue
        bi = bs.index(name)
        p, q = fr[bi, :3], fr[bi, 3:7]
        R = _q2m(q)
        vw = v @ R.T + p
        tris.append(vw[f])                       # (m,3,3)
        cols.append(c[f].mean(axis=1))           # (m,3)
    return np.concatenate(tris, 0), np.concatenate(cols, 0)


def render(tris, cols, eye, foc):
    eye = np.asarray(eye, float); foc = np.asarray(foc, float)
    fwd = foc - eye; fwd = fwd / np.linalg.norm(fwd)
    right = np.cross(fwd, [0, 0, 1.0]); right = right / np.linalg.norm(right)
    upv = np.cross(right, fwd)
    rel = tris - eye                              # (m,3,3)
    x = rel @ right; y = rel @ upv; z = rel @ fwd
    keep = (z > 0.05).all(axis=1)
    tris_k = tris[keep]; cols_k = cols[keep]
    x, y, z = x[keep], y[keep], z[keep]
    sx = W / 2 + FOCAL * x / z
    sy = H / 2 - FOCAL * y / z
    # lambert shading from the fixed light + slight depth dimming
    n = np.cross(tris_k[:, 1] - tris_k[:, 0], tris_k[:, 2] - tris_k[:, 0])
    nn = np.linalg.norm(n, axis=1); nn[nn == 0] = 1
    lam = np.abs((n / nn[:, None]) @ LIGHT)
    shade = 0.50 + 0.34 * lam   # capped: match the committed GIFs' light-gray floor
    rgb = np.clip(cols_k * shade[:, None] * 255, 0, 255).astype(np.uint8)
    order = np.argsort(-z.mean(axis=1))           # painter: far -> near
    im = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(im)
    for i in order:
        dr.polygon([(sx[i, 0], sy[i, 0]), (sx[i, 1], sy[i, 1]), (sx[i, 2], sy[i, 2])],
                   fill=tuple(rgb[i]))
    return np.asarray(im)
