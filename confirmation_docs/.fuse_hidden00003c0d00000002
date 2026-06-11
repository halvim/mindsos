# PHASE_47_DESIGN_LOG — L4 orchestrator: six-phase lifecycle + planning.* v0

**Chat:** Phase 47 (first L4 control-flow code — makes the Phase-46 substrate
*run*). PHASE_MAP estimate ~600–900 LOC + 3–5 ADRs, **plus** the corpus-wide
S12 `invoke`→CapacityContext flip Phase 46 deferred. **Design-pass first, then
ship** — ship shape is itself a pushback (PB-0; do NOT assume option-C combined).

**Status:** R0 open (design saturation). **No code written, no branch cut.**
Pre-impl pushback rounds (budget 2–3 per PHASE_43 §10.4) + a buildability scan
precede branching `phase-47`.

**Rail context:** All four Stream B rails + the Phase-46 convergence closed.
Phase 47 consumes the L4 substrate (`mindsos_intelligence`) + the deferred
surfaces (S12/PB-23, signal classifier, attention scorer, dream driver).
Phase 48 (L5 v1) consumes what 47 emits (chain artifacts → episodes).

**Prereq check (run 2026-06-08):**
- `git tag --list | grep -E "phase-4[0-6]-confirmed"` → 40/41/42/43/44/45/46
  all present. ✔
- `main`-tip `3cdfc5a`; on `main`. Working tree dirty: `M
  docs/_workbench/L3_FUTURE_WORK.md` + untracked `confirmation_docs/ROBOT_DEMO_*`
  / `confirmation_docs/PHASE_4*_NEXT_CHAT_PROMPT.md` / `DEMO_*`. **Never
  `git add -A`; stage selectively; leave Robot Demo + next-chat-prompt files
  alone** (Phase 46 prereq lesson). Branch `phase-47` off `main`-tip `3cdfc5a`. ✔
- **VERSION BUMP REQUIRED:** slot 47 > high-water 46 → full **9-surface** bump
  46→47 (PHASE_MAP §1 high-water rule). Now **8** package `__version__` strings
  (`mindsos_intelligence` joined the manifest at Phase 46). **No new top-level
  package expected** → new-package checklist N/A; host `pip install -e .` refresh
  NOT needed (no-new-package phase). ✔
- **PB-Z reading-list (Phase-46 modules this phase touches):**
  `mindsos_intelligence/{executor.py,intelligence_layer.py,signal_triage.py,
  mm_resolver.py,als_registry.py}`, `mindsos_capacity/{runtime.py,
  capacity_layer.py,context.py,tiers.py}`, `builtins/{consolidate.py,trace.py,
  dream.py}`. Read at R1 step 0 alongside the ADR transcription-parity probe.

---

## §0. Required-reading acknowledgement

- HANDOFF §1, §3.1.5 (Chat A closure — L4-vs-L3 line + Push 2 action contracts),
  §3.1.7 (Chat C plan), §3.1.19 (Phase 46 ship — substrate consumed +
  carry-forward list), §4/§4.1/§4.2 (L5 settled — 6-level chain + Plan-tree +
  planning.* family), §9 (process discipline: python3 host, pair-execution,
  squash-before-confirm, tag-at-confirm-artifacts-commit, docker rebuild).
- POST_PHASE_38_PHASE_MAP §0, §1 (DAG + high-water rule + 9-surface checklist +
  PB-L v0-catalog discipline), the Phase 47 detail block (lines 735–822), §6.
- PHASE_46_DESIGN_LOG §9 (authoritative carry-forward list) + §0 (process
  precedents: S-surface saturation, R1-step-0 transcription-parity probe,
  ground-first consumer-discipline rule).
- CHAT_A_DECISIONS: D12 (six-phase + simplified mode), Phase-1 5-step refactor +
  Method δ (lines 658–711), Push 2 (action contracts via predicate-capacity
  IRIs), D13 (Phase 6 + cross-val budget K=2), D14 (ReplanRecord + ReplanVerdict),
  D9.1–D9.7 (ALS 10-subsystem list + signal sources), the L4-vs-L3 strict line
  (lines 257–284), the L3-33 decision/scoring family.
- CHAT_B_DECISIONS: D-B22 (6-level chain) + D-B23 (Plan = recursive Milestone
  tree; planning.* 4-capacity family) + D-B30 (TaskRun) + D-B36 (replan model,
  invalidate-at-and-below) + D-B51 (10th signal source) + D-B52 (11th ALS
  subsystem).
- l5_mental_model_design_notes §1–§2 (sub-MM + the 8 chain-artifact schemas) +
  §3 (LifecyclePhase 1-6) + §4 (consolidation — Phase 48 boundary).

---

## §1. Design ground truth (implement; do NOT re-litigate)

From Chat A R1–R5 + Chat B chain + the PHASE_MAP Phase 47 Locked-decisions row:

