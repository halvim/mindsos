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
  composes by `PRODUCES`/`CONSUMES`; no higher-order dispatcher; no capacity calls another.
- **World-model locked** at `ONTOLOGY.md` §4 — relevant rows for the reason stage:
  **#16** touching (positional predicate, parameter-free), **#17** attribute = 4th role
  family (provenance vs attachment axes), **#18** Region = concrete root + located/normalized
  two-axis model, **#19** vocabulary alias reconciliation. These are settled; decisions below
  build *on* them, not against them.
- **Grounding state.** The **#8 specimen** (background ensemble + correspondence +
  `touching_delta` + selector) is now **topology-registered** in `spike/arc_capacities.py`
  (`_reason_capacities`, stub bodies, real compute still inline in `arc_solver`) and gated on
  Linux (#8 still solves). The **rest** of 3A–3I remains ▲ inline / off-graph.
- **Profile phase is a FILTER** realized via `find_pipeline` path-availability (an absent
  Delta ⇒ that transform family is uncomposable). **Background detection (H1) is the
  bottleneck** — the 3D selector, `touching_delta`, and 3A bg-exclusion all depend on it
  (even #8's own shape selector, since the background is also irregular).
- **Invoke boundary (current).** Capability bodies are computed **inline**, not via
  `capacity_layer.invoke`; `find_pipeline` only walks edges (see D3).

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
| **D3** | Invoke boundary: inline body-fold vs `capacity_layer.invoke` | open (currently inline) |

### Reason-stage grounding
| D | Question | Status / rec |
|---|---|---|
| **D4 ★** | Background detection (frequency vs residual vs ensemble) | **LOCKED 2026-06-21 — ensemble topology, frequency-only body**: `detect_background_frequency` (real body) → `BackgroundCandidate`; `reconcile_background` = **L4 fold** over candidates → `Background`, **degenerate now** (single candidate passes through; policy-pending). Additional detectors (residual/…) + real reconcile policy deferred to **CORPUS-ANALYSIS** (below). Residual NOT built now — known-wrong on #8, family unidentified. |
| **D5** | `detect_background` registration form | **LOCKED 2026-06-21 — swept, not composed**: background detection is an L4-style **sweep** over detector outputs → reconcile fold → `Background`, **not** a `find_pipeline`-pulled leg (verified: `find_pipeline` BFS returns one shortest path → can't gather N producers; ADR-0071). Corrects the prior "lazy find_pipeline-pulled" framing. |
| **CORPUS-ANALYSIS** | Background-detector bucketing over the 400 train tasks (which detector matches the human-evident bg; where frequency vs residual wins) | **SCHEDULED** — hard prerequisite for the real `reconcile_background` policy + the detector roster (D4). |
| **D6** | Correspondence (P3): register + resolve duplicates | **LOCKED 2026-06-21 — unambiguous-subset, defer resolution**: `build_correspondence` = swept fold over pairwise comparators → `Correspondence` DataState (not a `find_pipeline` leg, per D5). Assemble strictest-first 1:1 (`same_object` → `moved` → `same_point`); ambiguous pairs left uncorresponded; completeness check abstains if a needed object is uncorresponded. Duplicate-resolution **policy** routed to CORPUS-ANALYSIS. |
| **D7** | Adopt profile-as-`find_pipeline`-filter | **open — has a wrinkle**: `find_pipeline` walks the **static registered** graph, but "no DimensionDelta *this task*" is **per-task instance** data. Comparators always register as producing the Delta DataState (value `None` when no change), so `find_pipeline` always sees `resize`/`recolor` as composable — it **can't** prune per-task. The filter is real but it is an **instance-level gate**, not shipped-`find_pipeline` path-availability. Resolve the mechanism before adopting. |
| **D8** | Close palette-as-set hole (recolor-by-permutation) | open |
| **D9** | Wire `touching_delta` now vs register the induce sub-graph together | open |

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

`D1 + D2` → `D4` → `D6` → `D0` (build pivot) → `D7 / D8` → `D10–D13` → `D14`.

Immediate next move: **D1 + D2** (reasoning-graph + grounding semantics), then **D4**
(background detection) — the reasoning-graph is the tool that makes D4's dependents visible.

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
