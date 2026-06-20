"""Solver section — part-name callout map (demo_ui style).

Renders the Solver stepper faithfully + leader-line callouts to the bold part
name and its `.class` / `#id` / `solverStepN ← stageN` code binding, then
rasterises to ../solver_map.png via cairosvg. Re-run after UI changes:

    python maps/solver_map.py        # from intelligence_demo/arc1/spike/
"""
import os
import cairosvg

_OUT = os.path.dirname(os.path.abspath(__file__)) + "/.."

# palette = arc_debug.html :root vars
BG = "#11131a"; PANEL = "#1a1d27"; PANEL2 = "#222634"; LINE = "#2e3344"
INK = "#e7e9f0"; DIM = "#9aa3b8"; ACCENT = "#7aa2ff"; OK = "#3ddc84"
WARN = "#ffb454"; TOUCH = "#A78BFA"; SHIP = "#FF4136"; BLK = "#0074D9"; AZ = "#2ECC40"
W, H = 1180, 864
DX, DW = 410, 360
DR = DX + DW


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


S = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
     f'font-family="Segoe UI,Helvetica,Arial,sans-serif">']
S.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{BG}"/>')


def R(x, y, w, h, rx, fill, stroke=None, sw=1):
    s = f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="{rx}" fill="{fill}"'
    if stroke:
        s += f' stroke="{stroke}" stroke-width="{sw}"'
    return s + '/>'


def T(x, y, txt, fill, size, weight=400, anchor="start", mono=False, ls=None):
    fam = ' font-family="ui-monospace,Menlo,monospace"' if mono else ''
    wt = f' font-weight="{weight}"' if weight != 400 else ''
    l = f' letter-spacing="{ls}"' if ls else ''
    return (f'<text x="{x:.0f}" y="{y:.0f}" fill="{fill}" font-size="{size}"{wt}{fam}{l} '
            f'text-anchor="{anchor}">{esc(txt)}</text>')


def chip(x, y, w, txt, fg, bd, bgc, dim=False):
    op = ' opacity="0.55"' if dim else ''
    return (f'<g{op}>' + R(x, y, w, 20, 6, bgc, bd)
            + T(x + w / 2, y + 14, txt, fg, 10.5, anchor="middle") + '</g>')


def lead(x1, y1, x2, y2, c="#5c6773"):
    return (f'<polyline points="{x1:.0f},{y1:.0f} {x2:.0f},{y2:.0f}" fill="none" '
            f'stroke="{c}" stroke-width="1.1"/>'
            f'<circle cx="{x2:.0f}" cy="{y2:.0f}" r="2.6" fill="{c}"/>')


def lab(x, y, name, cls, anchor="start", col=INK):
    out = T(x, y, name, col, 12, 600, anchor)
    if cls:
        out += T(x, y + 13, cls, DIM, 10, anchor=anchor, mono=True)
    return out


# ── title ────────────────────────────────────────────────────────────
S.append(T(W / 2, 32, "Solver — part names (use the name or the .class / solverStepN ← stageN)",
           INK, 20, 700, "middle"))
S.append(T(W / 2, 55, "read-only run (option A) · same .sstep structure on every step · task #8 05f2a901",
           DIM, 12.5, anchor="middle"))

# ── header strip (.shdr) ───────────────────────────────────────────────
hy = 92
S.append(R(DX, hy, DW, 42, 8, PANEL2, LINE))
S.append(T(DX + 14, hy + 26, "Solver", INK, 14, 500))
S.append(T(DX + 70, hy + 26, "#8 · 05f2a901", ACCENT, 11.5, mono=True))
S.append(chip(DR - 96, hy + 11, 84, "SOLVED ✓", OK, OK, "#16302b"))

