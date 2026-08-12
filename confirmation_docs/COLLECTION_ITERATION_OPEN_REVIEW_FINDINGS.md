# Collection-iteration — open design-review findings (handoff to CORE main lane)

**Provenance:** design-review side-chat, closed 2026-08-11. That chat's two largest
findings — the missing planner→executor bridge and per-member replan — were
independently built since (see *Resolved* below), so the chat is archived. What
remains are three findings that are still live in the shipped code and are **not
tracked** in `CORE_CR_COLLECTION_ITERATION.md` or `CORE_VERIFIED_FINDINGS.md`.
Ownership of these now sits with the CORE main lane.

Cross-ref: `CORE_CR_COLLECTION_ITERATION.md` (canonical CR + slice status),
`COLLECTION_ITERATION_SLICE_{1A,1B,2,3,3B}_CONFIRMED.md`,
`PLAN_MILESTONES_PLANRESULT_CONFIRMED.md`.

## Resolved since the review (no action — listed so they're not re-raised)
- **Planner→executor bridge.** `plan_construction.build` now reads a planner
  `milestones` list (`_read_milestones` / `_build_from_milestones`) and populates
  `PlanResult.milestone_specs` + `leaf_targets`. The map/fold executor is reachable
  through the live lifecycle. (Was: `build` dropped the shape; executor test-only.)
- **Per-member replan.** Slices 3 + 3b shipped: `execution.run(blackboard=…,
  targeted=(map_idx,member_idx))`, `resolve_member_target`, retained-blackboard
  targeted re-run. (Was: attempt-scoped blackboard blocked point-replan — the exact
  tension raised in review, now built.)

## Open findings

### 1 — Bounded retry has no failure mode to catch in the deterministic path (verify or gate)
`_run_one_member` retries a failed member up to `MEMBER_RETRY_CAP=2`
(`execution.py:706-719`). But: members are already unpacked in memory
(`blackboard.get(collection_ds)`, `execution.py:620`), and the retried region
composes the pipeline **once** and reuses it (`compose_cache`, `_run_member_pipeline`
`execution.py:773-784`) then re-runs `execute_pipeline` over an identical in-memory
seed. There is **no load/IO step inside the retried region** — contradicting the
"transient load failure" rationale in the CR (`§Bounded retry`) and the docstring
(`execution.py:83`). For deterministic member capacities, retry re-runs identical
compute to an identical failure: pure cost (up to 2× member latency on failure),
zero benefit.
**Decision owed:** name the real transient mode (RNG / external resource / timeout in
a member capacity) and document it, OR gate retry behind an explicit capacity
`retryable` flag, OR drop the retry. Not a silent keep — the current rationale is
unsupported by the code path. *Severity: low-med (correctness fine; wasted work +
misleading doc).*

### 2 — A single unsolvable member aborts the whole request; folds fail soft (asymmetry)
Map member `success=False` after retry → `MemberAbortError` → orchestrator marks the
request `aborted` (`orchestrator.py`, `MemberAbortError` catch). A fold reducer
`success=False` is soft: `_run_fold_milestone` sets `pr.status="failed"` and does
**not** raise (`execution.py:827`), so it flows to the `sufficient_predicate`
`dont_know` path. Same collection machinery, two severities. There is **no
member-level `dont_know`**: a member that legitimately can't solve one element (e.g.
one degenerate ARC grid among many) has no outcome short of aborting the entire
request, unless its capacity returns `success=True` carrying a sentinel the fold must
decode — an unenforced, undocumented convention.
**Decision owed:** (a) keep hard ∀-abort and document that member `success=False`
MUST mean machinery failure, never "no answer" (push the sentinel convention onto the
consumer explicitly); or (b) add a third member outcome (member `dont_know`) the fold
weighs. Matters the moment a real consumer (arc) wires member capacities through
`invoke`. *Severity: med (shapes the consumer contract).*

### 3 — Same-level sibling map/fold can collide on the flat value bus (plan-authoring invariant, unguarded)
The blackboard is a flat dict keyed by DataState IRI; a map writes
`blackboard[out_ds]` and a fold `blackboard.update(outputs)` at the same level
(`execution.py:501,649,820`). Nesting is safe (members get isolated sub-blackboards),
but two **same-level** siblings sharing an `out_ds`/`in_ds` IRI silently overwrite.
No core guard; it's a consumer plan-authoring invariant. Likely not exercised by the
current gate.
**Decision owed:** accept as a documented consumer invariant, or add an assert-on-
collision write in `_run_milestone_sequence`. *Severity: low.*

## Explicitly NOT re-raised (already tracked)
- **Cross-stage grounding continuity** (value bus is in-memory; per-stage grounding
  graphs are isolated, no producer→consumer edge) — already named in
  `CORE_CR_COLLECTION_ITERATION.md` as its own deferred slice, bundled with Slice-3b
  option B. No new information here.
