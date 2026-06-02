## PHASE 43 — NEXT CHAT PROMPT

> Drafted 2026-06-02 by Phase 39 design-pass closure. Hand to the chat
> that opens Phase 43 — the second Rail A ship in the post-Phase-38 plan.
> Opens **after Phase 39 confirms.**
>
> **⚠ PRE-R0 DESIGN PASS CLOSED 2026-06-02 end-of-day.** §3 below
> (PB-43-1…10 default slate) is SUPERSEDED. The Phase 43 chat now opens
> at **R1 impl-locks**, NOT R0. Primary R0 inputs:
>
> 1. **`confirmation_docs/PHASE_43_R0_PICKS_SEED.md`** — locked picks,
>    drops (C-γ, P1, P-meta, A6 from scope), probe-resolved findings
>    (incl. N4 L2Schema subclass safe; task_patterns.confidence kept;
>    6 disciplines not 5; ADRs 0151/52/53 already Accepted). Replaces
>    PB-43-1…10 defaults.
> 2. **`confirmation_docs/PHASE_43_R0B_DERIVATIONS.md`** — R0b artifacts:
>    `applies_after` edge set (derived from D-L2-19), ADR-0150 §am-5
>    draft text (lift-ready), L2Schema(Schema) subclass sketch (full
>    Python pseudocode + Discipline/StorageMode enums + 14-row
>    transcription table + validator interface + exception).
> 3. **`HANDOFF.md §3.1.9`** — Phase 43 pre-R0 closure block.
>
> **HARD PREREQ:** `confirmation_docs/A0_HOUSEKEEPING_COMMIT_CHECKLIST.md`
> must have landed (4 commits A0-1…A0-4 on `main`) AND Phase 39 must
> have confirmed (`phase-39-confirmed` tag from `main`-tip). See
> `HANDOFF.md §3.1.9` for S9 blocker context.
>
> §1-§2 of this prompt (required reading) and §6 (outputs expected at
> chat close) remain authoritative. §3 (R0 expectations) is superseded
> by the seed + derivations. §4 (out of scope) and §5 (process notes)
> remain authoritative.

You are running the Phase 43 chat: **L2 schema-v2 — 4 new role-graph
schemas (`parameter-staging`, `pending-promotions`, `capacity-gaps`,
`learned-parameters`) + `mutation_discipline` runtime invariant +
`storage_mode` field + 14-step bootstrap topological order via
`applies_after` + ADR-0094 §am-1 (drop `confidence` from
promoted-pipelines) + ADR-0150 §am-5 (4-new-rows + exclusion list
migrated from §am-4) + ADR-0151 / ADR-0152 / ADR-0153 ratification +
finalization of `episodic_memories` schema with Episode/Memory
properties + `memory_contains_episode` IntergraphEdge + L1 `Schema`
field amendment.**

Rail A, slot 2 of 11 in the post-Phase-38 plan.

---

## Before you do anything — required reading, in this order

1. **`HANDOFF.md`** at the root. Canonical entry point. Read §0, §1,
   §2.2 (L2 shipped surfaces — should now reflect Phase 39 closure),
   §3.1.7 (Chat C closure block + Phase 43 row), §6.4 (current
   operating mode), §10 reading-map table — find the "Phase 43 chat"
   row; that row names this file's required reading.

2. **`confirmation_docs/POST_PHASE_38_PHASE_MAP.md`** — §0 (reading
   discipline; PB-Z prior-phase-diffs clause), §1 (settled cross-
   cutting decisions), **§4 Phase 43 row in full** (this is your
   specification — features, modules touched, tests, pass criterion,
   breaking changes, risks).

3. **`confirmation_docs/PHASE_39_DESIGN_LOG.md`** — picks inherited
   from the immediately-preceding Rail A phase, especially:
   - §2 Locked impl shape (the rename surface + new IRI builders +
     registry shape change Phase 43 builds on).
   - §5 Reading-list cascade — names this file as a downstream
     reader of Phase 39's `identifiers.py` + `episodic_memories.py`
     + `consolidate.py` edits.
   - PB-R1-A + PB-R1-B picks (EdgeTypes + property frozensets dropped
     at Phase 39; Phase 43 is the slot to re-add per D-L2-17).
   - PB-R2-B (exclusion list `sense-correlations` + `world-axioms` +
     `training-runs` + `fol-rules` + `fol-ledger` migrated from §am-4
     to §am-5 — this chat ships §am-5; the list lands here).

