"""Render arm-aware side-view GIFs for the cubby animations. argv: start count."""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_solid as RS
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); WEB = os.path.join(HERE, "..", "web")
OUT = os.path.join(WEB, "gifs")      # permanent, repo-relative (reference renders;
os.makedirs(OUT, exist_ok=True)      # was a session-scratch path that went stale per chat)

NAMES = [(1, "a1_box")] + [(1, "a1_r%dc%d" % (r, c)) for r in range(3) for c in range(3) if not (r == 0 and c == 1)]
NAMES += [(2, "a2_r%dc%d" % (r, c)) for r in range(3) for c in range(3)]
NAMES += [(1, "a1_sheet_r%dc%d" % (r, c)) for r in range(3) for c in range(3)]   # render idx 18-26
NAMES += [(1, "a1_sheet_pick_r%dc%d" % (r, c)) for r in range(3) for c in range(3)]   # idx 27-35
NAMES += [(2, "a2_tube_pick_r%dc%d" % (r, c)) for r in range(3) for c in range(3)]    # idx 36-44
NAMES += [(0, "a1_load_convey"), (0, "a2_load_convey")]                               # idx 45-46 (wide)


GEO_FULL = None


def render(name, arm):
    global GEO_FULL
    if GEO_FULL is None:
        GEO_FULL = RS.load_geo()
    anim = json.load(open(os.path.join(WEB, f"anim_{name}.json")))
    if arm == 0:    # wide both-arms view (cross-cell conveyor anims), from the belt side
        keep = lambda b: True
        foc = np.array([0.0, -0.2, 1.0]); eye = foc + np.array([0.0, 3.4, 0.9])
    elif arm == 1:
        keep = lambda b: b.startswith("a1_") or b in ("world", "shelf_L", "box1", "sheet1")
        foc = np.array([-1.20, -0.25, 1.02]); eye = foc + np.array([-3.0, 0.0, 0.55])
    else:
        keep = lambda b: b.startswith("a2_") or b.startswith("a2g_") or b in ("world", "shelf_R", "box2", "tube1")
        foc = np.array([1.20, -0.25, 1.02]); eye = foc + np.array([3.0, 0.0, 0.55])
    geo = {k: v for k, v in GEO_FULL.items() if keep(k)}
    RS.W, RS.H = 600, 430
    N = len(anim["frames"]); frames = []
    for fi in range(0, N, 4):
        tris, cols = RS.world_tris(anim, geo, fi)
        frames.append(Image.fromarray(RS.render(tris, cols, eye, foc)))
    frames[0].save(os.path.join(OUT, f"{name}.gif"), save_all=True,
                   append_images=frames[1:], duration=90, loop=0)
    print("wrote", name, len(frames))


if __name__ == "__main__":
    start = int(sys.argv[1]); count = int(sys.argv[2])
    for arm, nm in NAMES[start:start + count]:
        render(nm, arm)
