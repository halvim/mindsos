# PHASE_46_DESIGN_LOG — L4 substrate: convergence point

**Chat:** Phase 46 (first L4 code ever written). Largest R0 in the
post-Phase-38 map (~1000–1400 LOC + 6–8 ADRs per PB-BB). **Design-pass
first, then ship** — option-C combined design+ship is NOT assumed; the ship
shape is itself a pushback (PB-0 below).

**Status:** R0 open (design saturation). **No code written, no branch cut.**
Pre-impl pushback rounds (budget 2–3 per PHASE_43 §10.4) + a buildability
scan precede branching `phase-46`.

**Rail context:** All four Stream B rails closed — A (39/43), B (40/41/42),
C (44), D (45). Phase 46 is the convergence point the DAG was waiting on.
Phase 47 (orchestrator + `planning.*` v0) and Phase 48 (L5 v1) consume what
this phase builds.

**Prereq check (run 2026-06-08):**
- `git tag --list | grep -E "phase-4[0-5]-confirmed"` → 40/41/42/43/44/45 all
  present. ✔
- `main`-tip `be832be`; on `main`. Working tree: `M HANDOFF.md`,
  `M docs/_workbench/L3_FUTURE_WORK.md` + untracked Robot Demo workstream
  (`confirmation_docs/ROBOT_DEMO_*`, `demo_ui/`, `sim/`, `web/`,
  `prototype_zero/`). `ROBOT_DEMO_STATUS.md` **exists** → the HANDOFF inline
  Robot Demo §0 block was relocated; HANDOFF stages cleanly. **Never
  `git add -A`; stage selectively; leave Robot Demo files alone.** ✔
- **VERSION BUMP REQUIRED:** slot 46 > high-water 45 → full 9-surface bump
  45→46 (PHASE_MAP §1 high-water rule). Second real bump after Phase 45. ✔
