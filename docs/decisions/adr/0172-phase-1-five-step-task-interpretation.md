---
title: Phase-1 five-step task interpretation + Method δ + v0 catalog discipline
status: Accepted
date: 2026-06-08
accepted_date: 2026-06-08
layer: L4
related: [0171, 0159, 0195, 0197, 0206]
---

# ADR-0172: Phase-1 five-step task interpretation

**Status:** Accepted

**Date:** 2026-06-08

**Related:** ADR-0171 (six-phase lifecycle), ADR-0159 (capacity registration contract v2),
[ADR-0206](0206-planning-decomposition-confidence.md) (**amends this ADR** — see
§amendment-2), ADR-0195 (interpretation seam), ADR-0197 (modality ingress).

> ⚠ **The current design of this flow is
> [ADR-0206](0206-planning-decomposition-confidence.md), not this ADR.**
> ADR-0206 §3 states the steps as **request → hint → map → plan** — `derive_goal` is
> **gone** — and makes *plan* a loop (`search → find → decompose → repeat`). §4 retires
> the `MAX_DEPTH` bound. §8 **deletes** the thirteen `placeholder=True` capacities that
> §3 below ships. This ADR stays **Accepted** because its five-step flow is what
> `mindsos_intelligence/phase_1.py` runs today and ADR-0206 is **Proposed and unbuilt**
> (CORE-C4 has not started). **Read §amendment-2 before treating anything below as
> current.**

## Context

Chat A R3 refactored LifecyclePhase 1 (task interpretation) into an explicit 5-step flow so that mapping becomes auditable and learnable. The steps invoke L3 capacities (`process.*`, `hint.*`, `decision.derive_goal`, the mapping subsystem) whose **production bodies ship in WSD installation**. Phase 47 must run the control flow end-to-end with no real catalog.

## Decision

### 1. Five steps (Chat A R3, Method δ)

```
1. receive(task_input)                                   → raw
2. process_input(raw)            [L3 process.*]           → structured_input
3. extract_hints(structured_input) [L3 hint.* global]    → hint_set      → HintSet
4. derive_goal(structured_input, hint_set) [L3 decision.derive_goal] → goal
5. map_to_task_pattern(structured_input, hint_set, goal) → (task_pattern, mapping_confidence)
     5a shape-index candidate lookup
     5b per-candidate declared hints (Method δ)
     5c mapping subsystem #4 confidence
     5d dont-know on low confidence / no candidate
                                                          → MappingResult
```

Phase 1 emits **HintSet** (Level 1 chain artifact) at step 3 and **MappingResult** (Level 2) at step 5, both to intelligence-MM (Chat B chain).

### 2. Method δ — hybrid hint extraction

A global always-on hint subset runs every Phase 1 (step 3); per-pattern declared hints (`relevant_hints` on the task-pattern) run per candidate (step 5b). Methods α/β/γ/ε deferred.

### 3. v0 catalog discipline (PB-C / PB-7)

The orchestrator dispatches ~13 L3 points whose bodies are WSD-install. Phase 47 ships them as **placeholder-marked v0 capacities** in three modules under `mindsos_capacity/builtins/`:

- `planning_v0.py` — `planning.derive_initial_plan` (single-Milestone Plan), `planning.decompose` (`[]`), `planning.is_leaf` (`True`), `planning.aggregate_outputs` (last-child-output).
- `phase1_v0.py` — `process.identity` (raw→structured passthrough), `hint.*` global empty-set stub, `decision.derive_goal` (trivial goal), trivial mapping (fixed task-pattern).
- `orchestration_v0.py` — `decision.signal_to_tier`, `scoring.attention_score` (cold-start constants from `tiers.DEFAULT_TIER_SCORES`), `decision.should_replan`, `predicate.sufficient`, `phase6.attribute_blame`.

Every v0 capacity carries a `placeholder=True` registration marker and a guard that rejects production (non-test) invocation. **WSD installation atomically replaces the v0 catalog** with real capacities (Phase 45 dream-family precedent: ship v1 placeholders, downstream installation extends).

**Stub verdicts are test-configurable.** `decision.should_replan` and `predicate.sufficient` stubs accept an injected verdict so the **ReplanRecord + invalidate-at-and-below path (ADR-0173) and the dont-know path are exercised** — constant stubs would dead-ship those paths.

## Rationale

- **Explicit hint extraction before mapping** makes mapping auditable (HintSet on the MM) and gives ALS subsystem #10 / #4 a calibration target.
- **One coherent v0 catalog** (not scattered per-family) gives a uniform placeholder guard and a single replacement seam for WSD.
- **Test-configurable verdicts** close the coverage gap the constant-stub trap creates.

## Consequences

- Phase 47's trivial-task smoke runs the real 5-step path against v0 stubs.
- WSD installation replaces all three v0 modules atomically.
- HintSet + MappingResult chain artifacts are emitted at 47 (consumed by Phase 48 episodes).

## Alternatives considered

1. **Inject a pre-mapped task; skip Phase-1 L3 calls (PB-7 Opt B).** Rejected — Phase 1's success path stays untested at 47.
2. **Scatter stubs per family with constant verdicts (PB-C Opt B).** Rejected — dead-ships the replan/dont-know paths; no uniform guard.

