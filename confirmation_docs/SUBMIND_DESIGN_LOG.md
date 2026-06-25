# SubMind (Mindlet) — formalizing the "society of small minds" tier

**Status:** Design complete; implementation deferred (design-discussion chat, no code shipped)
**Branch (to open):** `feat/subminds` off `main` (NOT a numbered phase)
**Base:** `main` (HEAD at branch-open time — TBD)
**Scope:** new cross-layer construct touching L2 (new `subminds` role-graph), L3 (check-capacities), L4 (runtime: scheduler, registry, arbitration); reverses ADR-0155; amends ADR-0150
**Date:** 2026-06-23
**Companion ADRs:** ADR-0188 (construct + two-output model), ADR-0189 (priority + arbitration), ADR-0190 (endowment + `subminds` role-graph)

> This log consolidates a design-discussion chat that ran the SubMind concept to closure. Every "RESOLVED" item below is a locked decision. The architecture is settled; what remains is tuning + implementation (see §16). **WSD is fully detached** — it owns none of these mechanics (§17).

---

## §0 Motivation — the gap

MindsOS was inspired by Minsky's *Society of Mind*: a mind is the coordination of many small, individually-dumb sub-systems. The project's three-tier framing was:

1. **society of small minds** — a core coordinating dumb sub-systems into one mind;
2. **single mind** — the integrated L1–L5 stack;
3. **society of full minds** — minds hierarchically orchestrating minds.

The L1–L5 evolution delivered (2) and approaches (3), but left (1) un-formalized. A grounding pass (§17) found that the *autonomy dimension* of the system is currently hollow scaffolding: monitors are declarative-only (ADR-0155 retired their loop), signal-sources are empty skeletons, the ALS registry is empty, and the **only** self-firing loop in the whole stack is the dream-cycle timer (with a stubbed re-exec hook). So "society of small minds" was not a forgotten *concept* — it was drawn and left hollow.

This design fills that gap with a first-class construct: the **SubMind**.

---

## §1 Vocabulary (locked)

| Term | Definition |
|---|---|
| **Capacity** (L3) | Atomic, fixed-not-learned function. Invoked (pull). |
| **Skill** | A vertical *competence* — L2 knowledge + L3 capacities + L4 control — that lets the system **achieve** a class of goals (e.g. "type"). Goal-directed; engaged when its goal is pursued. **Acquired.** |
| **SubMind** *(nickname **Mindlet**)* | An autonomous, dumb **reflex** over one self-state vital. A sense loop that monitors a vital and emits a Signal or a Reflex. No reasoning. A *faculty that conditions* the system. **Endowed.** |
| **The Mind** (L4) | The single per-session orchestrator. Receives outputs, arbitrates, decides action. The unity *is* the arbitration. |
| **Sense loop** | A SubMind's monitoring cycle: sense (check-capacity) → compare to threshold (L2) → emit. (Replaces the discarded term "reflex arc".) |
| **Signal** | A SubMind's *normal* output: queued with (tier, severity), **deliberated** by L4. |
| **Reflex** | A SubMind's *emergency* output: a pre-wired immediate action that **bypasses** the queue and L4 deliberation, for non-reconcilable threats. |
| **Endowment** | The act of adding a SubMind to a mind (parallel to skill *acquisition*). A mind is *endowed with* a SubMind. |

**Skill vs SubMind, the distinction that drives everything:** a skill is the *use* of the system to achieve a goal (pull, goal-directed); a SubMind is an *improvement/extension* of the system — a standing self-state concern (push-capable, self-initiating, stateful-by-sensing). The difference is **goal-competence vs cross-cutting self-state concern**, not "improvement vs use" (which is leaky — installing a skill already improves the system).

---

## §2 Core principle — the reflex / deliberation split

**Autonomy ≠ reasoning.** A SubMind can be *autonomous* (self-firing) while having *zero* reasoning. This is Minsky-faithful: individual agents are dumb; intelligence lives in their coordination.

- A **SubMind** owns a minimal control loop (sense → compare → emit). It never deliberates.
- The single **L4 Mind** does all deliberation: it arbitrates the outputs of all SubMinds into one coherent action stream.

A SubMind does **not** get its own L4. It gets a reflex; L4 is the conductor. Many dumb reflexes + one conductor = one mind. This split is load-bearing — every later decision protects it.