4. **`confirmation_docs/L2_CHAT_DECISIONS.md`** — full file. Phase 43
   ratifies a substantial fraction of the L2 chat's settled picks.
   Most-load-bearing:
   - **D-L2-3** (`mutation_discipline` field + 5 v1 disciplines).
   - **D-L2-4** (per-field CONTENT_FIELDS / METADATA_FIELDS).
   - **D-L2-5** (reference-stability framing).
   - **D-L2-6** (promoted-pipelines schema v2 partial lock — Phase 43
     finalizes; HAS_STEP shape stays Phase 13 because L1/L3 reframe
     picked bipartite at X3, not hyperedges).
   - **D-L2-7** (`serves_task_types` cache eliminated).
   - **D-L2-10** (task-patterns flat 9-field).
   - **D-L2-11 / D-L2-13 / D-L2-14 / D-L2-15** (the 4 new role-graphs).
   - **D-L2-17** (full episodic_memories schema — Phase 43 adds
     Episode + Memory properties + memory_contains_episode edge that
     Phase 39 deferred per PB-R1-A + PB-R1-B).
   - **D-L2-19** (14-step bootstrap order via `applies_after`).
   - **D-L2-22** (3 storage tiers — ratified at ADR-0151).
   - **D-L2-24** (ADR-0094 §am-1 dropping `confidence`).
   - **D-L2-26 + Chat C IL-3 refinement** (ADR-0150 split into §am-4
     rename at Phase 39 / §am-5 4-new-rows + exclusion list at
     Phase 43 — this chat ships §am-5).

5. **`_workbench/STREAM_A_BACKLOG.md`** — verify A1 (`release.yml`
   retention amendment) landed pre-Phase-39 + is now closed. A6
   (`validate_local_to_global_ref` consumer) MAY surface as Phase 43
   absorption candidate (the 4 new role-graphs need validator
   wiring); probe at R0 before locking.

6. **`confirmation_docs/PHASE_MAP.md` §1** — inherited cross-cutting
   decisions. Phase 43 ships under these unchanged (per-phase
   workflow, two-machine, doctor self-test, branching off main).

7. **ADRs on disk (already drafted at L2 chat closure 2026-06-01):**
   - `docs/decisions/adr/0151-l2-storage-tiers.md` — ratifies
     `storage_mode` field + 3 tiers.
   - `docs/decisions/adr/0152-l2-role-graph-schema-v2.md` — ratifies
     4 new role-graph schemas.
   - `docs/decisions/adr/0153-l2-mutation-discipline.md` — ratifies
     5-discipline framework + L4 startup invariant.
   - `docs/decisions/adr/0094-confidence-pipeline-level.md` — draft
     §am-1 here (drops `confidence` from promoted-pipelines).
   - `docs/decisions/adr/0150-l2-knowledge-lifecycle.md` — §am-5 is
     this chat's draft (4-new-rows + migrated exclusion list per
     Phase 39 PB-R2-B).

8. **`confirmation_docs/PHASE_38_DESIGN_LOG.md` §5** — process notes
   (probe-first; tester ship-shape) inherited.

9. **`confirmation_docs/PHASE_39_CONFIRMED.md`** — ship metadata for
   Phase 39 (when it lands). Confirms baseline state Phase 43
   branches off.

Optional memory entries if you have memory access: `[[project-
mindsos-l2-chat-closure]]`, `[[project-mindsos-chat-c-closure]]`,
`[[project-mindsos-phase-39-design-closure]]` (created at Phase 39
closure 2026-06-02), `[[reference-mindsos-layer-handoffs]]`.

---

## Project rules (re-inherit)

User's standing project instructions apply: skeptical reviewer mode,
terse alternatives + pick format, push back when something is weak,
no filler. Saturation discipline per Chat C: three consecutive
reversal-free rounds = ready-to-ship.

L2 architectural picks (D-L2-3 through D-L2-26) are **settled by L2
chat closure 2026-06-01**. Phase 39 + Chat C IL-3 refinement settled
the rename + amendment split. **Do not re-litigate L2 architecture
or Phase 39 picks.** Re-litigate only Phase 43 impl-shape decisions
(exact `Schema.mutation_discipline` field semantics, exact bootstrap
importer order edge cases, exact CONTENT_FIELDS / METADATA_FIELDS
membership for promoted-pipelines + task-patterns + episodic_memories,
schema-file layout for 4 new role-graphs, migrator form for
promoted-pipelines `confidence` strip).

