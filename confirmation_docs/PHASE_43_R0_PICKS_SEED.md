# Phase 43 — R0 Picks Seed

> **Source:** Pre-R0 design-pass closure 2026-06-02 (this chat).
> **Status:** Seed for the chat that opens Phase 43 post-Phase-39-confirm.
> **Saturation:** 4 rounds of pre-R0 pushback + R0a probes + N-now-C resolution. R0b deferred to fresh chat.
> **Replaces:** Initial PB-43-1…10 defaults in `PHASE_43_NEXT_CHAT_PROMPT.md §3`.

This file captures every locked pick, every drop, and every probe-resolved finding from the pre-R0 design pass so the next Phase 43 chat does not re-litigate. Load this **alongside** `PHASE_43_NEXT_CHAT_PROMPT.md` — the prompt is the spec; this is the carry-forward picks.

---

## §0. Hard prerequisites (block Phase 43 branch creation)

1. **S9 — corpus committed to `main`.** See `confirmation_docs/A0_HOUSEKEEPING_COMMIT_CHECKLIST.md`. Until A0-1…A0-4 land, every probe in `PHASE_43_NEXT_CHAT_PROMPT.md §3` reads working-tree state, not `main`.
2. **Phase 39 confirmed.** `phase-39-confirmed` tag on `main`. Includes the §am-4 surgery (S4) — Phase 39 impl loop owns this; Phase 43 does not absorb. Includes the rename of `consolidate.py` to import `ROLE_EPISODIC_MEMORIES` (Phase 39 PB-3 single-line touch).
3. **Working tree clean** post-A0 commits and post-Phase-39 ship.

If any of 1-3 fail, Phase 43 R0 reading-list assumptions break.

---

## §1. Locked R0 picks (carry into R0b)

### §1.1 Original PB-43-1…10 slate

| PB | Pick | Rationale |
|---|---|---|
| **PB-43-1** | **Two-PR split on `phase-43` branch, single squash to `main`** | Validator surface lands first; PR2 relies on it. Single tag preserved (N1). |
| **PB-43-2** | **Transcribe ADR-0153 §1 table** | Disciplines are pre-assigned per role-graph; audit becomes mechanical (L-shrink-3). |
| **PB-43-3** | **Per-`*_PROPS` constants + partition invariant in `validate_mutation_discipline`** | Cheapest correctness gain; enforces `CONTENT ∪ METADATA == PROPS` (N3 partition). |
| **PB-43-4** | **`applies_after: frozenset[IRI]` explicit-required + author edges** | Field ships with real content; not dead-on-arrival. Edges derived from D-L2-11/13/14/15/17 + D-B47 at R0b. |
| **PB-43-5** | **Drop `USED_CAPACITY` / `PART_OF_PIPELINE` permanently; reserve schema slot + ADR-0152 note** | Phase 47/48 surfaces measurable cost or doesn't. Re-add is additive change. |
| **PB-43-6** | **`L2Schema(Schema)` subclass in `mindsos_knowledge/schemas/_base.py`** | N4 probe clean (zero `isinstance(.., Schema)` / `_SCHEMA_REGISTRY` / `Schema.__name__` hits). Subclass safe. |
| **PB-43-7** | Mechanical; add Phase 41 diff to PB-Z reading-list | Phase 40+41+42 all touch identifiers.py / KL boundaries. |
| **PB-43-8** | Confirm scope D-L2-17 + Chat B D-B47 | Verify cascade unchanged since 2026-05-31. |
| **PB-43-9** | **Retarget `consolidate.py` `type_="Memory"` → `type_="Episode"` at Phase 43** | Phase 42 collision is mechanical-different-line (`context.kl` accessor vs `type_=` kwarg). Collapses Phase 39/42/48 triple-touch to Phase 43/48 double-touch. |
| **PB-43-10** | **Detector form `tools/check_phase_43_confidence_state.py`** | v1 production has no `confidence` Local-Pipeline records; real migrator is dead code. Phase 39 PB-8 precedent. **Scope: `promoted-pipelines` only** (N-now-C — task_patterns.confidence kept). |

