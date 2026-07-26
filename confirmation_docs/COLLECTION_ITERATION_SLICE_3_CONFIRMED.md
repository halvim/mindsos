# Collection-iteration Slice 3 CONFIRMED — targeted (per-member) replan/diagnosis address

**Status:** BUILT + GATE-GREEN on `feat/collection-iteration-slice-3` (code commit `1f4efd2`) — NOT merged (PR pending).
**Gate:** full containerized run (Linux, live FalkorDB, 2026-07-26) = **4335 passed / 12 skipped / 1 xpassed / 0 failed**, 33m34s (fresh clone of `1f4efd2`, `--build`, slice3 collect = 4). `main` baseline (`c7b0775`, 4331/0) + 4 new (the Slice-3 tests); 0 regressions. Same skip/xpass profile as the Slice-2 gate.
**Targeted pre-gate:** `pytest tests/phase_48/test_slice3_targeted_replan.py test_slice1a_value_bus.py test_slice1b_map_fold.py test_slice2_nesting.py test_step5_solve_execution.py` = 21 passed (4 new + 17 regression: 2 Slice-1a + 4 Slice-1b + 3 Slice-2 + 8 Step-5).
**Base:** cut from `main` @ `c7b0775`, which includes the task→**Request** rename R1 (#74). This slice is written on the renamed surface (`request_run` / `request_id` / `RequestOutcome` / `emit_request_run`); the replan/diagnosis verdict + record + blame shapes (`ReplanVerdict`, `ReplanRecord`, `BlameVerdict`, `replan_check.check`, `phase_6.diagnose`) were untouched by R1.
**core_version:** stays `phase50` (L4/L5-side; no core-package / role / category change).
**CR / design:** `confirmation_docs/CORE_CR_COLLECTION_ITERATION.md`. Relates ADR-0171 (lifecycle); ADR-0199 PRESERVED. Builds on Slice 1a (`e9ed6f4`) + 1b (`e24b5c3`) + 2 (`41d2110`).

## What this slice is

**Addressing only.** Slices 1a/1b/2 gave every executed leaf an isolated grounding *ref-path* (`pipelinerun:{scope}:…:m{i}:…`) — a locatable member address. Slice 3 lets a real consumer (arc) put that address on its `decision.should_replan` verdict so replan/diagnosis can name the suspect member instead of the whole pipeline. The advisory target is (a) recorded on the `ReplanRecord` for member-scoped audit, and (b) fed into Phase-6 diagnosis so blame can be member-scoped (`BlameVerdict.milestone_ref`).

**What it deliberately does NOT do:** scope what re-runs. Replan *execution* stays whole-pipeline (clear-all). Targeted re-execution — re-running only the named member while preserving the rest of the run — is a separate, **non-additive** slice: it requires retaining the attempt-scoped blackboard across a replan, reversing a shipped Slice-1a decision (the same class as the deferred cross-stage-continuity slice, which reverses Slice-A). See "Deferred" below. So for **diagnosis** the CR's "point at a specific member instead of the whole pipeline" is fully delivered; for **replan execution** it is recorded-as-intent, not executed.

## What shipped (3 edited, 1 new test)

- **`mindsos_intelligence/chain_artifacts.py`** — `ReplanVerdict` gains two optional advisory fields: `replan_level: Optional[str] = None` (a reserved `REPLAN_LEVELS` granularity — `"map"` / `"plan_subtree"`) and `target_ref: Optional[str] = None` (the Slice-2 member ref-path). This is the ONLY new shape: `ReplanRecord.replan_milestone_ref` and `BlameVerdict.{chain_level, milestone_ref}` already existed (unused slots since Phase 47).
- **`mindsos_intelligence/replan_check.py`** — `check()` reads the two fields tolerantly (`v.get(...)`, exactly like `verified` / `divergence`). A v0 verdict omits both → `None`.
- **`mindsos_intelligence/orchestrator.py`** — the replan + abort branches record `verdict.target_ref` on the `ReplanRecord` (via the existing `replan_milestone_ref=` kwarg); the recorded `replan_level` stays `"pipeline"` (the ACTUAL whole-pipeline action) so `invalidated_refs`=ALL never contradicts a finer recorded level. The Phase-6 dont-know branch feeds the last verdict's advisory target into `phase_6.diagnose(outcome=…)`; when no target is named it passes `outcome=None` so the dispatch is `{}` exactly as before. Invalidation / re-execution unchanged.
- **`tests/phase_48/test_slice3_targeted_replan.py`** (NEW, 4): (1) `replan_check.check` carries `replan_level`/`target_ref` when the verdict names them; (2) `check` defaults both to `None` when absent (byte-identical); (3) integration — a custom `should_replan` emits a targeted verdict (`plan_subtree` + a member ref-path) and a capturing `attribute_blame` proves the orchestrator recorded the target on the `ReplanRecord` (`replan_milestone_ref` = the member ref, `replan_level` = `"pipeline"`, `verdict.replan_level` = `"plan_subtree"`) AND fed it into diagnosis (`attribute_blame` input = `{target_ref, replan_level}`, `outcome.blame.milestone_ref` = the member); (4) v0 inertness — standard v0 verdicts name no target, so the `ReplanRecord.replan_milestone_ref` is `None` at `replan_level="pipeline"` and blame is whole-pipeline.

## Inertness (no regression to shipped paths)

Every v0 / 1a / 1b / 2 / Step-5 verdict omits `replan_level`/`target_ref`, so `check` yields `None`/`None`, the orchestrator emits `emit_replan_record(..., replan_milestone_ref=None)` (identical to the prior positional call), and diagnosis dispatches `{}` (`diag_outcome=None` → `phase_6.diagnose(outcome=None)` → `outcome or {}`), identical to the prior `phase_6.diagnose(self._dispatcher)`. Whole-pipeline clear-all and the invalidated-refs set are unchanged. The 17 Slice-1a/1b/2/Step-5 regression tests pass unchanged; full gate 0 regressions.

## Design decisions honored (CR §Locked decisions, owner 2026-07-25)

- **Additive / inert** — new behavior is gated entirely behind a target a v0 verdict never names; existing paths byte-identical.
- **Members sequential (v1)** — unchanged; this slice adds no execution behavior.
- **Consumer emits the shape** — core only carries the advisory fields, records them, and forwards them to the L3 diagnosis capability; no core logic learns arc's structure. The v0 `should_replan` never sets a target.
- **No audit contradiction** — the recorded `replan_level` is the actual action (`"pipeline"`), distinct from the consumer's advisory `verdict.replan_level` and the advisory `replan_milestone_ref`; a full clear is never labeled a finer level.

## Deferred: targeted re-execution (finding)

The CR's Slice-3 bullet ("point replan … at a specific member instead of whole-pipeline") is delivered for **diagnosis + audit**, but **targeted re-execution is NOT additive** and is split out:

- Re-running only member *i* while keeping the other members' outputs requires retaining the attempt-scoped `blackboard` across the replan (upstream + sibling-member values), which reverses the shipped Slice-1a decision ("attempt-scoped, discarded on return, replan re-enters clean — no stale reads").
- The member address the CR names (the `pipelinerun:…:m{i}:…` grounding ref-path) is **not** the chain `PipelineRun` IRI that `invalidate_at_and_below` clears, and a map milestone emits **one** `PipelineRun` for all members — so there is no per-member chain artifact to invalidate. Scoped invalidation would additionally need members promoted to first-class `PipelineRun` artifacts (changes the chain tree).
- Both reverse a shipped Slice-A/1a per-run-isolation decision — the **same class** as the deferred cross-stage grounding-continuity slice, and best done together (they share the blackboard-retention machinery). Requires owner sign-off; not byte-identical.

**What Slice 3 delivers:** the reserved `"map"` / `"plan_subtree"` REPLAN_LEVELS become live (carried on the verdict, recorded, and driving member-scoped diagnosis). The connected, member-scoped *re-execution* is deferred.

## Open items (deferred within the CR)

- **Targeted re-execution (Slice 3b)** — reverses Slice-1a; see finding.
- **Cross-stage grounding continuity** — reverses Slice-A; its own slice.
- **Parallel members** — sequential in v1 by decision.

## Inert until arc

Like Slices 1a–2 and L5 Steps 1–4 pre-Step-5, the seam grounds nothing new in prod until arc's `derive_initial_plan` shadow emits a `should_replan` verdict that names a member (`replan_level` + `target_ref`). No arc-side change is requested here.
