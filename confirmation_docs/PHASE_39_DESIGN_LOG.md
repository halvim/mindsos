# Phase 39 — Design Log

> Captured 2026-06-02. Records the design pushbacks across 4 rounds
> (R0 → R1 → R2 → R3) that locked the design pass for Phase 39 (L2
> `memories` → `episodic_memories` atomic rename + L2-35 alignment
> reconciliation + 2 ADR amendments + 1 new ADR-0146 amendment forced by
> two-NodeType dispatch). Future amendments to ADR-0044 / ADR-0150 /
> ADR-0146 — or the Phase 43 schema-v2 ship that inherits the renamed
> role — should consult this file for rationale.
>
> **Saturation:** three consecutive reversal-free rounds (R1, R2, R3
> each surfaced new decisions without undoing prior picks). HANDOFF §9
> criterion satisfied.

---

## 0. Scope at chat-open

POST_PHASE_38_PHASE_MAP §4 Phase 39 row + Phase 39 next-chat-prompt
(authored by Chat C plan-authoring closure 2026-06-02). Architectural
direction settled by:

- L2_CHAT_DECISIONS D-L2-1 (alignment canonical form `alignment:<a>:<b>`).
- L2_CHAT_DECISIONS D-L2-16 (atomic-hard-rename rationale; no alias).
- L2_CHAT_DECISIONS D-L2-17 (`episodic_memories` schema v1 — Episode +
  Memory entry types + `memory_contains_episode` IntergraphEdge).
- L2_CHAT_DECISIONS D-L2-25 (ADR-0044 §am-3 specification).
- L2_CHAT_DECISIONS D-L2-26 + Chat C IL-3 refinement (ADR-0150
  §amendment-4 split: §am-4 rename row at Phase 39; §am-5 4-new-rows at
  Phase 43).

This chat re-litigated only impl-shape decisions (registry shape,
test-suite filenames, migration-script form, sentinel-anchor scope,
ADR text surgery style). L2 architectural picks were not reopened.

---

## 1. Rounds + load-bearing decisions

### R0 — architectural pushback slate

**Strongest concerns surfaced:**

1. **A1 prereq (`release.yml` retention amendment) had not landed.**
   Per POST_PHASE_38 §1 + Phase 39 row Depends-on, `phase-39` cannot
   branch off main until Stream A item A1 lands. **Pick: route to
   Stream A first.** Non-negotiable.

2. **`consolidate.py` semantic change disguised as rename.** Phase 33
   shipped `consolidate:mm` writes `type_="Memory"` with `memory_id`.
   Per D-L2-17, consolidation produces Episodes (per-task entries),
   not Memory composites. Phase 39 row framed this as "update to new
   Episode entry shape" — that's a contract change to a shipped
   capacity, plus Phase 33 test contract churn.
   **Pick: defer the semantic retarget to Phase 43.** Phase 39's
   `consolidate.py` touch is identifier-surface only (ROLE_MEMORIES →
   ROLE_EPISODIC_MEMORIES import rename; `type_="Memory"` stays).
   Phase 33 tests get string-rename only (no contract edits). Triple-
   touch (Phase 39/42/48) collapses to double-touch (42/48).

3. **Phase 39 scope is bigger than "atomic rename" billing.** Bundle:
   rename + Episode/Memory schema content + alignment fix + 2 ADR
   amendments + capacity-body change + migration script. Settled by
   PB-3 + PB-7 + PB-8 picks below.

**ADR-0150 §am-4 surgery (PB-5).** On-disk §am-4 (L2 chat closure
2026-06-01) bundles rename + 4-new-rows. Per IL-3 split, Phase 39
narrows §am-4 to rename-only; Phase 43 ships §am-5 with 4-new-rows.
**Pick: option (a) verbatim overwrite §am-4 to rename-only.** Git log
is the audit trail; pre-ship in-place edits are legitimate house style
(§am-4 has not yet shipped under any `phase-NN-confirmed` tag).

**Audit constant absorption (PB-6) — moot.** Probe:
`EVT_READ_OTHER_LOCAL_MEMORY` does not exist in `mindsos_server/audit.py`.
Nothing to rename. All episode-audit work ships Phase 44 per Chat C
plan unchanged. **Pick: delete from R0 slate.**

