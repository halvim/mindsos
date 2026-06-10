You are the Phase 47 chat: **L4 orchestrator — six-phase task lifecycle +
`planning.*` v0 + skeletons.** Phase 46 shipped the L4 substrate
(`mindsos_intelligence`); Phase 47 makes it *run* — the orchestrator that
drives a task through the lifecycle, consuming the substrate primitives and the
surfaces Phase 46 deferred to you. This is a large code phase; treat it as a
design-pass first, then ship (do NOT assume the ship shape — propose it as a
pushback, as Phase 46 did when its two-PR plan collapsed to one).

YOUR OPERATING SPEC IS THE FILES BELOW. Read them in full before acting; this
prompt only routes you — it deliberately does not restate what the files say.

READ FIRST (entry + process)
1. `HANDOFF.md` — §1 (orientation), **§3.1.19 (Phase 46 ship — the substrate
   you consume + the exact carry-forward list to Phase 47/48)**, §3.1.5 (Chat A
   closure), §3.1.7 (Chat C plan), §4 + §4.1 + §4.2 (L5 settled — the 6-level
   chain + Plan-tree + planning.* family you instantiate), §9 (process
   discipline — note the **`python3` host-env invariant**, pair-execution,
   squash-before-confirm, tag-at-confirm-artifacts-commit, docker rebuild).
2. `confirmation_docs/POST_PHASE_38_PHASE_MAP.md` — §0, §1 (DAG + high-water
   version-bump rule + 9-surface checklist + PB-BB ADR load), the **Phase 47
   detail block**, and §6.
3. `confirmation_docs/PHASE_46_DESIGN_LOG.md §9` — the authoritative
   carry-forward list + the grounding-driven decisions Phase 47 inherits.
4. `confirmation_docs/PHASE_46_DESIGN_LOG.md §0` + `PHASE_45/44/42_DESIGN_LOG.md
   §0` — process precedents: S-surface saturation, R1-step-0 ADR
   transcription-parity probe, pre-impl pushback rounds (~3), gate-driven
   follow-up budget, ground-first consumer-discipline rule.

DESIGN GROUND TRUTH (implement; do not re-litigate)
- `confirmation_docs/CHAT_A_DECISIONS.md` — R2 Pushes (esp. Push 2 action
  contracts via predicate-capacity IRIs), R3 Phase-1 5-step refactor + hint
  extraction, R4 D12 six-phase lifecycle (Phase 1→6), the L4-vs-L3 strict line,
  MSUR + SCMS as L3 orchestration capacities.
- `confirmation_docs/CHAT_B_DECISIONS.md` — D-B22 (6-level chain artifact
  HintSet→MappingResult→Plan→Pipeline→PipelineRun→TaskRun) + D-B23 (Plan =
  recursive Milestone tree; `planning.*` 4-capacity family) + the replan model
  (D-B30, invalidate-at-and-below).
- `docs/dev/l4_intelligence_design_notes.md` + `l5_mental_model_design_notes.md`
  (the chain + Plan-tree schemas).

CARRY-FORWARDS PHASE 47 MUST CONSUME (read each source; do not restate)
- From `PHASE_46_DESIGN_LOG.md §9` + HANDOFF §3.1.19: **S12 / PB-23** —
  `invoke`→`CapacityContext` (flip the shipped `runtime.invoke` /
  `capacity_layer.invoke` signature) + migrate the `consolidate`/`trace` bodies
  to `context.kl` + implement the write-body capability gate in L4 dispatch per
  **ADR-0170** (contract already drafted; enforcement is yours). This is a
  corpus-wide signature change — budget the gate-driven follow-ups.
- **L3 `decision.signal_to_tier`** capacity — replaces the Phase-46
  `signal_triage.passthrough_classifier` stub (returns a `TierVerdict`; tier
  type is `mindsos_capacity.tiers.TierEnum`).
