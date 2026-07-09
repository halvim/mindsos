# ARC Build Phase-Map — decomposed model → executed through the layer

**Status:** planned 2026-07-07 · from the decomposition chat · **build not started**
**Model:** `arc_solver/ATOM_TABLE.md` (the decomposed pipelines/caps/DataStates).
**Core deps:** shipped — `operand-arity-groups-readsmm-confirmed` (ADR-0198/0199/0200 = C1/C3/C4).
**Machine discipline:** Cowork builds → Mac commits → Linux gates. Gate = root `./run_spike` = **14
`[ok]`** (400-task profiling + #8 solves). Never `git add -A`; `arc_debug_data.js` stays gitignored.

## Locked decisions

- **Goal = full execution (PB-3b):** every pipeline runs through `cl.invoke`, all 400 tasks — not a
  #8-only specimen. End state: the imperative `arc_solver` is deleted; the solver is fully
  layer-executed.
- **PB-1a (corrected):** re-pin activates Part-6 input validation. `touching_delta`'s current
  `input_group=fold` **escape** (Part-6 skips fold validation) should survive re-pin — so re-pin does
  **not** break it, and the honest C3 declaration is **deferred to Slice 4** (its real inputs —
  `correspondence`, `touchings*` — aren't layer-produced until then; declaring them in Slice 1 would
  make them unsourceable). **Slice 1 must VERIFY the fold escape holds**; if it doesn't, revert the
  biting check to inline until Slice 4.
- **PB-2a:** **shadow-and-verify** per slice — run inline + layer both, assert parity across 400
  tasks (the D3 biting-check generalized). Inline removed only in the final slice.
- **PB-4a:** **Slice 2 is a measured go/no-go on performance.** Full layer-execution of
  `comparison_matrix` (~10⁶ invokes) + shadow-verify doubling may blow the gate wall-time. Measure vs
  a budget before committing Slices 3–8.
- `reads_mm=False` on every ARC cap (default). Re-pin is safe: no ARC body reads `mm_handle` today.

## Slices (each ends green at 14 `[ok]`; Cowork-gate → Mac commit → Linux confirm)

| # | slice | lands | shadow-verify vs |
|---|---|---|---|
| **1** | **Re-pin + registration** | re-pin `STATE.json` `phase50` → the core tag; register 14 comparators with `operand_arity` (positional; `touching` operands wrap as `region`); groups with `group`/`member_ds`; **verify the `touching_delta` fold escape survives** (no declaration change yet) | (topology only; #8 still solves via the D3 spike, unchanged) |
| **2** | **`comparison_matrix` executable — PERF GO/NO-GO** | L4 assembles the matrix by invoking comparators through `cl.invoke`, exhaustive in×out, **both `inset` directions** (PB-C); `object_matches*`/`shape_matches*`/`point_matches*` become **slices** | inline comparison results, all 400 · **MEASURE gate wall-time vs budget** |
| **3** | **profile + bg** | `classify_variance`; profile-pipeline (dims-vary + palette-vary); bg-pipeline (`eliminate_bg_colour`, reactive on `objects*` change); **kill `bg_deduction`, delete `profile`-as-DataState** | inline profile + bg_advance |
| **4** | **correspondence + touching-change** | `resolve_correspondence` (matrix → 1:1); **`touching_delta` honest C3 declaration** (`touchings_in*`, `touchings_out*`, `correspondence`, `bg_colour?`) — its real inputs now exist → drop the fold escape; scoped ≥1-moved; **kill `build_correspondence`** | inline `_correspondence` / `touching_changes` |
| **5** | **motivations + selector** | `detect_*_motivation` → `motivations`; `identify_roles` → `synthesize_selector` (motivations = soft scope) → `selector` | inline `motivations` / `stage_roles` / `_selectors_for` |
| **6** | **emit + select + apply** | `assemble_*` → `candidates*`; `combine_candidates`, `grids_equal`, `resolve_selector`, `∀-cover`; `select_rules` verifier (`apply_rule_set` + match); `apply_solution` (thin); `matches_withheld` → **eval, lifted out**. **#8 now solves fully through the layer** | inline `rules` / `select_rules` / `_apply_candidate_set` |
| **7** | **subdivision + re-comparison** | `detect_cover` → `subdivision`; `classify_part_relation` (reuses `same_object`/`recolored`) → `recomparison`; **delete `enclosed`** (`inside` covers containment for all colours; no `enclose_bg`) | inline `subdivisions` / `step_objcomp` |
| **8** | **Remove inline solver** | delete the imperative `arc_solver` paths + the shadow harness; solver **fully layer-executed** | final parity confirmed; 14 `[ok]` purely through the layer |

## Slice-2 go/no-go (PB-4a)

Budget: define at Slice 2 (proposal: gate wall-time **≤ 3× current**). If exceeded, choose a mitigation
**with data** before Slice 3 — do **not** pre-commit:
- optimize/batch `cl.invoke` (a new **core** request);
- prune the matrix to only downstream-needed cells (revises the "exhaustive" model);
- raise the gate timeout (accept a slow gate);
- hybrid: execute the decision pipelines through the layer, keep the 400-task comparison **bulk**
  inline (retreats from full (b) for the matrix only).

## Not in this build (unchanged)

- **C5** (known-pipeline L2 record/lookup) — deferred (ADR-0184); L4 code sequences the pipelines.
- **E-fixes** rideable per slice: E7 `arc.color` decl + `recolor↔recolor_transform` pairing;
  E2 drop `arc.background` orphan. E1 `perceived_grid` producer decided when `inside` is wired (Slice 4/2).