**Migration script (PB-8).** POST_PHASE_38 default = "trivial Python
script + idempotence test." Reaching for `mindsos doctor --self-test`
extension was overreach (doctor infra is workflow/lockfile parity).
**Pick: `tools/check_rename_state.py`** — ~20 LOC standalone Falkor
detector; exits 0 on clean state, 1 + stderr wipe-and-rebootstrap
instructions on pre-rename rows found. Honest about being a detector,
not a migrator.

**Other R0 picks:**

- **PB-7** rename `docs/usage/knowledge/memories.md` →
  `episodic-memories.md` + stub + forward-ref to Phase 48 (L5 docs
  land there).
- **PB-9** ADR-0044 §am-3 + ADR-0150 §am-4 are already on disk
  (authored at L2 chat closure 2026-06-01). Phase 39's R0 reading-list
  reads on-disk text first — verify §am-3, narrow §am-4. Not "draft."
- **PB-10** Phase 35 sentinel chain template handles two amendments;
  Phase 39 sentinel anchors three (ADR-0044 §am-3 + ADR-0150 §am-4 +
  ADR-0146 §am-N).

### R1 — impl-locks + cascading sub-decisions

**PB-N1 (`_IRI_BUILDERS` shape) — load-bearing impl-shape decision.**
Current registry `Dict[role, minter]` cannot dispatch two minters
under `ROLE_EPISODIC_MEMORIES`. Three options weighed:

- **(a) `Dict[(role, NodeType), minter]`** — chosen by user.
- (b) Single dispatcher with kind-as-content-kwarg.
- (c) Defer Memory-composite minter to Phase 48.

**Pick: (a) tuple-key registry.** Clean; future-proofs multi-NodeType
roles. Forces `KLWriteHandle.mint_iri` signature change to
`mint_iri(self, type_: str, **content) -> str` and ADR-0146 §am-N
ratifying the new shape.

**PB-N3 (key shape) — NodeType name vs IRI-body kind.**

- **(a1) IRI-body kind** (lowercase: "episode", "memory") — matches
  `_KINDS_PER_ROLE`.
- **(a2) NodeType name** (capitalized: "Episode", "Memory") — matches
  `write_and_validate(type_=...)`.

**Pick: (a2) NodeType name.** Zero caller-side translation;
`consolidate:mm` `type_="Memory"` flows through unchanged post-rename.
NodeType-name coupling is theoretical — every shipped role has 1:1
NodeType↔IRI-kind mapping today.

**PB-N4 (ADR amendment scope) — ADR-0146 alone, or also ADR-0143.**
**Pick: (a) ADR-0146 §am-N only.** Registry shape lives in ADR-0146's
domain; ADR-0143's handle pattern unchanged. One-line cross-reference
added to ADR-0143.

**PB-R1-A (USED_CAPACITY / PART_OF_PIPELINE EdgeTypes on old Memory
NodeType) — keep, move, or drop.**
**Pick: (c) Drop both at Phase 39.** Phase 13 single-Memory semantics
superseded by Chat B Episode + Memory-composite. Vestigial edges on a
composite are honest schema rot. Phase 13
`test_upper_layer_schemas.py` assertions deleted. Phase 43 may re-add
on Episode atomically with full D-L2-17 ship.

**PB-R1-B (`MEMORY_PROPS` advisory frozenset) — keep, restructure, or
drop.**
**Pick: (c) Drop both property frozensets at Phase 39; ship NodeType
skeletons only.** Properties land at Phase 43 alongside
CONTENT_FIELDS / METADATA_FIELDS / mutation_discipline apparatus.
`validate_node` advisory check passes (non-strict). Phase 13
`test_advisory_property_constants.py` assertions deleted.

**PB-R1-C (ADR-0146 §am-N text scope) — narrow vs broad.**
**Pick: (a) Narrow.** Amendment only ratifies registry-shape change +
mint_iri signature. Per-flow build discipline (ADR-0146 §am-1
clauses 4+5) unchanged; not reopened.

### R2 — concrete text draft

