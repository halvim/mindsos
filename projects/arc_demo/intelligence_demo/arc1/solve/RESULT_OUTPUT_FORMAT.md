# arc1/solve — canonical result-output format

This is the **canonical** way a phase result is reported. When the user asks for
"the result output" of a phase, reproduce it **exactly** in this format (the full
STEP block: the header lines + the `result` block), as pasted below.

## Reference example — Phase 1 (Input + Perceive), task #294

```
── STEP 1 · Input + Perceive ────────────────────────────────────────────  [general]
   uses     task input · arc_grids.get_task · arc_profile.grid_summary(extract_objects, extract_points, normalize_shape, palette, dimension)
   → future L4 task intake → TaskRun + L3 perceive chain via cl.invoke (find_pipeline) · mindsos_intelligence/orchestrator.py + mindsos_capacity/pipeline.py
   produces raw task · per-grid objects · points · shapes · palette · dims
   result   2 train pairs · 1 test
            Pair 1: In 10×10 pal[0,5] · 3 obj  →  Out 10×10 pal[0,2,5] · 5 obj
            Pair 2: In 10×10 pal[0,5] · 3 obj  →  Out 10×10 pal[0,2,5] · 5 obj
```

## Reference example — Phase 2 (Profile), task #294

```
── STEP 2 · Profile ─────────────────────────────────────────────────────  [general]
   uses     step-1 ctx · arc_profile.build_profile(match_pair, profile_sweep, hypotheses) · arc_search.task_tokens(same_cell_count_pairs, same_bbox_area_pairs)
   → future L4 phase_1 sweep — L3 profilers (compare_*, same_*) · mindsos_intelligence/builtins/phase1_v0.py + mindsos_capacity
   produces profile · profiler tokens
   result   dims=preserved · palette=added
            Pair 1:
              same_object  In1.O0.black = Out1.O0.black
            Pair 2:
              same_object  In2.O0.black = Out2.O0.black
```

### Phase 2 result body — format

- **Header line:** `dims={…} · palette={…}` — the two multi-result profiler
  tokens (one value each, every task):
  - `dims` = `compare_grid_dimension` ∈ `preserved | grew | shrank | mixed | varies`.
  - `palette` = `compare_palette` ∈ `preserved | added | removed | added+removed | varies`.
- **Per train pair with ≥1 positive match** (pairs with no positive are
  **omitted**): a `Pair {p}:` line, then one indented tier line per positive in
  fixed order **same_object → same_shape → same_point**. Tier line = 2-space
  indent, label left-justified to 11 chars, 2 spaces, body.
  - `same_object  In{p}.O{i}.{color} = Out{p}.O{j}.{color}, …` — an input Object
    identical (same cells + colour) to an output Object.
  - `same_shape   {left} = {right}` — same normalized shape, **not** identical;
    each side is `In{p}.O{i}.{color}` or bracketed `[…, …]` when >1. Shown only
    for non-identical shape_groups.
  - `same_point   In{p}.P{i} = Out{p}.P{j}, …` — matched single-cell Points
    (no colour printed for points).
- **Background is INCLUDED** (LOCKED 2026-06-27 — `O0.black` = the background
  region is reported like any object; do NOT exclude it, do not ask again). The
  reversed bg-exclude attempt was rejected.
- Refs: `In{p}`/`Out{p}` = pair p in/out grid; `O{i}` Object, `P{i}` Point,
  `.{color}` colour name. The displayed `same_shape` diverges from the
  `same_shape` token (token also counts identical objects via the wired
  `same_object ⟹ same_shape` skip — see `./arc solve --inferences`).

## Reference example — Phase 3 (Subdivision), task #294

