# Build Slice 1 — Re-pin + registration (additive; no execution change)

**Goal:** bring the new core (C1/C3/C4) into `arc-solver` and register the comparators' `operand_arity`
+ the group DataStates. **No execution change** — the inline solver still runs the gate; the gate stays
**14 `[ok]`**. This slice makes the *topology* honest; execution migrates in Slice 2+.
Refs: `BUILD_PHASE_MAP.md`, `ATOM_TABLE.md`, `CORE_REQUESTS.md`. Prereq verified: the `arc-solver`
worktree is on `phase50` — `operand_arity`/`group`/`member_ds` are **absent** until step 0.

---

## Step 0 — [Mac] core merge + re-pin  *(commit-worthy; Mac owns it)*

```
# on the arc-solver branch
git merge operand-arity-groups-readsmm-confirmed      # main 54b00c0 (ADR-0198/0199/0200)
# resolve any conflicts in mindsos_* (demo has diverged from main)
```
Then edit `STATE.json`: `core_version` `"phase50"` → the new tag/version.
**Re-pin safety (verified):** no ARC cap body reads `mm_handle`, so the ADR-0200 `reads_mm` gate does
not break any ARC body. `touching_delta` keeps `input_group=fold` — the escape Part-6 skips.

**After step 0, confirm the fields exist:**
`grep -n "operand_arity" mindsos_capacity/capacity.py` and `grep -n "member_ds" mindsos_capacity/datastate.py`
must both hit. If not, the merge didn't land the tag.

---

## Step 1 — [Cowork] `operand_arity` on the 14 pairwise comparators

File: `arc_solver/spike/arc_capacities.py`. Add `operand_arity={<DS>: 2}` to each declaration below
(the register-time check requires the key to be a **declared input** — it already is).

| capacity | add |
|---|---|
| `compare_grid_dimension` | `operand_arity={DS_GRID: 2}` |
| `compare_palette` | `operand_arity={DS_PALETTE: 2}` |
| `same_object` | `operand_arity={DS_OBJECT: 2}` |
| `same_shape`, `same_cell_count`, `same_bbox_area` | `operand_arity={DS_SHAPE: 2}` |
| `same_point` | `operand_arity={DS_POINT: 2}` |
| `moved`, `inset`, `union`, `recolored` | `operand_arity={DS_OBJECT: 2}` |
| `rotated`, `reflected` | `operand_arity={DS_SHAPE: 2}` |
| `touching` | change `inputs=(DS_OBJECT,)` → `inputs=(DS_REGION,)`, `operand_arity={DS_REGION: 2}` |

**`touching` note:** its operands are Object **or** Point (both `region`), so the honest declared type is
`DS_REGION` (ADR-0198). Stub body is unaffected (topology-only); the operand→region *wrap* is Slice 2.

**`inside` is NOT touched** — it consumes `DS_PERCEIVED_GRID` (whole-grid ray context for nested
containment), not two operands. No `operand_arity`. It stays grid-level.

---

## Step 2 — [Cowork] register the 6 group DataStates (C4)

Add **new** DataStates with `group=True` + `member_ds` = the existing singular IRI. The existing
singular DataStates are **unchanged** (they become the members). `member_ds` existence is not validated
(ADR-0199), so order is free. (Extend the local `ds(...)` helper with a group-aware variant, or build
these `DataState(..., group=True, member_ds=<iri>)` directly.)

| group DataState | member_ds |
|---|---|
| `arc.objects` | `arc.object` |
| `arc.points` | `arc.point` |
| `arc.shapes` | `arc.shape` |
| `arc.pairs` | `arc.pair` |
| `arc.raw_grids` | `arc.raw_grid` |
| `arc.grids` | `arc.grid` |

**Not rewired this slice:** `extract_*` still output the singular bundle (today's behavior). Emitting
the *group* type is execution → Slice 2. This slice only *adds* the group types.

---

## Step 3 — [Cowork] gate

Root `./run_spike` → **14 `[ok]`** (discovery + conformance + D3 biting + `./evaluate` + #8 solves +
write). Specifically verify:
- `register_capacity` accepts every `operand_arity` (no `unexpected key` raise).
- `register_datastate` accepts the 6 groups (`group` requires `member_ds`; `group=False` forbids it).
- the `touching_delta` **fold escape** still passes the D3 biting check (Part-6 skips fold).
- #8 `stage6.matches_withheld` stays **True** (inline unchanged).

## Step 4 — [Mac] commit → [Linux] confirm gate

Commit the `arc_capacities.py` + `STATE.json` changes (never `git add -A`; `arc_debug_data.js` stays
gitignored). Linux confirms `./run_spike` = 14 `[ok]`. Tag/record per the pair-execution norm.

---

## Rollback
Revert `arc_capacities.py` + `STATE.core_version`; the merge stays (or `git revert` the merge if the
core itself misbehaves). Additive-only, so rollback is clean.

## Exit → Slice 2
Topology is honest (comparators carry arity; group types exist). Slice 2 makes `comparison_matrix`
**executable** (L4 invokes comparators via `cl.invoke`, exhaustive in×out) + the **measured perf
go/no-go** — the decision point for the rest of the build.
