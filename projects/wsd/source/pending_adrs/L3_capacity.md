# L3 Capacity Layer — Updates from WSD Goal-Finalization

**For:** Resuming the L3 Capacity design chat with goal-finalization decisions loaded.
**Source:** `WSD_GOAL_FINALIZATION_OUTPUT.md` (project root). All items here are PROPOSED — ratification happens in the L3 design chat.

## How to use this file

Paste this file into the L3 design chat as loading context. Then work through:
- **§A** — ADRs to formalize.
- **§B** — schema / code changes to land in `mindsos_capacity` and L3 modules.
- **§C** — interfaces L3 must expose to other layers.
- **§D** — open sub-questions to resolve before implementation.

---

## §A — Required ADRs

### A.1 — Capacity graph: DataStates as nodes, capacities as (hyper)edges

L3's capacity graph is structured as:

- **Nodes = DataStates** (named, schema'd; uses `mindsos_capacity/datastate.py`'s `DataState` class with `ShapeDescriptor`).
- **Edges = capacities** (operations consuming one or more source-DSes and producing a target-DS).
- **Multi-input / multi-output capacities are hyperedges** (per L1-PROPOSAL-2).
- **Path = traversal**: ordered sequence of capacity-edges; start at DS, follow edge, arrive at next DS, etc.

The graph itself is the long-lived structure. Most "updates" are additions of new nodes (DSes) or new edges (capacities); the graph grows monotonically. Modifying nodes/edges in place is rare and admin-approved (per L1-PROPOSAL-3).

Path validity at registration: `edge[i+1].source_ds == edge[i].target_ds` using DS-node identity (not just structural compatibility).

Capacity discovery (UC-14) = identifying needed edges between existing DSes that no current edge supplies.

### A.2 — DataState identity registry layered on `mindsos_capacity/datastate.py`

- DSes registered with a unique name; the name is the node identity in the capacity graph.
- Structural shape (`ShapeDescriptor`) describes *what* the DS contains.
- Two DSes with structurally identical shapes but different names are distinct nodes (e.g. `text.tokens` vs. `text.pos_tagged_tokens`).
- `validate_datastate` extends to check name uniqueness on registration.
- `strict_compatible` continues to operate at the structural level.

### A.3 — Capacity contracts: typed markers (`unhandled_inputs`, `conflict-marker`, `fallback`)

Every L3 capacity (atomic and composed) must conform to:

- For inputs it can handle: produce the typed output DS.
- For inputs it cannot handle: emit `unhandled_inputs` as a typed structured output (not an exception).
- When **consuming** a coexistence-DS (per L1-PROPOSAL-3 migration): detect semantic conflict and emit `conflict-marker`. Path executor reads `DS.fallback` and uses predecessor form for that invocation.
- When **producing** a coexistence-DS: populate the `fallback` property with the predecessor-DS-form of the same data (embedded-copy representation per L1 decision).

Marker schema (minimum fields):
- `unhandled_inputs`: capacity ID, input DS reference, reason code, judgment-confidence.
- `conflict-marker`: consumer-capacity ID, conflicting DS reference, conflict-reason code, severity.

### A.4 — Promotion-rule capacities A–F as L3 ops

Six promotion-rule capacities ship in v1. Each consumes (incumbent-path, candidate-path, outcome-histories) and produces (promote/reject decision + rationale):

- **A. Single-metric threshold** — promote when chosen metric exceeds incumbent by X% over N runs.
- **B. Pareto-frontier multi-metric** — promote only if pipeline dominates incumbent on ≥1 metric without losing on others.
- **C. Composite score** — weighted blend of frequency, outcome quality, calibration drift.
- **D. Statistical-significance threshold** — paired bootstrap or similar.
- **E. Shadow deployment / tournament** — head-to-head live comparison.
- **F. Admin-discretionary with metric panel** — manual review.

L4 auto-selects per case (L4-PROPOSAL-1); admin overrides.

### A.5 — Calibration-aware-training as a v1 L3 capacity

- v1 L3 ships at least one calibration-aware-training capacity.
- Consumes (training-evidence DS, current-parameters DS), produces (updated-parameters DS).
- Applies calibration-aware loss (Brier, ECE-regularized, temperature scaling, or hybrid — concrete choice TBD in design chat).

### A.6 — User-authored atomic capacity contract

End-user-authored atomic capacities (Python DSL, sandboxed at L0 per L0-PROPOSAL-3) conform to the same L3 contract as built-in atomics:

- Typed input + output DSes (referenced from named-DS registry per A.2).
- Conform to A.3 (markers).
- Run inside Server-layer Python sandbox.
- Registered as new edges in the capacity graph; subject to L1-PROPOSAL-3 modification rules.

### A.7 — v1 L3 atomic capacity inventory

All ship in v1:

