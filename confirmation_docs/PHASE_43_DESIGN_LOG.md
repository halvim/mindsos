# Phase 43 — Design Log

> **Status:** Design pass closed 2026-06-03 (this chat); awaiting impl execution.
> **Predecessor:** `PHASE_39_DESIGN_LOG.md` (Rail A slot 1; closed 2026-06-02).
> **Successor:** Phase 44 (Rail C; gated on `L0_SUBSTRATE_CHAT` closure) per `PHASE_44_NEXT_CHAT_PROMPT.md`.
> **Branch target:** `phase-43` off `phase-39-confirmed` tag.
> **Ship tag:** `phase-43-confirmed` at squash-merge commit on `main`.

This log captures the Phase 43 design pass closure. 18 saturation rounds resolved R0 picks-seed drift, R0b derivation errors, chat-opener-vs-PHASE_MAP §4 staleness, and 5 ADR amendment-text drafts. R3 cross-check confirms R1 impl-locks + R2 amendment texts are jointly consistent. Sections §1-§8 capture the design pass; §9 reserved for impl-time amendments.

---

## §1. Saturation milestones

| Round | Type | Result | Saturation |
|---|---|---|---|
| 1 | Initial pushback (PB-1 to PB-6) | 6 picks; PB-1 split phase | reset |
| 2 | NPB-1 to NPB-5 | 5 process-lock picks | reset |
| 3 | NPB2-1 to NPB2-3 | 3 R1 refinement picks | reset |
| 4 | Probes (5) + NPB4-1 reversal | PB-1 split collapses → single Phase 43; NPB4-2 retracted later | reset |
| 5 | NPB5-1 to NPB5-4 | Diligence-step adds | reset |
| 6 | Reading sweep + 4 reversals (NPB6-1 to NPB6-5) | Chat opener materially stale vs R0/R0b | reset |
| 7 | NPB7-1 to NPB7-4 | Storage-mode string drift + parity probe step | reset |
| 8 | Parity check + NPB8-1/8-2 load-bearing reversals | storage_mode per-NodeType model + ADR-0153 §am-1 needed | reset |
| 9 | NPB9-1 to NPB9-4 reconsiders | §amendment vs in-place edit picks refined | 1/3 |
| 10 | NPB10-1 to NPB10-3 | PR1 manifest-bump ownership + PR merge-target | reset |
| 11 | Broader reading + NPB11-1 reversal | bootstrap.py field-only per L2-37 split; PHASE_MAP §4 stale | reset |
| 12 | NPB12-1 reversal | ADR-0151 §6 in-place edit unnecessary | reset |
| 13 | R1 impl-locks output + NPB13-1 reversal | PHASE_44 seed (not PHASE_46) | reset |
| 14 | NPB13-4 probe + NPB14-1 to NPB14-4 | Process risk note + R1 detail adds | 1/3 |
| 15 | NPB15-1 to NPB15-4 | Spec deltas + design log scoping | 2/3 |
| 16 | NPB16-1 + NPB16-2 | ADR-0143 cross-ref add + ADR-0146 §am-3 no-edit verification | **3/3 — R1 closed** |
| 17 (R2 r2) | NPB17-1 to NPB17-5 | 5 wording refinements on R2 drafts | 2/3 |
| 18 (R2 r3) | NPB18-1 | §am-5 backward-compat cross-ref drop | **3/3 — R2 closed** |
| R3 | Cross-check | Pass; no inconsistencies | **R3 closed; ship-ready** |

---

## §2. R0 picks seed + R0b derivation drift reconciled

The Phase 43 pre-R0 design pass (closed 2026-06-02) produced `PHASE_43_R0_PICKS_SEED.md` and `PHASE_43_R0B_DERIVATIONS.md`. Both carried incremental drift relative to the latest authoritative artifacts:

| Drift source | Drift | Resolution round |
|---|---|---|
| R0b §3.2 + §3.5 + §2.2 | `FALKOR_LARGE_PROPERTY = "falkor_large_property"` | NPB7-1: corrected to `FALKOR_BLOB = "falkor_blob"` per ADR-0151 line 58 |
| R0b §3.3 | `storage_mode` on L2Schema class-level (per-role-graph) | NPB8-1: removed from L2Schema; declared per-NodeType per ADR-0151/0152 §6; only LearnedParameter in Phase 43 scope |
| R0 PB-43-6 + R0a-10/N4 (subclass pick) vs ADR-0153 §6 (L1 amendment) | Conflict | NPB8-2: ADR-0153 §amendment-1 supersedes §6 placement |
| R0 picks seed §4 "8 existing schemas" | Listed 9; count off by 1 | NPB12-3: design log notes; R0 seed left as historical record |
| R0b §2.3 HANDOFF cross-ref claim "12 → 13" | Actual HANDOFF says "8 → 12" | NPB11-7: R0b transcription typo; minor doc correction |
| R0b §1.4 + §1.6 Kahn topological-sort consumer | L2-37 split routes scheduler to Phase 44 | NPB11-1: bootstrap.py field-only at Phase 43 |

---

## §3. Chat-opener vs PHASE_MAP §4 staleness reconciled

The chat-opener output requirements + `POST_PHASE_38_PHASE_MAP.md §4` Phase 43 row carried stale assumptions inherited from pre-R0 design pass:

