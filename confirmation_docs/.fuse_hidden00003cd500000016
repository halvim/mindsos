# L2 Chat — Decisions Log

**Purpose.** Per-decision settlement record for the L2 chat (D47 + L2-1 through L2-27 + Chat A/B cascades). Chat C plan-authoring, WSD installation, DWF installation, and L1/L3 reframe chats inherit from here.

**Format per decision:** ID, status, pick, rationale, alternatives considered, downstream cascades.

**Saturation:** picks below survived a single skeptical reanalysis pass (PB-A through PB-H). No reversals after pass.

**Inheritance precedence (downstream-stamped):** L2_CHAT_DECISIONS > CHAT_B_DECISIONS > CHAT_A_DECISIONS for any L2-touching decision. Items routed *out* of this chat (L1/L3 reframe, FOL, DWF, WSD installation) stay open.

---

## R1 — Naming + scope reconciliation

### D-L2-1 — Alignment role-graph canonical form

**Pick.** `alignment:<a>:<b>` where `<a>` and `<b>` are sorted role names. Colon is the separator.

**Supersedes:** the 3 inconsistent forms shipped at Phase 36 close — `identifiers.py:303` `alignment:<a><->b>`; `identifiers.py:297` docstring `alignment:<a>-<b>`; ADR-0150 §amendment-1 + `bootstrap.py:8,128` `alignment:<a>:<b>`; Phase 36 validator tests `alignment:<a>-<b>`.

**Rationale.** Three forms in flight; pick the one that is (a) already canonical in ADR-0150 §amendment-1, (b) already canonical in `bootstrap.py` (the load-bearing code path), and (c) unambiguous when role names contain hyphens. The single-dash form `alignment:promoted-pipelines-task-patterns` is **structurally ambiguous** because `promoted-pipelines` and `task-patterns` are both legal role names containing hyphens. Colon is a parser-reserved separator already used in every other IRI surface, and ADR-0150 §amendment-1 already commits to it; the `<->` arrow + dash variants are scrubbed.

**Alternatives considered.**
- `alignment:<a><->b>` (current `identifiers.py:303`) — pretty in prose, ugly in code; arrow has no parser semantics.
- `alignment:<a>-<b>` (current Phase 36 tests + docstring) — ambiguous with hyphenated role names.

**Cascade.**
- `mindsos_knowledge/identifiers.py` `alignment_role()` body fixed to `f"alignment:{a}:{b}"`; docstring rewritten.
- Phase 36 validator tests updated (`tests/phase_36/test_validators.py`).
- DWF installation chat **inherits this pick verbatim**; if DWF surfaces use-case pressure for an alternative, it amends this decision via `L2_CHAT_DECISIONS amendment` rather than reopening at install time.

### D-L2-2 — `sense-correlations` withdrawal

**Pick.** **Withdrawn as standalone L2 role-graph.** Empirical sense edges live in the lexicon role-graph's `empirical` layer (per WSD `coordinated_change_L2_lexicon_layers_and_role_graphs.md` §3 + §7).

**Reconciliation with Chat A R3 ALS subsystem #8 (`sense-correlations`, Track A).** The subsystem name is a *label* for the parameter set; its `parameter_set_iri` points at lexicon edges in the `empirical` layer, not at a separate role-graph. Naming preserved for ALS-side continuity; no L2 role-graph dispatch entry.

**Rationale.** WSD's withdrawal is the source-of-truth design (empirical sense data is structurally lexicon-resident — co-occurrences are edges between sense nodes that already live in lexicon). Chat A R3 Q4 said "ship both `sense-correlations` + `learned-parameters` v1" inheriting stale L2 §12 framing; this decision overrides via L2's role as schema-dispatch owner. ALS continues to learn against the lexicon empirical layer under the same subsystem name.

**Cascade.**
- L4 design notes lose `sense-correlations` reference (see WSD §7 action items).
- ADR-0150 §amendment-4 does **not** add `sense-correlations` to the role-set.
- ALS subsystem #8 retargets `parameter_set_iri` to lexicon empirical-layer parameter key (concrete IRI = WSD installation chat work).
- L2-1 closed.

---

## R2 — Per-role-graph mutation discipline + per-field content/metadata (PB-A + PB-12 + D47)

### D-L2-3 — Per-role-graph `mutation_discipline` field on Schema

**Pick.** Every L2 role-graph schema declares a `mutation_discipline` at build time. v1 enum:

