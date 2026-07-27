# Collection-iteration Slice 3b CONFIRMED — targeted per-member re-execution (option A)

**Status:** BUILT + GATE-GREEN + MERGED to `main` (squash `b3bae74`, PR #83).
**Gate:** full containerized run (Linux, live FalkorDB, 2026-07-27) = **4351 passed / 12 skipped / 1 xpassed / 0 failed**, 33m00s, on the pre-merge tip `18da8f2` (fresh GitHub clone, `--build`). `main` baseline `9e47654` = 4343/0 + **8 new** = 4351; 0 regressions.
**Targeted pre-gate (venv):** `pytest tests/phase_48/test_slice3b_targeted_reexec.py + slice3/slice1a/slice1b/slice2/step5/crash_recovery/consolidation_seam/dream_pipeline_hookup` = 39 passed.
**core_version:** stays `phase50` (L4/L5-side; no core-package / role / category change).
**CR / design:** `confirmation_docs/CORE_CR_COLLECTION_ITERATION.md`. Relates ADR-0171 (lifecycle); ADR-0199 PRESERVED. Builds on Slices 1a/1b/2/3.

## What this slice is

Slice 3 made replan/diagnosis **address** a suspect map member (advisory only) — replan *execution* stayed whole-pipeline (clear-all, discard blackboard). Slice 3b lets the orchestrator **act** on that address: when the verdict names a re-runnable **top-level flat map** member (reserved `"map"`/`"plan_subtree"` level + a resolvable ref-path), it **retains the blackboard across the replan loop** and **re-runs only that one member**, reusing the completed siblings (values + grounding graphs) and re-firing the fold + any downstream.

**Option A (owner-approved, this chat).** The member is addressed by its **existing Slice-2 grounding ref-path** — no promotion of map members to first-class chain PipelineRuns. That (option B) plus cross-stage grounding continuity are a **separate later slice** (see Deferred). Consequence: 3b is **additive-inert** — byte-identical to Slice 3 until a consumer names a bare `{leaf_idx}:m{member_idx}` member with the reserved level.

## What shipped (3 edited, 1 new test)

- **`mindsos_intelligence/execution.py`**
  - `run()` gains `blackboard` (reuse a retained board instead of a fresh seed) and `targeted=(map_leaf_idx, member_idx)`.
  - `_run_milestone_sequence` gains `start_idx` (skip the already-run prefix milestones on a targeted replan — their values ride the retained board) and `target_member`.
  - `_run_map_milestone` gains `only_member`: read the retained `blackboard[out_ds]`, re-run just that member, splice its new output over the old slot, keep siblings. Full fan-out (`only_member=None`) unchanged.
  - `_run_one_member` (NEW, extracted): the per-member work (nested sub-plan OR flat 1b find+execute + bounded retry + ∀-abort), shared by the full loop and the targeted single re-run — behaviour identical to the inline Slice-1b/2 loop.
  - `resolve_member_target` / `_parse_member_target` (NEW): resolve `target_ref` to `(map_idx, member_idx)` **only** for a bare top-level `"{idx}:m{j}"` naming a `map` milestone with no `sub_plan`; a full `pipelinerun:…` ref (scope may contain `:`) or a nested/deeper path returns `None`.
- **`mindsos_intelligence/replan_check.py`** — `invalidate_at_and_below(request_run, replan_level, at_index=None)`: with `at_index`, clear only the PipelineRuns from that milestone position onward (map + fold + downstream) and keep the prefix; `at_index=None` (v0 / `pipeline` / unresolved) clears all — byte-identical.
- **`mindsos_intelligence/orchestrator.py`** — replan loop holds one `blackboard` across iterations. On a `replan` verdict: if `resolve_member_target` yields a target, `targeted=(map_idx,member_idx)`, `invalidate_at_and_below(at_index=map_idx)`, re-enter `execution.run(targeted=…)` on the RETAINED board, and record the **actual** targeted level; else reset the board to a fresh seed + whole-pipeline clear, recorded as `"pipeline"` (byte-identical to Slice 3).
- **`tests/phase_48/test_slice3b_targeted_reexec.py`** (NEW, 8) — `resolve_member_target` gating (3: bare form accepted; full-ref/nested/non-map/out-of-range/malformed rejected; `sub_plan` map rejected); `invalidate_at_and_below(at_index)` keeps prefix + `None` clears all (2); execution-level targeted re-run touches only the named member, keeps siblings, re-fires the fold (1); non-targeted full run unchanged (1); orchestrator wiring retains the blackboard object across the loop + passes `targeted` + records the targeted level (1).

## Decisions (owner, this chat)

- **D2 = A (not B).** From-scratch, B (members → first-class chain PipelineRuns) is the cleaner end-state, but the code seams show B is **non-additive always** — it rewrites the shipped flat run-list + Slice-1b/2 test assertions — for a feature that is **inert until arc** ships a live `should_replan`. A preserves additive-inertness, reuses the shipped Slice-2 ref-path (which is exactly what Slice-3's `target_ref` already points at), and is **~80% reusable toward B**. B deferred.
- **D3 = keep-and-clear** the blackboard on a targeted replan (retain siblings; clear the target member's output + the fold aggregate + downstream). NOT full-retain (that reintroduces the Slice-1a stale-read bug), NOT rebuild-from-persist (couples to the inert-until-Step-5 persist read-path).
- **D4 = continuity deferred** (inert, no live reader; both build paths are real work; not needed by A-3b).

## Gate findings that shaped the design (verified against code at the branch base)

- **G1 — the replan-after-successful-map trigger EXISTS but is inert.** `orchestrator.run_lifecycle` runs `execution.run` (the whole map+fold), then `sufficient_predicate.evaluate` + `replan_check.check`; a `replan` verdict re-enters. Both predicate bodies are v0 stubs → dormant until arc/WSD. A member load-failure aborts terminally (never reaches replan), so 3b's live target is the **content-insufficiency** case (map completed, aggregate judged insufficient, blame names a member). Same inert-until-consumer maturity as Slices 1–3.
- **G2 — no run DAG; members are not chain runs.** `request_run.pipeline_runs` is a flat list; the shipped `invalidate_at_and_below` ignored the level and cleared all; a map emits ONE PipelineRun; the member axis (`m{i}`) lives **only** in the grounding ref-path. Option A targets exactly that path, aligning with Slice-3's `target_ref` semantics.
- **G3 — intergraph-edge persistence is unbuilt.** `FalkorMMPersister.persist` writes one graph (nodes + intra-graph edges) only; cross-graph edges/XRefs aren't captured. So cross-stage continuity via intergraph edges needs new persistence → deferred.

## Inertness (no regression to shipped paths)

With no `target_ref` (v0), a full `pipelinerun:` advisory ref (Slice-3's form), or a nested path, `resolve_member_target` returns `None` → whole-pipeline replan + fresh blackboard = **byte-identical** to Slice 3. The two Slice-3 tests and every lifecycle sibling (1a/1b/2, Step-5, crash-recovery, consolidation) pass unchanged.

## Rebase note (base health)

Built off `634e44b`; `main` advanced to `9e47654` mid-build. `634e44b` was transiently **red** from an in-flight `task→Request` rename lane (a runtime-breaking `test_slice3` `task_scope=` call + two cosmetic `__all__` stragglers) and a skill-role lane — **none caused by this slice** (proven: the 6-file diff is lifecycle-only; the failures reproduced on clean base and vanished on `9e47654`). Upstream **rename-R2 (#80)** repaired it. This slice was **rebased onto `9e47654`** and re-gated clean; the straggler fixes were dropped (upstream owns them). The two cosmetic `__all__` stragglers remain on main (gate-green; rename lane's scope).

## Deferred — the B + continuity slice (designed, not built)

One combined later slice, gated on arc having a **live** replan-after-map trigger:
- **Option B** — promote map members to first-class chain PipelineRuns (addressable by the existing invalidate walk; reverses Slice-2's flat-list-single-source-of-truth). A-3b's retry/keep-siblings/selective-invalidate logic carries over (~80%); only the addressing swaps.
- **Cross-stage grounding continuity** — connect a consumer stage's seeded start to the producer instance across per-run graphs (reverses Slice-A's per-run-graph / intra-graph-edge model; needs intergraph-edge persistence per G3).

## Next (arc handoff, unchanged)

The seam is inert until arc's `should_replan` shadow emits `replan_level` in `{"map","plan_subtree"}` + a bare `"{leaf_idx}:m{member_idx}"` `target_ref` for a top-level flat-map member — like L5 Steps 1–4 pre-Step-5. Parallel members remain sequential (v1) by decision.
