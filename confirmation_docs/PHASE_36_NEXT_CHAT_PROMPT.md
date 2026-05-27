# PHASE 36 → PHASE 38 NEXT CHAT PROMPT

> Phase 37 RETIRED 2026-05-19 (Phase 15a PB-17 / ADR-0140 §amendment-1).
> Phase 38 is the next chat — end-to-end vertical slice composing
> everything shipped through Phase 36.

══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 38 DESIGN + IMPLEMENTATION (cookbook flows)
══════════════════════════════════════════════════════════════════════

You are running the Phase 38 design + implementation chat for MindsOS.
Phase 38 = "End-to-end vertical slice" per PHASE_MAP §38. **Net-new?
No** — composes shipped pieces; goal is the cookbook text-realm +
code-slice flows running end-to-end via CLI through L0 → L1 → L2 → L3.

Phase 38 is the **final phase** before mkdocs `strict: true` lift and
`last_confirmed_phase` orphan audit. The phase doesn't introduce
new ADRs or L3/L2/L1 surfaces; it exercises what's already shipped
and surfaces gaps that need pre-strict-lift patches.

Project rules + memory system live in your normal context. Project
rules (skeptical reviewer, picks-per-pushback, alternatives format,
re-litigation cue, saturate before impl, no filler) apply.

══════════════════════════════════════════════════════════════════════
REQUIRED READING — read in this order
══════════════════════════════════════════════════════════════════════

**Scope target:**

1. `halvim_mindsos/confirmation_docs/PHASE_MAP.md` §"Phase 38" + §6
   "Doc-to-phase map" + §7 "Open questions" item 5 (mkdocs strict).
2. `halvim_mindsos/docs/usage/cookbook/text-realm.md` (existence
   check; may be stub/empty).
3. `halvim_mindsos/docs/usage/cookbook/nlu-slice.md` (existence check).
4. `halvim_mindsos/docs/usage/cookbook/code-slice.md` (existence
   check).

**Composition surfaces shipped at Phase 36 (the most recent):**

5. `halvim_mindsos/mindsos_knowledge/validators.py` — 5 validators +
   `_VALIDATORS_BY_ROLE` + `ValidationResult`.
6. `halvim_mindsos/mindsos_capacity/builtins/consolidate.py` +
   `trace.py` — wired capacity bodies calling
   `handle.validate_node(...)` as preconditions.
7. `halvim_mindsos/docs/dev/internals/knowledge.md` §Validator
   surface — composition contract documented.

**Memory entries:** load via `[[name]]` from MEMORY.md as cited:

- `[[project-mindsos-phase-36]]` — most recent ship (validators home).
- `[[project-mindsos-phase-34]]` — write-side surface for the
  capacity flows.
- `[[project-mindsos-phase-32]]` — Integration B precedent (L0+L1+L2+L3
  read-side scenario; Phase 38 is a write-side equivalent).
- `[[reference-mindsos-layer-handoffs]]` — current paths.

══════════════════════════════════════════════════════════════════════
LOAD-BEARING OPEN QUESTIONS (R0 PB-1 candidates)
══════════════════════════════════════════════════════════════════════

Phase 38 doesn't have a single load-bearing PB-1 the way Phases 33-36
did (no new ADR-flip; no new code surface). Multiple candidates:

- **Scope of cookbook flows** — text-realm + nlu-slice + code-slice
  are 3 separate cookbooks per PHASE_MAP §6. Phase 38 ships ALL 3,
  or 1 minimum-viable + defer 2?
- **Cookbook output format** — markdown narrative with embedded
  CLI commands + expected outputs (Phase 02-08 pattern), or
  golden-file test fixtures wrapping the same content?
- **mkdocs `strict: true` lift** — PHASE_MAP §7 question 5
  unresolved. Lift at Phase 38 ship (default), or before, or after?
  Affected by `docs/_inbox/LINK_TODO.md` 55-broken-links state.
