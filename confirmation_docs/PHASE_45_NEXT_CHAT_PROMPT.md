# PHASE_45_NEXT_CHAT_PROMPT — open Phase 46 (L4 substrate convergence)

You are the **Phase 46 chat: L4 substrate — the convergence point.** All four
Stream B rails are now closed (A 39/43, B 40/41/42, C 44, D 45), which is the
gate Phase 46 was waiting on. This is the largest phase in the post-Phase-38
plan (~1000–1400 LOC + ~6–8 new ADRs at R0) and the first L4 code ever
written. Treat it as a **design-pass first, then ship** — do NOT assume
option-C combined design+ship is right here; saturate the design and propose
the ship shape as a pushback (it may need to split across more than one PR or
even defer sub-surfaces, per consumer discipline).

**YOUR OPERATING SPEC IS THE FILES BELOW. Read them in full before acting; do
not infer scope from this prompt — it only routes you.**

═══ READ FIRST (entry + process) ═══
1. `HANDOFF.md` — §1 (orientation), §3.1.18 (Phase 45 ship — your most recent
   precedent + the dream contract you consume), §3.1.5/§3.1.6 (Chat A + L1/L3
   reframe closures), §3.1.7 (Chat C plan), §4 + §4.1 + §4.2 (L5 settled — the
   MM substrate Phase 46 instantiates), and §9 (process discipline:
   pair-execution Cowork↔Mac↔Linux, 6-step confirm-phase, docker rebuild,
   tag-at-confirm-artifacts-commit, fix the Linux `git config` identity BEFORE
   the confirm commit).
2. `confirmation_docs/POST_PHASE_38_PHASE_MAP.md` — §0 (how a phase chat reads
   it), §1 (cross-cutting: DAG, **high-water-mark version-bump rule** — slot 46
   > high-water 45 → a real 9-surface bump; the 9-surface checklist;
   pre-confirm-phase squash discipline; ADR drafting load PB-BB; PB-AAA
   physical-layout decision is a Phase 46 R0 call), the **Phase 46 detail
   block** (full locked-decisions + features + modules + tests + risks), and §6
   (downstream sequencing).
3. `confirmation_docs/PHASE_45_DESIGN_LOG.md` + `PHASE_44_DESIGN_LOG.md §0` +
   `PHASE_42_DESIGN_LOG.md` — process precedents: the S-surface saturation
   format, R1-step-0 ADR transcription-parity probe, pre-impl pushback rounds
   (saturate ~3), gate-driven follow-up budget, and the **ground-first
   consumer-discipline** rule (ground every surface against its real consumer;
   defer absent-consumer surfaces; ship contracts ahead of consumers only when
   the consumer is a *named later phase*).

═══ DESIGN GROUND TRUTH (Phase 46 implements these; do not re-litigate) ═══
- `confirmation_docs/CHAT_A_DECISIONS.md` — the full L4 architecture: R1 D32
  substrate (IntelligenceLayer lifecycle, priority-tier Executor D32.5b, worker
  pool, MM RWLock, cooperative cancellation, signal-triage worker, ALS
  subsystem registry) + the L4-vs-L3 boundary (L4 = substrate + control flow;
  all decisions are L3 capabilities) + Push 5 defer (`mode="pause"` ships as
  `NotImplementedError`).
