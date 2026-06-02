---
title: L2 role-graph schema v2 — promoted-pipelines, task-patterns, new role-graphs, episodic_memories
status: Accepted
date: 2026-06-01
layer: L2
---

# ADR-0152: L2 role-graph schema v2

**Status:** Accepted

**Date:** 2026-06-01 (L2 chat closure)

**Related (Accepted):** [ADR-0149](0149-l2-role-schemas-strict-false-and-tightening-rule.md),
[ADR-0150](0150-l2-knowledge-lifecycle.md) §amendment-4,
[ADR-0094](0094-confidence-pipeline-level.md) §amendment-1,
[ADR-0044](0044-memories-move-to-local-per-user.md) §amendment-3,
[ADR-0151](0151-l2-storage-tiers.md).

**Related (Proposed):** [ADR-0153](0153-l2-mutation-discipline.md).

**Companion docs:** `_workbench/L2_CHAT_DECISIONS.md` D-L2-6 through
D-L2-17.

## Context

Chat A (L4 design-resolution, 2026-05-28) + Chat B (L5 design-
resolution, 2026-05-31) together authored schema-level requirements
for v1 L4 substrate. Specifically:

- `promoted-pipelines` schema needs a 5-state lifecycle enum, paired-
  pipelines tracking, removal of `confidence` field, and quarantine
  semantics (Chat A R3 PB-R3-21 / PB-R3-22 / PB-R3-31).
- `task-patterns` schema needs new fields for hint extraction,
  mapping-confidence threshold, sufficient-predicate, domain
  classification (Chat A R3 Method δ + R5 D43).
- 4 new role-graph schemas need to ship: `parameter-staging`,
  `pending-promotions`, `capacity-gaps`, `learned-parameters` (Chat A
  R3 D9.5 + R4 D16 + WSD `coordinated_change_L2` §6).
- `episodic_memories` (renamed from `memories` per Chat B D-B48)
  needs two entry types (Episode + Memory) with edge-based association
  (Chat B D-B47).

This ADR locks the v2 schema contents. Mutation discipline + per-field
content/metadata partitioning is locked separately in ADR-0153.
Role-set closure + role names are locked in ADR-0150 §amendment-4.
Storage tiers are locked in ADR-0151. ADR-0094 §amendment-1 separately
tracks the `confidence` field removal.

## Decision

### §1 `promoted-pipelines` schema v2 (PARTIAL LOCK per L2_CHAT_DECISIONS D-L2-6)

**Pipeline node-type properties:**

| Field | Type | Discipline (ADR-0153) | Notes |
|---|---|---|---|
| `pipeline_name` | str | content | |
| `edge_sequence` | list[capacity_edge_id] | content | Immutable per WSD §A.2 |
| `start_ds` | datastate_iri | content | Derivable |
| `end_ds` | datastate_iri | content | Derivable |
| `expression_metadata` | dict | content | Registration-time inlining metadata |
| `status` | Literal["draft","tested","active","quarantined","retired"] | metadata | Chat A R3 PB-R3-22 |
| `n_runs` | int | metadata | |
| `outcome_history` | list[OutcomeRecord] | metadata (append-only sub-record) | |
| `provenance` | ProvenanceRecord | metadata (append-only) | |
| `quarantine_threshold` | float (default 0.85) | metadata (admin-tunable) | Chat A R3 PB-R3-31 |
| `created_at` | timestamp | metadata | |
| `tested_at` | timestamp | metadata | |
| `activated_at` | timestamp | metadata | |
| `quarantined_at` | timestamp | metadata | |
| `quarantined_by` | Literal["system","admin"] | metadata | Chat A R3 PB-R3-31 |
| `retired_at` | timestamp | metadata | |

**`confidence` field DROPPED** per ADR-0094 §amendment-1. Per-pipeline
confidence migrates to ALS subsystems #3 (selection parameters) + #4
(mapping confidence) on `learned-parameters`. Per-run output confidence
remains on `TaskRun` composite in L5 intelligence-MM.

**`serves_task_types` field NOT introduced on Pipeline** per
L2_CHAT_DECISIONS D-L2-7. Chat A R3 PB-R3-21 proposed
`serves_task_types` as a pipeline-side cache of the task-pattern → pipeline
relationship (authoritative on task-pattern as `paired_pipelines`).
L2 chat overrides: the pipeline-side cache is eliminated entirely.
Phase-2 pipeline lookup walks task-patterns via L3 pipeline-finder,
which maintains its own runtime index over `task-patterns.paired_pipelines`.
Note: `paired_pipelines` lives on **task-pattern** (see §2), never on
Pipeline — there is no pipeline-side `paired_pipelines` field, removed
or otherwise.

