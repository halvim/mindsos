# Phase 35 — Design Log

> Captured 2026-05-27. Records the design pushbacks across 4 rounds
> (R0+R1+R2+R3+R4) that resolved Phase 35's load-bearing open question
> (scope shape A/B/C/D) and locked the design-only ship surface for
> ADR-0147 §amendment-1. Future amendments to ADR-0147 (or ADR-0145 /
> ADR-0146 / ADR-0143) should consult this file for rationale.

## 0. Scope at chat-open

PHASE_MAP §Phase 35 row (handoff version, pre-amendment):

* **Features:** `KLWriteHandle.graph()` applies per-flow validators;
  concrete builder per write category.
* **Tests:** per-flow validator runs before commit; mismatched
  flow-vs-category rejected.
* **Docs:** ADR-0147.
* **Deps:** 34. **Layer:** L3. **Net-new?** Yes.

ADR-0147 §Implementation Phase 34 footer instruction: *"Status stays
Proposed. Phase 35 is the canonical flip target per
`halvim_mindsos/confirmation_docs/PHASE_MAP.md` §35."*

**Load-bearing open question (chat-prompt PB-1 territory).** The
PHASE_MAP §35 features line was at war with shipped reality on both
halves:

1. `KLWriteHandle.graph()` was already wired at Phase 34; "applies
   per-flow validators" reads like a runtime validator hook, but
   ADR-0139 §Decision puts validators in `mindsos_knowledge/validators.py`
   at **Phase 36**, not Phase 35. PHASE_MAP §36 even says "validators
   run via Phase 35's `write_and_validate`" — implying §36 wires
   validators INTO `write_and_validate`, not §35.
2. "Concrete builder per write category" reads like ship more
   `capacity:promote:*` / `capacity:author:*` / `capacity:state:*` —
   but ADR-0147 §Decision is explicit: per-flow build, capacities
   wait for L4 flow design closure; no L4 flow has closed.

R0 PB-1 resolved scope to **Option A — Documentary phase**: flip
ADR-0147 Proposed → Accepted via §amendment-1 reframing criterion (a)
in light of the two-step ramp (Phase 33 declaration + Phase 34 body
wiring, both anticipatory); PHASE_MAP §35 inline-amendment clarifies
the features line; per-flow discipline locks strict going forward.

Re-classified across 4 rounds to: **design-only phase per PHASE_MAP §1
exception, no code other than ADR sentinel tests, no version bump, no
tag, no `confirm-phase` invocation (Phase 14a + 15b precedent).**

## 1. Required reading consumed at chat-open

- `halvim_mindsos/confirmation_docs/PHASE_MAP.md` §35 + §34 inline-amendment.
- `docs/decisions/adr/0147-l3-per-flow-write-capacity-build-pattern.md`
  (full, incl. §Implementation Phase 33 + 34 footers).
- `docs/decisions/adr/0139-hybrid-invariant-home.md` §Decision (validator
  home; Phase 36).
- `halvim_mindsos/confirmation_docs/PHASE_34_CONFIRMED.md` (full).
- `halvim_mindsos/mindsos_knowledge/write_handle.py` (full Phase 34 wired body).
- `halvim_mindsos/mindsos_knowledge/identifiers.py` (full; 2-entry `_IRI_BUILDERS`).
- `halvim_mindsos/mindsos_knowledge/knowledge_layer.py` §writeable.
- `halvim_mindsos/mindsos_capacity/builtins/consolidate.py` (full).
- `halvim_mindsos/docs/dev/coordinated-changes/L3-capacity-write-flows.md`.
- Phase 15b sentinel test file (precedent for `tests/phase_35/`).
- Phase 15b DESIGN_LOG.md (precedent for this file).
- Memory: `[[project-mindsos-phase-34]]`,
  `[[feedback-export-slate-sentinel-audit]]`, plus ship-mechanics
  feedbacks.

