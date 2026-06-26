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