**PB-R2-A (ADR-0146 §am-N date header).**
**Pick: (a) placeholder `Phase 39 ship — 2026-06-XX`.** Tester edits
at `mindsos confirm-phase` time. Matches existing pre-ship ADR draft
convention.

**PB-R2-B (ADR-0150 §am-4 "Explicitly NOT added" exclusion list —
keep in §am-4 or migrate to §am-5).**
**Pick: (b) Migrate all to §am-5.** Exclusions are forward-looking
("considered and didn't add") which belongs with the role-addition
event (§am-5), not the rename event (§am-4).

**PB-R2-C (ADR-0044 §am-3 cross-reference to ADR-0146 §am-N).**
**Pick: (a) Add one-line cross-ref.** "Multi-NodeType dispatch
ratified at ADR-0146 §amendment-N." Helps future readers connect the
rename event to the contract change it forced.

**PB-R2-D (sentinel for schema-shape drops — separate test file).**
**Pick: (b) Separate `tests/phase_39/test_schema_shape.py`** —
positively asserts Episode + Memory NodeTypes-only shape (no EDGE_*
exports; no `MEMORY_PROPS`). Catches accidental re-introduction at
Phase 43.

**PB-R2-E (`check_rename_state.py` exact Cypher).**
**Pick: (b) Defer Cypher body to impl R0.** Contract locked (exit 0
clean / exit 1 + stderr on pre-rename rows; idempotent). Exact query
picked by impl after probing Phase 26a Falkor IRI-storage templates.

**PB-R2-F (ADR-0150 §am-4 surgery style — verbatim overwrite vs
strikethrough).**
**Pick: (a) Verbatim overwrite.** Git log is the audit trail. §am-4
has not shipped under any `phase-NN-confirmed` tag. Strikethrough
leaves dead text in the ADR forever.

### R3 — confirmation pass + impl-surface enumeration

**PB-R3-A (`write_handle.py` impl surface bigger than mechanical
rename).** Lines 170-185 (mint_iri body + error message) + module-
level docstrings (lines 21/26/42/155/259) + lookup logic (176/181)
all encode the old `Dict[str, Callable]` shape. ~15-line edit on
shipped surface.
**Pick: (a) Bundle into Phase 39 atomically.** No isolated consumer
of new shape; bundling with rename is correct.

**PB-R3-B (Phase 35 sentinel SKIP logic — inherit or strip).**
**Pick: (a) Strip SKIP entirely.** Model C dead post-housekeeping
(HANDOFF §7.2). Phase 39's sentinel resolves
`_REPO_ROOT / "docs" / "decisions" / "adr"` directly via
`assert _ADR_DIR.exists()` precondition.

**PB-R3-C (test function names containing "memories" / "memory_iri").**
**Pick: (a) Rename atomically.** PB-1 pass criterion is grep returns
zero hits; function names are searchable surface. D-L2-16's atomic-
rename principle extends to identifier-bearing function names.

**PB-R3-D (test file rewrite enumeration).** No pushback. Confirmed
~24 test files touched across Phases 12, 13, 14, 33, 34, 36.

**PB-R3-E (Stream A A7 `promotion-bridge.md` interaction with
Phase 39).** No interaction. A7 stays independent in Stream A.

---

## 2. Locked impl shape

**Registry + dispatch:**

- `_IRI_BUILDERS: dict[tuple[str, str], Callable[[str, dict], str]]`
  keyed `(role, NodeType_name)`.
- `KLWriteHandle.mint_iri(self, type_: str, **content: Any) -> str`.
  Lookup: `_IRI_BUILDERS[(self.role, type_)]`.
- `KLWriteHandle.write_and_validate` signature unchanged; passes
  `type_` through.
- Registry entries post-rename:
  - `(ROLE_EPISODIC_MEMORIES, "Episode") → _mint_episode`
  - `(ROLE_EPISODIC_MEMORIES, "Memory") → _mint_memory_composite`
  - `(ROLE_PROBLEM_TRACE, "ProblemTraceEntry") → _mint_problem_trace`

**IRI builders:**