---

## R0 expectations (your first response shape)

1. **Confirm required-reading consumed** — terse paths list.

2. **Run probes against shipped reality** (post-Phase-39 baseline):

   - `grep -rn "ROLE_MEMORIES\|memory_iri\|memories-" mindsos_*/
     tests/` — verify Phase 39 rename is clean on main. Should return
     zero hits. If non-zero: Phase 39 didn't ship cleanly; surface
     for tester before locking Phase 43 picks.
   - `cat docs/decisions/adr/0150-l2-knowledge-lifecycle.md | grep
     -n "amendment-4\|amendment-5"` — verify §am-4 is narrowed
     (rename-only) and §am-5 slot reserved.
   - `cat docs/decisions/adr/0151-l2-storage-tiers.md | head -30` —
     verify Status (Proposed vs Accepted) before this phase flips.
     Same for ADR-0152 + ADR-0153.
   - `grep -rn "confidence" mindsos_knowledge/schemas/
     promoted_pipelines.py` (if it exists by name) — surface any
     shipped `confidence` field that the migrator strips.
   - `grep -rn "mutation_discipline\|CONTENT_FIELDS\|
     METADATA_FIELDS" mindsos_core/ mindsos_knowledge/` — verify
     these are zero hits pre-Phase-43 (Schema field is net-new).
   - `cat mindsos_knowledge/bootstrap.py | grep -n "applies_after\|
     bootstrap"` — surface the current bootstrap order; Phase 43
     rewrites with topological `applies_after`.
   - `cat manifest.toml | grep "^phase"` — verify
     `[mindsos] phase = "39"` post-Phase-39 baseline before bumping
     to 43.
   - `grep -rn "_IRI_BUILDERS" mindsos_knowledge/identifiers.py
     mindsos_knowledge/write_handle.py` — verify Phase 39's tuple-
     key registry shape shipped; Phase 43's 4 new role-graphs add
     entries here.

3. **Draft Phase 43 R0 pushback slate.** Likely surfaces:

   - **PB-43-1.** Atomicity of the 4 new role-graph schemas — single
     PR (current POST_PHASE_38 default) vs split across 2 PRs (large
     surface). Default = single PR; re-litigate if test-load
     concern.
   - **PB-43-2.** `Schema.mutation_discipline` default value — pick
     `mutable_with_retention` (per D-L2-3 backward-compat) vs
     require-explicit-declaration in strict mode. Phase 13 shipped
     schemas need amendment regardless; explicit-required is
     stricter.
   - **PB-43-3.** Per-field CONTENT_FIELDS / METADATA_FIELDS
     frozenset shape — declare alongside `*_PROPS` constants (per
     D-L2-4 cascade) vs as a structured Schema-level mapping
     (`Dict[NodeType, ContentMetadataLabels]`). Default = alongside
     `*_PROPS` constants; re-litigate if validator surface grows.
   - **PB-43-4.** `applies_after: frozenset[IRI]` field on bootstrap
     importer registration — additive default-empty (per D-L2-19)
     vs require-explicit declaration. Default = additive; re-
     litigate if topological-sort surface grows.
   - **PB-43-5.** Episode + Memory **edge type** — `USED_CAPACITY` +
     `PART_OF_PIPELINE` dropped at Phase 39 (PB-R1-A). Phase 43
     decides: re-add on Episode (per-task entry, semantically
     correct) vs drop permanently (Phase 33 `consolidate:mm`
     re-target at Phase 48 handles via `mm_root_ref` XRef instead).
     Default = drop permanently; surface if Phase 48 chat surfaces
     pressure.
   - **PB-43-6.** `Schema` L1 amendment vs L2-only field — D-L2-3
     puts `mutation_discipline` on `mindsos_core.Schema`. That's an
     L1 amendment (Schema is L1). Alternative: introduce
     `L2Schema(Schema)` subclass in `mindsos_knowledge` and put the
     field there. Default = L1 amendment per D-L2-3; re-litigate
     only if L1 reframe chat surfaces ADR-0017 / ADR-0149 conflict.
   - **PB-43-7.** Ordering vs Phase 40 (Rail B X1) on `identifiers.py`
     — Phase 40 adds 9 REALM_* constants; Phase 43 adds 4 new
     `ROLE_*` constants + IRI builders. Per PB-Z reading-list,
     read Phase 40 ship-diff at branch-creation time.
   - **PB-43-8.** `episodic_memories` Episode + Memory properties +
     `memory_contains_episode` IntergraphEdge — D-L2-17 specifies
     these but Phase 39 deferred to here (PB-R1-A + PB-R1-B picks).
     Phase 43 must ship per D-L2-17 + Chat B D-B47. Confirm scope.
   - **PB-43-9.** `consolidate.py` semantic retarget — Phase 39 left
     `type_="Memory"` for mechanical-rename purity (per Phase 39
     PB-3). D-L2-17 says `consolidate:mm` should produce Episodes.
     Phase 43 decides: retarget here (matches D-L2-17 cleanly), or
     defer to Phase 48 (L5 v1, when MM consolidation write path
     ships and TaskRun composite is live).
     Default per POST_PHASE_38 §4 Phase 48 row = defer to Phase 48
     (consolidate.py triple-touch is Phase 39 → Phase 42 → Phase 48
     per Chat C PB-Z). Confirm.
   - **PB-43-10.** Migrator scope — POST_PHASE_38 says
     `tools/migrate_phase_43_confidence_strip.py`. Per Phase 39
     PB-8 precedent (script became detector), consider:
     real migrator vs no-op stub vs `tools/check_*_state.py`
     detector form. v1 production has no `confidence` Local-Pipeline
     records.