```
── STEP 3 · Subdivision ─────────────────────────────────────────────────  [general*]
   uses     step-2 ctx · arc_grids.subdivisions(inset) — input object partitioned by ≥2 output insets
   → future L3 derivation — subdivision (inset partition) over the profile · mindsos_capacity (→ L4 induce/learner)
   produces subdivision partitions (B → B1,B2,…)
   result   subdivision — yes (∀demo 2/2)
            Pair 1 [split]: In1.O1.grey → {Out1.O1.grey, Out1.O2.red}
                     In1.O1.grey → In1.O1.sub1.grey, In1.O1.sub2.grey
            Pair 1 [split]: In1.O2.grey → {Out1.O3.grey, Out1.O4.red}
                     In1.O2.grey → In1.O2.sub1.grey, In1.O2.sub2.grey
            Pair 2 [split]: In2.O1.grey → {Out2.O1.grey, Out2.O2.red}
                     In2.O1.grey → In2.O1.sub1.grey, In2.O1.sub2.grey
            Pair 2 [split]: In2.O2.grey → {Out2.O3.grey, Out2.O4.red}
                     In2.O2.grey → In2.O2.sub1.grey, In2.O2.sub2.grey
```

### Phase 3 result body — format

- **Header line:** `subdivision — {yes|no} (∀demo {k}/{n})` — `yes` iff a cover
  holds on **every** demo pair (either direction); `{k}/{n}` = pairs with ≥1
  finding / total pairs.
- **Per finding** (two lines): the whole `→ {parts}`, then the whole `→
  {sub-label}, …`:
  - `Pair {p} [{direction}]: {B} → {{part, part, …}}`
  - `{B} → {O{i}.sub1.{color}}, {O{i}.sub2.{color}}, …`
- **`{direction}` tag** — `split` (whole = INPUT object, parts = OUTPUT pieces)
  or `assemble` (whole = OUTPUT object, parts = INPUT pieces). Subdivision is
  **BIDIRECTIONAL** (LOCKED 2026-06-27): a pair holds if a cover exists in
  EITHER direction.
- `{B}` = `In{p}.O{i}.{color}` (split) or `Out{p}.O{i}.{color}` (assemble);
  parts = `Out…`/`In…` objects (`.O{j}.{color}`) or points (`.P{j}`, no colour).
- **Sub-label = `{side}{p}.O{i}.sub{k}.{color}`** — the `.sub{k}` suffix comes
  **before** the colour (LOCKED 2026-06-28; e.g. `In1.O1.sub1.grey`, not
  `In1.O1.grey.sub1`). The colour is the **whole's** colour.
- **Background is NOT excluded** (bg-AGNOSTIC, LOCKED 2026-06-27 — `subdivisions`
  treats every object incl. the background as a candidate whole, both
  directions). This is intentionally *different* from the `union` operator, which
  is bg-EXCLUDED. Empty pairs print nothing; a `no` task shows the header only.

## Reference example — Phase 4 (Component Re-Comparison), task #294

```
── STEP 4 · Component Re-Comparison ─────────────────────────────────────  [general*]
   uses     step-3 ctx · step-3 findings · same_object/same_point/same_shape(sub-piece, component) per sub-piece
   → future L3 reasoning — re-compare derived sub-pieces against perceived components (same_*) · mindsos_capacity (→ L4 induce/learner)
   produces sub-piece ↔ component correspondences
   result   component re-comparison — 8 sub-piece correspondence(s)
            Pair 1:
              same_object In1.O1.sub1.grey = Out1.O1.grey  [from split]
              same_shape In1.O1.sub2.grey = Out1.O2.red  [from split]
              same_object In1.O2.sub1.grey = Out1.O3.grey  [from split]
              same_shape In1.O2.sub2.grey = Out1.O4.red  [from split]
            Pair 2:
              same_object In2.O1.sub1.grey = Out2.O1.grey  [from split]
              same_shape In2.O1.sub2.grey = Out2.O2.red  [from split]
              same_object In2.O2.sub1.grey = Out2.O3.grey  [from split]
              same_shape In2.O2.sub2.grey = Out2.O4.red  [from split]
```

### Phase 4 result body — format

- **Header line:** `component re-comparison — {n} sub-piece correspondence(s)`
  — `{n}` = total sub-pieces across all subdivision findings (objects **and**
  points, so "component", not "object"). A task with no subdivision finding
  shows the header only (`— 0 …`).
- **Grouped by pair** (pairs with ≥1 finding only), in pair order: a `Pair {p}:`
  line, then one 2-space-indented line per sub-piece of every finding in that
  pair (finding order, then sub-index):
  - `{relation} {sub} = {component}  [from {direction}]`
