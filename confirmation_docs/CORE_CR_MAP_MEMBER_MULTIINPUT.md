# CORE CR — multi-input map members / leaves

**Status:** BUILT on `feat/mapfold-multi-input` (off `origin/main` `644e91c`). **Not merged, not gated on Linux.**
**Owner sign-off:** given 2026-07-30 (core edit to `mindsos_intelligence/execution.py`).
**Origin:** nilm-side `CR_MAP_MEMBER_MULTIINPUT.md`; bridge = `confirmation_docs/COLLECTION_MAP_FANOUT_COORDINATION.md` §11–§13.

---

## 1. Problem

Through Slice 3b the map executor composed a member's (and a plain leaf's)
pipeline with `find_pipeline` — the `BFSFinder` back-compat entry — which fires
each capacity off one `via` datastate and leaves its other declared inputs
unwired. And a member sub-run was seeded with only the member value
(`_run_member_pipeline`: `seed = {start_ds: seed_value}`; sub-plan path:
`sub_blackboard = {member_ds: member_value}`), so a member capacity's non-member
inputs had no source inside the member run.

Consequence: a member whose work is a genuinely multi-input composed segment
could not run inside a map. arc never hit this — its per-item capacity is
single-input. Verified against `origin/main` `644e91c`; see coordination §11.1,
including the correction that a missing declared input is **silently dropped**
from the dispatch (the body fails on the missing kwarg), not raised.

Both `ConjunctionFinder` (the sound multi-input finder) and multi-input
composition already ship and already run — nilm composes and executes its
per-window signature segment that way today. This CR only lifts the map
executor to the same footing.

---

## 2. Decisions (D1–D7)

| # | Decision | Rationale |
|---|---|---|
| **D1** | **Finder by arity.** >1 start ⇒ `ConjunctionFinder`; exactly 1 ⇒ `BFSFinder`. Optional explicit `"finder"` key overrides. `"bfs"` + plural starts raises. | The two finders disagree whenever >1 capacity can produce the same DataState (BFS = shortest-forward-from-start; Conjunction = first-producer-by-IRI-backward). Plural starts is a spec shape **no consumer emits today**, so arc cannot regress by construction. Fail loud rather than silently under-wire. |
| **D2** | **`shared_inputs` seeding**, not stored-reference sourcing. | Seeding needs nothing new. The stored variant (`learned-pipelines`, ADR-0203) is real but its only reader lives in `mindsos_server`, and `mindsos_intelligence` imports `mindsos_server` nowhere — verified. Clean follow-on, not this CR. |
| **D3** | Map member axis = **window start positions**, not windows (consumer-side). | `power_features` declares `(current_window, voltage_window)` — both per-window, so no member value can carry both and `shared_inputs` cannot supply the second. Positions as members + full signals as shared inputs works with no new core concept. |
| **D4** | Scope = **members and plain leaves**. `leaf_targets` gains optional plural `start_datastates`. | The stage producing the collection is itself multi-input; a member-only fix leaves it undeclarable. |
| **D5** | Hand-built `PlanResult` + direct `execution.run` for now. | `orchestrator.py:321` builds `solve_seed` as exactly one key, so `shared_inputs` constants are unreachable on the production path. Widening the seed picks where dataset constants live — a decision that overlaps the unbuilt dataset-role CR and Phase-1's contract, with no consumer needing it yet. **Deliberately held** (owner, 2026-07-30). |
| **D6** | Compose on the **first member**, reuse for the rest. | Composition ran per member per retry; `ConjunctionFinder`'s reachability pass has no memoisation and no depth bound. Must stay **lazy** — composing eagerly would turn an empty collection from "completes with `[]`" into a `PipelineNotFoundError`. |
| **D7** | Missing `shared_inputs` key ⇒ **hard `ValueError`** naming key + map, validated before the fan-out. | Skipping resurfaces much later as an opaque "required input unproducible" from the finder. Validating pre-fan-out means an empty collection cannot mask a mis-authored spec. |

---

## 3. Spec delta (additive; absent ⇒ byte-identical)

