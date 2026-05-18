# Phase 14a — Handoff Prompt (authored at Phase 13 close)

> Authored 2026-05-18 at close of Phase 13 ship. Paste the **PROMPT
> BODY** below into a fresh Claude chat (MindsOS project) when ready
> to run the Phase 14a design pass. Phase 14a is a docs/ADR-only
> phase per Phase 13 PB-19 + PB-20 — no code, no tag, no
> `mindsos confirm-phase`, no version bump.

---

## PROMPT BODY (copy from here)

```
══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 14a design pass (DESIGN-ONLY)
══════════════════════════════════════════════════════════════════════

Project: MindsOS — folder `halvim_mindsos/` under `Layered Intelligence`.

ROLE: Critical design reviewer for the L2 knowledge-addition
lifecycle synthesis. Follow the project-level CLAUDE.md
skeptical-default + terse + pros/cons + alternatives behavior.

PHASE 14a SCOPE — DESIGN-ONLY (no code, no tag, no confirm-phase, no
version bump per Phase 13 PB-20). Phase 14a is the first
design-only phase under the new §1 PHASE_MAP exception clause Phase
13 added.

Deliverables:

1. **ADR-0150** "L2 knowledge lifecycle" (Phase 13 reserved the
   number; Phase 14a writes the content). File:
   `/Layered Intelligence/docs/decisions/adr/0150-l2-knowledge-lifecycle.md`.
   Status → Accepted at chat-close.
2. **`docs/concepts/knowledge-lifecycle.md`** — synthesis page
   naming all entry points + cross-phase pointers.
3. **`docs/concepts/user-local-authoring.md`** — user-Local content
   path (Phase 24 propose_for_promotion + Phase 33-35 write
   capacities through KLWriteHandle).
4. **`docs/concepts/admin-global-shipping.md`** — admin-Global
   release path (Phase 15 importers + Phase 37 server-owns-importers).
5. **PHASE_MAP amendments** to §Phase 14 / 15 / 16 / 17 / 24 / 37
   rows naming each phase's "Lifecycle role" sub-field (a new
   optional §2 row-schema field Phase 14a introduces). §2 amendment
   declares the new optional field; 6 phase rows add it.

NOT in scope:

* Any `mindsos_*` package edits.
* Any test edits.
* Any phase-bump cascade.
* Any `mindsos confirm-phase` invocation.
* Any tag.

BEFORE DOING ANYTHING — REQUIRED READING (in order):

1. `MEMORY.md` (auto-loaded). Feedback entries are hard rules.
2. `project_mindsos_phase_12_implemented.md` (memory).
3. `confirmation_docs/PHASE_13_DESIGN_LOG.md` — esp. §1 PB-19 +
   PB-20 + PB-21 + PB-23 (the locks Phase 14a inherits).
4. `confirmation_docs/PHASE_13_CONFIRMED.md` `tester_notes`
   (load-bearing per PHASE_MAP §0).
5. `confirmation_docs/PHASE_MAP.md` §1 (esp. the NEW
   "design-only phases are an exception" clause) + §Phase 14a row
   (Phase 13 inserted this row) + §Phase 13 row.
6. `project_mindsos_l2_redesign_locks.md` (memory) — KL drops write
   API; hybrid validators; MetagraphView read-only; server owns
   importers. These bound the lifecycle design.
7. `_source_backup/docs_legacy_full/DESIGN_UPPER_LAYER_ROLES.md`
   §3-§5 — Global vs Local model + ownership matrix + ref-discipline.
8. `_source_backup/docs_legacy_full/DESIGN_SERVER_AUTH.md` (any
   §4-§5 content on installation/extraction hooks).
9. `/Layered Intelligence/docs/decisions/adr/0118-*.md`
   (propose_for_promotion).
10. `/Layered Intelligence/docs/decisions/adr/0144-*.md`
    (server-owns-importers, Phase 37).
11. `/Layered Intelligence/docs/decisions/adr/0145-*.md` and
    `0146-*.md` and `0147-*.md` (L3 write capacities chain).

CARRY-FORWARD FROM PHASE 13 (lifecycle-relevant subset):

* **Closed-role principle** — Phase 13 hard-codes the 8 roles
  (Phase 12 `ROLE_*` constants + Phase 13's 9 schema builders +
  alignment-prefix branch). Phase 14a's ADR-0150 §Decision MUST
  formally close Flavor B (no new roles at runtime) per Phase 13
  PB-19 lock. Anyone wanting to open Flavor B writes an ADR
  superseding ADR-0150.
* **Lifecycle pieces distributed across 6 phases (14, 15, 16, 17,
  24, 37).** Phase 14a synthesises — does NOT re-decide.

DESIGN WORKFLOW PHASE 14a SHOULD FOLLOW:

1. Round 1 of PBs covering: (a) what the lifecycle docs should
   contain at the synthesis level, (b) the §2 row-schema amendment
   shape for the "Lifecycle role" field, (c) ADR-0150 outline
   (Decision / Consequences / Alternatives).
2. User sign-off batch-by-batch.
3. Maximum 3 PB rounds per the §14a row Risks clause cap.
4. Then write the ADR + 3 docs + 6 row amendments.
5. Squash-merge to main. No tag.

FIRST RESPONSE IN THE NEW CHAT SHOULD:

1. Confirm you've read the cited files (or report which are
   missing).
2. Surface 1-3 PRE-DESIGN pushbacks about the lifecycle synthesis
   shape (e.g., should each lifecycle step be an ADR §Consequences
   item, or in a separate doc; should ADR-0150 §Alternatives list
   the rejected Flavor B opening; how granular should the
   "Lifecycle role" sub-field be).
3. Ask the user the single highest-value missing-constraint
   question.

DO NOT start writing the ADR / docs in the first response. Design
first, sign-off, then write.

Phase 14a's deliverables ship in one PR. Phase 14 branches off
main-tip after merge — no `phase-14a-confirmed` tag exists, by
design.

After Phase 14a ships, author `PHASE_14_NEXT_CHAT_PROMPT.md`
(Phase 14a's last deliverable) — Phase 14 chat will inherit the
ADR-0150 locks + the lifecycle docs.
══════════════════════════════════════════════════════════════════════
```