## 2. Design pushbacks (R0+R1+R2+R3+R4) — picks summary per round

Picks-summary-per-round form per R4 PB-F4 (DESIGN_LOG target ~400
lines; full PB enumeration only when picks reversed). All PBs were
user-agreed across re-litigation rounds; corrections from earlier
rounds supersede via the round numbers below.

### Round 0 — scope shape

| PB | Pick |
|---|---|
| PB-1 (load-bearing) | **A — Documentary phase.** Flip ADR-0147 Proposed → Accepted via §amendment-1; PHASE_MAP §35 inline-amendment; zero new src. Rejected: B (ship more anticipatory capacities — vacuum design risk per ADR-0147 §Rationale), C (validator hook framework — collides with ADR-0139), D (retire Phase 35 — contradicts ADR-0147 §Impl Phase 34 footer). |
| PB-2 | **c — anticipatory-grandfathered.** §amendment-1 carves the 2 shipped capacities; new capacities strictly per-flow. (Superseded by R2 PB-β + R3 PB-A3 on wording — see R2 + R3 below.) |
| PB-3 | Minimal ship: ADR flip + amendment + tracker bump + 2-3 sentinel tests + version bump. (Superseded by R1 PB-B + R3 PB-D3.) |
| PB-4 | ~3343/49 cumulative target. (Superseded by R1 PB-D + R2 PB-δ.) |
| PB-5 | §Accept (a) satisfied via spirit-of-rule reading documented in §amendment-1. (Superseded by R1 PB-A → R2 PB-β.) |
| PB-6 | No pre-positioning for Phase 36's validator hook. |

### Round 1 — ship mechanics correction

| PB | Pick |
|---|---|
| PB-A | **(a) Rewrite criterion (a) explicitly** in ADR-0147 §amendment-1. (Reversed at R2 PB-β: bad ADR hygiene; preserve text + clarify.) |
| PB-B | **No version bump.** Stays `0.0.0+phase34`. Phase 14a + 15b + 23 precedent. |
| PB-C | **No tag.** Same precedent. |
| PB-D | +~3 skip delta for parent-tree ADR sentinels; target ~3340/52. (Refined at R2 PB-δ.) |
| PB-E | **Parent ADR commit first, halvim PR second.** (Revised at R3 PB-H3: parent edit is filesystem-only, not a git commit.) |
| PB-F | Accept strict-forward blocker; no in-scope phase needs new write capacity. |
| PB-G | **Inline-amendment under §35 row** (Phase 34 pattern), not strikethrough. |
| PB-H | **Legend stays.** §amendment-1 carries the anticipatory/per-flow distinction; tracker rows stay `wired`. |
| PB-I | **5 sentinel tests.** (Refined at R2 PB-γ to 1 file with 5 cases.) |
| PB-J | **Hand-create `notes-phase-35.md`**, not `--init-notes`. (Mooted at R2 PB-α — design-only phases ship no notes file.) |

### Round 2 — design-only pattern correction

| PB | Pick |
|---|---|
| PB-α (load-bearing) | **PHASE_35_DESIGN_LOG.md, NOT CONFIRMED.md.** No `confirm-phase`. No `notes-phase-35.md`. Phase 14a (no tests dir, NEXT_CHAT_PROMPT only) + Phase 15b (DESIGN_LOG + 1 test file) + Phase 17 (RETIREMENT_DESIGN_LOG) all confirm design-only phases ship via PR squash-merge with `*_DESIGN_LOG.md` document; `confirm-phase` is for code-shipping phases. |
| PB-β (reverses R1 PB-A) | **Preserve criterion (a) text; §amendment-1 clarifies "shipped through the contract surface" suffices.** Better hygiene than rewriting the gate. |
| PB-γ (refines R1 PB-I) | **1 sentinel test file** (`test_adr_amendment_sentinels.py`, Phase 15b name), 2 files counting `__init__.py`, ~5 cases inside. |
| PB-δ | Skip-delta target: **~3342/51 cumulative**. |
| PB-ε | §amendment-1 text locked (5 clauses). (Refined at R3 PB-A3 to 3 clauses.) |
| PB-ζ | PHASE_MAP §35 inline-amendment text locked. |
| PB-η | **Phase 15b PR pattern:** branch off main → parent-tree filesystem edit + halvim commits → PR → squash-merge. |
| PB-θ | DESIGN_LOG carries Phase 36 carry-forwards explicitly. |

