# ADR-0201 — Amendment 6: partial results — a member stops in place, and a truncated domain is a stop

**Status:** Accepted (2026-08-15). Records the machinery half of the member
wall (`core-member-machinery-failure-partial-record`, owner-ruled 2026-08-14
to partial results; design pass coordination §62–§64). Amendment 5 made the
partial state RENDERABLE (ids by position); this amendment makes it
REACHABLE — and owns the vocabulary it needs: one `RunStopped` token and the
`PipelineRun` status word the conceded rule consumes.

## Context

A map member whose capacity failed for machinery reasons raised
`MemberAbortError` after `MEMBER_RETRY_CAP`, and the orchestrator marked the
whole request conceded: one exposure's crash destroyed every other exposure's
correctly-decided answer and the claim's Record with it — the opposite of
what the product claims. Worse, the record of the failure itself was DROPPED:
only accepted attempts appended their grounding graphs, so the failed
member's final attempt — which had grounded a manifest and a terminal
`RunStopped` — never reached persistence. And a member that asked for input
(`needs_input`) was retried — asked the same question again — then aborted
everything.

Shape (a) (ADR-0209) is the EPISTEMIC half: an exposure that cannot be
*decided* is an in-band value. This amendment is the MACHINERY half: an
exposure whose machinery *crashed* has no value at all, and the run must say
so without destroying its siblings' work.

## Decision

**1. A member stops IN PLACE; nothing aborts.** A flat member still failing
at `MEMBER_RETRY_CAP`, a member whose body asks for input, a cancelled
member, and a no-route member all return a structural
`(value, graph_id, completed=False)` outcome (an explicit flag, never a
sentinel in the value channel — absence-as-a-special-value is what the
silent-None hole punishes) — and their siblings run. The stopped member's
FINAL attempt's graph is retained: it carries the terminal `RunStopped`
(`step_failed` / `needs_input` / `cancelled`) the page renders as the stop
block at that member's position. A no-route member retains its manifest-only
graph — the run-4 precedent: manifest-only IS the no-route stop; no new
token. `MemberAbortError` is RETIRED as a raiser (the class remains as API);
the absence of raisers is pinned by a census test.

**Retry rule, written here so the next capacity author reads it:** retry is
for plain step failure only. A `needs_input` result is never re-asked —
inputs do not change between attempts, and a capacity whose `needs_input`
depends on mutable external state is mis-designed by the ADR-0208 split
(environment state is an outage that raises, never an epistemic verdict). A
cancellation is a decision, not a transient. No route is deterministic.

**2. The map records the truncation; the fold decides it.** The map writes
the COMPLETED members' outputs (ordered, compact) to `out_ds`, the full
N-length grounding-id list (am-5's carrier), and a parallel per-member
completed mask (`execution.member_completed_key`) — needed because the
compact outputs list can only be positionally re-aligned at a Slice-3b
targeted splice by knowing which members completed. Compact-list and mask
must agree at every consumer or the run RAISES (the record and the value bus
in step, or loud).

**3. `RUN_STOPPED_PARTIAL_DOMAIN` (`"partial_domain"`)**, the fifth member of
the closed set, with its phrase (*"some of what was needed could not be
completed, so no overall conclusion was drawn"*). A fold whose mask says
fewer members completed than exist — INCLUDING none of them — stops
pre-dispatch with this token, manifest carrying the full N-length id list so
every stopped member's position renders its stop block. Concluding from a
machinery-truncated domain is the empty-domain doctrine generalized;
`empty_domain` stays exactly "the map had ZERO members". The writer method
is `record_partial_domain` (`RunStopped` alone, no CapacityInstance — G3;
`record_stopped` refuses the token like its two siblings). The healing path
is a Slice-3b targeted re-exec of the stopped member — existing machinery,
existing budgets — after which the splice realigns outputs, ids, and mask,
and the re-run fold dispatches normally.

**4. Nested propagation, minimum-viable (§63 Q5).** A sub-plan member whose
sub-run's terminal milestone did not complete is a STOPPED member of its
parent — decided from the sub-run's own record (its terminal `PipelineRun`
status) cross-checked against `sub_target` presence, RAISING on
disagreement; its id falls back to the sub-run's last stopped graph (the
ADR-0209 D3 definition, amended). This closes the conversion path where an
inner stop would have surfaced as a silent completed-looking `None` in the
outer list. Full cascade policy (partial-within-partial, nested retries) is
deliberately NOT decided here — filed.

**5. The `conceded` rule, from the record.** `PipelineRun.status` gains
`"stopped"` — set by a fold that stopped pre-dispatch (partial OR empty
domain) and by a map with ≥1 stopped member — joining the closed vocabulary
{running, completed, failed, stopped}, written down here for the first time.
A terminal attempt with ≥1 `"stopped"` run and no `"failed"` run classifies
the request `conceded` (Dream D4: a reached stop-decision), decided by
`execution.terminal_attempt_stopped_short` reading the chain graph — the
artifact objects ARE the node values, and replan invalidation clears
superseded refs from `request_run.pipeline_runs`, so the list is always
exactly the terminal attempt. The classifier RAISES on an unknown status,
never defaults. ⚠ Owner-ruled consequence (coordination §65): an
EMPTY-domain run now also classifies `conceded` (previously `dont_know` via
insufficiency) — one uniform rule for reached stop-decisions.

## Consequences

- The `#158` member-order hazard is DEFUSED rather than tripped: the fold
  never consumes a gapped list (it stops first), so "seeded order = member
  order" still holds everywhere a reducer runs.
- The demo renderer's partial-fold form is now reachable: position *i* has a
  `graph_id`; entry absent + that graph carries `RunStopped` ⟹ stop block;
  entry absent + manifest-only graph ⟹ no-route stop block; anything else ⟹
  raise. The unmatched-member raise re-scope and the rest of the demo
  consumption stay a demo-lane ship (owner ruling D5).
- Three ∀-abort pins RESTATED, not deleted (slice1b, slice2 nesting,
  multiinput — the retry-cap halves kept verbatim); the replan-verdict
  `abort` path (`test_conceded_on_abort_verdict`) is untouched and stands as
  the negative control that the two abort words never merge.
- FILED, not decided here: nested cascade policy; the transient-retry mode
  (COLLECTION_ITERATION finding 1); a finer request status than `conceded`.
