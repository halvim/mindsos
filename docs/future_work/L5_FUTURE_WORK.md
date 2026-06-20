# L5 Mental Model — Future Discussions & Work

**Date:** 2026-05-31 (updated post Chat B closure)
**Status:** Living index. Chat B closed; this doc tracks **post-Chat-B** L5 v2+ work + cascades.

---

## 1. Chat B closure (2026-05-31)

L5 resolved. See `docs/_workbench/CHAT_B_DECISIONS.md` for full settlement. Highlights:

- **D'1 (version-IRI freeze + pin-at-instantiation + lazy inline-on-retire)** replaces note-fork. L5 v1 ships independent of L0 server-pivot v2.
- **Three sub-MMs** (knowledge-MM, capacity-MM, intelligence-MM) with thin root + IntergraphHyperEdge composition.
- **6-level chain** (HintSet → MappingResult → Plan → Pipeline → PipelineRun → TaskRun).
- **Plan = recursive tree of Milestones** (lazy decomposition; sequential siblings v1; max-depth=3 cold-start; planning.* L3 family).
- **No Global L5.** Memories Local + circumstantial.
- **Dream-as-live + ALS as sole learning track.**
- **Vocabulary:** episode / memory / `episodic_memories` / Milestone / TaskRun / PipelineRun / worker pool (L4 substrate).

---

## 2. Retired items

The following were either resolved by Chat B or rendered moot by other Chat B picks:

| # | Item | Disposition |
|---|---|---|
| L5-1 | Note-fork mechanism scope | **Retired.** D'1 + lazy inline-on-retire ships v1; note-fork unneeded. |
| L5-2 | If note-fork pulled forward — L0 coordination | **Retired** (L5-1 retired). |
| L5-3 | If retention redesigned — Option B/C | **Resolved.** D'1 picked; both B and C rejected. |
| L5-6 | R3 Cross-user Global promotion criteria | **Retired.** No Global L5; cross-user learning via ALS. |
| L5-8 | R5 Partial-MM consolidation on crash | **Resolved.** Consolidate-with-crash-flag + checkpoint trigger set; physical mechanism to L4-implementation. |
| L5-9 | MSUR ledger in MM during execution; v2 persistence | **Refined.** Live-cross-task continuity v2; episode-resident snapshot v1. |
| L5-10 | SCMS state snapshots in MM | **Confirmed v1.** SCMSState composite in intelligence-MM per task. |
| L5-11 | Replan history records on MM | **Resolved.** ReplanRecord schema extended with `replan_level` + `replan_milestone_ref`; bidirectional XRefs to TaskRun. |
| L5-Q1 | Chat B starts before note-fork designed? | **Resolved.** D'1 sidesteps the dependency entirely. |
| L5-Q2 | Phase 6 cross-val MM treatment | **Resolved.** Cross-validation results nest under parent episode as `CrossValSegmentVariant`; v1 = Level-4 (pipeline-segment) substitution only. |
| L5-Q3 | MSUR persistence vs Pause coupling | **Locked.** Both deferred together; coupling explicit; no decouple v2 without revisiting. |

---

## 3. L5 v2+ follow-ups