### Round 3 — ship-surface gap closure

| PB | Pick |
|---|---|
| PB-A3 (refines R2 PB-ε) | **§amendment-1 = 3 clauses** (drop R2's clauses 1 + 5). Clause 1 = criterion (a) clarified via contract-surface reading. Clause 2 = anticipatory carve-out. Clause 3 = per-flow strict forward. |
| PB-B3 | Test file header extends chain comment to **14a→15a→15b→35**. |
| PB-C3 | DESIGN_LOG.md includes **"Ship metadata"** section (git_sha + test_summary placeholders). |
| PB-D3 | **Skip export-slate sentinel rename.** Design-only precedent (Phase 14a + 15b did not rename). |
| PB-E3 | Test file name = `test_adr_amendment_sentinels.py` (Phase 15b verbatim). |
| PB-F3 (load-bearing miss) | Phase 35 **ships `PHASE_35_NEXT_CHAT_PROMPT.md`** for the Phase 36 R0 chat. |
| PB-G3 | Tracker page adds a **"Provenance note"** subsection cross-referencing ADR-0147 §am-1 clause 2. |
| PB-H3 (revises R1 PB-E) | **Parent ADR edit is filesystem-only**, not a git commit. (Parent `/Layered Intelligence/` has no `.git` per Model C / `[[project-mindsos-phase-14a-shipped]]`.) Halvim PR carries the halvim-side ship. |
| PB-I3 | **Branch off main**, not `phase-34`. |

### Round 4 — residual content drafting

| PB | Pick |
|---|---|
| PB-meta | **Design saturation reached.** R4 produces only content-drafting clarifications; recommend proceed after these locks. |
| PB-A4 | §amendment-1 clause 1 **cross-references §Implementation Phase 33 footer's existing "anticipatory" framing** — the framing is PROMOTED from descriptive footer caveat to binding §Accept-satisfying evidence. |
| PB-B4 | ADR-0147 §Implementation Phase 35 footer locked (text in §3 below). |
| PB-C4 | Date placeholder `2026-05-27`; tester fills at squash-merge. |
| PB-D4 | NEXT_CHAT_PROMPT.md surfaces validator-composition question with 3 unresolved options A/B/C for Phase 36 R0. |
| PB-E4 | Test assertion anchors locked (6 anchor strings; see `tests/phase_35/test_adr_amendment_sentinels.py`). |
| PB-F4 | DESIGN_LOG target ~400 lines; picks-summary-per-round (not full PB enumeration). |

## 3. Ship surface (Phase 35)

**Parent tree** (`/Layered Intelligence/`):

* `docs/decisions/adr/0147-l3-per-flow-write-capacity-build-pattern.md`
  EDITED — Status `Proposed → Accepted` (frontmatter + first-line);
  §amendment-1 appended with 3 clauses; §Implementation Phase 35
  footer appended; existing §Implementation Phase 34 footer's
  "Status stays Proposed" line annotated with "(Phase 35 ship update:
  Status now Accepted per §amendment-1 below.)".

**Halvim tree** (`halvim_mindsos/`):

* `confirmation_docs/PHASE_MAP.md` §Phase 35 row — §inline-amendment
  block added under the row (Phase 34 pattern). Features line not
  struck through; amendment block carries the corrective explanation.