- `episode_iri(version, user_id, episode_id) ->
  "episodic-memories-{v}:episode:{u}:{e}"`. Inherits `_USER_ID_RE`
  validation (ADR-0044 §am-1 unchanged).
- `memory_composite_iri(version, user_id, memory_id) ->
  "episodic-memories-{v}:memory:{u}:{m}"`. Same `_USER_ID_RE`.
- `memory_iri` retired.

**Identifier surfaces:**

- `ROLE_MEMORIES` → `ROLE_EPISODIC_MEMORIES`.
- `_PREFIXES`: `("memories-", ROLE_MEMORIES)` →
  `("episodic-memories-", ROLE_EPISODIC_MEMORIES)`.
- `_KINDS_PER_ROLE[ROLE_EPISODIC_MEMORIES] =
  frozenset({"episode", "memory"})`.
- `alignment_role(a, b)` body fixed to `f"alignment:{a}:{b}"`;
  docstrings at lines 297 + 353 rewritten.

**Schema (`mindsos_knowledge/schemas/episodic_memories.py`):**

- File renamed from `schemas/memories.py`.
- NodeTypes: `Episode`, `Memory`.
- EdgeTypes: NONE (USED_CAPACITY + PART_OF_PIPELINE dropped).
- Advisory property frozensets: NONE (MEMORY_PROPS dropped).
- IntergraphEdge `memory_contains_episode` deferred to Phase 43.
- `mutation_discipline` + CONTENT_FIELDS + METADATA_FIELDS apparatus
  deferred to Phase 43 (per ADR-0153 ship).

**`consolidate.py` (Phase 33 capacity body) touch:**

- Import: `ROLE_MEMORIES` → `ROLE_EPISODIC_MEMORIES`.
- `kl.writeable(role=ROLE_EPISODIC_MEMORIES, ...)` (was
  `ROLE_MEMORIES`).
- `type_="Memory"` unchanged. Continues writing Memory-composite-shape
  IRIs (semantically wrong per D-L2-17 but mechanically valid;
  retargets at Phase 43).

**ADR amendments:**

- ADR-0044 §amendment-3 — already on disk (L2 chat 2026-06-01).
  Phase 39 verifies + adds one-line cross-ref to ADR-0146 §am-N.
- ADR-0150 §amendment-4 — narrowed in place to rename row only;
  4-new-rows + exclusions list migrate to §am-5 (Phase 43).
- ADR-0146 §amendment-N — new; ratifies `Dict[(role, NodeType),
  minter]` shape + `mint_iri(type_, **content)` signature. ~5
  paragraphs. ADR-0143 gets one-line cross-ref (no §amendment).

**Tool:**

- `tools/check_rename_state.py` — ~20 LOC Falkor probe. Contract:
  exit 0 if zero pre-rename nodes; exit 1 + stderr instructions if
  found. Idempotent. Cypher body picked at impl R0 after probing
  Phase 26a templates.

**Docs:**

- `docs/usage/knowledge/memories.md` → `episodic-memories.md`. Stub
  content + frontmatter + forward-ref to Phase 48 (L5 docs ship there).

**Tests — new Phase 39 suite (7 files):**

- `tests/phase_39/__init__.py`
- `tests/phase_39/test_rename_atomic.py` — grep zero hits on retired
  names; `ROLE_EPISODIC_MEMORIES` importable; `ROLE_MEMORIES` raises.
- `tests/phase_39/test_alignment_canonical.py` — sort invariance;
  colon separator; no `<->` substring.
- `tests/phase_39/test_episode_memory_iri_builders.py` — both
  builders; `_USER_ID_RE` rejection; parse round-trip.
- `tests/phase_39/test_iri_builders_registry_shape.py` — tuple-key
  shape; 3 entries; mint_iri signature.
- `tests/phase_39/test_schema_shape.py` — Episode + Memory NodeTypes
  only; no EDGE_* exports; no `MEMORY_PROPS`.
- `tests/phase_39/test_check_rename_state_script.py` — exit codes;
  idempotence.
- `tests/phase_39/test_adr_amendment_sentinels.py` — chain root (PB-6);
  anchors ADR-0044 §am-3 + ADR-0150 §am-4 (narrowed) + ADR-0146 §am-N.
  No SKIP logic (PB-R3-B).