### §1.2 Process locks

| # | Pick |
|---|---|
| **N1** | Two PRs on `phase-43` branch; single squash to `main`; single phase tag. |
| **N3** | Both load-time + write-time `mutation_discipline` enforcement at Phase 43. KL bootstrap dispatch table (load-time); KLWriteHandle write-path body (write-time, second meaningful body of the Phase 33 stub). |
| **C-β** | `mutation_discipline` enforced at **KL bootstrap**, not L4 startup. Closes the zombie-field gap before Phase 46. |
| **C-δ** | PB-Z reading-list includes Phase 39 + 40 + 41 + 42 diffs at branch-creation time. |
| **P-A** | R0 split into R0a (probes + raw findings) + R0b (derivations + slate). R0a closed 2026-06-02. R0b runs in next chat. |
| **P-B** | `MAINTENANCE_CHAT` is the destination if any unrouted L2 items surface — **PROBE FOUND NONE; route unused** (L-die-2). |
| **P-C** | ADR-0153 in-place edit pre-ratification — **MOOT** (S2/L-die-1; ADRs already Accepted, all 6 disciplines enumerated). |
| **P-D** | N4 tri-state pre-commit ≤20 LOC consumer-fix threshold — **MOOT** (probe found zero consumers; clean subclass). |
| **P-E** | ADR-0151 + ADR-0153 language-neutral on placement — **MOOT** (ADRs already Accepted; placement decided per N4 = subclass; text references `Schema.mutation_discipline` which now means L2Schema-inherited Schema field). Verify text reads correctly under L2Schema(Schema). |

### §1.3 Storage placement (P3)

`storage_mode` (ADR-0151) and `mutation_discipline` (ADR-0153) **both live on `L2Schema(Schema)`**. Single placement; no L1/L2 split. PR1 audit covers both fields across 8 existing schemas + transcribes from ADR-0153 §1 table.

### §1.4 Resolved probe findings

| Finding | Resolution |
|---|---|
| **R0a-1 / S1** | Phase 39 NOT shipped. Phase 43 R0b proceeds; branch deferred. |
| **R0a-2 / S4** | ADR-0150 §am-4 still 4-rows. Surgery is Phase 39's job. |
| **R0a-3 / S2** | ADRs 0151/52/53 already `status: Accepted`. C-γ dropped. |
| **R0a-4 / S3** | **SIX disciplines on disk**, not 5: `immutable_successor`, `append_only_with_lazy_inline`, `mutable_with_retention`, `audit_only_after_settled`, `admin_authored`, `append_only`. ADR-0153 §1 table assigns each role-graph. |
| **R0a-5 / S5 / N-now-C** | `confidence` in two files. **promoted-pipelines: DROP (PR2 + detector).** **task-patterns: KEEP** (ADR-0152 §2 lists `confidence` as metadata in flat 9-field). |
| **R0a-6** | Net-new fields clean (zero pre-existence). |
| **R0a-7** | Bootstrap = two module-level functions; no `applies_after`; 14-step net-new. |
| **R0a-8** | Manifest `phase = "38"`; PR2 bumps to `"43"` after Phase 39 ship. Also `mindsos_instances` missing from `[mindsos] packages` — Stream A A8. |
| **R0a-9** | `_IRI_BUILDERS: dict[str, object]` single-key shape. Phase 39 tuple-key change not on disk. PR2 adds 4 entries after Phase 39 ship. |
| **R0a-10 / N4** | **L2Schema(Schema) subclass safe** — zero consumer cascade. |
| **R0a-11 / N6** | Phase 42 touches `consolidate.py` (`context.kl` accessor migration). PB-43-9 collision low; different lines. |
| **R0a-12 / C-α** | L2_FUTURE_WORK §11 routes L2-29/30/31/32/33/37/40 to Phase 43 explicitly. **A6 routed to Stream A or Phase 44, NOT Phase 43.** L2-38 (HAS_STEP) routed to Phase 42. |

