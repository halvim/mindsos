# Capacity Creation Guide — arc1 spike

The checklist to follow whenever a new capacity is added to the arc1 spike. Every
capacity must be wired through **all five** surfaces below or the debug UI / gate
model fall out of sync. Running example: the `inside` intra-grid predicate.

Files live in `arc_solver/spike/`. Single-source-of-truth rule: the UI
**draws** what Python computes — never re-derive a capacity's result in JS.

---

## 1. Implement code for the capacity

**a. Real compute** → `arc_grids.py`
Add the pure function(s) that actually compute the result (the body, off-graph),
mirroring `touching` / `moved` / `same_object`. Keep it a pure helper.

```python
# arc_grids.py
def inside_pairs(objects, points, dims, bg): ...   # the per-grid fold
```

**b. Register the capacity** → `arc_capacities.py`
- Add the DataState IRI: `DS_INSIDE = datastate_iri("arc.inside")` and a row in
  `arc_datastates()`.
- Add the `Capacity(...)` to the right group function: `_perceive_capacities` /
  `_profile_comparators` / `_induce_capacities` / `_intra_grid_capacities` /
  `_reason_capacities`. (`inside` → `_intra_grid_capacities`, `CATEGORY_PREDICATE`,
  like `touching`.)
- It is then auto-registered by `install_arc()` and listed by `ordered_catalog()`.

**c. Materialize for the UI** → `arc_profile.py`
- If it is a per-grid property, compute it in `grid_summary()` (e.g. add an
  `"inside"` key next to `"touching"` via `arc_grids.inside_pairs(...)`).
- If it is an inter-grid induce facet, add it to `INDUCE_CAPS` + `_present()` +
  `match_pair()` and the `hypotheses()` fold.

> Discipline: capacity **bodies stay inline / stub-registered** (D3 locked). The
> registered Capacity is topology + provenance; the real compute is the arc_grids
> helper consumed by the profile fold — not `find_pipeline`.

---

## 2. Run the spike including the new capacity

```
cd projects/arc_solver && ./run_spike
```

This re-registers the CapacityLayer and regenerates `arc_debug_data.js`.
**Gate must stay green:**
- `find_pipeline` discovery line + GF-6 conformance line + D3-spike line all print `[ok]`.
- `#8` still solves (`stage6.matches_withheld == True`).
- the new capacity appears in `DATA.capacities` (from `ordered_catalog()`).

---

## 3. Add the capacity accordion on the **Main** section of arc_debug

→ `arc_debug.html` (Main section: `renderMain` → `renderPairCard` → `renderMatch`).
Per-grid / intra-grid capacities render as an accordion in the pair card — copy the
`touchingAccordion` pattern and feed it the new `grid_summary` key (e.g. `gs.inside`).
Inter-grid facets render as a `renderMatch` tier instead.

---

## 4. Create the gate for it and represent it in the **Gate** section

→ `arc_gates.py` (the gate source of truth):
- Add any **new comparisons** the capacity needs to `COMPARISONS`
  (e.g. for `inside`: `object_count {none|single|multiple}`, `background {detected|none}`),
  with a clause in `eval_comparisons()`.
- Add the capacity to `CAPACITIES` with its **guard** (AND/OR over comparison:result):
  ```python
  {"key": "inside", "guard": {"op": "and", "args": [
      {"op": "is", "cmp": "background",    "result": "detected"},
      {"op": "is", "cmp": "colour_count",  "result": "multicolor"},
      {"op": "is", "cmp": "object_count",  "result": "multiple"}]}},
  ```
The Gate section (`renderGates` ← `DATA.gates` + per-task `gates.holds`/`enabled`)
picks it up automatically. Re-run the spike. Optionally refresh the callout map:
`python3 maps/gates_map.py`.

---

## 5. Add the capacity in the **Search** section of arc_debug

→ `arc_search.py`:
- Add a `FACETS` entry (`kind` = `bool` or `multi`, `phase`, `division`, `group`,
  and `requires` if it depends on another facet).
- Add the matching clause in `task_tokens()` so each task emits the token.
`build_availability()` + the Search panel repopulate on the next `run_spike`.

---

## 6. Mark it as a hypothesis when it persists across all pairs

Check whether the new capacity **fires in every demo pair** of a task. If it
does, it is a persistent hypothesis for that task → it must appear in the
**hypotheses card** (Main section).

→ `arc_profile.py`:
- Add the capacity name to `INDUCE_CAPS`.
- Add a clause in `_present(pr, cap)` returning whether it fired for one pair —
  intra-grid caps read `pr["input"].get(<key>)` / `pr["output"]`; inter-grid caps
  read off `pr["match"]`.

`hypotheses()` then includes it (fired in pair 1 **and** in all pairs), and
`buildExp` renders it in the `<b>hypotheses</b>` line of the Main card. (No JS
change — the hypotheses card is data-driven from `t.hypotheses.list`.)

---

## Definition of done

A new capacity is complete only when all six are true:

1. ☐ `arc_grids` compute + `arc_capacities` registration + `arc_profile` materialization.
2. ☐ `./run_spike` green — conformance + D3 + `#8` solve all pass; capacity in `DATA.capacities`.
3. ☐ Main-section accordion / tier renders its result.
4. ☐ Gate authored in `arc_gates.py` and shown in the Gate section (+ map if regenerated).
5. ☐ Facet in `arc_search.py`, filterable in the Search section.
6. ☐ Added to `INDUCE_CAPS` + `_present()` so it shows as a hypothesis when it persists across all pairs.