**Manifest:**

- `mindsos_cli/manifest.toml`: `phase = "38"` → `"39"`;
  `version = "0.0.0+phase38"` → `"0.0.0+phase39"`.

---

## 3. File touch surface

Net ~45-50 file touches. Breakdown:

| Surface | Count |
|---|---|
| Source files (rename + adapters + registry + write_handle.py) | ~12 |
| Test files updated (Phases 12/13/14/33/34/36) | ~24 |
| ADR files edited | 3 (ADR-0044 + ADR-0150 + ADR-0146; one-line in ADR-0143) |
| New tool | 1 (`tools/check_rename_state.py`) |
| Docs rename | 1 (`memories.md` → `episodic-memories.md`) |
| New Phase 39 test suite | 7 |
| Manifest | 1 |

Mostly mechanical string rename. Two non-mechanical surfaces:
`_IRI_BUILDERS` shape change (with `write_handle.py` body edits) and
new Episode + Memory NodeTypes in `schemas/episodic_memories.py`.

---

## 4. Pre-Phase-39 prereq

**Stream A item A1** (`release.yml` retention amendment per PB-R)
MUST land on main before `phase-39` branches. Status as of
2026-06-02: **pending.** Open A1 as a maintenance PR first.

---

## 5. Reading-list cascade

**For Phase 40 R0 (Rail B X1).** Per PB-Z, Phase 40 reads Phase 39
diff for `identifiers.py` collision check. Phase 40 adds 9 REALM_*
constants + frozenset; Phase 39 edits role + IRI builder + alignment
lines. Literal-line overlap probability near zero; rebase off main
after Phase 39 lands.

**For Phase 42 R0 (Rail B X3).** Phase 42 retargets `context["kl"]`
→ `context.kl` in `consolidate.py` (Phase 39 + Phase 42 touch). Phase
42 R0 reads Phase 39 diff.