* `docs/dev/coordinated-changes/L3-capacity-write-flows.md` —
  front-matter `last_confirmed_phase: 34 → 35`; new "Provenance note"
  subsection cross-referencing ADR-0147 §amendment-1 clause 2.
* `tests/phase_35/__init__.py` NEW (empty).
* `tests/phase_35/test_adr_amendment_sentinels.py` NEW — 5 cases:
  - `test_adr_0147_status_accepted` — parent-tree (skips in container).
  - `test_adr_0147_amendment_1_present` — parent-tree.
  - `test_adr_0147_implementation_phase_35_footer_present` — parent-tree.
  - `test_phase_map_section_35_inline_amendment` — halvim-tree.
  - `test_tracker_last_confirmed_phase_is_35` — halvim-tree.
* `confirmation_docs/PHASE_35_DESIGN_LOG.md` NEW (this file).
* `confirmation_docs/PHASE_35_NEXT_CHAT_PROMPT.md` NEW — Phase 36 R0
  chat-prompt seed.

**NOT shipped at Phase 35:**

* No source-code changes (zero new modules; zero edits to
  `mindsos_*` packages).
* No version bump. `[mindsos]` manifest `version` stays
  `0.0.0+phase34`; pyproject + `__init__.py` literals unchanged; no
  docker-compose image-tag bump. Phase 14a + 15b precedent.
* No git tag. Phase 14a + 15b + 23 precedent.
* No `mindsos confirm-phase --phase 35` invocation. No
  `PHASE_35_CONFIRMED.md`. No `notes-phase-35.md`. Design-only phases
  do not run `confirm-phase`.
* No export-slate sentinel function rename. Phase 33's
  `test_phase_34_export_count_is_110` stays under that name; the
  export count literal (110) is unchanged at Phase 35.

## 4. ADR-0147 §amendment-1 locked text (R3 PB-A3 + R4 PB-A4)

(Shipped form; cross-referenced from R2 PB-ε, R3 PB-A3, R4 PB-A4.)

> ## §amendment-1 (Phase 35 ship; halvim, 2026-05-27 — flip Proposed → Accepted)
>
> ADR-0147 Status flipped Proposed → Accepted at Phase 35. Three
> clauses close the §Acceptance gate and lock the per-flow rule going
> forward.
>
> **Clause 1 — §Acceptance criterion (a) clarified, NOT rewritten.**
> Per the §Implementation Phase 33 + 34 footers' existing
> "anticipatory" characterization, the 2 shipped capacities
> (`capacity:consolidate:mm` + `capacity:trace:problem`) **shipped
> through the `KLWriteHandle` contract surface** (`writeable() →
> mint_iri() → write_and_validate()`) and exercise the contract
> end-to-end. That is the contract-viability evidence §Acceptance
> criterion (a) was gating on. The anticipatory framing is hereby
> PROMOTED from descriptive §Implementation footer caveat to binding
> §Accept-satisfying evidence: "built per-flow and shipped" reads as
> "shipped through the contract surface", and anticipatory + per-flow
> both satisfy (a). Criteria (b) (tracker page populated) and (c) (KL
> deprecation warnings) remain satisfied per the §Implementation
> Phase 33 footer.
>
> **Clause 2 — Anticipatory carve-out (Phase 33+34 capacities).**
> `capacity:consolidate:mm` and `capacity:trace:problem` are explicitly
> classed as **anticipatory**. Their tracker rows stay `wired` (no
> new legend state); the tracker page's "Provenance note" subsection
> cross-references this clause. This is a one-time exception.
>
> **Clause 3 — Per-flow discipline strict going forward.** All future
> L3 write capacities (4 currently `deferred` rows + any new category)
> ship **only after their consuming L4 flow closes design**. The
> §Decision wording remains binding; no anticipatory builds are
> permitted post-Phase 35.

## 5. ADR-0147 §Implementation (Phase 35) footer (R4 PB-B4)

