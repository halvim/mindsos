# Phase 38 — Design Log

> Captured 2026-05-27. Records the design pushbacks across 6 rounds
> (R0+R1+R2+R3+R4+R5) that resolved Phase 38's load-bearing
> open-question stack (design-only-vs-code-shipping → docs-only ship
> shape) and locked the docs-only surface. Future amendments to the
> closing-phase scope or the docs-only-phase §1 clause should consult
> this file for rationale.

## 0. Scope at chat-open

PHASE_MAP §Phase 38 row (handoff version, pre-amendment):

  * **Deps:** all prior. **Layer:** cross. **Net-new?** No (composes
    shipped pieces).
  * **Features:** cookbook text-realm + code-slice end-to-end via CLI
    through L0 → L1 → L2 → L3.
  * **Tests:** golden-output for both cookbook flows; runs in under
    N seconds against the test fixture.
  * **Pass criterion:** the vertical slice that lives today across
    `tests/` produces the same artefacts via the CLI — no surprises.
    Final mkdocs pass: lift `strict: true` if all broken links are
    gone, and a final review of every page's `last_confirmed_phase`
    front-matter for orphans.
  * **Docs:** `docs/usage/cookbook/text-realm.md`, `nlu-slice.md`,
    `code-slice.md` — full.

**Load-bearing open question (chat-prompt PB-1 territory).** Phase 38
doesn't have a single load-bearing PB-1 the way Phases 33-36 did (no
new ADR-flip; no new code surface mandated). PHASE_MAP §38 says
"Net-new? No (composes shipped pieces)" — but the cookbook flows
still need authoring + golden fixtures + the mkdocs strict-lift
commit. Multiple R0 candidates: design-only vs code-shipping shape;
cookbook scope (3 cookbooks vs 1); mkdocs `strict: true` lift
timing; `last_confirmed_phase` orphan audit scope; Local-write CLI
session-injection mechanism.

The real R0 finding was that several of these candidates were
**unscoped against shipped reality** — Phase 36 carry-forward #5
(Local-write CLI smoke needs session-injection) was the load-bearing
fact none of the chat-prompt candidates surfaced cleanly.

**Reframed across 6 rounds to: docs-only ship per PHASE_MAP §1
design-only-phase extension (sub-shape `docs-only phase` introduced
at R4-PB-F).** No version bump, no tag, no `mindsos confirm-phase`,
no `release.yml` invocation. Sentinel chain extends
`14a → 15a → 15b → 35 → 36 → 38`. PHASE_38_DESIGN_LOG.md is the
ship artifact. Phase 14a + 15b + 35 precedent established the
design-only ship shape; Phase 38 extends to docs-only (no ADR work).

## 1. Required reading consumed at chat-open

- `halvim_mindsos/confirmation_docs/PHASE_MAP.md` §38 + §6 + §7
  (q5/q9/q10) + §1 design-only exception clause.
- `halvim_mindsos/confirmation_docs/PHASE_36_NEXT_CHAT_PROMPT.md`
  (the Phase 38 seed).
- `halvim_mindsos/confirmation_docs/PHASE_36_CONFIRMED.md` (most
  recent ship; baseline 3373/57).
- `halvim_mindsos/mkdocs.yml` (`strict: false` setting + nav).
- `halvim_mindsos/mindsos_capacity/__init__.py:108-125` (5 deferral
  anchors).
- `halvim_mindsos/mindsos_capacity/capacity_layer.py:486-560`
  (`invoke()` session signature).
- `halvim_mindsos/mindsos_capacity/builtins/consolidate.py:108-140`
  (Local-write capacity body; `context.get("session")` reader).
- `halvim_mindsos/mindsos_cli/commands/capacity.py:240-265`
  (`_construct_invoke_layer` — in-memory fresh KL per CLI invocation).
- `halvim_mindsos/mindsos_cli/commands/server.py:510-608`
  (`mindsos server login` already exists; writes `~/.mindsos/token`).
- `halvim_mindsos/mindsos_server/sessions.py:482`
  (`session_from_token(conn, token, *, ttl) -> Session`).
