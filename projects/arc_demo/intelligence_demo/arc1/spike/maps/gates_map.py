"""Gates section — part-name callout map → ../gates_map.png."""
from _kit import (R, T, chip, lead, lab, header, footer, render,
                  PANEL, PANEL2, LINE, INK, DIM, ACCENT, OK)

W, H = 1180, 560
S = []
header(S, W, "Gates — part names (use the name or the .class)",
       "comparison → result → gate → capacity · renderGates ← DATA.gates + gates.holds/enabled")

# ── phase bands (tint only) ──
b1x, b1w = 300, 220
b2x, b2w = 530, 170
S.append(f'<rect x="{b1x}" y="92" width="{b1w}" height="370" rx="8" fill="{ACCENT}" opacity="0.06"/>')
S.append(f'<rect x="{b2x}" y="92" width="{b2w}" height="370" rx="8" fill="{ACCENT}" opacity="0.06"/>')
S.append(T(b1x + b1w / 2, 110, "PHASE 1 · Profiling", ACCENT, 11, 700, "middle"))
S.append(T(b2x + b2w / 2, 110, "PHASE 2 · Components", ACCENT, 10, 700, "middle"))
S.append(T(748, 110, "GATE", DIM, 11, 700, "middle"))
S.append(T(860, 110, "CAPACITY", DIM, 11, 700, "middle"))

# ── phase 1: comparison + result chips ──
S.append(R(b1x + 8, 150, 150, 26, 5, PANEL2, ACCENT, 1.4))
S.append(T(b1x + 83, 167, "compare_grid_dimension", INK, 9, 600, "middle"))
for i, (r, ok) in enumerate([("preserved", True), ("grew", False), ("shrank", False),
                             ("mixed", False), ("varies", False)]):
    cy = 138 + i * 24
    S.append(f'<polyline points="{b1x+158},163 {b1x+170},{cy+10}" fill="none" stroke="{LINE}" stroke-width="1" opacity="0.6"/>')
    S.append(chip(b1x + 170, cy, 74, r, INK if ok else DIM, OK if ok else LINE, PANEL))

# ── phase 2: comparison + result chips ──
S.append(R(b2x + 6, 300, 120, 26, 5, PANEL2, ACCENT, 1.4))
S.append(T(b2x + 66, 317, "same_shape", INK, 9.5, 600, "middle"))
for i, (r, ok) in enumerate([("fires", True), ("—", False)]):
    cy = 296 + i * 24
    S.append(chip(b2x + 130, cy, 50, r, INK if ok else DIM, OK if ok else LINE, PANEL))

# ── gate (AND) ──
S.append(f'<circle cx="748" cy="240" r="16" fill="{PANEL2}" stroke="{ACCENT}" stroke-width="1.7"/>')
S.append(T(748, 238, "AND", ACCENT, 9, 700, "middle"))
S.append(T(748, 248, "all_required", DIM, 5.5, anchor="middle"))

# ── capacities ──
S.append(R(810, 221, 110, 38, 6, PANEL, OK, 2.4))
S.append(T(865, 245, "moved", INK, 13, 600, "middle"))
S.append(R(810, 320, 110, 38, 6, PANEL, LINE, 1.3))
S.append(T(865, 344, "touching", DIM, 13, 600, "middle"))

# ── matching-task panel ──
S.append(R(958, 150, 178, 300, 8, PANEL, LINE))
S.append(T(972, 174, "12 / 60 tasks match", INK, 12))
S.append(T(972, 192, "click chips to filter", DIM, 10))
for i in range(6):
    S.append(R(972, 210 + i * 22, 150, 16, 4, PANEL2, LINE))

# ── callouts (left) ──
LX = 290
S.append(lab(LX, 116, "phase band", ".band", "end", ACCENT)); S.append(lead(LX + 4, 112, b1x, 100))
S.append(lab(LX, 168, "comparison", "DATA.gates.comparisons[]", "end")); S.append(lead(LX + 4, 164, b1x + 8, 163))
S.append(lab(LX, 250, "result chip (click)", "gatePick(cmp, result)", "end")); S.append(lead(LX + 4, 246, b1x + 170, 210))
S.append(lab(LX, 330, "holding result", "gates.holds[cmp] (green)", "end", OK)); S.append(lead(LX + 4, 326, b1x + 170, 138))

# ── callouts (gate from above, capacity from below, panel inline) ──
S.append(lab(700, 150, "gate AND/OR", "guard {op}", "middle", ACCENT)); S.append(lead(720, 158, 740, 226))
S.append(lab(865, 400, "capacity (enabled)", "gates.enabled[k]", "middle", OK)); S.append(lead(865, 388, 865, 360))
S.append(lab(1047, 470, "matching panel", "_gateMatches()", "middle")); S.append(lead(1047, 458, 1047, 450))

footer(S, W, H, "The Gates section: renderGates draws comparison→result→gate→capacity from DATA.gates + "
                "per-task gates.holds/enabled; result chips filter (gatePick); the panel lists matching tasks.")
render(S, "gates_map.png", W, H)