---

## §2. Dropped picks (do NOT re-litigate)

| Drop | Reason |
|---|---|
| **C-γ** | ADRs 0151/52/53 already Accepted on disk (R0a-3 / S2). No flip to defer. |
| **P1** | ADR-0153 enumerates 6 disciplines explicitly (R0a-4 / S3). No probe gap. |
| **P-meta** | L2_FUTURE_WORK §11 has every L2 carry-forward routed (R0a-12). No items need a maintenance slot. |
| **A6 from Phase 43 scope** | L2_FUTURE_WORK §11 routes to Stream A or Phase 44. Prompt §1 step 5 is stale. |

---

## §3. R0b agenda (fresh chat picks this up)

After §0 prereqs satisfied:

1. **Author `applies_after` edge set.** Derive from D-L2-11/13/14/15/17 + D-B47. Suggested edges (verify at R0b):
   - `concepts` ← `ontology`, `lexicon`
   - `alignment:<a>:<b>` ← `<a>`, `<b>`
   - `task-patterns` ← (independent at bootstrap; runtime deps via L3 pipeline-finder index)
   - `promoted-pipelines` ← `task-patterns` (`paired_pipelines` back-refs)
   - `episodic_memories` ← `task-patterns` (`memory_contains_episode` references episodes by task-pattern)
   - `learned-parameters` ← (independent)
   - `parameter-staging` ← `learned-parameters` (staging targets the promotion store)
   - `pending-promotions` ← `promoted-pipelines`, `learned-parameters` (shepherds both)
   - `capacity-gaps` ← (independent; populated from L3 dont-know returns)
   - `problem-trace` ← (independent)
   - `capacity-state` ← (independent)
2. **Build PR1/PR2 module-touch list with LOC estimates.** Verify against POST_PHASE_38 §4 Phase 43 row "Modules touched."
3. **Draft ADR-0150 §am-5 text** (4 new role-graphs + exclusion list migrated from §am-4 per Phase 39 PB-R2-B). Coordinate timing: §am-5 cannot be written until Phase 39 §am-4 surgery lands.
4. **Draft ADR-0094 §am-1 text** (drop `confidence` from `promoted-pipelines` only; `task-patterns.confidence` retained per ADR-0152 §2).
5. **Sketch `L2Schema(Schema)` subclass surface.** Module: `mindsos_knowledge/schemas/_base.py`. Fields: `mutation_discipline: Discipline`, `storage_mode: StorageMode`. Migration: all 12 schema builders return `L2Schema`, not `Schema`.
6. **Update `PHASE_43_NEXT_CHAT_PROMPT.md`** to reflect drops + Phase-39-prereq framing + this seed file as primary R0 input.
7. **Revise test surface estimate** (~14-18 files per P5 — but tests-per-discipline = parametric single file). Surface to tester ship-shape.

R0b output: feed into R1 impl-locks.

---

## §4. Locked PR shapes (rough)

### PR1 — type system + validator + ADRs

- `mindsos_knowledge/schemas/_base.py` (NEW) — `L2Schema(Schema)` + `Discipline` enum (6 values) + `StorageMode` enum (3 values per ADR-0151).
- `mindsos_knowledge/validators.py` — `validate_mutation_discipline` + partition invariant.
- `mindsos_knowledge/exceptions.py` — `MutationDisciplineError(ValueError)`.
- **8 existing schemas transcribed** from ADR-0153 §1 table + ADR-0151:
  - `ontology.py`, `lexicon.py`, `concepts.py`, `alignment.py` → `admin_authored`
  - `promoted_pipelines.py` → `immutable_successor` + CONTENT/METADATA partition
  - `task_patterns.py` → `immutable_successor` + CONTENT/METADATA partition (keeps `confidence` as metadata)
  - `memories.py` → `append_only_with_lazy_inline` + CONTENT/METADATA partition (renamed in Phase 39 to `episodic_memories.py`)
  - `problem_trace.py` → `append_only`
  - `capacity_state.py` → `mutable_with_retention`
