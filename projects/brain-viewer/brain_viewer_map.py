"""Part-name callout map for the `view`-verb brain-graph viewer
(mindsos_cli/commands/brain_viz_template.html) -> brain_viewer_map.png.

Same demo_ui style as arc1-brain/viz/maps/*.py: a mockup of the real UI with
every part labelled by its #id / .class and its JS/DATA binding, so changes to
the HTML can be requested by name.
"""
from _kit import (R, T, chip, sw, lead, lab, header, footer, render,
                  PANEL, PANEL2, LINE, INK, DIM, ACCENT, OK, WARN)

W, H = 1600, 980
S_body = []
P = {}  # element -> (leftedge_x, mid_y) anchor for leads

# ── side panel geometry ──
SX, SW, SY = 440, 300, 92
cx, cw = SX + 16, SW - 32
y = SY + 18


def grp(text):
    global y
    S_body.append(T(cx, y + 9, text.upper(), DIM, 10.5, 600, ls="0.6"))
    y += 22


# 1 title
S_body.append(T(cx, y + 13, "arc1_brain graph", INK, 15, 700))
P["title"] = (SX, y + 8); y += 24
# 2 subtitle
S_body.append(T(cx, y + 10, "Every DataState (boxes) and capacity", DIM, 11))
S_body.append(T(cx, y + 23, "(ellipses); edges consume→ / produce→.", DIM, 11))
P["sub"] = (SX, y + 16); y += 40
# 3 segment section
grp("Conjunction Finder — segment")
S_body.append(R(cx, y, cw, 32, 7, PANEL2, LINE))
S_body.append(T(cx + 10, y + 21, "— show everything —", INK, 12, mono=True))
P["seg"] = (SX, y + 16); y += 40
# 4 isolate checkbox
S_body.append(R(cx, y + 1, 15, 15, 3, PANEL2, LINE))
S_body.append(T(cx + 24, y + 13, "isolate (hide the rest)", INK, 12))
P["iso"] = (SX, y + 8); y += 26
# 5 segsteps
S_body.append(T(cx, y + 10, "finder-composed order:", DIM, 10.5))
S_body.append(T(cx, y + 23, "1. build_grid   2. extract_objects", DIM, 10.5, mono=True))
P["segsteps"] = (SX, y + 15); y += 38
# 6 search
grp("Search")
S_body.append(R(cx, y, cw, 32, 7, PANEL2, LINE))
S_body.append(T(cx + 10, y + 21, "type a node name…", DIM, 12))
P["q"] = (SX, y + 16); y += 40
# 7 pipelines
grp("Pipelines — hover to highlight")
for i, (lbl, n) in enumerate([("1 · raw_task → raw_grids*", "5 steps"),
                              ("2 · raw_grid → objects*", "3 steps")]):
    S_body.append(R(cx, y, cw, 34, 7, PANEL2, LINE))
    S_body.append(T(cx + 10, y + 15, lbl, INK, 11, 600))
    S_body.append(T(cx + 10, y + 28, n, DIM, 10))
    if i == 0:
        P["pllist"] = (SX, y + 17)
    y += 40
# 8 capacity families legend
grp("Capacity families")
for color, name in [("#ff8f6b", "Perceiver"), ("#2dd4bf", "Reasoning"),
                    ("#c084fc", "Comparator")]:
    S_body.append(sw(cx, y, color))
    S_body.append(T(cx + 20, y + 11, name, INK, 12))
    if "capleg" not in P:
        P["capleg"] = (SX, y + 6)
    y += 21
y += 4
# 9 datastate groups legend
grp("DataState groups")
for color, name in [("#4C78A8", "Comprehension"), ("#72B7B2", "Perception"),
                    ("#B279A2", "Reasoning")]:
    S_body.append(sw(cx, y, color))
    S_body.append(T(cx + 20, y + 11, name, INK, 12))
    if "dsleg" not in P:
        P["dsleg"] = (SX, y + 6)
    y += 21
y += 4
# 10 selected node / detail
grp("Selected node")
det_h = 92
S_body.append(R(cx, y, cw, det_h, 7, PANEL2, LINE))
S_body.append(T(cx + 10, y + 18, "build_grid · perception capacity", INK, 11.5, 700))
S_body.append(T(cx + 10, y + 38, "consumes", DIM, 10.5, 700))
S_body.append(chip(cx + 10, y + 44, 62, "raw_grid", "#cdd3de", LINE, "#0e1218", h=18))
S_body.append(T(cx + 10, y + 74, "produces", DIM, 10.5, 700))
S_body.append(chip(cx + 10, y + 80, 42, "grid", "#cdd3de", LINE, "#0e1218", h=18))
P["det"] = (SX, y + det_h / 2); y += det_h + 4

PH = y - SY + 14
P["side"] = (SX, SY + 12)