> ## §Implementation (Phase 35 — Accepted; halvim, 2026-05-27)
>
> ADR-0147 Status flipped Proposed → Accepted at Phase 35.
> §amendment-1 clauses 1-3 close §Acceptance criterion (a) via the
> "shipped-through-contract-surface" reading. Per-flow build remains
> strict for the 4 deferred capacities; tracker page is canonical
> "where's the full list" source.
>
> Phase 35 is **design-only**: zero source changes, zero new write
> capacities, zero new exports. ADR + PHASE_MAP §35 inline-amendment
> + tracker note + sentinel tests are the entire ship surface.
>
> Cross-phase note: Phase 36 (ADR-0139, validator home) does NOT
> re-open ADR-0147; semantic validators integrate into existing
> shipped capacities' bodies + `write_and_validate` per ADR-0139
> §Decision, under the per-flow discipline locked here.

## 6. Sentinel test file design (R3 PB-E3 + R4 PB-E4)

File: `halvim_mindsos/tests/phase_35/test_adr_amendment_sentinels.py`.
Generic name matches Phase 15b precedent; later phases can extend
this file with their amendments rather than fragmenting per-ADR.

The file follows the Phase 15b `_skip_if_adr_dir_missing` pattern:
parent-tree ADR sentinels skip when the parent path is unreachable
(in-container runs); halvim-tree sentinels (PHASE_MAP + tracker) run
everywhere.

**Test inventory (5 cases):**

| # | Test | Tree | Docker skip? |
|---|---|---|---|
| 1 | `test_adr_0147_status_accepted` | parent | yes |
| 2 | `test_adr_0147_amendment_1_present` | parent | yes |
| 3 | `test_adr_0147_implementation_phase_35_footer_present` | parent | yes |
| 4 | `test_phase_map_section_35_inline_amendment` | halvim | no |
| 5 | `test_tracker_last_confirmed_phase_is_35` | halvim | no |

Phase 34 baseline = 3340 / 49. Expected Phase 35 baseline: **~3342 /
~52** (2 halvim-tree cases pass cumulative; 3 parent-tree cases skip
in container under Model C). Confirmed at sandbox run pre-ship.

The chain comment header extends `14a → 15a → 15b → 35` per R3 PB-B3.

## 7. Ship metadata (R3 PB-C3 — placeholders; tester fills at squash-merge)

* **git_sha (post-squash-merge):** 36d9125
* **PR number:** #45 (open against `main`).
* **Squash-merge date:** 2026-05-27 (replaces all `2026-05-27`
  placeholders in ADR-0147 §amendment-1 + §Implementation footer +
  PHASE_MAP §35 inline-amendment + this DESIGN_LOG).
* **Branch:** `phase-35` (branch off `main` at HEAD = `180460d`
  Phase 34 squash per R3 PB-I3).
* **Test summary (sandbox pre-PR):** N/A — expected
  `tests/phase_35/` → 2 passed / 3 skipped (no docker run needed for
  design-only ship; cumulative confirmed at next code-shipping phase).
* **Image build hash:** N/A (no image rebuild; Phase 34 image
  unchanged at `mindsos:phase34-*`).
* **falkordb_version:** N/A (no compose run).

## 8. Carry-forwards to Phase 36 (PB-θ + R3 PB-F3)

Phase 36 (ADR-0139, hybrid invariant home — L1 structural / KL
semantic) is the next phase. Phase 35 design-only ship does **NOT**
pre-position Phase 36 (per R1 PB-6 — no signature pre-positioning on
`write_and_validate`). Phase 36's load-bearing open question is the
**validator composition contract**: how does `write_and_validate`
integrate the new validator surface, with what scope routing?

**Carry-forwards seeded for Phase 36 R0:**

1. `mindsos_knowledge/validators.py` is NET-NEW at Phase 36
   (ADR-0139 §Decision §Semantic-invariants).
