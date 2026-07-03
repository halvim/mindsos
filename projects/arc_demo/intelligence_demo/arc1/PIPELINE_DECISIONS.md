# ARC-1 — Pipeline Decision Register

**Status:** recovered 2026-06-21 · the prior copy existed in no git ref (orphaned by the
2026-06-20 reorg) and is rebuilt here from the reason-stage view in `SOLVE_PIPELINE.md`
(pipeline half) + the open-decision register carried in the chat handoff (§4).
**Purpose:** the single place that tracks (a) the reason-stage pipeline we are grounding and
(b) the open `D`-decisions against it, with status, recommendation, and dependency order.
**Companions:** `SOLVE_PIPELINE.md` (full decomposition + status tags), `ONTOLOGY.md` (§4
locked world-model), `REASON_STAGE_HYPOTHESES.md` (H1/H2), `PIPELINE.md` (pre-2026-06-18
reason convention), `VOCAB_CONSOLIDATION.md`.

**Legend** — build status: ✅ built · ◐ partial / #8-only · ○ unbuilt · ⛔ parked/blocked ·
⚑ machine-can't-decide (option-A flag). Grounding: ▲ inline/off-graph · ○ not started.

---

## 0. Binding context (do not re-open)

- **Boundary invariant.** L4 = loop / control / topo-sort only. Every *decision* (next-step,
  goal, selector, conflict, min-path cost + selection, tie-break) is **L3**. `find_pipeline`
  composes by `PRODUCES`/`CONSUMES`; no higher-order dispatcher; **no capacity invokes another
  *capacity via the layer*** — shared *pure helpers* are allowed (GF-2; e.g. `moved` shares a
  private normalize/compare helper, not the `same_shape` capacity).
- **World-model locked** at `ONTOLOGY.md` §4 — relevant rows for the reason stage:
  **#16** touching (positional predicate, parameter-free), **#17** attribute = 4th role
  family (provenance vs attachment axes), **#18** Region = concrete root + located/normalized
  two-axis model, **#19** vocabulary alias reconciliation. These are settled; decisions below
  build *on* them, not against them.
- **Grounding state.** The **#8 specimen** (background ensemble + correspondence +
  `touching_delta` + selector) is now **topology-registered** in `spike/arc_capacities.py`
  (`_reason_capacities`, stub bodies, real compute still inline in `arc_solver`) and gated on
  Linux (#8 still solves). The **rest** of 3A–3I remains ▲ inline / off-graph. **Caveat (D3
  spike 2026-06-21):** the registered topology and the executable `arc_solver` are **disjoint** —
  the solver never invokes the layer — so "grounded" currently means *transcribed*, not
  *executed* (§4 D3-spike entry). `touching_delta` is the one cap with a real, layer-invoked body.
- **Profile phase is a FILTER, but NOT via `find_pipeline` path-availability** (D7 LOCKED
  2026-06-21). Comparators always produce their Delta DataState (value `None` when no change),
  so the type is never topologically absent — `find_pipeline` (type-static, value-blind) can't
  prune per-task. The filter is an **instance-level L3 predicate** over swept Delta values.
  **Background detection (H1) is v1-resolved** (D4 LOCKED — frequency-only, degenerate reconcile;
  the 3D selector, `touching_delta`, and 3A bg-exclusion consume it). The real reconcile **policy**
  + detector roster are the remaining open part, gated on **CORPUS-ANALYSIS** — not a standing
  bottleneck on the #8 path.
- **`find_pipeline` is NOT the reason-layer composer** (D-A LOCKED 2026-06-21). The live probe
  proved BFS composes EVERY multi-input reason cap *unsoundly* (fires on one input, drops the
  rest; folds taken as singletons — see §4). Reason-layer edges are **provenance** the grounding
  walk audits; a conjunction/fold finder (filed core proposal §5) is the eventual composer. BFS
  stays the sound finder for the linear perceive/transform chains only.
- **Invoke boundary — D3 LOCKED inline (demo).** Bodies compute **inline**, not via
  `capacity_layer.invoke`. Conjunction is enforced by NO layer (verified §4): `find_pipeline`
  disjunctive, L4 dispatch passes caller-assembled maps, `call_capacity` validates outputs only,
  bodies `**kw`+`.get()` → missing input silently `None`. Invoke wiring is core-future.

---

## 1. Pipeline — reason-stage view (condensed from `SOLVE_PIPELINE.md` Phase 3)

| Stage | What | Status | Governing decision(s) |
|---|---|---|---|
| **3A Correspondence** | bg proposal → build `C` (input ref → output ref), unambiguous subset; completeness check | ◐ ⚑ | D4 (bg), D5, **D6** |
| **3B Induce** | transition detectors (`moved`…) + intra-grid state predicates (`touching`…) + state-change (`touching_changes`) | ✅/◐/○ | D9, D14 |
| **3C Hypothesis** | enumerate states+transitions; persistence filter (∀demo); combination test; ternary schema | ◐ | D10, D11 |
| **3D Selector/target** | role id (mover/target); minimal discriminative selector (unique src+target else abstain); moving-target DAG | ◐ ⚑ | **D4**, D10, D12 |
| **3E Rule assembly** | bind schema→selectors + transition policy + write-conflict policy | ◐ | **D10** |
| **3F Search/selection** | enumerate rule sets; MDL ordering; tie-break; budget; seed-op freeze | ⛔ | **D11** |
| **3G Apply** | resolve roles; next-step proposer (L3); transition generator; greedy apply; serializer | ◐ | D10, D11 |
| **3H Verify** | apply to demos; exact-match; all-match→sufficient; Consistency ≠ Generalization (P5) | ✅ ⚑ | D11 |
| **3I Query / Abstain** | unique src+target on query → apply; structural abstain | ◐ | D6, D11 |

First grounding specimen (D18): **`touching_delta` + selector** — the #8 spine, smallest
end-to-end slice that exercises induce → state-change → selector.

---

## 2. Open decision register

All open; none locked. ★ = bottleneck. `rec` = recommendation carried from the handoff.

### Process
| D | Question | Status / rec |
|---|---|---|
| **D0** | Design↔build pivot | **LOCKED 2026-06-21 — pivot to build**: register the #8 specimen as topology-registered swept capacities (reason DataStates + `detect_background_frequency`/`reconcile_background`/`build_correspondence`/`touching_delta`/`selector`), stub bodies, real compute stays inline in `arc_solver`. Validate against the real `CapacityLayer`; #8 must still solve. |
| **D1** | Reasoning-graph grounding semantics | **LOCKED 2026-06-21 — topology-registered**: register reason DataStates + capacities with real `PRODUCES`/`CONSUMES` edges (the perceive-chain pattern), stub/inline bodies, `find_pipeline` walks them. Provenance walks real producers (no doc/code drift); defers live bodies (D3). Rejected pure model-grounding (two drifting representations). |
| **D2** | Approve + scope the reasoning-graph | **LOCKED 2026-06-21 — first specimen only**: `touching_delta` (state-change) + selector, the #8 spine (D18). Defers correspondence/search; grounding it surfaces D4 next. |
| **D3** | Invoke boundary: inline body-fold vs `capacity_layer.invoke` | **LOCKED 2026-06-21 — inline (demo)**: conjunction enforced by NO layer (verified §4); invoke is meaningful only once a conjunction finder exists → core-future. Bodies stay inline; #8 gated. |

### Reason-stage grounding
| D | Question | Status / rec |
|---|---|---|
| **D4 ★** | Background detection (frequency vs residual vs ensemble) | **LOCKED 2026-06-21 — ensemble topology, frequency-only body**: `detect_background_frequency` (real body) → `BackgroundCandidate`; `reconcile_background` = **L4 fold** over candidates → `Background`, **degenerate now** (single candidate passes through; policy-pending). Additional detectors (residual/…) + real reconcile policy deferred to **CORPUS-ANALYSIS** (below). Residual NOT built now — known-wrong on #8, family unidentified. |
| **D5** | `detect_background` registration form | **LOCKED 2026-06-21 — swept, not (BFS-)composed**: background detection is an L4-style **sweep** over detector outputs → reconcile fold → `Background`, **not** a `find_pipeline`-pulled leg (verified: BFS returns one shortest path and fires on a *single* producer, so it does not **soundly** compose a fold — the fold caps stay **registered** with binary CONSUMES provenance and are **swept** now; a fold-finder is the core-future composer per §5/GF-3). Not "find_pipeline-impossible"; ADR-0071. Corrects the prior "lazy find_pipeline-pulled" framing. |
| **CORPUS-ANALYSIS** | Background-detector bucketing over the 400 train tasks (which detector matches the human-evident bg; where frequency vs residual wins) | **SCHEDULED** — hard prerequisite for the real `reconcile_background` policy + the detector roster (D4). |
| **D6** | Correspondence (P3): register + resolve duplicates | **LOCKED 2026-06-21 — unambiguous-subset, defer resolution**: `build_correspondence` = swept fold over pairwise comparators → `Correspondence` DataState (not a `find_pipeline` leg, per D5). Assemble strictest-first 1:1 (`same_object` → `moved` → `same_point`); ambiguous pairs left uncorresponded; completeness check abstains if a needed object is uncorresponded. Duplicate-resolution **policy** routed to CORPUS-ANALYSIS. |
| **D7** | Adopt profile-as-`find_pipeline`-filter | **LOCKED 2026-06-21 — REJECT the find_pipeline framing; filter = instance-level L3 predicate**: `find_pipeline` is type-static + value-blind (verified `pipeline.py`); comparators always produce the Delta type (None-valued), so path-availability can't prune per-task. Realize the filter as an L3 eligibility predicate over swept Delta values, consumed by L4 to bound the target set. Build deferred to D13 (no consumer until a transform-family task). |
| **D8** | Close palette-as-set hole (recolor-by-permutation) | open — **reclassified vocabulary/transform** (not reason-stage); → travels with D12/D14 (I4 2026-06-21) |
| **D9** | Wire `touching_delta` now vs register the induce sub-graph together | **CLOSED 2026-06-21 — subsumed by D0/D1**: `touching_delta` + the full induce/intra-grid sub-graph are already registered + gated. Moot. |

### Grounding fidelity (reanalysis 2026-06-21, this chat) — all LOCKED demo-side