## §v2-reservations

- Methods α/β/γ/ε hint-extraction strategies.

## §Implementation (Phase 47; pending ship)

`phase_1.py` (5-step) + the three v0 builtin modules + `tests/phase_47/test_phase_1_5_step.py` + `test_planning_v0_catalog.py`.

---

## Amendments

### amendment-2 (2026-08-21, planning-design-pointer lane) — ADR-0206 amends this ADR

**Amendment status:** Proposed. It flips with ADR-0206 itself. The items that build it are
**CORE-C4R3** (`planning.decompose` + `decision.select_decomposition`) and **CORE-C4R7**
(interpretation contracts; every `placeholder=True` deleted), per
`confirmation_docs/CORE_RECONCILIATION_PLAN.md` §5.

**Trigger.** On 2026-08-20 a consumer lane asked how an input enters MindsOS and what
decides what to do with it. It searched the tree thoroughly and answered, with file:line
evidence, `process → hint → derive_goal → map` — this ADR's flow, as implemented in
`phase_1.py`. The answer was shipped, coherent, Accepted, and one design generation out of
date; the lane acted on it. Nothing in the code or in the published concept docs said so.
This amendment is the pointer that was missing.

**What ADR-0206 does to each clause above.**

| This ADR | ADR-0206 |
|---|---|
| §1 five steps | **Revised.** §3 makes the steps `request → hint → map → plan`; `derive_goal` is deleted and *plan* becomes a loop. §1's step-5 internals — 5a shape-index candidate lookup, 5b per-candidate declared hints, 5c mapping confidence, 5d dont-know-on-low-confidence — are neither kept nor named: §7 inverts the matching (*"requests do not match patterns — hints are patterns and are what get matched"*), §5 replaces the single `mapping_confidence` with a confidence **per transition**, and §6 splits *"I'm not sure"* from *"I don't know"*. |
| §2 Method δ | **Not named by ADR-0206** — it contains no "Method δ". §8 ships interpretation as **contract only** (bodies arrive in skill packages), which moves δ's owner without deciding δ. Treat δ as open, not retired. |
| §3 v0 catalog discipline | **Deleted.** §8: the thirteen `placeholder=True` capacities are removed, not kept as fixtures; the Phase-50 reference bundle becomes the canonical test fixture. Alternative 6 rejects keeping them and names this catalog as *"how the placeholders came to be mistaken for the plan."* |
| §v2-reservations (methods α/β/γ/ε) | Untouched. |
| `0172-amendment-1` (separate file, Accepted, shipped) | Untouched by ADR-0206. Its `PlanResult.solve_target` endpoint dict is collapsed into the milestone tree by **CORE-C2R6**, not by ADR-0206's text. |

**Why the status is not `Superseded`.** `RULES.md` §9 allows two words and states the rule:
a contradicted ADR flips to `Proposed` (new form decided, not built) or `Superseded`
(decision wholly replaced), and *"where an ADR is shipped and only partly wrong, leave it
`Accepted` and let the amendment carry `Proposed`, naming the CR that flips it."* Three
facts put this ADR there:

1. **The replacement is unbuilt.** ADR-0206 is `Proposed`; CORE-C4 has not started; the
   thirteen placeholders are registered and running the gate. Marking this `Superseded`
   today would leave **no Accepted ADR describing the code that runs** — the same defect
   this amendment closes, pointing the other way. The tree's precedent is to flip on ship:
   ADR-0007 (*"2026-05-22 — Phase 24 ship … close the supersession in code"*) and ADR-0037.
2. **The flow is jointly owned.** ADR-0195 (Accepted, shipped) factored it into
   `interpret()`; ADR-0197 (Accepted, shipped, `amends: [0195]`) re-specified ingress on top
   of it. ADR-0206 supersedes neither — ADR-0197 is not even in its `related:` list.
   Superseding this ADR orphans two Accepted, shipped ADRs that build on it.
3. **§2 survives.** A clause the replacement never names is not wholly replaced.

**The flip list — what changes when ADR-0206 becomes `Accepted`.** Recorded here so the
flip is one commit and not another archaeology pass:

1. this ADR — front-matter `status:`, the prose `**Status:**` line, the ⚠ note above, and
   this amendment's status. (RULES §9: an ADR-level status change is **four** edits —
   front-matter, prose, the `docs/decisions/adr/README.md` row, and any summary-table cell.)
2. `docs/decisions/superseded.md` — the 0172 row moves from *Amendments in flight* to
   *Effective supersessions*.
3. `docs/concepts/planning.md` and `docs/concepts/task-lifecycle.md` — the banners stop
   saying "not yet built".
4. the module docstrings naming this ADR as the shipped-but-amended implementation:
   `phase_1.py`, `plan_construction.py`, `planning_v0.py`, `phase1_v0.py`,
   `orchestration_v0.py`, `phase1_profile.py`, `phase1_text.py`.
5. `tests/architecture/test_retired_design_pointer.py` — `RETIRED` loses any token whose
   code is gone by then.