4. **Stop. Wait for re-litigation cue** before drafting R1 impl-locks.

Saturation expectation per Phase 25 + Phase 35 + Phase 38 + Phase 39
precedent: 3-5 R-rounds + impl + tester loop. Reading-list adds the
PB-Z prior-phase-diffs clause; Phase 43 has Phase 39 (Rail A) +
Phase 40 + Phase 41 + Phase 42 (Rail B parallel) as potential prior
diffs depending on DAG execution order.

---

## Out of scope for this chat

- Anything in any other phase's row (Phase 39 closed; Phase 40-42
  separate chats; Phase 44-49 separate chats).
- Re-litigation of L2 architecture (closed at L2 chat 2026-06-01).
- Re-litigation of `episodic_memories` rename (closed at Phase 39).
- Re-litigation of `_IRI_BUILDERS` registry shape (closed at Phase 39
  ADR-0146 §am-N).
- Stream A items (separate maintenance PR track).
- L0 substrate work (Rail C, Phase 44).
- Dream family (Rail D, Phase 45).
- L4 substrate (Phase 46 convergence).
- WSD installation chat scope (`world-axioms`, lexicon empirical-layer
  importers, predicate.* capacities).
- FOL installation chat scope (`training-runs`, parameter_set_iri
  format encoding).
- `HAS_STEP` shape re-litigation — D-L2-6 ship at Phase 43 carries
  Phase 13 form because L1/L3 reframe (closed 2026-06-01) picked
  bipartite at X3 (Phase 42), not capacities-as-hyperedges. Locked.

---

## Outputs expected at chat close

Per `PHASE_MAP.md §1` per-phase workflow (inherited unchanged):

- `phase-43` branch off main → squash-merged PR → `phase-43-confirmed`
  tag from main-tip.
- `confirmation_docs/PHASE_43_CONFIRMED.md` — ship metadata authored
  by tester via `mindsos confirm-phase --phase 43 --notes-file
  notes-phase-43.md`.
- `confirmation_docs/PHASE_43_DESIGN_LOG.md` — design-pass picks per
  round, following Phase 39 template (or Phase 25 if you want longer
  prose).
- `confirmation_docs/notes/notes-phase-43.md` — tester notes.
- ADR-0151 + ADR-0152 + ADR-0153 ratified text on disk (Status flips
  Proposed → Accepted if drafted-as-Proposed; verify at R0 probe).
- ADR-0094 §amendment-1 drafted + ratified.
- ADR-0150 §amendment-5 drafted + ratified (4-new-rows + exclusion
  list migrated from §am-4 per Phase 39 PB-R2-B).