- **PB-Z reading-list (diffs of prior phases touching this phase's modules):**
  Phase 42 `context.py` (CapacityContext + CancelToken Protocol +
  CancelTokenView — S8/S12 reconcile), Phase 42 `capacity_layer.py`
  (`register_capacity` bipartite + the 3 unmigrated bodies), Phase 41
  `capacity_layer.py` (`iter_monitors` — S11 consumer), Phase 45
  `builtins/dream.py` (DreamDirective / ReplanInjectionDirective / DreamCapacity
  — S14), Phase 43 `mindsos_core/schema.py` (only if S6 root needs a schema
  subclass — PB-AAA). To run at R0 step 0 alongside the ADR transcription-parity
  probe.

---

## §0. Required-reading acknowledgement

- HANDOFF §1, §3.1.5 (Chat A closure — 7 pushes + L4-vs-L3 line),
  §3.1.6 (L1/L3 reframe — ADR-0155→0159 + registration contract v2),
  §3.1.7 (Chat C plan / 4-rail DAG), §3.1.16 (Phase 41 — `iter_monitors`
  + MonitorSubscriptionRegistry carry), §3.1.17 (Phase 42 — PB-23/PB-24
  carry + ceremony lessons), §3.1.18 (Phase 45 — dream contract S14 consumes),
  §4/§4.1/§4.2 (L5 settled — three-sub-MM substrate this phase instantiates),
  §9 (process discipline: pair-execution, 6-step confirm, docker rebuild,
  tag-at-confirm-artifacts-commit, fix Linux git identity first).
- POST_PHASE_38_PHASE_MAP §0, §1 (DAG + high-water rule + 9-surface
  checklist + PB-BB ADR load + PB-AAA physical-layout call), Phase 46 detail
  block, §6.
- CHAT_A_DECISIONS R1 D32 family (D32 / D32.2 / D32.3 / D32.4 / D32.5 /
  D32.5b / D32.5c.1–7 + revised D32.5c.1) + L4-vs-L3 boundary + Push 5 defer
  + D9.1–D9.7 ALS registry.
- CHAT_B_DECISIONS D-B10/B11/B13/B14 (+ D-B5/B6 dream-as-live, D-B30 TaskRun,
  PB-AAA) + l5_mental_model_design_notes §1–§2 (sub-MM + chain schemas).
- PHASE_42 / 44 / 45 DESIGN_LOG §0 (process precedents: S-surface saturation,
  R1-step-0 ADR transcription-parity probe, pre-impl pushback rounds,
  gate-driven follow-up budget, ground-first consumer-discipline rule).

---

## §1. Design ground truth (implement; do NOT re-litigate)

From Chat A R1/R2 + Chat B + the Phase 46 PHASE_MAP Locked-decisions row:

- **IntelligenceLayer** — one per session. `start(session, knowledge=kl,
  capacity=cl)`, `stop(mode="abort")`, `enqueue(task)`. `mode="pause"` ships
  as `NotImplementedError` (Push 5 defer; tests must not exercise it).
- **Concurrency model (D32 = B):** single-process, multi-threaded; three
  thread classes — orchestrator (main), worker pool, signal-triage (dedicated).
  No subprocess pool v1 (D32.7 v2 opt-in).
- **Priority-tier Executor (D32.5b + D32.5c):** custom Executor over a
  `PriorityQueue` keyed `(tier, -attention_score, submit_time)`. 4 tiers
  CRITICAL/FOREGROUND/BACKGROUND/DREAM. Within-tier score-based, not FIFO.
  Defaults CRITICAL=1000 / FOREGROUND=500 / BACKGROUND=100 / DREAM=10
  (int 0–9999). Within-tier preempt rule `new_score > running_score + H`,
  H=50 per-deployment configurable. Auto-preempt-on-elevation. Queue-priority
  ordering, NOT running-task preemption (cancellation does that, cooperatively).
- **Worker pool:** default `min(8, cpu_count())`; per-deployment configurable.
- **MM RWLock (D32.3 = C):** reader-writer lock per active MM; writer-preferred
  fairness (writer-preferred when waiting > N ms).
- **Cooperative cancellation (D32.5 = A):** `cancel_token` kwarg; `.is_set()`
  at yield points; `CancelTokenView` enforces read-only at body side.
- **Signal-triage worker (D32.2 = A):** always-on dedicated thread; classifies
  signals into the 4 tiers by calling L3 `decision.signal_to_tier` (the
  capacity is an L3 skeleton at Phase 47).
- **ALS subsystem registry (D9.1):** `ALSSubsystemRegistration` dataclass +
  L4-owned registry dict; v0 catalog empty (concrete 10-subsystem catalog =
  WSD installation). Global aggregation has no L4 home (D9.4 → L0 admin).
- **MonitorSubscriptionRegistry (L1_L3_REFRAME §D36):** session-scope
  `Dict[DataState IRI, List[Monitor IRI]]`; consumes `cl.iter_monitors()`
  (Phase 41); per-task lazy Monitor instantiation; register/unregister
  orchestrator-thread-only.
- **Three sub-MMs (D-B10):** `knowledge-MM` + `capacity-MM` + `intelligence-MM`;
  thin root holds 3 pointers + `task_run_ref` + `ref:problem_trace` +
  `outcome_ref`.
- **L4 read discipline / no shadow state (D-B11/B13):** L4 reads only from MM;
  cache-miss → search L2/L3 → instantiate → read. **Invariant: no shadow state
  outside MM.**
- **MM resolution+instantiation (D-B13):** IRI-namespace dispatch; lazy
  single-node; monotone-grow; pin-at-instantiation (D-B14 — refs as
  `(iri, version_int)` tuples; lazy inline-on-retire is Phase 48).
- **L4-vs-L3 strict line:** L4 = substrate + control flow only; all
  decisions/computations are L3 capacities. L4 retains data-structure
  mutations, state-machine transitions, lock arbitration, lifecycle, threading.
- **PB-AAA / PB-AA physical layout:** default = Chat B schemas as-written;
  composite-collapse only post-Phase-49 if benchmarks demand.

---

## §2. S-surface enumeration (L4 substrate)

Mirror of the Phase 42/44/45 S-surface format. Each surface tagged with its
**real consumer** (the consumer-discipline test from Phase 44/45) — surfaces
whose only consumer is Phase 47/48 are deferral candidates (see PB-0/§3).

| S | Surface | Module | Real consumer | Ship at 46? |
|---|---|---|---|---|
| **S1** | Package skeleton + `__init__` + pyproject install + tier enum shared module | `mindsos_intelligence/` | self / all S* | **Yes** |
| **S2** | IntelligenceLayer lifecycle (`start`/`stop("abort")`/`enqueue`; pause→NotImplementedError) | `intelligence_layer.py` | Phase 46 roundtrip test; Phase 47 orchestrator | **Yes (substrate); empty-task only)** |
| **S3** | Priority-tier Executor + 4-tier queue `(tier,-attention_score,submit_time)` + `write_priority`/`elevate` + auto-preempt + hysteresis | `executor.py` | Phase 46 test; Phase 47 dispatch | **Yes (mutation primitive)** |
| **S4** | Worker pool `min(8,cpu_count())` | `executor.py` | S2/S3; Phase 47 | **Yes (dummy callables)** |
| **S5** | MM RWLock (per active MM, writer-preferred) | `mm_*` / `locks.py` | S6/S7; Phase 47/48 writes | **Yes** |
| **S6** | Three-sub-MM container + thin root | `mm_*.py` | S7; Phase 48 chain artifacts | **Yes (container)** |
| **S7** | MM resolution+instantiation (IRI dispatch, lazy single-node, monotone-grow, pin-at-instantiation) | `mm_resolver.py` | S13 materialise; Phase 47/48 | **Yes** |
| **S8** | Cooperative cancellation framework (`cancel_token` concrete + `CancelTokenView`) — reconcile w/ Phase 42 `context.py` Protocol | `cancellation.py` | S2 abort; Phase 47 capacity bodies | **Yes** |
| **S9** | Signal-triage worker thread (always-on) + classifier call | `signal_triage.py` | **classifier = L3 `decision.signal_to_tier`, Phase 47 skeleton** | **Fork F-stub (§3 F3)** |
| **S10** | ALS subsystem registry (dataclass + dict, empty) | `als_registry.py` | catalog = WSD; aggregate = Phase 47 phase-loop | **Registry only; aggregate DEFER** |
| **S11** | MonitorSubscriptionRegistry (session-scope dict; `iter_monitors`; lazy Monitor instantiation; orch-thread-only) | `monitor_subscription.py` | Phase 46 test; Phase 47 signal routing | **Yes** |
| **S12** | CapacityContext wiring (PB-23): `invoke`→CapacityContext + 3 bodies → `context.kl` + ADR-0146/0159 session-gate | `capacity_layer.py` / `context.py` | body migration: now; **live write-gate: Phase 47** | **Split (§3 F5)** |
| **S13** | Instance `materialise` (PB-24): 2 mindsos_instances intergraph subclasses | `mindsos_instances/` | **S7 capacity-MM instantiation = Phase 46** | **Yes** |
| **S14** | Dream-cycle timer (Phase 45 carry): reads `execution_policy`/`entry_point`, invokes bodies for DreamDirectives; MM deep-copy; live re-execution; ALS firing; ReplanInjectionDirective→replan | `intelligence_layer.py` / dream timer | **timer = L4; live re-exec/ALS/replan = Phase 48; task-thru-phase-loop = Phase 47** | **Split (§3 F6)** |
| **S15** | 6–8 new ADRs 0163–0170 | `docs/decisions/adr/` | ratification | **Yes (count = PB-BB call)** |
| **S16** | 9-surface version bump 45→46 | manifest/pyproject/7×`__version__`/compose/3×export-slate | release | **Yes** |
| **S17** | `doctor` L4 health check + `docs/concepts/intelligence-layer.md` + `mm-substrate.md` + l4 notes amend | doctor/docs | confirm | **Yes** |