**For Phase 43 R0 (Rail A schema-v2).** Phase 43 inherits the renamed
role; ships D-L2-17 fully (Episode + Memory properties + edge type +
mutation_discipline + CONTENT_FIELDS/METADATA_FIELDS). Phase 43 also
ships ADR-0150 §amendment-5 (4 new role-graphs + Phase 39's "explicitly
NOT added" exclusion list migrated here per PB-R2-B). Phase 43 R0 reads
Phase 39 diff.

**For Phase 48 R0 (L5 v1).** Phase 48 retargets `consolidate:mm` to
write Episodes (the semantic change deferred from Phase 39 per PB-3).
Phase 48 R0 reads Phase 39 + Phase 43 diffs on `consolidate.py`.

---

## 6. Outputs expected at chat close (impl side)

- `phase-39` branch off `origin/main` (after A1 lands).
- Squash-merged PR.
- `phase-39-confirmed` tag from main-tip.
- `confirmation_docs/PHASE_39_CONFIRMED.md` — ship metadata authored
  by tester via `mindsos confirm-phase --phase 39 --notes-file
  notes-phase-39.md`.
- This file (`PHASE_39_DESIGN_LOG.md`) updated with any impl-time
  amendments per Phase 38 R6 precedent.
- ADR-0044 §amendment-3 verified + cross-ref added.
- ADR-0150 §amendment-4 narrowed verbatim.
- ADR-0146 §amendment-N drafted at impl R0 + ratified.
- All shipped code per §2 above.
- `tools/check_rename_state.py` with impl-R0-picked Cypher.
- `tests/phase_39/` 7-file test suite.
- HANDOFF.md §1 line bump + §2.2 update reflecting rename completion
  + §3.1.7 status update.
- `docs/_workbench/STREAM_A_BACKLOG.md` — A1 closed (landed pre-Phase
  39); A6 absorbed if applicable.
- `docs/future_work/L2_FUTURE_WORK.md` §11 — L2-34 + L2-35 marked
  **CLOSED — shipped Phase 39**.
- `confirmation_docs/PHASE_43_NEXT_CHAT_PROMPT.md` — seed for the
  next Rail A chat (drafted at this design-pass close per Phase 25→26
  precedent; lives alongside this design log).

---

## 7. Saturation tracking

- **R0:** 10 PBs surfaced + picks (architectural).
- **R1:** 5 sub-PBs at concretization + picks (impl-shape; no R0
  reversals).
- **R2:** 6 PBs at text-draft + picks (no R0 or R1 reversals).
- **R3:** 5 findings at enumeration + picks (no prior reversals).

**Three consecutive reversal-free rounds (R1, R2, R3).** Chat C
saturation criterion satisfied (HANDOFF §9). Phase 39 design pass is
ship-ready.

---

## 8. Process notes inherited from Phase 25 / Phase 35 / Phase 38

- **Probe-first** (Phase 38 R5-PB-I). R0 probes caught the moot audit
  constant (PB-6) and the `_IRI_BUILDERS` single-minter limitation
  (PB-N1) — neither was in the chat prompt slate. Continue.
- **Reading-list discipline (Chat C PB-Z)** worked at R0 — caught the
  on-disk ADR-0150 §am-4 already containing rename + 4-new-rows
  (informed PB-5 surgery strategy).
- **Ship-shape default DROPPED** (Chat C IL-8). Phase 39 is
  unambiguously code-shipping; no docs-only PB raised. Lesson
  preserved.
- **Tester two-machine workflow** unchanged: Mac for git + edits + PR
  + tag; Linux for `docker compose run --rm mindsos-test pytest
  tests/` + `mindsos confirm-phase`.

---

*Original closure 2026-06-02 — design pass. Impl-time amendments
appended at §9 below per Phase 38 R6 precedent.*

---

## 9. Impl-time amendments (impl chat — 2026-06-02 ship)

The impl + tester chat ran R1/R2 rounds beyond the design log's
saturation. Eight non-architectural impl-shape picks landed; eight
gate-driven follow-up commits + a CONFIRMED.md ordering anomaly are
recorded here for future-chat reference.

### 9.1 R1 impl-shape picks

- **PB-R1-A (docs scope phasing).** Active docs (`docs/concepts/` +
  `docs/api/` + `docs/usage/` + `docs/dev/internals/` +
  `docs/decisions/summary/`) advanced atomically with code.
  Non-amend-target ADRs containing stale `ROLE_MEMORIES` / `memory_iri`
  example code (ADR-0045, ADR-0139, ADR-0143, ADR-0146 main body
  outside §am-3, ADR-0147, ADR-0154 example IRI form) **deferred to
  Phase 43** — Phase 43 ships adjacent ADR-0152/0153 amendments and
  naturally absorbs the stale-example cleanup. ADR-0044 filename
  cross-refs unchanged.
- **PB-R1-B (ADR-0044 filename frozen).** Filename
  `0044-memories-move-to-local-per-user.md` stays — ADR slugs are
  audit anchors; the §am-3 retitle carries the rename in content.
  14+ cross-ref filename pins across `docs/decisions/adr/*.md` and
  `docs/concepts/*.md` preserved.
- **PB-R1-C (sentinel_paths.py).** Test-file rename count corrected
  from design-log §3's "~24" to ~25 (`tests/_shared/sentinel_paths.py`
  was missed; landed in commit 5).
- **PB-R1-D (phase-48-retarget NOTE comment).** Inline
  `NOTE(phase-48-retarget)` comment added at
  `mindsos_capacity/builtins/consolidate.py` validate_node +
  write_and_validate call site flagging the two-phase semantic tech
  debt (Phase 39 keeps `type_="Memory"` writing per-task entries;
  Phase 48 retargets to `Episode` per D-L2-17 + Chat B D-B47). Module
  docstring also flags the interim state.
- **PB-R1-E (6-commit grouping).** `phase-39` branch ship grouped as:
  (1) ADR amendments; (2) identifier core; (3) schema rename +
  re-exports; (4) downstream callsites + first Linux gate;
  (5) tests + tool + manifest + full Linux gate; (6) active docs +
  project status. Mid-granularity matches the two failure modes that
  needed bisecting; finer splits would have created non-buildable
  intermediate commits which defeat per-commit gating. Squash-merged
  on ship.
