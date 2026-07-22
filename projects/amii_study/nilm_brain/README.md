# nilm_brain — the NILM leaf-learning brain (amii study)

A cycle-recognition brain built as a **consumer of MindsOS**: it registers the
full NILM application-doc registry into a pinned core and recognizes grid
cycles by dispatching L3 capacities the **finder composes** and core's
**`execute_pipeline`** runs. It never edits `mindsos_*` (the bongard/arc rule).

> **Current state, decisions, and next phase:** see **`STATE.md`**.
> Design refs: `docs/LEAF_LEARNING_NILM_APPLICATION.md` (the registry) and
> `docs/LEAF_LEARNING_PROCESS.md` (the domain-neutral doctrine).

## What's in it (the whole doc registry)

- **~44 DataStates** (`nilm.*` realm, doc §7 + 4 promoted search/loop
  hyperparameters so nothing is a literal in a body).
- **23 L3 capacities** — perception (`parse_raw`); derivation ×17; scoring
  (`calibrate`, the one learned); predicate (`compare`, `compare_structures`);
  comprehension (`bind_declaration`); decision (`verdict`).
- **The `cycle` recognition pipeline** (doc §6.1), composed by
  `ConjunctionFinder` and executed by `execute_pipeline`.

## Layout

```
nilm_brain/
  ontology.py       all DataStates (nilm.* realm) + register_ontology
  references.py     L2 references: cycle_reference + known_references (§8)
  perception.py     parse_raw (the §2 interpretation boundary)
  derivation.py     the 17 derivation caps — bodies own their numpy
  scoring.py        calibrate + Params fit off a clean-cycle seed
  decision.py       verdict -> cycle_verdict {state, axis, ...}
  comprehension.py  bind_declaration + compare + compare_structures (acquisition)
  pipelines.py      compose the recognition segment via the finder
  dispatch.py       thin dispatcher over cl.invoke (execute_pipeline seam)
  control.py        Solver: register + calibrate(seed) + recognize()
  harness.py        DuckSession (in-memory Local, no Falkor)
  scripts/cycle_demo.py   run it yourself over a PLAID record
  tests/test_gate.py      the F1/F2/F3 + C7 acceptance gate
```

## The consumer helpers (every non-capacity function)

`nilm_brain` is a **consumer**: the only mindsos code is what it imports
(`Capacity`, `CapacityLayer`, `execute_pipeline`, the category constants).
Everything below is therefore *ours* — and by the doctrine that is correct:
L4 iteration/control, wiring, L2-value production, and the `execute_pipeline`
seam are Python, **not** capacities (arc A4/C4). Each is listed so none is
hidden. Audit rule: **legit iff it is control-flow / wiring / an L2 value / the
dispatch seam and hides no decision threshold or reference that should be a
DataState-or-L2 input.**

| function / class (file) | role | kind |
|---|---|---|
| `build_given` (control) | caller-supplied given constants + promoted hyperparameters | L4 config |
| `Solver.__init__` (control) | registers ontology + families, composes the segment | wiring |
| `Solver._invoke` (control) | invoke wrapper that checks `success` (C7) | L4 |
| `Solver._refine_window` (control) | the period-refinement loop (A4/C4) | L4 iteration |
| `Solver._window_starts` (control) | window fan-out positions | L4 iteration |
| `Solver._segment_inputs` / `_run_segment` (control) | assemble + execute the segment | L4 plumbing |
| `Solver._voltage_signal` (control) | parse+bind pre-processing | L4 |
| `Solver.fit_calibrate` (control) | seed-fit of `calibrate_params` + `structuredness_thresholds` | L2 learning |
| `Solver.recognize` (control) | per-window recognition loop | L4 control |
| `build_solver` (control) | convenience constructor | wiring |
| `default_params` / `fit_calibrate_params` (scoring) | L2 calibrate params: default + seed-fit | L2 value |
| `default_thresholds` / `fit_thresholds` (decision) | L2 structuredness gates: default + seed-fit | L2 value |
| `cycle_reference` / `known_references` (references) | L2 reference library values | L2 value |
| `recognition_segment_starts` / `compose_recognition_segment` (pipelines) | declare entry inputs; finder composition | L4 |
| `DuckSession` (harness) | in-memory Local (no Falkor); v0 substrate — #4 swaps in `FalkorDBLocalPersister` | substrate |
| `CLDispatcher` (dispatch) | thin dispatcher over `cl.invoke` (the `execute_pipeline` seam) | seam |