| # | Item | Source | Owner chat |
|---|---|---|---|
| L5-NEW-1 | **Retention policy fine-tuning** — aging strategies (last N per task-type; top-K by confidence; keep all failures; compress aging) | L5 §7 R1; PB-QQ episode storage growth concern | v2 follow-up (or v1.5 if growth observed) |
| L5-NEW-2 | **Consolidation frequency** — every-completion default; revisit if write-volume problem | L5 §7 R2 | v2 follow-up |
| L5-NEW-3 | **Teaching** — user authors an episode/memory directly without execution | L5 §7 R4 | v3+ |
| L5-NEW-4 | **External blob store for DataStateInstance** (`storage_mode = blob_ref`) — > ~1 MB outputs | Chat B D-B44 + Chat A R5 D30 (FOL deferral) | FOL installation chat |
| L5-NEW-5 | **Cross-level dream variants** — re-run from sub-Milestone, re-extract hints, etc. (v1 dream operates at TaskRun level only) | Chat B D-B7 | v2 follow-up |
| L5-NEW-6 | **Parallel sibling Milestone execution** — declared `parallel_group` field on Milestone schema (v1 sequential only) | Chat B D-B29 (PB-PP) | v2 follow-up |
| L5-NEW-7 | **Plan-as-DAG** (vs tree v1) — allows shared sub-Milestones across parents | Chat B D-B23 + PB-EE pick (tree v1) | v2 evaluation |
| L5-NEW-8 | **Per-Milestone on_child_failure policy** — `fail_parent` / `skip_and_continue` / `retry` (v1 fail-fast only) | Chat B D-B24 (PB-II) | v1.5 evaluation |
| L5-NEW-9 | **L2 `milestone-patterns` role-graph** — admin-authored catalog of milestone-patterns referenced by `planning.decompose` | Chat B PB-T sub-question; capacity-internal v1 | v1.5 if admin-authoring pressure materializes |
| L5-NEW-10 | **Cross-task SCMS context** | Chat A R5 D42 → L4-22 | v2 evaluation |
| L5-NEW-11 | **Memory cluster secondary indexes** — pre-build "episodes originally mapped to X" index (v1 walks via retrieval capacity) | Chat B D-B54 (PB-OO) | v2 if query volume |
| L5-NEW-12 | **L0 audit-log cross-link on episode** — optional field on Episode for direct audit-event refs (v1 cross-link via L0 query API) | Chat B reanalysis crack 17 | v2 evaluation |
| L5-NEW-13 | **Falkor query indexes for cross-sub-MM hyperedges** — performance work for Pipeline-membership queries. **Strategy ratified ADR-0181 @ Phase 49 (decide-and-document; no index code); physical creation → WSD retrieval (first query consumer).** Indexes named: `Episode.task_pattern_iri`, `Memory.memory_id`, `IntergraphHyperEdge` membership. | Chat B PB-HHH | **SCHEDULED — Phase 52** (`WSD_INSTALLATION_PHASE_MAP.md` §2 WSD-2, 2026-06-10) |
| L5-NEW-14 | **Physical-layout optimization** — composite collapse opportunities (e.g., StepExecutionRecord as properties on capacity-MM step NodeInstance if benchmarks favor) | Chat B PB-AAA | Chat C / L4-implementation |
| L5-NEW-15 | **Admin cross-Local memory search tooling** — when admin wants to curate Global training material manually | Chat B D-B4 | v2 follow-up |
| L5-NEW-16 | **`dream.exploration` plural-strategy variant catalog** — FOL plural-strategies + alt-pipeline exploration | Chat B D-B6 + Chat A R5 D27 (Q5 deferred) | FOL installation chat |
| L5-NEW-17 | **Episode-level promotion to a curated corpus** — promotion granularity is per-episode (Chat B PB-3 ii); flow + admin tooling | Chat B D-B47 | v2 follow-up |
| L5-NEW-18 | **Cross-replan blame chain reconstruction** — multi-replan task with cascade of ReplanRecords; reconstruction tooling | Chat B reanalysis crack 6 | Maintenance / debug tooling chat |

---

## 4. Open coordination questions (post Chat B)

| # | Question | Source |
|---|---|---|
| L5-NEW-Q1 | KL retention TTL backstop policy under D'1 — episodes never re-read still eventually surrender storage to KL; TTL value? | Chat B PB-J.a; L0 chat coordination |
| L5-NEW-Q2 | Falkor checkpoint mechanism — continuous vs phase-boundary periodic | Chat B D-B50; L4-implementation |
| L5-NEW-Q3 | Episode storage growth monitoring thresholds — when does v1.5 retention policy trigger? | Chat B PB-QQ |
| L5-NEW-Q4 | Aggregator capacity catalog — what aggregators ship v1 (sum, max, last, concat, etc.)? | Chat B D-B24 |

---

## 5. Cascades to other layers (Chat B-derived)

### L0 cascades
- L0-10 (note-fork mechanism) — **retired from L0 v2 scope.**
- L0-13 amendment — `capacity-gaps` extended with `promotion-candidates` sub-queue for dream-found candidates.
- New L0-NEW-A: `kl.read_at_version(iri, version)` public API. **SHIPPED Phase 48.**
- New L0-NEW-B: `kl.retire_version()` operation hook triggers lazy-inline marker. **SHIPPED Phase 48.**
- **L0-26 / PB-RT (surfaced Phase 49 Integration C):** the L5 **Episode** node carries a structured dict `value` (Chat B D-B47), but the L0 node persister stored node `value` as a primitive → an episode-bearing Local could not flush to Falkor. Live episode flush was **descoped** at Phase 49; contract fixed at **ADR-0182** + `value_codec.py` (Phase 50). **Durable Episode persistence still open → v1.5 durable-retention work** (codec is in; the Episode-flush consumer is not). Tracked as L0-26.

### L1 cascades
- IntergraphHyperEdge (Phase 05c) gains documented use case ("Pipeline composition over capacity-MM"). Documentation amendment.

### L2 cascades
- L2-23 amendment — `episodic_memories` role-graph schema (Episode, Memory entry types).
- L2-24 amendment — bootstrap-importer suite includes `episodic_memories_bootstrap` (schema-only).
- New edge type `memory_contains_episode` across the role-graph.