- `docs/decisions/adr/0150-l2-knowledge-lifecycle.md` §am-5 authored.
- `docs/decisions/adr/0094-confidence-pipeline-level.md` §am-1 authored.
- `tests/phase_43/test_l2schema_subclass.py`, `test_validate_mutation_discipline.py`, `test_partition_invariant.py`, `test_adr_amendment_sentinels.py`.

### PR2 — schemas + bootstrap + retarget + migrator

- `mindsos_knowledge/schemas/parameter_staging.py` (NEW).
- `mindsos_knowledge/schemas/pending_promotions.py` (NEW).
- `mindsos_knowledge/schemas/capacity_gaps.py` (NEW).
- `mindsos_knowledge/schemas/learned_parameters.py` (NEW).
- `mindsos_knowledge/schemas/episodic_memories.py` (Phase 39 skeleton finalized: Episode + Memory + `memory_contains_episode` IntergraphEdgeType + discipline declared).
- `mindsos_knowledge/identifiers.py` — 4 new `ROLE_*` constants, 4 new IRI builders, 4 prefix entries, 4 `_KINDS_PER_ROLE` rows, 4 `_IRI_BUILDERS` registrations (tuple-key shape inherited from Phase 39).
- `mindsos_knowledge/bootstrap.py` — 14-step topological order via `applies_after` consumption.
- `mindsos_knowledge/knowledge_layer.py` — bootstrap discipline dispatch table.
- `mindsos_knowledge/write_handle.py` — `KLWriteHandle` write-path discipline enforcement body (N3).
- `mindsos_capacity/builtins/consolidate.py` — `type_="Memory"` → `type_="Episode"` (PB-43-9 retarget; one line).
- `manifest.toml` — `phase = "39"` → `"43"`.
- `tools/check_phase_43_confidence_state.py` (NEW; detector; promoted-pipelines only).
- 10-14 test files in `tests/phase_43/`.

---

## §5. Out of scope (do NOT absorb)

- Phase 39 §am-4 surgery (S4) — Phase 39 owns.
- Stream A items A1-A8 (separate maintenance track).
- `task_patterns.confidence` removal — kept per ADR-0152 §2.
- L0 substrate (Phase 44).
- Dream family (Phase 45).
- `HAS_STEP` re-litigation — locked at Phase 13 form per L2-38 → Phase 42.
- L4/L5 substrate (Phases 46-48).
- WSD / FOL / DWF chat scope.
- `mindsos_instances` manifest entry — Stream A A8.

---

## §6. Reading-list for next chat

Required, in order:

1. **This file (`PHASE_43_R0_PICKS_SEED.md`)** — load picks; do not re-litigate dropped items.
2. `PHASE_43_NEXT_CHAT_PROMPT.md` — spec.
3. `A0_HOUSEKEEPING_COMMIT_CHECKLIST.md` — verify A0 landed.
4. `PHASE_39_CONFIRMED.md` + `PHASE_39_DESIGN_LOG.md` — confirm Phase 39 ship metadata.
5. `POST_PHASE_38_PHASE_MAP.md §4 Phase 43 row` — modules touched, tests, pass criterion.
6. `L2_CHAT_DECISIONS.md` D-L2-3/4/5/6/7/10/11/13/14/15/17/19/22/24/26 — settled L2 picks.
7. ADRs on disk: 0094, 0150, 0151, 0152, 0153, 0154.
8. `HANDOFF.md` §2.2 + §3.1.7 + §3.1.8.
9. Phase 39 ship diffs (PB-Z): `identifiers.py`, `episodic_memories.py`, `consolidate.py`.
10. Phase 40 + 41 + 42 ship diffs if those rails landed first.

Optional: `STREAM_A_BACKLOG.md` for context on parallel maintenance.

---

*End of PHASE_43_R0_PICKS_SEED.md. Last updated 2026-06-02 (this chat closure). Replaces the PB-43-1…10 defaults section of PHASE_43_NEXT_CHAT_PROMPT.md §3.*