- **L3 `scoring.attention_score`** capacity (learnable, `learned-parameters`
  cold-start constants) + the L4 `update_priority` wrapper (invoke scorer →
  `executor.write_priority`) + the ALS S9 mutation-frequency signal.
- **Dream driver** — the callback the Phase-46 `DreamCycleTimer` ticks: read
  `DreamCapacity.execution_policy`/`entry_point`, invoke the dream bodies for
  `DreamDirective`s, enqueue the DREAM-tier task through the new phase-loop
  (ADR-0162 §Invocation-contract). The MM deep-copy primitive
  (`IntelligenceLayer.fork_dream_mm`) already exists; **live re-execution + ALS
  firing + replan-injection consumption stay Phase 48** — confirm the 47/48
  split at R0.

PREREQ CHECK (run before branching)
- `git tag --list | grep -E "phase-4[0-6]-confirmed"` — 40-46 all present.
  Branch `phase-47` off `main`-tip.
- **VERSION BUMP REQUIRED:** slot 47 > high-water 46 → 9-surface bump to
  phase47 (now **8** package `__version__` strings — `mindsos_intelligence`
  joined the manifest `[mindsos] packages` roster at Phase 46). See
  `PHASE_46_DESIGN_LOG.md §9` / HANDOFF §3.1.19 for the exact surface list +
  export-slate sentinel files.
- **PB-Z reading-list:** diff the Phase-46 modules this phase touches —
  `mindsos_intelligence/*` (esp. `executor.py`, `intelligence_layer.py`,
  `signal_triage.py`, `mm_resolver.py`), `mindsos_capacity/runtime.py` +
  `capacity_layer.py` (the `invoke` signature you flip), `context.py`
  (`CapacityContext`), `builtins/consolidate.py` + `trace.py` (body migration),
  `builtins/dream.py` (dream contract).
- No new top-level package expected (Phase 47 lives in `mindsos_intelligence`
  + new L3 `planning.*`/`decision.*`/`scoring.*` capacities) → the
  new-top-level-package checklist is N/A unless that changes; **host
  `pip install -e .` refresh is only needed if a new top-level package is
  added** (Phase 46 needed it; a no-new-package phase does not).

INHERITED LESSONS (apply, don't re-derive)
- Probe-first: R1 step 0 = ADR transcription-parity probe + read the real
  shipped signatures before locking picks (Phase 46 caught 3 ADR corrections +
  the S12 scope reversal this way).
- Ground every surface against its real consumer; defer absent-consumer
  surfaces (Phase 40/42/45/46 precedent).
- **`python3`, not `python`, for host smokes** (HANDOFF §9).
- Squash-merge to `main` BEFORE running `confirm-phase` (Phase 46 avoided the
  Phase 40/42/45 branch-tip cherry-pick anomaly this way); tag
  `phase-47-confirmed` at the confirm-artifacts commit, not the squash; fix the
  Linux git identity before the confirm commit.
- Budget 2-3 pre-impl pushback rounds + a buildability scan before branching.

OPERATING MODE
"Before proceeding with any implementation, reanalyze the plan and list your
pushbacks with options, then show me your choice. Any decision can change as we
go." Skeptical review each round, terse, options + your pick, pause for
authorization before impl. Drive the git/ship ceremony one tagged (Mac/Linux)
command-group at a time with expected output.

FIRST ACTION: run the prereq check; ack required-reading; open
`confirmation_docs/PHASE_47_DESIGN_LOG.md` R0 (mirror the Phase 46 S-surface
format) — enumerate the orchestrator surfaces from the PHASE_MAP Phase 47 row +
the carry-forward consumers above; surface the genuine design forks (six-phase
lifecycle shape, `planning.*` v0 catalog, the `invoke`→CapacityContext
corpus-migration strategy, the write-gate enforcement design, the dream-driver
47/48 split) as pushbacks with options; then run the pre-impl pushback rounds
before branching `phase-47`.
