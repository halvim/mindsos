# PHASE_48_DESIGN_LOG — L5 v1: consolidation + dream hookup + retention monitoring + crash recovery + concepts docs

**Chat:** Phase 48 (final convergence — makes the Phase-47 chain artifacts
*persist* as episodes and wires dream as live re-execution). PHASE_MAP estimate
~400–700 LOC + 3–5 ADRs (0176–0180). **Design-pass first, then ship** — ship
shape is itself a pushback (PB-0; do NOT assume option-C combined).

**Status:** R0 open (design saturation). **No code written, no branch cut.**
Pre-impl pushback rounds (budget 2–3 per PHASE_43 §10.4) + a buildability scan
precede branching `phase-48`.

**Rail context:** All four Stream B rails + Phase-46 substrate + Phase-47
orchestrator closed. Phase 48 consumes the chain artifacts Phase 47 emits
(`chain_artifacts.py`, TaskRun root) + the surfaces Phase 47 explicitly left
open (S12 write-half, dream driver, MM `attention_score` already lands at 47).
Phase 49 (Integration C) exercises what 48 ships end-to-end.

---

## §0. Prereq check (run 2026-06-09) — TWO BLOCKERS surfaced

- `git tag --list | grep -E "phase-4[0-7]-confirmed"` → **40/41/42/43/44/45/46
  present; `phase-47-confirmed` ABSENT.** ✘ (the routing prompt's "40-47 all
  present" is false.)
- `main`-tip = `cd8abb0` ("Phase 47: L4 orchestrator …") = the Phase-47 squash
  itself. `PHASE_47_CONFIRMED.md` is **untracked** (`??`), `git_sha: cd8abb0`
  inside it. So the Phase-47 **ship-closure ceremony was never completed**: the
  squash landed on `main` but the confirm-doc + notes were never committed and
  no `phase-47-confirmed` tag was cut. (Distinct from the Phase-39/40/42/45
  tag-placement anomalies — this is an *un-run* closure, not a misplaced tag.)
- Working tree dirty: `M docs/future_work/L3_FUTURE_WORK.md` + a large untracked
  **Robot Demo** corpus (`confirmation_docs/ROBOT_DEMO_*`, `demo_ui/`,
  `prototype_zero/`, `sim/`, `web/`) + `PHASE_4{1,6}_NEXT_CHAT_PROMPT.md` +
  `DEMO_DERIVED_FEATURES_NEXT_CHAT_PROMPT.md`. **Never `git add -A`; stage
  selectively; leave the Robot Demo + next-chat-prompt files alone** (Phase
  46/47 prereq lesson).

### BLOCKER-1 — Phase 47 is unconfirmed/untagged

Phase 48 branches off `main`-tip, which **is** the Phase-47 squash `cd8abb0`, so
the *code* prereq is satisfiable. But:
- the `release.yml` gate (Phase-42 lesson) requires `PHASE_N_CONFIRMED.md` at the
  tagged commit;
- the **sentinel chain** is per-phase (§9) — the Phase-48 `test_adr_amendment_
  sentinels.py` chains off Phase-47's;
- the version high-water rule reads the **shipped manifest** `version`/`phase`,
  which Phase 47 bumped to 47 in-tree but never closed.

**Recommendation:** close Phase 47 first as a tiny pre-Phase-48 step — commit
`PHASE_47_CONFIRMED.md` + `notes/notes-phase-47.md` on `main`, tag
`phase-47-confirmed` at `cd8abb0`, push. Then branch `phase-48` off the tag.
**User decision required** (pair-execution: user runs git). Alternative: branch
`phase-48` off `cd8abb0` now and fold the Phase-47 confirm artifacts into the
Phase-48 ship — rejected: muddies two phases' closure and the high-water/sentinel
machinery.

### BLOCKER-2 — the D'1 KL hooks do NOT exist (scope discovery)

Carry-forward (d) says "confirm they exist or land them." **They do not exist.**
Repo-wide grep for `read_at_version` / `retire_version`:
- `mindsos_capacity/context.py:68-74` — a **Protocol stub** on `CapacityContext`
  ("concrete KL implementation lands Phase 48 (L0-21 / `kl.read_at_version`)").
- `mindsos_intelligence/mm_resolver.py:13-14` — a **comment** ("inline-on-retire
  (D'1) lands Phase 48 with `kl.read_at_version` / `kl.retire_version`").
- **No `def read_at_version` / `def retire_version` anywhere in
  `mindsos_knowledge/`.**

ADR-0161 §Decision *text* still reads "Phase 44 ships both," but the live tree
contradicts it — Phase-44 CR-4 (PHASE_MAP line 517 + CLAUDE.md Phase-44 block)
explicitly **deferred S6 `read_at_version`/`retire_version` → Phase 48**, freezing
only the marker name (`_retired_inline_pending`, ADR-0161 §3 + `RESERVED_
PROPERTY_KEYS`). **Probe action at R1:** confirm whether even the marker *write*
shipped at Phase 44 (`grep _retired_inline_pending mindsos_knowledge/`) — if not,
Phase 48 lands the hook + marker-write + read-consumer; if so, Phase 48 lands the
two KL methods + the read-time consumer only.

**Consequence:** Phase 48 has a real **L2 (`mindsos_knowledge`) surface** the
PHASE_MAP Phase-48 "Modules touched" list omits (it lists only `episodic_
memories.py` "rectified consumer paths" + the L4 `retention.py` consumer). This
is a scope delta to ratify, not a free call. ADR-0161 §Decision text needs an
amendment to match reality regardless.

---

## §0.1 Required-reading acknowledgement

- HANDOFF §1, §3.1.19 (Phase 46 substrate consumed), §3.1.20-equivalent (Phase 47
  ship — read via `PHASE_47_CONFIRMED.md` + `PHASE_47_DESIGN_LOG.md` since §3.1.20
  is not yet written into HANDOFF), §4/§4.1/§4.2 (L5 settled — three-sub-MM +
  6-level chain + D'1 retention), §9 (process discipline: `python3` host,
  pair-execution, squash-before-confirm, tag-at-confirm-artifacts-commit, docker
  rebuild, no `gh`/no `mindsos` CLI on the gate host → hand-write confirm doc via
  heredoc, BSD sed → perl, watch CI on the GitHub Actions web page, bump manifest
  `phase` field alongside `version`).
- POST_PHASE_38_PHASE_MAP §0, §1 (DAG + high-water rule + the **effectively
  10-surface** checklist incl. manifest `phase` field), the Phase 48 detail block
  (lines 826–914), §6 (post-49 sequencing).
- PHASE_47_DESIGN_LOG + PHASE_47_CONFIRMED — authoritative record of what Phase 47
  shipped + the explicit "Open for Phase 48" list (consolidation write path;
  Episode/Memory authoring; dream live re-execution + ALS + ReplanInjection;
  S12 write-half; D'1 + inline-on-retire).
- CHAT_B_DECISIONS: D-B47 (Episode/Memory schema + `memory_contains_episode`),
  D-B50 (crash recovery / checkpoint trigger set), D-B5/B6 (dream-as-live + ALS
  as sole learning track), D'1 retention, PB-QQ (retention monitoring v1 / policy
  v1.5).
- l5_mental_model_design_notes §4 (retention/consolidation/Episode/Memory/
  version-ref resolution) + §5 (retrieval/dream/ALS).
- ADR-0175 §amendment-1 (S12 write-half deferred to 48 — the authorization
  reconciliation is mine); ADR-0162 (dream contract) + `builtins/dream.py`
  (DreamCapacity/DreamDirective/ReplanInjectionDirective) + `intelligence_layer.py`
  (DreamCycleTimer — callback still unwired, default-absent injected callback).
- ADR-0161 (KL version-pinned read + retire hook — marker `_retired_inline_
  pending`; §Decision text stale per BLOCKER-2).

---

## §1. Design ground truth (implement; do NOT re-litigate)

From Chat B + l5 notes §4–§5 + the PHASE_MAP Phase-48 Locked-decisions row:

- **Consolidation = retain-by-default.** On task completion (success / failure /
  abort — all *complete* a task), L4 freezes the MM (final outcome metadata,
  end-time, late bindings) and writes it as an **Episode** entry to
  L2.`episodic_memories`, following KL's versioned role-graph pattern; then
  releases the live L5 instance. Opt-out per task. (l5 §4.1–§4.2.)
- **Episode shape (D-B47 / D-L2-17, live schema confirmed):** `task_input_ref`
  (XRef), `mm_root_ref` (XRef → frozen 3-sub-MM + outcome), `task_pattern_iri`
  (primary cluster key = last-active mapping), `outcome_classification`
  ∈ {succeeded, failed, low_confidence, asked_user, dont_know}, `crash_marker`
  (Optional[CrashInfo]), `consolidated_at`. Episode is a **frozen full MM** — 3
  sub-MMs + all chain artifacts + provenance + MSUR ledger + SCMS state + chain
  history (replanned artifacts marked `aborted_for_replan_at_level_L`).
- **Memory composite (D-B47 / D-L2-15):** clusters episodes by
  `task_pattern_iri`; **materializes on first episode** of a task-pattern;
  subsequent episodes attach via **`MEMORY_CONTAINS_EPISODE` EdgeType** (regular
  EdgeType, Memory → Episode within the same role-graph Schema per Phase-43
  impl-time discovery — *not* an IntergraphEdge despite the L5-notes §9 wording).
  Fields: `task_pattern_iri`, `created_at`, `admin_notes`, `rejected_promotions`
  (denormalized; L0 audit-log authoritative). Promotion granularity is
  per-episode; Memory is organizational scaffolding.
- **Episode immutability (D-B47 §4.5):** append-only externally; the *only*
  internal mutation is lazy inline-on-retire. Admin verify-queue acts on Memory,
  never Episodes.
- **D'1 retention (§4.4):** refs are version-pinned `(node_iri, version_int)`
  tuples, pinned **at instantiation** (during execution), not at consolidation.
  KL keeps versions side-by-side (Phase 11). On `kl.retire_version()` (distinct
  from `deprecate_version`), affected episodes inline the retired content
  **lazily on first read after retire**; the inlined content is a full snapshot;
  its outgoing refs stay version-pinned and inline on *their* next read (bounded
  transitive inflation).
- **Crash recovery (D-B50):** checkpoint trigger set = LifecyclePhase
  transitions + per-Milestone completion + per-replan event. On L4 startup, scan
  for unconsolidated MMs; consolidate with `crash_marker` set. Physical
  checkpoint mechanism = L4-implementation (mine to pick).
- **Dream-as-live (D-B5/B6, §5.2):** dream = load an episode → materialize a
  fresh MM by **deep-copy** (`fork_dream_mm` exists) → re-execute as if live
  through the phase-loop. ALS signals fire per normal Chat A mechanics; **no
  separate dream-learning track.** 3 v1 pipelines all at **TaskRun level**:
  `dream.maintenance` (replay_recorded), `dream.exploration` (re_execute_
  capacities), `dream.retry` (re_execute_capacities + replan-injection).
  Signals carry `dream_source_episode_iri`. Dream runs under the owning user's
  session; ALS tags Local-only.
- **Retrieval is L3, not L5** (§5.1) — out of scope here except as a dependency
  the dream episode-loader uses (or a thin L4 read).
- **Retention monitoring (PB-QQ / PB-AA):** v1 ships **instrumentation only** —
  episode-count + episode-size histogram + Falkor-row-count exporters. Retention
  *policy* = v1.5 if growth observed. Do not build aging/eviction.
- **L4-vs-L3 strict line (Chat A).** L4 = data-structure mutations, state-machine
  transitions, lock arbitration, lifecycle, threading, dispatch. Every
  decision/computation is an L3 capacity invocation. The KL *write* is the L3
  `consolidate:mm` surface (ADR-0146 symmetric write contract). This line is the
  fulcrum of PB-1 and PB-2 below.

---

## §2. S-surface enumeration (L5 v1)

Mirror of the Phase 42/44/45/46/47 S-surface format. Each surface tagged with its
**real consumer** (consumer-discipline test).

| S | Surface | Module | Real consumer | Ship at 48? |
|---|---|---|---|---|
| **S1** | MM consolidation write path — freeze MM + assemble Episode record + dispatch the KL write; release live instance | `mindsos_intelligence/consolidation.py` (NEW) | orchestrator Phase-5→complete seam (Phase-47 stub) | **Yes** |
| **S2** | `consolidate:mm` body finalized — full D-B47 Episode shape (6 fields) + S12 write-half migration off dict context | `mindsos_capacity/builtins/consolidate.py` (3rd touch) | S1 | **Yes** |
| **S3** | Memory materialize-on-first-episode + `MEMORY_CONTAINS_EPISODE` edge wiring | consolidate.py / a 2nd capacity / S1 (PB-6 fork) | S1; retrieval; dream rejected_promotions | **Yes** |
| **S4** | S12 write-half: `consolidate`/`trace` off dict `context` → CapacityContext + authorization reconciliation + dispatch `effect_iri` resolution | `runtime.py`/`capacity_layer.py` + bodies + `dispatch.py` | S1 (wired consolidation = the real consumer) | **Yes (PB-2)** |
| **S5** | Dream driver — wire DreamCycleTimer callback → episode select → `fork_dream_mm` → re-execute via phase-loop → ALS firing + ReplanInjectionDirective consumption | `mindsos_intelligence/dream_cycle.py` (NEW) + `intelligence_layer.py` callback | dream timer; ALS; S1 episode corpus | **Yes (PB-3)** |
| **S6** | D'1 KL hooks — `kl.read_at_version` + `kl.retire_version` + (verify) marker write | `mindsos_knowledge/…` (NEW — see BLOCKER-2) | S7; episode read | **Yes (scope delta)** |
| **S7** | D'1 read-time consumer — consult `_retired_inline_pending` on episode read; lazy inline + bounded transitive inflation | `mindsos_intelligence/retention.py` (NEW) | episode read (dream/retrieval/inspection) | **Yes (PB-4)** |
| **S8** | Crash recovery — checkpoint trigger set (LifecyclePhase/Milestone/replan) + L4-startup unconsolidated-MM scan → consolidate with `crash_marker` | `mindsos_intelligence/crash_recovery.py` (NEW) + orchestrator/`intelligence_layer.start` hooks | L4 startup; S1 | **Yes (PB-5)** |
| **S9** | Retention monitoring instrumentation — episode-count + size histogram + Falkor-row-count exporters | `mindsos_intelligence/monitoring.py` (NEW) | ops/inspection; Phase-49 exports first numbers | **Yes (instrumentation only)** |
| **S10** | `episodic_memories.py` rectified consumer paths (Episode/Memory write helpers used by S2/S3) | `mindsos_knowledge/schemas/episodic_memories.py` | S2/S3 | **Yes** |
| **S11** | 3–5 new ADRs 0176–0180 (D'1 retention; three-sub-MM composition; Episode immutability; lazy inline-on-retire; dream-as-live + ALS-sole-track) + ADR-0161 §am + ADR-0175 §am-2 (write-half close) | `docs/decisions/adr/` | ratification | **Yes (count = PB-7)** |
| **S12** | Docs — `concepts/layers.md` + `concepts/society-of-mind.md` + `getting-started/facts-and-figures.md` (NEW) + amend `concepts/episodic-memories.md` + `concepts/dream.md` | `docs/` | confirm; `mkdocs build --strict` | **Yes** |
| **S13** | 10-surface version bump 47→48 (8×`__version__` + pyproject + manifest `version` **and** `phase` + compose prod/test tags + export-slate sentinels) | manifest/pyproject/versions/compose/sentinels | release | **Yes** |

**Deferred / not-in-scope (consumer discipline):** retention *policy* / aging
(v1.5); cross-level dream variants (v2+); retrieval family bodies (WSD install);
real ALS mechanisms (WSD install — Phase 48 only fires signals into skeletons);
Local→Global episode promotion (no Global L5); teaching-mode episode authoring
(v3+).

---

## §3. Genuine design forks (pushbacks — options + pick)

Provisional picks; pre-impl rounds (§5) may revise.

### PB-0 — Ship shape + Phase-47 closure (HEADLINE)

**Concern.** Phase 48 crosses **L5 + L4 + L2** (5 new L4 modules + consolidate
3rd touch + trace migration + 2 new KL methods + episodic_memories helpers + 3
docs + 3–5 ADRs + 10-surface bump). Plus BLOCKER-1 (Phase 47 unconfirmed). Two
questions: (a) close Phase 47 first? (b) one branch or split?

- **Opt A — close Phase 47, then one `phase-48` branch with a logical commit
  split, single cumulative gate at confirm (Recommended).** Pre-step: commit
  Phase-47 confirm artifacts + tag `phase-47-confirmed` at `cd8abb0`. Then
  `phase-48` off the tag. Commit order inside the branch: **(1)** S6 KL hooks +
  S10 helpers (L2 foundation, gated by a targeted `pytest mindsos_knowledge
  tests/phase_44`) → **(2)** S4 S12 write-half + S2 consolidate finalize + S3
  Memory (the write path) → **(3)** S1 consolidation.py + crash-recovery S8 +
  wire the orchestrator seam → **(4)** S5 dream driver + S7 retention read
  consumer → **(5)** S9 monitoring + S12 docs + S13 bump. Targeted test runs
  between groups; full ~32-min cumulative gate only at confirm (PHASE_47 PB-A
  precedent — one branch, no double full gate).
- **Opt B — fold Phase-47 confirm into Phase-48 ship.** Cons: two phases'
  closure entangled; high-water/sentinel machinery muddied. Rejected.
- **Opt C — two PRs / two full gates.** Cons: second ~32-min docker cycle not
  worth it (Phase-46/47 collapse precedent). Rejected.

**Pick: Opt A.** **User ratification required** on closing Phase 47 first.

### PB-1 — Consolidation write-path division (L4 `consolidation.py` vs L3 `consolidate:mm`) — HEADLINE

**Concern.** The PHASE_MAP lists *both* `consolidation.py (NEW; MM-freeze +
Episode write path)` *and* `consolidate.py (writes new Episode + Memory entry
shape)`. Two modules both claiming "the Episode write" is the central ambiguity.
The L4-vs-L3 strict line resolves it, but the exact seam is a fork. Today
`consolidate:mm` writes a **single Episode node** from `record["value"]` +
`record["episode_id"]` via `handle.write_and_validate` — it does **not** assemble
the 6-field D-B47 shape, does not read the chain, does not touch Memory.

- **Opt A — L4 freezes + assembles; L3 validates + writes (Recommended).**
  `consolidation.py` (L4): acquire MM writer lock, freeze the 3-sub-MM root +
  outcome, walk the TaskRun chain to assemble the Episode **record** (resolve
  `task_input_ref`/`mm_root_ref` XRefs, `task_pattern_iri` = last-active
  MappingResult, `outcome_classification` from TaskRun, `consolidated_at`,
  `crash_marker` if set), then **dispatch `consolidate:mm`** (L3) which runs the
  semantic validator + performs the KL write. Memory materialize + edge =
  PB-6. Matches the strict line: assembly/freeze (data mutation) = L4; the KL
  write surface stays L3 (ADR-0146).
  Pros: clean layer split; single KL write surface; consolidate.py stays the
  sole `episodic_memories` writer. Cons: the Episode record crosses the L4→L3
  dispatch boundary as a payload — must fit `DS_MM_COMPOSITE_INSTANCE` shape
  (widen the DataState contract).
- **Opt B — L4 `consolidation.py` performs the KL write directly; `consolidate:mm`
  retired/bypassed.** Pros: one module. Cons: violates "L3 is the write surface"
  + ADR-0146 symmetric write contract; orphans a shipped capacity; re-opens the
  S12 reconciliation in the wrong direction. Rejected unless PB-2 forces it.
- **Opt C — `consolidate:mm` does everything (freeze + assemble + write), L4
  just dispatches.** Cons: freeze is a *live-MM mutation under the MM writer
  lock* — an L4 substrate concern the capacity has no lock handle for; pushes
  threading into L3. Rejected.

**Pick: Opt A** — but it's coupled to PB-2 (the capacity needs a principal to
write). **The DataState-shape widening (Episode record as the consolidate input)
is the concrete impl-lock to confirm at R1.**

### PB-2 — S12 write-half authorization reconciliation (ADR-0175 §am-1) — HEADLINE

**Concern.** The crux the prompt assigns me. `CapacityContext` is
**authorization-free** (10 typed fields incl. `session_id`/`user_id`/`kl`/`cl`,
**no Session object**). But `consolidate`/`trace` bodies call
`kl.writeable(session, …)` + `session.has(CAN_WRITE_GLOBAL)` — they need the
**Session object**. ADR-0170 §Decision-1 froze "authorization-free context";
ADR-0175 §am-1 deferred the reconciliation to 48 with the real consumer (wired
consolidation). Three reconciliations:

- **Opt A — L4 dispatch performs the gated KL write; capacity body becomes
  pure-assemble (Recommended, leaning).** `dispatch.py` already holds the
  IntelligenceLayer session + gates on `effect_iri`. Move the `kl.writeable` call
  *out* of the capacity body into the L4 dispatcher: the body validates +
  returns the validated node value (a *decision/computation*, L3); the
  dispatcher, having gated `effect_iri` against the session's granted caps,
  performs the `kl.writeable(session,…).write_and_validate(...)` (the *mutation*,
  L4). This **honors** both ADR-0170 (context stays authorization-free) and the
  L4-vs-L3 line (write = data mutation = L4; validation = L3). Reframes ADR-0146:
  the symmetric *contract* (validate-then-write) holds, but the write *executor*
  is L4, not the capacity.
  Pros: no Session on the context; single gate choke point already exists; closes
  PB-23 for good. Cons: re-reads ADR-0146 "L3 is the write surface" as "L3 is the
  write *decision* surface"; needs an ADR-0146/0147 amendment; `trace:problem`
  (Global, cap-gated) migrates the same way for consistency even though its
  consumer isn't wired at 48.
- **Opt B — principal on the context.** Add a `session` (or a narrow
  `WriteAuthorization`/capability-token) field to `CapacityContext`. Pros:
  smallest body change (s/dict/context.session/). Cons: **breaks ADR-0170
  §Decision-1** explicitly; puts authorization back inside L3; the exact thing
  the reframe removed. Rejected unless Opt A's ADR churn is judged too large.
- **Opt C — refactor `kl.writeable` to take `(session_id, capability_set)`
  instead of a Session.** Pros: CapacityContext's typed fields suffice; cleanest
  semantics. Cons: an L2 signature change with a corpus of Phase-33/34/44
  callers + tests; widest blast radius; arguably out of a v1 L5 phase.

**Pick (RATIFIED Round 1 — refined Opt A "pre-authorized write capability"):**
The naive options force a bad trade — Opt B hands L3 a `Session` it can call
`.has()` on (structurally re-opens L3-side authorization, the exact thing the
strict line + ADR-0170 forbid, and the contract WSD builds against); naive Opt A
breaks ADR-0146 ("L3 validates *and* writes") and needs a `_CapacityBase`
write-target declaration. **The dominating third form:** L4 `dispatch.py` — after
gating `effect_iri` against the session's granted caps — injects a **session-bound,
pre-authorized `writeable` callable** onto `CapacityContext`. The body calls
`context.writeable(role=…, scope=…, version=…)` → handle → `validate_node` +
`write_and_validate`, exactly as today.
- **ADR-0146 intact** — L3 still validates+writes through the handle.
- **ADR-0170 intact** — context carries a narrowed *capability* (a callable that
  only mints write-handles for the bound session), not a principal and not an
  auth decision. L3 cannot call `.has()` — there is no session to query.
- **Gate in L4** — `effect_iri` subsumes `trace`'s `session.has(CAN_WRITE_GLOBAL)`;
  that check leaves the body.
- **No `_CapacityBase` change, no write-target declaration** — role/scope stay in
  the body (it knows what it writes). Body migration ~1 line each
  (`kl.writeable(session,…)` → `context.writeable(…)`, drop `.has()`). 2 test
  files migrate. Closes PB-23 without parking the authorization-free principle.
R1 probe still due: census `kl.writeable(` callers; confirm no non-
consolidate/trace production caller; confirm `CapacityContext` is a frozen
dataclass that admits a new callable field.

### PB-3 — Dream driver live re-execution design (S5)

**Concern.** Wire the unwired DreamCycleTimer callback. The substrate exists:
`DreamCycleTimer` (injected callback, default absent), `fork_dream_mm` (deep-copy
primitive), `dream.*` capacities emit `DreamDirective(execution_policy,
entry_point, replan_injection?)`. Open: (a) **episode selection** — which episode
does a tick dream over? (b) **how re-execution enters the orchestrator** —
re-enqueue `run_lifecycle` with a pre-loaded MM, or a dream-specific entry? (c)
ReplanInjectionDirective consumption by `replan_check`. (d) ALS signal tagging.

- **Opt A — minimal closed-loop v1 (Recommended).** Tick → invoke the 3 `dream.*`
  capacities (each reads a candidate TaskRun from the episode corpus → emits a
  DreamDirective; `dream.retry` only on failed episodes) → for each directive:
  load the Episode → `fork_dream_mm` deep-copy → **enqueue a DREAM-tier task
  closure** that runs the existing phase-loop over the forked MM from
  `entry_point` (= latest-active TaskRun, v1), under the owning session. Signals
  emitted during re-exec carry `dream_source_episode_iri`. `dream.retry`'s
  ReplanInjectionDirective is injected at the replan-check seam (force-replan at
  the injected level). Episode selection v1 = **policy-free**: each capacity's
  body picks (its v0 placeholder picks latest-active; real policy = WSD/retrieval
  install).
  Pros: exercises timer→capacity→fork→phase-loop→ALS end-to-end on real episodes
  (which exist after S1); reuses the Phase-47 orchestrator wholesale. Cons:
  episode-selection is thin (delegated to capacity bodies); ReplanInjection seam
  needs a hook in `replan_check`.
- **Opt B — wiring + synthetic only (Phase-47 PB-3 Opt-A shape), real re-exec to
  WSD.** Cons: the prompt names dream live re-execution as core Phase-48 scope;
  episodes now exist (S1), so the deferral rationale is gone. Rejected.

**Pick: Opt A.** R1 impl-locks: (1) DREAM-tier exists in `TierEnum`? probe; (2)
the phase-loop must accept a pre-instantiated MM (not just `task_input`) — confirm
`run_lifecycle` signature admits a forked-MM entry or add a `dream_entry` param;
(3) ReplanInjection consumption point in `replan_check`. **User input welcome** on
whether v1 dream must demonstrate a *promotion candidate* surfacing (§5.3) or just
the re-exec + ALS loop (lean: re-exec + ALS only; promotion-candidate queue =
WSD).

### PB-4 — D'1 inline-on-retire mechanism + read-consumer home (S7)

**Concern.** Land the lazy inline. The marker (`_retired_inline_pending`) is a
node property frozen by ADR-0161. Open: where does the read-time consultation
live, and what does "first read after retire" mean operationally?

- **Opt A — consumer in L4 `retention.py`, invoked on episode load
  (Recommended).** Any path that *loads an episode for use* (dream loader,
  inspection, retrieval-result hydration) routes through a `retention.resolve_
  refs(episode)` helper: for each version-pinned `(iri, version)` ref, call
  `kl.read_at_version(iri, version)`; if the version node carries
  `_retired_inline_pending`, inline a full snapshot into the episode + clear the
  pending marker for that ref; inlined content's outgoing refs stay pinned and
  inline on *their* next `resolve_refs` (bounded transitive inflation —
  one level per read). Pros: L4 owns episode lifecycle; KL stays a pure
  version-store; matches l5 §8 "marker consulted on episode read."
  Cons: every episode-load site must route through the resolver (discipline, not
  enforced by types).
- **Opt B — consultation inside `kl.read_at_version` itself (L2).** Pros: can't
  be bypassed. Cons: KL would mutate episode content on read — a read with a
  write side-effect across role-graphs; violates KL's read/write separation +
  Episode immutability is an L5 invariant KL shouldn't own. Rejected.

**Pick: Opt A.** Impl-locks: the marker is **per-retired-version-node**, so
"inline" writes into the *episode* (the referrer), not the retired node;
Episode-immutability §4.5 carves this out explicitly ("the only internal mutation
permitted is lazy inline-on-retire"). Test: retire a pinned version → first
episode read inlines + transitive ref inlines on second read.

### PB-5 — Crash-recovery checkpoint granularity + mechanism (S8)

**Concern.** D-B50 fixes the *trigger set* (LifecyclePhase transitions +
per-Milestone completion + per-replan event) and the *startup scan* +
`crash_marker`. But the **physical mechanism is mine**, and the Phase-47
worker-per-task model makes it load-bearing: the MM is **in-process working
memory**, only written to Falkor at consolidation. A crash mid-task loses the MM
entirely **unless** checkpoints flush it. So "scan for unconsolidated MMs at
startup" presupposes checkpoints already persisted *something* to scan.

- **Opt A — checkpoint = flush the live MM to a Falkor staging area at each
  trigger; startup scans the staging area (Recommended, leaning).** At each
  trigger, serialize the MM root (or a dirty-delta) to a `mm_checkpoints`
  staging location (Falkor, per ADR-0121); mark `consolidated=false`. On clean
  consolidation, the Episode is written + the checkpoint cleared. On startup,
  scan staging for `consolidated=false` MMs → consolidate each with
  `crash_marker`. Pros: the only way the startup scan has anything to find;
  re-uses the persister. Cons: per-trigger Falkor write cost (PHASE_MAP flags
  "bootstrap-time overhead, configurable"); checkpoint serialization format is
  new work; arguably heavier than ~400–700 LOC implies.
- **Opt B — checkpoint = a lightweight progress marker only (no MM flush); on
  crash, the in-process MM is lost; startup scan finds the marker and records a
  `crash_marker` "lost" Episode stub.** Pros: cheap; small LOC; matches the
  literal "scan + crash_marker" wording without an MM serializer. Cons: no
  recovery of *content*, only a tombstone — is that "crash recovery"? Honest but
  thin.
- **Opt C — defer the physical mechanism; ship the trigger-set hooks + startup-
  scan skeleton + `crash_marker` plumbing as no-op-until-persister.** Cons:
  leaves the headline feature untested end-to-end; the PHASE_MAP pass-criterion
  is "simulated crash + restart produces consolidated Episode with crash_marker"
  — Opt C can't satisfy it.

**Pick (RATIFIED Round 1 — Opt B, tombstone with useful payload).** Full MM flush
(Opt A) is wrong for v1 on three counts: (1) **value** — a crashed task's MM is
partial/mid-Milestone, so recovered *content* can't be meaningfully dream-replayed
or inspected; (2) **cost** — per-trigger Falkor flushes + a mid-flight MM
serializer likely blow the ~400–700 LOC budget shared with consolidation/dream/
D'1/monitoring; (3) **posture** — the phase ships retention as instrumentation-only
(PB-QQ → policy v1.5); a heavy checkpoint engine contradicts it. Crash recovery
must deliver at v1: clean startup (no orphaned in-flight tasks), a crash record
(audit), task preservation for re-submit. A marker delivers all three. **Impl:**
write a small durable marker at each D-B50 trigger carrying `task_input_ref` +
last LifecyclePhase + last Milestone + `task_pattern_iri` (once mapped); on
startup scan `consolidated=false` markers → emit a `crash_marker` Episode from
that metadata (`mm_root_ref` null/partial). `CrashInfo` = {last_phase,
last_milestone, detected_at, recovered=False}. Satisfies the literal
pass-criterion; content recovery is a clean v1.5 swap (marker → MM staging flush)
if observed crash rates justify. Opt C rejected (can't pass the criterion).
**Marker store:** Falkor staging node (consistent with the Phase-44
Falkor-only persister; avoids re-opening the deferred SQLite persister) — R1
impl detail, not a fork.

### PB-6 — Memory materialization home (S3)

**Concern.** Memory materializes on first episode per task-pattern + wires
`MEMORY_CONTAINS_EPISODE`. Where?

- **Opt A — inside `consolidate:mm` (Recommended).** The capacity already holds
  the KL writeable handle for `episodic_memories`; after writing the Episode it
  checks "does a Memory for this `task_pattern_iri` exist? if not, materialize;
  then add the edge." Single write surface, single dispatch.
  Pros: one capacity, one role-graph handle, atomic-ish. Cons: widens the
  capacity body's responsibility beyond "write one node."
- **Opt B — a second L3 capacity `consolidate:memory` dispatched by L4 after
  the Episode write.** Pros: single-responsibility capacities. Cons: two
  dispatches, two writeable handles, ordering/atomicity concern across them; more
  surface for v1.

**Pick: Opt A.** Minor fork; not a blocker. Confirm the "Memory exists?" read
uses an existing KL read (versions_in_role / a node-exists query) at R1.

### PB-7 — ADR count + numbering (minor)

**Pick (provisional):** 5 ADRs **0176–0180** — 0176 MM consolidation write path +
freeze/assemble/dispatch division (PB-1) + Episode authoring; 0177 D'1 retention
+ version-pinned refs + lazy inline-on-retire read-consumer (PB-4); 0178 dream
live re-execution driver + ReplanInjection consumption + ALS provenance (PB-3);
0179 crash recovery checkpoint mechanism + startup scan (PB-5); 0180 retention
monitoring instrumentation + three-sub-MM consolidation framing + Episode
immutability ratification. **Plus amendments:** ADR-0175 §am-2 (S12 write-half
close — PB-2), ADR-0161 §am (correct the stale "Phase 44 ships both" + record the
Phase-48 landing), ADR-0146/0147 §am (write-executor-is-L4 reframe, if PB-2 Opt A
holds). Lock count/numbering at R1 after the transcription-parity probe (highest
ADR on disk = 0175 → 0176–0180 free; verify).

### PB-8 — `trace:problem` migration scope (minor)

**Concern.** S12 write-half names *both* `consolidate` and `trace`. `trace:
problem` is Global, cap-gated (`CAN_WRITE_GLOBAL`), and its consumer is **not**
wired at 48 (problem-trace is written by the orchestrator failure path, Phase 47
skeleton). Migrating it for consistency vs consumer discipline.

- **Opt A — migrate both for one coherent write-path contract (Recommended).**
  The PB-2 reframe (L4 performs the gated write) must apply uniformly or the dict
  path lingers. trace's L4 consumer is the Phase-6 failure path (skeleton at 47,
  but it *does* dispatch). Migrate both; the synthetic gate test covers trace.
- **Opt B — migrate consolidate only; leave trace on the dict path.** Cons:
  dual contract lingers (the PB-23 smell); trace re-migrated later. Rejected for
  the same reason PB-1 picked the hard split.

**Pick: Opt A** (migrate both). Low cost once the dispatcher write-executor
exists.

---

## §4. Carry-forward consumption map (Phase 47 "Open for Phase 48" → 48)

| Source | Carry | Phase 48 disposition |
|---|---|---|
| PHASE_47_CONFIRMED "Open" (a) | MM consolidation write path — replace orchestrator stub seam | **S1 + PB-1** (L4 freeze/assemble, L3 write) |
| (a) | Episode/Memory authoring | **S2/S3 + PB-1/PB-6** |
| (b) | S12 write-half: consolidate/trace off dict context + `kl.writeable(session)` reconciliation + dispatch `effect_iri` resolution | **S4 + PB-2** (L4 performs gated write; ADR-0175 §am-2) |
| (c) | Dream driver: timer callback → episode → fork_dream_mm → phase-loop → ALS + ReplanInjection | **S5 + PB-3** |
| (d) | D'1 retention + lazy inline-on-retire via `kl.read_at_version`/`kl.retire_version` (confirm exist or land) | **S6/S7 + PB-4 — they do NOT exist (BLOCKER-2); Phase 48 LANDS them** |
| (e) | Crash recovery (checkpoint trigger set + startup unconsolidated-MM scan) | **S8 + PB-5** |
| PHASE_47 PB-6 (shipped) | `attention_score` write-through to TaskRun | **already shipped at 47** (no Phase-48 work) |

---

## §5. Pre-impl pushback rounds (saturation tracker)

Budget 2–3 rounds (PHASE_43 §10.4) + a buildability scan before branching.
Saturation signature = a round producing impl-locks only, zero reversals.

- **Round 0 (this document) — CLOSED 2026-06-09.** S-surfaces S1–S13 enumerated;
  forks PB-0…PB-8 surfaced with provisional picks; 2 blockers raised
  (Phase-47 unconfirmed; D'1 KL hooks absent).
- **Round 1 — CLOSED 2026-06-09 (blocker resolution + 2 headline forks decided).**
  - **BLOCKER-1 RESOLVED.** Phase 47 closed: Mac/Linux had diverged Phase-47
    squashes off common ancestor `3cdfc5a` (Mac `cd8abb0`, Linux `6f49524`);
    Linux line is canonical — `6f49524` (squash) → `db1a562` (confirm doc, tagged
    `phase-47-confirmed`, `origin/main`, release green). Mac `main` repointed to
    `origin/main` via `git reset --hard` (redundant `cd8abb0` discarded; no work
    lost — content lives on `6f49524`); `L3_FUTURE_WORK.md` edit stashed/popped.
    `main` = `db1a562` = tag. ✔
  - **BLOCKER-2 ACCEPTED (scope delta).** D'1 KL hooks don't exist; Phase 48 lands
    `kl.read_at_version` + `kl.retire_version` (+ verify/land marker write) — an
    L2 `mindsos_knowledge` surface beyond the PHASE_MAP "Modules touched" list.
    ADR-0161 §Decision stale text gets an amendment. ✔
  - **PB-2 = refined Opt A** (pre-authorized `writeable` capability on
    `CapacityContext`; gate in L4 `dispatch.py`; ADR-0146 + ADR-0170 both
    preserved; no `_CapacityBase` change). User delegated the analysis; picked
    over raw-Session (Opt B, structural L3-auth risk) and naive-Opt-A (ADR-0146
    break + write-target declaration). ✔
  - **PB-1 LOCKED by PB-2** — L4 `consolidation.py` freezes+assembles the 6-field
    Episode record + dispatches `consolidate:mm`; body writes via
    `context.writeable`. ✔
  - **PB-5 = Opt B** (tombstone marker with useful payload; content recovery →
    v1.5). User delegated; decided on value/cost/posture grounds. ✔
  - PB-3 / PB-4 / PB-6 / PB-7 / PB-8 picks **stand**; open to contest in Round 2.

- **Round 2 — CLOSED 2026-06-09 (grounding probe; impl-locks only; ZERO design
  reversals → saturation signature).**
  - **Highest ADR = 0175** → 0176–0180 free (PB-7 confirmed). `TierEnum.DREAM = 3`
    present (default score 10) — PB-3 tier exists.
  - **`CapacityContext` = `@dataclass(frozen=True)`, 10 fields, `session_id`/
    `user_id` as strings (no Session)** → PB-2 adds an 11th field `writeable:
    Optional[Callable]=None` populated by `dispatch.build_context` for write-bodies.
    `KLHandle` Protocol already stubs `read_at_version`.
  - **`kl.writeable` census:** exactly **2 production callers** (`consolidate.py:145`,
    `trace.py:128`); `knowledge_layer.py:400` is the def's own error string, not a
    caller; **7 test files** reference `.writeable(` — triage at impl (only those
    exercising consolidate/trace via dict context migrate; direct-KL-setup tests
    don't). PB-2 blast radius confirmed small.
  - **S6 SCOPE WIDENED (impl-lock, not reversal).** `_retired_inline_pending`
    appears **nowhere** in `mindsos_knowledge`/`mindsos_core`. Phase 44 shipped
    **none** of ADR-0161's D'1 forward-contract — not the marker write, not the
    `RESERVED_PROPERTY_KEYS` entry, not `read_at_version`/`retire_version`. Phase
    48 lands the **entire** D'1 stack: both KL methods + marker write + reserved-key
    registration (`mindsos_core/schema/validation.py`) + the read consumer
    (`retention.py`). ADR-0161 §Decision/§Implementation text is aspirational/stale
    → amend to "Phase 48 lands."
  - **PB-2 gate bug (impl-lock).** `dispatch.required_capability_for` v0 demands
    `CAN_WRITE_GLOBAL` for *any* write-body, but `consolidate:mm` writes **Local**
    (own user) → a normal session would be wrongly denied. PB-2 impl splits
    **local-write (no cap; `kl.writeable` enforces own-user scope)** from
    **global-write (`CAN_WRITE_GLOBAL`; e.g. `trace`)**. This is the deferred
    "effect_iri-driven capability resolution → 48."
  - **PB-3 impl-lock + micro-call.** `run_lifecycle(task_input, *, tier, executor,
    task_id)` takes the MM via the orchestrator **constructor** (`self._mm`) and
    always enters at `phase_1.run(...)`. v1 dream: dream_cycle builds an
    orchestrator over the `fork_dream_mm` copy, seeds the episode's `task_input`,
    runs the full lifecycle **live**, tags signals `dream_source_episode_iri`.
    `replay_recorded` vs `re_execute_capacities` *behavioral* differentiation
    (recorded-output replay) needs a dispatcher "return recorded outputs" mode with
    **no v1 consumer** → deferred to WSD; v1 records the policy + fires signals,
    runs both as live re-exec. `dream.retry`'s ReplanInjectionDirective injected at
    the replan-check seam.
  - **PB-1 no DataState change.** `DS_MM_COMPOSITE_INSTANCE` = `{"episode_id": str,
    "value": Any}`; L4 assembles the 6-field D-B47 Episode dict as `value`; the
    body's `validate_node(value, type_="Episode")` checks it against the Episode
    NodeType partition. No contract widening.
  - **Buildability:** L4→L3/L2 imports downward; no new top-level package; the new
    L2 KL methods + reserved-key entry are additive. Clean.
  - **No design pick reversed.** PB-0…PB-8 all stand.
- **Round 3 — CLOSED 2026-06-09 (skeptical re-pass; 2 important refinements + 1
  impl-note + scope-realism flag; ZERO prior picks reversed).**
  - **PB-9 — NEW (refines PB-3; important).** Shipped `IntelligenceLayer.
    fork_dream_mm()` is `self.mm.deep_copy()` — it copies the **live** MM, not a
    loaded episode. "Load episode → fork → re-execute" has a missing middle:
    episode→MM reconstruction. **Opt A** = full reconstruction (rebuild frozen
    3-sub-MM from `mm_root_ref`, resolve version-pinned refs — the real S7
    consumer); heavy. **Opt B (PICK)** = re-run from the episode's `task_input_ref`
    only (fresh MM, live lifecycle, ALS firing, `dream_source_episode_iri`); full
    reconstruction + `replay_recorded` regression differentiation defer to WSD
    together. **Consequence: S7 (inline-on-retire read consumer) has NO live v1
    consumer → ships with a unit test only (retire→read→inline); real consumer =
    WSD retrieval / episode reconstruction.** (Stop calling dream the S7 consumer.)
  - **PB-10 — NEW (refines PB-2; important).** The write-capability depends on
    **scope** (local→none; global→`CAN_WRITE_GLOBAL`), and scope is a `context.
    writeable(role, scope, version)` call-arg — unknown at pre-invocation gate
    time. **Opt A (PICK)** = gate **inside the L4-built `writeable` callable at
    call-time** (scope-aware; no `_CapacityBase` field; keeps PB-2's "no contract
    change"); refines ADR-0170 "gate before invocation" → "gate at L4-controlled
    write-time for scope-dependent effects" and supersedes the Phase-47
    `check_write_permitted` pre-gate for these. **Opt B** = declare write-scope on
    `_CapacityBase` + keep pre-gate (registration-contract touch for 2 consumers;
    heavier; rejected).
  - **PB-11 — impl-note (not a fork).** Crash tombstone is writable: `crash_marker`
    is a content field; the partition validator checks classification, not
    presence. Tombstone = `outcome_classification="failed"` + `crash_marker` +
    `mm_root_ref=None`. Confirm at impl the Episode NodeType doesn't enforce
    all-6-present.
  - **Scope-realism flag (not a fork).** Full D'1 stack (S6) + episode-aware paths
    → real LOC plausibly **700–1000+** (> PHASE_MAP 400–700). Deferral valve =
    **S9 monitoring** (no consumer until Phase 49). Consolidation must be
    **idempotent** (crash *during* consolidation must not double-write on the
    startup re-scan — startup scan checks Episode-exists before emitting a
    tombstone).
  - **No prior design pick reversed.** PB-9 refines PB-3; PB-10 refines PB-2.

---

## §6. R1 step-0 grounding probe (PARTIAL — run pre-R0 2026-06-09)

Already validated against shipped code:
1. **Phase-47 closure** — `phase-47-confirmed` absent; `PHASE_47_CONFIRMED.md`
   untracked; `main`-tip `cd8abb0` = the squash. (BLOCKER-1.)
2. **D'1 KL hooks** — `read_at_version`/`retire_version` exist only as a
   `context.py` Protocol stub + `mm_resolver.py` comment; **no `mindsos_knowledge`
   impl.** (BLOCKER-2.)
3. **`consolidate:mm` today** — writes a single `type_="Episode"` node from
   `record["value"]`/`record["episode_id"]` via `kl.writeable(session,…)
   .write_and_validate`; reads `context.get("session")`/`context.get("kl")` (dict
   path). Does **not** assemble the 6-field D-B47 shape, read the chain, or touch
   Memory. (S2/S3 confirmed open.)
4. **`trace:problem`** — Global, gates `session.has(CAN_WRITE_GLOBAL)`, dict
   `context` path. (S4/PB-8.)
5. **Episode/Memory live schema** (`episodic_memories.py`) — `NODE_EPISODE`/
   `NODE_MEMORY` + 6 Episode content fields + `MEMORY_CONTAINS_EPISODE` **regular
   EdgeType** (Memory→Episode, same Schema — *not* IntergraphEdge; Phase-43
   impl-time discovery overrides l5 §9 wording). `task_input_ref` storage cascades
   via XRef target `storage_mode`; no Episode-level storage_mode.
6. **Dream substrate** — `DreamCycleTimer` injected callback (default absent);
   `fork_dream_mm` deep-copy primitive present; `dream.*` bodies emit
   `DreamDirective(execution_policy, entry_point, replan_injection?)`, entry_point
   = `ENTRY_POINT_LATEST_ACTIVE_TASKRUN`.
7. **Chain artifacts** — `chain_artifacts.py` defines 8 composites; `TaskRun`
   (root, `attention_score` field already written at 47); `ChainArtifactWriter`
   emits under the MM writer lock via the resolver.

**To run at R1 (pre-branch):** ADR transcription-parity (0161 stale text; highest
ADR = 0175); `_retired_inline_pending` marker-write presence in Phase-44 ship;
`kl.writeable(` caller census (PB-2 blast radius); `DREAM`-tier presence in
`TierEnum` + `run_lifecycle` signature (does it admit a pre-instantiated MM?);
`DS_MM_COMPOSITE_INSTANCE` shape (PB-1 record widening); PB-Z diff read of
`consolidate.py` across Phase 39/42/43.

---

## §7. Saturation status

**SATURATED 2026-06-09 (re-confirmed after Round 3).** Round 0 (S-surfaces +
forks) + Round 1 (blockers resolved; PB-1/PB-2/PB-5 decided) + Round 2 (grounding
probe) + Round 3 (skeptical re-pass — 2 refinements PB-9/PB-10 + 1 impl-note +
scope flag, **zero prior picks reversed** = the §10.4 signature). Buildability
clean. Budget = 3 rounds (PHASE_43 §10.4); reached.

**Locked picks:**
- **PB-0** = close Phase 47 first (DONE), one `phase-48` branch off
  `phase-47-confirmed`, logical 5-group commit split, targeted tests between
  groups, single cumulative gate at confirm.
- **PB-1** = L4 `consolidation.py` freezes+assembles the 6-field Episode record +
  dispatches `consolidate:mm` (body writes via `context.writeable`).
- **PB-2** = pre-authorized `writeable` capability injected on `CapacityContext`
  by L4 `dispatch.py`; gate splits local-write (no cap) vs global-write
  (`CAN_WRITE_GLOBAL`); ADR-0146 + ADR-0170 both preserved; no `_CapacityBase`
  change.
- **PB-3 / PB-9** = dream driver re-runs from the episode's `task_input_ref` (fresh
  MM, full live lifecycle), `dream_source_episode_iri` tagging, ReplanInjection at
  the replan seam; full episode→MM reconstruction + execution-policy behavioral
  differentiation (`replay_recorded` regression) → WSD.
- **PB-4** = D'1 read consumer in L4 `retention.py`; **S7 ships unit-test-only at
  v1** (no live consumer — PB-9), real consumer = WSD reconstruction/retrieval.
- **PB-10** = write-cap gate fires inside the L4-built `writeable` callable at
  call-time (scope-aware: local→no cap, global→`CAN_WRITE_GLOBAL`).
- **PB-5** = crash-recovery tombstone marker (useful payload) + startup scan;
  content recovery → v1.5.
- **PB-6** = Memory materialize + `MEMORY_CONTAINS_EPISODE` inside `consolidate:mm`.
- **PB-7** = 5 ADRs 0176–0180 + amendments (ADR-0175 §am-2, ADR-0161 §am,
  ADR-0146/0147 §am for the writeable-capability framing).
- **PB-8** = migrate both `consolidate` and `trace` off dict context.
- **S6 lands the full D'1 stack** (both KL methods + marker write + reserved-key +
  read consumer) — Phase 44 shipped none of ADR-0161's forward-contract.

**Next:** commit R0–R2 design-log record + draft 5 ADRs (0176–0180) + the 3
amendments; branch `phase-48` off `phase-47-confirmed`; begin commit-group 1
(S6 KL hooks + S10 helpers). **Awaiting user go-ahead to branch.**
