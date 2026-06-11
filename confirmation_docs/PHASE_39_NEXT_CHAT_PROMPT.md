## PHASE 39 — NEXT CHAT PROMPT

> Drafted 2026-06-02 by Chat C plan-authoring closure. Hand to the chat that opens Phase 39 — the first code-ship of the post-Phase-38 plan.

You are running the Phase 39 chat: **L2 `memories` → `episodic_memories` atomic rename + L2-35 alignment reconciliation + migration script + 2 ADR amendments (ADR-0044 §am-3 + ADR-0150 §am-4 rename row).**

Rail A, slot 1 of 11 in the post-Phase-38 plan.

---

## Before you do anything — required reading, in this order

1. **`HANDOFF.md`** at the root. Canonical entry point. Read §0, §1, §2.2 (L2 shipped surfaces), §3.1.7 (Chat C closure block with rail layout), §6.4 (current operating mode), §10 reading-map table — find the "Phase 39 chat" row; that row names this file's required reading.

2. **`confirmation_docs/POST_PHASE_38_PHASE_MAP.md`** — §0 (how a phase chat reads this file; especially the PB-Z reading-list clause), §1 (settled cross-cutting decisions for Phases 39-49 including the DAG execution rule, `release.yml` retention amendment as pre-Phase-39 prereq, IL-3 ADR-0150 amendment split, sentinel chain disposition, ship-shape disposition), §2 (per-phase row schema verbatim from PHASE_MAP §2), **§4 Phase 39 row in full** (this is your specification — features, modules touched, tests, pass criterion, breaking changes, risks).

3. **`confirmation_docs/L2_CHAT_DECISIONS.md`** — D-L2-1 (alignment canonical form `alignment:<a>:<b>`), D-L2-16 (atomic-hard-rename rationale; no alias, no deprecation window), D-L2-17 (`episodic_memories` schema v1: Episode + Memory entry types + `memory_contains_episode` IntergraphEdge — Phase 39 ships schema-only; full storage discipline `append_only_with_lazy_inline` runtime invariant lands Phase 43), D-L2-25 (ADR-0044 §am-3 details), D-L2-26 + its Chat C IL-3 refinement note (split into §am-4 rename row at Phase 39; §am-5 4-new-role-graphs at Phase 43).

4. **`_workbench/STREAM_A_BACKLOG.md`** — verify item **A1 (`release.yml` retention amendment per PB-R) has landed** before this branch opens off main. Phase 39 has no other Stream A blocker; A6 (`validate_local_to_global_ref` consumer) and A2 (`--session-token` CLI flag) are not Phase 39 prereqs.

5. **`confirmation_docs/PHASE_MAP.md` §1** — inherited cross-cutting decisions from the L0-L3 plan (per-phase workflow, two-machine Mac+Linux, doctor self-test checks, branching off main, design-only-phase exception language). Phase 39 ships under these unchanged. Skim §3 + §2.2 row for L2 / Phase 13 schemas / `consolidate:mm` Phase 33 capacity body — these are the surfaces you'll edit.

6. **Existing ADRs on disk** — `docs/decisions/adr/0044-memories-move-to-local-per-user.md` (amend chain: §am-1 + §am-2 exist; you draft §am-3) and `docs/decisions/adr/0150-l2-knowledge-lifecycle.md` (amend chain: §am-1 through §am-3 exist; you draft §am-4 covering rename row only per IL-3 split). ADR-0154 already shipped (alignment naming canonical); your L2-35 reconciliation work is the shipped-code-side fix that ADR-0154 specified.

