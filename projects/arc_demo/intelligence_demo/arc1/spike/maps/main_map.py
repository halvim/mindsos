"""Main section — part-name callout map (demo_ui style) → ../main_map.png.

Layout: profile card on top · demonstration cards side by side (.demorow) ·
test + hypotheses cards side by side beneath (.botrow).
"""
from _kit import (R, T, chip, lead, lab, divider, header, footer, render,
                  PANEL, PANEL2, LINE, INK, DIM, ACCENT, OK, TOUCH,
                  RED, BLUE)

W, H = 1180, 656
DX = 350
CW, GAP = 150, 12
ROWW = CW * 3 + GAP * 2          # 474
DR = DX + ROWW
S = []
header(S, W, "Main — part names (use the name or the .class)",
       "profile on top · demonstrations side by side (.demorow) · test + hypotheses beneath (.botrow)")


def minigrid(ox, oy, cells, cs=9):
    out = [R(ox - 2, oy - 2, len(cells[0]) * cs + 4, len(cells) * cs + 4, 3, "#0c0e14")]
    for r, row in enumerate(cells):
        for c, v in enumerate(row):
            col = {0: "#000000", 2: RED, 8: BLUE}.get(v, "#000000")
            out.append(f'<rect x="{ox+c*cs}" y="{oy+r*cs}" width="{cs-1}" height="{cs-1}" fill="{col}"/>')
    return "".join(out)


# toolbar
ty = 86
S.append(R(DX, ty, 150, 24, 6, PANEL2, LINE)); S.append(T(DX + 10, ty + 16, "#8  05f2a901  ▾", INK, 10.5))
S.append(chip(DX + 158, ty + 1, 78, "Objects", ACCENT, ACCENT, "#1a2233", h=22))
S.append(chip(DX + 242, ty + 1, 62, "Shapes", ACCENT, ACCENT, "#1a2233", h=22))

# profile card
py = 122
S.append(R(DX, py, ROWW, 54, 9, PANEL, LINE))
S.append(T(DX + 12, py + 20, "TASKPROFILE — 05F2A901", DIM, 10.5, 600, ls="0.5"))
for i, (k, v) in enumerate([("demos / tests", "3 / 1"), ("dims preserved", "yes"), ("palette Δ", "no change")]):
    bx = DX + 12 + i * 150
    S.append(R(bx, py + 28, 140, 18, 6, PANEL2, LINE))
    S.append(T(bx + 8, py + 41, k + " · " + v, DIM, 10, mono=True))


def demo_card(x, y, n, inG, outG, dirn):
    S.append(R(x, y, CW, 232, 9, PANEL, LINE))
    S.append(T(x + 10, y + 18, "demonstration " + str(n), DIM, 10.5, 600))
    S.append(T(x + 10, y + 34, "IN", DIM, 8.5, ls="0.5")); S.append(minigrid(x + 10, y + 38, inG))
    S.append(T(x + 10, y + 86, "OUT", DIM, 8.5, ls="0.5")); S.append(minigrid(x + 10, y + 90, outG))
    S.append(T(x + 10, y + 146, "INTER-GRID", ACCENT, 8.5, 600, ls="0.7"))
    S.append(divider(x + 10, y + 150, x + CW - 10))
    S.append(T(x + 10, y + 165, "≡ same_object", OK, 10))
    S.append(T(x + 10, y + 180, "≅ same_shape · moved " + dirn, "#5aa2ff", 10))
    S.append(T(x + 10, y + 196, "INTRA-GRID", ACCENT, 8.5, 600, ls="0.7"))
    S.append(divider(x + 10, y + 200, x + CW - 10))
    S.append(T(x + 10, y + 215, "▸ touching candidates · 2", DIM, 10))


dy = 200
g1i = [[0, 2, 2, 0, 0], [2, 0, 2, 0, 0], [0, 0, 0, 0, 0], [0, 8, 8, 0, 0]]
g1o = [[0, 0, 0, 0, 0], [0, 2, 2, 0, 0], [2, 0, 2, 0, 0], [0, 8, 8, 0, 0]]
g2i = [[2, 2, 0, 0, 0], [0, 2, 0, 8, 8], [2, 2, 0, 8, 8], [0, 0, 0, 0, 0]]
g2o = [[0, 0, 2, 2, 0], [0, 0, 0, 2, 8], [0, 0, 2, 2, 8], [0, 0, 0, 0, 0]]
g3i = [[0, 8, 8, 0, 0], [0, 8, 8, 0, 0], [0, 0, 0, 0, 0], [2, 2, 2, 0, 0]]
g3o = [[0, 8, 8, 0, 0], [0, 8, 8, 0, 0], [2, 2, 2, 0, 0], [0, 0, 0, 0, 0]]
demo_card(DX, dy, 1, g1i, g1o, "↓")
demo_card(DX + CW + GAP, dy, 2, g2i, g2o, "→")
demo_card(DX + 2 * (CW + GAP), dy, 3, g3i, g3o, "↑")