---

## §3. Genuine design forks (pushbacks — options + pick)

These are the forks the chat opener flags. Each: concern → options → **pick**.
Picks are provisional; pre-impl pushback rounds (§5) may revise.

### PB-0 — Ship shape (HEADLINE; option-C combined vs split)

**Concern.** ~1000–1400 LOC + 6–8 ADRs in one PR is the largest single ship
in the map. Several surfaces (S9 classifier, S10 aggregate, S12 write-gate,
S14 live re-exec) have **no Phase-46 consumer** — their consumer is the Phase
47 orchestrator / phase-loop or Phase 48 L5. The inherited consumer-discipline
rule (Phase 44/45) says: ship the contract/primitive ahead of its consumer
only when it is *self-contained and testable*; **defer surfaces whose behavior
cannot be exercised until the consumer exists.**

- **Opt A — One monolithic PR (pure option-C).**
  Pros: single gate, single confirm ceremony.
  Cons: 1400 LOC + 8 ADRs in one review; mixes self-contained primitives with
  consumer-absent stubs; high cascade-failure blast radius at the gate;
  contradicts consumer discipline.
- **Opt B — Two PRs on `phase-46`, single confirm (Recommended).**
  PR-A = self-contained substrate primitives (S1–S8, S11, S13, S12-body-migration,
  S15-core-ADRs, S16). PR-B = async/threaded surfaces with stubs (S9 thread +
  fallback classifier, S10 registry, S14 timer + MM deep-copy primitive) +
  remaining ADRs. Confirm once after both land + cumulative gate.
  Pros: bounded reviews; primitives gate-clean before threads layer on;
  one version bump / one tag.
  Cons: two gate cycles; branch carries an intermediate state.
- **Opt C — Phase 46 ships primitives only; push S9/S10-aggregate/S14
  live-behavior to Phase 47.**
  Pros: maximal consumer discipline; smallest 46.
  Cons: leaves `mindsos_intelligence` package visibly incomplete vs the
  PHASE_MAP "Features in scope" list; renegotiates the phase boundary the DAG
  set; the threads ARE substrate (Chat A "L4 retains" lists both).

**Pick: Opt B.** The threads (signal-triage, dream-timer) are explicitly L4
substrate per Chat A's "L4 retains" list, so they belong at 46 — but their
*decision content* (classifier verdict, live re-execution) is L3/L5 and
defers. Ship the threads + their substrate scaffolding with stubbed decision
calls; defer the decision content to its consumer phase. Two PRs keep the
review bounded. **Open question for the user: is even Opt B too much for one
phase — should S14 dream-timer defer wholesale to Phase 47?** (see PB-6.)

### PB-1 — Executor public API: `set_score`/`elevate` vs `write_priority`/`update_priority`

**Concern.** D32.5c names the APIs `set_score()` / `elevate()`. The later
"Vocabulary fix" (CHAT_A lines 223–227) **renames** to `queue.write_priority()`
(pure L4 mutation) + an L4 wrapper `update_priority(task_id, context)` that
invokes L3 `scoring.attention_score` then writes. The PHASE_MAP Phase 46 row
still says "`set_score` + `elevate` APIs" (pre-Vocabulary-fix text).

- **Opt A — Ship `write_priority` + `elevate` (pure mutation) at 46; defer
  `update_priority` wrapper to Phase 47 (Recommended).**
  The wrapper needs `scoring.attention_score` (L3, Phase 47). The pure
  mutation primitive is the substrate; it's testable now with explicit scores.
  Pros: honors the Vocabulary-fix strict-line; consumer discipline (wrapper's
  L3 dep is Phase 47); PHASE_MAP row is stale, not authoritative over CHAT_A.
  Cons: PHASE_MAP row wording diverges → note it as an as-shipped delta.