- **PB-R1-F (POST_PHASE_38_PHASE_MAP + HANDOFF dual SHIPPED flip).**
  Both `confirmation_docs/POST_PHASE_38_PHASE_MAP.md` Phase 39 row
  Status and `HANDOFF.md` §1 line + §3.1.7/8 status block flipped
  to SHIPPED at commit 6. Drift between phase-map (rail-progress
  board) and HANDOFF (human-readable status) is a known anti-pattern.

### 9.2 R2 ADR text-shape picks

- **PB-R2-1/2/3 (ADR-0146 §am-3 header + title + placement).**
  Header style `## §amendment-N — <title> (halvim, <date>)` matches
  ADR-0146 local convention (not the level-3 `### amendment-N
  (<tag>)` of ADR-0044/0150). Title `Phase 39 multi-NodeType dispatch
  — tuple-key registry + mint_iri signature` names change driver +
  shipped surfaces. Appended at end of file after §am-2.
- **PB-R2-4 (ADR-0150 §am-4 surgery).** 8-block surgery (trigger
  paragraph rescoped, amended-behavior trimmed, renamed-row table +
  row-meaning + scoped rationale + scoped out-of-scope kept;
  new-rows table + per-role-graph mutation discipline + "Explicitly
  NOT added" exclusion list + escape clause all deleted to migrate to
  §am-5 at Phase 43). Net: ~93 lines → ~32 lines.
- **PB-R2-5 (ADR-0150 §am-4 retitle).**
  `v1 L4-driven role-graph expansion + episodic_memories rename` →
  `episodic_memories rename + Episode/Memory entry-type split`.
- **PB-R2-6 (ADR-0044 §am-3 cross-ref).** Inline parenthetical on
  the `_IRI_BUILDERS` migration-plan bullet (lines 146-147) pointing
  at ADR-0146 §am-3 (single-line edit).
- **PB-R2-7 (ADR-0143 cross-ref).** Added as a line under
  `## Implementation references` (line 121+) pointing at ADR-0146
  §am-3. No §amendment on ADR-0143 (handle pattern unchanged;
  signature evolution = registry-dispatch, not handle-pattern).
- **PB-R2-8 (`check_rename_state.py` Falkor enumeration).**
  `FalkorDB.list_graphs()` + per-graph filter by IRI-prefix Cypher
  match. Tools are explicitly cross-layer (not subject to layer
  isolation) — direct FalkorDB connection via env-var config,
  separate from FalkorClient layer.
- **PB-R2-9/10 (HANDOFF status text + date placeholders).** SHIPPED
  marker on §3.1.8 anchor block; date placeholder `2026-06-XX` in
  pre-ship ADR drafts; ADR-0150 §am-4 authorship date
  `(L2 chat — 2026-06-01)` preserved (surgery is text-shape narrow,
  not a new amendment event).

### 9.3 Gate-driven follow-up commits (5b, 5c)

Linux full gate at end of commit 5 surfaced 30 failures across 6
categories. Two follow-up commits fixed them:

- **Commit 5b** (`ddc2c14`) — 17 files. Per-package `__version__`
  bumps (`mindsos_core` + `mindsos_cli` + `mindsos_capacity` +
  `mindsos_server` + `mindsos_instances` + `mindsos_admin` all
  advanced `0.0.0+phase38` → `0.0.0+phase39`) + `pyproject.toml`
  version + `docker-compose.yml` image tags
  (`mindsos:phase38-prod/test` → `mindsos:phase39-prod/test`) +
  `Dockerfile` test-stage `COPY tools ./tools` (Phase 39 ships the
  first runtime `tools/` script; test-stage previously didn't copy
  the dir; new convention for any future tools shipping). Plus
  `tests/phase_13/test_knowledge_schema_cli.py` (CLI role-string
  surface + fixture rename `memories_bad.json` →
  `episodic_memories_bad.json`); `tests/phase_25/` (2 files; role
  assertion text); `tests/phase_33/` (mint_iri signature + role
  assertion); `tests/phase_34/test_phase_34_export_slate.py` +
  `test_writeable_version_kwarg.py` (version + signature).