7. **Phase 33 + Phase 38 references** — `confirmation_docs/PHASE_33_CONFIRMED.md` (the `consolidate:mm` capacity body you'll re-target) and `confirmation_docs/PHASE_38_DESIGN_LOG.md` §5 (process notes inherited, especially probe-first discipline + the R6 ship-shape lesson that Chat C IL-8 preserved here as origin record). Phase 38 documents the design-only-vs-code-shipping discipline; Phase 39 is unambiguously code-shipping.

8. **Phase 35 sentinel chain anchor precedent** — `tests/phase_35/test_adr_amendment_sentinels.py`. Phase 39 starts a new chain rooted at Phase 39 (Chat C PB-6 picked new chain at Phase 39; IL-2 picked Phase 35 ancestor-matching-content filename); your sentinel file is `tests/phase_39/test_adr_amendment_sentinels.py` following that pattern.

Memory entries available if you have memory access (optional speedups; canonical text is in files above): `[[project-mindsos-l2-chat-closure]]`, `[[project-mindsos-chat-c-closure]]`, `[[reference-mindsos-layer-handoffs]]`, `[[feedback-confirm-phase-machine-locality]]`, `[[user-two-machine-setup]]`.

---

## Project rules (re-inherit)

User's standing project instructions apply: skeptical reviewer mode, terse alternatives + pick format, push back when something is weak, no filler. Saturation discipline: R5 produces impl-locks only, zero reversals = ready-to-ship.

The L2 picks you're implementing are already settled by L2 chat closure 2026-06-01 + Chat C IL-3 refinement 2026-06-02. **Do not re-litigate L2 architecture.** Re-litigate only Phase 39 impl-shape decisions (CLI verb names, file paths, fixture scoping, migration-script form, test layout, sentinel-anchor scope).

---

## R0 expectations (your first response shape)

1. **Confirm required-reading consumed** — terse paths list.

2. **Run probes against shipped reality** — these were load-bearing in Phase 38 R3-PB-A:
   - `grep -rn "ROLE_MEMORIES\|memory_iri\|memories-\|schemas/memories" mindsos_*/ tests/` — current callsites count + locations. Drives test-fixture rename scope estimate.
   - `git log --oneline -- mindsos_knowledge/schemas/memories.py mindsos_knowledge/identifiers.py mindsos_capacity/builtins/consolidate.py` — last-touched commits; surfaces any post-Chat-C drift.
   - `grep -n "alignment_role\|alignment:" mindsos_knowledge/identifiers.py` — verify the `alignment:<a><->b>` arrow form is still shipped at line 303 (the L2-35 reconciliation target).
   - `mkdocs build --strict 2>&1 | grep -i warning | wc -l` — baseline warning count (Chat C IL-8 audit recorded ~16 baseline; verify Phase 40 X1 hasn't already touched).
   - `ls confirmation_docs/PHASE_38_CONFIRMED.md` — confirms Phase 38 still tagged on main.
   - `git log --oneline release.yml | head -3` — verify Stream A item A1 (PB-R retention amendment) has landed; if not, **stop and route to Stream A first**.
   - `grep -n "READ_OTHER_LOCAL_EPISODIC_MEMORY\|EVT_READ_OTHER_LOCAL_MEMORY" mindsos_server/audit.py` — verify whether the pre-rename audit constant exists (drives D-L2-23 + L2-39 partial absorption decision: rename now vs at Phase 44).
   - `cat manifest.toml | grep "^phase"` — verify `[mindsos] phase = "38"` baseline before bumping to 39.

3. **Draft Phase 39 R0 pushback slate.** Likely surfaces:
   - **PB-39-1.** Schema-shape for `Episode` + `Memory` entry types at Phase 39 vs Phase 43 boundary. Per POST_PHASE_38_PHASE_MAP §4 Phase 39 row: schema-only at this phase; full `append_only_with_lazy_inline` discipline + `storage_mode` + `CONTENT_FIELDS`/`METADATA_FIELDS` frozensets land Phase 43. Confirm or re-litigate that boundary.
   - **PB-39-2.** `tools/rename_memories_to_episodic_memories.py` migration script form per PB-X. v1 production state is empty; script is dev-environment safety net. Pick: trivial Python script vs admin CLI verb vs no-op stub. Default per POST_PHASE_38 §4 Phase 39 = trivial script + idempotence test.
   - **PB-39-3.** Reading-list discipline (PB-Z) — Phase 40 X1 is the next ship on Rail B and edits `identifiers.py`. Coordinate with Phase 40 chat author at branch-creation time so Phase 40 R0 reads the Phase 39 PR diff. Standard branch-rebase discipline applies.
   - **PB-39-4.** Triple-touch on `consolidate.py` (Phase 39 + Phase 42 X3 `context["kl"]` migration + Phase 48 L5 D-B47 schema target). Flag Phase 42 + Phase 48 R0 reading-list to include this Phase 39's `consolidate.py` diff. Discipline-level.
   - **PB-39-5.** Whether to absorb L2-39 (`EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` audit constant rename) inline at Phase 39 vs defer to Phase 44 (per current POST_PHASE_38 routing). Probe at R0 — if pre-rename constant exists in `mindsos_server/audit.py`, rename it here (the rename is mechanical); otherwise defer.
   - **PB-39-6.** ADR-0150 §am-4 wording scope per IL-3 — strictly rename row only, no role-graph expansion language (§am-5 ships those at Phase 43). Confirm wording boundary.
   - **PB-39-7.** Whether `usage/knowledge/memories.md` (PHASE_38 §4 #16 drift) gets renamed to `episodic-memories.md` (preserves URL chain via mkdocs redirect) or deleted. POST_PHASE_38 row defers to phase-chat pick.

4. **Stop. Wait for re-litigation cue** before drafting R1 impl-locks.

Saturation expectation per Phase 24 / Phase 25 precedent: 2-4 R-rounds + impl + tester loop. Reading-list adds the PB-Z prior-phase-diffs clause but Phase 39 has no prior post-Phase-38 phase to consult — only the Phase 13 ship that established the role + Phase 33 ship that wrote the `consolidate:mm` body.

---

## Out of scope for this chat

- Anything in any other phase's row (Phase 40-49 are separate chats).
- Re-litigation of L2 architecture (closed at L2 chat 2026-06-01; closed at Chat C plan-authoring 2026-06-02).
- Re-litigation of rename atomicity, alias/deprecation policy, or `Episode` vs `Memory` entry-type split — all locked at L2_CHAT_DECISIONS D-L2-16 + D-L2-17.
- Stream A item A1 (`release.yml` retention amendment) — that's a maintenance PR; if it hasn't landed, route there first; not Phase 39 chat work.
- The 4 new role-graph schemas — those ship Phase 43 (Rail A second slot).
- The runtime `mutation_discipline` invariant + `KnowledgeLayer.bootstrap()` discipline dispatch table — Phase 43 scope.

---

## Outputs expected at chat close

Per `PHASE_MAP.md §1` per-phase workflow (inherited unchanged):

- `phase-39` branch off main → squash-merged PR → `phase-39-confirmed` tag from main-tip.
- `confirmation_docs/PHASE_39_CONFIRMED.md` — ship metadata authored by the tester via `mindsos confirm-phase --phase 39 --notes-file notes-phase-39.md`.
- `confirmation_docs/PHASE_39_DESIGN_LOG.md` — your design-pass picks per round, following the Phase 25/Phase 35 template.
- `confirmation_docs/notes/notes-phase-39.md` — tester notes (created by the wrapper; tester edits).
- ADR-0044 §amendment-3 + ADR-0150 §amendment-4 (rename row only) ratified text on disk under `docs/decisions/adr/`.
- All shipped code per POST_PHASE_38 §4 Phase 39 "Modules touched."
- `tools/rename_memories_to_episodic_memories.py` migration script.
- `tests/phase_39/` test suite per POST_PHASE_38 §4 Phase 39 "Automated tests."
- `HANDOFF.md` §1 line bump + §2.2 reflection of rename completion + §3.1.7 status update.
- `_workbench/STREAM_A_BACKLOG.md` — close item A1 (if landed); close A6 if absorbed; surface any new Stream A items discovered.
- `future_work/L2_FUTURE_WORK.md` §11 — mark L2-34 + L2-35 as **CLOSED — shipped Phase 39**.

After Phase 39 confirms, the next chat opens **Phase 43** (Rail A, schema-v2) — drafted by you as `confirmation_docs/PHASE_43_NEXT_CHAT_PROMPT.md` per Phase 25→Phase 26 precedent (each phase chat seeds the next).

---

## Process notes inherited from Phase 25 / Phase 35 / Phase 38

- **Probe-first** (Phase 38 R5-PB-I). Most of Phase 38's 5 reversals traced to probes R0 didn't run. The probes above are non-negotiable at R0.
- **Branch off `origin/main` only** — never off a sibling rail's branch even if Phase 40/43/44/45 has a phase-NN branch open under DAG execution.
- **Reading-list discipline (Chat C PB-Z)** — Phase 39 R0 reading-list must enumerate every file Phase 39 touches + diff-check against most-recent main-tip. Anticipates merge collisions with parallel rails.
- **Sentinel chain anchor (Chat C PB-6 + IL-2)** — `tests/phase_39/test_adr_amendment_sentinels.py` (Phase 35 ancestor pattern, applies because Phase 39 ships ADR amendments).
- **Ship-shape default DROPPED at Chat C closure (IL-8)** — Phase 39 is unambiguously code-shipping (net-new src LOC: rename + migration script + ADR amendments + test fixture renames + capacity body re-target). No docs-only PB at R0.
- **Tester two-machine workflow** unchanged: Mac for git + edits + PR + tag; Linux for `docker compose run --rm mindsos-test pytest tests/` + `mindsos confirm-phase`.

---

*End of PHASE_39_NEXT_CHAT_PROMPT.md.*