**No entry hides L3 knowledge.** The one historical violation was
`structuredness_thresholds` living in `build_given` (a decision gate posing as a
domain constant) — fixed in open item #1a. **Remaining watch item:**
`required_confidence` still sits in `build_given` (`0.9`), but §7 classifies it
as an *L5 task input*, not a domain constant — same species, to be re-homed next.

## Run it

```
# gate (synthetic; no PLAID needed)
PYTHONPATH=.:projects/amii_study python -m pytest projects/amii_study/nilm_brain/tests -q

# demo over a real PLAID record
PYTHONPATH=.:projects/amii_study \
  python projects/amii_study/nilm_brain/scripts/cycle_demo.py \
  --data datasets/PLAID_2018/_sample --record Water_kettle
```

Needs `mindsos_capacity` + `mindsos_intelligence` importable and `numpy`.
In-memory only — no `boot_brain`/Falkor for v0.

## The design discipline (why this isn't a "44 caps, 3 live" brain)

The arc audits (`arc1-brain/docs/BRAIN_MINDSOS_CONFLICTS.md`) name the traps;
this brain is built against them:

- **Bodies own their logic** — no inline oracle they echo (D4). There is no
  `probe.py` import; the numpy lives in the capacity bodies.
- **Composition is the finder's job** — the recognition segment is composed by
  `ConjunctionFinder` (sound on multi-input; BFS is not — A7) and run by core's
  `execute_pipeline`, never a hand-rolled walker (A6/D8).
- **Iteration is L4's job** — parse/bind, the window fan-out, and the
  repeat-until-converged refinement loop are Python control flow (A4/C4). So
  `find(raw_data -> cycle_verdict)` is *correctly* NOT FOUND end-to-end; the
  finder composes the per-window **segment**, L4 loops around it.
- **No buried L3 knowledge** — thresholds, references, required_confidence are
  DataState/L2 inputs, never a python if-chain (D2), which is also the "no
  hardcoded values" rule.
- **Every invoke checks `success`** (the ADR-0072 envelope never raises — C7).
- **Learned state is L2** — `calibrate` is a `Params` fit off a clean-cycle
  seed; a healthy cycle scores high, a disturbance low (this is what resolves
  the single-pass "everything is request_reference" collapse). Durable L2
  persistence of the params + taught references is v1.

## The acceptance gate (`tests/test_gate.py`)

- **F1** — the finder composes `cycle_model + voltage_window -> cycle_verdict`.
- **F2** — that pipeline executes to **real values** (no `None` fictions), and
  a seeded clean cycle is recognized as `cycle` (not universally
  `request_reference`).
- **C7** — a bad invoke returns `success=False`, not a raise.

## Honest scope (v0)

- In-memory, shipped level. **Rung 5** (mindsos's own orchestrator driving the
  brain) is out of reach until core ships the WSD/phase-1 placeholders — same
  blocker as arc1 and arc3. Not faked here.
- `power` / `harmonic_amplitudes` capacities are registered but not wired:
  `power` needs a current-signal bind (a second `bind` output, v1).
- `onset` / `harmonics_present` / `load_type` / `appliance` rungs: their §4A
  template is the same as `cycle`, but they have **no L2 references yet** (§8),
  so they are not composed. Adding each reference **is** the leaf-learning.