| Stale assumption | Reality | Resolution round |
|---|---|---|
| "3 new ADRs ratified" (chat opener + PHASE_MAP §4 line 482) | ADRs 0151/0152/0153 already Accepted on disk per R0a-3 | NPB6-3: Phase 43 implements, doesn't ratify |
| "ADR-0094 §amendment-1 (you add)" (chat opener) | §am-1 already on disk dated 2026-06-01 per R0b §4 | NPB6-2: Phase 43 verifies; ships detector only |
| "tools/migrate_phase_43_confidence_strip.py" (chat opener + PHASE_MAP §4 line 456) | R0 PB-43-10 picks detector form per Phase 39 PB-8 precedent | NPB6-4: `tools/check_phase_43_confidence_state.py` |
| "Phase 43 leaves consolidate.py unchanged" (chat opener OUT OF SCOPE) | R0 PB-43-9 picks retarget (`type_="Memory"` → `Episode`) | NPB6-1: Phase 43 retargets per R0 (PHASE_MAP §4 Phase 43 row didn't reflect this either) |
| "L1 Schema amendment" framing (PHASE_MAP §4 lines 415, 431, 443, 490, 503) | R0 picks L2Schema(Schema) subclass per N4 probe | NPB6-3 + NPB8-2 + NPB11-2 |
| "5 disciplines" (PHASE_MAP §4 line 432) | ADR-0153 §1 has 6 disciplines (append_only added per R0a-4/S3) | NPB6-3 + NPB11-2 |
| "PHASE_44_NEXT_CHAT_PROMPT seed" (chat opener) | Chat opener correct; NPB10-4 misread "unblocks Phase 46" | NPB13-1: revert to PHASE_44 seed per chat opener literal |

PHASE_MAP §4 Phase 43 row scope-rewrite is part of PR2 commit 6 deliverable.

---

## §4. ADR transcription parity check (R1 step 0)

NPB7-4 added explicit parity probe before R1 lifts R0b drafts. Findings:

- ADR-0094 §am-1 already drafted on disk (verified R0b §4 claim); only line 77-80 in-place edit needed (NPB8-4 / NPB17-3 / NPB18 final wording).
- ADR-0151 §Decision text correctly per-field-model (NPB12-1 reverses NPB8-3/NPB9-1 in-place edit pick — no edit needed).
- ADR-0151 frontmatter Related (Proposed) lists 0152/0153 as Proposed (stale; both Accepted on disk); cleanup NPB8-5.
- ADR-0152 §6 correctly puts `storage_mode` as per-NodeType property (confirmed per-field model).
- ADR-0153 §6 says "mindsos_core.Schema gains" (L1 placement); R0 N4 reverses to L2Schema(Schema); §amendment-1 lands (NPB8-2 / NPB17-2 final header style).

Pattern (NPB11-META): each rounds-6-onward probe surfaced additional drift. Future-phase chats should run ADR transcription parity as R1 step 0 by default — drift accumulates between design-pass artifacts and Accepted ADRs.

---

## §5. R1 impl-shape locks — PR1 (framework + 9-surface manifest bump)

Branch: `phase-43`. Both PRs target the branch; single squash to `main` at confirm-phase; single tag.

### §5.1 PR1 module touches

| File | Action | LOC est |
|---|---|---|
| `mindsos_knowledge/schemas/_base.py` | NEW: `Discipline` enum (6 values) + `StorageMode` enum (3 values, `"falkor_blob"` per ADR-0151) + `L2Schema(Schema)` single-field subclass (`mutation_discipline: Discipline`, required) | ~70 |
| `mindsos_knowledge/exceptions.py` | ADD: `MutationDisciplineError(ValueError)` per ADR-0153 §5 | ~25 |
| `mindsos_knowledge/validators.py` | ADD: `validate_mutation_discipline` + partition invariant | ~80 |
| `mindsos_knowledge/schemas/{ontology,lexicon,concepts,alignment}.py` | EDIT each: `Schema(...)` → `L2Schema(mutation_discipline=Discipline.ADMIN_AUTHORED, ...)` | ~3 each |
| `mindsos_knowledge/schemas/promoted_pipelines.py` | EDIT: → IMMUTABLE_SUCCESSOR + `PIPELINE_CONTENT_FIELDS` + `PIPELINE_METADATA_FIELDS` (16 fields; `confidence` dropped) | ~30 |
| `mindsos_knowledge/schemas/task_patterns.py` | EDIT: → IMMUTABLE_SUCCESSOR + partition frozensets (13 fields; `confidence` kept) | ~25 |
| `mindsos_knowledge/schemas/episodic_memories.py` | EDIT: → APPEND_ONLY_WITH_LAZY_INLINE (PR2 fills body) | ~3 |
| `mindsos_knowledge/schemas/problem_trace.py` | EDIT: → APPEND_ONLY + partition frozensets | ~15 |
| `mindsos_knowledge/schemas/capacity_state.py` | EDIT: → MUTABLE_WITH_RETENTION | ~3 |
| `docs/decisions/adr/0150-l2-knowledge-lifecycle.md` | §amendment-5 per §8.1 | ~60 |
| `docs/decisions/adr/0153-l2-mutation-discipline.md` | §amendment-1 per §8.2 | ~25 |
| `docs/decisions/adr/0151-l2-storage-tiers.md` | In-place: frontmatter Related block per §8.4 | ~2 |
| `docs/decisions/adr/0094-confidence-pipeline-level.md` | In-place §am-1 line 77-80 per §8.3 | ~5 |
| `docs/decisions/adr/0143-kl-write-handle-pattern.md` | §Implementation references cross-ref line per §8.5 | ~3 |
| `docs/decisions/adr/0045-*.md` through `docs/decisions/adr/0154-*.md` (6 ADRs) | Stale `ROLE_MEMORIES` / `memory_iri` / `memories-` example cleanup (§9.6 carry-forward) | ~40 total |
| `docs/_workbench/L2_CHAT_DECISIONS.md` | D-L2-3 cascade (L1→L2 placement); D-L2-4 (paired_pipelines stale); D-L2-10 (9-field naming nit) | ~10 |
| `mindsos_cli/manifest.toml` | `phase = "39"` → `"43"`; `version = "0.0.0+phase39"` → `"0.0.0+phase43"` | ~2 |
| `mindsos_{core,cli,capacity,server,instances,admin,knowledge}/__init__.py` (×7) | `__version__` bump | ~7 |
| `pyproject.toml` | `[project] version` bump | ~1 |
| `docker-compose.yml` | `mindsos:phase39-*` → `mindsos:phase43-*` (prod + test) | ~2 |
| `tests/phase_{30,31,34}/test_phase_*_export_slate.py` (×3) | `test_version_bumped_to_phase_34` literal phase-39 → phase-43 | ~3 |

### §5.2 PR1 test surface

| File | Assertions |
|---|---|
| `tests/phase_43/__init__.py` | empty |
| `tests/phase_43/test_l2schema_subclass.py` | `L2Schema.__bases__ == (Schema,)`; constructor requires `mutation_discipline`; subclass round-trip; all 9 schema builders return `L2Schema`; each declared discipline matches §3.5 table; Discipline enum = 6 values; StorageMode enum = 3 values with `FALKOR_BLOB.value == "falkor_blob"`; **L2Schema adds exactly `mutation_discipline` beyond Schema** (NPB14-3 single-field invariant guard) |
| `tests/phase_43/test_validate_mutation_discipline.py` | partition-required disciplines fail without CONTENT/METADATA declarations; partition-optional pass; partition invariant enforced; rejection raises `MutationDisciplineError` |
| `tests/phase_43/test_partition_invariant.py` | promoted_pipelines + task_patterns + problem_trace: CONTENT ∪ METADATA == *_PROPS; CONTENT ∩ METADATA == ∅; cardinality matches ADR-0152 |
| `tests/phase_43/test_adr_amendment_sentinels.py` | ADR-0150 §am-5 present + 4 new rows + 5-item exclusion list; ADR-0153 §am-1 present + L2Schema placement language; ADR-0151 frontmatter Related lists 0152/0153 as Accepted; ADR-0094 §am-1 says "detector"; ADR-0151/0152/0153 status: Accepted; ADR-0143 §Implementation references gains ADR-0153 §2 cross-ref |

### §5.3 PR1 commit boundary (7 commits)

1. NEW amendment text (ADR-0150 §am-5 + ADR-0153 §am-1)
2. `_base.py` + `exceptions.py`
3. `validators.py`
4. 9 existing schema audits (discipline transcription + partition frozensets where required)
5. Sentinel tests + 9-surface manifest bump (atomic per Phase 39 §9.4) — **cumulative gate trigger**
6. ADR cleanup sub-commit A: 6 stale-example ADRs + ADR-0151 frontmatter + ADR-0094 §am-1 in-place + ADR-0143 cross-ref
7. Decisions-doc cleanup sub-commit B: D-L2-3 + D-L2-4 + D-L2-10

Follow-up commits 5b/5c per Phase 39 §9.3 precedent if cumulative-gate failures surface.

---

## §6. R1 impl-shape locks — PR2 (4 new schemas + body finalization + consumer wiring)

### §6.1 PR2 module touches

| File | Action |
|---|---|
| `mindsos_knowledge/identifiers.py` | ADD: 4 `ROLE_*` constants; 4 IRI builders (`staged_evidence_iri`, `pending_promotion_iri`, `capacity_gap_iri`, `learned_parameter_iri`); 4 prefix entries; 4 `_KINDS_PER_ROLE` rows; **4 `_IRI_BUILDERS` tuple-key registrations** (NPB11-3 per Phase 39 §am-3) |
| `mindsos_knowledge/schemas/parameter_staging.py` | NEW: `StagedEvidence` per D-L2-11 + ADR-0152 §3; MUTABLE_WITH_RETENTION |
| `mindsos_knowledge/schemas/pending_promotions.py` | NEW: `PendingPromotion` per D-L2-13 + ADR-0152 §4; AUDIT_ONLY_AFTER_SETTLED |
| `mindsos_knowledge/schemas/capacity_gaps.py` | NEW: `CapacityGap` per D-L2-14 + ADR-0152 §5; MUTABLE_WITH_RETENTION |
| `mindsos_knowledge/schemas/learned_parameters.py` | NEW: `LearnedParameter` per D-L2-15 + ADR-0152 §6; Local=MUTABLE_WITH_RETENTION / Global=ADMIN_AUTHORED; **per-property `storage_mode` field** (NPB8-1) |
| `mindsos_knowledge/schemas/episodic_memories.py` | FINALIZE: Episode (6 content fields) + Memory (1 content + 3 metadata) + `memory_contains_episode` IntergraphEdge per D-L2-17; `EPISODE_CONTENT_FIELDS` + `EPISODE_METADATA_FIELDS` (empty) + `MEMORY_CONTENT_FIELDS` + `MEMORY_METADATA_FIELDS`; **no storage_mode on Episode** (defers to TaskInput composite at L5) |
| `mindsos_knowledge/bootstrap.py` | ADD: `applies_after: frozenset[str] = frozenset()` parameter on 13 `ensure_*_role_graph` functions; declarations per R0b §1.2 (soft edge `episodic_memories ← {task-patterns}` per NPB6-6); **field-only** per NPB11-1 (Phase 44 ships scheduler) |
| `mindsos_knowledge/knowledge_layer.py` | ADD: `KnowledgeLayer.bootstrap()` discipline dispatch table per ADR-0153 §2 |
| `mindsos_knowledge/write_handle.py` | FILL: `KLWriteHandle` write-path body with discipline enforcement per ADR-0153 §2 (second meaningful body fill of Phase 33 stub per R0 N3) |
| `mindsos_capacity/builtins/consolidate.py` | RETARGET per R0 PB-43-9: `type_="Memory"` → `type_="Episode"`; `memory_composite_iri` → `episode_iri`; remove `NOTE(phase-48-retarget)` comments at `validate_node` + `write_and_validate` sites; module docstring updated |
| `tools/check_phase_43_confidence_state.py` | NEW: detector per R0 PB-43-10 (FalkorDB query; exits non-zero if any Pipeline carries `confidence`) |
| `tests/phase_33/test_consolidate_mm_capacity.py` | UPDATE per NPB13-5: `memory_id` fixture keys → `episode_id` (5 line changes); line 137 IRI literal `:memory:` → `:episode:` |
| `tests/phase_13/test_dispatch.py` | EXTEND per R0b §2.3: 4 new role assertions |
| `HANDOFF.md` | §1 line bump; §2.2 Phase 43 shipped state (12 named role-graphs + alignment-prefix; Episode/Memory body); §3.1.X status block |
| `confirmation_docs/POST_PHASE_38_PHASE_MAP.md` | §4 Phase 43 row **scope-rewrite** per NPB11-2 (L1→L2, 6 disciplines, detector, write_handle.py + `_IRI_BUILDERS` adds, Episode no storage_mode, bootstrap field-only, 3 doc files) + Status: SHIPPED |
| `docs/future_work/L2_FUTURE_WORK.md` | §11 routing: L2-29/30/31/32/33/37(field)/40 marked CLOSED — shipped Phase 43; routing-note text updated (L2-29 "L1 amendment" → "L2 placement via ADR-0153 §am-1"; L2-40 migrator → detector); L2-37 consumer + L2-39 + L2-41 routed to Phase 44 |
| `docs/concepts/role-graphs.md` | UPDATE: 4 new role-graph descriptions |
| `docs/concepts/mutation-discipline.md` | NEW: framework + 6 disciplines + L2Schema subclass + dispatch table + validator + exception |
| `docs/concepts/storage-tiers.md` | NEW: 3 tiers + per-NodeType `storage_mode` pattern + v1 consumers |
| `confirmation_docs/PHASE_43_DESIGN_LOG.md` | THIS FILE |
| `confirmation_docs/PHASE_44_NEXT_CHAT_PROMPT.md` | NEW: seeds Phase 44 with L2-37 consumer/scheduler + L2-39 audit constant + L2-41 KL retention surface |

### §6.2 PR2 test surface

| File | Assertions |
|---|---|
| `tests/phase_43/test_4_role_graphs.py` | 4 new schemas registered; IRI builders produce expected forms; `_IRI_BUILDERS` tuple-key registrations present; **5-item exclusion list regression guard** (NPB14-4) — sense-correlations / world-axioms / training-runs / fol-rules / fol-ledger NOT in ROLE_* constants |
| `tests/phase_43/test_mutation_discipline_runtime_invariant.py` | `KnowledgeLayer.bootstrap()` builds dispatch table from 13 schemas; write attempts violate disciplines raise `MutationDisciplineError`; lazy-inline on episodic_memories passes |
| `tests/phase_43/test_storage_mode_field.py` | LearnedParameter declares `storage_mode`; **no other Phase 43 NodeType declares it** (NPB11-4 regression guard); Literal accepts inline / falkor_blob / blob_ref only |
| `tests/phase_43/test_bootstrap_applies_after.py` | All 13 `ensure_*_role_graph` accept `applies_after` parameter; declarations match R0b §1.2 table; **Kahn behavior NOT asserted** (defers to Phase 44 per NPB11-5) |
| `tests/phase_43/test_confidence_detector_script.py` | Detector exits 0 on empty state; non-zero on injected confidence property |
| `tests/phase_43/test_episodic_memories_completion.py` | Episode + Memory NodeTypes; `memory_contains_episode` IntergraphEdge; partition frozensets correct; discipline=APPEND_ONLY_WITH_LAZY_INLINE |
| `tests/phase_43/test_promoted_pipelines_v2.py` | status enum (5 values); lifecycle metadata; `confidence` ABSENT; `paired_pipelines` ABSENT from Pipeline schema |
| `tests/phase_43/test_task_patterns_v2.py` | 13 fields including `confidence` (metadata; kept) |
| `tests/phase_43/test_consolidate_retarget.py` | `consolidate.py` writes `type_="Episode"`; `episode_iri` used; `NOTE(phase-48-retarget)` comments absent |

### §6.3 PR2 commit boundary (6 commits)

1. `identifiers.py` + 4 new schema files + `episodic_memories.py` body finalization
2. `bootstrap.py` applies_after declarations + `knowledge_layer.py` dispatch + `write_handle.py` enforcement
3. `consolidate.py` retarget (capacity layer)
4. `tools/check_phase_43_confidence_state.py` detector
5. Tests (9 in `tests/phase_43/` + `tests/phase_13/test_dispatch.py` extension + `tests/phase_33/test_consolidate_mm_capacity.py` updates) — **cumulative gate trigger**
6. HANDOFF + PHASE_MAP §4 rewrite + L2_FUTURE_WORK + 3 doc files + this design log + PHASE_44 seed — **shipped flip per Phase 39 PB-R1-F dual-flip precedent**

Follow-up commits 5b/5c per Phase 39 §9.3 precedent if cumulative-gate failures surface.

---

## §7. Process locks

- **NPB10-1** — PR1 owns 9-surface manifest bump (atomic per Phase 39 §9.4); PR2 builds on stable post-bump state.
- **NPB10-2** — Both PRs target `phase-43` branch; single squash to `main`; single tag.
- **NPB10-3** — Cumulative gate runs twice on phase-43 branch (post-PR1 + post-PR2); final main-squash gate-free. Mac → push → Linux pull → gate → report cycle per Phase 39 precedent.
- **NPB11-1** — `bootstrap.py` field-declarations-only per L2-37 split; Kahn scheduler defers to Phase 44.
- **NPB9-4** — PR1 cleanup pass sub-split into two commits (ADR cleanup + decisions-doc cleanup).
- **NPB13-1** — PR2 commit 6 ships `PHASE_44_NEXT_CHAT_PROMPT.md` (not PHASE_46; Phase 46 gated on all 4 rails per DAG).

---

## §8. R2 amendment-text drafts

### §8.1 ADR-0150 §amendment-5 (NEW; lands after §am-4 in Revisions)

```markdown
### amendment-5 (Phase 43 ship — 2026-06-XX) — 4 new role-graph rows + exclusion list

**Trigger:** Phase 39 PB-R2-B + Chat C IL-3 (`POST_PHASE_38_PHASE_MAP.md §1` IL-3 row) split the original L2-chat single-bulk §am-4 into two surgical amendments — §am-4 holds the `memories` → `episodic_memories` rename row only (Phase 39 ship); §am-5 holds the 4-new-role-graph expansion + the exclusion list (Phase 43 ship). This split matches the §am-1 / §am-2 / §am-3 precedent of one event per amendment. See `_workbench/L2_CHAT_DECISIONS.md` D-L2-26 + `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §1` IL-3 + `confirmation_docs/PHASE_39_DESIGN_LOG.md` PB-R2-B.

**Amended behavior.**

The §Decision closed role-set expands by 4 named entries. Combined with §am-4's rename row, the post-§am-5 closed role-set is 12 named entries + alignment-prefix.

**New rows added:**

| Scope | Role | Schema builder |
|---|---|---|
| Local | `parameter-staging` | `build_parameter_staging_schema(strict)` |
| Local + Global | `pending-promotions` | `build_pending_promotions_schema(strict)` |
| Global | `capacity-gaps` | `build_capacity_gaps_schema(strict)` |
| Local + Global | `learned-parameters` | `build_learned_parameters_schema(strict)` |

Concrete schema contents per ADR-0152 §3-§6.

**Per-role-graph mutation discipline** for the 4 new roles per ADR-0153 §1:

| Role | Discipline |
|---|---|
| `parameter-staging` | `mutable_with_retention` |
| `pending-promotions` | `audit_only_after_settled` |
| `capacity-gaps` | `mutable_with_retention` |
| `learned-parameters` (Local) | `mutable_with_retention` |
| `learned-parameters` (Global) | `admin_authored` |

**Storage tier.** Among the 4 new role-graphs, only `learned-parameters.LearnedParameter.value` carries a large-payload field warranting an explicit `storage_mode = "falkor_blob"` declaration per ADR-0151 + ADR-0152 §6. `StagedEvidence`, `PendingPromotion`, and `CapacityGap` carry no large-payload fields; no `storage_mode` declaration needed.

**Explicitly NOT added in this amendment (migrated from §am-4):**

- `sense-correlations` — withdrawn; data lives in lexicon empirical layer per `_workbench/L2_CHAT_DECISIONS.md` D-L2-2. ALS subsystem #8 retains the name as a parameter-set label pointing at lexicon-empirical parameter key.
- `world-axioms` — WSD installation chat owns; future amendment row when WSD ships.
- `training-runs` — FOL installation chat owns per Chat A R5 D29; future amendment if FOL accepts.
- `fol-rules`, `fol-ledger` — FOL installation chat owns.

These items were originally listed in §am-4's "Explicitly NOT added" section; they migrate here per Phase 39 PB-R2-B to keep §am-4 narrowed to the rename-only surgical scope.

**Rationale.** The 4 new role-graphs are a single architectural event authored by Chat A + Chat B and closed by the L2 chat. Bulk amendment matches the per-amendment pattern. Splitting from §am-4 (rather than authoring 4 separate §am-5/6/7/8 rows) preserves the event coherence; the §am-4 / §am-5 split is between **rename** (one mechanical change touching identifiers + KL surface) and **expansion** (four schema-shape additions touching the closed role-set bound).

**Out-of-scope for amendment-5:**

* Schema field contents for each new role-graph (locked in ADR-0152 §3-§6).
* Bootstrap topological order field (`applies_after`) ships at Phase 43 per L2-37; the **consumer/scheduler** ships at Phase 44 per L2-37 split.
* `mutation_discipline` placement on the Schema surface — locked in ADR-0153 + §amendment-1 (L2Schema(Schema) subclass placement supersedes §6 L1-Schema text).
* `storage_mode` placement on NodeTypes — per ADR-0151 §Decision + ADR-0152 §6 (per-NodeType-property; not on L2Schema class).

**Escape clause** (preserved from §am-4): Future role additions require new §Revisions entries citing the consumer requirement + schema builder + mutation discipline. Phase 13 sentinel test enforces.

See `confirmation_docs/PHASE_43_R0_PICKS_SEED.md` for the Phase 43 R0 pick chain + cross-references to ADR-0151, ADR-0152, ADR-0153, ADR-0094 §am-1.
```

### §8.2 ADR-0153 §amendment-1 (NEW)

```markdown
### amendment-1 (Phase 43 ship — 2026-06-XX) — L2Schema(Schema) subclass placement

**Trigger.** ADR-0153 §6 as-authored said: "`mindsos_core.Schema` gains: `mutation_discipline: Literal[...] = "mutable_with_retention"  # backward-compat default`." That is an L1 amendment placement.

Phase 43 R0 design pass (`confirmation_docs/PHASE_43_R0_PICKS_SEED.md` PB-43-6 + R0a-10 / N4 probe) reversed via probe: an `L2Schema(Schema)` subclass in `mindsos_knowledge/schemas/_base.py` is consumer-cascade-safe (zero `isinstance(.., Schema)` / `_SCHEMA_REGISTRY` / `Schema.__name__` hits across all packages) and respects ADR-0010 import direction (L1 Schema does not gain L2-specific vocabulary).

**Amended behavior.**

§6 placement language supersedes as follows:

- **`mindsos_knowledge.schemas._base.L2Schema(Schema)` gains `mutation_discipline: Discipline`** — required at construction (no backward-compat default; L2 schemas declare explicitly).
- **`mindsos_core.Schema` is unchanged** — L1 stays primitive; no `mutation_discipline` field; no `Discipline` enum import.
- The `Discipline` enum is defined in `mindsos_knowledge.schemas._base` (L2-private vocabulary) with the six values enumerated in §1.
- Existing schemas (Phase 13's 9 builders) migrate from `Schema(...)` to `L2Schema(mutation_discipline=Discipline.<value>, ...)` in Phase 43 PR1 audit.
- The L4 startup invariant (§2) and field partition discipline (§3) read `L2Schema.mutation_discipline` (via the inherited Schema attribute access pattern); `MutationDisciplineError` (§5) is raised against L2Schema-owned writes.

**Rationale for L2 placement.** N4 probe found zero L1 Schema consumers depending on the discipline field; backward-compat default loses its load-bearing role. L2-private vocabulary (Discipline enum's six values are L2 concepts) belongs at L2. ADR-0010 import-direction symmetry preserved (no L1 imports of L2 enums). Required-at-construction is stricter than L1's loose backward-compat default; L2 schemas can't accidentally inherit `mutable_with_retention` without intent.

**Out-of-scope for amendment-1.**

* Discipline enum value semantics (locked in §1; six values unchanged).
* L4 startup invariant (§2) unchanged in mechanism.
* Per-field partition discipline (§3) unchanged.
* MutationDisciplineError signature (§5) unchanged.

**Cross-reference.** See `confirmation_docs/PHASE_43_R0_PICKS_SEED.md` PB-43-6 + R0a-10/N4/P-D/P-E; `confirmation_docs/PHASE_43_R0B_DERIVATIONS.md` §3 L2Schema sketch; ADR-0152 §6 for per-NodeType-property `storage_mode` placement (analogous L2 vocabulary localization).
```

### §8.3 ADR-0094 §am-1 in-place edit (lines 77-80)

Replace existing text:

```markdown
**Migration of shipped state:** Per Phase 43 R0 pick PB-43-10 (`confirmation_docs/PHASE_43_R0_PICKS_SEED.md`), v1 production has no `confidence`-carrying Local-Pipeline records; a real migrator is dead code. Phase 43 ships **a detector form** (`tools/check_phase_43_confidence_state.py`) per the Phase 39 PB-8 precedent (`tools/check_rename_state.py`) — queries FalkorDB for any Pipeline record carrying the `confidence` property; exits non-zero if any found.
```

### §8.4 ADR-0151 frontmatter Related block

Replace existing block:

```markdown
**Related (Accepted):** [ADR-0121](0121-falkordb-persistence.md),
[ADR-0150](0150-l2-knowledge-lifecycle.md),
[ADR-0044](0044-memories-move-to-local-per-user.md) §amendment-3,
[ADR-0152](0152-l2-role-graph-schema-v2.md),
[ADR-0153](0153-l2-mutation-discipline.md).
```

(Related (Proposed) block removed; 0152/0153 promoted to Accepted; §am qualifiers dropped on 0150/0153 per NPB17-4.)

### §8.5 ADR-0143 §Implementation references cross-ref

Append after existing ADR-0146 §am-3 cross-ref line:

```markdown
- ADR-0153 §2 (Phase 43 PR2 ship — 2026-06-XX) — `KLWriteHandle` write-path body fills with mutation-discipline enforcement consuming `KnowledgeLayer.bootstrap()`'s dispatch table per ADR-0153 §2. Handle pattern + Surface + Constraint defined in this ADR are unchanged.
```

---

## §9. Impl-time amendments (reserved for tester ship pass)

Per Phase 39 §9 precedent, this section captures impl-shape picks + gate-driven follow-up commits + ship-closure anomalies + carry-forwards. Reserved for tester to fill during impl execution.

### §9.1 R1 impl-shape picks (Cowork-driven pair execution ship pass)

The Phase 43 ship execution chat ran R1 + R2 impl-time picks beyond design pass saturation. 11 of the impl picks were forecast at design closure (P1-P5, Q1-Q5, R1) and resolved pre-PR1; 6 emerged in-flight during impl (R2-R10); 1 was an impl-time architectural reconciliation (R6).

**Pre-impl pushback round 1 (P1-P5):** raised before branching.

- **P1 — BLOCKER: design-chat dirty-tree resolution.** Design chat (2026-06-03) closed without committing the 4 modified + 2 untracked files (CLAUDE.md, HANDOFF.md, PHASE_39_DESIGN_LOG.md §9 backfill, POST_PHASE_38_PHASE_MAP.md, PHASE_43_DESIGN_LOG.md NEW, PHASE_43_SHIP_CHAT_PROMPT.md NEW). Resolution: **split-land** — Commit A on main contains the Phase 39 §9 backfill + POST_PHASE_38 §1 IL-3 carry-forwards (Phase 39 history; belongs on main); the 4 Phase-43-design-closure files (CLAUDE.md status + HANDOFF §3.1.12 + design log + ship prompt + POST_PHASE_38 §4 stale-notice) ship as PR1 commit 0 design-closure landing on `phase-43` branch. Forensic correctness: Phase 39 history attributed to a main commit, not a Phase 43 squash SHA.
- **P2 — REAL: consolidate.py retarget non-buildable intermediate.** Design log §6.3 PR2 commit 3 ships consolidate.py retarget (`type_="Memory"` → `Episode`) while §6.3 PR2 commit 5 ships the corresponding `tests/phase_33/test_consolidate_mm_capacity.py` fixture updates — commits 3 + 4 would fail the phase_33 test until commit 5 lands. Resolution: **co-locate test updates with retarget at PR2 commit 3** per the design log §117 "each commit must be independently buildable" rule.
- **P3 — MINOR: PR1 commits 6+7 land AFTER cumulative-gate trigger.** Acknowledged; gate per design log §11.1 runbook fires after the full PR1 push (post-commit-7), not after commit 5 individually. Commit 5 is the "test surface trigger" rather than the gate execution moment.
- **P4 — HISTORY HYGIENE.** Resolved by P1 split-land (Phase 39 §9 backfill on main, not in phase-43 squash).
- **P5 — CARRY-FORWARD: design-chat-close process gap.** Recorded in §9.2 + POST_PHASE_38 §1 + HANDOFF §9 as a Phase 44+ discipline carry-forward: design-pass chats must commit closure artifacts before ending.

**Pre-impl pushback round 2 (Q1-Q5):**

- **Q1 — REAL: tests/phase_13/test_dispatch.py non-buildable intermediates.** Probe at line 74 (`assert len(_ROLE_SCHEMA_BUILDERS) == 8`) + line 78 (set-equality `_ALL_NAMED_ROLES`) revealed exactly-8 sentinel that breaks at the moment PR2 commit 1 adds 4 new schemas. Resolution: **move tests/phase_13/test_dispatch.py extension to PR2 commit 1** (import 4 new ROLE_*, extend `_ALL_NAMED_ROLES` 8→12, bump `len == 12`). Same buildability rule violation class as P2; design log §6.3 violated its own §117 rule in two places.
- **Q2 — REAL: CLAUDE.md needs a second status-line flip at PR2 commit 6.** PR1 commit 0 landed the "design pass closed" status; PR2 commit 6 must flip to "SHIPPED". Design log §6.1 deliverables list HANDOFF.md but omits CLAUDE.md.
- **Q3 — MINOR: squash-to-main may not be fast-forward.** Resolution applied: branched `phase-43` off `main` (`bbf4838`, post-Commit-A) instead of the literal `phase-39-confirmed` tag (`7a8bf10`) — squash is now a fast-forward + no cross-hunk merge on POST_PHASE_38_PHASE_MAP.md.
- **Q4 — MINOR: `git add -p` partial-file commit on POST_PHASE_38_PHASE_MAP.md for Commit A.** Successfully executed; staged only the §1 hunk; left §4 hunks for PR1 commit 0.
- **Q5 — RECORDED: design log violated own buildability process lock in two places.** P2 + Q1. Carry-forward: design-pass closure should run a buildability scan over the locked commit boundary before ratification.

**Pre-impl pushback round 3 (R1-R5):**

- **R1 — MINOR: design log §5.1 mistransposes export-slate edit count.** Says "tests/phase_{30,31,34}/test_phase_*_export_slate.py (×3)" but the actual `__version__` literal bumps are 4 lines across 3 files (`phase_34` has 2 literals — capacity + knowledge). Resolution: PR1 commit 5 bumped 4 literals; design log §9.4 wording could be tightened in a future-phase update.
- **R2 — TRACK: gate coverage on 5 non-tested packages is zero.** Only `mindsos_capacity` + `mindsos_knowledge` have `__version__` test coverage. Phase 44+ test surface should cover all 7 packages.
- **R3 — TRACK: notes-phase-43.md author step missing from design log §6.3.** Added to pair-execution plan post-PR2-gate per §9 below.
- **R4 — TRACK: §6.1 omits `mindsos_knowledge/schemas/__init__.py` + `mindsos_knowledge/__init__.py` from PR2 commit 1 file list.** The new schemas + IRI builders + ROLE constants MUST be re-exported. Resolution: PR2 commit 1 included plumbing edits (and additional re-export plumbing was filed as PR1 commit 5b for L2Schema / Discipline / StorageMode top-level exports — see R8).
- **R5 — TRACK: Commit A mkdocs check.** Done; 17 WARN baseline match HANDOFF §3.1.10 + 0 ERROR + 0 new from Commit A content.

**Impl-time picks (R6-R10):**

- **R6 — ARCHITECTURAL: `memory_contains_episode` nomenclature reconciled.** ADR-0152 §7 names this edge an "IntergraphEdge" but `IntergraphEdgeType` lives on :class:`MetagraphSchema` (per ADR-0148 + Phase 05b), not on per-graph :class:`Schema`. Both `Episode` + `Memory` NodeTypes live in the same `episodic_memories` Schema (Chat B D-B47 "inside the same role-graph"). Phase 43 ships as a regular `EdgeType` (`MEMORY_CONTAINS_EPISODE`: Memory → Episode); within-role-graph routing matches actual data shape. MetagraphSchema-level `IntergraphEdgeType` registration may be reconsidered if a cross-role-graph use case surfaces (Phase 48+ Memory composite consolidation flow may revisit).
- **R7 — PATH DRIFT: design log §5.1 referenced `docs/_workbench/L2_CHAT_DECISIONS.md`** but the file lives at `confirmation_docs/L2_CHAT_DECISIONS.md` per Chat C IL-9 migration. PR1 commit 7 edits the file at its actual location. Future-phase doc-touch enumerations should reference current paths.
- **R8 — DISCOVERED: top-level `mindsos_knowledge` re-exports missing for L2Schema / Discipline / StorageMode.** PR1 commit 2 added these to `mindsos_knowledge.schemas` only; PR1 commit 5 sentinel tests import from `mindsos_knowledge` top-level per Phase 13 schema-builder re-export convention. Linux collection ImportError surfaced post-PR1-push; fixed in **PR1 commit 5b** gate-driven follow-up.
- **R9 — DISCOVERED: 3 phase_13 + phase_43 test failures at first PR1 gate run.**
  - `tests/phase_13/test_advisory_property_constants.py::test_pipeline_props_declare_design_properties`: asserted `{"pipeline_name", "task_type", "confidence", "n_runs"} <= PIPELINE_PROPS` but Phase 43 schema-v2 drops `task_type` (never had real consumer) + `confidence` (ADR-0094 §am-1).
  - `tests/phase_13/test_advisory_property_constants.py::test_task_pattern_props_declare_design_properties`: same class; `task_type` renamed to `pattern_name` per ADR-0152 §2.
  - `tests/phase_43/test_adr_amendment_sentinels.py::test_adr_0153_amendment_1_present_with_l2schema_placement`: asserted `"mindsos_core.Schema is unchanged"` substring; the ADR body has backtick-wrapped form `` `mindsos_core.Schema` is unchanged ``; substring without backticks broke at closing backtick. Fixed in **PR1 commit 5c** by switching to backtick-wrapped substring.
- **R10 — DISCOVERED: docker test image rebuild required after each push.** `docker-compose.yml` mindsos-test service has no source bind-mount; image bakes source at build time. Each Linux gate run requires `docker compose build mindsos-test` before `docker compose run`. Documented in HANDOFF §9 for future-phase tester runbooks.

### §9.2 R2 ADR text-shape picks

R2 amendment-text drafts §8.1-§8.5 shipped verbatim with one adjustment: the placeholder ship-date `2026-06-XX` was bound to `2026-06-03` per the L2-chat-closure-date precedent (ADR-0044 §am-3 used the L2 chat closure date 2026-06-01, not the Phase 39 ship date 2026-06-02). All 5 amendment texts landed at PR1 commit 1 (ADR-0150 §am-5 + ADR-0153 §am-1) and PR1 commit 6 (ADR-0094 §am-1 + ADR-0151 frontmatter + ADR-0143 §Implementation cross-ref).

### §9.3 Gate-driven follow-up commits

- **PR1 commit 5b (`3cd7a0b`)** — top-level `mindsos_knowledge` re-exports for `Discipline` / `L2Schema` / `StorageMode` per R8. Fixed sentinel-test collection ImportError.
- **PR1 commit 5c (`610ed60`)** — 3 test fixes per R9 (`tests/phase_13/test_advisory_property_constants.py` v2 expected-fields + `tests/phase_43/test_adr_amendment_sentinels.py` backtick-wrapping).

Both surfaced at PR1 cumulative gate; resolved cleanly per Phase 39 §9.3 pattern. PR1 gate result: **3544 passed / 0 failed / 8 skipped (31:43)**. PR2 gate result: (filled at confirm-phase).

**Pair-execution discipline (R11 NEW — Cowork ↔ Mac ↔ Linux).** This phase ran under a 3-actor pair-execution pattern: Cowork (sandbox) prepares file content via Edit/Write tools; user (Henrique) runs git on Mac; Linux runs cumulative gates via docker. Sandbox `.git/` is read-only, so Cowork cannot commit/branch/push directly. Pattern established as default for all future Phase ship chats. See POST_PHASE_38 §1 row + HANDOFF §9.

**6-step confirm-phase workflow (R12 NEW).** Two canonical CLI commands underpin the workflow: **(a)** `mindsos confirm-phase --init-notes N` generates `confirmation_docs/notes/notes-phase-N.md` from the project's notes template; **(b)** `mindsos confirm-phase --phase N --notes-file notes-phase-N.md` writes `PHASE_N_CONFIRMED.md` and consumes the notes file. The 6 steps: (1) Cowork instructs `mindsos confirm-phase --init-notes N` (Mac) to mint the notes file; (2) Cowork provides layer title in a copy-block; (3) Cowork provides complete tester_notes body in a copy-block; (4) tester edits the notes file on Linux; (5) tester runs `mindsos confirm-phase --phase N --notes-file notes-phase-N.md` on Linux from post-squash main; (6) tester commits `PHASE_N_CONFIRMED.md` + notes-phase-N.md + pushes. Documented in HANDOFF §9 + POST_PHASE_38 §1.

### §9.4 Per-phase manifest-bump checklist (carry-forward from Phase 39 §9.4)

Unchanged from Phase 39 §9.4. Applied at PR1 commit 5 atomically across:

1. `mindsos_cli/manifest.toml` `[mindsos] phase` + `version`.
2-8. `mindsos_{core,cli,capacity,server,instances,admin,knowledge}/__init__.py` `__version__` (×7).
9. `pyproject.toml` `[project] version`.
10. `docker-compose.yml` `mindsos:phase43-prod` + `mindsos:phase43-test`.
11. `tests/phase_{30,31,34}/test_phase_*_export_slate.py` literal value bumps (×3 files; file name stays at `phase_34`).

Doctor self-test + version-parity tests gate this. Doctor failure at the cumulative gate is the cleanest detection signal.

### §9.5 Pre-confirm-phase squash-merge discipline (carry-forward from Phase 39 §9.5)

`mindsos confirm-phase --phase 43` MUST run on a `main` that already contains the squash-merge of `phase-43`. Skipping the squash-merge step on Mac before running confirm-phase on Linux yields a CONFIRMED.md committed BEFORE the squash-merge it describes (Phase 39 ship anomaly; recovered via reflog restore + force-retag — see `PHASE_39_DESIGN_LOG.md §9.5`).

### §9.6 Phase 44 carry-forwards

Items deferred from Phase 43 that Phase 44's chat must absorb:

- **L2-37 consumer/scheduler.** Phase 43 ships `applies_after` field declarations; Phase 44 implements Kahn topological-sort scheduler that consumes them (per L2_FUTURE_WORK §11 L2-37 split).
- **L2-39 audit constant.** `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` + capability per D-L2-23; routed to L0_SUBSTRATE_CHAT scope.
- **L2-41 KL retention surface.** `kl.read_at_version` + `kl.retire_version` per D-L2-18; routed to L0_SUBSTRATE_CHAT scope.

---

## §10. Phase 43 carry-forwards to future-phase chats

### §10.1 ADR transcription parity probe as default R1 step 0 (NPB11-META + NPB7-4)

Rounds 6-12 surfaced incremental drift between design-pass drafts (R0 picks seed, R0b derivations, chat opener, PHASE_MAP §4 row) and Accepted ADRs on disk. Pattern: drafts written at point-in-time T1 accumulate small transcription errors when downstream artifacts update at T2 without re-anchoring T1 artifacts.

**Recommendation for future-phase chats:** R1 step 0 = ADR transcription parity check. Grep each design-pass artifact's transcription tables against the source ADR-on-disk; surface drift; correct draft, not ADR.

### §10.2 PHASE_MAP §4 row stale-by-design pattern

`POST_PHASE_38_PHASE_MAP.md §4` Phase 43 row was authored at Chat C plan-authoring closure (2026-06-02 morning); subsequent design passes (R0 + R0b + this chat) updated state. Row text never re-anchored.

**Recommendation:** future-phase R1 includes "PHASE_MAP §4 row parity scan" alongside ADR parity check. PR2 last commit rewrites the row to reflect post-ship reality, not just SHIPPED-status flip.

### §10.3 R0 picks seed audit-count drift (NPB12-3)

R0 picks seed §4 said "8 existing schemas transcribed" but listed 9. R0 picks seed is historical; design log captures the correction. Future-phase chats: count audit before drafting "N existing schemas" claims.

### §10.4 Pre-impl pushback saturation discipline (this ship chat lesson)

Phase 43 ship chat opened with the user requesting multiple rounds of "reanalyze the plan and list your pushbacks with options.... show me your choice" before authorising any execution. Pattern observed:

- **Round 1 (P1-P5):** raised before reading the design log fully — broad concerns about workflow shape (dirty-tree blocker, PR2 size, history hygiene, follow-up budget).
- **Round 2 (Q1-Q5):** raised after reading the design log — concrete buildability violations (Q1: tests/phase_13 exactly-N sentinel; Q2: CLAUDE.md double-flip; Q3-Q5: minor/squash/process).
- **Round 3 (R1-R5):** raised after probing specific code paths — transcription details (R1 export-slate count, R4 file-list omission, R5 mkdocs gate timing, etc.).

By round 3 the pushback signal was clearly diminishing — minor corrections only, no architectural or process reversals. Saturation declared: "Further reanalysis is diminishing returns; impl-time will surface anything else and §9.1 absorbs it per process." User accepted this as the closure point and authorised execution.

**Pattern for future ship chats.** Budget 2-3 pre-impl pushback rounds:
- Round 1: workflow-level concerns (commit ordering, branching, sync points).
- Round 2: design-log-level concerns (buildability, transcription drift, file-list completeness).
- Round 3: probe-level concerns (sentinel test exact-N gates, regex matches against changed strings).

Declare saturation when round-N surfaces only minor/track items with no architectural or process reversals. The pushback budget catches the load-bearing P2 + Q1 buildability violations *before* commit boundaries lock, which is precisely the carry-forward §10.5 names below.

### §10.5 Buildability scan over locked commit boundaries pre-impl (P2 + Q1 lesson)

Design log §6.3 violated its own §117 "each commit must be independently buildable" rule in two places: P2 (consolidate.py retarget vs tests/phase_33 fixture updates at different commits) + Q1 (tests/phase_13 exactly-N dispatch sentinel vs new schema additions at different commits). Both caught at round 2 pushback (Q1) and round 1 pushback (P2) — fixed pre-impl by co-locating test updates with the schema/code changes at the same commit.

**Pattern for future design-pass closures.** Before ratifying PR1/PR2 commit ordering:

1. Identify every "exactly-N" sentinel in the test corpus that the changed schemas/role-set/IRI registry touches (`grep -rn "== <integer>" tests/`).
2. Identify every test that uses fixtures that the changed code-path keys on (`grep -rn "<fixture-name>" tests/`).
3. Check that each such sentinel/fixture is updated at the SAME commit as the code change that breaks it.
4. If not: split-restage the boundary so test updates land with the code change.

A 10-minute grep-pass catches violations that would otherwise surface as cumulative-gate cascade errors (Phase 43: 79 errors + 185 failures from violations that survived the design-log §117 rule check).

### §10.6 Cascade-error root-cause diagnosis pattern (Phase 43 PR2 gate lessons)

Phase 43 ran two PR2 gates with large failure counts that traced to single-line bugs:

- **PR2 gate 1: 79 collection errors.** All shared the message "Phase 15a bootstrap_global _GLOBAL_ROLE_ORDER drifted". Single root cause: module-level `assert frozenset(_GLOBAL_ROLE_ORDER) == _GLOBAL_NAMED_ROLES` in `mindsos_admin/bootstrap.py` fired on every import because the admin-side tuple wasn't bumped to match the knowledge-side frozenset 6→9 expansion. One-line fix landed all 79 errors green.
- **PR2 gate 2: 185 failed + 44 errors.** All shared the message "Role 'learned-parameters' is Local-scoped per ADR-0044". Single root cause: binary scope-rejection in `ensure_global_role_graph` didn't account for dual-scope roles (`pending-promotions` + `learned-parameters` in BOTH `_GLOBAL_NAMED_ROLES` AND `_LOCAL_NAMED_ROLES`). Introduced `_GLOBAL_ONLY_ROLES` + `_LOCAL_ONLY_ROLES` set-difference helpers; one-commit fix resolved the cascade.

**Pattern for future ship-chat gates.** When a gate surfaces a large failure count, look at the **error/failure message text** before the test names. Identical or near-identical messages across many tests almost always trace to a single root cause — typically a module-level invariant, sentinel test, or fixture pattern that the cumulative change broke once. Diagnose root cause first; fix is often single-line. Distinguish from genuine multi-cause failures (different messages per test) which require per-test investigation.

---

## §11. Risk notes for tester ship pass

### §11.1 2-PR sync triples Mac/Linux coupling points

Phase 39 ran one cumulative gate (Mac → Linux → Mac sync once). Phase 43 runs two cumulative gates on `phase-43` branch (post-PR1 + post-PR2) + final-squash gate-free per NPB14-1. Three sync points instead of one. Temporal-coupling risk increases.

**Tester runbook:**

1. Mac: complete PR1 commit set; push to phase-43 branch.
2. Linux: pull phase-43; run `docker compose run --rm mindsos-test pytest tests/`.
3. Linux: report green or follow-up commits 5b/5c to Mac.
4. Mac: commit follow-ups (or proceed if green).
5. Mac: stack PR2 commits on phase-43 branch.
6. Linux: pull phase-43; run cumulative gate.
7. Linux: report green; OR follow-up commits to Mac.
8. Mac: squash-merge phase-43 to main; push main.
9. Linux: pull main (post-squash).
10. Linux: `mindsos confirm-phase --phase 43 --notes-file notes-phase-43.md` from post-squash main per §9.5.
11. Linux: commit CONFIRMED.md + notes; push.
12. Mac: tag `phase-43-confirmed` at squash-merge commit; push tag.

### §11.2 Parallel-rail collision on `identifiers.py` (currently dormant)

Per POST_PHASE_38 §1 reading-list discipline (PB-Z): known collision surface `identifiers.py` (Phase 39 + 40). Phase 40 (Rail B X1) adds REALM_* constants on `identifiers.py`. Phase 43 PR2 adds 4 ROLE_* constants + IRI builders + prefixes + tuple-key registrations on same file.

If Phase 40 ships during Phase 43's PR1/PR2 window: rebase phase-43 branch + re-resolve conflicts. Currently Phase 40 hasn't started; risk dormant.

### §11.3 Cumulative gate timeline doubles vs Phase 39

Two cumulative gates instead of one (NPB10-3) + potential 5b/5c follow-up commits per PR. Budget time accordingly. Phase 39 cumulative gate was within `_CONFIRM_PHASE_TIMEOUT_SECONDS = 2700` (45 min); Phase 43 individual gates should also fit.

### §11.4 Phase 43 test suite count ~17 files

PR1: 5 test files. PR2: 9 test files + tests/phase_13/ extension + tests/phase_33/ updates. Total: ~17 test files contributing to tests/phase_43/ + scattered extensions. Phase 39 ran 7 files; Phase 43 is 2-3× the test surface. Estimated cumulative passes post-Phase-43: ~3620-3750 (Phase 39 ended at 3501).

---

## §12. Closing

Design pass closed 2026-06-03. R1 + R2 + R3 saturated. Impl execution can proceed.

The chat that produced this design pass tracked 18 rounds of pushback under skeptical-reviewer discipline. Round counts include reconsiders, reversals, and probe-resolved findings. Saturation gate per Chat C: three consecutive reversal-free rounds = ready to ship. Met at R1 round 16, R2 round 18, R3 round 1.

PHASE_43_CONFIRMED.md will be authored by tester via `mindsos confirm-phase --phase 43 --notes-file notes-phase-43.md` post-squash-merge. PHASE_44_NEXT_CHAT_PROMPT.md (PR2 commit 6) carries Phase 44's seed.

---

*End of PHASE_43_DESIGN_LOG.md. §1-§8 capture design pass closure 2026-06-03; §9 reserved for impl + tester ship pass amendments. Last updated: 2026-06-03.*