- **`{relation}`** — the strongest true relation between the sub-piece and the
  component it covers (cells match by construction): `same_object` if the colour
  is kept (object), `same_point` if kept (point), else `same_shape` (colour
  changed; the colour-changed-point case is also `same_shape`, verified in a
  later phase).
- **`{sub}`** = `{side}{p}.O{i}.sub{k}.{color}` — the `.sub{k}` suffix comes
  **before** the colour; colour is the **whole's** colour.
- **`{component}`** = `{side}{p}.O{j}.{color}` (object) or `{side}{p}.P{j}`
  (point, no colour).
- **`[from {direction}]`** — `[from split]` / `[from assemble]`, carrying the
  phase-3 `[split]`/`[assemble]` tag the sub-piece came **from**.

## Block structure (what each line is)

- `── STEP {n} · {name} ───…  [{scope}]` — phase number, name, scope tag.
- `   uses     {input ctx} · {real function chain}`
- `   → future {proposed MindsOS feature + location}`
- `   produces {what the phase adds to ctx}`
- `   result   {header line}` then the multi-line body indented 12 spaces.
- `   Background Color  {per-grid bg}` — **phases 2+ only.** Each train pair's
  background candidate(s) from `bg_advance`: `Pair{i}.bg=X` when one side
  resolved to `X` **and** `X` is a candidate on the other side
  (consistency-guarded propagation, option C), else `In{i}.bg={…} ·
  Out{i}.bg={…}`; the test grid always shows `test.bg={…}`. Singletons render
  bare (no braces), multi-candidate sets in `{…}`; colours are names.

Result body per phase = a header line + one block per train pair (see STEPS.md
for each phase's body format). This file fixes the **rendering** contract; the
per-phase body content is defined in `pipeline.py` / `arc_solver`.

## Locked format decisions

- **Phase 1 `· {k} pt` segment is CONDITIONAL** (shown only when a grid has
  points > 0). LOCKED 2026-06-27 — do not change, do not ask again. Verified
  conformant across all 400 train tasks (1302 pair-lines; 972 with `pt`, 330
  without). A grid with no points renders `· {n} obj` with no `pt` segment.
- **Phase 2 INCLUDES the background** in the same_object/same_shape/same_point
  tiers. LOCKED 2026-06-27 — a bg-exclude change was tried and reverted; do not
  exclude bg, do not ask again.
- **Phase 2 OMITS empty pairs** — a pair with no positive tier prints nothing;
  a task with no positive match on any pair shows the **header line only**.
  LOCKED 2026-06-27 (already implemented via the `if tiers:` guard; verified
  400/400, 100 tasks header-only). Do not add empty-pair markers, do not ask again.
- **Phase 3 subdivision is BIDIRECTIONAL + bg-AGNOSTIC.** It fires if a disjoint
  cover holds in EITHER direction — `split` (input whole / output parts) or
  `assemble` (output whole / input parts) — each finding tagged `[split]` /
  `[assemble]`; background is included as a candidate whole. LOCKED 2026-06-27
  (user chose bg-agnostic over the bg-excluded `union` route). Do not ask again.
- **Phase 3 sub-label = `{side}{p}.O{i}.sub{k}.{color}`** — `.sub{k}` before the
  colour (e.g. `In1.O1.sub1.grey`). LOCKED 2026-06-28; shared with phase 4.
- **Phase 4 (Component Re-Comparison) format LOCKED 2026-06-28.** Header
  `component re-comparison — {n} sub-piece correspondence(s)`; per pair, one
  `{relation} {sub} = {component}  [from {direction}]` line per sub-piece;
  relation = same_object / same_point if colour kept, else same_shape; verified
  structurally uniform across all 400 tasks (0 nonconforming; 156 with content,
  244 header-only). Do not re-litigate.
- **The `status` line is REMOVED** (2026-06-28). `./arc solve` no longer
  checkpoints — every phase recomputes in-memory each invocation — so the
  `status computed → step-{n}.json` / `cached ✓` line carried no information and
  was dropped. A STEP block now opens with the `── STEP {n} · {name} …` bar
  followed directly by the `uses` line. The phase-1–4 reference blocks above are
  relocked without it.