- All shipped code per POST_PHASE_38 §4 Phase 43 "Modules touched":
  - `mindsos_core/schema.py` (`mutation_discipline` field).
  - `mindsos_knowledge/identifiers.py` (4 new ROLE_*; 4 new IRI
    builders; 4 new prefix entries; 4 new `_KINDS_PER_ROLE` rows;
    register the 4 new minters into `_IRI_BUILDERS` per Phase 39
    tuple-key shape).
  - `mindsos_knowledge/schemas/parameter_staging.py` (NEW).
  - `mindsos_knowledge/schemas/pending_promotions.py` (NEW).
  - `mindsos_knowledge/schemas/capacity_gaps.py` (NEW).
  - `mindsos_knowledge/schemas/learned_parameters.py` (NEW).
  - `mindsos_knowledge/schemas/episodic_memories.py` (Phase 39
    skeleton finalized — Episode + Memory properties +
    `memory_contains_episode` IntergraphEdgeType +
    `mutation_discipline` discipline declared).
  - `mindsos_knowledge/schemas/promoted_pipelines.py` (drop
    `confidence`; add status enum + lifecycle metadata; eliminate
    `serves_task_types`; CONTENT_FIELDS + METADATA_FIELDS).
  - `mindsos_knowledge/schemas/task_patterns.py` (flat 9-field per
    D-L2-10; CONTENT_FIELDS + METADATA_FIELDS).
  - `mindsos_knowledge/validators.py`
    (`validate_mutation_discipline`).
  - `mindsos_knowledge/exceptions.py` (`MutationDisciplineError`).
  - `mindsos_knowledge/bootstrap.py` (14-step `applies_after` order +
    4 new role-graph bootstraps + episodic_memories finalization).
  - `mindsos_knowledge/knowledge_layer.py` (`bootstrap()` discipline
    dispatch table + runtime invariant enforcement).
- `tools/migrate_phase_43_confidence_strip.py` — per PB-43-10 pick
  (script vs detector vs stub).
- `tests/phase_43/` test suite per POST_PHASE_38 §4 Phase 43
  "Automated tests" (10+ test files).
- `HANDOFF.md` §1 line bump + §2.2 update reflecting schema-v2
  completion + §3.1.7 status update.
- `_workbench/STREAM_A_BACKLOG.md` — close any absorbed items
  (likely A6).
- `_workbench/L2_FUTURE_WORK.md` §11 — mark closed items per Phase
  43 cascade.
- `confirmation_docs/PHASE_44_NEXT_CHAT_PROMPT.md` — seed for next
  rail. Note: Phase 44 is Rail C (L0 substrate), gated on
  `L0_SUBSTRATE_CHAT` closure; the next Rail A phase after Phase 43
  is the convergence Phase 46. Decide which chat to seed (Phase 44
  if L0_SUBSTRATE_CHAT has closed; Phase 46 substrate if all rails
  are closing; otherwise seed both).

After Phase 43 confirms, the next Rail A action is **convergence at
Phase 46** — gated on Phase 42 + Phase 44 + Phase 45 also being
confirmed. Phase 43 is the last pure-L2 ship; the L2 architectural
program closes here.

---

## Process notes inherited from Phase 25 / Phase 35 / Phase 38 / Phase 39

- **Probe-first** (Phase 38 R5-PB-I; reaffirmed at Phase 39 R0
  finding 2). Run the probes in §3 above before locking R0 picks.
- **Branch off `origin/main` only** — never off a sibling rail's
  branch.
- **Reading-list discipline (Chat C PB-Z)** — Phase 43 R0 reading-
  list MUST enumerate every prior phase touching files in Phase 43's
  `Modules touched`. Anticipates DAG merge collisions.
- **Sentinel chain anchor** — Phase 39 was chain root; Phase 43
  inherits and links forward (per Phase 35 ancestor-matching-content
  pattern). File: `tests/phase_43/test_adr_amendment_sentinels.py`.
  No SKIP logic (Model C dead post-housekeeping per Phase 39 PB-R3-B).
- **Ship-shape default DROPPED at Chat C closure (IL-8).** Phase 43
  is unambiguously code-shipping. No docs-only PB at R0.
- **Tester two-machine workflow** unchanged.
- **In-place ADR text edits are legitimate house style** for pre-
  ship amendments (per Phase 39 PB-R2-F). Git log is the audit
  trail.

---

*End of PHASE_43_NEXT_CHAT_PROMPT.md.*