- **Commit 5c** (`<sha>`) — 2 files.
  `tests/phase_30/test_phase_30_export_slate.py` +
  `tests/phase_31/test_phase_31_export_slate.py` —
  `test_version_bumped_to_phase_34` literal-version assertions
  advanced. The "phase_34" test name is from the phase-34 sentinel
  flip; the literal value bumps at each subsequent phase per the
  sentinel-flip-at-target-phase convention.

### 9.4 Generic per-phase manifest-bump checklist (carry-forward)

Surfaced at Phase 39 commit 5; documented here for every subsequent
phase. **9 surfaces must advance in lockstep with a manifest phase
bump** (see HANDOFF §9 process notes + POST_PHASE_38_PHASE_MAP §1):

1. `mindsos_cli/manifest.toml` `[mindsos] phase` + `version`.
2-7. `mindsos_core/__init__.py` + `mindsos_cli/__init__.py` +
   `mindsos_capacity/__init__.py` + `mindsos_server/__init__.py` +
   `mindsos_instances/__init__.py` + `mindsos_admin/__init__.py`
   `__version__`.
8. `mindsos_knowledge/__init__.py` `__version__`.
9. `pyproject.toml` `[project] version`.
10. `docker-compose.yml` `image: mindsos:phase{N}-prod` +
   `mindsos:phase{N}-test`.
11. `tests/phase_30/test_phase_30_export_slate.py` +
   `tests/phase_31/test_phase_31_export_slate.py` +
   `tests/phase_34/test_phase_34_export_slate.py`
   `test_version_bumped_to_phase_34` literal assertions (per the
   sentinel-flip-at-target-phase pattern — file name stays at
   `phase_34`; literal value bumps).

Doctor self-test + version-parity tests gate this. Doctor failure at
the cumulative gate is the cleanest detection signal.

### 9.5 Ship closure anomaly (recorded for replay-prevention)

The squash-merge step on Mac was skipped in the first ship attempt;
`mindsos confirm-phase` ran on Linux against a stale `main` that did
not yet contain the Phase 39 squash-merge. Result: origin/main reached
`6c73108` (CONFIRMED.md + tester notes) BEFORE the actual squash-merge
landed. Recovery: restored `phase-39` branch from Mac reflog (tip
`cfe1503`), squash-merged on top of `6c73108`, re-cut
`phase-39-confirmed` tag at the new SHA, force-pushed the tag.

**Final main ordering (semantically backwards but functionally
correct):**

| Commit | Content |
|---|---|
| `7a8bf10` (tag: phase-39-confirmed) | Phase 39 squash-merge — the actual ship |
| `6c73108` | PHASE_39_CONFIRMED.md + notes-phase-39.md |
| `ec16443` (tag: a0-corpus-landed) | A0-5 doc closure |
| `f33db02` | A1 retention rule |

**Future-chat advisory:** ensure the squash-merge to `main` lands +
pushes BEFORE `mindsos confirm-phase` runs. Or run confirm-phase on
Mac with a clean `main` post-squash-merge. The two-machine workflow
makes the temporal coupling subtle.

### 9.6 Phase 43 carry-forwards

Items deferred from Phase 39 that Phase 43's chat must absorb:

- **Stale `ROLE_MEMORIES` / `memory_iri` example code cleanup** in
  ADR-0045 (§Decision body), ADR-0139 (example code block),
  ADR-0143 (Usage skeleton + Constraint), ADR-0146 (main body
  outside §am-3), ADR-0147 (per-flow example), ADR-0154 (example IRI
  `memories-<v>:memory:<u>:<m>` form). Phase 43 ships adjacent
  ADR-0152/0153 amendments and ADR-0150 §am-5 — natural alignment
  for the cleanup pass.
- **Phase 9 manifest-bump checklist** (§9.4 above) inherited by
  every numbered-phase ship.
- **Pre-confirm-phase squash-merge discipline** (§9.5 above).

---

*End of PHASE_39_DESIGN_LOG.md. §1-8 capture the design pass closure
2026-06-02 morning; §9 captures the impl + tester ship pass closure
2026-06-02 end-of-day.*