- **`last_confirmed_phase` front-matter audit** — Phase 38 is the
  final pass per PHASE_MAP §6 "Final review at Phase 38" — every
  doc page's `last_confirmed_phase` checked against the phase that
  actually last edited it.
- **Phase 38 retirement vs ship.** Does Phase 38 ship code at all?
  The PHASE_MAP §38 entry says "no new code (composes shipped
  pieces)" but the cookbook flows still need authoring + golden
  fixtures + the mkdocs strict-lift commit. R0 PB-1 candidate:
  is Phase 38 code-shipping or design-only?

══════════════════════════════════════════════════════════════════════
SECONDARY OPEN QUESTIONS
══════════════════════════════════════════════════════════════════════

- **Cookbook flows exercise which capacities?** `capacity:consolidate:mm`
  (Phase 34 + 36 wiring) + `capacity:trace:problem` are the only
  shipped writes. Text-realm cookbook likely just walks the read-side
  path (Phase 32 Integration B parity). NLU-slice + code-slice may
  surface gaps in read-side composition.
- **CLI surface completeness.** All Phase 38 cookbooks run via CLI
  per PHASE_MAP §5 "Features: cookbook text-realm + code-slice end-
  to-end via CLI through L0 → L1 → L2 → L3." Are all needed CLI
  verbs shipped? Phase 30 shipped `mindsos capacity find` + Phase 31
  shipped `mindsos capacity invoke`; Phase 38's smoke surfaces any
  missing verbs.
- **Phase 38 carry-forward / no-carry-forward.** This is the last
  numbered phase. Anything not done at Phase 38 needs explicit
  defer-to-later-plan capture (L4/L5 design phase TBD).
- **`docs/getting-started/whats-new-v4.md` + `facts-and-figures.md`**
  per PHASE_MAP §6 "Get Started" — both `Confirms in phase 38`.
  Content authoring is part of Phase 38 ship.

══════════════════════════════════════════════════════════════════════
DESIGN PASS + SHIP CHECKLIST
══════════════════════════════════════════════════════════════════════

Design pass: R0 surfaces scope-of-cookbook-flows + design-only-vs-
code-shipping picks; saturate per project rules; do NOT begin impl
until user says "proceed."

Ship checklist (if Phase 38 ends up code-shipping):

- Branch off `main` at HEAD = Phase 36 squash sha (recorded in
  `PHASE_36_CONFIRMED.md` after Phase 36 ship completes).
- Version bump `0.0.0+phase36 → 0.0.0+phase38` (skip 37 retired).
  10-site list per `[[feedback-docker-compose-version-bump-site]]`.
- `mindsos confirm-phase --phase 38 --notes-file notes-phase-38.md`
  per `[[feedback-confirm-phase-machine-locality]]`.
- Tag `phase-38-confirmed` after squash-merge per
  `[[feedback-release-tag-after-squash-merge-only]]`.

If Phase 38 ends up design-only:

- Pattern follows Phase 14a + 15b + 35 precedent: no version bump,
  no tag, no `confirm-phase`, PHASE_38_DESIGN_LOG.md as the ship
  artifact.
- Sentinel chain extends `14a→15a→15b→35→36→38`.

══════════════════════════════════════════════════════════════════════
FIRST RESPONSE EXPECTATIONS
══════════════════════════════════════════════════════════════════════

1. Confirm required-reading files consumed (terse paths list; no
   content paraphrase).
2. Open Round 0 with design PBs. **PB-1 candidate: design-only-vs-
   code-shipping + cookbook-scope decision.** Secondary PBs follow.
3. Stop. Wait for user re-litigation cue.

DO NOT begin implementation until user says "proceed" after design
saturation.

══════════════════════════════════════════════════════════════════════
before proceeding with these tasks, reanalyze the plan and list your
push backs with options.... show me your choice…. Make sure to read
all required-reading files. The load-bearing open question is whether
Phase 38 is code-shipping or design-only — that choice determines
ship mechanics + sentinel-chain extension shape.
══════════════════════════════════════════════════════════════════════
