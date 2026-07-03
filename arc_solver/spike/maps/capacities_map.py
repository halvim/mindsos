"""Capacities section — part-name callout map → ../capacities_map.png."""
from _kit import (R, T, chip, lead, lab, divider, header, footer, render,
                  PANEL, PANEL2, LINE, INK, DIM, ACCENT, OK)

W, H = 1180, 612
DX, DW = 300, 588
DR = DX + DW
S = []
header(S, W, "Capacities — part names (use the name or the .class)",
       "capacities in pipeline order · live L3 registration · renderCapacities() ← DATA.capacities")

# profile card
cy = 100
S.append(R(DX, cy, DW, 408, 10, PANEL, LINE))
S.append(T(DX + 16, cy + 26, "CAPACITIES — PIPELINE ORDER (LIVE L3 REGISTRATION)", DIM, 11, 600, ls="0.5"))

ROWS = [
    ("ph", "perceive"),
    ("cap", "1.", "comprehend_task", "comprehension", "raw_task → task, pair, raw_grid"),
    ("cap", "2.", "build_grid", "perception", "raw_grid → grid"),
    ("cap", "4.", "extract_objects", "decomposition", "grid → object"),
    ("ph", "profile-sweep"),
    ("cap", "8.", "compare_palette", "comparator", "palette → palette_delta"),
    ("ph", "induce"),
    ("cap", "10.", "same_object", "comparator", "object → same_object"),
    ("cap", "13.", "moved", "comparator", "object → move_transform"),
    ("ph", "intra-grid"),
    ("cap", "14.", "touching", "predicate", "object → touching"),
]
y = cy + 40
row_y = {}
for r in ROWS:
    if r[0] == "ph":
        S.append(T(DX + 16, y + 14, r[1].upper(), ACCENT, 10, 600, ls="0.8"))
        y += 24
    else:
        _, n, nm, cat, io = r
        S.append(R(DX + 14, y, DW - 28, 30, 7, PANEL2, LINE))
        S.append(T(DX + 26, y + 20, n, DIM, 11, anchor="end"))
        S.append(T(DX + 36, y + 20, nm, INK, 12, 600, mono=True))
        S.append(chip(DX + 188, y + 6, 104, cat, DIM, LINE, PANEL, h=18))
        S.append(T(DR - 18, y + 20, io, DIM, 11, anchor="end", mono=True))
        row_y[nm] = y
        y += 36
S.append(T(DX + 16, cy + 392, "perceive chain discovered by find_pipeline (no router); "
                              "profile-sweep via the L4 phase_1 sweep.", DIM, 10.5))

# ── callouts ──
LX, RX = 282, DR + 18
S.append(lab(LX, 120, "section + entry", "#secCapacities · renderCapacities()", "end")); S.append(lead(LX + 4, 116, DX, cy + 8))
S.append(lab(LX, 175, "phase header", ".ph", "end", ACCENT)); S.append(lead(LX + 4, 171, DX + 16, cy + 48))
S.append(lab(LX, 240, "capacity row", ".cap", "end")); S.append(lead(LX + 4, 236, DX + 14, row_y["comprehend_task"] + 15))
S.append(lab(LX, 300, "index", ".n", "end")); S.append(lead(LX + 4, 296, DX + 20, row_y["build_grid"] + 15))
S.append(lab(LX, 360, "capacity name", ".nm (mono)", "end")); S.append(lead(LX + 4, 356, DX + 40, row_y["extract_objects"] + 15))
S.append(lab(LX, 430, "list container", ".caps", "end")); S.append(lead(LX + 4, 426, DX, cy + 300))

S.append(lab(RX, 175, "list = DATA.capacities", "ordered_catalog()", "start")); S.append(lead(RX - 4, 171, DR, cy + 60))
S.append(lab(RX, 250, "category pill", ".cat", "start")); S.append(lead(RX - 4, 246, DX + 240, row_y["comprehend_task"] + 15))
S.append(lab(RX, 320, "consumes → produces", ".io (mono)", "start")); S.append(lead(RX - 4, 316, DR - 70, row_y["same_object"] + 15))
S.append(lab(RX, 400, "intra-grid family", "touching = predicate", "start", OK)); S.append(lead(RX - 4, 396, DX + 240, row_y["touching"] + 15))

footer(S, W, H, "Phases: perceive · profile-sweep · induce · intra-grid. The perceive chain is composed by "
                "find_pipeline (PRODUCES/CONSUMES); comparators run via the L4 phase_1 sweep.")
render(S, "capacities_map.png", W, H)