- **Opt B — Ship `set_score`/`elevate` names verbatim per PHASE_MAP row.**
  Cons: masks the L3-decision/L4-mutation split the Vocabulary fix exists to
  expose; forces a rename at Phase 47.

**Pick: Opt A.** Record the PHASE_MAP-row naming divergence as an as-shipped
delta (Phase 40 PB-2 precedent for amending stale row text).

### PB-2 — `attention_score` scope at 46 (constant defaults vs L3 capacity)

**Concern.** D32.5c.1 has two recorded picks: original (D: hybrid constant +
v2 hook) and **revised** (L3 capacity `scoring.attention_score` with learnable
params from v1, cold-start constants). The L3 capacity is a Phase 47 skeleton.

- **Opt A — 46 ships constant per-tier defaults + the mutation primitive only;
  no `scoring.attention_score` invocation (Recommended).**
  Pros: the L3 scoring capacity + `learned-parameters` read + ALS S9 wiring all
  live at Phase 47; 46 substrate is complete and testable with constants.
  Cons: none material — the revised D32.5c.1 is satisfied incrementally.
- **Opt B — wire the L3 capacity call at 46.** Cons: capacity doesn't exist
  until 47; would ship dead/stubbed.

**Pick: Opt A.**

### PB-3 — MM RWLock granularity (root vs per-sub-MM)

**Concern.** D32.3 = C is "reader-writer lock per active MM." Three-sub-MM
(D-B10) raises: one lock at MM-root, or one per sub-MM? D32.3 explicitly
rejected per-instance locks (B) for deadlock risk.

- **Opt A — Single writer-preferred RWLock at MM-root granularity, guarding all
  three sub-MMs (Recommended).**
  Pros: matches D32.3 = C literally ("per active MM"); no cross-sub-MM deadlock;
  `set_score` write-through to `attention_score` (D32.5c.4) is atomic under one
  lock.
  Cons: writes to capacity-MM block reads of intelligence-MM. Acceptable v1 —
  per-sub-MM is a v2 throughput optimization, gated on benchmarks (PB-AAA
  posture).
- **Opt B — per-sub-MM RWLock.** Cons: re-opens the deadlock D32.3 rejected;
  premature optimization.

**Pick: Opt A.** ADR documents the root-granularity choice + the v2 split
escape hatch.

### PB-4 — CancelToken / CancelTokenView reconciliation with Phase 42 `context.py`

**Concern.** Phase 42 already shipped `CancelToken` (`@runtime_checkable`
Protocol) + `CancelTokenView` in `mindsos_capacity/context.py`. Phase 46
`cancellation.py` adds the concrete framework. Duplication risk.

- **Opt A — `cancellation.py` provides the concrete `CancelToken` impl
  (threading.Event-backed) satisfying the Phase 42 Protocol; `CancelTokenView`
  stays in `context.py` (L3 body-side), re-exported from `cancellation.py`
  (Recommended).**
  Pros: Protocol stays at the L3 boundary where bodies import it; concrete impl
  is L4; no symbol duplication.
  Cons: a re-export to verify in the export-slate sentinels.
- **Opt B — move `CancelTokenView` to `cancellation.py`.** Cons: breaks Phase
  42 `context.py` imports; churns a shipped module.

**Pick: Opt A.** R0 step-0 probe must read Phase 42 `context.py` to confirm the
exact Protocol signature before drafting the concrete impl.

### PB-5 — ADR-0146/0159 session-gating boundary (PB-23 part ii)

**Concern.** `CapacityContext` (Phase 42, 10 fields) has **no session field**,
so ADR-0146 write-body capability gating has no home. PB-23 carried the
resolution to Phase 46. But the gate's consumer is an L4 path that invokes a
write-body capacity *with a session* — which is the Phase 47 orchestrator (no
L4 invokes capacities through a session until then; the Phase 46 roundtrip test
is an empty task).

- **Opt A — Split PB-23: do the mechanical body migration (`context.get("kl")`
  → `context.kl` for consolidate/trace/text) at 46; draft the session-gate
  ADR contract at 46 but **defer live gate enforcement to Phase 47**
  (Recommended).**
  Pros: the readable surface (context.kl) ships and is testable; the gate's
  absent consumer is respected; the ADR fixes the contract now so Phase 47
  implements against it.
  Cons: PB-23 not "fully closed" at 46 — record as an explicit split.
- **Opt B — add a `session`/capability handle to `CapacityContext` now + gate
  at L4 dispatch.** Cons: dispatch-with-session is Phase 47; the field would
  ship unconsumed; widens the frozen 10-field context the moment after it
  shipped.
- **Opt C — gate entirely in L4 dispatch wrapper, CapacityContext untouched.**
  Pros: keeps context frozen. Cons: still no Phase-46 consumer; same defer.

**Pick: Opt A.** The ADR records the resolution (gate lives in L4 dispatch,
reads session from IntelligenceLayer, NOT in CapacityContext — keeps the L3
body context session-free per the strict line); enforcement lands Phase 47.