# ── step 1 card (full) ─────────────────────────────────────────────────
y1 = 150
S.append(R(DX, y1, DW, 198, 10, PANEL, LINE))
S.append(f'<circle cx="{DX+26}" cy="{y1+24}" r="11" fill="{OK}"/>')
S.append(T(DX + 26, y1 + 28, "1", "#06251a", 12, 600, "middle"))
S.append(T(DX + 46, y1 + 29, "States, transitions & changes", INK, 13, 500))
S.append(chip(DR - 58, y1 + 14, 46, "done", OK, OK, PANEL2))
S.append(f'<line x1="{DX}" y1="{y1+40}" x2="{DR}" y2="{y1+40}" stroke="{LINE}"/>')
# objects
S.append(T(DX + 16, y1 + 60, "OBJECTS (DEMO 1)", DIM, 10, ls="0.5"))
cy = y1 + 68
S.append(chip(DX + 16, cy, 116, "O0 · background", DIM, LINE, PANEL2))
S.append(chip(DX + 138, cy, 78, "O1 · ship", OK, "#2ECC40", "#1d2b1f"))
S.append(chip(DX + 222, cy, 86, "O2 · block", "#7fb3f0", "#378ADD", "#11253a"))
# touching + toggle
S.append(T(DX + 16, y1 + 110, "TOUCHING · INPUT → OUTPUT", DIM, 10, ls="0.5"))
S.append(chip(DR - 96, y1 + 100, 84, "background off", DIM, LINE, PANEL2))
S.append(T(DX + 16, y1 + 130, "{ } → {", DIM, 11, mono=True))
S.append(R(DX + 64, y1 + 119, 64, 16, 5, "#1e1b2e", TOUCH))
S.append(T(DX + 96, y1 + 131, "+ O1·O2", TOUCH, 10, anchor="middle", mono=True))
S.append(T(DX + 132, y1 + 130, "}", DIM, 11, mono=True))
# result box
ry = y1 + 146
S.append(R(DX + 12, ry, DW - 24, 42, 7, PANEL2))
S.append(T(DX + 24, ry + 17, "RESULT", DIM, 10, ls="0.5"))
S.append(T(DX + 24, ry + 33, "touching gained (O1·O2)", TOUCH, 11.5, mono=True))
S.append(T(DX + 210, ry + 33, "✓ 3/3 demos", OK, 11.5))

# ── step 3 card (resolved) ─────────────────────────────────────────────
y3 = 366
S.append(R(DX, y3, DW, 96, 10, PANEL, LINE))
S.append(f'<circle cx="{DX+26}" cy="{y3+24}" r="11" fill="{OK}"/>')
S.append(T(DX + 26, y3 + 28, "3", "#06251a", 12, 600, "middle"))
S.append(T(DX + 46, y3 + 29, "Selector synthesis", INK, 13, 500))
S.append(chip(DR - 110, y3 + 14, 98, "resolved · shape", OK, OK, PANEL2))
S.append(f'<line x1="{DX}" y1="{y3+40}" x2="{DR}" y2="{y3+40}" stroke="{LINE}"/>')
S.append(T(DX + 16, y3 + 58, "MOVER SELECTORS (LOCKED ✓)", DIM, 10, ls="0.5"))
S.append(chip(DX + 16, y3 + 66, 70, "colour = 2", DIM, LINE, PANEL2, dim=True))
S.append(chip(DX + 92, y3 + 66, 64, "largest", DIM, LINE, PANEL2, dim=True))
S.append(chip(DX + 162, y3 + 66, 110, "irregular ✓", OK, "#2ECC40", "#1d2b1f"))

# ── step 6 card (grids) ────────────────────────────────────────────────
y6 = 480
S.append(R(DX, y6, DW, 178, 10, PANEL, LINE))
S.append(f'<circle cx="{DX+26}" cy="{y6+24}" r="11" fill="{OK}"/>')
S.append(T(DX + 26, y6 + 28, "6", "#06251a", 12, 600, "middle"))
S.append(T(DX + 46, y6 + 29, "Apply to test", INK, 13, 500))
S.append(chip(DR - 58, y6 + 14, 46, "done", OK, OK, PANEL2))
S.append(f'<line x1="{DX}" y1="{y6+40}" x2="{DR}" y2="{y6+40}" stroke="{LINE}"/>')


def minigrid(ox, oy, cells, cs=12):
    out = [R(ox - 2, oy - 2, len(cells[0]) * cs + 4, len(cells) * cs + 4, 3, "#0c0e14")]
    for r, row in enumerate(cells):
        for c, v in enumerate(row):
            col = {0: "#000000", 2: SHIP, 8: BLK}.get(v, "#000000")
            out.append(f'<rect x="{ox+c*cs}" y="{oy+r*cs}" width="{cs-1}" height="{cs-1}" fill="{col}"/>')
    return "".join(out)


