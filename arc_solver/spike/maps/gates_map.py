"""Gates section — part-name callout map → ../gates_map.png.

Four phases: Profiling → Components → Gating → Comparison Capacity. A comparison
capacity carries its own fires/— + a { }json editor; an implied capacity is
indented under the one that implies it (inside ⟹ touching). renderGates ←
DATA.gates.{comparisons (phase/division/implies), capacities (guards)}.
"""
from _kit import (R, T, chip, lead, lab, header, footer, render,
                  PANEL, PANEL2, LINE, INK, DIM, ACCENT, OK)

W, H = 1180, 560
S = []
header(S, W, "Gates — part names (use the name or the .class)",
       "Phase 1 Profiling · Phase 2 Components · Phase 3 Gating · Phase 4 Comparison Capacity")

# ── phase bands ──
for bx, bw, label in [(286, 156, "PHASE 1 · Profiling"), (456, 140, "PHASE 2 · Components"),
                      (610, 86, "PHASE 3 · Gating"), (710, 296, "PHASE 4 · Comparison Capacity")]:
    S.append(f'<rect x="{bx}" y="92" width="{bw}" height="430" rx="8" fill="{ACCENT}" opacity="0.06"/>')
    S.append(T(bx + bw / 2, 110, label, ACCENT, 9.5, 700, "middle"))

# ── phase 1: comparison box ABOVE its result chips (holding one green) ──
S.append(R(298, 138, 132, 24, 5, PANEL2, ACCENT, 1.3))
S.append(T(364, 154, "compare_grid_dimension", INK, 8, 600, "middle"))
for i, (r, ok) in enumerate([("preserved", True), ("grew", False), ("shrank", False)]):
    S.append(chip(300, 172 + i * 24, 128, r, INK if ok else DIM, OK if ok else LINE, PANEL))

# ── phase 2: component atom box ABOVE fires/— ──
S.append(R(468, 300, 116, 24, 5, PANEL2, ACCENT, 1.3))
S.append(T(526, 316, "same_shape", INK, 9, 600, "middle"))
for i, (r, ok) in enumerate([("fires", True), ("—", False)]):
    S.append(chip(470, 334 + i * 24, 112, r, INK if ok else DIM, OK if ok else LINE, PANEL))

# ── phase 3: per-capacity AND gate ──
S.append(f'<circle cx="653" cy="184" r="14" fill="{PANEL2}" stroke="{OK}" stroke-width="2"/>')
S.append(T(653, 188, "AND", OK, 8, 700, "middle"))
S.append(T(653, 250, "AND · OR", DIM, 8, anchor="middle"))
S.append(T(653, 263, "AND+OR · OR+AND", DIM, 7, anchor="middle"))


def cap(x, y, w, nm, fires):
    on = fires
    S.append(R(x, y, w, 28, 6, PANEL2 if on else "#161a24", OK if on else LINE, 2 if on else 1.2))
    S.append(T(x + 12, y + 18, nm, INK if on else DIM, 10, 600))
    S.append(R(x + w - 92, y + 5, 34, 18, 5, PANEL, OK if on else LINE))
    S.append(T(x + w - 75, y + 17, "fires" if on else "—", OK if on else DIM, 8, anchor="middle"))
    S.append(R(x + w - 50, y + 5, 46, 18, 5, "#1a1d27", ACCENT, 1))
    S.append(T(x + w - 27, y + 17, "{ }json", ACCENT, 8, anchor="middle"))


# ── phase 4: capacities (inter / intra, indentation) ──
S.append(T(722, 150, "INTER-GRID", DIM, 9, 700))
for i, (nm, fr) in enumerate([("moved", True), ("recolored", False), ("reflected", False), ("rotated", False)]):
    cap(722, 158 + i * 34, 180, nm, fr)
S.append(T(722, 318, "INTRA-GRID", DIM, 9, 700))
cap(722, 326, 180, "inside", True)
# touching: implied → indented, SOLID box (full board)
S.append('<path d="M728,354 L728,378 L740,378" fill="none" stroke="%s" stroke-width="1.3"/>' % LINE)
cap(740, 364, 162, "touching", True)

# ── edges (illustrative active path) ──
S.append(f'<path d="M584,346 C 620,346 620,184 639,184" fill="none" stroke="{OK}" stroke-width="1.8"/>')
S.append(f'<path d="M667,184 C 695,184 695,172 722,172" fill="none" stroke="{OK}" stroke-width="1.8"/>')

# ── matching-task panel ──
S.append(R(1030, 138, 132, 300, 8, PANEL, LINE))
S.append(T(1044, 162, "tasks match", INK, 11))
for i in range(6):
    S.append(R(1044, 184 + i * 22, 104, 16, 4, PANEL2, LINE))

# ── callouts ──
S.append(lab(280, 116, "phase band", ".band", "end", ACCENT)); S.append(lead(284, 112, 286, 100))
S.append(lab(280, 200, "comparison + chips", "DATA.gates.comparisons[]", "end")); S.append(lead(284, 196, 298, 184))
S.append(lab(653, 300, "gate · guard {op}", "per capacity", "middle", ACCENT)); S.append(lead(653, 292, 653, 198))
S.append(lab(560, 470, "capacity · fires/— · { }json", "phase=capacity · gateJson(k)", "middle", OK)); S.append(lead(660, 466, 722, 360))
S.append(lab(960, 392, "implied → indented", "inside ⟹ touching · skip", "middle")); S.append(lead(905, 392, 902, 378))

footer(S, W, H, "renderGates draws Phase 1-4 from DATA.gates; result chips filter (gateChipClick); each capacity "
                "gate = AND(own fire, requires); an implied capacity is indented (inside ⟹ touching) and skipped; "
                "{ }json edits a gate; boxes drag; edges highlight on hover.")
render(S, "gates_map.png", W, H)