- **Six-phase task lifecycle (D12).** Production path = LifecyclePhase 1→6.
  Simplified mode (`--bypass-lifecycle`) bypasses goal-verification +
  consolidation + ALS emission — dev/test only.
- **Phase 1 = 5 steps (Chat A R3, Method δ):** receive → `process.*` →
  `hint.*` extract (global always-on subset) → `decision.derive_goal` →
  `map_to_task_pattern` (candidate shape-index → per-pattern hints 5b →
  mapping subsystem #4 confidence → dont-know on low confidence/no candidate).
  Produces **HintSet + MappingResult**.
- **Phase 2 = Plan + Pipeline construction (D-B22/D-B23):** Plan is a recursive
  **Milestone tree** (single-parent v1); lazy decomposition (children derived
  when Milestone becomes active); cold-start **max-depth = 3** admin-tunable;
  per-leaf Pipeline via `pipeline_finder.from_milestone`.
- **Phase 3–5 = execution:** DFS Milestone order via `sequence_index`; sibling
  sequential v1; child-failure → fail-fast v1; aggregator default =
  last-child-output. MSUR + SCMS are **L3 orchestration capacities** (bodies =
  WSD installation; 47 ships dispatch only).
- **Phase 6 = failure diagnosis (D13):** `phase6.attribute_blame` skeleton
  emits **BlameVerdict** (`chain_level` ∈ {hint,map,plan,plan_subtree,pipeline}
  + milestone_ref + capacity_step_ref + blame_score + rationale). Cross-val
  budget K=2 admin-tunable. Concrete body = WSD installation.
- **Replan-check (D14 + D-B36):** `decision.should_replan` dispatch →
  `ReplanVerdict(decision, verified, divergence)`; **ReplanRecord emitted
  sparsely** (only on `replan`/`abort`); replan **invalidates artifacts at and
  below the replan level**, reuses upstream. `replan_level` ∈
  {hint,map,plan,plan_subtree,pipeline}. Budgets: per_milestone=2, per_task=5.
- **Sufficient-predicate (D41):** dispatch `predicate.sufficient(state,
  task_pattern)`; per-pattern predicate IRI accepts multi-candidate success.
- **`planning.*` v0 placeholder catalog (PB-L):** 4 L3 capacities —
  `derive_initial_plan` → single-Milestone Plan; `decompose` → `[]`; `is_leaf`
  → `True`; `aggregate_outputs` → last-child-output. **Marked placeholder in
  registration metadata + guarded against v1-prod use.** WSD installation
  atomically replaces.
- **10 signal-source skeletons** (S1–S10; S7 reserved): S1 self_distillation,
  S2 gold_anchor, S3 fol_disagreement, S4 ensemble_agreement, S5 hitl,
  S6 task_outcome, S8 replan_divergence, S9 mutation_frequency,
  S10 plan_decomposition_outcome (D-B51). Empty payload contracts.
- **11 ALS subsystem skeletons** (Chat A 10 + Chat B #11 planning-decomposition
  calibration). Empty mechanism + validator pointers; filled by WSD install.
- **8 chain-artifact composites emitted to intelligence-MM** (D-B22…D-B37):
  HintSet, MappingResult, Plan(+Milestone), Pipeline, PipelineRun, TaskRun,
  ReplanRecord, StepExecutionRecord. Schemas = l5 notes §2 as-written.
- **L4-vs-L3 strict line.** L4 = data-structure mutations, state-machine
  transitions, lock arbitration, lifecycle, threading, **dispatch**. Every
  decision/computation is an L3 capacity invocation. Predicates ARE capacities
  (Push 2: `precondition_iri`/`effect_iri` are predicate-capacity IRIs).

---

## §2. S-surface enumeration (L4 orchestrator)

Mirror of the Phase 42/44/45/46 S-surface format. Each surface tagged with its
**real consumer** (consumer-discipline test). Surfaces whose only consumer is
Phase 48 are deferral candidates (see §3 forks).

| S | Surface | Module | Real consumer | Ship at 47? |
|---|---|---|---|---|
| **S1** | Six-phase lifecycle state machine (`LifecyclePhase` enum + transition table; replan re-entry) | `mindsos_intelligence/orchestrator.py` | enqueue→run; Phase 47 smoke | **Yes** |
| **S2** | Phase 1 5-step refactor (receive→process→extract_hints→derive_goal→map) → HintSet + MappingResult emit | `phase_1.py` | S1; smoke | **Yes (control-flow; L3 catalog stubbed — see PB-7)** |
| **S3** | Phase 2 Plan + Pipeline construction (recursive Milestone tree, lazy decompose, max-depth=3, pipeline_finder) | `plan_construction.py` | S1; smoke | **Yes (over planning.* v0)** |
| **S4** | Phase 3–5 DFS execution (PipelineRun spawn in DFS order; MSUR/SCMS dispatch) | `execution.py` | S1; smoke | **Yes (dispatch; bodies = WSD)** |
| **S5** | Phase 6 failure diagnosis hookup (`phase6.attribute_blame` dispatch → BlameVerdict) | `phase_6.py` | S1 failure path | **Yes (skeleton; body = WSD)** |
| **S6** | Replan-check dispatch + ReplanRecord emit (`decision.should_replan`; invalidate-at-and-below) | `replan_check.py` | S1/S4 | **Yes (dispatch; body = WSD)** |
| **S7** | Sufficient-predicate evaluator (`predicate.sufficient` dispatch) | `sufficient_predicate.py` | S4 | **Yes (dispatch)** |
| **S8** | `planning.*` v0 catalog (4 placeholder L3 capacities + metadata guard) | `mindsos_capacity/builtins/planning_v0.py` | S3 | **Yes** |
| **S9** | 10 signal-source registration skeletons (empty payload contracts) | `signal_sources.py` | WSD install; smoke registration test | **Yes (registration only)** |
| **S10** | 11 ALS subsystem registration skeletons (empty mechanism/validator pointers) | `als_subsystems.py` | WSD install | **Yes (registration only)** |
| **S11** | 8 chain-artifact composite emit to intelligence-MM | `chain_artifacts.py` | S1–S6; Phase 48 consolidation | **Yes** |
| **S12** | **PB-23 carry:** `invoke`→CapacityContext signature flip + consolidate/trace body migration + write-body capability gate (ADR-0170 enforce) | `mindsos_capacity/runtime.py` + `capacity_layer.py` + bodies + L4 dispatch | **orchestrator capacity dispatch = 47** | **Yes (corpus-wide; see PB-1/PB-2)** |
| **S13** | L3 `decision.signal_to_tier` capacity (replaces Phase-46 passthrough stub) | `mindsos_capacity/builtins/` + `signal_triage.py` swap | signal-triage thread | **Yes** |
| **S14** | L3 `scoring.attention_score` (learnable, cold-start constants) + L4 `update_priority` wrapper + ALS S9 wiring | `builtins/` + `executor.py`/`intelligence_layer.py` | priority queue; TaskRun write-through (PB-6) | **Yes (queue); write-through = PB-6 fork** |
| **S15** | ~~Dream driver — DreamCycleTimer callback~~ | `intelligence_layer.py` | episodes = Phase 48 corpus | **DEFERRED WHOLESALE → 48 (PB-3 ratified)** |
| **S16** | 3–5 new ADRs 0171–0175 | `docs/decisions/adr/` | ratification | **Yes (count = PB-7)** |
| **S17** | 9-surface version bump 46→47 (8×`__version__`) | manifest/pyproject/8×version/compose/export-slate | release | **Yes** |
| **S18** | Docs: `task-lifecycle.md` + `replan.md` + `planning.md` (NEW) | docs/concepts | confirm | **Yes** |

---

## §3. Genuine design forks (pushbacks — options + pick)

Provisional picks; pre-impl rounds (§5) may revise.

### PB-0 — Ship shape (HEADLINE)

**Concern.** Phase 47 = a large control-flow surface (orchestrator + 6 phase
modules + chain emit + 2 v0/skeleton catalogs) **plus** the corpus-wide S12
`invoke`→CapacityContext flip. The S12 flip is high-blast-radius (every dict-
context call site + the 2 bodies + a gate). Mixing it into the orchestrator PR
makes the gate failure surface ambiguous. Phase 46 collapsed two PRs to one
*because its deferred surfaces had no consumer* — the inverse holds here: S12's
consumer **is** the orchestrator, so S12 must land first **within** the branch.

- **Opt A — single monolithic PR.** Pros: one gate/confirm. Cons: corpus-wide
  signature flip + 900 LOC orchestrator in one review; ambiguous gate blame.
- **Opt B — two PRs on `phase-47`, single confirm (Recommended).**
  PR-A = S12 corpus migration (invoke→CapacityContext + 2 bodies + write-gate
  in L4 dispatch) + the v0/skeleton catalogs (S8/S9/S10/S13/S14-queue) + the
  L3 capacities, landed + gate-clean first. PR-B = the orchestrator + 6 phase
  modules + chain-artifact emit + dream driver + smoke, built on the migrated
  signature. One version bump + one tag at confirm.
  Pros: corpus flip gates clean before the state machine layers on; bounded
  reviews; matches the "S12 first" sequencing requirement.
  Cons: two gate cycles; intermediate branch state.
- **Opt C — single PR but S12 deferred again.** Cons: orchestrator can't invoke
  capacities with a typed context; re-opens PB-23 a third time; not viable.

**Pick: Opt B.** S12 is the dependency root; isolating it de-risks the gate.
**Open question for the user:** is even PR-B too large — should the dream driver
(S15) or Phase 6 (S5) split to a PR-C? (Lean no; they're skeletons.)

### PB-1 — S12 `invoke`→CapacityContext migration strategy (corpus-wide)

**Concern.** Shipped `runtime.invoke(decl, inputs, *, context:
Optional[Mapping[str,Any]]=None, ...)` is consumed corpus-wide; `capacity_layer.
invoke` wraps it. Bodies `consolidate.py:136` + `trace.py:119` read
`context.get("kl")`. CapacityContext (Phase 42, frozen, 10 fields:
session_id/user_id/learned_parameters_snapshot/mm_handle/cancel_token/…) is
**caller-built**, not invoke-built (invoke has no session/mm_handle).

- **Opt A — hard flip (Recommended).** Change `context` type to
  `Optional[CapacityContext]`; migrate the 2 bodies to `context.kl`; migrate
  every call site (census first). The orchestrator builds the CapacityContext;
  invoke just threads it. Consumer discipline: the only *production* caller is
  the L4 lifecycle (runtime docstring already names it the canonical caller);
  the rest are tests. Budget gate-driven follow-ups.
  Pros: single clean contract; no lingering dual path; PB-23 closes for good.
  Cons: atomic corpus change; test-fixture churn.
- **Opt B — transitional union (`Mapping | CapacityContext`) + body shim.**
  Pros: no atomic flip. Cons: dual contract lingers; bodies need isinstance
  branching; the exact thing PB-23 exists to remove.
- **Opt C — new `cap_context` param alongside deprecated `context`.** Cons: two
  params for one concept; worse than B.

**Pick: Opt A.** R1 step-0 must run a **call-site census** (`grep` for
`invoke(` + `context=` across `mindsos_*`/`tests*`) to size the blast radius
before locking. If the census shows >~40 sites the user may prefer B as a
staging step — decide at R1 with the real number.

### PB-2 — Write-body capability gate home (ADR-0170 enforcement)

**Concern.** ADR-0170 drafted the gate as "L4 dispatch reads session from
IntelligenceLayer; CapacityContext stays authorization-free." Phase 47 enforces
it. Where does the gate physically live?

- **Opt A — new `mindsos_intelligence/dispatch.py` invoke-wrapper (Recommended).**
  L4 wrapper: build CapacityContext (session_id/user_id from IntelligenceLayer,
  mm_handle, cancel_token, learned_parameters_snapshot) → if the declaration is
  a write-body (zero outputs) check the session's capability → call
  `runtime.invoke`. All orchestrator capacity calls route through it.
  Pros: single choke point; gate + context-build co-located; L3 stays
  authorization-free per the strict line.
  Cons: one more module; every phase module imports it.
- **Opt B — gate inside `runtime.invoke`.** Cons: L3 has no session/capability
  handle — the whole reason ADR-0170 put it in L4. Rejected.

**Pick: Opt A.** Document the capability-check stub shape (real capability
catalog = Server/WSD; 47 gates against a present-or-absent capability set).

### PB-3 — Dream driver 47/48 split (S15)

**Concern.** The carry-forward says 47 ships the DreamCycleTimer callback that
reads `DreamCapacity.execution_policy`/`entry_point`, invokes dream bodies for
DreamDirectives, and enqueues a DREAM-tier task through the phase-loop. **But
the dream corpus — episodes — does not exist until Phase 48 consolidation.** A
dream re-executes a *loaded episode via MM deep-copy*; with no episodes, there
is nothing to load.

- **Opt A — ship the driver *wiring* at 47, exercised with a synthetic
  directive (Recommended).** Timer callback → read DreamCapacity policy/entry_
  point → build a DreamDirective → enqueue a DREAM-tier task that enters the
  phase-loop. Tested with a stub/synthetic directive (no episode corpus). DEFER
  to 48: episode load + MM deep-copy materialise as live re-execution + ALS
  firing + ReplanInjectionDirective consumption.
  Pros: the timer→enqueue→phase-loop path is genuine substrate, testable now;
  decision/corpus content defers to its consumer (Phase 48 episodes).
  Cons: the driver's first *real* action (load episode) is Phase 48; 47 ships
  thin.
- **Opt B — defer the whole dream driver to Phase 48.**
  Pros: cleanest 47; the driver's corpus is Phase-48 anyway. Cons: the
  timer→enqueue→phase-loop wiring is substrate other tests want; leaves S15
  fully open across two phases.

**Pick: Opt A** (ship wiring, defer corpus behavior) — **but this is a genuine
47/48 boundary call the prompt asks me to confirm at R0.** If the user prefers
minimal 47, Opt B is clean since episodes are Phase 48. **User ratification
requested.**

### PB-6 — `attention_score` MM write-through: 47 or 48? (Phase-46 PB-11 conflict)

**Concern — a documented contradiction.** Phase 46 PB-11 deferred
`attention_score` MM write-through to **Phase 48** on the stated grounds that
"it writes to the TaskRun composite, a **Phase-48** chain artifact." **But the
PHASE_MAP Phase 47 row lists `TaskRun … composite emit` AND `Attention-score-on-
TaskRun (D32.5c.4)` in Phase 47 scope.** TaskRun ships at **47**, not 48 — so
the write-through *target* exists at 47, invalidating PB-11's premise.

- **Opt A — write-through lands at 47 (Recommended; follows PHASE_MAP).** The L4
  `update_priority` wrapper invokes `scoring.attention_score` → writes the queue
  priority **and** writes through to `TaskRun.attention_score` under the MM
  writer lock. TaskRun exists (S11). Corrects Phase-46 PB-11 as an as-shipped
  delta.
  Pros: PHASE_MAP-faithful; no orphaned `attention_score` field on the TaskRun
  ships at 47; single coherent surface.
  Cons: contradicts the Phase-46 §9 carry-forward note (which listed write-
  through under Phase 48) — record the reversal explicitly.
- **Opt B — queue-only at 47; write-through to TaskRun at 48 (follows Phase-46
  §9 carry-forward).**
  Pros: honors the literal Phase-46 carry-forward text. Cons: TaskRun ships at
  47 with a written-but-never-updated `attention_score`; splits one surface
  across two phases for no consumer reason.

**Pick: Opt A**, flagged as a **Phase-46 PB-11 reversal** (TaskRun moved earlier
than PB-11 assumed). **User ratification requested** — this is a real
cross-phase boundary correction, not a free call.

### PB-7 — Phase-1 smoke when `process.*`/`hint.*`/`derive_goal`/`mapping` are WSD-install artifacts

**Concern.** Phase 1's 5 steps invoke L3 `process.*`, `hint.*`,
`decision.derive_goal`, and the mapping subsystem — **none of which ship until
WSD installation.** The PHASE_MAP trivial-task smoke says "Phase 1–5 …
control-flow only." With no Phase-1 capacities registered, what does step 2–5
invoke?

- **Opt A — ship trivial v0 stubs for the Phase-1 capacities too (Recommended).**
  Alongside `planning.*` v0: a single `process.identity` (raw→structured
  passthrough), a `hint.*` empty-set global stub, `decision.derive_goal` →
  trivial goal, and a trivial mapping that returns a fixed task-pattern. All
  placeholder-marked, WSD replaces. The smoke runs real control flow end-to-end.
  Pros: smoke exercises the actual 5-step path; v0-discipline already exists
  for planning.*. Cons: widens the v0 catalog beyond the PHASE_MAP's literal
  "4 planning.* capacities."
- **Opt B — smoke injects a pre-mapped task (skip Phase 1 L3 calls).** Pros: no
  extra v0 capacities. Cons: Phase 1 control flow is then untested by the smoke;
  contradicts "Phase 1–5."
- **Opt C — Phase 1 graceful dont-know when no `process.*` registered.** Pros:
  exercises the dont-know path. Cons: the *success* path of Phase 1 stays
  untested at 47.

**Pick: Opt A** (minimal Phase-1 v0 stubs), recorded as a PHASE_MAP scope
delta. **User input wanted** — this expands the v0 catalog; confirm it's
acceptable vs Opt B's thinner smoke.

### PB-4 — Six-phase lifecycle structure (minor)

**Pick:** `orchestrator.py` owns a `LifecyclePhase` enum (1–6) + a transition
table; each phase delegates to its module (`phase_1`/`plan_construction`/
`execution`/`phase_6`). Replan re-enters at the invalidate level (D-B36).
Matches the PHASE_MAP module list; not a real fork.

### PB-5 — `planning.*` v0 home + placeholder discipline (minor)

**Pick:** `mindsos_capacity/builtins/planning_v0.py` (L3), registered with a
`placeholder=True` (or category-marker) guard that raises/warns on v1-prod
invocation outside the smoke. DreamCapacity-builtin precedent. Not a real fork;
confirm the guard mechanism at R1.

### PB-7-ADR — ADR count + numbering

**Pick (provisional):** 5 ADRs 0171–0175 — 0171 six-phase lifecycle +
simplified mode; 0172 Phase-1 5-step refactor + Method δ; 0173 replan-check
verdict + invalidate-at-and-below + ReplanRecord sparsity; 0174 sufficient-
predicate + Phase-6 BlameVerdict dispatch; 0175 `invoke`→CapacityContext flip +
write-body gate enforcement (amends ADR-0146/0159/0170). Lock count/numbering
at R1 after the transcription-parity probe.

---

## §4. Carry-forward consumption map (Phase 46 §9 → 47)

| Source | Carry | Phase 47 disposition |
|---|---|---|
| §9 / S12 / PB-23 | `invoke`→CapacityContext + consolidate/trace body migration + write-gate (ADR-0170) | **S12 — ship (PB-1 hard flip; PB-2 gate in L4 dispatch); PR-A** |
| §9 signal classifier | L3 `decision.signal_to_tier` replaces passthrough stub | **S13 — ship; swap in signal_triage** |
| §9 attention scorer | L3 `scoring.attention_score` + `update_priority` wrapper + ALS S9 | **S14 — ship queue path; write-through = PB-6 (→47, reversing PB-11)** |
| §9 dream driver | timer callback → DreamDirective → DREAM-tier task thru phase-loop | **S15 — split (PB-3): wiring now; episode re-exec/ALS/replan → 48** |
| §9 (Phase 48) | MM `attention_score` write-through to TaskRun | **PB-6 reversal candidate — likely 47 (TaskRun ships at 47)** |
| §9 (Phase 48) | dream live re-execution + ALS firing + replan-injection; inline-on-retire (D'1) | **stays Phase 48** |

---

## §5. Pre-impl pushback rounds (saturation tracker)

Budget 2–3 rounds (PHASE_43 §10.4) + a buildability scan before branching.
Saturation signature = a round producing impl-locks only, zero reversals.

- **Round 1 — CLOSED 2026-06-08.** Forks PB-0…PB-7-ADR surfaced with picks.
  User ratified the cross-phase boundary calls:
  - **PB-6 = Opt A** (attention_score write-through lands at **47**, reversing
    Phase-46 PB-11 — TaskRun ships at 47 per the PHASE_MAP row, so PB-11's
    "Phase-48 target" premise is false). ✔
  - **PB-3 = Opt B** (dream driver **deferred wholesale to Phase 48** — episodes,
    the dream corpus, are a Phase-48 artifact; the timer→enqueue wiring has no
    corpus to act on at 47). **S15 drops from Phase 47 entirely.** ✔
  - **PB-7 = Opt A** (add minimal Phase-1 v0 stubs so the smoke runs the real
    5-step path). ✔
  - **PB-0 = Opt B** (two PRs, single confirm) — user delegated; picked two PRs
    on S12-blast-radius grounds. PR-A = S12 migration + v0/skeleton catalogs +
    L3 capacities; PR-B = orchestrator + 6 phase modules + chain emit + smoke.
    With S15 deferred, no PR-C. ✔
  - PB-1/PB-2/PB-4/PB-5/PB-7-ADR picks **stand**; open to contest in Round 2.
- **Round 2 — CLOSED 2026-06-08 (grounding probe + skeptical pass; ZERO design
  reversals → saturation signature; impl-locks only).** See §6 for the probe.
  - **PB-1 CONFIRMED + sized.** S12 call-site census: blast radius = **2
    production bodies** (`consolidate.py:136`, `trace.py:119` read
    `context.get("kl")`) + the `capacity_layer` write-path (`157/577/580/588`,
    `context["kl"]`/`context.get("kl")`) + `runtime.py:218` (`call_capacity(…,
    context=context)`) + **2 test files** (`tests/phase_30/test_invoke_session_
    user_id_in_context.py`, `tests/phase_33/test_invoke_session_context_
    injection.py`) that inject session via dict keys. Well under the ~40-site
    threshold → **hard flip (Opt A) safe.** Impl-locks: (a) `CapacityContext`
    is **caller-built**, `invoke` just threads it (it has no session/mm_handle
    to construct one); (b) the 2 session-injection tests migrate from
    `context={"session_user_id":…}`/`{"session":sentinel}` dicts to building a
    `CapacityContext` (session_id/user_id are already typed fields); (c) `text.*`
    bodies pass `context=context` through to helpers but don't read `kl` (Phase-46
    probe) → no migration.
  - **PB-2 CONFIRMED.** ADR-0170 §Decision is exact: gate at **L4 dispatch**
    checks the capacity's declared `effect_iri` (ADR-0159) against the
    **IntelligenceLayer session-held granted-capability set**; `CapacityContext`
    stays authorization-free (10 fields confirmed: session_id, user_id,
    learned_parameters_snapshot, mm_handle, cancel_token, current_task_iri,
    current_pattern_iri, version_snapshot, kl, cl). Impl-lock: gate in
    `mindsos_intelligence/dispatch.py`; reads `effect_iri`. **IMPL FLAG:** the
    granted-capability *set source* — Server owns capabilities (ADR-0010 forbids
    L3 reaching Server; L4 may). If Server-session capability wiring isn't
    threaded into IntelligenceLayer at 47, the gate checks against a
    present-or-absent set passed at `start()`; real catalog = Server/WSD.
    Resolve at impl against the shipped `IntelligenceLayer.start` signature.
  - **PB-6 impl-lock.** `update_priority(task_id, context)` wrapper: invoke
    `scoring.attention_score` → `executor.write_priority` (queue) **and** write
    `TaskRun.attention_score` through the MM-root writer lock (TaskRun exists at
    47 via S11). Both writes under one lock acquisition (D32.5c.4 atomicity).
  - **PB-7 impl-lock (module naming).** Phase-1 v0 stubs split from planning:
    `builtins/planning_v0.py` (4 planning.* capacities) +
    `builtins/phase1_v0.py` (`process.identity` raw→structured passthrough,
    `hint.*` global empty-set stub, `decision.derive_goal` trivial goal, trivial
    mapping returning a fixed task-pattern). All `placeholder=True`-marked +
    v1-prod invocation guard. Confirm guard mechanism vs DreamCapacity-builtin
    precedent at R1.
  - **Consolidation seam (D12 / smoke).** Real MM-consolidation is Phase 48;
    the orchestrator's Phase-5→complete consolidation hook ships as a **stub/
    no-op** at 47 (PHASE_MAP smoke = "L5 stub-consolidate"). Clean seam; Phase 48
    fills it. Not a fork.
  - **Buildability scan.** L4→L3 imports are downward (orchestrator/dispatch
    import `runtime.invoke` + `CapacityContext` from `mindsos_capacity`;
    planning_v0/phase1_v0 are L3 builtins). No new top-level package; no cycle.
    Clean.
  - **No design pick reversed.** PB-0/1/2/3/4/5/6/7/7-ADR all stand.
- **Round 3 — CLOSED 2026-06-08 (skeptical re-pass; 3 important pushbacks,
  user-ratified; refines ship mechanics + closes 2 test-coverage gaps; ZERO
  design reversals).**
  - **PB-A — REFINED PB-0.** "Two PRs / two full gates" is not worth the second
    ~30-min docker cycle (Phase-46 collapse precedent). **One branch, S12-first
    commit order, a *targeted* L3/capacity test run right after the flip
    (`pytest mindsos_capacity tests/phase_3x`), full cumulative gate only at
    confirm.** Earns the S12-blast-radius discipline without a second full gate.
    (PB-0's "two PRs" is retained as a *logical* PR-A/PR-B commit split on one
    branch, not two gate cycles.)
  - **PB-C — NEW (structural).** The orchestrator dispatches ~13 L3 points whose
    bodies are all WSD-install (planning ×4, phase1 ×4, `decision.signal_to_tier`,
    `scoring.attention_score`, `decision.should_replan`, `predicate.sufficient`,
    `phase6.attribute_blame`). Ship them as **one coherent placeholder-marked v0
    catalog** (`planning_v0.py` + `phase1_v0.py` + `orchestration_v0.py`, shared
    guard) with **test-configurable stub verdicts** — `should_replan`/`sufficient`
    must be forceable to `replan`/`abort`/`false` so the **ReplanRecord +
    invalidate-at-and-below path and the dont-know path are exercised** (the
    PB-7 trap, generalized: constant stubs dead-ship the replan/dont-know paths).
  - **PB-D — NEW (consumer-discipline vs ADR-0170).** The write-body capability
    gate guards the zero-output capacity path; at 47 the only write-body
    (consolidation) is stubbed → no production write-body-under-session traffic.
    Pure consumer discipline would defer enforcement to Phase 48; but ADR-0170
    §Decision-2 committed enforcement to 47 and PB-23 has slipped twice.
    **Resolution: ship the gate in `dispatch.py` at 47 (zero extra cost — the
    module exists for context-building) + a dedicated synthetic test** (throwaway
    write-body capacity dispatched with/without the capability). A self-contained
    testable contract clears the Phase-46 "ship-ahead-of-consumer only if
    testable" bar — so this is *consistent* with the discipline, not a violation.
  - **Refinements (no fork):** `dispatch.py` lands in the **S12 commit** (not the
    orchestrator) so the migrated session-injection tests use the canonical
    CapacityContext-builder; Phase 3–5 execution at 47 = DFS pipeline run with
    **MSUR/SCMS as absent/skeleton hooks** (bodies = WSD; loop tolerates absence);
    Phase 6 + the 21 signal/ALS skeletons held to thinnest-possible registration.
- **Round 4 — CLOSED 2026-06-08 (grounding re-pass; 1 impl-lock + 1 minor scope
  pick; ZERO design reversals → saturation re-confirmed).**
  - **Lifecycle execution thread — GROUNDED (impl-lock).** Read the shipped
    Phase-46 substrate: `enqueue(task: Callable[[],object])` submits the closure
    to the **worker pool**; `IntelligenceLayer.start()` launches executor +
    signal-triage + dream timer but **no separate orchestrator main thread**. So
    a task's whole six-phase lifecycle runs **on the worker thread that dequeues
    it**, capacity invocations inline (sequential v1), chain artifacts written
    under the MM writer lock; per-task `cancel_token` on that worker drives
    cooperative cancel/preempt. **Diverges from Chat A D32's literal "orchestrator
    thread (main) owns phase transitions"** — Phase 46 shipped worker-per-task;
    the shipped substrate is authoritative. Impl-lock: orchestrator =
    `run_lifecycle(task_input, ctx)` enqueued as a closure; **ADR-0171 documents
    the D32 divergence.** (Simplifies replan/cancellation — no cross-thread
    phase coordination.)
  - **PB-E — NEW (minor scope).** Phase-46 §9 said "orchestrator CLI is Phase
    47" + D12 names `--bypass-lifecycle`; but the PHASE_MAP Phase 47 module list
    has no CLI file and all tests (incl. the smoke) are pytest. **Pick:
    library-only at 47** — lifecycle driven via API; the D12 simplified mode
    ships as an **API flag on `run_lifecycle`** (bypass goal-verification/
    consolidation/ALS); the **CLI verb is deferred** until an interactive
    consumer exists (consumer discipline). Recorded as a Phase-46 §9 scope
    clarification. User-ratified.

---

## §6. R1 step-0 grounding probe (run 2026-06-08 — read-only, pre-branch)

All design assumptions validated against shipped code. **Zero reversals.**

1. **S12 census** (above, PB-1) — small blast radius; hard flip safe.
   `CapacityContext` (`context.py`) frozen, 10 fields, caller-built.
2. **ADR-0170** (`docs/decisions/adr/0170-*.md`) — gate = L4 dispatch reads
   `effect_iri` vs session capability set; contract drafted, enforcement is
   Phase 47's (§Decision 2 names "Phase 47" explicitly). PB-2 Opt A holds.
3. **Shipped substrate** — `IntelligenceLayer.enqueue(task: Callable[[],object],
   *, tier, task_id, score)` (the orchestrator builds task closures);
   `PriorityTierExecutor.write_priority` (queue mutation, S14 consumes);
   `MMResolver.get_or_instantiate` IS the `MMHandle` (chain-artifact emit target);
   `DreamCycleTimer` exists but its callback is **unwired** (S15 defer is a
   no-op on the substrate — nothing to remove). `signal_triage.passthrough_
   classifier` present → S13 swaps it for `decision.signal_to_tier`.
   `als_registry.ALSSubsystemRegistry.register(key, registration)` present →
   S10 registers 11 skeletons; `ALSSubsystemRegistration` shape matches D9.1.
4. **ADR numbering** — highest = **0170** → 0171–0175 free (PB-7-ADR).
5. **Chain artifact schemas** — l5 notes §2 are the as-written shapes for the 8
   composites (HintSet/MappingResult/Plan+Milestone/Pipeline/PipelineRun/TaskRun/
   ReplanRecord/StepExecutionRecord). Impl-lock: `chain_artifacts.py` defines
   the shapes + emit helpers writing through the MM-root writer lock to
   intelligence-MM via the resolver.

**Net:** probe clean; impl-locks recorded (S12 caller-built context + 2-test
migration; PB-2 capability-set-source flag; PB-6 single-lock dual-write; PB-7
two v0 modules; consolidation stub seam; chain-artifact emit via resolver). No
design pick reversed.

---

## §7. Saturation status

**SATURATED 2026-06-08.** Round 1 (4 boundary/ship calls ratified) + Round 2
(grounding probe clean) + Round 3 (3 ship-mechanic/coverage pushbacks ratified)
+ Round 4 (lifecycle-thread grounding impl-lock + PB-E scope pick) — all
impl-locks/refinements, **zero design reversals across rounds 2–4** (the
PHASE_43 §10.4 saturation signature). Buildability scan clean.

**Locked picks:**
- **PB-0/PB-A** = one branch, logical PR-A/PR-B commit split, S12-first order,
  targeted L3 test after the flip, single cumulative gate at confirm.
- **PB-1** = hard flip `invoke`→CapacityContext (caller-built; census = 2 bodies
  + write-path + 2 tests).
- **PB-2/PB-D** = write-gate in L4 `dispatch.py` reading `effect_iri`; enforced
  at 47 + synthetic gate test.
- **PB-3** = dream driver deferred wholesale → Phase 48.
- **PB-4** = `LifecyclePhase` enum + transition table + per-phase modules;
  lifecycle runs on the dequeuing worker (Round-4 grounding; ADR-0171 documents
  the D32 divergence).
- **PB-5/PB-C** = one placeholder-guarded v0 catalog (`planning_v0` +
  `phase1_v0` + `orchestration_v0`) with test-configurable stub verdicts.
- **PB-6** = attention_score write-through at 47 under MM writer lock (reverses
  Phase-46 PB-11).
- **PB-7** = Phase-1 v0 stubs so the smoke runs the real 5-step path.
- **PB-E** = library-only at 47 (simplified mode = API flag; CLI verb deferred).
- **PB-7-ADR** = 5 ADRs 0171–0175.

**ADRs drafted at R0 (status Accepted; §Implementation "pending ship"):** 0171
six-phase lifecycle + worker-per-task + simplified-mode flag (documents D32
divergence); 0172 Phase-1 5-step refactor + Method δ + v0 catalog discipline;
0173 replan-check verdict + invalidate-at-and-below + ReplanRecord sparsity;
0174 sufficient-predicate + Phase-6 BlameVerdict dispatch; 0175 `invoke`→
CapacityContext flip + write-body gate enforcement (amends 0146/0159/0170).

**Next:** commit R0 record (design log + 5 ADRs), branch `phase-47` off `3cdfc5a`,
begin PR-A.