# bottom row: test + hypotheses
by = 452
S.append(R(DX, by, 230, 150, 9, PANEL, LINE))
S.append(T(DX + 10, by + 18, "test 1", DIM, 10.5, 600))
S.append(T(DX + 10, by + 36, "INPUT (TIN1)", DIM, 8.5, ls="0.5"))
S.append(minigrid(DX + 10, by + 40, [[0, 0, 0, 2, 0], [0, 0, 0, 2, 2], [8, 8, 0, 2, 0], [8, 8, 0, 0, 0]]))
S.append(T(DX + 110, by + 36, "OUTPUT", DIM, 8.5, ls="0.5"))
S.append(R(DX + 110, by + 40, 108, 50, 5, "none", LINE))
S.append(T(DX + 164, by + 60, "withheld", "#ffb454", 10, anchor="middle"))
S.append(T(DX + 164, by + 74, "(answer gated)", DIM, 9, anchor="middle"))

hx = DX + 244
S.append(R(hx, by, 230, 150, 9, PANEL, LINE))
S.append(T(hx + 10, by + 18, "HYPOTHESES — PERSIST ACROSS DEMOS", DIM, 9.5, 600, ls="0.4"))
for j, nm in enumerate(["same_object", "same_shape", "moved", "touching"]):
    ry = by + 30 + j * 28
    S.append(R(hx + 10, ry, 210, 22, 6, "#16302b", OK))
    S.append(T(hx + 20, ry + 15, nm, TOUCH if nm == "touching" else ACCENT, 10.5, mono=True))
    S.append(T(hx + 168, ry + 15, "3/3", DIM, 10))
    S.append(T(hx + 202, ry + 15, "✓", OK, 11, anchor="end"))

# ── callouts ──
LX, RX = 332, DR + 18
S.append(lab(LX, 100, "toolbar", "#picker · #tObjs · #tShapes", "end")); S.append(lead(LX + 4, 96, DX, ty + 12))
S.append(lab(LX, 150, "profile card", ".profile · .verdicts/.v", "end")); S.append(lead(LX + 4, 146, DX, py + 20))
S.append(lab(LX, 205, "demonstrations row", ".demorow (side by side)", "end", ACCENT)); S.append(lead(LX + 4, 201, DX, dy))
S.append(lab(LX, 270, "demonstration card", ".pair · .pair-h", "end")); S.append(lead(LX + 4, 266, DX, dy + 20))
S.append(lab(LX, 345, "inter-grid division", ".division (renderPairCard)", "end", ACCENT)); S.append(lead(LX + 4, 341, DX + 10, dy + 146))
S.append(lab(LX, 420, "invariant tier", ".tlabel.eq · .objbox.eq", "end", OK)); S.append(lead(LX + 4, 416, DX + 10, dy + 165))
S.append(lab(LX, 500, "test + hypotheses row", ".botrow (side by side)", "end", ACCENT)); S.append(lead(LX + 4, 496, DX, by))

S.append(lab(RX, 150, "section", "#secMain ← DATA.tasks[]", "start")); S.append(lead(RX - 4, 146, DR, py + 20))
S.append(lab(RX, 230, "render entry", "renderMain() → renderPairCard()", "start")); S.append(lead(RX - 4, 226, DR, dy + 12))
S.append(lab(RX, 300, "intra-grid touching", ".touchacc (touchingAccordion)", "start", TOUCH)); S.append(lead(RX - 4, 296, DR, dy + 215))
S.append(lab(LX, 548, "test card", ".pair · gridOnly(withheld)", "end")); S.append(lead(LX + 4, 544, DX, by + 70))
S.append(lab(RX, 512, "hypotheses card", ".hyplist · .hyprow", "start", OK)); S.append(lead(RX - 4, 508, hx + 220, by + 70))

footer(S, W, H, "renderMain(): profile card · .demorow of renderPairCard() demos · .botrow of test card(s) + the "
                "hypotheses card. Per-pair card = inter-grid tiers (renderMatch) + intra-grid touchingAccordion.")
render(S, "main_map.png", W, H)