# schematic test grids (ship slides to the block)
gin = [[0, 0, 0, 0, 0], [0, 0, 2, 0, 0], [0, 0, 2, 2, 0], [8, 8, 0, 2, 0], [8, 8, 0, 0, 0]]
gout = [[0, 0, 2, 0, 0], [0, 0, 2, 2, 0], [8, 8, 0, 2, 0], [8, 8, 0, 0, 0], [0, 0, 0, 0, 0]]
S.append(T(DX + 16, y6 + 58, "TEST INPUT", DIM, 10, ls="0.5"))
S.append(minigrid(DX + 16, y6 + 66, gin))
S.append(T(DX + 150, y6 + 58, "PRODUCED OUTPUT · 2 STEPS", DIM, 10, ls="0.5"))
S.append(minigrid(DX + 150, y6 + 66, gout))
S.append(chip(DX + 16, y6 + 144, 120, "withheld ✓ match", OK, OK, "#16302b"))

# ── callouts ───────────────────────────────────────────────────────────
# LEFT (anchor end)
LX = 392
S.append(lab(LX, 108, "section + entry", "#secSolver · renderSolver()", "end"));            S.append(lead(LX + 4, 104, DX, hy + 8))
S.append(lab(LX, 170, "step badge", ".sbadge.done", "end", OK));                                S.append(lead(LX + 4, 166, DX + 15, y1 + 24))
S.append(lab(LX, 214, "step title", ".sttl", "end"));                                           S.append(lead(LX + 4, 210, DX + 46, y1 + 29))
S.append(lab(LX, 256, "block label", ".sl", "end"));                                            S.append(lead(LX + 4, 252, DX + 16, y1 + 60))
S.append(lab(LX, 300, "object chip", ".schip", "end"));                                         S.append(lead(LX + 4, 296, DX + 18, y1 + 78))
S.append(lab(LX, 360, "card body", ".sbody", "end"));                                           S.append(lead(LX + 4, 356, DX + 12, ry + 21))
S.append(lab(LX, 430, "selector chips (locked)", ".schip ✓ ← stage3.selected", "end", OK)); S.append(lead(LX + 4, 426, DX + 16, y3 + 76))
S.append(lab(LX, 560, "produced grids", "solverGridHTML() ← stage6", "end"));               S.append(lead(LX + 4, 556, DX + 16, y6 + 78))

# RIGHT (anchor start)
RX = 800
S.append(lab(RX, 104, "SOLVED banner", "stage6.matches_withheld", "start", OK));                S.append(lead(RX - 4, 100, DR - 54, hy + 21))
S.append(lab(RX, 150, "step card", ".sstep", "start"));                                         S.append(lead(RX - 4, 146, DR, y1 + 12))
S.append(lab(RX, 192, "step header", ".sshead", "start"));                                      S.append(lead(RX - 4, 188, DR, y1 + 20))
S.append(lab(RX, 234, "status chip", '.sstat ("done")', "start"));                              S.append(lead(RX - 4, 230, DR - 12, y1 + 24))
S.append(lab(RX, 300, "background toggle", "#sbgtg · solverBg", "start", TOUCH));           S.append(lead(RX - 4, 296, DR - 12, y1 + 108))
S.append(lab(RX, 344, "result box", ".sres", "start"));                                         S.append(lead(RX - 4, 340, DR - 12, ry + 21))
S.append(lab(RX, 410, "resolved status", '.sstat "resolved · shape"', "start", OK));        S.append(lead(RX - 4, 406, DR - 12, y3 + 24))
S.append(lab(RX, 540, "withheld confidence", "stage6 (not used by solver)", "start"));          S.append(lead(RX - 4, 536, DX + 136, y6 + 154))

# ── footer ─────────────────────────────────────────────────────────────
S.append(T(W / 2, H - 26,
           "Every step = solverStepN ← DATA.solver.stageN · unresolved flags use .sflag / .sbadge.flag "
           "· full element→code reference: SOLVER_UI_MAP.md", DIM, 11.5, anchor="middle"))

S.append("</svg>")
cairosvg.svg2png(bytestring="".join(S).encode(),
                 write_to=os.path.join(_OUT, "solver_map.png"),
                 output_width=W, output_height=H, background_color=BG)
print("rendered solver_map.png")
