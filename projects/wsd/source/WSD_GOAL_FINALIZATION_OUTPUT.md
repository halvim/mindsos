# WSD Goal-Finalization — Output Summary

**Date:** 2026-04-30
**Origin:** WSD goal-finalization chat (forked from WSD design chat).
**Purpose:** Consolidated output to paste back into the WSD design chat. Captures the final goal statement, the architectural framing decisions made during goal-finalization, the v1 scope under those decisions, the disposition of all twelve original goal-discussion items, the pending topics queue, and pointers to companion artifacts.

---

## 1. Final goal statement

**MindsOS aspires to eventually match or surpass LLMs across the targeted text-task domain, recognizing that v1 ships as a foundation and surpassing is a multi-decade compounding outcome of the flywheel.**

Operational decomposition (the four functions from the original reformulated goal, retained):

1. Updates beliefs given new evidence.
2. Knows what it doesn't know (calibrated multi-candidate output, capacity-gap surfacing).
3. Explicit auditable representations.
4. Handles novel inputs by class-grounded generalization.

The differentiator vs LLMs is not output quality on day one. It is *auditability + calibration + on-the-fly updates without retraining + compounding capacity acquisition*. v1 ships the foundation that supports compounding; production parity with LLMs is a multi-decade flywheel outcome.

---

## 2. Foundational framing (decided in this chat)

### 2.1 Learner-not-knower

MindsOS is architected as a **learner**, not a knower. v1 cold-start coverage is acceptable. Three knowledge inflows: (1) admin curation, (2) user-driven teaching, (3) internal discovery via dreaming. Success is measured by *learning velocity* — the cleanliness of teach → promote → dream cycles — not initial coverage.

### 2.2 Knowledge ≡ capacities (not text statistics)

For MindsOS, **knowledge** is the union of (graph facts in L2 sub-graphs) and (capacities — operations that acquire and manipulate those facts). Text is the human-facing communication channel; the system's internal "language of the mind" is capacities applied to data. Distinct from LLMs, which encode knowledge implicitly as text statistics.

### 2.3 Capacity granularity is recursive

A capacity at abstraction level N is composed of capacities at level N-1, down to atomic L3 operations as the base case. "Atomic" is relative. WSD is composed of sub-capacities (lexicon-query, sense-scoring, calibration, etc.) but at the NLU layer, WSD is itself a single capacity. NLU is a composition of WSD + FOL + Frame + further capacities added over time.

### 2.4 LLM relationship

LLMs are external benchmarks for admin-driven evaluation. Not a v1 system component. MindsOS provides audit + reproducibility affordances (per-capacity I/O extraction, standalone capacity/pipeline execution, deterministic re-run) so admin can run external comparisons. No LLM-specific code, prompts, parsers, or comparison machinery in v1.

### 2.5 Cat-equivalent boundary

v1 is text-only. Perception, action, embodied state are out of v1 (post-v1, robotic deployment).

### 2.6 v1 = bedrock; flywheel post-v1

v1 ships hand-crafted L3 atoms + seed knowledge + the architecture for the flywheel. The teach-promote-dream loop runs at low velocity in v1 (admin-driven). Volume and self-driven loops mature post-v1.

---

## 3. Architectural framing (decided in this chat)

### 3.1 Capacity graph structure