- `confirmation_docs/CHAT_B_DECISIONS.md` — D-B10/D-B11/D-B13/D-B14 (the
  three-sub-MM composition + L4 read discipline + MM resolution+instantiation
  layer + D'1 lazy-instantiation). `docs/dev/l4_intelligence_design_notes.md`
  + `docs/dev/l5_mental_model_design_notes.md` §1–§2.
- The Phase 46 PHASE_MAP row's **Locked decisions** are the authoritative
  feature list. Phase 46 R0 also owns: PB-AAA (physical-layout optimization;
  default = Chat B schemas as-written) + PB-HHH is Phase 49, not here.

═══ CARRY-FORWARDS PHASE 46 MUST CONSUME (named in the ship-closure sections) ═══
These were shipped as forward-contracts by earlier rails and Phase 46 is their
first/declared consumer. Read each source section, do NOT restate it:
- **From `HANDOFF.md §3.1.16` (Phase 41):** implement `MonitorSubscriptionRegistry`
  (session-scope `Dict[DataState IRI, List[Monitor IRI]]`) consuming
  `cl.iter_monitors()` + per-task lazy Monitor instantiation +
  orchestrator-thread-only register/unregister.
- **From `HANDOFF.md §3.1.17` (Phase 42 / PB-23 + PB-24):** wire
  `invoke`→`CapacityContext`; migrate the 3 capacity bodies
  (`consolidate`/`trace`/text) from dict-context `context.get("kl")` to
  `context.kl`; resolve the ADR-0146/0159 session-gating boundary
  (`CapacityContext` has no session-object field — design the L4-side gate);
  `materialise` the two `mindsos_instances` intergraph instance subclasses
  (capacity-MM instantiation is their first consumer).
- **From `HANDOFF.md §3.1.18` (Phase 45 — this chat's output):** the L4
  dream-cycle timer interface reads `execution_policy`/`entry_point` off the
  registered `DreamCapacity` nodes and invokes the bodies for `DreamDirective`s;
  the timer then performs MM deep-copy + live re-execution + ALS signal firing
  under each directive (incl. `dream.retry`'s `ReplanInjectionDirective` →
  actual replan per Chat B D-B30). ADR-0162 §Invocation-contract +
  §v2-reservations bound what is in scope. NOTE: `kl.read_at_version` /
  `retire_version` live re-execution under D'1 is mostly **Phase 48** — confirm
  the L4/L5 split at R0.

═══ PREREQ CHECK (run before branching) ═══
- `git tag --list | grep -E "phase-4[0-5]-confirmed"` — 40/41/42/43/44/45 all
  present; `main`-tip carries the Phase 45 ship + doc-closure. Branch `phase-46`
  off `main`-tip.
- **VERSION BUMP REQUIRED:** slot 46 > high-water 45 → full 9-surface manifest
  bump to phase46 (same checklist Phase 45 ran; see `PHASE_45_DESIGN_LOG.md §R1`
  for the exact 9 surfaces + the export-slate sentinel-flip files).
- **PB-Z reading-list:** Phase 46 R0 reads diffs of prior phases touching files
  in its `Modules touched` set — esp. `mindsos_core/schema.py` (Phase 43, per
  PHASE_MAP §1 collision note) + the Phase 42 `context.py`/`capacity_layer.py`
  (CapacityContext) + Phase 41 `capacity_layer.py` (iter_monitors) + Phase 45
  `builtins/dream.py` (dream directives).
- **Robot Demo:** the Robot Demo workstream now lives in
  `confirmation_docs/ROBOT_DEMO_STATUS.md` (HANDOFF §0 carries only a one-line
  pointer), so HANDOFF.md no longer carries a perpetual uncommitted block. Still
  **never `git add -A`; stage explicit Phase-46 paths** — the working tree may
  carry in-flight Robot Demo edits + untracked `ROBOT_DEMO_*`/`demo_ui/`/`sim/`/
  `web/`/`prototype_zero/` you must leave alone.

═══ INHERITED LESSONS (apply, don't re-derive) ═══
- Ground every surface against its real consumer before writing; defer
  absent-consumer surfaces (Phases 40–45 all did this).
- ADR transcription-parity probe is R1 step 0.
- Ceremony: confirm-phase MUST run on post-squash `main` (not the branch tip —
  Phases 40/42/45 all hit the branch-tip anomaly and had to cherry-pick onto
  main); tag `phase-46-confirmed` at the **confirm-artifacts commit**, not the
  squash; fix the Linux `git config` identity before the confirm commit.
- Budget 2–3 pre-impl pushback rounds + a buildability scan before branching;
  expect gate-driven follow-ups proportional to scope (Phase 46 is large —
  budget several).

═══ OPERATING MODE (the user runs every ship chat this way) ═══
"Before proceeding with any implementation, reanalyze the plan and list your
pushbacks with options, then show me your choice. Any decision can change as we
go." Honor it — skeptical review each round, terse, options + your pick, pause
for authorization before impl. Use `AskUserQuestion` for genuine forks. Drive
the git/ship ceremony as one tagged (Mac/Linux) command-group at a time with
expected output.

**FIRST ACTION:** run the prereq check; ack required-reading completion; open
`confirmation_docs/PHASE_46_DESIGN_LOG.md` R0 (mirror the Phase 42/44/45
S-surface format) — enumerate the L4-substrate surfaces from the PHASE_MAP
Phase 46 row + the three carry-forward consumers above; surface the genuine
design forks (Executor priority model, MM RWLock granularity, cancellation
framework shape, ALS subsystem registry v0, the ADR-0146/0159 session-gating
resolution, the dream-timer L4/L5 split) as pushbacks with options; then run
the pre-impl pushback rounds before branching `phase-46`.