# ── assemble ──
S = []
header(S, W, "Brain viewer — part names (use the #id or the .class)",
       "the `view`-verb graph  ·  mindsos_cli/commands/brain_viz_template.html  "
       "·  _do_view() → build_data() → DATA → template")
# side panel container
S.append(R(SX, SY, SW, PH, 10, PANEL, LINE))
S += S_body

# ── graph canvas mockup ──
NX, NW, NY, NH = 770, 620, SY, PH
S.append(R(NX, NY, NW, NH, 10, "#0d0f14", LINE))
S.append(T(NX + NW / 2, NY + 26, "vis-network canvas", DIM, 11.5, anchor="middle"))


def ell(cxp, cyp, rx, ry, fill):
    return (f'<ellipse cx="{cxp:.0f}" cy="{cyp:.0f}" rx="{rx}" ry="{ry}" '
            f'fill="{fill}" stroke="#0b0d12" stroke-width="2"/>')


def box(x, yb, wb, txt, fill):
    return (R(x, yb, wb, 34, 6, fill, "#0b0d12", 2)
            + T(x + wb / 2, yb + 22, txt, "#0b0d12", 12, 700, anchor="middle", mono=True))


def arrow(x1, y1, x2, y2, dashed=False):
    d = ' stroke-dasharray="5 4"' if dashed else ''
    return (f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" '
            f'stroke="#5a6577" stroke-width="1.6"{d} marker-end="url(#ar)"/>')


S.insert(0, '<defs><marker id="ar" markerWidth="8" markerHeight="8" refX="7" refY="3" '
            'orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#5a6577"/></marker></defs>')

# sample nodes
gx, gy = 900, 250
S.append(box(gx, gy, 92, "grid", "#72B7B2"))                 # ds
bx, by = 1120, 330
S.append(ell(bx, by, 58, 26, "#2dd4bf"))                     # cap
S.append(T(bx, by + 4, "build_grid", "#0b0d12", 11.5, 700, anchor="middle", mono=True))
px, py = 1000, 440
S.append(box(px, py, 92, "palette", "#54A24B"))             # ds
S.append(arrow(gx + 92, gy + 20, bx - 54, by - 14, dashed=True))   # consume
S.append(arrow(bx - 20, by + 24, px + 60, py, dashed=False))       # produce
# collision-fix illustration: two same-short datastates
g1x, g1y = 820, 590
g2x, g2y = 1080, 630
S.append(box(g1x, g1y, 150, "goal", "#BAB0AC"))
S.append(T(g1x + 75, g1y + 46, "ds:path_finding.goal", DIM, 9.5, anchor="middle", mono=True))
S.append(box(g2x, g2y, 150, "goal", "#BAB0AC"))
S.append(T(g2x + 75, g2y + 46, "ds:phase1.goal", DIM, 9.5, anchor="middle", mono=True))

# ── callouts: side panel (left column) ──
LX = SX - 26
def lc(key, name, cls, ty=None):
    ex, ey = P[key]
    ly = ty if ty is not None else ey
    S.append(lab(LX, ly, name, cls, "end"))
    S.append(lead(LX + 6, ly - 4, ex, ey))

lc("side", "left panel", "#side  · width 310", ty=104)
lc("title", "brain title", "#title ← DATA.title", ty=146)
lc("sub", "description", ".sub", ty=188)
lc("seg", "segment picker", "#seg · onchange→draw()")
lc("iso", "isolate toggle", "#iso · label.rc")
lc("segsteps", "composed order", "#segsteps · .hint")
lc("q", "search box", "#q → selectNodes/showDet")
lc("pllist", "pipelines list", "#pllist · hover→render(k)")
lc("capleg", "capacity legend", "#capleg · .leg/.sw ← capNames")
lc("dsleg", "datastate legend", "#dsleg · .leg/.sw ← dsNames")
lc("det", "selected node", "#det · showDet() · .chip")

# ── callouts: graph (right column) ──
RX = NX + NW + 26
def rc(name, cls, tx, ty, ly):
    S.append(lab(RX, ly, name, cls, "start"))
    S.append(lead(RX - 6, ly - 4, tx, ty))

rc("graph canvas", "#net · new vis.Network", NX + NW, NY + 20, NY + 40)
rc("DataState node", "box · group→dsColor", gx + 92, gy + 17, 240)
rc("capacity node", "ellipse · family→capColor", bx + 58, by, 330)
rc("edge", "consume(dashed) / produce(solid)", px + 92, py, 470)
rc("unique node ids", "id = cap:/ds: + full IRI", g2x + 150, g2y + 17, 640)

footer(S, W, H, "build_data(views, spec) → DATA{nodes,edges,segments,capColor,dsColor,capNames,dsNames,title}  "
                "·  per-brain labels/segments from viz_spec.py  ·  legend labels fall back to the raw group key")
render(S, "brain_viewer_map.png", W, H)
