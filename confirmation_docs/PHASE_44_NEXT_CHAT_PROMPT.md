# Phase 44 — Next Chat Prompt (Rail C: L0 substrate)

> **You are the Phase 44 design + ship chat (Rail C — L0 substrate).** Phase 43 (Rail A slot 2) shipped 2026-06-03 (`PHASE_43_DESIGN_LOG.md §9` + `HANDOFF.md §3.1.13`). Phase 44 inherits 3 Phase-43-deferred items + L0_SUBSTRATE_CHAT closure dependencies.

═══════════════════════════════════════════════════════════════════
SCOPE
═══════════════════════════════════════════════════════════════════

Phase 44 is a **combined design + ship chat (option C, ratified 2026-06-04).** It absorbs `L0_SUBSTRATE_CHAT` closure into R0 rather than waiting on a separate chat — PHASE_MAP lines 528 + 981 grant R0 the ADR-ratification authority. **Prereq #6 below is superseded:** R0 step 1 *is* the L0 substrate design saturation, not a gate on an external chat.

This SCOPE is reconciled against `POST_PHASE_38_PHASE_MAP.md` Phase 44 detail block (lines 492-561), which is the authoritative fuller scope; the prompt's prior 3-item list was a subset that dropped the persisters, the orchestrator refactor, the Falkor-backed bootstrap, and the `ProblemTraceSink`. Governance rulings taken 2026-06-04: **CR-2 = Falkor-only v1** (reversed from "ship both" on PR1.2 investigation — the `mindsos_cli` state-file serializer is disk-coupled + SQLite has no v1 consumer; `SQLiteLocalPersister` + `MetagraphDump` + serializer promotion deferred — see design log §6); **CR-3 = do the `MindsOSServer` class refactor now** (ADR-0011 note 4 satisfied, not deferred).

**A. Design (R0 — absorbs L0_SUBSTRATE_CHAT):**

- **ADR-0160** (NEW) — `FalkorDBLocalPersister` + `SQLiteLocalPersister` impls + **backend-neutral `MetagraphDump` serialization contract** (deferred to this phase by ADR-0011 note 1; must round-trip through both backends).
- **ADR-0161** (NEW) — `kl.read_at_version` + `kl.retire_version` KL version surface.
- **ADR-0011 §amendment-N** — Protocol-shape revision (`Metagraph` → `MetagraphDump` at load/save) + `MindsOSServer` class lifecycle (on-login hydrate / on-logout flush / promotion-flush / delete hooks).
- **ADR-0004/0121 one-line clarification** — `SQLiteLocalPersister` stores an opaque serialized `MetagraphDump` blob (not graph-relational); does not violate the FalkorDB-for-graphs substrate split.
- **CR-4 retire-marker forward-contract** — freeze the lazy-inline marker's storage location + format now so the Phase 48 episode-read consumer can consult it (ADR-0153 §am-2 or ADR-0161, as saturation surfaces).

**B. Ship (PR1 / PR2):**