- `halvim_mindsos/mindsos_server/persistence/bootstrap.py:51-95`
  (`bootstrap_kl_from_falkordb(client) -> KnowledgeLayer`).
- `halvim_mindsos/mindsos_server/persistence/local_persister.py:57-58`
  ("Phase 25 ships `InMemoryLocalPersister` only.
  `SQLiteLocalPersister` + `FalkorDBLocalPersister` land at the
  [pending future phase]" — the load-bearing R3-PB-A finding).
- `halvim_mindsos/mindsos_knowledge/knowledge_layer.py:231-250`
  (`local_metagraph(user_id)` lazy in-memory).
- `halvim_mindsos/tests/phase_32/test_integration_b.py` (the
  cookbook transcribe-source).
- `halvim_mindsos/tests/phase_35/test_adr_amendment_sentinels.py`
  (sentinel-chain ancestor pattern).
- `halvim_mindsos/tests/phase_36/test_adr_amendment_sentinels.py`
  (most recent chain link).
- `halvim_mindsos/confirmation_docs/PHASE_35_DESIGN_LOG.md` (the
  template for this file).
- `halvim_mindsos/docs/index.md` (Phase 00 stub awaiting rewrite).
- `halvim_mindsos/docs/changelog/CHANGELOG.md` (front-matter
  precedent; missing per-phase entries 18-36).
- 5 pages with established `last_confirmed_phase` front-matter
  (knowledge-sources/{dolce,oewn,framenet}.md +
  changelog/CHANGELOG.md + usage/core/metagraph-schema.md).
- Memory: `[[project-mindsos-phase-36]]`,
  `[[project-mindsos-phase-32]]`,
  `[[feedback-export-slate-sentinel-audit]]`,
  `[[feedback-docker-compose-version-bump-site]]`,
  `[[feedback-release-tag-after-squash-merge-only]]`,
  `[[feedback-confirm-phase-machine-locality]]`,
  `[[user-two-machine-setup]]`.

## 2. Design pushbacks (R0+R1+R2+R3+R4+R5) — picks per round

Picks-summary-per-round form per Phase 35 R4 PB-F4 (target ~400
lines; full PB enumeration only when picks reversed). All PBs were
user-agreed across re-litigation rounds; corrections from earlier
rounds supersede via the round numbers below.

### Round 0 — initial scope shape + cookbook scope

| PB | Pick |
|---|---|
| PB-1 (load-bearing) | **Documentation-shipping or code-shipping?** — answer downstream of PB-5; my pick at R0: documentation-shipping IF PB-5 says no, code-shipping IF yes. (Resolved code-shipping at R0; reversed at R3-PB-D to docs-only.) |
| PB-2 | **text-realm cookbook only.** nlu-slice + code-slice → §6 `out of scope` via §inline-amendment. No shipped capacities back nlu or code-slice. (Locked; stable through ship.) |
| PB-3 | **Probe `mkdocs build` at impl step-0; lift if clean.** (Reversed at R4-PB-A: structural Model C blocker, defer entirely.) |
| PB-4 | **`PHASE_38_PAGE_INVENTORY.md` artifact;** flag drift; don't block ship on resolving. (Locked.) |
| PB-5 | **Ship `mindsos server session create --user-id X --as-admin <admin>` + `--session-token` flag on `capacity invoke` (~50 LOC).** (Reversed at R1-PB-A to no-new-verb-just-flag, then reverted entirely at R3-PB-B.) |
| PB-6 | **Parent-tree ADR consolidation out of scope** (Model C). (Locked.) |
| PB-7 | **`_source_backup/` retention out of scope** (parent-tree concern). (Locked.) |

### Round 1 — reframe PB-5 + missing-pages fate

| PB | Pick |
|---|---|
| PB-A | **REFRAME PB-5: `mindsos server login` already exists** (Phase 19 ships `~/.mindsos/token`); no new verb needed. Surface = `--session-token` flag on `capacity invoke` only. Hybrid auto-detect (`~/.mindsos/token`) + explicit override. ~20 LOC. (Reversed at R3-PB-B.) |
| PB-B | **Spec 4 failure-mode cases at R1: token missing → silent Global fallback; token expired → exit 4; CAN_WRITE_GLOBAL missing → unchanged; token valid → Session populated.** (Mooted at R3-PB-B revert.) |
| PB-C | **4-clause §inline-amendment under PHASE_MAP §38.** (Refined at R3-PB-E to 3 clauses, then back to 4 at R4-PB-G.) |
| PB-D | **Add `Phase 32+` / `--session-token CLI flag` literals to step-0 probe checklist** + update `[[feedback-export-slate-sentinel-audit]]` with future-anchor-class extension. (Locked.) |
| PB-E | **Author 3 missing pages (`index.md` + `whats-new-v4.md` + `glossary.md`); 3 out-of-scope (`facts-and-figures.md` + `layers.md` + `society-of-mind.md`).** (Locked.) |
| PB-F | **Full `last_confirmed_phase` backfill on existing pages** (estimated 29 at R1; corrected at impl step-0 to **2 pages**, 71 of 73 already adopted). |
| PB-G | **Hold R0 PB-3 — strict-lift probe at impl step-0.** (Mooted at R4-PB-A.) |
| PB-H | **11-site version bump `+phase36 → +phase38`.** (Mooted at R3-PB-D revert to docs-only.) |

### Round 2 — refinements + REVERSAL #1 (Falkor wire-up)

| PB | Pick |
|---|---|
| PB-A | **REVERSAL #1: option (b) — close Phase 30 CF #3 by wiring `bootstrap_kl_from_falkordb` into `_construct_invoke_layer` with in-memory fallback (~80-120 LOC).** Reason: in-memory KL undermines Local-write cookbook narrative; wiring Falkor makes persistence truthful. (Reversed at R3-PB-A: Local persistence itself wasn't shipped — fix doesn't actually fix the problem.) |
| PB-B | **Lock R1-PB-A surface at ~10 LOC.** `_construct_invoke_layer` doesn't need a session= parameter; `layer.invoke(*, session=None, ...)` already exists per Phase 33 ADR-0146 §am-1 clause 2. (Mooted at R3-PB-B.) |
| PB-C | **Explicit `--session-token` → exit 4 if server.db missing; auto-detect → silent Global fallback.** (Mooted at R3-PB-B.) |
| PB-D | **`last_confirmed_phase`: single value = highest phase in §6 row.** (Refined at R4-PB-H to allow `last_design_only_phase` per CHANGELOG.md precedent.) |
| PB-E | **Lift if `mkdocs build --strict` exits 0 OR fails only on OOS pages.** (Reversed at R4-PB-A.) |
| PB-F | **8 sentinel files in `tests/phase_38/` (option b path).** (Refined at R3-PB-G to 5, then R5-PB-D to 1 file with 6 functions.) |
| PB-G | **Cookbook = transcript Phase 32 + extend with Local-write under (b).** (Refined at R3-PB-F to "light rewrite of Phase 32 transcript, no extension.") |
| PB-H | **`mindsos confirm-phase --init-notes 38`** for notes template. (Mooted at R3-PB-D revert.) |

### Round 3 — REVERSAL #2 (Local persistence)

| PB | Pick |
|---|---|
| PB-A | **REVERSAL #2: Local persistence wasn't shipped at Phase 36** (`local_persister.py:57-58` — "`SQLiteLocalPersister` + `FalkorDBLocalPersister` land at the [pending future phase]"). Wiring Falkor for Global doesn't fix Local-write evaporation. Revert R2-PB-A. **Read-side cookbook only.** Defer Local-write CLI demo to L4 follow-up plan. |
| PB-B | **Revert R1-PB-A: defer `--session-token` flag to L4** alongside `FalkorDBLocalPersister` as a coherent unit. (The flag's primary use case is Local-write; without persistence the flag's value is half-broken.) |
| PB-C | **NEW: update `mindsos_capacity/__init__.py:117` future-anchor comment** ("Phase 32+ per PB-30(a)" → "deferred to L4 follow-up plan per Phase 38 R3-PB-B"). (Refined at R4-PB-D + R5-PB-C to 5 anchors total.) |
| PB-D | **REVERSAL #3: design-only ship.** With R1-PB-A reverted + R2-PB-A reverted, Phase 38 has zero net-new code. Phase 14a/15b/35 precedent: no version bump, no tag, no `confirm-phase`, PHASE_38_DESIGN_LOG.md as ship artifact. |
| PB-E | **3-clause §inline-amendment** under PHASE_MAP §38 (down from 4). (Reversed at R4-PB-G: pass criterion line itself is wrong post-Model-C, restore to 4.) |
| PB-F | **Cookbook = light rewrite of Phase 32 transcript; no extension.** Smokes via tests/phase_32/test_integration_b.py. (Locked.) |
| PB-G | **5 sentinel files in tests/phase_38/.** (Refined at R5-PB-D to 1 file, 6 functions.) |
| PB-H | **§inline-amendment under §38 + direct §6 sub-table edits.** (Locked.) |

### Round 4 — REVERSAL #4 (strict-lift) + saturation pass

| PB | Pick |
|---|---|
| PB-A | **REVERSAL #4: strict-lift structurally impossible without Model C remediation.** `mkdocs build` against halvim tree produces hundreds of `decisions/adr/NNNN-*.md` cross-link WARNINGs because ADRs live in parent project tree (Model C). Defer to L4/L5 follow-up plan; document blocker in DESIGN_LOG. |
| PB-G | **4-clause §inline-amendment** (restored from R3-PB-E's 3 — pass criterion line itself needs revision because broken-link condition can't be met). |
| PB-B | **Fix nav at Phase 38: 3 R1-PB-E authored pages + capacity-write-flows broken nav + CHANGELOG orphan.** (At impl step-0 the nav-vs-disk diff revealed false positives — basename-only regex caught path-qualified entries as broken. R4-PB-B narrowed to: add 3 authored pages + new Cookbook subsection.) |
| PB-C | **Rename `test_adr_amendment_sentinels.py` → `test_phase_38_doc_sentinels.py`** — Phase 38 ships zero ADR amendments; filename misrepresents content. |
| PB-D | **Update 5 deferral anchors (not 4) in `mindsos_capacity/__init__.py:100-125`.** R3-PB-C miscounted; line 100 `add_type_compat` was missed. (Confirmed at step-0; the actual count is 5.) |
| PB-F | **Extend §1 design-only-phases clause via §inline-amendment to cover docs-only sub-shape** — Phase 38 is the inflection. |
| PB-E | **PHASE_38_DESIGN_LOG.md = Phase 35 structure mirror** (~400-500 lines target). |
| PB-H | **Front-matter: single `last_confirmed_phase`; add `last_design_only_phase` only when applicable** (CHANGELOG.md precedent). |
| PB-I | **Keep cookbook fixture `"the cat sat"`; document seed-text choice in prose.** |
| PB-J | **No `L3-capacity-write-flows.md` tracker update at Phase 38** (no new write capacity at Phase 38). |

### Round 5 — impl-lock pass (zero reversals)

| PB | Pick |
|---|---|
| PB-A | **PHASE_MAP §38 4-clause §inline-amendment text locked** (literal). |
| PB-B | **PHASE_MAP §1 1-clause §inline-amendment text locked** (literal). |
| PB-C | **`mindsos_capacity/__init__.py:100-125` replacement block locked** (5 anchors, literal). |
| PB-D | **1 sentinel file + 6 functions in `test_phase_38_doc_sentinels.py`** (refined from R3-PB-G's 5 files). |
| PB-E | **7-column inventory schema + sample row locked.** |
| PB-F | **6-section DESIGN_LOG outline locked** (this file). |
| PB-G | **NEW: CHANGELOG.md backfill** of ~20 missing per-phase entries (18-36 + 14a + 35) + front-matter bump to `last_confirmed_phase: 36` + `last_design_only_phase: 38`. |
| PB-H | **NEW: §7 q5/q9/q10 RESOLVED-at-Phase-38 annotations** inline in §7. |
| PB-I | **Declare R5 saturated; await `proceed`** — pattern matches Phase 36 R5 (impl-locks only, zero reversals). |

### Round 6 — post-design reversal (tester preference)

Captured 2026-05-28 post-impl, mid-ship. Tester preferred running the
canonical `mindsos confirm-phase --phase 38 --notes-file
notes-phase-38.md` wrapper to produce `PHASE_38_CONFIRMED.md` as a
template-parity artifact with code-shipping phases. The wrapper's
doctor preflight enforces `--phase NN` against
`manifest.toml [mindsos] phase` and `docker-compose.yml` image tags
(both at "36" / "phase36-*" after R3-PB-D's no-version-bump pick).
Doctor refused: `--phase 38 mismatches manifest [mindsos] phase = '36'`.

| PB | Pick |
|---|---|
| PB-A (**REVERSAL #5**) | **Convert Phase 38 from docs-only ship to code-shipping at execution.** Reverses R3-PB-D + R5-PB-B (sub-shape-application-to-Phase-38). 12-site version bump `+phase36 → +phase38` executed mid-ship: `pyproject.toml` + `mindsos_cli/manifest.toml` (version + phase fields) + `docker-compose.yml` (prod + test image tags) + 7 package `__init__.py` `__version__` literals. The PHASE_MAP §1 docs-only-phase sub-shape definition (R5-PB-B) stays valid as a future-precedent extension; Phase 38 itself opts out of it at execution. PR-to-main + tag `phase-38-confirmed` after squash-merge + release.yml runs on tag push. |
| PB-B | **Artifact reconciliation:** PHASE_38_DESIGN_LOG (this §2 round), PHASE_MAP §38 Status line, PHASE_MAP §1 §inline-amendment (preserved-as-precedent + Phase-38-opted-out note), CHANGELOG.md Phase 38 entry, sentinel test module docstring, and the notes-phase-38.md input file all updated to reflect the execution-time conversion. The `mindsos_capacity/__init__.py` 5 deferral anchors stay as-is (R4-PB-D's L4-deferral picks are unaffected by ship shape). |
| PB-C | **Docs-only-vs-code-shipping reconciliation rule of thumb (for L4/L5 follow-up plan):** design-time picks the convention; execution-time may revert if the tester finds the convention impractical. Record post-design reversals in DESIGN_LOG §2 as a separate round (this Round 6), not as inline `§inline-amendment` to the original round. Saturation count therefore becomes "6 design rounds + 1 post-design reversal round." |

### Saturation observation

6 design rounds (R0+R1+R2+R3+R4+R5) + 1 post-design reversal round (R6). 5 reversals across saturation:

  1. **R1-PB-A** reversed R0-PB-5 (no new "session create" verb;
     `mindsos server login` already exists).
  2. **R3-PB-A** reversed R2-PB-A (Falkor wire-up doesn't fix Local
     persistence; `FalkorDBLocalPersister` unshipped at Phase 36).
  3. **R3-PB-B** + **R3-PB-D** reversed R0-PB-1 + R1-PB-A (no
     `--session-token` flag; revert to docs-only ship).
  4. **R4-PB-A** reversed R0-PB-3 + R2-PB-E (strict-lift structurally
     impossible; Model C remediation is L4/L5 scope).
  5. **R6-PB-A** (post-design, mid-ship) reversed R3-PB-D + R5-PB-B's
     application-to-Phase-38 (docs-only ship → code-shipping at
     tester preference for running `mindsos confirm-phase` wrapper).
     R5-PB-B's docs-only sub-shape definition stays as a future
     precedent; Phase 38 itself opts out at execution.

R5 produced impl-locks only, zero reversals — saturation matched the
Phase 36 R5 signature at design time. R6 is a post-design reversal
captured separately. Each design-time reversal (R1-R4) was caused by
probing reality that an earlier round had not probed. R6 was caused
by tester preference at execution overriding a design-time pick.
Lesson for future closing-phase work: probe deeply on the layer-state
assumptions (persistence shipping status, Model C link state,
in-memory-vs-Falkor) before locking the cookbook narrative AND
acknowledge that design-time picks about ship-shape may be reversed
at execution if the tester prefers the canonical workflow.

## 3. Ship surface

### Halvim tree (committed at `phase-38` branch)

- **EDIT** `confirmation_docs/PHASE_MAP.md` §38 — 4-clause
  §inline-amendment block (R5-PB-A literal text).
- **EDIT** `confirmation_docs/PHASE_MAP.md` §1 — 1-clause
  §inline-amendment extending design-only-phases row with docs-only
  sub-shape (R5-PB-B literal text).
- **EDIT** `confirmation_docs/PHASE_MAP.md` §6 — 5 sub-table rows
  revised to `**out of scope** (deferred to L4/L5 follow-up plan;
  Phase 38 ...)`: `nlu-slice.md`, `code-slice.md`,
  `facts-and-figures.md`, `layers.md`, `society-of-mind.md`.
- **EDIT** `confirmation_docs/PHASE_MAP.md` §7 — q5/q9/q10 inline
  RESOLVED annotations (R5-PB-H).
- **EDIT** `mindsos_capacity/__init__.py:100-125` — 5 deferral
  anchors updated from "Phase 30+/32+" to "deferred to L4 follow-up
  plan per Phase 38 R4-PB-D" (R5-PB-C literal text).
- **EDIT** `mkdocs.yml` — add 3 nav entries (whats-new-v4 in Get
  started, glossary in Concepts) + new "Cookbook (Phase 38)"
  subsection under Usage referencing `text-realm.md`.
- **REWRITE** `docs/index.md` — from Phase 00 stub to v4 docs
  homepage (R1-PB-E).
- **NEW** `docs/getting-started/whats-new-v4.md` — v4 release
  headlines + L4/L5 carry-forward list (R1-PB-E).
- **NEW** `docs/concepts/glossary.md` — terms-of-art reference
  (R1-PB-E).
- **NEW** `docs/usage/cookbook/text-realm.md` — read-side cookbook
  transcribing Phase 32 Integration B's 11 substeps (R3-PB-F +
  R4-PB-I).
- **EDIT** `docs/dev/review-checklist.md` — add
  `last_confirmed_phase: 36` front-matter (R1-PB-F backfill).
- **EDIT** `docs/usage/knowledge/versioning.md` — add
  `last_confirmed_phase: 17` front-matter (R1-PB-F backfill).
- **EDIT** `docs/changelog/CHANGELOG.md` — backfill ~21 missing
  per-phase entries (Phases 18 + 19 + 20 + 21 + 22 + 24 + 25 + 26a
  + 26b + 27 + 28 + 29 + 30 + 31 + 32 + 33 + 34 + 35 + 36 + 14a +
  38); bump front-matter to `last_confirmed_phase: 36` +
  `last_design_only_phase: 38` (R5-PB-G).
- **NEW** `confirmation_docs/PHASE_38_PAGE_INVENTORY.md` — 7-column
  audit per R5-PB-E.
- **NEW** `tests/phase_38/__init__.py` (empty).
- **NEW** `tests/phase_38/test_phase_38_doc_sentinels.py` — 6
  sentinel functions per R5-PB-D + R4-PB-C rename. Sentinel chain
  extends `14a → 15a → 15b → 35 → 36 → 38`.
- **NEW** `confirmation_docs/PHASE_38_DESIGN_LOG.md` (this file).
- **POST-DESIGN (R6-PB-A):** 12-site version bump
  `+phase36 → +phase38` across `pyproject.toml`,
  `mindsos_cli/manifest.toml` (version + phase fields),
  `docker-compose.yml` (prod + test image tags), and 7 package
  `__init__.py` `__version__` literals (`mindsos_admin`,
  `mindsos_capacity`, `mindsos_cli`, `mindsos_core`,
  `mindsos_instances`, `mindsos_knowledge`, `mindsos_server`).
- **POST-DESIGN (R6-PB-A):** `notes-phase-38.md` hand-authored at
  Mac as wrapper input (matches code-shipping per-phase convention
  for Phase 02+).
- **POST-DESIGN (R6-PB-A):** `confirmation_docs/PHASE_38_CONFIRMED.md`
  generated by `mindsos confirm-phase --phase 38 --notes-file
  notes-phase-38.md` from Linux test image (wrapper run replaces the
  initially hand-authored draft that was created before R6-PB-A's
  conversion decision; that draft was deleted from Mac).

### Parent tree (filesystem-only, Model C; no commit)

**Zero parent-tree changes at Phase 38.** Per R0-PB-6 + R0-PB-7 +
R4-PB-A, parent-tree ADR consolidation + `_source_backup/` retention
+ Model C ADR-link remediation are all explicitly out of scope.

## 4. Carry-forwards to L4/L5 follow-up plan

Consolidated list of everything deferred at Phase 38. The L4/L5
follow-up plan should treat these as the inherited backlog.

### Code surfaces

1. **`mindsos capacity invoke --session-token` CLI flag** (Phase 30
   PB-30(a); Phase 38 R3-PB-B revert). Hybrid auto-detect
   `~/.mindsos/token` + explicit override. ~10 LOC + 4 failure-mode
   cases. Ships symmetrically with item 3.
2. **Falkor-backed L3 bootstrap + state-file serialization** (Phase
   30 R2 PB-27(a); Phase 38 R4-PB-D). Wire
   `bootstrap_kl_from_falkordb` (Phase 26a) into
   `_construct_invoke_layer` with reachability probe + in-memory
   fallback. ~80-120 LOC.
3. **`FalkorDBLocalPersister`** (Phase 25 named-as-deferred;
   Phase 38 R3-PB-A). The persistence implementation that makes
   Local-write end-to-end CLI demo work. ~200-400 LOC + Cypher
   contracts + ADR. Pairs with item 2 (Falkor-backed Global) and
   item 1 (--session-token flag) for the Local-write cookbook
   surface.
4. **`add_type_compat` admin API + bulk rediscover verb** (Phase 38
   R4-PB-D; was Phase 32+).
5. **`include_deprecated` parameter discipline across L3 walks**
   (Phase 38 R4-PB-D; was Phase 30+).
6. **Per-user Local-scoped `ProblemTraceSink` dict** (was deferred
   to L4 since Phase 28 R2 PB-29(a); already L4-pointing).
7. **`--install-builtins=<family,...>` CLI flag on `capacity
   invoke`** (Phase 38 R4-PB-D; was Phase 32+ "when a second
   builtins family ships"). Waits for the second builtins family.
8. **`handle.validate_xref` body** wires alongside first
   XRef-writing L3 capacity per ADR-0139 §am-1 clause 3.
9. **4 unconsumed L2 validators** (`validate_local_to_global_ref`,
   `validate_alignment_role_naming`, `validate_ref_type`,
   `validate_promotion_candidate`). Pure-function tests cover them
   at Phase 36; no integration coverage until per-flow consumer
   capacities land.

### Docs surfaces

10. **`mkdocs build --strict` lift** (Phase 38 R4-PB-A; PHASE_MAP §7
    q5 RESOLVED-deferred). Requires Model C remediation across
    halvim `concepts/*.md` + `api/*.md` pages. Options: (α) strip
    `decisions/adr/NNNN-*.md` links across ~30 pages; (β)
    `mkdocs-redirects` plugin with path-prefix redirect to parent
    tree; (γ) halvim-side ADR shim pages mirroring parent
    filenames + `external_url` front-matter. Recommended: (β) —
    minimum edit surface; one config block + new dep.
11. **`docs/usage/cookbook/nlu-slice.md` + `code-slice.md`** (Phase
    38 R0-PB-2). Currently OOS in §6. Either flip back to in-scope
    once nlu + code builtins ship, or accept as permanent OOS.
12. **`docs/getting-started/facts-and-figures.md`** (Phase 38
    R1-PB-E OOS). Reference-table material; ships after L4/L5
    delivers something to reference.
13. **`docs/concepts/layers.md` + `society-of-mind.md`** (Phase 38
    R1-PB-E OOS). L4/L5 conceptual content; authoring at Phase 38
    would pre-empt L4/L5 design.
14. **Per-page ADR cross-reference cleanup** — ~17 pages currently
    link to `decisions/adr/NNNN-*.md` paths that don't resolve.
    See PHASE_38_PAGE_INVENTORY.md "Drift discussion" for the
    full inventory. Solved as a side-effect of item 10.
15. **PHASE_MAP §5 row appendices**: ~15 ADR §amendment-N texts
    are flagged in PHASE_MAP "(file edit Phase 38)" but live in
    parent tree per Model C. Per R0-PB-6 these are parent-tree
    consolidation work, not halvim Phase 38 scope. Defer
    indefinitely or take up as a parent-tree-only ship event.
16. **`usage/knowledge/memories.md` §6 drift** — PHASE_38_PAGE_INVENTORY.md
    flags this single non-benign drift. Reconcile by either
    re-including in §6 as Phase 13 (the actual ship phase) or
    deleting the page at L4 cleanup. Recommended: re-include.
17. **`concepts/promotion-bridge.md`** — Phase 24 §6 amendment
    appears unapplied; verify and back-fill.

### Phase-mechanics carry-forwards

18. **`notes-phase-NN.md` per-phase parity** — Phase 38 ships no
    notes file (design-only/docs-only shape) but historical
    phases 02-36 have them. L4/L5 should standardize.
19. **CHANGELOG `last_design_only_phase` convention** — only
    CHANGELOG.md adopts the 2-field shape today. Either extend
    convention or simplify to single-field across the board.

## 5. Process notes

- **Saturation pattern (R5-PB-I).** 4 reversals across 5 design
  rounds is high — each reversal traceable to a probe R0 didn't run.
  Future closing-phase or layer-boundary phases should probe more
  deeply at R0:
  - Read the **persistence implementation status** of every type
    that the phase's narrative depends on. R3-PB-A would have been
    caught at R0 with a `grep "FalkorDBLocalPersister"` probe.
  - Read the **current `mkdocs build` output** before locking
    strict-lift criteria. R4-PB-A would have been caught at R0.
  - Read the **CLI verb roster vs intended surface** before
    proposing new verbs. R1-PB-A would have been caught at R0
    with `grep "@server_app.command"`.

- **Design-time picked docs-only (R3-PB-D + R5-PB-B); execution-time
  reverted to code-shipping (R6-PB-A).** Design-time rationale stood:
  Phase 38 has zero net-new runtime code, so the design picked
  docs-only-shape (Phase 14a/15b/35 precedent). At ship execution the
  tester preferred running `mindsos confirm-phase` per the
  code-shipping convention; the wrapper's doctor preflight enforces
  manifest parity, so the conversion required the 12-site version bump
  + image retag. R5-PB-B's docs-only sub-shape definition stays
  precedent-valid for future phases. release.yml runs on the
  `phase-38-confirmed` tag after PR squash-merge.

- **Two-machine workflow** (`[[user-two-machine-setup]]`): Mac for
  file edits + git + PR; Linux required for the docker test image
  rebuild + sentinel run + cumulative regression + `mindsos
  confirm-phase` wrapper invocation. (Design-time R3-PB-D had made
  Linux optional for this phase; R6-PB-A's docs-only → code-shipping
  conversion at execution restored the standard two-machine
  pattern.)

- **Branch off `main`** at HEAD = Phase 36 squash sha `72ca8fc`
  per PHASE_MAP §1 "branch off `origin/main`, never off prior
  phase's branch." Branch name `phase-38`. PR → squash-merge to
  main; no tag.

- **Sentinel-chain extension** `14a → 15a → 15b → 35 → 36 → 38`
  is established at `tests/phase_38/test_phase_38_doc_sentinels.py`
  module docstring + the file is renamed per R4-PB-C from the
  ancestor `test_adr_amendment_sentinels.py` pattern because
  Phase 38 ships zero ADR amendments. Chain semantics are
  per-phase, not per-filename.

- **R5-PB-G CHANGELOG backfill** is the largest doc-edit in the
  ship — adds ~21 per-phase entries spanning Phase 14a through
  Phase 38. The pattern was that CHANGELOG.md had drifted since
  Phase 17's ship (last entry pre-Phase 38 was Phase 17 RETIRED).
  Each entry pulls a terse summary from the corresponding memory
  entry or `PHASE_NN_CONFIRMED.md`.

- **R3-PB-A's load-bearing finding** — `local_persister.py:57-58`
  saying "Phase 25 ships `InMemoryLocalPersister` only" — was the
  single fact that reframed the entire Phase 38 scope. Carry the
  lesson: design saturation against shipped reality must probe
  persistence layer state explicitly when the phase narrative
  depends on persistence semantics.