---

## §3 SubMind anatomy (the endowment record)

A SubMind is defined (at endowment) by:

1. **check-capacity** (L3) — reads the vital's current value. ("check water level", not "water level".)
2. **threshold / criterion** (L2 knowledge) — the line(s) that define distress. Global or Local.
3. **severity normalization range** — maps the vital's native units onto a physical `[threshold → failure] → [0 → 1]` scale.
4. **severity → tier mapping** — a fixed, monotonic step-function (§5).
5. **importance weight** — an L4-side scalar used to compute the cross-SubMind ordering score (§5).
6. **resolver reference** — a skill or a single capacity that resolves the need (§9), plus its **declared exclusive-resource needs** (§8).
7. **cadence law parameters** — the proximity→interval control law, with min/max bounds + hysteresis (§4).
8. **activation class** — always-on vs context-gated (§6).
9. **Reflex conditions** — zero or more declared predicates (non-reconcilable triggers) → pre-wired immediate actions (§7, §10).
10. **refractory / reset-band parameters** — for storm suppression (§7).

The **runtime class + scheduler** live in L4; the **persisted definition record** lives in the L2 `subminds` role-graph (§13).

---

## §4 Sense loop + adaptive cadence (RESOLVED)

A SubMind is **autonomous**: it owns its sampling loop and self-schedules. (Channel (a), L4-initiated, is then only an on-demand one-shot read; the loop is not L4's — §11.)

**Cadence is variable** — the sample interval is a **fixed control law inside the SubMind**: `interval = f(proximity to threshold)` — rare when the vital is safe, frequent as it nears the threshold (receptor-adaptation analogy). Two cadence inputs are kept **separate**:

- **proximity** (SubMind-owned, fixed law, **not** learnable) — drives the normal cadence;
- **context-relevance** (L4-owned) — drives activation (§6), not the cadence law.

Requirements: **min/max interval bounds** (never sleep so long a regime change is missed; cap cost) and **anti-thrash hysteresis** on band edges (a value hovering at threshold must not flap its own rate).

Adaptive cadence makes *cheap* always-on vitals nearly free (leave them on, slow when safe). It shrinks but does **not** eliminate the context-gated class — vitals that are **undefined out of context** (e.g. grip force with an empty hand) still need explicit L4 activation.

---

## §5 Severity, tier, attention_score (RESOLVED — OQ-B + OQ-norm)

Three distinct quantities with distinct owners:

- **severity** — *how bad it is now*, **physical**, normalized `0–1` over `[threshold → failure]`. **SubMind-owned.** Drives the tier band and the SubMind's own over-time ordering.
- **tier** — the system-wide urgency bucket (the executor's common currency). Computed as a **fixed, monotonic step-function of severity, set at endowment** (e.g. battery `>50% → BACKGROUND`, `20–50% → FOREGROUND`, `<20% → CRITICAL`). Immutable *mapping*, dynamic *result*. The SubMind never **names** its own tier — the mapping does. (A SubMind that could pick its own tier would leak arbitration into the reflex.)
- **attention_score** = `importance_weight × severity`. **L4-owned.** Drives within-tier ordering **across** different SubMinds (battery-vs-thirst at the same tier). Maps onto the existing `attention_score` heap key.

Why severity is physical, not "urgency": keeping it physical preserves the reflex/deliberation split (the reflex measures distress; L4 owns *how much it matters* via the weight) and isolates the single tunable/learnable knob (the weight) on L4's side. The importance weight is **static at v1**; if ever made learnable, the learner is a **core L4** mechanism (not WSD).

**Adrenaline / tier escalation** falls out for free: as a vital worsens, severity rises and crosses a band, so the tier escalates deterministically. Conditions: mapping monotonic + fixed; hysteresis on band edges.

**Tier is decoupled from preemption.** Tier governs *ordering/visibility only*. Escalating to CRITICAL says "this is urgent"; it must **not** by itself cancel running work (see §8). Wiring tier → automatic preempt recreates the blind-preempt problem.

The queue orders by **(tier, then attention_score)** — exactly the shipped `PriorityTierExecutor` heap.

---

## §6 Activation (RESOLVED)

Every SubMind is a resident sampling loop; **L4 owns the activation state**:

- **always-on** (vitals: thirst, battery) — active for the session;
- **context-gated** (balance — relevant only in certain postures/tasks) — L4 toggles active/inactive by relevance;
- **floored** — a "deactivated" SubMind is never truly off; it drops to a **slow floor cadence** (bounded blindness, not total). L4 can flip floored ↔ active at will.

The SubMind owns its loop + cadence *within* the granted state. Floored ≠ free: all N SubMinds keep ticking, so background load scales with N. Safety-critical vitals should not rely on the floor — they use the Reflex/write-hook instant path (§7, §10) regardless of activation state.

---

## §7 Storm suppression (RESOLVED)

Near the threshold the adaptive cadence is fast, so a naive loop would emit an identical Signal on every sample → L4 spam. Fix = **edge-triggered emission + reset band**, two states per SubMind:

- **ARMED** — watching. On a threshold crossing, emit **once**, go to FIRED.
- **FIRED** — silent. Does **not** re-emit while still below threshold. Re-arms only after the value recovers past a reset margin (threshold + margin).

Exception: while FIRED, if severity **worsens past a next step**, emit a new **escalation** Signal — re-emit on worsening *steps*, not per sample. This kills the storm and the boundary oscillation while preserving genuine escalation.

---

## §8 Preempt vs reconcile (RESOLVED — OQ-D; resource-tagged)

The hardest question: when a queued Signal arrives, does L4 **preempt** (pause/abort current work) or **reconcile** (weave the need into the running plan as a concurrent sub-goal)? Battery-low mid-important-task should *reconcile* (charge while working), not blindly preempt.

**Decision: the verdict is not declared — it is derived from resource contention.** At endowment, each SubMind's **resolver declares the exclusive resources it needs**; each running task declares the resources it holds. L4's rule is mechanical:

- **no overlap → reconcile** — run the resolver concurrently, woven in as a sub-goal/constraint;
- **overlap → contention** — resolve by tier/severity: **preempt** if the need outranks the task, else **defer** as standing pressure (§12).

This also answers OQ-D's second half — *a need is a rival only when resources overlap; otherwise it is a constraint woven into the plan.* "resource" means **exclusive/contended** resources (actuators, single-holder locks), **not** shared schedulable compute. An optional `non-reconcilable` flag = "resolver contends with everything" (or escalate to a Reflex). This requires a one-time **resource model** (a lock/acquisition model), which is also what the Reflex path uses (§10).

---

## §9 Resolver (RESOLVED)

Each SubMind carries a **resolver** = a **skill or a single capacity** (DataState change), taught/exemplified at endowment. The resolver is *what L4 dispatches to satisfy the need* — distinct from the SubMind's check-capacity (which only senses). A SubMind without a resolver is a smoke alarm with no fire department.

---

## §10 Reflex — the bypass output (RESOLVED — OQ-Reflex)

Some threats are **non-reconcilable** and play out faster than L4 can deliberate (a robot falling — the fall is inevitable; redirecting to avoid landing on someone is urgent). Routing such a case through queue → deliberation → resolver is too slow. So the **Reflex** is a separate mechanism, not an ordering tier:

- **Trigger:** a **declared predicate** at endowment (non-reconcilability, **not** mere magnitude). A SubMind may declare zero or more Reflex conditions alongside its Signal path; the same SubMind emits Signals normally and a Reflex at its declared extreme.
- **Action:** a **single fast capacity** (no multi-step pipeline — no time to plan), pre-wired at endowment.
- **Routing:** **bypasses the queue and L4's preempt/reconcile decision**; notifies L4 *after*.
- **Reflex has no tier** — it never queues. It is an *output mode*, not a priority level. (Originally called "URGENT"; renamed because a tier reads as "stronger priority on the same axis", which it is not.)

**Resource seizure = supersede, not negotiate.** A Reflex cannot use the Phase-46 cooperative cancellation (which waits for a checkpoint). It forcibly seizes via, by resource kind:

- **command-stream / actuators** → a **low-level arbiter override**: Reflex commands win while active; the displaced task keeps its logical hold but its commands are superseded, then control returns and the task **resumes or replans** (its world-model may be stale);
- **compute / attention** (the orchestrator's own) → a **drain**: suspend other work, redirect capacity.

NOT abstract locks — Reflexes are physical/operational-threat responses, so their resources are arbitratable command streams or compute, not database locks.

**The Reflex stays dumb (key invariant).** A cognitive Reflex ("subordinate Mind critical → orchestrator drops everything") must not put *problem-solving* inside the reflex. Decomposition:

> trigger → **Reflex** fires (instant: drain/suspend other work, escalate the crisis) → a **CRITICAL Signal/task** does the solving (deliberated, using the freed resources).

The Reflex **reallocates**; it does not think. A cognitive Reflex also has **no natural bound**, so it must keep a **hard floor that never starves the reflex/monitoring layer** (else a second crisis or a fall during the first is invisible — self-inflicted denial-of-service), plus the same refractory/hysteresis as Signals.

---

## §11 Communication channels (RESOLVED)

Two channels between L4 and a SubMind:

- **(a) L4-initiated** — an **on-demand one-shot read** (L4 wants the current value now, or is activating a dormant SubMind). *Not* cadence-driven — the adaptive cadence belongs to the SubMind's own loop.
- **(b) SubMind-initiated** — a **push**: the loop emits a Signal (attention shift) or a Reflex (bypass). Covers both threshold-reach and the "adrenaline" preempt.

Only the autonomous reading makes both channels coherent (a passive, L4-polled SubMind could not initiate (b)).

**Exact-crossing detection (OQ-C):** Signals are **always** adaptive latency-poll — a small bounded delay on a non-urgent need is fine. If a case needs *instant* detection, that case is a **Reflex**, not a Signal (the write-hook/arbiter exists only to feed Reflexes). So there is no per-Signal poll-vs-hook choice; it collapses into the Signal/Reflex distinction.

---

## §12 Unsatisfiable need (RESOLVED — OQ-unsat)

A need that cannot currently be resolved (battery low, no charger) is handled by **splitting retry from awareness**:

- **Tier never decays.** Criticality is a property of the need, not of solvability — a dying battery with no charger is exactly as critical as one with a charger. Decaying the tier would lie about urgency.
- **The cap is on retry activity only.** Retry backs off and resumes **event-driven** when the contended resource frees.
- Starvation was a misframing: an unsatisfiable need does not starve, because its resolver is **not running** (parked). The workers are free; lower-tier work proceeds. When the resource appears, the parked resolver fires and rightly takes precedence.

Two cases: **resource-unavailable** (resolver can't start → fully parked, zero runtime cost) and **runs-and-fails** (backoff makes attempts rare; each brief attempt at CRITICAL preempts, then dormant). **Never auto-give-up** — the need persists at its true tier, visible, until resolved, the vital recovers, or a human dismisses it.

---

## §13 Endowment + the `subminds` role-graph (RESOLVED — OQ-home)

- **Definition home:** a **new L2 role-graph `subminds`** (Global + Local). Closed role-set grows **13 → 14** (amends ADR-0150).
- **Runtime home:** the SubMind runtime class + scheduler + registry live in **L4**.
- **Endowment is a distinct process from skill-acquisition.** Skill = acquired ability to *do*; SubMind = endowed faculty that *conditions*. The two have **distinct concept / vocabulary / registry / lifecycle / audit** — but **reuse low-level primitives** (`register_capacity`, role-graph write, the ADR-0180 admin gate, audit events). Do **not** clone the entire skill installer (preflight/digest/records/driver/activation) just to rename it.
- The **teaching** path writes a record into `subminds` the same way an authored endowment would.

---

## §14 Concurrency + lifecycle (RESOLVED)

- **Scheduler:** a **single scheduler thread** owns *when* — a timer-heap of next-fire times; it sleeps until the earliest due, runs that check, reschedules at the new adaptive interval. Cheap checks run inline; heavy ones offload to the Phase-46 worker pool. (Thread-per-SubMind is rejected — it does not scale.)
- **MM safety:** SubMinds are **read-only** on the MM and **push to the signal queue** — never write MM. Contention is limited to short read-locks against the Phase-46 writer-preferred RWLock.
- **Lifecycle owner:** the per-session L4 **`SubMindRegistry`** (`start()` spins up active ones, the orchestrator toggles context-gated ones, `stop()` tears down).

---

## §15 Recursion — toward the "society of full minds"

The same `{sense → severity → Signal | Reflex}` machinery operates **SubMind → Mind** *and* **Mind → Mind-of-Minds**. The original three-tier vision falls out of one mechanism. The cost: the **resource model + arbiter must exist at every orchestration level**, not just the robot's motors.

**Out of scope for this design:** how full Minds compose/arbitrate among one another (the society-of-full-minds tier proper) was **not** designed here — only the recursion observation holds. It is its own construct and its own future chat.

---

## §16 What remains

**Tuning (not architecture):** cadence min/max bounds + hysteresis margins; the proximity→interval curve; severity→tier band edges; importance weights; retry backoff curve + the standing-pressure cap; the cognitive-Reflex floor.

**Implementation:**
- Reverse **ADR-0155** (resident monitor lifecycle returns — as an L4-owned scheduler, not the deleted L3 `start_resident`/`stop_resident`). See ADR-0188.
- New ADRs **0188 / 0189 / 0190**.
- **ADR-0150 amendment** — closed role-set 13 → 14 (`subminds`).
- Reconcile against the existing scaffolding (§17): the Phase-46 `MonitorSubscriptionRegistry` becomes the write-hook/arbiter feed for Reflexes; `TierEnum` + `attention_score` are reused as-is; the empty signal-source/ALS skeletons are either populated or retired per this model.

---

## §17 Grounding — existing scaffolding reused

A code grounding pass established the current state of the autonomy dimension (all skeletal/declarative unless noted):

| Component | State today | Role under this design |
|---|---|---|
| `KIND_MONITOR`, `iter_monitors` | Declarative only (ADR-0155 retired the loop) | Becomes the SubMind check-capacity declaration |
| `MonitorSubscriptionRegistry` (Phase 46) | Registry, no reactive firing | The write-hook/arbiter feed for Reflex instant-detection |
| signal-sources S1–S10 (Phase 47) | Empty skeletons, no emitters | Superseded by SubMind Signal emission |
| signal-triage worker (Phase 46) | Passthrough stub | Receives SubMind Signals → tier |
| ALS registry, 11 subsystems (Phase 47) | Empty | The (optional, core-L4) learnable-weight home, if ever used |
| `TierEnum` + `attention_score` (Phase 46/48) | Live | Reused unchanged — `(tier, attention_score)` heap key |
| dream-cycle timer (Phase 48) | Only live self-firing loop; re-exec stubbed | Precedent for autonomous loops; orthogonal |

**WSD detachment:** earlier framing treated the ALS priority-scorer (#10) as "owned by / colliding with WSD". That was wrong — it conflated an implementation-scheduling artifact (the WSD chat was slated to populate some ALS entries) with ownership. **WSD is a text subsystem built on top of MindsOS; it owns zero core mechanics.** All priority/scoring/learning here is core L4, consumer-agnostic.

---

## §18 Decision ledger (closed)

| ID | Question | Resolution |
|---|---|---|
| OQ-A | Autonomous or L4-polled? | **Autonomous** — SubMind owns its loop; channel (a) = one-shot read only |
| OQ-B | Emit tier or severity? | **Severity (physical)**; tier = fixed monotonic severity→tier mapping; never self-named |
| OQ-C | Exact-crossing for Signals? | **Always latency-poll**; instant-detection ⇒ it's a Reflex |
| OQ-D | Preempt vs reconcile? | **Derived from resource contention** (resolver declares exclusive resources) |
| OQ-Reflex | Forcible seizure? | **Supersede** — arbiter override (actuators) / drain (compute); stays dumb; recursive |
| OQ-norm | Severity normalization? | **severity = physical**, `attention_score = weight × severity` (L4) |
| OQ-unsat | Unsatisfiable need? | **Tier never decays**; backoff on retry; never auto-give-up |
| OQ-home | Where + how created? | New L2 `subminds` role-graph + L4 runtime; **endowment**, distinct from skill-acquisition |
| OQ-trigger | Signal vs Reflex choice? | **Declared predicate** (non-reconcilability, not magnitude) at endowment |

---

## §19 Implementation plan + build log (`feat/subminds`)

**Branch:** `feat/subminds` off `main`. **Base commit:** `ace98b4`
(`state: ratify Part-5 keep-deferred (R0 2026-06-23)`) — `main` tip at
branch-open. NOT a numbered phase.

### §19.1 Slice breakdown (4 slices; only Slice 1 built)

1. **Slice 1 — definition + autonomous sensing + Signal-to-heap (BUILT).**
   L2 `subminds` role-graph (Global form) + ADR-0150 §am-7 (13→14); L4
   `SubMind` runtime (adaptive cadence, storm suppression, severity→tier
   mapping, int `attention_score` scaling) + `SubMindScheduler`
   (timer-heap) + `SubMindRegistry`; live sense→emit→triage→executor heap
   with a **stub resolver**. Reverses ADR-0155's loop at L4.
2. **Slice 2 — resource model + arbitration.** `resources.py` (L4),
   tasks declare held resources, resolvers declare needs; reconcile /
   preempt-or-defer; real resolver dispatch; unsatisfiable-need policy.
   *Largest surface.* (`resolver_resources` already ships on the Slice-1
   definition, unconsumed.)
3. **Slice 3 — Reflex path.** Declared non-reconcilable predicate → fast
   capacity; the **net-new write-hook/arbiter feed** over
   `MonitorSubscriptionRegistry` (today a passive lookup, not a feed);
   supersede-not-cancel seizure; cognitive-Reflex floor.
4. **Slice 4 — Local scope + teaching + de-endowment + tuning.** Local
   `subminds` bootstrap (episodic_memories pattern); taught endowment;
   marker-only de-endowment (Phase-50 precedent); tuning knobs as config.

### §19.2 Grounding drift found vs the design (all reconciled in Slice 1)

- `MonitorSubscriptionRegistry` is a **passive lookup table**, not a
  reactive feed — the Reflex write-hook is net-new code (Slice 3), not a
  repurpose. (§17 wording is aspirational.)
- `attention_score` is an **int** heap key in `[0, 9999]`; severity is a
  float fraction → SubMind scales `round(weight × severity)`, clamped.
  Shipped executor key untouched.
- The shipped passthrough triage classifier is reused as-is: the SubMind
  computes its tier from the per-SubMind mapping and attaches it; the L3
  `decision.signal_to_tier` classifier is **not** used for SubMind
  signals (one global classifier cannot hold N band-sets).
- `subminds` is Global+Local by design; Slice 1 bootstraps **Global
  only** (authored, admin-gated). Schema is scope-agnostic.

### §19.3 Surfaces touched (Slice 1)

- **New (L2):** `mindsos_knowledge/schemas/subminds.py`.
- **Edited (L2 wiring, ADR-0150 §am-7):** `identifiers.py`
  (`ROLE_SUBMINDS`, `submind_definition_iri`, mint adapter + dispatch +
  prefix + kinds), `schemas/__init__.py`, `bootstrap.py`
  (`_GLOBAL_NAMED_ROLES` + `_APPLIES_AFTER_BY_ROLE`), `__init__.py`
  re-exports.
- **New (L4):** `mindsos_intelligence/submind.py`,
  `submind_scheduler.py`, `submind_registry.py`.
- **Edited (L4):** `signal_triage.py` (additive `set_on_classified`),
  `intelligence_layer.py` (`SubMindRegistry` wired into start/stop +
  `endow`), `__init__.py` exports.
- **Tests:** `tests/feat_subminds/` (5 files); updated forward the
  closed-set / global-graph-count sentinels in `tests/phase_13`,
  `tests/phase_14` (×4), `tests/phase_15a` (×2), `tests/phase_50`.

### §19.4 ADR-0150 §am-7 mechanics

Closed role-set **13 → 14** (`subminds`). Touched sentinels:
`_ROLE_SCHEMA_BUILDERS` size (13→14), `ALL_ROLES`/`UPPER_LAYER_ROLES`,
phase_14 `_EXPECTED_GLOBAL_ROLES` + global-graph count (10→11),
phase_15a bootstrap_global count (10→11), phase_50 closed-set (13→14).

### §19.5 Build/gate status + handoff

- **Authoritative gate (Linux, Docker, Py3.11, live FalkorDB) — GREEN
  2026-06-24:** `4069 passed / 11 skipped / 1 xpassed / 0 failed` on the
  full cumulative suite. Tag `feat-subminds-slice1-confirmed` at
  `cebd6ef`. Two gate-only fixes beyond the build: `mindsos_admin`
  `_GLOBAL_ROLE_ORDER` parity tuple (`a64e18d`) and 5 role-set /
  IRI-builder parity sentinels in phase_12/34/39 (`cebd6ef`) — both
  classes were invisible to the sandbox (the `mindsos_server`
  `datetime.UTC` / `typer` import gaps on Py3.10).
- **Sandbox dev-check (Linux, Py3.10):** `tests/feat_subminds` 57
  passed; phase_13/14 (non-CLI) + phase_46/47/48 green. Runtime
  behaviors verified: adaptive cadence, emit-once storm suppression,
  escalation-on-worsening-step, re-arm after reset margin, live
  scheduler→triage→heap path with correct tier + scaled score.
- **Sandbox-only non-failures:** phase_50 capability/audit tests +
  phase_15a/24 conftests need `datetime.UTC` (Py3.11) / `typer`, absent
  in the sandbox — these collect+pass on the Py3.11 gate host. Not code
  issues.
- **Pair-execution handoff (per HANDOFF / memory):** Cowork built the
  code; the **Mac** clears the stale `.git/index.lock`, opens
  `feat/subminds` off `ace98b4`, commits the design artifacts
  (SUBMIND_DESIGN_LOG.md, ADRs 0188/0189/0190, HANDOFF §6.0) + Slice 1,
  and pushes; **Linux** runs the authoritative cumulative gate. Do not
  run the gate on the Mac; do not git-mutate from the sandbox.
- **ADRs 0188/0189/0190 now `Accepted`** (gate green 2026-06-24). 0188
  + 0190 fully Slice-1; 0189 partial (§1/§4 shipped; §2/§3 → Slice 2).

### §19.6 Open implementation items the design deferred (unchanged)

Tuning: cadence min/max + hysteresis margins, proximity→interval curve,
severity→tier band edges, importance weights, retry backoff + standing-
pressure cap, cognitive-Reflex floor. Semantics: de-endowment
(marker-only, Slice 4). All carried into Slices 2–4.

---

## §20 Slice-2 design decisions (resolver model + resource arbitration)

Decided in the Slice-2 design chat (2026-06-25). Settled after 4 skeptical
passes (2 consecutive clean). These supersede any earlier Slice-2 framing.

**Resolver is goal-directed, not a fixed capacity/skill.** A SubMind's
resolver is a **goal** ("add energy to the system"), satisfied by a
**pipeline constructed at dispatch from whatever capabilities the system
currently has** (charger *or* battery-swap; drink *or* IV). Runtime
endowment fields (mirror the unconsumed `resolver_resources` pattern; no
L2 migration — Local persistence rides Slice 4):
`resolver_start_datastate`, `resolver_goal_datastate`,
`resolver_resources` (static, for the contention check),
`fallback_resolver` (a **direct** ask-human capacity).

**A capacity *is* a 1-step pipeline.** Registering a capacity registers
its input + output DataStates, so every capacity is itself a pipeline;
pipelines compose into larger pipelines. There is **no** "single
capacity vs pipeline" fork — the resolver always runs a pipeline; a
single capacity is the degenerate 1-step case.

**Real pipeline execution is a CORE component (not WSD).** The Phase-47
`execution.run` notional-step stub must become real capacity-step
execution (topological DAG walk → dispatch each step via `L4Dispatcher`
→ thread DataStates). Built at core, individualized, first consumer =
the SubMind resolver. Scope boundary: *Pipeline-step* execution now;
*Plan/Milestone* orchestration (MSUR/SCMS) stays where it is. (See
RULES §8 — subsystems own nothing architectural.)

**`PipelineNotFoundError` is a dont-know, not a failure.** Goal-
unreachable means "no capacity reaches a goal-DataState in the desired
direction" — an honest dont-know (maps to the ADR-0157 path-finding
family), not an exception. The SubMind then fires its `fallback_resolver`
(ask-human), so there is **always** a resolution path; the need persists
at its true tier until resolved / the vital recovers / a human dismisses
it. **Scope split:** Slice 2 catches unreachability at the arbiter
boundary → dont-know → ask-human fallback; the L3 finder refactor
(replace `PipelineNotFoundError` with a path-finding dont-know verdict
across `pipeline.py`, update composition-lifecycle) is a **separate
core-mod chat** — logged follow-up, not in Slice 2.

**Arbitration model (resource contention).** `resources.py` =
`ResourceLedger` (acquire/release/holder + on-release callback) +
`Contention` verdict — the reusable resource model the Slice-3 Reflex
path reuses. `SubMindArbiter` holds the stateful policy. Verdict
collapses (cooperative preempt cannot seize — it must wait for the
holder to yield): **resource free → dispatch now (reconcile =
independent concurrent task, `preempt=False`); resource contended →
park on that resource, plus a cooperative cancel iff the need outranks
the holder; resume event-driven on `ledger.release`.** Two park reasons
unify: resource-contended and means-unavailable (dont-know) both park +
resume event-driven. Tier never decays; never auto-give-up.

**Executor change is additive.** `submit(preempt: bool = True)` gates
the existing tier-based `_maybe_preempt_locked` (default = shipped
behavior, zero impact on Phase-47); the SubMind path passes
`preempt=False`. Optional `resource_ledger` injected (default None =
no-op); holds bracket the worker run-loop (register on run-start,
release on `finally`). `enqueue`/`submit` grow optional
`held_resources=()`. The orchestrator's own blind tier-preempt is **out
of scope** for Slice 2 (a logged follow-up — the design-log §8
"blind-preempt" reform).

**Self-contention guard (built form).** A running resolver registers its
own `resolver_resources` as held. To avoid a SubMind parking behind its
*own* in-flight resolver (self-deadlock), an escalation that arrives
while the resolver is in flight short-circuits **before** the contention
check: it updates the need's recorded tier/severity in place (dedup,
keyed by `submind_name`) but does **not** dispatch a second resolver. The
updated tier takes effect on the next dispatch (a retry, or a
resume-after-release). The heavier "cancel + redispatch the running
resolver at the higher tier" was considered and **deferred as tuning** —
it introduces a done-callback/resume race for marginal benefit (the
SubMind re-emits only on worsening steps, so escalations are sparse, and
tier governs queue ordering, not a running task).

**Recovery-clear.** Tier-never-decays means nothing drops a parked need
when the vital recovers. The registry detects the per-SubMind
`FIRED→ARMED` transition after `tick()` and calls `arbiter.clear(name)`
— no change to the frozen Slice-1 `tick()` contract.

### §20.1 Surfaces touched (Slice 2)

- **New (core L4):** `mindsos_intelligence/pipeline_execution.py`
  (`execute_pipeline` + `PipelineExecutionResult` — the real Pipeline-step
  executor, RULES §8 core component); `resources.py` (`ResourceLedger` +
  `ResourceHold` + `Contention`); `submind_arbiter.py` (`SubMindArbiter`).
- **Edited (L4):** `executor.py` (additive `submit(preempt=True,
  held_resources=())` + optional `resource_ledger` + run-loop hold
  bracketing); `submind.py` (resolver goal/start/fallback fields on
  `SubMindDefinition`); `submind_registry.py` (arbiter delegation +
  FIRED→ARMED recovery-clear; arbiter optional → Slice-1 stub preserved);
  `intelligence_layer.py` (build ledger + dispatcher + arbiter; `enqueue`
  `held_resources`; `resource_ledger` property); `__init__.py` exports +6.
- **Tests:** `tests/feat_subminds/` +4 files (pipeline executor, ledger,
  executor resources, arbiter policy). No role-set change → **role-set
  parity sentinels untouched** (landmine (a) avoided).

### §20.2 Build/gate status

- **Sandbox dev-check (Linux, Py3.10) GREEN:** `tests/feat_subminds` 57
  passed (37 Slice-1 + 20 Slice-2, no regression); `tests/phase_46/47/48`
  + `tests/phase_30` (pipeline) + `tests/composition_lifecycle` 210 passed
  (excluding the `typer`/CLI + `datetime.UTC` modules that only collect on
  the Py3.11 gate — landmine (b)). New modules are stdlib + the allowed
  `mindsos_capacity.tiers` downward import; layer-isolation green.
- **Authoritative gate (Linux, Py3.11, live FalkorDB):** PENDING —
  pair-execution: Cowork built the code; Mac commits/pushes
  `feat/subminds-s2` off `main`; Linux runs the cumulative gate with
  `--build`. Tag `feat-subminds-s2-confirmed` on green.
- **ADRs:** 0189 status → §2/§3 shipped; 0188 amendment-trail notes the
  `ResourceLedger` is the shared Reflex-seizure model (Slice 3).