1. **`FalkorDBLocalPersister`** — native round-trip via `MetagraphRepository.persist` + `MetagraphLoader.load` (no serialization); MERGE-on-id idempotency (ADR-0122); best-effort `delete -> bool`; per-user mutex on write.
2. ~~`SQLiteLocalPersister`~~ — **deferred** (CR-2 Falkor-only v1; ships with the first local-first/portable-export consumer).
3. ~~`MetagraphDump` + serializer promotion~~ — **deferred** with item 2.
4. **`MindsOSServer` class refactor** — free-functions → class; migrate `_installed_locals` / `_install_lock` / `_mutex_registry`; preserve `reset_state_for_tests()`; rewire the `read_other_local` ctx-mgr mutex (ADR-0006). Adds `mindsos_server/orchestrator.py` to Modules-touched.
5. **Falkor-backed L3 bootstrap + state-file serialization** — `bootstrap_kl_from_falkordb` into `_construct_invoke_layer`; reachability probe + in-memory fallback (PHASE_38 §4 #2).
6. **Kahn topological-sort scheduler (L2-37 consumer).** Consumes `_APPLIES_AFTER_BY_ROLE`; respects soft edge `episodic_memories ← {task-patterns}`; cycles raise; missing → `frozenset()`.
7. **`EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` audit constant + `CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY` capability (L2-39).** Audit constant in `mindsos_server/audit.py`; capability in `mindsos_server/capabilities.py` (NOT `auth.py`) — new constant + `ADMIN_CAPS` (9 → 10) + `ALL_CAPABILITIES` tuple; Phase 18 `test_capabilities_parity` sentinel flips. Default-deny + admin opt-in. Distinct from existing `CAN_READ_OTHER_LOCALS`.
8. **KL retention surface (L2-41).** `kl.read_at_version(metagraph, role, version)` + `kl.retire_version(metagraph, role, version)`. retire fires the lazy-inline marker. **Consumer (episode-read consultation) is Phase 48** — Phase 44 ships hook + marker-write + marker-state unit test only (corrects PHASE_MAP "Features in scope" + `test_kl_retire_version.py` framing, which over-claim consumer-side consultation here).
9. **Per-user Local-scoped `ProblemTraceSink` dict** (PHASE_38 §4 #6).

**C. Pending minor absorption decisions (confirm at R0; changeable):**

- `validate_local_to_global_ref` (L2-10) — **IN** (Phase 44 is the first per-flow consumer, via the cross-user read path).
- `--session-token` CLI flag (L0-3) — **OUT** (defer to Stream A; keeps the CLI surface stable).

**Follow-up budget:** 4-5 (revised up from 2-4 — class refactor + dual-backend dump are Phase-43-class scope-rewrite surface).

═══════════════════════════════════════════════════════════════════
PREREQ CHECK (run BEFORE anything else)
═══════════════════════════════════════════════════════════════════

1. `git tag --list | grep phase-43-confirmed` — must exist.
2. `git status` — clean working tree.
3. `cat mindsos_cli/manifest.toml | grep "^phase"` — should read `phase = "43"`.
4. `git log --oneline -3` — top SHA is the Phase 43 squash-merge commit (descendant of `phase-43-confirmed`).
5. Confirm `confirmation_docs/PHASE_43_CONFIRMED.md` exists.
6. **L0_SUBSTRATE_CHAT absorbed into R0 (option C, 2026-06-04).** Phase 44 does NOT wait on a separate L0_SUBSTRATE_CHAT — its closure work (persister Cypher contracts + KL surface + audit roster) is **R0 step 1** here, per the line 528 / 981 R0-ratification grant in `POST_PHASE_38_PHASE_MAP.md`. No external-chat gate; do not pause on it. (Supersedes the prior "blocked if not closed" framing.)

If any check fails, surface immediately. Do not branch.

═══════════════════════════════════════════════════════════════════
REQUIRED READING (in order; do NOT skip)
═══════════════════════════════════════════════════════════════════

1. **`HANDOFF.md` §1, §2.2, §3.1.13 (Phase 43 ship closure), §9 (process discipline + pair-execution + 6-step confirm-phase).**
2. **`confirmation_docs/PHASE_43_DESIGN_LOG.md §9` IN FULL.** Captures all Phase 43 impl-time amendments + carry-forwards. §9.6 names Phase 44 inheritance items explicitly.
3. **`confirmation_docs/PHASE_43_CONFIRMED.md` + `confirmation_docs/notes/notes-phase-43.md`.** Tester-side ship metadata.
4. **`docs/_workbench/L2_FUTURE_WORK.md §11`** — L2-37(consumer), L2-39, L2-41 routing notes.
5. **`mindsos_knowledge/bootstrap.py`** — the `_APPLIES_AFTER_BY_ROLE` field declarations Phase 44 consumes.
6. **`mindsos_knowledge/knowledge_layer.py`** — `discipline_for` cache + lifecycle hooks where retention surface lands.
7. ADRs on disk Phase 44 may touch:
   - `docs/decisions/adr/0153-l2-mutation-discipline.md` — possible §amendment-2 if retention semantics surface a new field.
   - `docs/decisions/adr/0150-l2-knowledge-lifecycle.md` — possible §amendment-6 if version-retirement surface lands here.
   - L0_SUBSTRATE_CHAT closure docs (when they exist).

═══════════════════════════════════════════════════════════════════
PAIR-EXECUTION DISCIPLINE (Cowork ↔ Mac ↔ Linux)
═══════════════════════════════════════════════════════════════════

Per Phase 43 R11 + HANDOFF §9: Cowork sandbox cannot run git commands. Cowork prepares file content via Edit/Write tools; the user runs git on Mac; Linux runs cumulative gates via docker. **One command-group at a time** with expected output; user pastes back if diverges, says "proceed" if matches. **Group simple obvious sequences in one box**; tag Mac vs Linux explicitly. **Docker test image rebuild required after each Mac push** (R10) — `docker compose build mindsos-test` before `docker compose run --rm mindsos-test pytest tests/`.

═══════════════════════════════════════════════════════════════════
6-STEP CONFIRM-PHASE WORKFLOW (Phase 43 R12 carry-forward)
═══════════════════════════════════════════════════════════════════

After PR2 cumulative gate green + squash-merge to main:

1. Cowork instructs `mindsos confirm-phase --init-notes 44` (Mac) to create `confirmation_docs/notes/notes-phase-44.md` from template.
2. Cowork provides the layer title in a copy-block (e.g., "L0 substrate ship — Kahn scheduler + audit constant + retention surface").
3. Cowork provides the complete `tester_notes` body in a copy-block (drawn from cumulative gate output + design log §9 content).
4. Tester edits the notes file on Linux.
5. Tester runs `mindsos confirm-phase --phase 44 --notes-file notes-phase-44.md` on Linux from post-squash main.
6. Tester commits `PHASE_44_CONFIRMED.md` + notes-phase-44.md + pushes; Mac tags `phase-44-confirmed` at squash-merge commit + pushes tag.

═══════════════════════════════════════════════════════════════════
DESIGN PASS PROCESS DISCIPLINE
═══════════════════════════════════════════════════════════════════

Per Phase 43 design log §10 carry-forwards:

- **R1 step 0: ADR transcription parity probe.** Grep each design-pass draft's transcription tables against the source ADR-on-disk; surface drift; correct draft, not ADR.
- **R1 step 1: PHASE_MAP §4 row parity scan.** Compare with current state; flag stale items.
- **R1 step 2: Buildability scan over locked commit boundaries.** Before ratifying PR1/PR2 commit ordering, scan for exactly-N sentinels + fixture-keyed tests that would fail at mid-PR intermediate states. 10-minute grep-pass catches violations that would otherwise surface as cumulative-gate cascade errors.
- **Saturation: three consecutive reversal-free rounds.** Reversals reset the clock per Chat C discipline.
- **Closure discipline: commit closure artifacts BEFORE ending the chat.** Phase 43 P1 surfaced the design-chat-close gap.
- **Pre-impl pushback saturation (3 rounds typical) per §10.4.** Ship-chat user may request "reanalyze the plan and list your pushbacks with options.... show me your choice" multiple times. Budget 2-3 rounds: workflow-level → design-log-level → probe-level. Declare saturation explicitly when round-N surfaces only minor/track items.
- **Cascade-error root-cause diagnosis per §10.6.** When a gate surfaces a large failure count, look at the failure message text BEFORE the test names. Identical messages across many tests almost always trace to a single root cause — often a module-level invariant, sentinel, or fixture pattern. Diagnose root cause first; fix often single-line.
- **Gate-driven follow-up budget per §10.5.** Phase 39 needed 2 follow-up commits; Phase 43 needed 6. Budget follow-ups proportional to scope-rewrite surface. Phase 44's L0 substrate scope (Kahn scheduler + audit constant + retention surface) is narrower than Phase 43; expect 2-4 follow-ups.

═══════════════════════════════════════════════════════════════════
OUT OF SCOPE
═══════════════════════════════════════════════════════════════════

- Re-litigation of Phase 43 design picks (L2 schema-v2 surface, discipline framework, storage tiers, role-graph closed set).
- Rail B (Phases 40/41/42), Rail D (Phase 45), L4/L5/Integration C (Phases 46-49).
- WSD / FOL / DWF / code-skill installation chat scope.

═══════════════════════════════════════════════════════════════════
FIRST ACTION
═══════════════════════════════════════════════════════════════════

Run the prereq check above. Confirm `phase-43-confirmed` tag + clean working tree. **L0_SUBSTRATE_CHAT is absorbed into R0 (option C)** — do not pause on it; R0 step 1 is the L0 substrate design saturation (see `PHASE_44_DESIGN_LOG.md §1`). Ack required reading completion + begin R0 saturation.
