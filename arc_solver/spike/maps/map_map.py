"""Map section — part-name callout map → ../map_map.png."""
from _kit import (R, T, chip, lead, lab, divider, header, footer, render,
                  PANEL, PANEL2, LINE, INK, DIM, ACCENT, OK)

W, H = 1180, 600
DX, DW = 330, 520
DR = DX + DW
S = []
header(S, W, "Map — part names (use the name or the .class)",
       "selector buttons switch the section callout map · #mapnav + .mappanel + #arcmeta")

# button bar
by = 100
btns = ["Main", "Search", "Solver", "Capacities", "Map"]
bx = DX
for i, b in enumerate(btns):
    w = 26 + len(b) * 8
    on = (b == "Solver")
    S.append(R(bx, by, w, 26, 6, "#1a2233" if on else PANEL2, ACCENT if on else LINE))
    S.append(T(bx + w / 2, by + 17, b, ACCENT if on else INK, 11, anchor="middle"))
    bx += w + 8

# selected map frame (.mappanel → .mapimg)
my = 148
S.append(R(DX, my, DW, 150, 10, "#0c0e14", LINE))
S.append(T(DX + DW / 2, my + 70, "callout map — selected section", DIM, 13, anchor="middle"))
S.append(T(DX + DW / 2, my + 92, "(main / search / solver / capacities / map)_map.png", DIM, 10.5, anchor="middle", mono=True))

# arc metagraph overlay
ay = 318
S.append(T(DX, ay, "ARC METAGRAPH (L3 OVERLAY)", DIM, 11, 600, ls="0.5"))
sect = [("atoms", ["same_object", "same_shape", "same_point"]),
        ("object_comparator", ["moved"]),
        ("profile", ["compare_*"])]
gx = DX
for name, members in sect:
    gw = 150
    S.append(R(gx, ay + 12, gw, 92, 8, PANEL2, LINE))
    S.append(T(gx + 10, ay + 30, name, ACCENT, 11, 600))
    for j, m in enumerate(members):
        S.append(T(gx + 10, ay + 48 + j * 16, m, INK, 10.5, mono=True))
    gx += gw + 12
S.append(T(DX, ay + 124, "moved", ACCENT, 11, mono=True))
S.append(T(DX + 44, ay + 124, "—requires→", DIM, 11))
S.append(T(DX + 120, ay + 124, "same_shape", ACCENT, 11, mono=True))
S.append(T(DX + 200, ay + 124, "(intergraph edge)", DIM, 11))

# ── callouts ──
LX, RX = 312, DR + 18
S.append(lab(LX, 116, "selector bar", "#mapnav button[data-map]", "end", ACCENT)); S.append(lead(LX + 4, 112, DX, by + 13))
S.append(lab(LX, 200, "section panel", ".mappanel[data-map]", "end")); S.append(lead(LX + 4, 196, DX, my + 10))
S.append(lab(LX, 270, "callout image", ".mapimg (maps/*.py)", "end")); S.append(lead(LX + 4, 266, DX + 60, my + 110))
S.append(lab(LX, 360, "metagraph overlay", "#arcmeta ← renderArcMeta()", "end")); S.append(lead(LX + 4, 356, DX, ay + 12))

S.append(lab(RX, 150, "switch handler", "setMap(which)", "start")); S.append(lead(RX - 4, 146, bx - 8, by + 13))
S.append(lab(RX, 360, "section graph", ".amg · .amn", "start")); S.append(lead(RX - 4, 356, DR, ay + 58))
S.append(lab(RX, 430, "requires edge", ".amreq", "start")); S.append(lead(RX - 4, 426, DX + 160, ay + 124))

footer(S, W, H, "The Map section: #mapnav buttons toggle .mappanel panels (setMap); each panel embeds a "
                "maps/*.py callout image. The Map panel also renders the Arc metagraph (#arcmeta).")
render(S, "map_map.png", W, H)
