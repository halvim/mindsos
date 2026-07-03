"""Search section — part-name callout map (demo_ui style) → ../search_map.png."""
from _kit import (R, T, chip, lead, lab, divider, header, footer, render,
                  PANEL, PANEL2, LINE, INK, DIM, ACCENT, OK, TOUCH)

W, H = 1180, 660
S = []
header(S, W, "Search — part names (use the name or the .class)",
       "facets in two divisions (inter-grid / intra-grid) · AND across caps · OR within a cap")

# facets pane
FX, FW = 372, 250
fy = 92
S.append(R(FX, fy, FW, 470, 10, PANEL, LINE))


def frow(y, name, count, on=False, sub=False):
    x = FX + (28 if sub else 14)
    ck = "#7aa2ff" if on else "none"
    S.append(R(x, y, 13, 13, 3, ck, LINE))
    S.append(T(x + 22, y + 11, name, INK if on else DIM, 11.5, mono=True))
    S.append(T(FX + FW - 14, y + 11, str(count), DIM, 10.5, anchor="end"))


def dhead(y, txt):
    S.append(T(FX + 14, y, txt, ACCENT, 10, 600, ls="0.8"))
    S.append(divider(FX + 14, y + 5, FX + FW - 14))


def ghead(y, txt):
    S.append(T(FX + 14, y, txt, DIM, 10, 600, ls="0.5"))


dhead(fy + 24, "INTER-GRID")
ghead(fy + 46, "PROFILE (MULTI-RESULT)")
S.append(T(FX + 22, fy + 64, "▸ compare_grid_dimension", DIM, 11, mono=True))
S.append(T(FX + 22, fy + 82, "▸ compare_palette", DIM, 11, mono=True))
ghead(fy + 104, "ATOMS")
frow(fy + 114, "same_object", 312)
frow(fy + 134, "same_shape", 198)
frow(fy + 154, "same_point", 76)
ghead(fy + 184, "OBJECT COMPARATOR")
frow(fy + 194, "moved", 87)
dhead(fy + 230, "INTRA-GRID")
frow(fy + 252, "touching", 143, on=True)
S.append(T(FX + 14, fy + 290, "AND across caps · OR within", ACCENT, 10.5, mono=True))

# matches pane
MX, MW = FX + FW + 30, 360
my = 92
S.append(T(MX, my + 8, "143", INK, 12, 600)); S.append(T(MX + 30, my + 8, "matching", DIM, 12))
S.append(T(MX, my + 30, "show counts:", DIM, 10.5))
for i, t in enumerate(["≡ obj", "≅ shape", "≡ pt"]):
    S.append(chip(MX + 78 + i * 56, my + 20, 50, t, DIM, LINE, PANEL2, h=16))
# a match row
ry = my + 54
S.append(R(MX, ry, MW, 96, 6, PANEL2, LINE))
S.append(T(MX + 12, ry + 20, "#3  a68b268e", ACCENT, 11.5, mono=True))
S.append(T(MX + MW - 14, ry + 20, "Main ↗", ACCENT, 10.5, anchor="end"))
S.append(divider(MX, ry + 30, MX + MW))
S.append(T(MX + 12, ry + 48, "touching · In1: 2 · Out1: 0 · In2: 1", DIM, 10.5, mono=True))
S.append(R(MX + 12, ry + 58, 160, 22, 6, "#1e1b2e", "#3a3358"))
S.append(T(MX + 22, ry + 73, "In1.O0 ⟷ In1.O1", ACCENT, 10, mono=True))

# ── callouts ──
LX, RX = 354, MX + MW + 18
S.append(lab(LX, 132, "division header", ".division (inter / intra)", "end", ACCENT)); S.append(lead(LX + 4, 128, FX + 14, fy + 24))
S.append(lab(LX, 188, "group sub-header", ".facet-ph", "end")); S.append(lead(LX + 4, 184, FX + 14, fy + 46))
S.append(lab(LX, 250, "boolean facet row", ".frow · .ck · .fct", "end")); S.append(lead(LX + 4, 246, FX + 14, fy + 128))
S.append(lab(LX, 320, "multi-result facet", ".caprow ▸ .subwrap", "end")); S.append(lead(LX + 4, 316, FX + 22, fy + 64))
S.append(lab(LX, 400, "touching facet (intra)", ".frow ← FACETS division", "end", TOUCH)); S.append(lead(LX + 4, 396, FX + 14, fy + 252))
S.append(lab(LX, 470, "facets pane", "#facets ← buildFacets()", "end")); S.append(lead(LX + 4, 466, FX, fy + 420))

S.append(lab(RX, 110, "matches pane", "#matches ← renderMatches()", "start")); S.append(lead(RX - 4, 106, MX + MW, my + 4))
S.append(lab(RX, 170, "count toggles", ".cnttoggles · .cnttg", "start")); S.append(lead(RX - 4, 166, MX + MW - 30, my + 28))
S.append(lab(RX, 240, "match row", ".mrow · .mrow-h · .openlink", "start")); S.append(lead(RX - 4, 236, MX + MW, ry + 20))
S.append(lab(RX, 320, "inline expand (S2)", ".mexp · buildExp()", "start")); S.append(lead(RX - 4, 316, MX + MW, ry + 48))
S.append(lab(RX, 390, "touching pair row", ".trow · .tbond", "start", TOUCH)); S.append(lead(RX - 4, 386, MX + 172, ry + 70))

footer(S, W, H, "Facets in two divisions (inter-grid / intra-grid); AND across capacities, OR within a capacity's results. "
                "buildFacets() ← DATA.search.facets · matchedIds() ← availability.")
render(S, "search_map.png", W, H)