**HAS_STEP / PipelineStep shape DEFERRED** to L1/L3 reframe chat
close (D38 capacities-as-hyperedges). Current Phase 13 shape
(`HAS_STEP` regular EdgeType with `position` advisory property +
`PipelineStep` NodeType) remains in effect until reframe lands. If
reframe accepts capacities-as-hyperedges, this ADR gets
§amendment-1 with hyperedge-ordering replacing `HAS_STEP`.

**Status transitions (Chat A R3 PB-R3-31 confirmed):**

- `draft → tested`: admin.
- `tested → active`: admin (promotion).
- `active → quarantined`: **system** (on failure with
  `mapping_confidence_at_arrival > quarantine_threshold`).
- `quarantined → active`: admin (reinstate).
- `quarantined → retired`: admin (delete).

Status mutates in place under `immutable_successor` discipline
(ADR-0153) because it is *metadata* per per-field partition above.

**Read-side status filter** per L2_CHAT_DECISIONS D-L2-8: L3
pipeline-finder filters by status (default `status_in={"active"}`).
L2 read APIs return all status values; L3 owns selection. Dream
pipelines may target `status="quarantined"` explicitly.

### §2 `task-patterns` schema v2

**TaskPattern node-type properties (flat 9-field + 2 timestamps):**

| Field | Type | Discipline | Source |
|---|---|---|---|
| `pattern_name` | str | content | Phase 13 |
| `task_shape_recognizer` | dict | content | Phase 13 |
| `sufficient_predicate_iri` | IRI | content | Chat A R3 |
| `domain` | str | content | Chat A R5 D43 |
| `paired_pipelines` | list[IRI] | content (source-of-truth per PB-R3-21) | Chat A R3 |
| `relevant_hints` | list[IRI] | metadata (admin-tunable post-author) | Chat A R3 Method δ |
| `mapping_confidence_threshold` | float | metadata (ALS subsystem #4 refines) | Chat A R3 |
| `n_observations` | int | metadata | Phase 13 |
| `confidence` | float | metadata | Phase 13 |
| `provenance` | ProvenanceRecord | metadata (append-only) | WSD `pending_adrs` §A.7 |
| `routing_override` | Optional[dict] | metadata (v1.5) | PB-R3-32 |
| `created_at` | timestamp | metadata | |
| `last_updated_at` | timestamp | metadata | |

**Edge types unchanged:** `DECOMPOSES_INTO`, `PREREQUISITE_OF` (Phase
13). `SubgoalTemplate` node-type unchanged.

**Flat schema chosen over split** per L2_CHAT_DECISIONS D-L2-10.
Normalization (`config_ref → TaskPatternConfig`) costs an extra L2
read hop per Phase-1 candidate eval; Phase-1 budget < 50ms per
Chat A R3. Flat wins on perf; per-field discipline (ADR-0153) handles
growth.

### §3 `parameter-staging` schema (Local only)

**StagedEvidence node-type properties:**

| Field | Type | Notes |
|---|---|---|
| `parameter_set_iri` | str (opaque) | L2_CHAT_DECISIONS D-L2-12 |
| `signal_source_iri` | IRI | One of 10 v1 signal sources (Chat B D-B51) |
| `target_parameter_iri` | str (opaque sub-key) | |
| `target_value` | float OR dict (JSON-encoded) | |
| `evidence_pointer` | IRI | XRef to source episode |
| `signal_weight` | float | |
| `blame_weight` | float (default 1.0) | |
| `staged_at` | datetime | |
| `retention_window_until` | datetime | Admin-tunable; default 30 days |

**Edge types:** none v1.

**Discipline:** `mutable_with_retention` (ADR-0153) — TTL-pruned
evidence rows.

### §4 `pending-promotions` schema (Local + Global)

**PendingPromotion node-type properties:**

| Field | Type | Notes |
|---|---|---|
| `parameter_set_iri` | str (opaque) | |
| `proposed_at` | datetime | |
| `scope` | Literal["local","global"] | |
| `proposer` | str | user_id (Local) or `"system"` (Global) |
| `audit_policy` | Literal["auto-apply","batched-summary","individual-review"] | Chat A R3 D9.3 |
| `validation_results` | dict | gold-validator / calibration-validator / drift-validator outcomes (Chat A R3 validator rename) |
| `proposed_diff` | dict | Per-parameter old_value / new_value / confidence |
| `evidence_summary` | dict | # contributing tasks, signal-source breakdown, examples |
| `status` | Literal["pending","approved","rejected","applied"] | metadata; mutates until settled |
| `decision_at` | Optional[datetime] | |
| `decided_by` | Optional[str] | |
| `decision_notes` | Optional[str] | |

**Edge types:** none v1.

**Discipline:** `audit_only_after_settled` (ADR-0153) — mutable until
`status ∈ {applied, rejected}`, then frozen.

### §5 `capacity-gaps` schema (Global)

**CapacityGap node-type properties:**

| Field | Type | Notes |
|---|---|---|
| `gap_kind` | Literal["unsolvable_task","promotion_candidate"] | Discriminator |
| `task_shape_iri` | IRI | (unsolvable_task only) |
| `start_datastate_iri` | IRI | (unsolvable_task only) |
| `goal_datastate_iri` | IRI | (unsolvable_task only) |
| `candidate_kind` | Literal["pipeline","task_pattern","capacity"] | (promotion_candidate only) |
| `candidate_proposal` | dict | (promotion_candidate only) |
| `attempted_searches` | list[dict] | |
| `first_seen_at` | datetime | |
| `last_seen_at` | datetime | |
| `occurrence_count` | int | |
| `status` | Literal["open","resolving","resolved","out_of_scope"] | |
| `resolution` | Optional[Literal["taught_capacity","added_adapter","scope_limit_documented",...]] | |
| `resolved_at` | Optional[datetime] | |
| `resolved_by` | Optional[str] | |

**Edge types:** none v1.

**Discipline:** `mutable_with_retention` (ADR-0153) — admin actions
mutate status; retention policy per admin tuning.

`promotion_candidate` sub-queue per Chat B D-B53 + L5 cascade L0-13:
dream-found promotion candidates surface here for admin review.

### §6 `learned-parameters` schema (Local + Global)

**LearnedParameter node-type properties:**

| Field | Type | Notes |
|---|---|---|
| `parameter_set_iri` | str (opaque) | |
| `target_parameter_iri` | str | |
| `value` | float OR dict (JSON-encoded) | Carries `storage_mode` per ADR-0151 when payload may exceed Tier 1 |
| `storage_mode` | Literal["inline","falkor_blob","blob_ref"] | Per ADR-0151 |
| `confidence` | float | ALS-reported |
| `applied_at` | datetime | |
| `applied_from_promotion_iri` | Optional[IRI] | Audit chain link |

**Edge types:** none v1.

**Discipline:** `admin_authored` (Global) + `mutable_with_retention`
(Local) per ADR-0153.

**FOL #4 split deferred** per L2_CHAT_DECISIONS D-L2-12; single v1
role-graph; `parameter_set_iri` opaque. If FOL chat accepts the 3-way
split (Chat A R5 D28), this ADR gets §amendment-1.

### §7 `episodic_memories` schema (Local only)

**Renamed from `memories`** per ADR-0044 §amendment-3.

**Episode node-type properties** (per Chat B D-B47 + L5 design notes
§4.3):

| Field | Type | Discipline | Notes |
|---|---|---|---|
| `task_input_ref` | XRef | content | Frozen TaskInput; payload via ADR-0151 tiers |
| `mm_root_ref` | XRef | content | Frozen MM root (three sub-MMs + outcome) |
| `task_pattern_iri` | IRI | content | Primary cluster key (last-active mapping) |
| `outcome_classification` | Literal["succeeded","failed","low_confidence","asked_user","dont_know"] | content | |
| `crash_marker` | Optional[CrashInfo] | content | Set when consolidation followed a crash (Chat B D-B50) |
| `consolidated_at` | timestamp | content | |

**Memory node-type properties** (per Chat B D-B47):

| Field | Type | Discipline | Notes |
|---|---|---|---|
| `task_pattern_iri` | IRI | content | Primary cluster key |
| `created_at` | timestamp | metadata | |
| `admin_notes` | Optional[str] | metadata | |
| `rejected_promotions` | list[XRef] | metadata (denormalized; audit log authoritative) | |

**Edge types:**

- `memory_contains_episode` IntergraphEdge (Memory → Episode entries
  inside the same role-graph). Chat B D-B46 + D-B47 PB-VV. NOT an
  embedded list.

**Discipline:** `append_only_with_lazy_inline` per ADR-0153. Episodes
are append-only externally; lazy inline-on-retire is the only
permitted internal mutation per Chat B D-B17 + L2_CHAT_DECISIONS
D-L2-5.

**Bootstrap importer:** schema-only per Chat B D-B49. Per-user Local
references schema at first task; entries grow from task execution.
No Global seed content (no Global L5 per Chat B D-B4).

**IRI builders:** `episode_iri(version, user_id, episode_id)` and
`memory_composite_iri(version, user_id, memory_id)` per ADR-0044
§amendment-3. Both Local-per-user; `user_id` charset per ADR-0044
§amendment-1.

## Rationale

**Why partial lock on `promoted-pipelines`.** D38 (capacities-as-
hyperedges) is routed to L1/L3 reframe chat. Locking the full
`HAS_STEP` shape now risks re-amendment if reframe accepts. The
status + lifecycle + paired-pipelines surface is needed by WSD
installation (Phase 2 routing) and unaffected by reframe's outcome;
ship that now. Step-shape lands in §amendment-1 once reframe closes.

**Why flat task-patterns.** Three alternatives: flat-9, split into two
node types (`TaskPattern` + `TaskPatternConfig`), normalized via
`config_ref`. Normalization fails Chat A R3's <50ms Phase-1 budget.
Split adds schema concept without addressing growth. Flat wins
operationally; per-field content/metadata discipline (ADR-0153)
manages cohesion.

**Why eliminate `serves_task_types` cache.** Bidirectional caches
need invalidation; invalidation needs either write-through coupling
(harder to evolve schemas) or rebuild-on-startup (transient drift).
Single source of truth on task-patterns + L3-side runtime index is
cheaper than maintaining cache consistency in L2.

**Why two entry types in `episodic_memories`.** Chat B D-B47 — Episode
is the per-task frozen artifact; Memory is the clustering composite
over Episodes keyed by task-pattern. Different lifecycles, different
mutability, different IRI shapes. Conflating them (as the old single-
type `memories` did) creates ambiguity at the first promotion-
granularity question.

**Why edge-based Memory→Episode association.** Chat B PB-VV — embedded
`episode_refs: list[XRef]` would either grow unboundedly (perf cost on
every Memory read) or need pagination logic. Edges are the L1
primitive for n-ary associations; reuse.

## Consequences

**Good:**

- L4 substrate has a stable v2 surface to write against; WSD
  installation chat unblocked on schema-side.
- `confidence` field removal eliminates the
  "where-does-confidence-live" ambiguity (pipeline / TaskRun /
  per-capacity).
- Per-field content/metadata partition (ADR-0153) makes
  `immutable_successor` enforceable.
- ADR-0151 storage-tier hooks land cleanly in `learned-parameters` +
  `episodic_memories`; FOL chat's blob_ref work plugs in without
  schema change.

**Tradeoffs:**

- L2-25 partial lock means an §amendment-1 on this ADR after L1/L3
  reframe closes — known follow-up; not blocking.
- Phase 13 shipped schemas need amendment (one-liners adding
  `mutation_discipline` declaration + `CONTENT_FIELDS` /
  `METADATA_FIELDS` frozensets). Chat C plan-authoring sequences this
  as part of the v2 schema deploy phase.
- `promoted-pipelines` v2 deploy needs a one-shot maintenance migrator
  to strip `confidence` from any shipped Local-Pipeline records
  (none exist in v1 production — L4 is in design — but discipline
  ships).

**Lock-ins:**

- Field names are schema contract. Renames require migration.
- Flat task-patterns commits to property-set growth (managed by
  ADR-0153 partition).
- Two-entry-type `episodic_memories` commits to edge-based
  association (no embedded list option without amendment).

## Alternatives considered

1. **Per-role-graph individual ADRs (5+ ADRs).** Rejected — bulk ADR
   matches the architectural event (v1 L4-driven schema-v2 deploy).
   Five ADRs citing each other fragment the review surface.

2. **Lock `HAS_STEP` shape now; re-amend if reframe accepts.** Rejected
   — two amendments to the same shape in one cycle. Partial lock is
   cleaner.

3. **Keep `confidence` on `promoted-pipelines` as legacy field.**
   Rejected — see ADR-0094 §amendment-1 rationale; pipelines are
   binary deterministic; pipeline-level confidence vestigial under
   the migrated ALS framing.

4. **Two-type split for task-patterns (`TaskPattern` +
   `TaskPatternConfig`).** Rejected — splits one growth axis;
   doesn't address future axes. ADR-0153 partition handles cohesion
   without two-type cost.

5. **`serves_task_types` cache stored + write-through.** Rejected —
   bidirectional write coupling; cache rebuild-on-startup leaves
   transient drift; eliminate the cache entirely (D-L2-7).

6. **Single `Memory` entry type in `episodic_memories` (per old
   `memories` shape).** Rejected — Chat B's Episode vs Memory
   distinction is load-bearing; conflating them prevents
   per-episode promotion (Chat B PB-3) and forces ambiguous lifecycle.

7. **Embedded `episode_refs: list[XRef]` on Memory.** Rejected per
   Chat B PB-VV.

## Source

L2_CHAT_DECISIONS D-L2-6 through D-L2-17; Chat A R3 PB-R3-21,
PB-R3-22, PB-R3-31 (promoted-pipelines lifecycle); Chat A R3 Method δ
+ R5 D43 (task-patterns hint + domain); Chat A R3 D9.5 + R4 D16
(parameter-staging + pending-promotions + capacity-gaps); Chat B
D-B47 + D-B48 (episodic_memories entry types); WSD
`coordinated_change_L2_lexicon_layers_and_role_graphs.md` §6
(role-graph specs).
