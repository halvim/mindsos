# Phase 44 — Next Chat Prompt (Rail C: L0 substrate)

> **You are the Phase 44 design + ship chat (Rail C — L0 substrate).** Phase 43 (Rail A slot 2) shipped 2026-06-03 (`PHASE_43_DESIGN_LOG.md §9` + `HANDOFF.md §3.1.13`). Phase 44 inherits 3 Phase-43-deferred items + L0_SUBSTRATE_CHAT closure dependencies.

═══════════════════════════════════════════════════════════════════
SCOPE
═══════════════════════════════════════════════════════════════════

Phase 44 ships the L0 substrate consumer + scheduler that Phase 43 declared but did not consume:

1. **Kahn topological-sort scheduler (L2-37 consumer split).** Phase 43 ships `_APPLIES_AFTER_BY_ROLE` declarations + `applies_after: frozenset[str] = frozenset()` kwarg on `ensure_*_role_graph` per NPB11-1. Phase 44 implements the scheduler that consumes the declarations: bootstrap iteration order respects the soft edge (`episodic_memories ← {task-patterns}`); cycles raise; missing declarations default to `frozenset()` (no constraint).
2. **`EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` audit constant (L2-39).** Per L2_CHAT_DECISIONS D-L2-23. Distinct from generic `READ_OTHER_LOCAL` capability. Audit-log surface in `mindsos_server/audit.py`; capability registration in the per-flow capability registry.
3. **KL retention surface (L2-41).** `kl.read_at_version(metagraph, role, version)` + `kl.retire_version(metagraph, role, version)` per D-L2-18. Lazy inline-on-retire mechanism per ADR-0153 §4 reference-stability framing.

═══════════════════════════════════════════════════════════════════
PREREQ CHECK (run BEFORE anything else)
═══════════════════════════════════════════════════════════════════

1. `git tag --list | grep phase-43-confirmed` — must exist.
2. `git status` — clean working tree.
3. `cat mindsos_cli/manifest.toml | grep "^phase"` — should read `phase = "43"`.
4. `git log --oneline -3` — top SHA is the Phase 43 squash-merge commit (descendant of `phase-43-confirmed`).
5. Confirm `confirmation_docs/PHASE_43_CONFIRMED.md` exists.
6. **L0_SUBSTRATE_CHAT closure required.** Phase 44 R0 depends on L0_SUBSTRATE_CHAT design closure for the runtime envelope (per `POST_PHASE_38_PHASE_MAP.md §6` sequencing). If L0_SUBSTRATE_CHAT has not closed, Phase 44 R0 is blocked.

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

1. Cowork gives Mac command to generate `confirmation_docs/notes/notes-phase-44.md` (from template if exists; `touch` + Edit if not).
2. Cowork provides the layer title in a copy-block (e.g., "L0 substrate ship — Kahn scheduler + audit constant + retention surface").
3. Cowork provides the complete `tester_notes` body in a copy-block (drawn from cumulative gate output + design log §9 content).
4. Tester edits the notes file on Linux.
5. Tester runs `mindsos confirm-phase --phase 44 --notes-file confirmation_docs/notes/notes-phase-44.md` on Linux from post-squash main.
6. Tester commits `PHASE_44_CONFIRMED.md` + notes file + pushes; Mac tags `phase-44-confirmed` at squash-merge commit + pushes tag.

═══════════════════════════════════════════════════════════════════
DESIGN PASS PROCESS DISCIPLINE
═══════════════════════════════════════════════════════════════════

Per Phase 43 design log §10 carry-forwards:

- **R1 step 0: ADR transcription parity probe.** Grep each design-pass draft's transcription tables against the source ADR-on-disk; surface drift; correct draft, not ADR.
- **R1 step 1: PHASE_MAP §4 row parity scan.** Compare with current state; flag stale items.
- **R1 step 2: Buildability scan over locked commit boundaries.** Before ratifying PR1/PR2 commit ordering, scan for tests that would fail at mid-PR intermediate states.
- **Saturation: three consecutive reversal-free rounds.** Reversals reset the clock per Chat C discipline.
- **Closure discipline: commit closure artifacts BEFORE ending the chat.** Phase 43 P1 surfaced the design-chat-close gap.

═══════════════════════════════════════════════════════════════════
OUT OF SCOPE
═══════════════════════════════════════════════════════════════════

- Re-litigation of Phase 43 design picks (L2 schema-v2 surface, discipline framework, storage tiers, role-graph closed set).
- Rail B (Phases 40/41/42), Rail D (Phase 45), L4/L5/Integration C (Phases 46-49).
- WSD / FOL / DWF / code-skill installation chat scope.

═══════════════════════════════════════════════════════════════════
FIRST ACTION
═══════════════════════════════════════════════════════════════════

Run the prereq check above. Confirm `phase-43-confirmed` tag + L0_SUBSTRATE_CHAT closure state. If L0_SUBSTRATE_CHAT has not closed: surface the dependency to the user and pause. Otherwise: ack required reading completion + begin R0.