### PB-6 — Dream-cycle timer L4/L5 split (Phase 45 carry / S14)

**Concern.** Phase 45 carried "L4 dream-cycle timer + MM deep-copy + live
re-execution + ALS firing + replan" to Phase 46. But: the timer enqueues a
DREAM-tier *task that runs the phase-loop* (= Phase 47); live re-execution +
ALS firing = Phase 48; the prompt itself says "D'1 live re-execution is mostly
Phase 48."

- **Opt A — 46 ships: the dream-cycle timer thread + DreamCapacity node read
  (`execution_policy`/`entry_point`) + the **MM deep-copy primitive** (a pure
  substrate op on the three-sub-MM container). DEFER: enqueue-as-phase-loop-task
  → 47; live re-execution + ALS firing + ReplanInjectionDirective consumption
  → 48 (Recommended).**
  Pros: timer + deep-copy are substrate, testable at 46; decision content
  defers to its consumer; matches D9.6 (ALS aggregate is a phase-loop task =
  47) and Chat B dream-as-live (re-exec is 48).
  Cons: S14 visibly partial at 46.
- **Opt B — defer S14 wholesale to Phase 47.**
  Pros: cleanest 46; the timer's first real action (enqueue task) needs the
  phase-loop anyway.
  Cons: MM deep-copy primitive is genuine substrate other phases may want; Chat
  A lists "ALS dream-cycle timer" under L4 retains.
- **Opt C — ship full S14 at 46.** Cons: re-executes through a phase-loop that
  doesn't exist; impossible.

**Pick: Opt A**, but flag for the user: if PB-0 lands on a tighter 46, **Opt B
(defer S14 to 47)** is the fallback. Decide jointly with PB-0.

### PB-7 — Signal-triage thread classifier stub (S9)

**Concern.** The always-on thread calls L3 `decision.signal_to_tier`
(Phase 47 skeleton). At 46 the classifier doesn't exist.

- **Opt A — ship the thread + a trivial fallback classifier (constant tier,
  e.g. FOREGROUND, or a dont-know→FOREGROUND default); swap to the L3 capacity
  at 47 (Recommended).**
  Pros: thread is live + testable (classification path test in PHASE_MAP);
  decision content defers.
  Cons: fallback is throwaway.
- **Opt B — ship thread dormant (started, no classification).** Cons: the
  PHASE_MAP "classification path" test has nothing to exercise.

**Pick: Opt A.** Fallback documented as a Phase-47-replaced stub.

### PB-8 — Tier enum shared-module placement

**Concern.** D32 says the tier enum lives in a shared module (Executor +
signal-triage import it). Both are L4.

- **Pick:** small `mindsos_intelligence/tiers.py` (or top of `executor.py`)
  exporting the 4-tier enum + per-tier default scores + H constant; both
  `executor.py` and `signal_triage.py` import. Minor; not a real fork.

### PB-9 — PB-AAA physical layout (R0-owned)

**Pick:** default = Chat B schemas as-written (three-sub-MM root + chain
artifacts as logical composites). No composite-collapse; that's a post-Phase-49
benchmark-gated optimization. Confirmed, no fork.

### PB-10 — ADR count (PB-BB: 6–8) + numbering

**Concern.** PHASE_MAP enumerates 8 candidate ADR topics (priority-tier
Executor primitive, MM RWLock semantics, MonitorSubscriptionRegistry contract,
three-sub-MM composition, MM resolution+instantiation layer, cooperative
cancellation contract, signal-triage worker thread placement,
attention-score-on-TaskRun). Numbers 0163–0170 reserved.

- **Pick (provisional):** draft the count that matches what ships at 46 under
  PB-0 Opt B. If S14 dream-timer behavior defers (PB-6), the dream-timer ADR
  may be a thin "L4 timer contract" stub or fold into the Executor ADR. Lock
  the exact count + numbering at R1 after the transcription-parity probe.
  Candidate mapping: 0163 priority-tier Executor + attention_score; 0164 MM
  RWLock granularity (PB-3); 0165 three-sub-MM composition; 0166 MM
  resolution+instantiation; 0167 cooperative cancellation contract (+ PB-4
  reconcile); 0168 MonitorSubscriptionRegistry contract; 0169 signal-triage
  thread placement; 0170 session-gating boundary resolution (PB-5). = 8.

---

## §4. Carry-forward consumption map (Phase 41/42/45 → 46)

| Source | Carry | Phase 46 disposition |
|---|---|---|
| §3.1.16 (Phase 41) | `iter_monitors` consumer + MonitorSubscriptionRegistry + lazy Monitor instantiation + orch-thread-only register | **S11 — ship in full** |
| §3.1.17 (Phase 42 PB-23) | `invoke`→CapacityContext + 3 bodies→`context.kl` + ADR-0146/0159 gate | **S12 — split (PB-5): body migration now; gate ADR now, enforce 47** |
| §3.1.17 (Phase 42 PB-24) | `materialise` 2 intergraph instance subclasses | **S13 — ship (consumer = S7 capacity-MM instantiation, at 46)** |
| §3.1.18 (Phase 45) | dream-cycle timer + MM deep-copy + live re-exec + ALS firing + replan | **S14 — split (PB-6): timer + deep-copy primitive now; re-exec/ALS/replan → 48; task-thru-phase-loop → 47** |