2. `KLWriteHandle.validate_node(...)` + `KLWriteHandle.validate_xref(...)`
   stubs still raise `WriteHandleNotWiredError` post-Phase 34; Phase
   36 wires bodies.
3. `KLWriteHandle.write_and_validate(...)` extension: how validators
   compose. PHASE_MAP §36 features line says "validators run with
   scope structural / semantic / both" — no `scope` kwarg exists on
   `write_and_validate` today; Phase 36 owns whether to add one
   (Option A) or compose externally in capacity bodies (Option B per
   ADR-0139 §Capacity-contract sketch) or hybrid (Option C). R4 PB-D4
   surfaces this as Phase 36 R0 PB-1.
4. ADR-0146 §amendment-1 clause 1 (failure modes return PTR vs raise)
   stays open per Phase 34 carry-forward.
5. Tracker page `last_confirmed_phase` bumps 35 → 36 at Phase 36 ship.
6. Per-flow discipline (ADR-0147 §am-1 clause 3) applies to Phase 36's
   validator integration: validators wire only where shipped capacities
   need them; do NOT pre-emptively populate validators for the 4
   deferred capacities' roles.

**NOT carried forward to Phase 36:** new write capacity declarations,
new IRI builder registry entries, new `mindsos_capacity/builtins/`
modules. All 4 deferred capacities continue waiting for their L4
flows.

## 9. Observed quirks / process notes

- Phase 35 R0 spent significant chat surface on the load-bearing open
  question (PHASE_MAP §35 features-line wording vs shipped reality).
  Anyone reading this DESIGN_LOG should note: features-line wording
  in PHASE_MAP is **not** authoritative once shipped reality diverges
  — ADR §Implementation footers + this DESIGN_LOG carry the load.
- R1 PB-A ("rewrite criterion (a) explicitly") was reversed at R2
  PB-β. The lesson: when an ADR's §Accept criterion appears to need
  rewriting, prefer clarifying via §amendment-1 over editing the
  §Accept clause text. Reading "the gate text was edited" reads worse
  in retrospect than "the criterion was clarified."
- R2 PB-α (design-only phases ship no CONFIRMED.md) was the
  load-bearing R2 correction. R0+R1 listed CONFIRMED.md + notes file
  + tag for ~3 rounds before this was found. Future design-only
  phases: load the Phase 14a + Phase 15b pattern early in R0.
- R3 PB-F3 (PHASE_35_NEXT_CHAT_PROMPT.md) was the load-bearing R3
  miss. Design-only phases still seed the next-phase prompt; this is
  not optional.
- R4 hit saturation. Re-litigation past R4 yielded only content
  drafting (amendment date placeholders, assertion-anchor strings,
  DESIGN_LOG section list). The saturation signal: when the meta-PB
  ("nothing substantive remains") becomes the load-bearing pushback.

## 10. Memory edit at ship

Write `[[project-mindsos-phase-35]]` index entry per Phase 33+34
precedent. Highlights to capture:

* Phase 35 design-only ship; squash sha (TBD); no tag; no version bump.
* ADR-0147 flipped Proposed → Accepted; §amendment-1 with 3 clauses
  (criterion (a) clarified via contract-surface reading; anticipatory
  carve-out for Phase 33+34 capacities; per-flow strict going forward).
* Test surface: 1 file / 5 cases; chain extends 14a→15a→15b→35.
* Phase 14a + 15b design-only pattern re-confirmed: no CONFIRMED.md,
  no notes file, no tag, no version bump, no `confirm-phase`
  invocation.
* DESIGN_LOG.md is the ship artifact; NEXT_CHAT_PROMPT.md seeds Phase
  36 R0.
* R2 PB-α + R3 PB-F3 = load-bearing corrections (CONFIRMED.md
  precedent + NEXT_CHAT_PROMPT.md missed in R0-R2).

Update `MEMORY.md` index entry per the 1-line-under-200-chars
convention.