| D | Question | Status / decision |
|---|---|---|
| **D-A ★** | Reason-layer registration purpose: composition vs provenance | **LOCKED — provenance / finder-selection**: BFS does NOT (cannot soundly) compose the reason layer; registered reason edges are real composition substrate for a future conjunction/fold finder AND audited as provenance now. Retires §0's old "profile filter = find_pipeline path-availability". |
| **GF-1** | Source of truth among 3 reps (bodies / bipartite topology / `arc_metagraph` REQUIRES overlay) | **LOCKED — body-canonical**: executed bodies are truth; topology is derived-and-asserted (provenance); `arc_metagraph` demoted to a generated debug-only view, REQUIRES dropped as an ontology relation. |
| **GF-2** | §0 invariant "no capacity calls another" (`moved` calls `same_shape`+`normalize_shape`) | **LOCKED — relax**: "no capacity invokes another *capacity via the layer*; shared pure helpers allowed." `moved` shares a private normalize/compare helper, not the `same_shape` capacity. (`moved` flagged: a future finder may make it a real `SameShape` consumer.) |
| **GF-3** | Fold caps (`reconcile_background`, `build_correspondence`) modelling | **LOCKED — keep registered (binary CONSUMES = provenance), composed by the sweep now**; NOT pulled off-graph (revised once the finder-seam landed). Typed input-group hyperedge is the core-future model (§5). D5 wording corrected: folds are swept, not "find_pipeline-impossible". |
| **GF-4** | Background per-grid vs task-level (`_bg_color` pools demo inputs; ONTOLOGY #3 = per-grid, no Task-level) | **LOCKED — keep per-grid detect; relabel pooling as the degenerate reconcile policy**, v1-pending-CORPUS-ANALYSIS. Do NOT amend ONTOLOGY #3. |
| **GF-5** | Selector "else abstain" contract vs hardcoded shape tie-break | **LOCKED — reword "unique else FLAG (option A)"**; shape pick stays a recorded flag; real tie-break → D11. |
| **GF-6** | Drift enforcement | **LOCKED — add `run_spike` conformance assertion (xfail→hard)**: (a) BFS composes the linear chains soundly, (b) multi-input reason caps are NOT BFS-composable (drift made executable), (c) registered reason edges match the bodies' real *semantic* dependencies. |
| **GF-7** | Doc/name reconciliation | **LOCKED — batch the actively-false items now** (H2 pushback; ONTOLOGY §3 stale `detect_background` row; §3 "immediate next move"); defer alias renames (`extract_shapes`→`normalize_shape`, `touching_changes`→`touching_delta`) to D14. |
| **D1/D2** | (amendment) | **Rationale amended 2026-06-21**: registration stands, but the "find_pipeline walks the reason graph" clause is RETRACTED (false for all multi-input reason caps per the probe) → replaced by "finder-per-subgraph". |

### Generalization (beyond #8)
| D | Question | Status / rec |
|---|---|---|
| **D10** | De-hardcode 3E rule synthesis | open |
| **D11** | 3F search / MDL / budget / seed-op freeze | open (⛔ spine) |
| **D12** | Recogniser family (`Region → typed`) | open |
| **D13** | Which 2nd task — mechanism vs vocabulary axis? | open |

### Consolidation
| D | Question | Status / rec |
|---|---|---|
| **D14** | Reason-stage vocabulary pass (State / transition / state-change / selector / mover-target / correspondence / Delta) into ontology + lexicon + L3 | open |

### Artifacts
| D | Question | Status / rec |
|---|---|---|
| **D15** | Reasoning-graph file + format (`REASON_GRAPHS.md`? mermaid?) | open |
| **D16** | Fold the #8 walkthrough into `SOLVE_PIPELINE.md` | open |
| **D17** | Doc-set index / canonicality | open |
| **D18** | Use `touching_delta` + selector as the reasoning-graph's first specimen | open · rec yes |

---

## 3. Recommended order

Demo-side locks (D0–D6, D-A, GF-1…GF-7, D1/D2 amendment, D3, D7) are decided. Remaining open
work, in order:
~~`apply GF-1…GF-6 + D-A edits to the spike/docs`~~ **(APPLIED + gated 2026-06-21; GF-7 alias
renames deferred to D14)** → **`D3-spike` (one-specimen `touching_delta` real-body invoke —
IN PROGRESS 2026-06-21)** → `D13` (which 2nd task; un-double-booked — was listed twice) →
`D7-build` (only if the chosen task gives it a non-inline consumer) → `D10–D12` → `D14`
(incl. GF-7 alias renames + D8 vocabulary hole) → artifacts `D15–D17`.
D9 closed (subsumed). **CORPUS-ANALYSIS** gates D4-policy + a data-grounded D13.
**CORPUS-ANALYSIS** runs in parallel (gates the real `reconcile_background` policy + detector roster).

Core-side: the finder-seam + conjunction primitive is a **separate core-mod chat** (§5); ARC is
filed as motivating consumer; the demo does NOT block on it.

---

## 4. Log

- **2026-06-21** — file recovered post-reorg (was in no git ref); content rebuilt from the
  handoff register + `SOLVE_PIPELINE.md`. No decisions locked yet.
- **2026-06-21** — **D1 locked** (topology-registered grounding) + **D2 locked** (scope = first
  specimen `touching_delta` + selector). Next: D4 (background detection).
- **2026-06-21** — **D4 + D5 locked** (ensemble topology, frequency-only body, reconcile = L4 fold
  degenerate/policy-pending; background is swept not `find_pipeline`-composed) + **CORPUS-ANALYSIS**
  scheduled (gates reconcile policy + detector roster). Next: D0 (build pivot) or D6 (correspondence).
- **2026-06-21** — **D6 locked** (correspondence = swept fold → `Correspondence`; unambiguous-subset,
  resolution policy → CORPUS-ANALYSIS). Specimen inputs now designed (background + correspondence +
  touching_delta + selector). Next: D0 (build pivot).
- **2026-06-21** — **D0 locked + BUILT + gated.** `spike/arc_capacities.py` now registers 5 reason
  DataStates + 5 swept capacities (`_reason_capacities`); perceive discovery unchanged, #8 still
  solves, Linux-gated. Commit `8fa24d6`. Open next: **D7** (profile-as-filter — has a wrinkle, see
  row), D8–D18, and **CORPUS-ANALYSIS** (gates the real background reconcile policy + detector roster).
- **2026-06-21** — **Reanalysis pass (this chat): D7, D-A, GF-1…GF-7, D1/D2 amendment LOCKED; D3
  LOCKED inline; core-policy = file-and-continue.** Drivers: (1) `find_pipeline` (`pipeline.py`) is
  type-static + value-blind → D7's path-availability framing impossible. (2) **Live probe** (scratch
  `find_pipeline` over reason targets) returned a path for EVERY reason target but each is
  **structurally unsound** — BFS fires a cap when ANY one consumed DataState is reachable, never
  checking the rest: `grid→state_change` via `touching` alone (dropped `correspondence`),
  `grid→selector` via `object` alone (dropped `state_change`), `same_object→correspondence` via
  `same_object` alone (dropped `moved`/`same_point`), `grid→background` as a 1-fold singleton. (3)
  **Conjunction enforced by NO layer**: L4 `dispatch`/`plan_construction`/`execution` never call
  `find_pipeline`; `runtime.call_capacity` validates outputs only; bodies `**kw`+`.get()` → missing
  input silently `None`. (4) **Finder-seam** (owner observation): BFS should be ONE finder; the
  architecture already names alternatives (`pipeline.py` docstring promoted-path lookup; L2
  `promoted-pipelines`; L4's own v0 finder) but never abstracted them → reframes D-A to
  finder-selection and revises GF-3 (keep folds registered, don't pull off-graph). (5) Not every
  multi-input cap is a conjunction: `touching_delta`/`selector` = AND, `build_correspondence` =
  optional-union, `reconcile_background` = fold → the core model is a **typed input-group
  {all|any|fold}**, not a blanket "all members required" hyperedge. Core upgrade FILED as a separate
  core-mod chat (§5), ARC = first multi-input-dispatch consumer. All demo-side locks are doc +
  small-code only; #8 stays green.
- **2026-06-21** — **GF demo-side edits APPLIED + gated.** GF-1 `arc_metagraph` demoted to a
  generated debug-only sectional view (REQUIRES dropped as an ontology relation; `summary.requires`
  now empty; debug header relabeled). GF-6 `run_spike._conformance_check` added as a **hard**
  assertion: (a) perceive chains are soundly BFS-composed, (b) the multi-input reason caps
  (`state_change`/`selector`/`correspondence`) are **found-but-unsound** under BFS (drift now
  executable), (c) registered reason CONSUMES/PRODUCES == declared inputs/outputs. GF-2 factored
  `arc_grids._same_normalized_shape` (private pure helper) so `moved` no longer references the
  `same_shape` *comparator*; §0 invariant reworded. GF-4 `_bg_color` relabeled the degenerate
  reconcile-background policy. GF-5 selector contract reworded "unique else FLAG (option A)". GF-3
  D5 wording corrected (folds swept, not "find_pipeline-impossible"). Re-ran the full 400-task
  spike: discovery chains match, conformance passes, **#8 `stage6.matches_withheld` stays True**.
  GF-7 alias renames deferred to D14. Next: **D7-build** (with D13).
- **2026-06-21** — **Reanalysis pass 2 + D3 ONE-SPECIMEN SPIKE.** Pass-2 headline finding:
  `arc_solver` imports **only** `arc_grids` and takes `(profile, raw_task)` — it never touches the
  `CapacityLayer`/`find_pipeline`. So the registered reason topology and the executable solver are
  **disjoint artifacts**; "grounded + solves" conflated two things that never meet. GF-1
  "body-canonical" was vacuous for reason caps (their bodies were stubs) and GF-6(c) only checks
  declared==registered (can't see the body). Acted: gave `touching_delta` a **real body** invoked
  through `cl.invoke` for #8 + a **biting** check (`run_spike._invoke_biting_check`). Result: the
  cap executes through the layer and **matches** the inline solver; #8 stays green. **Findings
  (D3 evidence):** (1) `invoke` does **not** validate inputs against the registered CONSUMES — the
  declared topology is advisory; passing the declared `(touching, correspondence)` runs nothing,
  passing the *real* `(pair, background)` works → declared edges are **neither necessary nor
  sufficient**. (2) The real body consumes `(pair, background)`; **background isn't even a declared
  input**, and the body **recomputes** touching+correspondence — it is a **monolith over the pair**,
  so the reason-graph decomposition is **paper-only**. (3) The DataState model can't represent
  **two same-type operands** (in-touching vs out-touching collide on one DS key) — the **pair-axis
  is invisible** to the topology; this hits **every comparator** (`same_object` "consumes two
  Objects", etc.). (4) The solver has no `CapacityLayer` handle → having the solver *invoke* the cap
  needs `cl` threaded into `build_solver` (inverted-dependency / plumbing cost, deferred). **Verdict:**
  bridging inline→registered is **not just plumbing** — it needs (a) the monolith body decomposed
  into the registered atoms and (b) a DataState model carrying operand arity. Both are **CORE**
  concerns → folded into §5. Demo does not block; returns to its track (D13 / CORPUS-ANALYSIS).
- **2026-06-23 — DEMO-UI + CAPACITY + DATASET session (shipped, Linux-gated `68a0ab3`).** Built the
  arc_debug **Gates section** — a phased `comparison → result → gate(AND/OR) → capacity` graph
  backed by NEW `spike/arc_gates.py` (comparisons + per-task `holds`/`enabled` + capacity guards),
  reactive result-chip filter + matching-task list, + a Map callout (`maps/gates_map.py` →
  `gates_map.png`). Added the **`inside`** intra-grid capacity (`arc_grids`: flood-fill enclosure
  **pockets** + object-level **bbox containment**; bg-excluded) wired end-to-end via the new
  **`CAPACITY_CREATION_GUIDE.md`** (6 steps: grids/capacities/profile compute + spike + Main
  accordion + gate + search facet + hypothesis tag). Fixed a compact grid-sizing overflow (cellSize
  divides by `max(rows,cols)`). **Corrected 21 corrupted tasks in `arc1.json`** vs canonical
  fchollet/ARC-AGI (incl. #4 `025d127b`) — now exact-matches canonical, zero mismatches. Core
  recheck: §5 Part 6 SHIPPED, Part 5 deferred (see §5). Next-phase prompt drafted for the re-pin +
  finder-consumption decision. Gate green (4 `[ok]`: discovery + GF-6 + D3 + write 12708 KB; #8 solves).
- **2026-06-23 — REANALYSIS of the re-pin / finder-consumption plan (4 passes; this chat).**
  **Re-pin is NOT a clean no-op — it reds the gate (verified in core code, not hypothesised).**
  Core Part 6 `capacity._validate_inputs` (capacity.py:274; `input_group` defaults to
  `all_required`, capacity.py:92) now raises on the `invoke` path. The D3 biting check
  (`run_spike.py:120`) invokes `touching_delta` with `{DS_PAIR, DS_BACKGROUND}` while the cap
  declares `CONSUMES=(DS_TOUCHING, DS_CORRESPONDENCE)` → violates Part 6 **two ways**
  (`missing_required` on the two declared inputs + `unexpected_input` on pair/background) →
  `res.success` False → `assert` at run_spike.py:121 fails → **gate #3 red on re-pin.** The fiction
  the D3 spike deliberately exposed is exactly what Part 6 now enforces; re-pin forces choosing one
  of: (A) redeclare CONSUMES = (pair, background) — loses the semantic provenance edges; (B) revert
  the biting check to inline-only — loses the one layer-invoked specimen; (C) decompose the monolith
  body to consume the declared edges — the deferred Part-5/body-decomposition work; (D) don't re-pin.
  **Decisions (this reanalysis):** (1) **Re-pin — DEFER**, coupled to consumption per RULES §3
  ("bump deliberately, for a reason"); re-pin without a consumer = change without a consumer.
  Precondition still to verify Mac-side: is `composition-lifecycle-s2-confirmed` merged to `main`?
  (the `MindsOS/` main tree carries Parts 1–4+6 in the working dir but its STATE.json still reads
  phase50 — STATE is stale either way). (2) **Finder consumption — REJECT for ARC.** Solver and
  registered topology are DISJOINT (solver never touches the layer), so routing the reason layer
  through `ConjunctionFinder` is finder-level-only / cosmetic until Part 5 (operand-arity for the
  same-type in/out-touching pair) AND monolith-body decomposition also land — multi-phase core+demo
  work with zero task-solving payoff. ARC declines the Part-5 consumer role; **bongard m5 is §5's
  named candidate.** Do NOT hand off the Part-5 core-mod prompt from here. (3) **Reorder §3:** the
  real critical path is **CORPUS-ANALYSIS → D13**, not re-pin; D13 gates whether D7-build /
  finder-consumption ever get a non-inline consumer. Demo stays provenance-only / inline (D3 holds).
  Housekeeping: STATE.json arc.status is stale (predates the `composition-lifecycle-s2-confirmed`
  tag + Part 6 ship); gitignore the generated `arc_debug_data.js` (12.7 MB; dirties the tree each
  gate) before any merge work.
- **2026-06-25 — capacity-testing pipeline + implication skip (gate panel).** Built the transform
  family (generators `recolor`/`rotate`/`reflect` + comparators `recolored`/`rotated`/`reflected`)
  and a 4-phase gate panel (Profiling → Components → Gating → Comparison Capacity, inter/intra).
  **Pipeline rule added:** an *implied* capacity is **not re-tested when its parent tests positive**
  — `gate_report` records `implied` (child→parent) and takes the child known-true. Sound only for
  capacity-phase implications verified 0/400: **`inside ⟹ touching`** (275/400 tasks skip the
  touching test). `moved`/`recolored ⟹ same_shape` stay as gate `requires` (cross-phase).
  `same_object ⟹ same_shape` is **display-only** (Search indentation) — token-unsound for a skip
  (120/400 fire same_object without same_shape), so it never drives the skip. `enabled == Search
  token` holds for all 400 after the skip. Reference: `CAPACITY_ROADMAP.md` (icecuber = checklist).
- **2026-06-25 — profiler/comparator taxonomy + `./evaluate` (LOCKED + BUILT + gated).** Split the
  bool facets into two kinds. **PROFILERS** (universal task facts, NOT capacities): `compare_*`,
  `same_object`/`same_shape`/`same_point`, and two NEW shape invariants `same_cell_count` /
  `same_bbox_area` (both **D4-invariant** — a rotation/reflection preserves cell count and bbox
  area). `same_object/shape/point` recategorized from `comparator` → new `CATEGORY_PROFILER`
  (`arc_capacities`/`arc_metagraph`/docs). **COMPARATORS** (the 6 capacities): `moved`, `recolored`,
  `rotated`, `reflected`, `touching`, `inside` — bool facets outside the `atoms` group
  (`arc_search.is_comparator`/`comparator_names`). Implications: `same_shape ⟹ same_cell_count` and
  `same_shape ⟹ same_bbox_area` (independent, display-only); `rotated`/`reflected` **demand**
  `same_cell_count`+`same_bbox_area` (used as a cheap pre-filter in `rotated_pairs`/`reflected_pairs`
  before the shape check). **Demands = `requires`** (single source: a comparator's facet). **Removed
  constant profilers** (zero information across 400): `colour_count` (multicolor 400/400 — 0
  monochrome tasks; 65 monochrome single grids exist, e.g. `1190e5a7`), `object_presence` (400/400),
  `component_presence` (400/400); kept `point_presence` (absent 58/400) + `object_count` (single
  6/400). `touching`/`inside` are now demand-less (their old `object_presence` demand was vacuous).
  **`./evaluate <comparator> [task#|all]`** (`arc1/solve/evaluate.py`): lists demands + implication
  parents, applies a comparator via an independent code path, demand-gates, cross-checks vs the
  Search token, and writes `capacities.json` `{task:{cap:bool}}` + `capacities_discrepancies.json`.
  Gate adds two checks: `enabled == Search token` (all 6 × 400) and **0 `./evaluate` discrepancies**
  (6 × 400). Counts: moved 82, recolored 54, rotated 75, reflected 44, touching 400, inside 275.
- **2026-06-26 — `./arc` launcher + solve viewer UX (BUILT + gated; restructure UNCOMMITTED).**
  Tooling: root `./arc` dispatcher (`start` builds the spike + serves `arc_debug.html`; `solve`;
  `evaluate`) with `--help` per subcommand; `start`/`solve`/`evaluate` removed the per-folder scripts'
  cwd dependence. `./arc solve --phases` lists every phase + description (`pipeline.STEP_DESC`).
  **SHIPPED (pushed, Linux-gated): launcher + `--help` + cached-step full-output (each phase's
  `result` is stamped into its checkpoint via `_result_<n>` so cached phases render in full) +
  `→ future` line (each phase's proposed MindsOS feature+location, `pipeline.STEP_TARGETS`).**
  **UNCOMMITTED (built, Cowork-gated 400/green, NOT pushed) — the phase RESTRUCTURE:** (1) `solve`
  is now 10 phases — **Input+Perceive collapsed** (phase 1) and **Profile→{Profile (profilers),
  Comparators}** split (phases 2/3); (2) `arc_profile.grid_summary` is **pure perception** (no
  `touching`/`inside`) — those intra-grid comparator relations are attached by the new
  `arc_profile.attach_relations` inside `build_profile` and attributed to phase 3 (option A: physically
  in `build_profile`, displayed under phase 3 — a presentation slice; option B, computing them at
  token time, was rejected as it breaks `build_solver`'s direct stage calls); (3) the per-phase
  `engine` line was **dropped** — the real **function call chain** now renders on the `uses` line
  (STEPS 5th tuple field renamed `engine`→`functions`); (4) checkpoints gained a `_name_<n>` phase
  stamp — a layout change invalidates a stale checkpoint (auto-recompute, no manual `rm`).
  `STEPS.md` rewritten to the 10-phase layout. **OPEN — result-line wording:** the user wants to
  revise the per-phase `result` strings; built in `pipeline.step_*` (phases 1–7, 10) except phases 8/9
  whose prose (`policy`/`verdict`) lives in `arc_solver.stage_rule`/`stage_verify` (also consumed by
  the gate's `build_solver` — edit there + re-gate). No new wording was supplied yet. Gate is still
  6 `[ok]` lines / 400 green.
- **2026-06-26 — solve-viewer result rewrite (phases 1-2) + `same_object⟹same_shape` token wire +
  `--inferences` (BUILT + Linux-gated; `arc_debug_data.js` now untracked).** Prior phase RESTRUCTURE
  confirmed **already committed+pushed** (HEAD `2f0e71e` == `origin/demo/arc`; the "uncommitted"
  handoff note was stale). Shipped on `demo/arc`: (1) **Phase 1** result → per-pair perceive
  (`pipeline._perceive_line` + `_block`): header `N train pairs · M test`; per train pair In/Out
  `dims · pal[..] · N obj` + `N pt` **only when points >0**; multi-line. (2) **Phase 2** result →
  per-pair correspondence tiers (`step_profile`): top `dims=… · palette=…`; positives only, order
  **same_object → same_shape → same_point**; objects `O#.colour`, points `P#` (no colour); group
  brackets only when a side has >1; `same_shape` shown only for **non-identical** `shape_groups`;
  empty pairs omitted. (3) **Colour map** `arc_grids.COLOR_NAMES`/`color_name` (0 black,1 blue,2 red,
  3 green,4 yellow,5 grey,6 magenta,7 orange,8 cyan,9 brown). (4) **`same_object ⟹ same_shape` WIRED
  as a token skip — REVERSES the prior "display-only / token-unsound 120/400" framing** (the GF/D row
  + arc_search comment): `task_tokens` same_shape = `shape_groups OR equal` → **147→267/400**; sound
  0/400 (identical cells ⇒ identical `shape_key`); `skip` field added to the `same_object` facet. The
  TOKEN (267) **deliberately diverges** from the phase-2 DISPLAY (non-trivial reuse only) — **option
  A**, documented by `--inferences`. (5) **`./arc solve --inferences`** (static; `arc_search.inferences()`)
  groups edges wired / requires / display-only. (6) **Gate** gained `run_spike._inference_soundness_check`
  (same_object⟹same_shape 0/400) → now **7 `[ok]`**; #8 still solves. (7) **`arc_debug_data.js`
  untracked** (`git rm --cached` + gitignore) — resolves the Linux pull-dirty gotcha. **Checkpoint
  gotcha:** a result-STRING edit does NOT invalidate a checkpoint (only a phase-NAME change does) →
  `rm -rf runs/<task>` to see new wording; `runs/` is owned per-machine (Cowork can't `rm`
  Mac-written ones). **OPEN:** phases **3-10** result wording (unrevised — phases 8/9 prose lives in
  `arc_solver.stage_rule`/`stage_verify`, the rest in `pipeline.step_*`); `gates_map.py`/PNG regen
  for the 2 phase-2 chips (`same_cell_count`/`same_bbox_area`) still deferred.

- **2026-06-27 — solve-viewer phases 3–4 (Subdivision + Task pattern) + `inset` capacity
  (BUILT + Cowork-gated 8 `[ok]`/400; NOT yet committed).** Two new hypothesis/display
  phases inserted into `arc1/solve` (now **12 phases**), both reading the phase-2 profile and
  **non-load-bearing** (the #8 stages compute independently). **Phase 4 Task pattern**
  (`arc_solver.task_patterns` + `_addition_evidence`): first pattern **addition** = ∀demo
  `dims preserved ∧ palette ⊆ output ∧ all non-bg inputs same_object ∧ ≥1 new non-bg output
  object`. **Background-exclusion is mandatory** — the literal "all inputs preserved" fires
  **0/400** because the background is an extracted object that mutates on any addition; bg-excluded
  → **87/400**, #8 excluded (it's a move task). **Phase 3 Subdivision** (`arc_grids.subdivisions`
  built on **`inset`**): an input object B partitioned by **≥2 disjoint output insets** (objects +
  **points**) whose cell-union == B → `B → B.sub1, B.sub2, …`. ∀demo, points included = **103/400**
  (objects-only would be 44 but task-2 fails ∀ — pair-2's fill is a single-cell **point**); #8
  excluded. Display = finding (`{Out…}`) then indented consequence (`…sub1, sub2`). Over-fire
  (103) accepted (single-pixel recolors read as "object → remnant + point"). **`inset(a,b)` =
  `a.cells ⊆ b.cells`** (positional, literal, reflexive → `same_object ⟹ inset`); verified on task 2
  pair 1 = `Out1.O2.yellow inset In1.O0.black` (the added cells were input-background cells — NOT
  bbox/region containment, which is `inside`). Decisions: **inset = capacity-only** (registered in
  `arc_capacities` `_comparator_capacities`, `CATEGORY_PREDICATE`, DS_INSET; **no Search facet** —
  near-universal 350/400; **not** in `comparator_names`/`./evaluate`; 27→**28** caps);
  **subdivision = a phase process, not a comparator and not a capacity** (consumes `inset` inline
  per D3). Phase 3 is **background-agnostic** (treats all input objects as candidate B; the bg is
  in fact always the B for task 2). `inset_pairs` (an earlier bbox-era helper) **removed**;
  `subdivisions()` routes through `inset()` (single source). Gate stays green (8 `[ok]` incl. write;
  conformance/evaluate/#8-solve all pass; run_spike label `10-step`→`12-step`). **OPEN:** phases 5–12
  result wording unrevised; commit (Mac) + Linux-gate pending; STEPS.md updated to 12 phases.

- **2026-06-27 — `union` operator + `./evaluate` operator track + `union ⟹ inset`
  (BUILT + Cowork-gated 8 `[ok]`/400; NOT yet committed).** Adds the first
  **object operator** to the demo. Decisions locked this chat:
  - **`union` = an OPERATOR** (new `CATEGORY_OPERATOR`, the dual of
    `CATEGORY_DECOMPOSITION`), output **`DS_REGION`** (new DataState — an
    arbitrary cell-set; NOT an Object, since the union of two objects may be
    multi-colour/disconnected). Registered in `arc_capacities._operator_capacities`
    (`inputs=(DS_OBJECT,)` **arity fiction** as with `inset`/comparators —
    operand-position is the deferred §5 Part-5 core concern); stub body,
    L4-called-when-needed (provenance only, D3, like every ARC cap). **28→29 caps.**
  - **`union` compute = `arc_grids.union(a,b)`** (positional cell-union → Region).
    **Occurrence detector = `arc_grids.union_in_pair(in,out,bg)`**, built on
    `inset` (single source): a non-bg whole object = the disjoint union of ≥2
    non-bg parts (objects+points) at identical cells, checked **both directions**
    — `split` (whole=in, parts=out) and `assemble` (whole=out, parts=in).
    **Background-EXCLUDED** (locked: "disregard the background colour for this
    test"). Task-level helpers in `arc_solver` (`union_occurs`/`inset_occurs`/
    `union_detail`, bg via `_bg_color`).
  - **`inset` + `union` added to `./evaluate` as a show-only OPERATOR track**
    (`arc_search.operator_names()`): reports whether the operator **occurs** in
    the task (∃ demo, either direction) + its **demands** — **NO Search-token
    cross-check, NO discrepancy** (operators carry no token). The gate's
    6-comparator invariants (`enabled==token`, `0 discrepancies`) stay scoped to
    `comparator_names()` and are untouched. `union <task>` prints the partition
    detail in the decided subdivision format (`whole → {parts}`; `whole →
    whole.part1…`), `.partN` not `.subN` (for union the parts **compose** the
    whole). Reverses the 2026-06-27 "inset = not in `./evaluate`" line.
  - **`union ⟹ inset` inference** (`C=union(A,B) ⟹ inset(A,C)∧inset(B,C)` — sound
    by construction): a **wired skip** (`arc_search.OPERATOR_INFERENCES`) — when
    union occurs, `inset` is known-true and its check is skipped. New gate check
    `run_spike._operator_inference_check` (0/400) → **8 `[ok]`** lines + write
    (was 7); also surfaced in `./arc solve --inferences`.
  - **Corpus (bg-excluded):** union *occurs* (∃ demo, either dir) **39/400**;
    ∀demo split **19** / assemble **3** / either **22**. **split ⊆ subdivision**
    (subdivision = the in→out split test) — the genuinely new detection is the
    **assemble** direction (3 ∀demo: #11 `09629e4f`, #46 `234bbc79`, #192
    `7e0986d6`; subdivision reads `no` on all three). Verify specimen = **#46**.
  - **PB2 (recorded, not actioned):** subdivision stays **bg-AGNOSTIC** (103/400,
    its own tests, unchanged); union is **bg-EXCLUDED** (criterion-1 conceptually,
    code-disjoint). They diverge on the ~84 bg-cover tasks (e.g. #59 `29623171`:
    subdivision 0/3, and union’s earlier "3/3" was a **background-cover artifact**
    — corrected to 0/3 bg-excluded). A future subdivision criterion-1 = bg-excluded
    union would drop 103→19. Do NOT amend subdivision now.
  - union’s task payoff over subdivision is only the 3 assemble tasks; its real
    justification is the **operator vocabulary + the `union ⟹ inset` inference +
    `./evaluate` visibility** (not coverage). Gate green (8 `[ok]` incl. write;
    conformance/evaluate/#8-solve pass). **SHIPPED — committed `a8f7a13`.**

- **2026-06-27 — result-output format contract + bidirectional subdivision
  (BUILT + Cowork-gated 8 `[ok]`/400).** Format work over the `./arc solve`
  phase viewer:
  - **New canonical doc `solve/RESULT_OUTPUT_FORMAT.md`** — the per-phase
    result-output rendering contract (reference STEP blocks for phases 1/2/3 +
    the locked decisions). This is the single source for "the result output"
    format; when the user asks for it, reproduce the STEP block **verbatim**.
  - **Phase 1** (`pipeline.step_setup`) — `· {k} pt` segment is **CONDITIONAL**
    (only when points > 0). LOCKED; verified conformant 400/400.
  - **Phase 2** (`step_profile`) — tiers **INCLUDE background**; **empty pairs
    OMITTED** (all-empty task = header only). Both LOCKED (a bg-exclude attempt
    was reverted); verified 400/400 (300 with tiers / 100 header-only).
  - **Phase 3** (`step_subdivision`) — now **BIDIRECTIONAL + bg-AGNOSTIC**:
    `arc_grids.subdivisions` run both ways, a pair holds if a disjoint cover
    exists in EITHER direction; each finding tagged `[split]` (input whole) /
    `[assemble]` (output whole). LOCKED bg-agnostic (user chose it over the
    bg-excluded `union` route — so Phase-3 subdivision and the `union` operator
    now differ only in bg handling). Verified 400/400 (yes 118 / no 282 / 244
    header-only; findings split 464 / assemble 192). #8 still solves.
  - All per-phase format decisions are in `RESULT_OUTPUT_FORMAT.md` "Locked
    format decisions" — do not re-litigate. **OPEN:** Phase-4 result format +
    further task patterns (next chat); commit + Linux-gate the subdivision change.

- **2026-06-28 — Phase 4 "Component Re-Comparison" inserted + bg_deduction
  reworked to the persistent component-list model (BUILT + Cowork-gated 8
  `[ok]`/400; NOT committed).** Two threads, both in `arc1/solve`.

  **(A) New phase 4 = "Component Re-Comparison" (pipeline now 13 phases).**
  Inserted after Subdivision; Task pattern→5, Comparators→6, …, Apply→13. All
  `STEPS`/`STEP_DESC`/`STEP_TARGETS` keys + the gate "13-step" label renumbered;
  `STEPS.md` rewritten to 13 phases. `pipeline.step_objcomp` reads the phase-3
  findings and, per sub-piece, renders `{relation} {sub} = {component}  [from
  {direction}]`, grouped by pair under `Pair {p}:`. **Phase 3 stays subdivision
  ONLY (the cover); the same_* COMPARISON is phase 4** (relations computed in
  `step_objcomp`, NOT `step_subdivision`). Relation = `same_object`/`same_point`
  when the colour is KEPT, else `same_shape` (colour changed; a colour-changed
  point is also `same_shape`). Sub-label format **`{side}{p}.O{i}.sub{k}.{color}`**
  — the `.sub{k}` BEFORE the colour (e.g. `In1.O1.sub1.grey`); fixed in BOTH
  phase 3 (the `→ kids` line) and phase 4. Header = `component re-comparison —
  {n} sub-piece correspondence(s)` ("component" because points too). Verified
  structurally uniform 400/400 (0 nonconforming; 156 with content, 244
  header-only). Phase 4 + the phase-3 sub-label LOCKED in `RESULT_OUTPUT_FORMAT.md`.
  Phase 4 publishes `ctx["recomparison"]` (the per-sub-piece relations) for the
  bg rules.

  **(B) bg_deduction = persistent per-grid/per-colour component lists, mutated
  by the phases; ONE rule reapplied after each phase (`arc_solver.bg_advance`).**
  Final model (after several wrong turns — recorded so they're not repeated):
  - **State** (persistent in `ctx["bg_state"]`, JSON-safe, checkpointed): per
    grid, per colour, a **list of still-UNMATCHED components** (ids `O{j}`/`P{j}`/
    `S{whole}_{k}`), plus a `cand` set and the resolved `bg`.
  - **The phases MUTATE the state** (not rebuilt): phase 1 **add** components ·
    phase 2 **remove** same_object/same_point matches (per grid: input uses the
    match `in` side, output the `out` side) · phase 3 **REPLACE** each subdivided
    whole `O{idx}` with its sub-pieces `S{idx}_{k}` · phase 4 **remove** the
    sub-pieces that KEPT colour (same_object/same_point; same_shape does NOT
    count as a match).
  - **After EVERY phase (FR2) re-apply ALL rules** (`_bg_rules`): **FR1** commit
    guard (never empty `cand`) · **FR3** `len(cand)==1 → bg` · **PR1** ELIMINATION
    — a colour whose component list is EMPTY is dropped from `cand` (the one rule,
    unchanged, reapplied) · **PR2** train→test inheritance (all train grids resolve
    to one agreeing bg → test inherits it; this is what resolves the test grid).
    The runner calls `bg_advance(ctx, n)` after every phase from step 1;
    `bg_advance` self-initialises if `bg_state` is absent (recovers a stale
    checkpoint).
  - Capacity `bg_deduction` (`CATEGORY_REASONING`, `DS_BACKGROUND_SET`) registered
    in `arc_capacities` (stub body, provenance, D3) — the real logic is
    `arc_solver.bg_advance` per D3.
  - **Reversals locked this chat (do NOT reintroduce):** NO separate "PR3"
    same_*-elimination rule (it's just phase 4 mutating the lists + PR1) · NO
    recompute-from-palette / replay-from-profile orchestrator (state is genuinely
    persistent + mutated across phases) · `same_shape` is NOT a match for the
    component lists · addition's bg is via the pre-existing `_bg_color` interim
    (the earlier "discovered single_canvas" was Claude's unrequested invention,
    removed).
  - **OPEN (deferred):** #294 resolves bg=grey not black — rule 1 eliminates the
    static (unchanged, same_object-preserved) black canvas, leaving grey as the
    survivor. The "static-bg" gap; a future rule (e.g. containment/coverage guard)
    will fix it — owner declined all candidates for now. `bg_cand` is computed
    into ctx but NOT displayed in the `./arc solve` viewer.

- **2026-06-28 (cont.) — phase-5 Comparators Hypothesis + Background-Color display
  + Phase Rule 4 (same_shape+same_color) + phase-5 bg-exclusion.** Threads in
  `arc1/solve`.

  **(A) Phase 5 = "Comparators Hypothesis" — SHIPPED `eafd824`.** Swap: old phase 6
  "Comparators" → phase 5 (renamed); "Task pattern" (addition) → phase 6; still 13
  phases. Phase 5 lists the comparators firing on **ALL** demo pairs (∀, add-only
  walk = the per-pair intersection; over a fixed comparator vocabulary secondary
  adds never fire and removal is disabled per owner — verified 0/400 secondary
  add, 79/400 would-remove). **Registry-driven**: `arc_search._PAIR_PRED`
  (name→per-pair predicate) + `comparator_names()` are the single source for BOTH
  the ∃ `task_tokens` and the ∀ hypothesis (a future comparator auto-runs once it
  registers a facet + predicate). **`touching_delta` shown instead of intra-grid
  `touching`** (reuses `arc_solver.touching_changes`, gained∪lost over
  correspondence, **bg-forgotten** `exclude_bg=False`; ∀=12/400 vs touching
  400/400). Result = `Comparators Hypothesis:` header + one `{name} ✓` line per
  ∀-comparator (option a: only-firing). ∃ `task_tokens`/`./evaluate`/gate counts
  unchanged. Files: `arc_search.py`, `pipeline.py`, `STEPS.md`.

  **(B) Background Color display line — UNCOMMITTED.** New step-block line on
  phases 2–13 of `./arc solve` rendering `bg_advance`'s per-grid `bg_cand`. Per
  pair: `Pair{i}.bg=X` when one side resolves to X **and** X is a candidate on the
  other side (**option C**, consistency-guarded — the naive "one side resolves →
  other auto-resolves" conflicts on 133/1302 pairs: 36 resolve to different
  colours, 97 to a colour the other side excludes); else `In{i}.bg={…} ·
  Out{i}.bg={…}`; `test.bg={…}` always. Singletons bare, multi in braces; colour
  names. Files: `runner.py`, `RESULT_OUTPUT_FORMAT.md`.

  **(C) Phase Rule 4 = same_shape + same_color — UNCOMMITTED.** A bg-deduction
  **phase rule** (list mutation, like Rules 1–3 — NOT a foundational `_bg_rules`
  rule; the PR3-in-`_bg_rules` direction was tried and **reverted**, the state
  carries no shape data). Removes components whose in/out counterparts share shape
  + colour, at **phase 2** (objects — shape-group colour-matched pairs) and
  **phase 4** (sub-pieces — the colour-kept `same_object`/`same_point`, i.e. the
  former Rule 3 folded in). PR1 then eliminates the colour once its list empties.
  **REVERSES the 2026-06-28 lock "`same_shape` is NOT a match for the component
  lists"** (narrowly: shape **+ colour**, excluding recolored). No `moved`
  framing/data (owner: "the system doesn't know moved at phase 2"); identified via
  shape-group colour match. Impact: 65/400 `bg_cand` change, test bg resolved
  2→11; **#8 resolves bg=black**. Phase 2 vs 4 vs both = identical final result
  (0/400 differ); both chosen so the display resolves from phase 2. File:
  `arc_solver.bg_advance`.

  **(D) Phase-5 bg-object exclusion — UNCOMMITTED.** At phase 5, if a grid's bg is
  resolved (`ctx['bg_cand']`), its bg-colour objects/points are dropped and
  match/relations recomputed before the comparator checks. #8 phase-5 →
  `moved`/`touching_delta` (was +`inside`; the `inside` involved the black bg).
  Gate path (`run_all`, no `bg_cand`) unaffected. File:
  `pipeline.step_comparators_hypothesis`.

  **(E) bg resolution is NOT a success metric (owner).** The bg model is a
  per-phase elimination *trace*; abstaining is fine, and for #294 the bg doesn't
  matter. Baseline grounding (pre-Phase-Rule-4): `bg_advance` resolved a test bg on
  only 2/400 — recorded, not a target.

- **2026-06-28 (cont.) — checkpoint/`runs` tracking REMOVED from `./arc solve`
  (option C: full removal).** `./arc solve <task> <step>` now recomputes phases
  1..step in-memory on every invocation; no `runs/<task_id>/step-<n>.json`, no
  cached-vs-computed distinction, no `_result_<n>`/`_name_<n>` stamping. **The
  `status` STEP-block line is dropped entirely** (option C — it only ever carried
  the checkpoint path); a STEP block now opens `── STEP n · name …` then `uses`.
  RESULT_OUTPUT_FORMAT phase-1–4 reference blocks relocked without it. **The gate
  is unaffected** (`run_spike._solve_pipeline_check` already used
  `pipeline.run_all`, in-memory). `bg_state` is still JSON-round-tripped between
  phases *in-memory* (`_bg_dump`/`_bg_load`) — that machinery stays. Removed:
  `runner.RUNS`/`_ckpt`/the cache block/`os`+`json` imports; `solve/.gitignore`
  `runs/` line (kept `capacities*.json`); doc refs in STEPS.md / RESULT_OUTPUT_FORMAT
  / root `./arc` help (also corrected its stale 10-phase list → 13). **Kills the
  whole checkpoint-staleness gotcha class** (`rm -rf runs/<task>`, the
  Cowork-can't-rm `{}`-write workaround, `_name_<n>` invalidation). Verified
  Cowork-side: `./arc solve 8 13` solves #8, `run_all` `matches_withheld` True,
  no `runs/` written. **NOTE the stale gotcha text still in the
  `*_NEXT_CHAT_PROMPT.md` handoffs is now superseded by this entry.** **Mac:
  `rm -rf` the now-unignored `runs/` before commit; then gate.**

- **2026-06-28 (cont.) — phase-5 per-pair PARAMETER + ∀ CONCLUSION (BUILT +
  Cowork-gated; NOT committed).** Phase 5 lines go from bare `{name} ✓` to
  `{comp} → {item} | … → {conclusion}` — one item per demo pair. Decisions
  (this chat): **PB1=(a)+conclusion**; **per-pair item model** (supersedes the
  earlier per-instance-flat PB-d): item = the pair's parameter when all that
  pair's instances **agree**, else `multi` — **PB-l(b)**: `multi` = genuine
  within-pair disagreement, so a uniform many-object transform still shows its
  parameter (grounded: same-param multi-pairs = moved 16 / rotated 26 / reflected
  13 / recolored 16 over the ∀ set — (b) keeps those `constant`, literal-`multi`
  would have mislabeled them `varies`). Item rendering: moved `(dr,dc)` · rotated
  deg · reflected `H-axis`/`V-axis` (PB-g) · recolored `{from}→{to}` colour names
  (PB-f constant/varies only — no same-target bucket) · touching_delta
  `gained`/`lost` (PB-c: per-transition, all-same→`all gained`/`all lost`).
  Conclusion (any `multi`⟹`varies`; else first-match): moved `constant`→`all
  vertical: (X,0)`(dc=0)→`all horizontal: (0,Y)`(dr=0)→`varies`; rotated/recolored
  `constant`/`varies`; reflected `all H-axis`/`all V-axis`/`varies` (PB-a mixed→
  varies, PB-b constant-first); touching_delta `all gained`/`all lost`/`varies`.
  `inside` stays **bare `✓`** (PB-c/PB-k — a predicate, no transform param).
  Over-fire (rotated/reflected/recolored `*_pairs` over-fire) is **absorbed by
  `multi`** (a spurious extra instance just makes the pair `multi`→conservative),
  so the correspondence-filter (PB-h opt 3) was **not** needed. **Descriptive,
  not the rule** (PB5): #8 reads `moved → (6,0) | (0,3) | (-3,0) → varies`
  (slide-to-touch — vectors vary) + `touching_delta → gained | gained | gained →
  all gained`; non-load-bearing, no coupling to the #8 stages. Code: all in
  `pipeline.py` (`_PAIR_PERCEPTION` extractors + `_render_param` + `_pair_value` +
  `_conclusion` + `_comparator_line`; `_hyp_pair_set` split into `_hyp_pair_d`).
  **Corpus-grounded 400/400: 0 nonconforming, 86 enriched lines, all conclusions
  in the closed set, 50 lines carry `multi`.** Phase 5 reopened + relocked in
  RESULT_OUTPUT_FORMAT.md (new reference block + locked-decision) + STEPS.md.
  Gate: `./arc solve 8 13` still solves #8; full Linux gate pending.

- **2026-06-28 (cont.) — phase 6 "Task Patterns" (multi-pattern) + frequency-bg
  PURGED (BUILT + Cowork-gated 8 `[ok]`/400, #8 solves; NOT committed).** Two
  threads.

  **(A) Phase 6 = "Task Patterns".** Renamed from "Task pattern"; `produces`
  drops "(addition)". Now lists the patterns holding on EVERY demo pair (∀),
  read off the phase-2/4 `same_*` match results — bare `{name} ✓` per match
  (`Pattern Hypothesis:` header; `(none)` if none); a firing line is prefixed
  `bg not resolved` when a grid's bg is unresolved (PB-F). Six patterns
  (`arc_solver.task_patterns(profile, bg_cand)` + `_pattern_flags` /
  `_matched_families` / `_grid_components` / `_palette_label`):
  - **matched** (PB1/q2) = a component (object **or** point) with one of:
    same_object · same_point · same_shape+same_color (moved) ·
    same_shape+different_color (recolored) · **rotated** · **reflected**
    (rotated/reflected via the actual detectors — option **a**, not the
    same_cell_count∧same_bbox_area proxy, which over-matches). Else **unmatched**.
  - filters (all dims=preserved, ∀ pairs): addition = palette∈{preserved,
    increased} ∧ ≥1 unmatched **output**; subtraction = palette∈{preserved,
    decreased} ∧ ≥1 unmatched **input**; recoloring = ≥1 recolored-family (PB-A:
    **no palette gate** — {preserved,increased} rejected 19/37 real recolours);
    moving = palette=preserved ∧ all matched ∧ ≥1 moved (PB3 ≥1-moved guard);
    rotation = ≥1 rotated; reflection = ≥1 reflected (PB-D).
  - **#8 → `moving ✓`** (was wrongly "addition" — equal-only matched counted the
    mover as a new output object). Corpus (phases 1-6, ∀): addition 160 /
    subtraction 94 / recoloring 37 / moving 7 / rotation 16 / reflection 8;
    bg unresolved on 380/400 (those prefixed `bg not resolved`). Display-only,
    not consumed downstream. Phase 6 LOCKED in RESULT_OUTPUT_FORMAT + STEPS.md.
  - **Deferred (noted):** the phase-3 subdivision **component-universe**
    modification (PB-E "modified in phase 3") is NOT folded into matched yet —
    matched is computed over phase-1 objects+points (correct for the 244
    no-subdivision tasks + #8). Confirm if subdivided-task addition/subtraction
    accuracy matters.

  **(B) Frequency background DELETED — `bg_cand`/`bg_advance` is the SOLE bg
  method (owner directive).** Removed `arc_solver._bg_color` (pooled
  most-frequent) + `arc_grids.verify_background` (dead frequency helper) + the
  registered reason-caps `detect_background_frequency` + `reconcile_background`
  + `DS_BACKGROUND_CANDIDATE` (kept `DS_BACKGROUND` — the touching_delta body +
  D3 spike consume it). `bg_ground.py` deleted (its only purpose was the
  bg_advance-vs-frequency divergence). All executable consumers re-routed to
  **`arc_solver.resolve_bg(profile, raw)`** (runs `bg_advance` phases 1-2 →
  `bg_cand`) + `_resolve_solver_bg` (single bg for the placeholder #8 solver):
  `stage_background(profile, bg)` now takes bg injected; `step_background` feeds
  it from `ctx['bg_cand']`; `build_solver` from `resolve_bg`; `run_all` now runs
  `bg_advance` after each phase so `bg_cand` exists on the gate path; the gate
  D3 spike (`run_spike`) + the `./evaluate` `union` track use `resolve_bg`.
  Conformance unaffected (it iterates the remaining reason caps). **`union ⟹
  inset` fix:** routing union's bg through `bg_advance` exposed a latent bug —
  `union_in_pair` composes wholes from objects **and points** but `inset_occurs`
  scanned objects only, so a point-part union broke the skip-soundness on 2
  tasks; `inset_occurs` now scans objects+points → sound by construction,
  bg-independent. **Consequence:** union *occurs* drops 39→23/400 (bg-exclusion
  now relies on `bg_advance`, which abstains more than frequency did) — accepted
  per the directive. **`detect_background_frequency`/`reconcile_background` rows
  struck in ONTOLOGY §; re-add a detector only when needed.** **Mac: `git rm`
  the now-deleted `spike/bg_ground.py`.**

- **2026-06-29 — bg PR3 propagation + subdivision-sub-pieces-as-objects + phase-6
  `moving` fix (BUILT + Cowork-gated 8 `[ok]`/400, #8 solves; NOT committed).**
  Driven by 4 logic problems the owner found on `./arc solve 2 6` (#2 `00d62c1b`).

  **(A) New bg rule PR3 (pairwise propagation), `arc_solver._bg_propagate`.** When
  one grid of a train pair has bg resolved to `C` and the partner has `C` among
  its candidates, re-check the `C`-coloured objects: if they do **not** all
  recolor to one single colour together (`_c_persists` — uniform-recolor test
  over `recolored_pairs`), the partner resolves to `C` too. Reapplied each phase
  in `_bg_rules` (now takes `profile`); PR2 then carries `C` to test. Fixes the
  #2 issues: train **outputs** never resolved (the added colour blocks
  elimination), so PR2 couldn't fire; PR3 resolves them (`C` persists) →
  `bg_resolved=True`, the `bg not resolved` tag drops. (The option-C display line
  was *also* misleading — it showed `Pair.bg=black` when only the input resolved;
  PR3 makes display + per-grid agree for #2.)

  **(B) Subdivision sub-pieces ARE full objects (PB-E, full + "recoloring").**
  Owner: "when an object gets subdivided, the subdivisions are considered full
  objects." So a subdivided whole is replaced (in the matched/comparator universe)
  by its sub-pieces, driven off the **phase-4 recomparison** (no parallel object
  dicts). Phase 4 relation relabel `same_shape`→**`recolored`** (sub-piece + the
  object it covers share cells → colour change = recolor). Phase 5 `recolored`
  also fires off sub-pieces (`_recolored_params` adds `whole_color→part_color`).
  Phase 6 matched/unmatched over the augmented universe (whole removed, sub-pieces
  added + matched, covered parts matched). **#2 → phase 5 `recolored → black→yellow
  (×5) → constant`, phase 6 `recoloring`** (was `addition`/`bg not resolved`).

  **(C) bg-exclusion is now conditional + scoped (owner, option iii-refined).**
  NOT removed wholesale: transforms + phase-6 matched/unmatched **never** exclude
  (bg objects participate — an un-subdivided unmatched bg object drives
  `addition`/`subtraction`). Only `touching`/`inside`/`touching_delta` exclude the
  bg colour, and **only when that grid's bg is resolved** (`pipeline._inside_present`
  / `_pair_bg_excl`). #8 (bg resolved) keeps `moved` + `touching_delta` and still
  drops `inside`; an unresolved grid evaluates them with the bg colour in.

  **(D) `moving` filter corrected (owner).** `moving` = **dims=preserved ·
  palette=preserved · ≥1 moved-family** (dropped the "all matched" condition).
  So #8 reads `moving` again — and also `addition`+`subtraction` (its black bg
  object's cells change as movers move → unmatched, #8 not subdivided). "Fill"/
  "canvas"/"foreground" language struck from code/docs per owner ("the arc-solver
  doesn't know fill") — only mechanical terms (object, sub-piece, recolored,
  matched, the colour bg_advance resolved).

  **(E) `bg not resolved` flag** moved to a **suffix** `· bg not resolved` after
  the pattern name; purely informational (gates nothing now). Corpus (phases 1-6,
  ∀): recoloring 145 / addition 74 / subtraction 88 / moving 11 / rotation 16 /
  reflection 8; bg unresolved 289/400 (was 380 pre-PR3). 0 errors. Gate green
  (8 `[ok]`, #8 solves; union occurs 24/400). Phases 4/5/6 reopened + relocked in
  RESULT_OUTPUT_FORMAT + STEPS.md.

  **(F) Resolved bg considered for addition/subtraction (owner follow-up).** bg
  objects still participate in matched/unmatched, but the `addition`/`subtraction`
  unmatched-test drops the **resolved** bg colour (`_pattern_flags`/`_comp_color`,
  per-grid `bg_in`/`bg_out`) — a resolved bg can't read as added/removed; an
  unresolved bg still counts. recoloring/moving/rotation/reflection (family-presence)
  unaffected. **#8 → `moving` only** now (its unmatched black object is the bg →
  dropped); #2 still `recoloring`. Corpus shifts: addition 74→67, subtraction
  88→80. Gate stays green (8 `[ok]`, #8 solves).

- **2026-06-30 — Step-7 "Motivations" design + Batch-1 prerequisites (BUILT +
  gated 8 `[ok]`/400, #8 solves; NOT committed). Phase 7 itself = Batch 2.**

  **Design (Step 7 = "Motivations"; owner-driven).** Phase-5 detector conclusions
  and predicates become **motivations** driving the **generators**, in two flavors:
  - **reason** = a condition/parameter (the constant transform param, or a
    predicate condition `if touching`/`if inside` which also **scopes which
    objects**); **goal** = a target *state* a continuous transform proceeds toward
    (`until touching`).
  - **generator KIND**: **continuous** {move} → needs **reason + goal**;
    **discrete** {recolor,rotate,reflect} → **reason only**. A constant *vector*
    move is complete (`move (dr,dc)`); a constant *direction* rides with a goal
    (`move up until touching`); #8 = `move until touching` (direction varies).
  - Phase 7 enumerates candidate motivations per generator (parameter-reasons
    from phase-5 constants; condition-reasons + until-goals from predicates —
    predicate×generator combos are **open**, pruned by the demo test, not a fixed
    validity table), and **shows + tests each separately** per pair, ∀ add-only
    (like phase 5): **generative** test for parameter/goal (apply the generator,
    check it reproduces the output), **correspondence** test for a condition
    (transformed set == predicate set). Phase 8 combines motivations into rules
    (a later reasoning layer). A motivation is reasoning but individually tested;
    kept display-only for now (no capacity registered).

  **Capacities re-organized into 7 categories** (the organizing axis; free-string
  categories → lazily-created graphs, no core validation; `capacity_iri` embeds
  the category so `CAP_*` + the gate D3 IRI were resynced): **perceiver**(6) ·
  **profiler**(7) · **operator**(1 union) · **detector**(5: moved, recolored,
  rotated, reflected, touching_delta) · **generator**(4) · **predicate**(3: inset,
  touching, inside) · **reasoning**(3: build_correspondence, synthesize_selector,
  bg_deduction). DataState `provenance_category` tags left unchanged.
  `ordered_catalog` regroups by category (`CATEGORY_ORDER`).

  **`move`/`moved` generator↔detector pair.** Added the **`move`** generator
  (`(object, move_transform) → object`, body `arc_grids.translate`), completing
  the four pairs. Generator **`kind`** field (`GENERATOR_KIND` +
  `generator_kind`/`generator_args`) defines the arg set per KIND.

  **Comparatives — a VALUE family (DataState), not a capacity category**, modeled
  as **`(dimension, form)`**, form ∈ {sign(±), rank(1..n)}: **direction**(spatial
  axis, sign — movement/orientation), **relative-position**(spatial axis, sign —
  between objects), **size**(size, sign/rank), **ordering**(rank). direction &
  relative-position are the same `(axis, sign)`, different uses. First consumer
  already exists: `synthesize_selector` uses the size comparative
  (`largest/smallest non-bg`). Built **`direction`** now (`arc_grids.direction_of`
  — derived `(axis,sign)`, **4 orthogonal**, up=−row, diagonal/zero→None); size
  formalized where it lives; relative-position/ordering deferred to a consumer.

  **`synthesize_selector`** (clarified): from a `state_change` (mover/target
  roles) + object features → the **minimal discriminative selector** per role
  (colour / size / shape) that holds ∀ demos and distinguishes the role from the
  other non-bg objects. Batch 1 = these prerequisites (gate green). Batch 2 =
  phase 7 (enumerate + show/test motivations, ∀, generative/correspondence).

  **Batch 2 — phase 7 "Motivations" SHIPPED (gate green 8 `[ok]`/400, #8 solves,
  14-step; NOT committed).** Inserted **phase 7 = Motivations** (the #8 solver
  stages renumber 7–13 → 8–14; gate label `13-step`→`14-step`).
  `arc_solver.motivations(profile, bg_cand, recomparison)` + `pipeline.step_motivations`:
  per generator, the ∀-holding goals/reasons — discrete (recolor/rotate/reflect):
  constant-parameter reason (`recolor {colour}` reading whole-object recolored +
  subdivision sub-piece targets; `rotate {deg}`; `reflect {H/V-axis}`) + predicate
  condition-reason (`… if touching`/`… if inside`, transformed set == predicate
  set); continuous move: `move ({dr},{dc})` (constant vector) and/or
  `move [{dir}] until touching` (goal — moved objects gained touching; `dir` via
  `arc_grids.direction_of`). **#8 → `move until touching`, #2 → `recolor yellow`.**
  Corpus: 85/400 tasks have ≥1 motivation (recolor 66 / move 9 / rotate 9 /
  reflect 1). Phase 7 LOCKED in RESULT_OUTPUT_FORMAT + STEPS.md (14-phase). Phase
  8 (combine motivations into rules) is the next layer.

- **2026-06-30 (cont.) — Step-8 "Rules" SHIPPED (move + recolor; gate green 8
  `[ok]`/400, #8 solves, 15-step). Solver stages 8–14 renumber → 9–15; gate label
  `14-step`→`15-step`.**

  **Design (Step 8 = "Rules").** A **rule** = a generator + selector-bound role(s)
  + reason/goal, assembled so it reproduces every demo output. Phase 7 tested a
  motivation's components separately using the objects it *observed* changing;
  phase 8's step up is **binding a feature-selector that identifies those objects
  without observing the change** (`_selectors_for`, the inverse `_select` drives
  the apply), then **generatively verifying** the fully selector-driven rule
  reproduces every demo output (∀ add-only). A rule is kept only if every role is
  pinned by an ∀ selector AND the apply reproduces all demos; else it abstains.
  `arc_solver.rules` + `pipeline.step_rules` (phase 8, `general*`, display/
  hypothesis — the general precursor to the hardcoded #8 rule stages 13–15).
  Forms: move-goal `move [{mover}] to [{target}] until touching` (#8; reuses the
  `_slide` machinery via `_apply_move_goal`, single mover→single target v1);
  move-vector `move [{sel}] by (dr,dc)` (`_apply_move_vector`, sel = all-non-bg or
  a single mover's feature). Corpus: **2/400** assemble a verified rule — #8
  (`move [no base shape (irregular)] to [shape = square] until touching`, ✓∀ 3/3)
  and #53 `25ff71a9` (`move [all non-background] by (1,0)`, ✓∀ 3/3); 0 errors. The
  other 7 move-motivation tasks abstain (selector doesn't reproduce ∀) — sound
  add-only behaviour, like phases 5–7.

  **Scope = move + recolor (owner: A→C→C-move→+recolor, grounded).** Owner first
  chose "all four families" (A); probes narrowed then re-expanded:
  - **rotate/reflect rules deferred — no reliable in→out correspondence.** Probe
    over the 9 rotate + 1 reflect motivation tasks: **0/10 have a clean 1-to-1
    in→out object correspondence** (2–42 rotated/reflected candidate pairs per
    demo — small/symmetric shapes match many rotations); the bbox-origin
    placement delta is ∀-constant for only 1/10 (an artifact of picking
    candidate-0). The origin-delta placement model (owner's proposal) is sound
    *given* correspondence, but correspondence is the upstream blocker (several of
    these look grid/region-level, not per-object). Filed: **"rotate/reflect rule —
    blocked on in→out object correspondence (+ probably a grid/region-level
    transform model, not per-object placement)."**
  - **recolor rule — BUILT: `recolor [enclosed] {colour}` (enclosed sub-piece
    fill).** The recolor target is the **enclosed subdivision sub-piece(s)**: phase
    3 splits the bg object into an outer region + its enclosed pockets, phase 4
    marks the pocket recolored (verified #2 pair1 → `In1.O0.sub2` recolored yellow).
    Because subdivision partitions using the OUTPUT insets it can't run on the test
    input, so the enclosed region is computed **input-only** by
    `arc_grids.enclosed_bg_cells` (bg cells that can't reach the border through bg,
    4-conn — the cell analogue of `inside`); this **equals** the phase-3 enclosed
    sub-pieces' cells (verified #2: == the recolored sub-pieces, incl. pair3's
    two-pocket union) but computes from the input alone so the rule generalizes to
    the test. **Owner directive: this input-only enclosure is a PHASE-3 product
    (`ctx["enclosed"]`), and phase 8 CONSUMES it — `enclosed_bg_cells` is not
    called in any validation after phase 3.** (Validating on the phase-3 *output*-
    derived sub-pieces would be circular — they're defined by the recolor — so the
    input-only enclosure is what keeps the ∀ verify a real generalization test.)
    Derive the constant fill colour, verify the fill reproduces every demo ∀. Corpus: **2/400** — #2 `00d62c1b` (`recolor [enclosed]
    yellow`, ✓∀ 5/5) + #251 `a5313dff` (`recolor [enclosed] blue`, ✓∀ 3/3). This is
    the owner's "bg is a colour with shapes too" point at cell granularity.
    (Correction: an earlier note claimed the pocket is "part of the big bg
    component / not a separate object" — that was the phase-1 view; post-phase-3
    the pocket IS a first-class sub-piece.)

  The move family already has correspondence (via `moved` + touching-gained) and a
  sound grid-apply (`_slide`/`_render`), so it ships verified; the deferred
  families are gated on machinery upstream of the rule (correspondence / region
  selection) — "no scaffolding without a consumer." Phase 8 LOCKED in
  RESULT_OUTPUT_FORMAT + STEPS.md (15-phase). Next layer: general test-apply
  (the general replacement for the #8-specific stages 13–15).

- **2026-06-30 (cont.) — `inside` = ray-based containment (`arc_grids.contained_pairs`);
  REPLACES first-diff `inside_pairs` as the `inside` comparator everywhere.**
  `a inside b` iff, from EVERY cell of `a`, a ray to the grid edge in each of the
  4 directions passes through object `b` (b may sit beyond other objects, so
  **nested containment O1⊃O2⊃P0 is captured** — the first-diff test dropped it
  because the inner content polluted the wall set). Emits one `{"a","b"}` pair per
  container (nested element → several), same shape as `inside_pairs`.
  **`bg_resolved` flag** (owner directive): **True** (bg known — phase 5
  `_inside_present`, phase 7 `_pred_objs`) applies the background rule — a
  bg-coloured object is a VALID container only if it is **itself contained** by a
  valid container (fixpoint bottoming at non-bg objects), so the ambient bg
  (inside nothing) is excluded and an enclosed bg pocket is kept; **False**
  (perception `attach_relations`, driving the ∃ Search token / `./evaluate` /
  induce, where bg isn't resolved) = raw ray containment, no bg filter. This
  unblocks using the same comparator bg-blind (the ∃ token) and bg-aware
  (reasoning). **Design path** (owner, iterated): the ambient-bg exclusion is NOT
  a border-touching test (an invented dead-end, reverted) but the structural
  "valid container ⟺ itself contained" rule. Grounded on **#251 `a5313dff`**: O1
  (red shape) ⊃ O2 (black pocket) ⊃ P0 (red dot); first-diff missed `O2 inside O1`
  because O2's walls span O1 **and** P0 (both red, different components); the ray
  test + valid-container rule yields `O1⊃O2, O1⊃P0, O2⊃P0` and excludes the
  ambient bg O0. Cost 1302 grids/0.59s. Gate green 8 `[ok]`/400 (invariant +
  evaluate self-adjusted; ∃ `inside` token 259→268/400), #8 solves, #251 fires
  `inside` ∀. `inside_pairs` (first-diff) retained as a primitive but no longer
  called. STEPS.md + RESULT_OUTPUT_FORMAT.md updated.

- **2026-07-01 — Phase 8 REWORKED to candidate emission + NEW Phase 9 "Rules
  Selection" (BUILT + Cowork-gated 8 `[ok]`/400, #8 solves, 16-step; NOT
  committed).** Old solver stages 9–15 renumber → 10–16 (gate label
  `15-step`→`16-step`); `STEPS`/`STEP_DESC`/`STEP_TARGETS` renumbered; STEPS.md +
  RESULT_OUTPUT_FORMAT.md updated (phase-8 reopened, phase-9 locked).

  **Design (owner-driven, this chat).** Phase 8 previously emitted **complete**
  ∀-verified rules only; the owner's intended contract is **per-comparator
  CANDIDATES** — "recolor because inside" + "recolor because biggest" are two
  individual candidates that need **not** reproduce the output alone. Phase 9
  finds the **minimum candidate set** that does (e.g. `recolor [biggest ∧
  inside]`). Split:
  - **Phase 8 = candidate emission.** `arc_solver.rules` now returns
    `{"candidates":[…], "bg":…}`. MOVE (goal/vector) + cell-RECOLOR
    (`recolor [enclosed]`) stay self-contained **complete** candidates (carry
    their apply spec: `kind`+`param`; `_assemble_*` enriched, ∀-verified at
    assembly, marked `✓ complete`). **object-RECOLOR** emits one
    `recolor_obj` candidate per **necessary** single condition
    (`_recolor_condition_candidates`): a constant target colour ∀, condition ∈
    `_condition_labels` (`inside`/`touching`/`biggest`/`smallest`/`colour=`/
    `shape=`), necessary = transformed ⊆ condition ∀, **vacuous** (== every non-bg
    object) dropped. `_cond_objs(gs,bg,cond)` resolves a label → object-index set
    (predicates reuse `_pred_objs`; features = size/colour/shape).
  - **Phase 9 = `arc_solver.select_rules` + `pipeline.step_rules_selection`.**
    Minimum-cardinality covering set: singles first (complete candidate = size 1),
    then **2×2 → 3×3** conjunctions of same-param `recolor_obj` (target = the
    **intersection** of condition sets, `_apply_recolor_objs`); apply set to each
    demo input, exact-match output ∀; first covering set wins; none →
    **`I don't know how to solve this task`**. **Conjunction only** — a size-≥2
    set must share one (generator, param); mixed-kind = cross-generator
    **composition** → `_apply_candidate_set` returns None (deferred). **No test
    apply** in phase 9 (owner PBE → phase 16 / a future phase 10).
  - **Decisions locked (owner):** PBA build the candidate model now (few
    comparators today, more later); PBB **conjunction only**, composition
    deferred; PBC phase 8 emits candidates (was complete-only — reopened the
    LOCKED phase-8 format); PBD a **complete** rule is reused as-is (size-1 set)
    or conjoined; PBE phase 9 selects on demos only, no test-apply; PBF combos
    matter (see corpus finding).
  - **Corpus finding (probe 2026-07-01).** With today's 6-condition vocab, the
    **≥2 conjunction path has ZERO corpus consumers**: object-recolor to a
    constant colour = 10 tasks (0 selectable by any conjunction), per-colour
    object-recolor ∀ = 2 tasks (both size-1). So the ≥2 branch is **forward-
    looking** (consumers arrive as comparators/predicates land, RULES §8) and is
    gated on a **synthetic 2-demo fixture** (`run_spike._SYN_CONJ`: recolor red
    the biggest∧green object → phase 9 returns size 2). Live size-1 path:
    #8 (move goal), #2/#251 (`recolor [enclosed]`). **task 5 `045e512c`** (owner's
    "copy shape / follow directions / with given colours") → **`I don't know`**:
    it needs copy/replicate + tile + direction-from-marker generators the demo
    lacks, and is cross-generator **composition** (not conjunction) — filed as
    the next, larger arc (new generator family + composition algebra).
  - **Gate:** `_solve_pipeline_check` extended (same `[ok]` line, still 8) — #8
    solves via the hardcoded tail + matches `build_solver`; phase 9 selects a
    covering set for #8/#2/#251; the synthetic conjunction resolves at size 2.
    Gate green (8 `[ok]`, wrote 400 profiles). **DEFERRED:** cross-generator
    composition + copy/replicate/tile generators (task-5 family); retiring the
    hardcoded #8 tail (stages 10–16 still serve `build_solver`/arc_debug);
    general test-apply of the selected set (phase 10). `inside_pairs` still dead.

- **2026-07-01 (cont.) — Phase 10 "Solve Task" + the #8 hardcoded tail RETIRED;
  pipeline is now 10 general phases (BUILT + Cowork-gated 8 `[ok]`/400, #8/#2/#251
  solve end-to-end; NOT committed).** Owner directives: add phase 10 (apply the
  phase-9 rule set to the test → answer + explanation); **delete all phases after
  10** (the old #8-specific stages 10–16); add a **description section** to each
  phase 1–10.
  - **Phase 10 = `pipeline.step_solve`.** Applies the phase-9 selected set to the
    **test input** via `arc_solver._apply_candidate_set` (reused from phase-9 demo
    verification) → answer grid; result = `solved by: {rule set}` +
    `ANSWER {H}×{W} · matches withheld test: {✓|✗|n/a}`; abstains
    `I don't know how to solve this task` when phase 9 found no set. **No new
    apply code** — the move/recolor apply already existed. **Enclosure fallback:**
    for `recolor [enclosed]` the phase-3 test enclosure is `[]` when the test bg
    is unresolved (#251); phase 10 recomputes `enclosed_bg_cells(test, solver-bg)`
    (guarded on `not enc_cells`, not `is None` — phase 3 returns `[[]]`). #8 (move
    goal), #2/#251 (`recolor [enclosed]`), #53 (move vector) all solve their test
    ∀; 396/400 → `I don't know`; 0 apply-failures, 0 exceptions across 400.
  - **#8 tail RETIRED.** Removed `step_background`/`step_roles`/`step_persistence`/
    `step_selectors`/`step_rule`/`step_verify`/`step_apply` + the dead `_changes`
    helper + `ctx["bg"]`/`stage1..stage6` producers from the pipeline; `STEPS`
    16→**10 rows**, all `general`/`general*` (no more `semi`/`⚑#8`). The
    `arc_solver.stage_*` functions + `build_solver` **survive** (still called at
    `run_spike:287` for the `arc_debug` solver panel + the D3 biting check) — only
    the pipeline's `step_*` wrappers went. This is the retire-the-tail step
    flagged as deferred on 2026-07-01 morning, now greenlit.
  - **Gate repointed.** `_solve_pipeline_check` no longer asserts `stage6`/`stage1`
    or run_all-vs-`build_solver` parity (run_all has no `stage*` now); it asserts
    **phase 10 solves #8/#2/#251** (test answer == withheld output) + the phase-9
    synthetic size-2 conjunction. Same single `[ok]` line, still **8 `[ok]`**;
    label `16-step`→`10-step`.
  - **Description line.** `runner._print_step` renders an `about` line (the
    `STEP_DESC` phase description) under each STEP header; `STEP_DESC`/`STEP_TARGETS`
    trimmed to 1–10. STEPS.md + RESULT_OUTPUT_FORMAT.md relocked to 10 phases.
  - **Still deferred:** cross-generator composition + copy/replicate/tile
    generators (task-5 family); real ≥2-conjunction corpus consumer (synthetic
    fixture until more comparators land); retiring `build_solver`/`arc_debug`
    hardcoded panel; `inside_pairs` dead code.

- **2026-07-02 — MindsOS WIRING chat (branch `demo/arc-wiring` off `demo/arc`; NOT
  merged). The arc-solver now RUNS ON THE REAL MindsOS layers; a durable Falkor-backed
  instance persists solved-task Episodes. ZERO core changes.** Full running record in
  memory `[[arc-wiring-progress]]` + `[[mindsos-persistence-model]]` +
  `[[arc-mindsos-layer-mapping]]`.
  - **Layer model (owner-corrected + code-verified).** capacity = L3 (fixed function);
    its per-task RESULT = L5 mental-model instance; L4 = orchestration (decides which
    caps to call + sequence); `cl.invoke`/`find_pipeline` = the L3 door. Persistence:
    L2 + L3 = Global+Local metagraphs; L4 outputs persist via L2; **L5 episodes are
    LOCAL-ONLY ("No Global L5")** ⇒ arc-solve is Local.
  - **New files:** `spike/arc_l4.py` (L4 driver + in-memory instance assembly — mirrors
    the shipped `tests/phase_49` `build_stack`), `spike/arc_instance.py` (the DURABLE
    Falkor instance — Linux+docker only, NOT in `./run_spike`), `docker-compose.yml`
    (FalkorDB sidecar). Modified: `spike/arc_capacities.py` (+`inside` real body, +3
    solve caps, +8 DataStates, `install_arc(session=…)`), `spike/run_spike.py` (+3
    in-memory checks).
  - **Solve through the layer.** 3 new L3 DECISION caps in `_solver_capacities`
    (CATEGORY_REASONING): `emit_candidates` (phase 8 = `arc_solver.rules`),
    `select_rules` (9), `apply_solution` (10) + 7 solve DataStates (DS_PROFILE/BG_CAND/
    RECOMPARISON/ENCLOSED/RULES/SELECTION/SOLVE). `arc_l4.solve_through_layer` runs
    phases 1-7 inline (profile) then DISPATCHES 8→9→10 via `L4Dispatcher` — L4=control,
    caps=decisions (NO monolith `arc.solve` — that puts orchestration in L3, the
    boundary the owner corrected). `run_spike._arc_solve_layer_check`: dispatched answer
    == inline AND == withheld ground-truth for #8/#2/#251 (non-tautological). `inside`
    became the first real predicate cap (`arc.perceived_grid` bundle DS, ray
    `contained_pairs`, 400-grid conformance). Phases 1-7 stay inline in the driver
    (perceive IS dispatchable — `_l4_intake_check` — decompose later).
  - **Why no core needed.** `find_pipeline`/ConjunctionFinder compose data-flow chains,
    NOT the solver's control logic (∀/min-set/apply) → an authored L4 sequence, not
    discovered (so `composition-lifecycle` merge + Part 5 are OFF the path). Caps take
    COARSE bundle inputs (profile/pair/grid) → no same-type-operand arity ever (Part 5
    moot). Durable Episode: ADR-0182 (Phase 50) already routes dict node `value` → the
    `_value_json` column (live-tested `tests/maintenance/…::test_live_structured_value_
    round_trip`) → an Episode dict persists with NO core change; the demo calls
    `FalkorDBLocalPersister.save(user, kl.local_metagraph(user))`.
  - **Durable instance (b), Local.** `build_durable_instance` =
    `arc_l4.build_instance(arc_local=True)` (arc caps + DataStates → the user's Local L3;
    all-Local — both share scope, mixed Global-ds+Local-caps raises) + `FalkorDBLocalPersister`.
    `run_and_persist(SOLVED_TASKS = 05f2a901 #8, 00d62c1b #2, a5313dff #251, 25ff71a9 #53)`:
    per task solve_through_layer → `consolidate_task(task_pattern_iri="arc:solved:<id>",
    outcome)` → 4 Episodes in one Local → `delete`+`save` → reload asserts 4. `restart`
    mode: fresh `KL.bootstrap()` + `install_local_metagraph(user, persister.load(user))`
    finds all 4 with NO trip re-run (survives restart). Run:
    `python3 -m intelligence_demo.arc1.spike.arc_instance [restart]`; container
    `mindsos-falkordb` (6379); `FalkorConfig.from_env()`. Gotcha: `delete`-before-`save`
    (same Local name `local_knowledge:arc` else runs accumulate).
  - **Gate:** `./run_spike` now prints **13 `[ok]` lines**; #8/#2/#251 still solve; durable
    path separate (Linux+docker). Discipline: Cowork builds / Mac commits / Linux gates
    (`[[machine-paths-and-gate]]`).
  - **Deferred:** decompose phases 1-7 into dispatched caps; `synthesize_selector`/
    `bg_deduction` remain stubs (not on the solve-decision path in use); merge
    `demo/arc-wiring`→`demo/arc`. Next-chat prompts drafted:
    `ARC_REPORTING_NEXT_CHAT_PROMPT.md`, `ARC_SOLVER_CAPACITY_NEXT_CHAT_PROMPT.md`.

- **2026-07-02 (cont.) — merged `main` (phase-1 seam + composition-lifecycle) into
  `demo/arc-wiring`; `touching_delta` → `input_group=fold` (§0 D3 amendment).** Merging
  `main` brought core's **input-contract enforcement** (`call_capacity`, ADR-0072
  §am-2 / composition-lifecycle Slice 2 Part 6): `invoke` now validates inputs against
  declared CONSUMES (`missing_required` + `unexpected_input`; **`fold` is not enforced**).
  This broke the D3 biting spike — `touching_delta` **declares** `(touching, correspondence)`
  but its body reads `(pair, background)`, and the wrong-input invoke is now rejected.
  - **Fix = `input_group=INPUT_GROUP_FOLD` on `touching_delta`** (one line). Chosen over
    re-declaring the real inputs `(pair, background)`: re-declaration breaks conformance
    check **(b)** (`DS_STATE_CHANGE` unreachable from `DS_GRID` once it consumes `pair`,
    which isn't grid-reachable) + forces a spike/docstring/§0 rewrite. `fold` keeps the
    gate green as-is (both spike invokes pass; declared edges unchanged so (b)/(c) hold)
    and is the **GF-3 "typed input-group, core-future" arriving** — the cap folds over C,
    so `fold` is the honest label, not a dodge.
  - **§0 D3 / GF-1 amendment.** The clause "invoke validates outputs only; declared
    CONSUMES may be fiction; bodies `**kw`+`.get` → missing → None" is **superseded** by
    ADR-0072 §am-2 (inputs now enforced). Provenance-divergent reason caps must be
    `input_group=fold` to keep that latitude. GF-1 body-canonical stands; D-A
    (`find_pipeline` isn't the fold composer) stands, reinforced (missing inputs fail loud).
    The deeper D3 truth is UNCHANGED by this fix — `touching_delta` is still a **monolith**
    with an **inverted `arc_solver` dependency** (the real decomposition/wiring stays deferred).
  - **Divergence audit (reason caps, declared-inputs vs body).** Only `touching_delta` is
    **invoked** through the layer and diverges → fixed. `build_correspondence` /
    `synthesize_selector` / `bg_deduction` are stub bodies (`… → None`, ignore inputs),
    **dormant** (never invoked in the gate); they'd only bite if invoked with non-declared
    inputs → mark `fold` **when/if** invoked. `emit_candidates`/`select_rules`/
    `apply_solution` + generators are honest (declared == read). No other runtime break.
  - Gate: re-run `run_spike` on the merged core; anchor **13 `[ok]`** (Cowork built; Mac
    commits; Linux gates).

- **2026-07-02 (cont.) — the "ask" front door: `solve task <ref>` intake via the shipped
  Phase-1 seam (ADR-0195/0196); gate 13→14.** A user request now enters through
  `mindsos_intelligence.interpret()` instead of a hardcoded `task_id`. New `spike/arc_intake.py`:
  arc-Local `hint`/`map`/`resolve` bodies + a `Phase1Profile`-bound dispatcher + `solve_task()`.
  Flow: `interpret("solve task <ref>")` → hint `{predicate:solve, object:task, reference,
  reference_kind}` → `map` → `task-pattern:arc:solve` (Local, ADR-0150 §am-8) → `resolve`
  (index→id8, `find_pipeline` composes `[resolve? → solve]` off `reference_kind`) → id8 fed to
  the bespoke `solve_through_layer`. Interpretation-only (ADR-0195): stops at
  `resolved_reference`; no core TaskRun/Episode for arc runs (arc's own `consolidate_task` writes
  the Episode). Seam contract confirmed in the core chat (ADR-0195 seam + ADR-0196 needs_input);
  arc owns the bodies + task-pattern + enumeration, all Local (RULES §8).
  - **`<ref>` = 8-char id OR int index.** Enumeration is PINNED: canonical ARC order = task ids
    **sorted ascending, 1-based** (`sorted(dataset['train'])[idx-1]`; matches `run_spike`/viewer;
    **#8=05f2a901, #2=00d62c1b, #251=a5313dff, #53=25ff71a9**). CORRECTION: earlier `#labels`
    used *insertion* order and were wrong — canonical is sorted.
  - **Cold-start confirm (ADR-0196 `NeedsInput`), policy = cold-start-only (owner).** While the
    arc-Local "ordering-established" marker is absent, an index request returns `NeedsInput`
    (propose the id8; user confirms → re-submits the canonical request, stateless two-turn).
    `confirm_ordering(inst)` sets it. The marker is a **persisted** `CapacitySnapshot` node in the
    Local `capacity-state` graph (+ a live in-memory mirror the resolve body reads) → confirm is
    **once-per-USER, survives restart**, not once-per-session.
  - **Durable (b).** `arc_instance.build_durable_instance` now `register_intake`s; `run_and_persist`
    `confirm_ordering`s + persists the task-pattern + marker alongside the 4 Episodes; `restart`
    asserts both survived (index resolves silently, no re-confirm). Verified on Falkor.
  - **Gate:** `_arc_intake_check` (wiring step 5) — one `[ok]` line; anchor now **14**. Run
    `arc_instance` as a **script** (`python3 intelligence_demo/arc1/spike/arc_instance.py [restart]`),
    NOT `-m` (the `__package__` guard sets `sys.path`; `-m` skips it → `mindsos_intelligence`
    ModuleNotFoundError).
  - **§0 D3 amendment (from the merge).** Core now ENFORCES the invoke input-contract
    (composition-lifecycle Part 6, ADR-0072 §am-2): `call_capacity` validates inputs vs declared
    CONSUMES (missing/unexpected), **except `input_group=fold`**. `touching_delta` → `fold` (it
    folds over C; provenance topology kept). The old "layer validates outputs only / declared may
    be fiction" clause is dead; provenance-divergent reason caps must be `fold`.
  - **Deferred (intake):** out-of-range index crashes (`canonical_for_index` IndexError, unguarded);
    no CLI verb (Python API only); `map` single-target. Still open from prior: `grid_rigid` (+7,
    built + verified 4→11/0-wrong then **REVERTED by owner** — coverage stays 4); merge
    `demo/arc-wiring`→`demo/arc`.

---

## 5. CORE PROPOSAL — **IMPLEMENTED (parts 1–4), 2026-06-21**

**Status (checked 2026-06-21).** The core-mod chat (`COMPOSITION_LIFECYCLE_DESIGN_LOG.md`) shipped
ARC's four-part proposal on branch **`feat/composition-lifecycle`** (commit `3253ce8`; ADR-0071
§am-2 + ADR-0159 §am-1). Built:
- **Part 1 finder seam** — `Finder` ABC (L3 algorithms / L4 selection); `BFSFinder` (the old
  unsound walk) + `ConjunctionFinder` are the two strategies.
- **Part 2 conjunction/fold finder** — `ConjunctionFinder`: backward hyperpath, resolution **per
  input-group × OR over producers**; returns a DAG. Validated structurally against ARC's 3 cases.
- **Part 3 typed input-group** — a **`_CapacityBase.input_group` field** (`INPUT_GROUP_ALL_REQUIRED`
  / `ANY_OF` / `FOLD` in `identifiers.py`), read from the declaration registry. The **graph
  hyperedge** (ADR-0156 §am) is **DEFERRED** (no graph-walking consumer).
- **Part 4 DAG result** — `PipelineDAG`/`DAGStep`/`DAGEdge` **replaces** the linear `Pipeline`;
  `find_pipeline` retained, BFS emits a degenerate-linear DAG.
- Deferred: promoted-path strategy, composite `node_kind`, promotion loop (all zero-writer).

**Parts 5–6 status (updated 2026-06-23, against `composition-lifecycle-s2-confirmed`):**
- **Part 6 (invoke input contract) — SHIPPED.** Core commit `2676b9d`: `capacity._validate_inputs`
  now validates invoke inputs against declared CONSUMES (raises on missing required), called from
  `call_capacity` + `runtime.invoke`. Closes the D3-spike "validates outputs only" gap.
- **Part 5 (operand-arity / same-type operands) — DEFERRED, consumer-gated.** Core design log:
  "ship Part 6 standalone; gate Part 5 behind a confirmed consumer." No shipped path hits the
  same-type-operand case (bongard self-validates presence only; ARC ships provenance-only). bongard
  m5 is the named candidate (its "N-values-under-one-IRI" fold shape). A **Part-5 core-mod prompt
  was drafted 2026-06-23** (hand to a fresh core chat when a consumer commits).
- Demo still pins `phase-50`; has NOT consumed the Slice-1 finder/`input_group` yet — that's the
  next-phase decision (re-pin → declare `input_group` per reason cap → route through
  `ConjunctionFinder`; doing so is what would un-defer Part 5).

**Consumption gating (RULES §3).** This is on a feature branch — **not merged to `main`, not
tagged, demo still pins `phase-50-confirmed`.** The demo cannot use `ConjunctionFinder`/`input_group`
until: `feat/composition-lifecycle` → merge to `main` → confirmed tag → `git merge <tag>` into
`demo/arc` → re-pin `STATE.json`. The demo does **not** block on this.

**What it unlocks (new decision when pinned):** declare `input_group` per reason cap
(`touching_delta`/`synthesize_selector` = `all_required`, `build_correspondence` = `any_of`,
`reconcile_background` = `fold`) and route the reason layer through `ConjunctionFinder` → turns
D-A / GF-6(b) from "found-but-unsound (BFS)" into "found-and-sound (conjunction)". Caveat: parts
5–6 + the monolith bodies (D3 spike) mean *sound composition at the finder* ≠ *decomposed bodies*.

---

### 5.1 Original proposal text (kept for provenance)

(filed — for the core-mod chat; demo does NOT block on it)

**Problem.** `find_pipeline` (ADR-0071, `mindsos_capacity/pipeline.py`) is a single-input BFS over
binary `PRODUCES`/`CONSUMES` edges (ADR-0156). It (a) fires a capacity when ANY one input is
reachable — unsound for multi-input caps; (b) returns a linear `Pipeline` (`Tuple[PipelineStep]`)
that can't represent a converging DAG; (c) is the only implemented finder yet hardwired-canonical;
(d) no layer enforces conjunction at dispatch/invoke (verified — see §4). First real multi-input
consumer = the ARC reason layer.

**Proposal (4 parts).**
1. **Finder seam** — a finder-strategy interface; BFS becomes one strategy. Siblings: conjunction/
   fold finder, promoted-path lookup (L2 `promoted-pipelines`), hand-authored.
2. **Conjunction/fold finder** — AND/OR hyperpath search: capability = AND over required inputs,
   DataState = OR over producers; returns a DAG.
3. **Typed input-group hyperedge `{all_required | any_of | fold}`** on the registration contract
   (ADR-0156/0159) — finder-agnostic; replaces N undifferentiated binary CONSUMES. NOT a blanket
   "all members required" rule (that breaks `build_correspondence`/`reconcile_background`).
4. **DAG result type** — replace the linear `Pipeline.steps` with a converging-DAG plan.
5. **(D3-spike 2026-06-21) DataState operand-arity / pair-axis.** The inputs map is keyed by
   DataState IRI, so a capability consuming **two operands of the same DataState type** (in-touching
   vs out-touching; `same_object`'s two Objects) cannot express both — the pair-axis is invisible.
   Registration needs an operand-position/arity notion (roles, not just a set of input DS).
6. **(D3-spike 2026-06-21) `invoke` input contract.** `call_capacity`/`runtime.invoke` validate
   **outputs only**; inputs are splatted as kwargs with no check against the registered CONSUMES.
   So nothing keeps a body's real dependencies in sync with the declared topology (the ARC
   `touching_delta` body consumes `(pair, background)` while it declares `(touching, correspondence)`
   and still runs). A finder built on CONSUMES is trusting an unenforced contract.

**Caveat / discipline.** "No scaffolding without a consumer." ARC is filed as the motivating
consumer but ships provenance-only (binary edges, sweep) and does not pin this. Confirm whether L4's
"real finder" is meant to own conjunction before sizing the phase. Reopens ADR-0071/0156/0159.
**D3-spike evidence (demo-local, #8 green):** wiring one cap (`touching_delta`) through `cl.invoke`
proved execution is mechanically trivial but full inline→registered fidelity is blocked by parts
5–6 + the monolith-vs-decomposed-body gap — all CORE, none demo-blocking.