- `tokenize` — text → token list.
- `dep_parse` — tokens → parsed-text with dependencies + POS.
- `lexicon_query` (multi-metric: Resnik selectional association + PMI + conditional probability) — given lemma/POS, return candidate senses + correlations from L2 lexicon.
- `wsd_init` — calibrated multi-candidate sense distributions per content word.
- `fol_init` — derive logical implications from sense distributions.
- `frame_init` / `frame_match` — match candidate frames + fillers from text + sense distributions.
- The five SCMS monitors: `wsd_update`, `fol_update`, `frame_match` (monitor variant), `retrieval`, `cross_word`.
- `msur` — Multi-Source Update Resolver.
- `class_generalization` — DOLCE + WordNet hypernym hybrid + per-hierarchy learnable weights.
- `calibration_aware_training` — per A.5.
- `multi_candidate_calibrated_output` — produces ranked candidates with confidence scores when ambiguity is genuine.
- Six promotion-rule capacities A–F per A.4.
- Admin-extensibility capacities: `schema_add`, `axiom_add`, `capacity_add`, `path_add`, `supersedes`.
- Layered contradiction detection (G) — surface checks (E + F) at add-time; deeper checks (B + D) in dream cycles.

### A.8 — v1 L3 composed (orchestration) capacity inventory

- **SCMS** — BSP turn execution invoking init capacities + monitors + MSUR until pair-wise quiescence.
- **NLU full path** — `tokenize → dep_parse → wsd_init → frame_init → fol_init → SCMS-monitors → calibrate-output`, with inter-graph hops handled by path engine.
- **ALS** — full audit pipeline orchestrating all six signal sources (S1-S4, S6, S8) + dream-fan-out + multi-metric validation + admin panel + versioned apply.

---

## §B — Required schema / code changes in `mindsos_capacity`

### B.1 — Named-DS registry

- New module: named-DS registration + lookup.
- Extend `validate_datastate` to enforce name uniqueness.
- Two DSes with same name must have identical `ShapeDescriptor`; conflicting registrations rejected.

### B.2 — Capacity-edge registration in graph

- New module: capacity-edge registration as L1 hyperedge with role-labeled endpoints.
- Each edge: capacity ID, ordered input-DS roles, output-DS role(s), version, signature, atomic-vs-composed flag.
- Atomic capacity records: Python algorithm reference (built-in module path or user-authored sandbox handle).
- Composed capacity records: `edge_sequence` of sub-edge IDs (inlined per L2-PROPOSAL-1 value-typed paths).

### B.3 — Capacity contract enforcement

- All capacities (built-in and user-authored) registered with marker-emitting interface.
- Path executor branches on markers: `unhandled_inputs` → Phase 6 capacity-gap classifier; `conflict-marker` → fallback-property read.
- Producer contract: capacity outputs validated to populate `fallback` when target DS is in coexistence migration.

### B.4 — v1 atomic capacity implementations

Each capacity in §A.7 needs an implementation in `mindsos_capacity` or a sub-module:

- WSD-init: scoring engine combining Resnik + PMI + cond-prob with Bayesian update.
- FOL-init: forward-chaining inference over DOLCE axioms + sense-derived predicates.
- Frame-init: FrameNet-frame matching with sense distribution + parsed-text input.
- SCMS monitors: each is a state-change-driven emitter (state subscription + computation + signal output).
- MSUR: multi-source signal partitioning + contradictory branching + per-monitor evaluator.
- Class generalization: DOLCE traversal + WordNet hypernym lookup + hierarchy weights.
- Calibration-aware training: pick from Brier / ECE-reg / temperature / hybrid (TBD).
- Multi-candidate calibrated output: aggregation across scorer outputs with calibration normalization.
- Promotion-rule capacities A–F: each consumes (incumbent, candidate, outcome-history) → decision.
- Layered contradiction detection: E + F implementations (cheap surface checks).

### B.5 — SCMS orchestration capacity

- BSP turn execution loop.
- Monitor invocation order: state-change-driven emission.
- Pair-wise quiescence detection.
- Max-iteration cap (TBD in design chat).
- Returns refined sense distributions + frame elements + FOL atoms after quiescence.

### B.6 — User-authored atomic capacity registration support

- Capacity registration accepts (signature, Python algorithm, DS-input list, DS-output list).
- Algorithm validated at registration: parseable + signature-compatible.
- Sandbox handle stored in registry for runtime execution at L0.

---

## §C — Interfaces L3 exposes to other layers

- **To L4:** capacity registry (lookup by ID); path executor invocation; SCMS orchestration handle; ALS pipeline composition; promotion-rule capacity invocation.
- **To L2:** read access to L2 sub-graphs through capacity execution (capacities consume L2 data); write access for ALS-driven `learned-parameters` updates.
- **To L0:** capacity registry write API for user-authored capacities; sandbox execution interface.
- **To L1:** capacity-edge registration as hyperedge with version metadata; named-DS registry primitives.

---

## §D — Open sub-questions for L3 design chat

1. Capacity granularity — admin/designer discretion per goal-finalization, but design chat should set conventions for built-in capacity granularity.
2. Calibration-aware-training mechanism choice — Brier / ECE-reg / temperature / hybrid.
3. Multi-output capacity convention — single hyperedge with multiple targets, or split into multiple capacities.
4. SCMS BSP turn cap (maximum iterations before forced termination).
5. Per-capacity comparison-metric standard interface (admin/designer discretion per goal-finalization, but a default interface helps).
6. Marker schema details — exact serialization format for `unhandled_inputs` and `conflict-marker`.
7. Layered contradiction-detection thresholds — when does a near-match count as conflict at F (local consistency) check.
8. SCMS monitor priority / signal partitioning specifics in MSUR.
9. Performance budgets — latency targets for full NLU path execution.
10. Cross-validation by sub-path substitution (Phase 6) — alternative-edge registry minimum size for v1.

---

**End of L3 updates.**