| Discipline | Semantics | Used by |
|---|---|---|
| `immutable_successor` | Content is write-once; updates mint successor IRIs. Status/lifecycle fields excluded (per D-L2-4). | `promoted-pipelines`, `task-patterns`, `world-axioms` (when WSD chat ships it) |
| `append_only_with_lazy_inline` | External writes append-only; internal mutation only via lazy inline-on-retire (Chat B D-B17 + D'1). | `episodic_memories` |
| `mutable_with_retention` | Rows mutable; TTL-pruned per admin policy. | `parameter-staging`, `capacity-state`, `capacity-gaps`, `learned-parameters` (Local) |
| `audit_only_after_settled` | Mutable until `status ∈ {applied, rejected}`, then frozen. | `pending-promotions` |
| `admin_authored` | Mutable only via admin importer or admin tooling; no L4/L3 write path. | `ontology`, `lexicon`, `concepts`, `alignment:*`, `learned-parameters` (Global) |
| `append_only` | All fields append-only; no retention; no successor; no lazy inline. | `problem-trace` |

**Phase 43 cleanup note (PR1 commit 7 — ADR-0153 §1 6-value reconciliation):** Original L2-chat closure rendered 5 disciplines; `append_only` was added at ADR-0153 §1 ratification per R0a-4 / S3 (the row for `problem-trace`). Also: `capacity-gaps` was originally tabled under `admin_authored` here; ADR-0152 §5 + ADR-0153 §1 lock it as `mutable_with_retention` (admin actions mutate status; retention policy per admin tuning).

**L4 startup invariant.** `KnowledgeLayer.bootstrap()` walks installed role-graphs; each Schema reports its `mutation_discipline`; L4 builds a runtime dispatch table that enforces the discipline at write time (write attempt against `immutable_successor` content field → `MutationDisciplineError`).

**Rationale.** D47's binary "mutable-vs-immutable" framing was always too coarse — `parameter-staging` needs mutability for evidence pruning; `pending-promotions` needs a settled-frozen transition; `episodic_memories` needs lazy inline. A per-role-graph discipline matches the actual ground-truth shape and lets each role-graph evolve independently. Aligns with the existing "L3 reachability invariant" enforcement pattern (Chat A R3 D51 generalized).

**Alternatives considered.**
- **A2 — single global D47 pick** (`immutable_successor` everywhere): incompatible with parameter-staging. Forces special-casing.
- **A3 — docstring discipline only**: unenforceable; D47's whole point was preventing drift.

**Cascade.**
- **Phase 43 ship reversed L1 placement to L2Schema(Schema) subclass per ADR-0153 §amendment-1.** `mindsos_knowledge.schemas._base.L2Schema(Schema)` gains `mutation_discipline: Discipline` — required at construction (no backward-compat default; L2 schemas declare explicitly). `mindsos_core.Schema` stays primitive; no L2 vocabulary on L1. R0 N4 probe found zero L1 consumers of the discipline field; ADR-0010 import-direction symmetry preserved. (Original closure framing in this cascade said "mindsos_core.Schema gains" — that L1 placement was the closure's correctness gap, reversed in place per Phase 43 R0 PB-43-6 + R0a-10 / N4.)
- New L2 validator `validate_mutation_discipline` added to `mindsos_knowledge/validators.py` (post-Phase-36 carry-forward).
- New exception `MutationDisciplineError` in `mindsos_knowledge.exceptions` (multi-inherits `KnowledgeError` + `ValueError` per ADR-0153 §5).
- Each Phase 13 shipped schema gets a one-line amendment in its `build_*_schema(strict)` body to declare its discipline (`promoted-pipelines` → `immutable_successor`, `task-patterns` → `immutable_successor`, `episodic_memories` (post-Phase-39 rename of `memories`) → `append_only_with_lazy_inline`, `capacity-state` → `mutable_with_retention`, `problem-trace` → `append_only`, `ontology`/`lexicon`/`concepts`/`alignment:*` → `admin_authored`).
- L2-27 / D47 closed under this framing (immutable-with-successor-IDs holds for the role-graphs Chat A had in scope; per-role-graph discipline generalizes).

### D-L2-4 — Per-field `content` vs `metadata` declaration

**Pick.** For role-graphs with discipline `immutable_successor` or `append_only_with_lazy_inline`, every node/edge type declares per-field membership in `content_fields: frozenset[str]` or `metadata_fields: frozenset[str]`. Validator enforces.

**Promoted-pipelines fields:**
- **Content (immutable; successor required for change):** `pipeline_name`, `edge_sequence`, `start_ds`, `end_ds`, `expression_metadata`.
- **Metadata (mutable in place):** `status`, `n_runs`, `outcome_history`, `provenance` (append-only sub-record), `quarantine_threshold`, `created_at`, `tested_at`, `activated_at`, `quarantined_at`, `quarantined_by`, `retired_at`.

**Phase 43 cleanup note (PR1 commit 7 — D-L2-7 paired_pipelines staleness reconciliation):** Original closure listed `paired_pipelines` under Pipeline metadata as "reverse-cached references". D-L2-7 (below in this doc) subsequently eliminated the pipeline-side cache entirely — `paired_pipelines` lives only on `task-patterns` (source-of-truth per PB-R3-21). Phase-2 pipeline lookup walks task-patterns via L3 pipeline-finder, which maintains its own runtime index. Per ADR-0152 §1, `pipeline_name` is in content (originally missing) + `quarantine_threshold` is in metadata (originally missing); `confidence` dropped per ADR-0094 §am-1.

**Task-patterns fields:**
- **Content:** `pattern_name`, `task_shape_recognizer`, `sufficient_predicate_iri`, `domain`, `paired_pipelines` (this IS source-of-truth per PB-R3-21).
- **Metadata:** `relevant_hints` (admin-tunable post-author), `mapping_confidence_threshold` (ALS-learnable per subsystem #4), `n_observations`, `confidence`, `provenance`, `routing_override` (v1.5).

**Episode (episodic_memories) fields:**
- **Content (external-append-only):** `task_input_ref`, `mm_root_ref`, `task_pattern_iri`, `outcome_classification`, `consolidated_at`.
- **Metadata-via-lazy-inline (Chat B D-B17 carve-out):** content reachable through `mm_root_ref` may be replaced by inline snapshot when a referenced L2/L3 version retires. Reference-stable; content-may-snapshot. Explicitly documented as **not** a violation of content-immutability — see D-L2-5.

**Rationale.** D47 was unenforceable without this. Without per-field labels, "successor on change" applies to nothing in particular and every write needs a per-call judgment call. With the labels, mutation-discipline validator is a one-pass field-mask check.

**Cascade.**
- Phase 13 shipped schemas amended to declare `CONTENT_FIELDS` / `METADATA_FIELDS` frozensets alongside the existing `*_PROPS` constants.
- Validator `validate_mutation_discipline` reads schema + write payload; rejects content-field writes on `immutable_successor` schemas.

### D-L2-5 — Reference-stability vs content-immutability framing

**Pick.** The architectural commitment is **reference-stability**, not strict content-immutability. Storage content may change via the discipline-permitted mechanism (lazy inline-on-retire for episodes; never for promoted-pipelines content fields). Logical reference identity (IRI + version tuple) does not change.

**Wording lock.** ADR text + design docs use "reference-stable, content-may-snapshot-on-retire" for `episodic_memories`. Do not use "immutable" without qualifier; it overstates the guarantee and confuses lazy-inline.

**Cascade.** Chat B framing of "Episode immutability invariant" gets a docs cross-reference noting D-L2-5 supersedes the wording without changing the picks.

---

## R3 — Promoted-pipelines schema v2 (L2-25 partial lock per PB-E)

### D-L2-6 — Promoted-pipelines schema v2 fields + status enum

**Pick.** Schema v2 lands with status + lifecycle metadata + paired-pipelines back-references **now**; `HAS_STEP` + `PipelineStep` internal structure deferred until L1/L3 reframe chat closes D38 (capacities-as-hyperedges).

**v2 Pipeline node-type properties:**

| Field | Type | Discipline | Source |
|---|---|---|---|
| `pipeline_name` | str | content | Chat A R3 |
| `edge_sequence` | list[capacity_edge_id] | content (immutable per WSD §A.2) | Chat A R3 |
| `start_ds` | datastate_iri | content (derivable) | Chat A R3 |
| `end_ds` | datastate_iri | content (derivable) | Chat A R3 |
| `expression_metadata` | dict | content | Chat A R3 |
| `paired_pipelines` | **REMOVED from pipeline-side** | — | D-L2-7 cache elimination |
| `serves_task_types` | **REMOVED** | — | D-L2-7 cache elimination |
| `status` | Literal["draft","tested","active","quarantined","retired"] | metadata | Chat A R3 PB-R3-22 |
| `n_runs` | int | metadata | Chat A R3 |
| `outcome_history` | list[OutcomeRecord] | metadata (append-only sub-record) | WSD §A.2 |
| `provenance` | ProvenanceRecord | metadata (append-only) | WSD `pending_adrs` §A.7 |
| `quarantine_threshold` | float (default 0.85) | metadata (admin-tunable) | Chat A R3 PB-R3-31 |
| `created_at` / `tested_at` / `activated_at` / `quarantined_at` / `retired_at` | timestamp | metadata | timestamps |
| `quarantined_by` | Literal["system","admin"] | metadata | Chat A R3 PB-R3-31 |

**`confidence` field DROPPED** per ADR-0094 amendment (see D-L2-15). v1 carry-forward: any shipped Local-Pipeline records carrying `confidence` get the field stripped by a one-shot maintenance migrator at v2 schema deploy.

**Deferred to L1/L3 reframe close:** `HAS_STEP` edge shape + `PipelineStep` node-type. If reframe lands capacities-as-hyperedges, `HAS_STEP` becomes hyperedge ordering and `PipelineStep` disappears. If reframe rejects, current shape stands.

**Rationale (PB-E).** WSD installation chat needs status + paired-pipelines source-of-truth now (Phase 2 routing). Step-shape isn't needed until pipeline execution lands (much later in Chat C's phase map). Locking dual schemas wastes review surface.

### D-L2-7 — `serves_task_types` cache eliminated (PB-B)

**Pick.** Pipelines do **not** store reverse references to task-patterns. Task-pattern's `paired_pipelines` is the **sole** source of truth. Phase-2 pipeline lookup walks task-patterns via L3 pipeline-finder, which builds its own runtime index from the task-patterns role-graph (admin-tunable cache TTL).

**Rationale.** Cache-invalidation problem dissolves; one truth; no validator/test surface for bidirectional consistency. Phase-2 lookup is L3's job per Chat A strict line; the index lives in L3, not L2.

**Alternatives considered.**
- **B2 cache + write-through** — bidirectional write coupling; harder to evolve as schemas grow.
- **B3 cache + rebuild-on-startup-only** — transient drift in long sessions; not safe under live writes.

**Cascade.**
- L3 pipeline-finder gains internal task-pattern index (Chat A R3 cascade L3-40 absorbs this; shape-indexing covers both task-shape and serves-task-type lookup).
- PB-R3-21's "integrity check at startup" reduces to walk-and-verify on task-patterns side only.

### D-L2-8 — Status filter at read (PB-C)

**Pick.** L2 read APIs return all status values; L3 pipeline-finder applies status discipline. Default filter: `status="active"`. Dream pipelines may target `status="quarantined"` explicitly.

**Rationale.** Matches Chat A strict line (L4 substrate / L3 decisions); L2 stays dumb-store. Lets `dream.retry` rerun quarantined pipelines for re-validation without an L2 special case.

**Cascade.**
- L3 pipeline-finder signature gains optional `status_in: frozenset[str] = frozenset({"active"})`.
- ADR-0094 amendment notes this filter (see D-L2-15).

### D-L2-9 — Status transition authority (Chat A R3 PB-R3-31 confirmed)

**Pick.** Confirmed as-shipped from Chat A:
- `draft → tested`: admin.
- `tested → active`: admin (promotion).
- `active → quarantined`: **system** (on failure with `mapping_confidence > quarantine_threshold`).
- `quarantined → active`: admin (reinstate).
- `quarantined → retired`: admin (delete).

Status field mutates in place under D-L2-3 `immutable_successor` discipline because it's *metadata*, per D-L2-4 field labels. No successor IRI mint on status transition.

---

## R4 — Task-patterns schema v2 (L2-26)

### D-L2-10 — Flat 13-field schema; no config split (chat closure framed as "9-field"; canonical count per ADR-0152 §2 is 13 = 11 listed below + 2 timestamps)

**Phase 43 cleanup note (PR1 commit 7 — D-L2-10 naming nit reconciliation):** Original closure named this decision "9-field" but the table below lists 11 fields; ADR-0152 §2 ratified the canonical 13-field count by adding `created_at` + `last_updated_at` timestamps (metadata partition). Header retained "13-field" label for forward-reading clarity; original "9-field" framing preserved as historical record. See ADR-0152 §2 + design log §3 NPB12-3 (R0 picks seed audit-count drift).

**Pick.** `TaskPattern` node type carries all R3+R5 additions inline (flat):

| Field | Type | Discipline | Source |
|---|---|---|---|
| `pattern_name` | str | content | Phase 13 |
| `task_shape_recognizer` | dict (declarative) | content | Phase 13 |
| `sufficient_predicate_iri` | IRI | content | Chat A R3 |
| `domain` | str | content | Chat A R5 D43 |
| `paired_pipelines` | list[IRI] | content (source-of-truth per PB-R3-21) | Chat A R3 |
| `relevant_hints` | list[IRI] | metadata (admin-tunable) | Chat A R3 Method δ |
| `mapping_confidence_threshold` | float | metadata (ALS subsystem #4 refines) | Chat A R3 |
| `n_observations` | int | metadata | Phase 13 |
| `confidence` | float | metadata | Phase 13 |
| `provenance` | ProvenanceRecord | metadata (append-only) | WSD `pending_adrs` §A.7 |
| `routing_override` | Optional[dict] | metadata (v1.5) | PB-R3-32 |

Plus existing edges: `DECOMPOSES_INTO`, `PREREQUISITE_OF` (Phase 13 — unchanged).

**Rationale.** Three options were on the table — flat-9, two-type split (`TaskPattern` + `TaskPatternConfig`), normalized via `config_ref`. Normalization (`config_ref`) costs an extra L2 read hop per Phase-1 candidate eval; Phase-1 budget is <50ms per Chat A R3; the hop is real cost. Two-type split adds a schema concept (config-vs-identity) without addressing the underlying growth (the config side keeps growing). Flat wins on perf + simplicity; growth managed by Schema-level discipline (D-L2-4 content/metadata labels).

**Alternatives considered.**
- **Split TaskPattern + TaskPatternConfig** — schema cohesion split for one growth axis; doesn't address future growth.
- **Normalized config_ref** — extra hop kills Phase-1 perf budget.

**Cascade.**
- `mindsos_knowledge/schemas/task_patterns.py` gains the new property frozensets; `*_PROPS` constants amended.
- ALS subsystem #4 `parameter_set_iri` refines `mapping_confidence_threshold`.

---

## R5 — New role-graph schemas (L2-23)

### D-L2-11 — `parameter-staging` schema (Local only)

**Pick.** Node type `StagedEvidence` per WSD `coordinated_change_L2` §6.1. Discipline: `mutable_with_retention`.

**Schema:**
- `parameter_set_iri: str` (opaque — see D-L2-12 on FOL #4)
- `signal_source_iri: IRI` (one of 10 v1 signal sources per Chat B D-B51)
- `target_parameter_iri: str` (opaque sub-key)
- `target_value: float | dict` (JSON-encoded)
- `evidence_pointer: IRI` (XRef to source memory/task — episodic_memories.Episode after rename)
- `signal_weight: float`
- `blame_weight: float` (default 1.0)
- `staged_at: datetime`
- `retention_window_until: datetime` (admin-tunable; default 30 days)

**Edges:** none v1.

**Cascade.**
- New schema file `mindsos_knowledge/schemas/parameter_staging.py`.
- IRI builder `staged_evidence_iri(version, evidence_id)` in `identifiers.py`.
- `_KINDS_PER_ROLE[ROLE_PARAMETER_STAGING] = frozenset({"evidence"})`.
- New role constant `ROLE_PARAMETER_STAGING = "parameter-staging"`.
- ADR-0150 §amendment-4 entry.

### D-L2-12 — `parameter_set_iri` format stays opaque (PB-R3-2 confirmed; L2-Q1 resolved)

**Pick.** **Stay opaque per Chat A.** L2 commits no internal structure to `parameter_set_iri`. If FOL chat picks the 3-way split (D28), `parameter_set_iri` body can encode the role-graph routing without L2 schema rewrite.

**Rationale.** PB-3 in R0 considered constraining the format; reanalysis dropped it. Opaque + Chat A's v2-compatible framing is good enough. Format constraint would presume FOL's split shape; FOL hasn't picked.

### D-L2-13 — `pending-promotions` schema (Local + Global)

**Pick.** Node type `PendingPromotion` per WSD `coordinated_change_L2` §6.2. Discipline: `audit_only_after_settled` (mutable until status ∈ {applied, rejected}, then frozen).

**Schema:**
- `parameter_set_iri: str` (opaque)
- `proposed_at: datetime`
- `scope: Literal["local","global"]`
- `proposer: str` (user_id for Local; `"system"` for Global aggregation)
- `audit_policy: Literal["auto-apply","batched-summary","individual-review"]`
- `validation_results: dict` (gold-validator / calibration-validator / drift-validator outcomes per Chat A R3 validator-rename)
- `proposed_diff: dict`
- `evidence_summary: dict`
- `status: Literal["pending","approved","rejected","applied"]` (metadata under discipline; mutates until settled)
- `decision_at: Optional[datetime]`
- `decided_by: Optional[str]`
- `decision_notes: Optional[str]`

**Cascade.**
- New schema file `mindsos_knowledge/schemas/pending_promotions.py`.
- New role constant `ROLE_PENDING_PROMOTIONS = "pending-promotions"`.
- IRI builder + parser entries.
- ADR-0150 §amendment-4 entry.

### D-L2-14 — `capacity-gaps` schema (Global, admin-visible)

**Pick.** Ship full v1 per Chat A R4 D16 + WSD `coordinated_change_L2` §6.3. Discipline: `mutable_with_retention` (rows are admin-actionable; statuses transition).

**Schema:** per WSD §6.3 (unchanged) + Chat B amendment: `promotion-candidates` sub-queue per L0-13 extension (dream-found candidates). Node type `CapacityGap` carries `gap_kind: Literal["unsolvable_task","promotion_candidate"]` to discriminate.

**Cascade.**
- New schema file `mindsos_knowledge/schemas/capacity_gaps.py`.
- New role constant `ROLE_CAPACITY_GAPS = "capacity-gaps"`.
- ADR-0150 §amendment-4 entry.

### D-L2-15 — `learned-parameters` schema (Local + Global, single v1)

**Pick.** Single v1 role-graph per Chat A R3 D9.5 + R5 D28. Discipline: `admin_authored` for Global; `mutable_with_retention` for Local. FOL #4 split deferred to FOL chat; `parameter_set_iri` opaque key carries forward (D-L2-12).

**Schema:** Node type `LearnedParameter`:
- `parameter_set_iri: str`
- `target_parameter_iri: str`
- `value: float | dict` (JSON-encoded; `storage_mode` field per D-L2-22)
- `confidence: float` (ALS-reported, per subsystem)
- `applied_at: datetime`
- `applied_from_promotion_iri: Optional[IRI]` (link to source `pending-promotions` row for audit chain)

**Cascade.**
- New schema file `mindsos_knowledge/schemas/learned_parameters.py`.
- New role constant `ROLE_LEARNED_PARAMETERS = "learned-parameters"`.
- ADR-0150 §amendment-4 entry.

---

## R6 — `episodic_memories` (Chat B D-B48 cascade + rename strategy)

### D-L2-16 — Hard rename `memories` → `episodic_memories` (PB-11 + PB-G)

**Pick.** Atomic hard rename. **No alias, no deprecation window.**

- `ROLE_MEMORIES` → `ROLE_EPISODIC_MEMORIES` (constant rename; all imports updated in same PR).
- `memory_iri(version, user_id, memory_id)` → renamed to `episode_iri(version, user_id, episode_id)`; new sibling `memory_composite_iri(version, user_id, memory_id)` for Chat B's *clustering* Memory.
- `_PREFIXES` entry `"memories-"` → `"episodic-memories-"`.
- `_KINDS_PER_ROLE` adds entries `"episode"` + `"memory"` under `ROLE_EPISODIC_MEMORIES`.
- `schemas/memories.py` → `schemas/episodic_memories.py`; old single Memory node-type retired; new Episode + Memory node types per Chat B D-B47 + L5 design notes §4.3 + §4.6.
- `mindsos_capacity/builtins/consolidate.py` (`consolidate:mm`) updated to target the renamed role + new Episode entry shape.
- Phase 25 `read_other_local` audit constant `EVT_READ_OTHER_LOCAL_MEMORY` (if present) → `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY`; see also D-L2-23.
- Test fixtures (Phase 12/14/25/33/34/36) renamed atomically.

**Rationale (PB-11).** Old `memories` had one entry type (Memory). New `episodic_memories` has *two* entry types (Episode + Memory) with semantically *different* objects sharing one name (the new Memory is a clustering composite, not the per-task entry). Soft alias is incoherent because `memory_iri()` cannot map to a single new entry kind. Leave-as-legacy adds catalog confusion forever. Hard rename is the only coherent option; the codebase is internal, no shipped production rows exist (L4 is still in design), and the Phase 33 `consolidate:mm` capacity migrates atomically with the rename.

**Rationale (PB-G).** Alias-with-deprecation has no real users to protect. Atomic update keeps the codebase coherent; deferring the break invites mid-window confusion about which name to use.

**Cascade.**
- ADR-0044 amendment (see D-L2-25) renames + records new entry-type structure.
- ADR-0150 §amendment-4 row.
- L4 design notes cross-reference updated (already covered by Chat B closure).
- Maintenance migration script: `tools/rename_memories_to_episodic_memories.py` (Chat C plan-authoring sequences the migration phase; this chat does not write the script body).

### D-L2-17 — `episodic_memories` schema v1

**Pick.** Two entry types per Chat B locks; storage discipline per D-L2-3 = `append_only_with_lazy_inline`. Schema text inherited from Chat B D-B47 + L5 design notes §4.3 + §4.6.

**Edge types:**
- `memory_contains_episode` IntergraphEdge (Chat B D-B46; Memory → Episode entries inside the same role-graph; modeled as IntergraphEdge per L1 Phase 05b semantics — same metagraph, but cross-entry-type structural link).

**No embedded list.** Memory's old `episode_refs: list[XRef]` field rejected per Chat B PB-VV. Edge-based association only.

**Schema-only bootstrap.** Per Chat B D-B49 — bootstrap importer ships schema definition + zero entries. Per-user Local references schema at first task.

**Cascade.**
- New schema file `mindsos_knowledge/schemas/episodic_memories.py` per D-L2-16 rename.
- `mindsos_knowledge/bootstrap.py` gains `episodic_memories_bootstrap` entry (schema-only).
- IRI builders: `episode_iri`, `memory_composite_iri` (both Local-per-user; both inherit `_USER_ID_RE` per ADR-0044 §amendment-1).
- ADR-0044 amendment (see D-L2-25).

### D-L2-18 — KL retention surface (PB-12 wording lock + Chat B D-B17 carve-out)

**Pick.** KL public API gains two new operations per Chat B cascade:
- `kl.read_at_version(iri, version) -> Node | Edge` (Phase 11 side-by-side graph surface; routed to KL chat for impl).
- `kl.retire_version(role, version)` triggers lazy-inline marker; affected episodes inline retired content on next read.

L2 chat ratifies the API shape; L0 chat owns implementation phase per L5_FUTURE_WORK L2 cascades.

**Lazy-inline trigger discipline.** Per D-L2-5 wording: reference-stable, content-may-snapshot-on-retire. Lazy-inline is the *only* permitted mutation against `episodic_memories` content; it doesn't violate `append_only_with_lazy_inline` discipline by definition.

---

## R7 — Bootstrap closure + storage tiers + cross-cutting

### D-L2-19 — Bootstrap ordering via `applies_after` (PB-F)

**Pick.** Bootstrap importer suite uses topological order derived from a per-importer `applies_after: frozenset[IRI]` field. Reuses Chat A R3 PB-R3-17's ALS-subsystem ordering mechanism.

**v1 bootstrap order (topological):**

1. `ontology` bootstrap (DOLCE).
2. `lexicon` bootstrap (OEWN; declares `theoretical` + `empirical` layers — WSD installation chat ships the empirical importers).
3. `concepts` bootstrap (FrameNet).
4. `alignment:lexicon:ontology` bootstrap.
5. `task-patterns` bootstrap (v1 admin-authored seed set per WSD §6.4: 9 patterns).
6. `promoted-pipelines` bootstrap (v1 admin-authored seed pipelines per Chat A R3 D51 reachability invariant).
7. `learned-parameters` Global v0 (bootstrap importer ships per-subsystem v0 entries — Chat A R3 Gap 4).
8. `world-axioms` bootstrap (WSD installation chat — ConceptNet distillation; out of this chat).
9. `capacity-gaps` schema-only bootstrap (empty queue).
10. `parameter-staging` schema-only bootstrap (Local; empty).
11. `pending-promotions` schema-only bootstrap (Local + Global; empty).
12. `episodic_memories` schema-only bootstrap per Chat B D-B49 (Local; empty).
13. `problem-trace` schema-only bootstrap (empty).
14. `capacity-state` schema-only bootstrap (Local; empty).

**Hint-extractor seeds (L3) bootstrap BEFORE step 7** — `learned-parameters` v0 for ALS subsystem #4 (mapping confidence) depends on subsystem #10 (hint extraction) having seed parameters. L3 bootstrap order is L1/L3 reframe chat scope; L2 chat surfaces the constraint.

**Rationale.** Same machinery (`applies_after`) for two ordering concerns (ALS subsystem application + bootstrap import). Smaller blast radius than hardcoded order.

**Cascade.**
- L2-24 closed under this framing.
- Bootstrap importer registration contract gains `applies_after: frozenset[IRI] = frozenset()`.

### D-L2-20 — `domain_tag` on lexicon edges (L2-19)

**Pick.** Ratified per Chat A R5 D43 + WSD §3.3. Lexicon empirical-layer edges carry `domain_tag: str` (open vocabulary; admin-extended). v1 baseline values: `general | news | biomedical | conversational`. Per-domain class-generalization weights live in `learned-parameters` keyed by `(domain_tag, hierarchy_iri)`.

**Cascade.**
- Lexicon schema's empirical-layer edge type vocab carries `domain_tag` in its property set (when L1 schema-layer mechanism ships per WSD installation chat).
- ALS subsystem #7 (per-hierarchy class-generalization weights) writes domain-keyed entries.

### D-L2-21 — Memory schema extension for per-segment provenance (L2-22 dissolved)

**Pick.** **L2-22 closed; no L2-side work.**

Per-segment provenance is Chat B's frozen MM internals (intelligence-MM ReplanRecord + chain artifacts). L2 owns role-graph registration + bootstrap + container lifecycle. Episode internals are Chat B's lock (D-B47 + L5 design notes §4.3). The "memory schema extension" framing dissolves — Episode container is sufficient; per-segment provenance lives inside the frozen MM, not as L2 schema fields.

### D-L2-22 — Storage-tier discipline (PB-13)

**Pick.** **New ADR-0151 (L2 storage tiers)** locks the three-tier convention. v1 tiers:

| Tier | Range | Mechanism | `storage_mode` value |
|---|---|---|---|
| Inline | ≤ ~4 KB | JSON-encoded property | `"inline"` |
| Falkor large-property | ~4 KB to ~1 MB | Falkor BLOB-style property | `"falkor_blob"` |
| External blob_ref | > ~1 MB | v2 only; routed to FOL chat (Chat A R5 D30) | `"blob_ref"` (v2 reserved) |

Schemas carrying large-payload fields declare `storage_mode: Literal["inline","falkor_blob","blob_ref"]` alongside the value. v1 consumers: `episodic_memories.Episode.task_input_ref` (frozen TaskInput); `learned-parameters.LearnedParameter.value` when neural-model artifacts appear (post-FOL); future DataStateInstance frozen payloads inside Episode mm_root_ref.

**Rationale.** Chat B introduces the tiers as a v1 commitment that crosses L2/L4/L5. ADR-0121 (FalkorDB persistence) is too narrow — Tier 1 is backend-agnostic, Tier 3 is non-Falkor. A new ADR is the right anchor for downstream chats to cite.

**Alternatives considered.**
- ADR-0121 section — too backend-specific; misses Tier 1 and Tier 3.
- Cookbook page only — no architectural anchor; downstream chats can't cite.

**Cascade.**
- New ADR-0151 (see file).
- Schemas with large-payload fields gain `storage_mode` property declaration in their `*_PROPS` frozensets.
- L4 substrate handles tier routing on write (Chat C plan-authoring sequences impl phase).

### D-L2-23 — Cross-user read-side audit for `episodic_memories` (PB-H)

**Pick.** New audit event constant + capability for cross-user episodic_memories read.

**Additions (post-Phase-25 carry-forward; L0 chat owns impl):**
- `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` audit constant in `mindsos_server.audit`.
- New capability `READ_OTHER_LOCAL_EPISODIC_MEMORY` distinct from generic `READ_OTHER_LOCAL` (which gates `capacity-state`, `problem-trace` lookups).
- Admin role gets the new capability; default user role does not.
- Audit-log query API (Chat A R5 cascade L0-20) carries the new event constant.

**Rationale.** Episodes contain frozen TaskInput payloads which can include PII (chat transcripts, code with secrets, customer data). Inheriting generic `READ_OTHER_LOCAL` hides the privacy uplift in audit logs. Surface a distinct constant so audit queries can isolate episode reads from low-sensitivity capacity-state reads. Additive only; doesn't block v1 ship.

**Cascade.** L0_FUTURE_WORK gains L0-NEW-C (this chat surfaces; L0 chat sequences the constant + cap-roster amendment).

---

## R8 — ADR amendments package

### D-L2-24 — ADR-0094 amendment (drop `confidence` from promoted-pipelines)

**Pick.** §amendment-1 to ADR-0094. Removes `confidence` from promoted-pipelines record. Per-pipeline confidence migrates to:
- **Pipeline selection** parameters (ALS subsystem #3) — efficiency ranking when multiple valid pipelines exist for a task-type.
- **Task-to-task-type mapping confidence** (ALS subsystem #4) — load-bearing replacement.

Per-run output confidence remains on TaskRun (Chat B D-B33 + Chat A R3) in L5 intelligence-MM. No per-capacity confidence (unchanged from original §Decision).

Pipelines are binary deterministic solvers; failure → quarantine → admin review (per Chat A R3 + D-L2-9).

### D-L2-25 — ADR-0044 amendment (memories → episodic_memories rename + restructure)

**Pick.** §amendment-3 to ADR-0044 (continuing the amendment chain after §amendment-1 / §amendment-2).

Renames role + entry-type structure:
- Role-graph: `memories` → `episodic_memories`.
- IRI builders: `memory_iri(v,u,m)` retired; `episode_iri(v,u,e)` + `memory_composite_iri(v,u,m)` ship.
- Entry types: single Memory → Episode + Memory (clustering composite); see Chat B D-B47 + D-B48.
- Storage discipline: `append_only_with_lazy_inline` per D-L2-3.

**Architectural invariant preserved.** Local-per-user binding unchanged. `user_id` charset per ADR-0044 §amendment-1 + §amendment-2 unchanged. ADR-0010 import-direction unchanged.

**Out-of-scope for this amendment.** Cross-user `read_other_local` capability for episodic_memories — routed to L0 chat per D-L2-23.

### D-L2-26 — ADR-0150 §amendment-4 (v1 L4-driven role-graph expansion + episodic_memories rename) (PB-D)

**Pick.** Single bulk amendment to ADR-0150. Covers:
- Rename `memories` row → `episodic_memories` (entry types: Episode + Memory; discipline: `append_only_with_lazy_inline`).
- Add 4 new role-graph rows: `parameter-staging` (Local), `pending-promotions` (Local + Global), `capacity-gaps` (Global), `learned-parameters` (Local + Global).
- Confirm `sense-correlations` is **not** added (lexicon empirical-layer instead per D-L2-2).
- Confirm `world-axioms` and `training-runs` are **not** added in this amendment (WSD installation / FOL chats respectively own them).
- Closed role-set count: 8 (pre-amendment) → 12 (post-amendment); plus alignment-prefix; minus the `memories` → `episodic_memories` rename (no count change for rename).

**Rationale (PB-D).** Single amendment matches ADR-0150's existing pattern (one event per amendment: §am-1 alignment-Global-only; §am-2 evidence correction; §am-3 Phase-17 retirement). v1 L4-driven role-graph expansion *is* a single architectural event — Chat A + Chat B authored together; L2 chat closes. Reversibility concern is hypothetical; cohesion is real.

**Cascade.** Phase 13 sentinel test (`tests/phase_13/test_dispatch.py`) gains the 4 new role assertions + episodic_memories rename. Maintenance migration script (Chat C plan-authoring scope) handles shipped state.

**Chat C refinement note (2026-06-02 IL-3 split).** D-L2-26 picked single bulk §amendment-4 covering both rename + 4 new role-graphs. Chat C plan-authoring refined to PB-C 2-phase L2 split: Phase 39 (Rail A) ships rename atomically; Phase 43 (Rail A) ships 4 new role-graph schemas. The single bulk amendment doesn't fit the split — either it ships at Phase 39 documenting role-graphs not yet shipped (premature) or at Phase 43 documenting a rename 4 phases stale (late).

**Resolution per Chat C IL-3:** split into two amendments, each landing at its shipped-content phase:
- **§amendment-4** (Phase 39) — rename row only (`memories` → `episodic_memories`; entry-type structure; discipline `append_only_with_lazy_inline`).
- **§amendment-5** (Phase 43) — 4 new role-graph rows (`parameter-staging`, `pending-promotions`, `capacity-gaps`, `learned-parameters`); closed role-set 8 → 12.

Matches §am-1/§am-2/§am-3 precedent (one event per amendment). Sentinel test split: Phase 39 anchors §am-4; Phase 43 anchors §am-5 (4-role-assertion expansion). D-L2-26's "single amendment matches pattern" rationale was correct in principle but missed the Phase 39/43 phase-split that arose downstream at Chat C.

Captured in `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §1` cross-cutting + §4 Phase 39 / Phase 43 rows.

---

## R9 — Items routed out / explicitly out-of-scope confirmation

| Item | Disposition |
|---|---|
| L2-6 `world-axioms` role-graph | WSD installation chat owns; ADR-0150 §amendment-4 does NOT add. |
| L2-7 `training-runs` role-graph | FOL chat owns (Chat A R5 D29 defer). |
| L2-8 `fol-rules` + `fol-ledger` | FOL chat owns. |
| L2-12 `AlignmentsImporter` body | DWF installation chat owns. |
| L2-13 6 new lexicon importers | WSD installation chat owns. |
| L2-14 lexicon theoretical/empirical layers | Gated on L1/L3 reframe; WSD installation chat ships. |
| L2-15 empirical-layer edge vocabulary | WSD installation chat. |
| L2-16 cross-system mappings as InterGraphEdges | Gated on L1 InterGraphEdge naming reconciliation (L1/L3 reframe chat). |
| L2-17 parallel foundational ontologies (BFO / UFO / YAMATO) | FOL installation chat. |
| L2-21 module glossary + project-specific code knowledge | Code-skill installation chat. |
| L2-Q1 FOL #4 parameter_set_iri format encoding | Resolved at D-L2-12 (opaque). FOL chat re-litigates if split. |
| L2-9 `handle.validate_xref` body | Maintenance chat. |
| L2-10 4 unconsumed validators | Maintenance chat. |
| D38 capacities-as-hyperedges | L1/L3 reframe chat — L2-25 schema-v2 partial lock (D-L2-6) accommodates either outcome. |
| D36 Monitor lifecycle ownership | L1/L3 reframe chat. |
| D46 universal `unhandled_inputs` contract | L1/L3 reframe chat. |
| D48 DataState taxonomy expansion | L1/L3 reframe chat. |

---

## L2 Chat — CLOSURE

**Status:** L2 chat complete 2026-06-01.

**Decisions resolved:** D-L2-1 through D-L2-26 (26 substantive picks across 9 rounds).

**Architectural commitments locked:**
- **Per-role-graph `mutation_discipline`** with 5 v1 disciplines + L4 startup invariant.
- **Per-field `content` vs `metadata`** declaration on schemas under immutable disciplines.
- **Reference-stability framing** supersedes "immutability" wording for episodic_memories.
- **`alignment:<a>:<b>` colon-separated** canonical form (3 conflicting forms in shipped code reconciled to this).
- **`sense-correlations` withdrawn** as standalone role-graph; lexicon empirical-layer hosts the data; ALS #8 label preserved.
- **`promoted-pipelines` schema v2 partial lock** — status + lifecycle + paired-pipelines source-of-truth + serves_task_types cache eliminated; HAS_STEP/PipelineStep shape deferred to L1/L3 reframe.
- **L3 owns status filter** at read; L2 stays dumb-store.
- **`task-patterns` flat 9-field schema** with explicit content/metadata partition.
- **4 new role-graph schemas** ship v1: `parameter-staging`, `pending-promotions`, `capacity-gaps`, `learned-parameters` (single, opaque `parameter_set_iri`).
- **`memories` → `episodic_memories` hard rename**, atomic PR, no alias.
- **ADR-0151 storage-tier discipline** (≤4 KB inline / ≤1 MB Falkor BLOB / >1 MB blob_ref v2).
- **Bootstrap topological order** via `applies_after` (same machinery as ALS subsystem ordering).
- **`EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` audit constant** + new capability.
- **ADR-0150 §amendment-4** single bulk amendment for v1 L4-driven role-graph expansion.
- **ADR-0094 amendment** drops `confidence` from promoted-pipelines.
- **ADR-0044 §amendment-3** records rename + new entry-type structure; Local-per-user invariant preserved.

**Items routed elsewhere (see R9 table).**

**Pre-Chat-C handoff.**
Chat C inherits this L2_CHAT_DECISIONS + CHAT_A_DECISIONS + CHAT_B_DECISIONS as the foundation for the L4/L5 phase-map authoring. Specifically:
- Phase plan must include a `memories → episodic_memories` rename migration phase (atomic; single PR; high-risk for cap-roster touches).
- Phase plan must include `mutation_discipline` runtime invariant enforcement at `KnowledgeLayer.bootstrap()`.
- ADR-0151 storage-tier impl phase (write-side routing) sized at ~200-400 LOC.
- Bootstrap importer suite phase ships all 4 new role-graphs + episodic_memories rename atomically.

**Pre-WSD-installation handoff.**
WSD chat inherits:
- `lexicon` empirical-layer ships the `sense-correlations` data (no separate role-graph).
- ALS subsystem #8 `parameter_set_iri` retargets to lexicon-empirical-layer.
- Phase-2 routing via L3 pipeline-finder + status filter (D-L2-8); cache lives in L3, not L2.
- `paired_pipelines` source-of-truth on task-patterns (D-L2-7).

**Pre-DWF-installation handoff.**
DWF chat inherits `alignment:<a>:<b>` canonical form (D-L2-1); ratifies or re-litigates with use-case pressure.

**Pre-L1/L3-reframe handoff.**
L1/L3 reframe chat closure must pick between:
- HAS_STEP-property shape (current Phase 13) → no further L2-25 amendment.
- Capacities-as-hyperedges (D38 reframe direction) → L2-25 §amendment-1 lands with hyperedge ordering replacing `HAS_STEP`.

**Document outputs (this chat).**
- `_workbench/L2_CHAT_DECISIONS.md` — this document.
- `decisions/adr/0150-l2-knowledge-lifecycle.md` §amendment-4.
- `decisions/adr/0094-confidence-pipeline-level.md` §amendment-1.
- `decisions/adr/0044-memories-move-to-local-per-user.md` §amendment-3.
- `decisions/adr/0151-l2-storage-tiers.md` (NEW).
- `decisions/adr/0152-l2-role-graph-schema-v2.md` (NEW).
- `decisions/adr/0153-l2-mutation-discipline.md` (NEW).
- `decisions/adr/0154-alignment-naming-canonical.md` (NEW).
- `_workbench/L2_FUTURE_WORK.md` — closure markers on L2-1, L2-11, L2-19, L2-22, L2-23, L2-25, L2-26, L2-27, L2-Q1, L2-Q2.
- `HANDOFF.md` updated with L2 closure summary in §2.2 + §6.

---

*L2 chat closed 2026-06-01. 26 substantive picks, 4 new ADRs, 3 ADR amendments, 1 dissolved future-work item (L2-22), 1 confirmed withdrawal (sense-correlations). Zero reversals across 1 reanalysis pass.*
