# Solver UI — reference map

A reference for modifying the **Solver** section of `arc_debug.html` (the read-only
run viewer, option A). Maps every visible part → its DOM id / CSS class / JS
function / data field. Companion: `arc_solver.py` (computes the data),
`../PIPELINE.md` "Reason-stage design" (the decisions behind it).

Everything is **data-driven from `window.ARC_DATA.solver`** (written by
`run_spike.py` → `arc_solver.build_solver`). To change *content*, edit
`arc_solver.py` + regenerate; to change *layout/style*, edit the `solver*`
JS/CSS in `arc_debug.html`.

---

## Wiring (how the section is mounted)

| Part | Name in code | File |
|---|---|---|
| Side-menu item | `<div class="mi" data-sec="secSolver">Solver</div>` | `arc_debug.html` `<nav>` |
| Section element | `<section id="secSolver">` → inner `<div id="solverBody">` | `arc_debug.html` body |
| Section switching | `SECTIONS` array (must list `"secSolver"`) + `setSection()` | `arc_debug.html` script |
| Entry point | `renderSolver()` (called in `init()` after `searchInit()`) | `arc_debug.html` script |
| Data source | `DATA.solver` = `payload["solver"]` = `arc_solver.build_solver(prof8)` | `run_spike.py` |
| Scope | task #8 only (`arc_solver.TASK8 = "05f2a901"`); `DATA.solver` is `null` otherwise | `arc_solver.py` |

---

## Shared building blocks (CSS classes)

| Class | What it styles |
|---|---|
| `.shdr` | header row: "Solver · #8 · read-only run" + a green `SOLVED ✓` banner when `stage6.matches_withheld === true` |
| `.sstep` | a step **card** (steps 1–2) |
| `.sshead` | a step card's header bar |
| `.sbadge` + `.done` / `.pend` | the round step-number badge (green done / muted pending) |
| `.sttl` | step title text |
| `.sstat` | the right-aligned status chip ("done") |
| `.sbody` | a step card's body (vertical stack, `gap:13px`) |
| `.sl` | a small uppercase block label ("objects", "result", …) |
| `.sres` | the highlighted **result** box inside a step |
| `.smono` | monospace inline text (refs, pairs) |
| `.stbl` | the combination-test table (step 2) |
| `.sflag` / `.sflag .fk` | a flag band (reserved for stages 3+; step 1's blocking flag was removed) |
| `.spend` | a pending-step dashed row (steps 3–6) |
| `.schip` | an object role chip (step 1) |

Colours come from the page `:root` vars: `--touch` (violet, touching), `--ok`
(green, verified), `--accent` (blue, refs), `--warn` (amber, flags), `--dim`,
`--line`, `--panel`/`--panel2`. Role-chip colours: the `ROLECLR` JS map
(`background` grey / `mover` green / `target` blue).

---

## Step 1 — `solverStep1(st)`  ← `DATA.solver.stage1`

| UI element | Class / markup | Data field |
|---|---|---|
| Object role chips | `.schip`, coloured via `ROLECLR[role]` | `stage1.roles_demo1[]` = `{ref, role, color, size}` |
| Touching `input → output` line | `.smono` | `stage1.touching_in_excl/_full`, `touching_out_excl/_full` |
| Background toggle | `#sbgtg` (click → `solverBg = !solverBg; renderSolver()`) | toggles `_excl` vs `_full` display |
| Gained-pair highlight | inline violet pill (`+ Oa·Ob`) | `stage1.gained_demo1[]` (membership test) |
| Result box | `.sres` | `stage1.change` = `{state, kind, persists}` |
| Background note | `.sres` footer line | `stage1.background` = `{color, objects[], note}` |

State var: `solverBg` (module-level JS bool; default `false` = background excluded).

---

## Step 2 — `solverStep2(st)`  ← `DATA.solver.stage2`

| UI element | Class / markup | Data field |
|---|---|---|
| Persistence row | `.smono`, green spans | `stage2.persistent[]` = `[name, "k/n"]` |
| Combination test table | `.stbl` (cols: combo / obj-per-pair / d1 d2 d3 / verdict) | `stage2.combos[]` = `{combo, objects[], per_demo[], verdict}` |
| "static excluded" note | small `.dim` line | `stage2.excluded_static[]` |
| Result box | `.sres` | derived from `combos[0]` |

---

## Step 3 — `solverStep3(st)`  ← `DATA.solver.stage3`

| UI element | Class / markup | Data field |
|---|---|---|
| Mover / target candidate chips (locked one highlighted + ✓, others dimmed) | `.schip` | `stage3.mover.candidates[]`, `stage3.target.candidates[]` |
| Resolved status chip | `.sstat` ("resolved · shape") | `stage3.selected`, `stage3.mover_selected`, `stage3.target_selected` |
| Tie note | small `.dim` line | `stage3.tie`, `stage3.note` |

`.sbadge.flag` / `.sstat.flag` (amber "needs you") and `.sflag` remain available for
a future *unresolved* flag, but #8's selector tie ships **resolved** (owner pick = shape).

## Step 4 — `solverStep4(st)`  ← `DATA.solver.stage4`

| UI element | Class | Data field |
|---|---|---|
| Rule line | `.sres` + `.smono` | `stage4.rule`, `mover_sel`, `target_sel` |
| Policy / dependency | `.sl` blocks | `stage4.policy`, `stage4.dag` |

## Step 5 — `solverStep5(st)`  ← `DATA.solver.stage5`

| UI element | Class | Data field |
|---|---|---|
| Per-demo verify table | `.stbl` (demo / slide / result) | `stage5.per_demo[]` = `{demo, steps, match}` |
| Verdict | `.sres` | `stage5.verdict`, `stage5.all_match` |

## Step 6 — `solverStep6(st)`  ← `DATA.solver.stage6`

| UI element | Class / fn | Data field |
|---|---|---|
| Test input / produced output grids | `solverGridHTML(cells)` | `stage6.input`, `stage6.output` |
| Withheld-match badge | inline green/amber pill | `stage6.matches_withheld` (true/false/null) |
| Step count | `.sl` label | `stage6.steps` |

## Pending steps — inline in `renderSolver()`  ← `DATA.solver.pending`

When `pending` is non-empty, a "pending (not built)" `.sl` label + `.spend` rows
(`.sbadge.pend`) render after the built steps. For task #8 `pending` is now `[]`
(all six stages built), so the block is skipped.

---

## How to modify (common edits)

- **Change what a step shows** → edit the matching field in `arc_solver.build_solver`, rerun `run_spike`.
- **Restyle a step** → edit the `solver*` JS template strings + the `.s*` CSS block in `arc_debug.html`.
- **Promote a pending step to built** → add a `solverStepN(...)` template + its data in `build_solver`, append it in `renderSolver()`, and remove its `.spend` row from `pending`.
- **Add an interactive (non-recompute) view toggle** → precompute both variants in `build_solver` (as done for background `_excl`/`_full`), add a JS state var + a toggle element that calls `renderSolver()`. Recompute-requiring choices stay option A (answer in chat → rerun).
- **Regenerate after any code/data change**: `python -m arc_solver.spike.run_spike` (writes `arc_debug_data.js`), then reload `arc_debug.html`.