- **Nodes = DataStates** (named, schema'd; `mindsos_capacity/datastate.py` ShapeDescriptor + a named-DS registry layered above).
- **Edges = capacities** (typed transformations from one or more source-DSes to a target-DS).
- **Multi-input / multi-output capacities are hyperedges** (uses L1 Core's hyperedge primitives).
- **Path = traversal** through the graph; ordered sequence of capacity-edges.
- The graph itself is the long-lived structure. Most "updates" are additions of new nodes (DSes) or new edges (capacities); the graph grows monotonically. Modifying existing nodes/edges in place is rare and admin-approved (DS modification + capacity-edge replacement protocol below).

### 3.2 Paths are value-typed

- "Paths-of-paths" composition is **registration-time shorthand only**, not a runtime reference.
- When user composes P_new = P1 + C, the system inlines P1's current edge sequence into P_new's storage.
- After registration, paths have no reference dependencies. If P1 is updated, P_new's content is unchanged.
- No cascade re-evaluation; no reference-graph staleness. Dream improvements at one composition level do not auto-propagate to higher levels — admin/system schedules per-level dreams.
- Registration-time equivalence detection rejects/links duplicate atomic sequences.
- Registration-time expression metadata is recomputed on graph updates (display-only).

### 3.3 Inter-graph traversal

**Path-engine-handled** (decision B). Paths can cross multiple L2 sub-graphs via metaedges; the path executor manages graph context, capacities stay graph-local. **Needs L1 ADR** — see `pending_adrs/L1_core.md`.

### 3.4 DS modification + capacity-edge replacement protocol

Three-phase migration:

1. **Pre-flight audited validation.** Admin reviews cascade enumeration + representative-task replay; approves or rejects.
2. **Coexistence rollout with `fallback` property.** DS2' carries an internal `fallback` property populated with the DS2-form of the data (embedded copy; v1 default). On semantic conflict (signaled by consuming-capacity-emitted `conflict-marker`), per-invocation runtime fallback to the DS2-form. Aggregate fallback frequency monitored separately by L4 for migration-phase decisions.
3. **Deprecation.** Once aggregate fallback frequency stays below threshold for N cycles or M tasks, DS2 retired; fallback property removed from DS2'.

**Constraint:** no nested fallback chains. Maximum one fallback per DS at any time. If a second migration is needed before the first deprecates, the new target replaces the prior intermediate.

### 3.5 Promotion model

- All six promotion-rule options A–F are L3 capacities. L4 auto-selects per case; admin can override.
- Promotion criterion: result quality (outcome metrics), not frequency alone.
- Consumer-coupling regime: **R3 phased** — internal-metric-only WSD promotion in v1.0; consumer-coupled metrics added as FOL/Frame stabilize; v2 full multi-consumer.

### 3.6 Outcome metrics

- All metrics measured every cycle as capacities (ECE, Brier, NLL, top-k, Coverage@τ, gold-set drift, per-domain breakdowns).
- Active promotion uses a subset chosen by the active promotion rule.
- **Calibration-aware training is a v1 commitment** — required for honest "I don't know" output.

### 3.7 Dream model

- Dreams = **recomposition** over the existing capacity graph (not truth-seeking).
- Anchor: **task outcomes** (the stable evaluator).
- Dreams **fan out** — each cycle generates multiple recomposed variants, each maximizing a specific outcome metric. Admin compares via panel and selects.
- Dream priorities are user-editable in the minimal UI; can specify any of: goal-to-optimize, metric-to-maximize, path-to-vary, weight-on-cycle-resources.
- Per-level independent dreaming — improvements at one composition level do not auto-propagate; admin/system schedules dreams across levels.

### 3.8 Knowledge organization

- L2 sub-graphs in v1: `ontology`, `lexicon` (theoretical + empirical layers), `concepts`, `alignments`, `memories`, `promoted-pipelines`, `task-patterns`, `problem-trace`, `capacity-state`, `sense-correlations`, `learned-parameters`, **`world-axioms`** (new in v1).
- Every knowledge node carries provenance metadata: `source`, `source_version`, `extraction_pipeline_version`, `add_timestamp`, `confidence`/`trust_level`, `superseded_by`.
- Knowledge versioning + supersedes for in-place updates.
- Schema is admin-only (instances are user-addable; new schemas require admin).

### 3.9 Contradiction detection (v1 policy)

**Layered (option G):**

- Cheap surface checks at add-time: source-disagreement (E) + local consistency (F).
- Deeper checks (FOL B, defeasible C, empirical D) in dream cycles for thoroughness.
- Admin escalation for ambiguous cases.

### 3.10 v1 minimal UI

- Admin UI (full surface): schema editor, axiom editor, capacity editor (Python DSL for atomics), path editor, query interface, audit-trail viewer, knowledge browser, supersedes/version-history viewer, contradiction queue, dream-variant comparison panel (multi-metric tradeoff), capacity-gap report queue, decision-rationale logging.
- End-user UI: same surface scoped to Local metagraph + dream-priority editing + audit on own Local.
- Per-user training preferences in L0 server settings (opt-in/opt-out, audit-policy override more-conservative-only).

### 3.11 User-authored capacities

End-users can add atomic L3 capacities by declaring DataState-in, DataState-out, and the transformation algorithm in Python. Sandboxed at Server layer (resource limits, restricted imports, typed error containment). Same registry contract as built-in atomics.

---

## 4. v1 scope (final)

### 4.1 Bootstrap knowledge

- **Lexicon (theoretical):** OEWN.
- **Lexicon (empirical):** SemCor + OntoNotes (commercial license) + FrameNet + VerbNet + SemLink + GlossTag. Multi-metric per edge (Resnik selectional association + PMI + conditional probability).
- **Ontology:** DOLCE (mandatory).
- **Concepts:** FrameNet frames + frame relations.
- **Alignments:** VerbNet + SemLink cross-resource maps.
- **`world-axioms`:** ConceptNet distilled (CC-BY-SA legal review path).
- **Class generalization:** DOLCE + WordNet hypernym hybrid + per-hierarchy learnable weights.

### 4.2 Atomic L3 capacities in v1

Tokenize, dep-parse, lexicon-query (multi-metric), WSD-init, FOL-init, Frame-init / Frame-match, the five SCMS monitors (`wsd-update`, `fol-update`, `frame-match`, `retrieval`, `cross-word`), MSUR, class generalization, calibration-aware training, multi-candidate calibrated output, six promotion-rule capacities (A–F), schema-add, axiom-add, capacity-add, path-add, supersedes, layered contradiction-detection, reproducibility infrastructure, per-invocation `conflict-marker` + `fallback` reading.

### 4.3 Composed / orchestration capacities in v1

- **SCMS** (BSP turn execution until pair-wise quiescence).
- Full v1 NLU path: `tokenize → dep-parse → wsd-init → frame-init → fol-init → SCMS-monitors → calibrate-output`.
- **ALS** with all six signal sources (S1 self-distillation, S2 gold anchor, S3 FOL disagreement, S4 ensemble agreement, S6 task outcome, S8 replan divergence) + dream-fan-out + multi-metric validation + admin panel + versioned apply.
- **Phase 6** blame attribution at path-segment granularity + cross-validation by sub-path substitution.
- **Six-phase task lifecycle.**
- **L4 migration orchestration** — pipeline eligibility + aggregate fallback monitoring + Phase 2/3 transitions.

### 4.4 What v1 ships vs. doesn't ship

v1 ships the **architecture and infrastructure** functionally complete. It does not ship:

- Production-grade calibration tuning (parameters at hand-set defaults).
- Production-grade UI polish (functional minimum only).
- Bullet-proof scale handling (designed for single-instance / small-team use).
- Pre-loaded demo content (task-solving demos are post-implementation).
- Solved end-tasks (architecture supports them; solving specific tasks is post-v1 work).

The 16 use cases in `WSD_USE_CASES.md` serve as **architectural validation**, not production benchmarks. Passing UC-1 through UC-16 confirms the architecture works; production performance comes later.

### 4.5 LLM relationship in v1

LLM is **external** to v1. No system integration, no prompt templates, no comparison machinery. Admins/designers run LLM comparisons externally using standard tooling and feed insights back via the standard add-knowledge / add-capacity / add-pipeline UI flows.

---

## 5. 12-items disposition (final)

| # | Item | Disposition | Notes |
|---|---|---|---|
| 1 | New-lexical-item ingestion | **Per original handoff** — admin-add via UI in v1; auto-hypothesis pipeline post-v1 | Not a new deferral |
| 2 | Compositional semantics | **Out of v1** | Future NLU capacities discovered reactively via UC-14 pattern |
| 3 | World knowledge beyond senses | **Addressed in v1** | New `world-axioms` sub-graph + ConceptNet distillation |
| 4 | Discourse-level processing | **Per original handoff** — `cross-word` monitor stub in v1; full discourse post-v1 | Not a new deferral |
| 5 | Active learning / question generation | **Out of v1** | Reactive admin-driven only; proactive HITL post-v1 |
| 6 | Pragmatics / intent inference | **Out of v1** | Future capacity, post-v1 |
| 7 | Non-text grounding | **Out of v1** | Cat-equivalent boundary; robotics deployment |
| 8 | Knowledge-scale strategy | **Answered** | Learner-not-knower + commercial-licensed empirical lexicon + flywheel post-v1 |
| 9 | Self-improvement ceiling and oracle quality | **Answered** | Task-outcome anchor + multi-metric panels + admin discretion |
| 10 | Deep reasoning chain machinery | **Out of v1** | Future capacities discovered reactively via UC-14 |
| 11 | Belief-update latency | **Answered** | Per-level dream cycles + per-invocation fallback; no separate fast-belief tier |
| 12 | LLM complementarity | **Answered** | LLM external; system provides audit + reproducibility affordances |

---

## 6. Pending topics (to be picked up in layer-specific design chats)

- **L1:** inter-graph traversal ADR; capacities-as-hyperedges ADR; DS-modification protocol ADR.
- **L2:** value-typed promoted-pipelines schema ADR; Local↔Global visibility ADR; schema-conformance validation ADR.
- **L3:** capacity-graph structure ADR; DS identity registry ADR; capacity contracts (`unhandled_inputs`, `conflict-marker`, `fallback`) ADR; promotion-rule capacities A–F ADR; calibration-aware-training capacity ADR; user-authored-capacity contract ADR.
- **L4:** promotion-rule auto-selection logic ADR; dream priority schema ADR; per-level dream scheduling ADR; data-vs-capacity-gap classifier ADR; Phase 6 path-segment blame ADR; SCMS-as-orchestration-capacity ADR; migration phase orchestration ADR.
- **L0/Server:** minimal user UI scope ADR; schema-conformance validation ADR; user-authored-capacity sandbox ADR; cross-domain admin governance ADR (post-v1).
- **Cross-cutting deferred sub-decisions:**
  - Capacity granularity (admin/designer discretion).
  - Per-capacity comparison metric standard interface (admin/designer discretion).
  - Concrete rollout policies for migration coexistence (random sampling, traffic-based, capability-flag).
  - Aggregate fallback signal thresholds (rollback-threshold, deprecation-threshold).
  - Conflict-marker and unhandled-inputs schema details.
  - Cascade size cap heuristics for migrations.

See `pending_adrs/` directory in the project folder for the per-layer ADR proposals as starting points.

---

## 7. Companion files

- `WSD_USE_CASES.md` — 16 architectural stress-test use cases (UC-1 through UC-16). UC-6 revised; UC-11 through UC-16 added in this chat.
- `MINDSOS_DEMO_EXAMPLES.md` — synthetic-domain demo examples for testing the learning loop. Post-v1 priority.
- `MINDSOS_BUSINESS_PROBLEMS.md` — commercial use case catalog for vertical pilot planning. Post-v1 priority.
- `pending_adrs/` — per-layer ADR proposals (L0, L1, L2, L3, L4) capturing decisions that need ratification in layer-specific design chats.

---

## 8. What changed vs. the original handoff

The original `WSD_GOAL_FINALIZATION_HANDOFF.md` framed twelve items for scoping. This chat converted that into:

- **Architectural reframes** that go significantly deeper than the handoff envisioned: capacity-graph structure, value-typed paths-of-paths, three-phase DS migration, layered contradiction detection, dream fan-out across multiple metrics, per-invocation fallback, path-engine-handled inter-graph traversal.
- **Scope additions to v1:** minimal user UI (originally cut from v1), `world-axioms` sub-graph (new), six promotion-rule capacities, calibration-aware training, all of ALS's six signals + dream-fan-out, full Phase 6 with path-segment blame, full migration coexistence machinery.
- **Goal statement reformulation:** from "complement, not substitute" → "match or surpass over multi-decade compounding."
- **LLM relationship clarification:** from "12 different design decisions" → "LLM is external; v1 has no LLM integration."
- **Item dispositions:** 12 items resolved as detailed in §5.

---

**End of summary.**

Paste sections 1, 2, 3, 4, 5 directly into the WSD design chat to resume design work with the goal-finalization context loaded. Sections 6, 7, 8 are reference material.