### L3 cascades
- L3-34 amendment — capacity registration gains semantic "reads MM"; harness exposes `mm.get_or_instantiate()` to worker threads.
- L3-37 amendment — ALS family + new subsystem #11 (planning decomposition calibration) + new signal source `signal.plan_decomposition_outcome`.
- L3-47 amendment — typed CapacityContext gains `version_snapshot: dict[IRI, version_int]`.
- New L3-50 — `planning.*` capacity family (4 capacities v1).
- New L3-51 — `dream.*` orchestration capacity family (3 capacities v1).
- pipeline-finder revision — `pipeline_finder.from_milestone(milestone, ctx) → Pipeline`.

### L4 cascades
- New L4 substrate component — MM resolution+instantiation layer (+100-200 LOC).
- L4 invariant — no shadow state outside MM.
- D14 (ReplanRecord) amended with `replan_level` + `replan_milestone_ref`.
- D32.5c.4 (attention_score) — moves to TaskRun.
- Vocabulary rename: PlanRun → PipelineRun across Chat A inheritance.
- "L3 worker pool" → "worker pool" naming discipline (Chat C inheritance).

---

## 6. Chat C closure routing (2026-06-02)

Chat C plan-authoring closed 2026-06-02 (`confirmation_docs/POST_PHASE_38_PHASE_MAP.md`). Routing of L5 items:

| Item | Routed to | Notes |
|---|---|---|
| L5-NEW-1 (retention policy fine-tuning) | **v1.5 chat if observed growth** | Phase 48 SHIPPED monitoring instrumentation (`mindsos_intelligence/monitoring.py`, instrumentation-only); policy itself still v1.5. |
| L5-NEW-2 (consolidation frequency) | **v2 follow-up** | — |
| L5-NEW-3 (teaching: user authors episode) | **v3+** | — |
| L5-NEW-4 (external blob store for DataStateInstance) | **FOL_INSTALLATION_CHAT** | Chat B D-B44; FOL pushback #8. |
| L5-NEW-5 (cross-level dream variants) | **v2 follow-up** | v1 = TaskRun level only. |
| L5-NEW-6 (parallel sibling Milestone execution) | **v2 follow-up** | v1 = sequential. |
| L5-NEW-7 (Plan-as-DAG vs tree) | **v2 evaluation** | v1 = tree. |
| L5-NEW-8 (per-Milestone `on_child_failure` policy) | **v1.5 evaluation** | v1 = fail-fast. |
| L5-NEW-9 (`milestone-patterns` role-graph) | **v1.5 if admin-authoring pressure** | v1 = capacity-internal. |
| L5-NEW-10 (cross-task SCMS context) | **L4-v2 evaluation** | Same as L4-22. |
| L5-NEW-11 (Memory cluster secondary indexes) | **v2 if query volume** | — |
| L5-NEW-12 (L0 audit-log cross-link on episode) | **L4-v2 evaluation** | — |
| L5-NEW-13 (Falkor query indexes) | **Phase 49 R0** (PB-HHH) | — |
| L5-NEW-14 (physical-layout optimization) | ~~Phase 46 R0~~ **resolved-default at Phase 46** (PB-AAA deferred) | Default taken = Chat B schemas as-written; optimization remains a v2 watch item. |
| L5-NEW-15 (admin cross-Local memory search tooling) | **v2 follow-up** | — |
| L5-NEW-16 (`dream.exploration` plural-strategy catalog) | **FOL_INSTALLATION_CHAT** | FOL plural-strategies. |
| L5-NEW-17 (episode-level promotion flow) | **v2 follow-up** | — |
| L5-NEW-18 (cross-replan blame chain reconstruction) | **MAINTENANCE_CHAT or debug tooling chat** | — |
| L5-NEW-Q1 (KL retention TTL backstop policy) | **L0/KL follow-up chat** | Coordinated with L0_SUBSTRATE_CHAT; v1 picks default; refine post-Phase-48 monitoring. |
| L5-NEW-Q2 (Falkor checkpoint mechanism) | ~~Phase 46 R0~~ **durable Falkor checkpoint store deferred → v1.5** | Continuous vs phase-boundary periodic; Phase 48 shipped tombstone/startup-scan crash recovery, not the durable store. |
| L5-NEW-Q3 (Episode storage growth thresholds) | ~~Phase 48 R0~~ **monitoring shipped Phase 48 (instrumentation); thresholds → v1.5** | `monitoring.py` exposes the instrumentation; exporter thresholds set when v1.5 retention policy lands. |
| L5-NEW-Q4 (aggregator capacity catalog v1) | **WSD_INSTALLATION_CHAT — scheduled Phase 54** (real `planning.*` catalog incl. aggregation; `WSD_INSTALLATION_PHASE_MAP.md` §2 WSD-4, 2026-06-10) | sum/max/last/concat — first consumer triggers. |

---

*End of L5_FUTURE_WORK.md. Last updated 2026-06-02 post Chat C plan-authoring closure; staleness pass 2026-06-11 (L0-26/PB-RT cascade added; Phase 46/48 future-tense rows flipped).*