---

## §5. Pre-impl pushback rounds (saturation tracker)

Budget 2–3 rounds (PHASE_43 §10.4) + a buildability scan before branching.

- **Round 1 — CLOSED 2026-06-08.** Forks PB-0…PB-10 surfaced with picks. User
  ratified the two coupled blockers:
  - **PB-0 = Opt B** (two PRs on `phase-46`, single confirm: PR-A primitives,
    PR-B threaded/async surfaces; one version bump + tag). ✔
  - **PB-6 = Opt A** (S14 = dream-cycle timer thread + DreamCapacity node read +
    MM deep-copy substrate primitive at 46; enqueue-as-phase-loop-task → 47;
    live re-execution + ALS firing + ReplanInjectionDirective → 48). ✔
  - PB-1/2/3/4/5/7/8/9/10 picks **stand** (uncontested); open to contest in
    Round 2.
- **Round 2 — CLOSED 2026-06-08 (skeptical pass; 1 reversal + 1 new defer + 2
  refinements + 1 clarification).**
  - **PB-8 — REVERSED.** Tier enum must NOT live in `mindsos_intelligence`
    (L4). The signal-triage classifier `decision.signal_to_tier` is an **L3**
    capacity (Phase 47); L3 cannot import L4 (upward-import violation). The
    shared tier enum + per-tier default scores must live in **`mindsos_capacity`**
    (L3) — alongside the Phase 42 `context.py` verdict types — and L4 imports it
    *downward*. Impl: small L3 edit (`mindsos_capacity/tiers.py` or extend
    `context.py`) bundled into PR-A; `executor.py` + `signal_triage.py` import it.
  - **PB-11 — NEW (defer).** `attention_score` MM write-through (D32.5c.4) has
    **no target at 46**: it writes to the TaskRun composite, a Phase-48 chain
    artifact. → 46 ships **queue-only** `attention_score`; MM write-through
    defers to Phase 48 when TaskRun exists. (Consumer discipline.)
  - **PB-1 — REFINED.** Per the Vocabulary-fix exact text, collapse to a single
    primitive `write_priority(task_id, score, tier=None)` (does score and/or
    tier); drop `elevate` as a separate public method (keep its "top of new
    tier" default as the `score=None` path). One primitive, not two.
  - **PB-7 — REFINED.** Stub classifier = **tier-passthrough** (routes a
    test-signal-carried tier hint), NOT constant-FOREGROUND. Constant-FOREGROUND
    would mean CRITICAL never surfaces and the classification-path test is
    vacuous. Swapped for L3 `decision.signal_to_tier` at 47.
  - **S12 — CLARIFIED.** The `invoke`→CapacityContext change is **L3-side**
    (`runtime.py` builds a `CapacityContext` instead of a dict; bodies →
    `context.kl`), tested by the existing L3 invoke tests — NOT gated on the L4
    worker pool. Belongs in PR-A.
  - Unchanged: PB-0, PB-2, PB-3, PB-4, PB-5, PB-6, PB-9, PB-10 (numbering may
    shift slightly per PB-8/PB-11).
- **Round 3 — CLOSED 2026-06-08 (confirm pass; ZERO reversals → saturation).**
  Probed the Round-2 deltas against shipped code:
  - **PB-8 CONFIRMED + strengthened.** `mindsos_capacity/context.py:151` already
    ships `TierVerdict` with `tier: Optional[Any]` and the docstring *"tier is
    the downstream TierEnum (typed `Any` here pending its owning family)."*
    Phase 42 deliberately deferred the TierEnum to its owning family = **L3**.
    **Impl-lock:** define `TierEnum` (+ per-tier default scores + H) in
    `mindsos_capacity` (`tiers.py` or extend `context.py`); narrow
    `TierVerdict.tier` from `Optional[Any]` → `Optional[TierEnum]`; L4
    `executor.py`/`signal_triage.py` import it downward. Layer isolation is
    **enforced** (`tests_server/integration/test_layer_isolation.py` +
    `tests/phase_16` + `tests/phase_28` import-isolation suites) → an L4-home
    tier enum would have failed the gate. `mindsos_capacity` is upward-clean
    (imports no higher layer). PB-8 is mandatory, not stylistic.
  - **PB-11 CONFIRMED.** No `TaskRun` class exists (`grep` finds only a string
    ref in `builtins/dream.py`, not a composite) → MM write-through target
    genuinely absent at 46; queue-only `attention_score` holds; write-through → 48.
  - PB-1/PB-4/PB-5/PB-7 anchors re-confirmed (`CancelToken` Protocol +
    `CancelTokenView` at `context.py:85/93`; verdict types at 150–185).
  - **No design pick reversed.** New impl-lock: `TierVerdict.tier` narrowing.
- **R1 step 0 (pre-branch):** ADR transcription-parity probe (read each
  Chat A/B decision against the ADR draft) + PB-Z diff reads (Phase 42
  `context.py`/`capacity_layer.py`, Phase 41 `capacity_layer.py`, Phase 45
  `builtins/dream.py`) + buildability scan over the locked module boundaries.
- Rounds 2–3: TBD after Round 1.

**Saturation signature (PHASE_43 §10.4):** a round producing impl-locks only,
zero reversals.

---

## §6. R1 step-0 grounding probe (run 2026-06-08 — read-only, pre-branch)

All design assumptions validated against shipped code. **Zero reversals.**

1. **CapacityContext** (`mindsos_capacity/context.py`) — frozen, 10 fields,
   **no `session` field** → PB-5 Opt A holds (gate in L4 dispatch, not in
   context). `CancelToken` Protocol + `CancelTokenView` present as expected →
   PB-4 Opt A holds (concrete `threading.Event`-backed `CancelToken` in
   `cancellation.py` satisfies the Protocol; re-export `CancelTokenView`).
2. **`iter_monitors()`** → `List[Monitor]`; **Monitors declare subscriptions
   via a `subscribes_to` tuple of DataState IRIs.** → S11 builds the
   `Dict[DataState IRI, List[Monitor IRI]]` by **inverting `subscribes_to`**.
   (Impl-lock: registry construction = invert each Monitor's `subscribes_to`.)
3. **Unmigrated bodies** — `consolidate` + `trace` use dict-style
   `context.get("kl")`; `context` is passed as `Mapping[str, Any]` through
   `runtime.invoke()`. → S12 migration = `invoke` builds a `CapacityContext`
   instead of a dict; bodies switch to `context.kl`. **FLAG:** probe found
   `context.get("kl")` in consolidate + trace only; the `text.*` body's kl
   access (named in PB-23 as the 3rd) must be re-confirmed at impl — it may not
   touch kl or may access differently. Minor; R1 impl verifies.
4. **Dream** (`builtins/dream.py` + `DreamCapacity` in `capacity.py`) —
   `execution_policy` + `entry_point` fields, `DreamExecutionPolicy` enum,
   `DreamDirective` + `ReplanInjectionDirective` all present → S14 timer reads
   them directly (PB-6 Opt A).
5. **MM root schema is brand-new** — no existing `L2Schema`/`MMSchema` pattern
   to subclass → PB-AAA confirmed (build the three-sub-MM root fresh, Chat B
   schemas as-written). `IntergraphEdgeInstance` + `IntergraphHyperEdgeInstance`
   exist; **`materialise` absent** → S13/PB-24 confirmed (add it; consumer = S7).
6. **`mindsos_intelligence/` does not exist** → S1 creates it.
7. **Phantom-file check:** `docs/concepts/intelligence-layer.md` +
   `mm-substrate.md` absent (NEW, correct). Highest ADR = **0162** → 0163–0170
   free (PB-10).

**Net:** probe clean; the two impl-locks recorded (S11 `subscribes_to`
inversion; S12 `invoke`→CapacityContext build site) + one impl-time FLAG
(text-body kl access). No design pick reversed.

---

## §7. Saturation status

**SATURATED 2026-06-08.** Round 1 (2 blockers ratified) + R1 step-0 probe clean
+ Round 2 (1 reversal + 1 defer + 2 refinements) + Round 3 (zero reversals,
impl-locks only — the PHASE_43 §10.4 saturation signature). Design pass is
ready to ship.

**Locked picks:** PB-0 = two PRs/one confirm; PB-1 = single `write_priority`
primitive; PB-2 = constant tier defaults; PB-3 = MM-root RWLock; PB-4 =
concrete CancelToken in `cancellation.py`; PB-5 = session-gate in L4 dispatch
(enforce 47); PB-6 = dream timer + MM deep-copy primitive; PB-7 = tier-passthrough
stub classifier; PB-8 = TierEnum in `mindsos_capacity` (L3) + narrow
`TierVerdict.tier`; PB-9 = Chat B schemas as-written; PB-10 = 8 ADRs 0163–0170;
PB-11 = queue-only `attention_score` (write-through → 48).

**ADRs DRAFTED 2026-06-08 (8, status Accepted at R0; §Implementation footers
"pending ship"):**
- **0163** — L4 priority-tier Executor + attention_score (PB-1 single
  `write_priority`; PB-2 constant defaults; PB-11 queue-only score).
- **0164** — MM RWLock, root granularity, writer-preferred (PB-3).
- **0165** — three-sub-MM composition + thin root + no-shadow-state (PB-9).
- **0166** — MM resolution+instantiation + `materialise` (PB-24).
- **0167** — cooperative cancellation; concrete token L4, Protocol stays L3 (PB-4).
- **0168** — MonitorSubscriptionRegistry (`subscribes_to` inversion).
- **0169** — TierEnum home = L3 + `TierVerdict.tier` narrow + signal-triage
  thread w/ passthrough stub (PB-8 + PB-7).
- **0170** — write-body session-gating = L4 dispatch; contract now, enforce 47
  (PB-5); amends ADR-0146/0159.

Dream-cycle timer + MM deep-copy primitive (PB-6/S14) carry no standalone ADR:
the timer's contract is ADR-0162 §Implementation forward-ref; the deep-copy
primitive is covered in ADR-0165 §Consequences. (8 ADRs = PB-BB count.)

**BRANCHED + R0 RECORD COMMITTED 2026-06-08** (`phase-46` @ `53245de`: design
log + 8 ADRs, 1077 insertions).

## §8. Impl-time decisions (grounding-driven, post-branch)

- **ADR fixes (R1 grounding probe of `context.py`):** (1) ADR-0167 — concrete
  CancelToken mutator is `request_cancel()` (the shipped Protocol method), not
  `cancel()`/`set()`. (2) ADR-0170 — `CapacityContext` *does* carry `session_id`
  + `user_id` (string IDs); what it lacks is a capability/authorization handle.
  Reworded "session-free" → "authorization-free". (3) ADR-0166 — the MM resolver
  IS the concrete `MMHandle` the Phase 42 Protocol named (`get_or_instantiate`/
  `find_instances_by_type`/`produces_of`/`consumes_of`); ADR now says so.
  (4) Only `consolidate.py:136` + `trace.py:119` use `context.get("kl")`; `text.*`
  doesn't (R1 flag resolved — no text migration).
- **S12 DEFERRED WHOLESALE TO PHASE 47 (user-ratified).** `invoke`'s
  `context: Optional[Mapping[str, Any]]` is a shipped public signature consumed
  by the whole corpus; flipping it to `CapacityContext` is a corpus-wide atomic
  change with no Phase-46 caller. The `invoke`→CapacityContext migration + the
  2-body migration + the gate enforcement all land at Phase 47 (their caller =
  the orchestrator). **PB-23 closes at 47, not 46.** PR-A is now almost purely
  additive.

**PR-A scope (revised, additive):** new `mindsos_intelligence` package
(IntelligenceLayer, Executor+worker pool, MM container+RWLock, mm_resolver as
MMHandle, cancellation, signal_triage w/ stub, als_registry, monitor_subscription,
dream-timer + MM deep-copy primitive) + L3 edit (`mindsos_capacity/tiers.py`
TierEnum/defaults + `TierVerdict.tier` narrow + isolation-sentinel add) +
`mindsos_instances` `materialise` + `pyproject` package declaration +
`tests/phase_46/`. Version bump (S16) at confirm. PR-B (signal-triage live
wiring) folds into 47 per the S12/S9 defers — **re-evaluate whether PB-0 still
needs two PRs** now that the consumer-gated surfaces moved to 47.

## §9. Ship closure (2026-06-08)

**SHIPPED 2026-06-08.** Squash-merge `47c3568` on `main`; confirm artifacts
`18ba793`; tag `phase-46-confirmed` at the confirm-artifacts commit `18ba793`
(per the Phase 42 release-gate lesson — `release.yml` requires
`PHASE_46_CONFIRMED.md` at the tagged commit). Cumulative gate **3793 passed /
9 skipped / 0 failed** (Linux docker, 31:55) at phase46. `doctor --self-test`
green (8-package parity). Manual host smokes (`python3`): lifecycle
start/enqueue/stop("abort")=42; pause→NotImplementedError; deep-copy
independence; tier order `['c','b','d']`.

**Shipped as a SINGLE PR.** PB-0 Opt B (two PRs) collapsed once S12 + the S9 L3
classifier deferred to Phase 47 — no PR-B content remained (the signal-triage
thread w/ passthrough stub + dream timer landed in the primitives PR). Ship
sequence: R0 record `53245de` → PR-A.1 L3 prereqs `9540f32` → PR-A.2 materialise
`a19c018` → PR-A.3a–e package → PR-A.4 docs+roster → PR-A.5 version bump →
squash `47c3568` → confirm `18ba793`.

**Grounding-driven decisions (probe-first, R1):** PB-8 TierEnum home = L3 (layer
isolation test-enforced; shipped `TierVerdict.tier` placeholder confirmed
intent); only `consolidate.py`/`trace.py` use `context.get("kl")` (no `text.*`
migration); `CancelToken` mutator is `request_cancel()`; `CapacityContext` has
`session_id`/`user_id` but no capability handle (gate → L4 dispatch);
`MMResolver` IS the concrete `MMHandle`. **S12 deferred wholesale to Phase 47**
(user-ratified) — `invoke`→CapacityContext flips a shipped public signature
consumed corpus-wide with no Phase-46 caller; PB-23 closes at 47.

**New-top-level-package checklist completed:** Dockerfile COPY (both stages),
pyproject `packages.find` include, manifest `[mindsos] packages` (8th package),
`sentinel_paths.py`, mkdocs nav, `tests_server` domain-layer isolation roster,
host pip refresh. No CLI verb (orchestrator CLI is Phase 47).

**Carry-forward to Phase 47 (L4 orchestrator):** consume the substrate —
six-phase task lifecycle + `planning.*` v0 + the deferred surfaces:
`invoke`→CapacityContext + body migration + write-gate enforcement
(PB-23/ADR-0170); L3 `decision.signal_to_tier` (replaces the passthrough stub);
L3 `scoring.attention_score` + `update_priority` wrapper; the dream driver.
**Phase 48:** dream live re-execution + ALS firing + replan-injection
consumption; MM `attention_score` write-through to TaskRun; MM inline-on-retire
(D'1).