```
map spec:
  shared_inputs: [DataState IRI, ...]     # optional
  finder: "bfs" | "conjunction"           # optional; default = by arity (D1)

leaf_targets[ref]:
  start_datastates: [DataState IRI, ...]  # optional; alternative to start_datastate
  finder: "bfs" | "conjunction"           # optional
```

Declaring both `start_datastate` and `start_datastates` raises. Shared inputs are
merged **under** the member value, so a spec that also lists `member_ds` as
shared cannot shadow the member being iterated. Shared inputs seed the sub-plan
member path too; there is no implicit inheritance past the member sub-blackboard
— a nested map re-declares what it needs.

---

## 4. What changed

`mindsos_intelligence/execution.py`

* New helpers: `_endpoint_starts`, `_select_finder`, `_compose_pipeline`,
  `_resolve_shared_inputs`; constants `FINDER_BFS` / `FINDER_CONJUNCTION`
  (exported).
* `_run_leaf_pipeline` — reads plural-or-singular starts, selects the finder,
  composes through `_compose_pipeline`. Local→Global view fallback preserved.
* `_run_map_milestone` — snapshots `shared_inputs` once before the fan-out;
  owns the one-slot `compose_cache`; threads both into every member (full
  fan-out and the Slice-3b targeted single-member re-run share the path).
* `_run_one_member` — merges shared inputs into the sub-plan sub-blackboard.
* `_run_member_pipeline` — composes with the arity-selected finder over
  `(member_ds, *shared)`, memoised via `compose_cache`; seeds the member value
  plus shared inputs, filtered to the pipeline's `start_datastates`.
* `find_pipeline` is no longer imported here (zero call sites remain).

`mindsos_intelligence/plan_construction.py` — `PlanResult` field docs for the two
new spec keys; `leaf_targets` type widened to `Dict[str, Dict[str, Any]]`.

`tests/phase_48/test_map_member_multiinput.py` — new, 14 tests.

**Untouched:** `reduction_v0`, the learned-parameters snapshot, ∀-abort /
`MEMBER_RETRY_CAP` semantics, the orchestrator, the WSD planner.

---

## 5. Gate evidence (sandbox — Linux gate still owed)

Partial-tree run on python3.12 (`mindsos_core` / `capacity` / `knowledge` /
`instances` / `intelligence` + `tests/phase_48`; no FalkorDB):

| Tree | Result |
|---|---|
| `origin/main` `execution.py` + `plan_construction.py`, new test removed | **34 passed** |
| This branch | **48 passed** (34 + 14 new) |
| New file alone | **14 passed** |

No pre-existing test changed status. Prior to that, a 12-case standalone
sim-validation ran the modified executor against the **real** `ConjunctionFinder`
/ `BFSFinder` / `execute_pipeline` with a hand-built registry — 12/12.

**Still owed:** full gate on the Linux clone against the *merged* state (rebase
onto current `main`, re-gate; merged-state baseline was 4408).

---

## 6. Consumer-side prerequisites (nilm, not core)

1. Split `ds:signal` into per-channel DataStates + channel-specific window
   capacities. `window` is `(SIGNAL, FREQ_ESTIMATE, WINDOW_CYCLES, FS,
   WINDOW_START) → SIGNAL_WINDOW` and is invoked twice under the same IRI with
   the outputs renamed in Python; the blackboard holds one value per IRI and
   `ConjunctionFinder.fire` memoises per capacity IRI. **No core change fixes
   this — it blocks the end-to-end demo.**
2. A `window_starts` producer capacity, declared as a plural-start leaf (D4).
3. The `{score, label}` packaging terminal for the inner library map
   (coordination §8 / A-V2).
4. The nested `PlanResult` + direct `execution.run` harness (D5).

Accepted by the nilm chat, coordination §12.

---

## 7. Deferred

* **Multi-key `solve_seed`** (D5) — makes `shared_inputs` reachable from the
  orchestrator. Held deliberately: it decides where dataset constants live, and
  that overlaps the dataset-role CR. Revisit when a consumer needs the
  orchestrator path.
* **Pipeline-reference members** (D2) — once a `learned-pipelines` reader exists
  below the server layer.
* **Nested targeted re-execution** — unchanged; Slice 3b still falls back to a
  whole-pipeline replan for nested members.
