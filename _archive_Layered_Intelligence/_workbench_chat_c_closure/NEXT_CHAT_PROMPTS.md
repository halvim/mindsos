# Next-Chat Prompts (post Chat A closure)

**Date:** 2026-05-29
**Status:** Chat A (L4 design-resolution) closed 2026-05-28. Four follow-on chats can open. Three are parallelizable; Chat C waits for the others.

This file holds copy-paste-ready prompts for each chat. Each prompt is self-contained at the top but points to files (rather than repeating content) so future chats can audit the full state.

---

## Sequencing reminder

```
                    (Chat A — CLOSED)
                    /     |          \
            (parallel: any/all of B, reframe, L2)
            /            |            \
       Chat B         L1/L3        L2 chat
       (L5)          reframe       (path-mut +
                     (D36/D38/      role-graph
                      D46/D48)      schemas)
            \            |            /
             \           |           /
                    (all complete)
                         |
                    Chat C (plan-authoring)
                         |
            WSD installation, FOL installation,
            DWF installation, etc.
```

---

## Prompt 1 — Chat B: L5 Design + Note-Fork Decision

````
You are running **Chat B — L5 design-resolution + note-fork decision**, the
second of the multi-chat sequence that follows Chat A (L4 design-resolution,
closed 2026-05-28).

## Project rules (inherited from MindsOS project instructions)

Skeptical reviewer mode. Pushbacks > agreement. Options + pros/cons + your
pick for every substantive decision. Concise prose; no filler. After each
sign-off, reanalyze with skeptical eye and surface missed pushbacks until
saturation (R-rounds produce impl-locks only, zero reversals).

## Required reading at chat open (in this order)

1. `MindsOS/HANDOFF.md` — current project state. Especially §3.1.5 (Chat A
   closure summary) and §4 (L5 design state).
2. `MindsOS/docs/_workbench/CHAT_A_DECISIONS.md` — full L4 settlement record
   from Chat A. The L4 contract that L5 must satisfy.
3. `MindsOS/docs/_workbench/CHAT_PLAN_L4_L5.md` — multi-chat plan; explains
   Chat B's scope and dependencies.
4. `MindsOS/docs/dev/l5_mental_model_design_notes.md` — full L5 design notes.
   Pay special attention to §3.4 (2026-04-26 amendment — Option A note-fork
   pick + the gating implication).
5. `MindsOS/docs/_workbench/L5_FUTURE_WORK.md` — items already routed to
   Chat B (especially L5-1, L5-2, L5-3 — note-fork scope decision).
6. `MindsOS/docs/_workbench/L4_FUTURE_WORK.md` — note dependencies that
   touch L5 (L4-21 FOL #1 watch, L4-22 cross-task SCMS v2).
7. Search for `PIVOT_V1_SCOPE_2026-04-26.md` — referenced by L5 §3.4 but
   may be missing (dangling link per mkdocs probe). If present, read it.

## Chat B scope (your job)

You inherit the L4 contract verbatim. Your job is to settle L5 v1 such
that (a) it satisfies the L4 contract and (b) the note-fork gating
decision is resolved.

Concretely:

- **L5-1 (load-bearing):** Note-fork mechanism scope decision. Three sub-
  options per L5 §3.4: (A) pull note-fork forward into v1 from server-
  pivot-v2 scope; (B) sequence L5 v1 after server-pivot v2 ships;
  (C) redesign L5 retention without note-fork (Options B/C from L5 §3.4).
- **L5-2:** If (A), coordinate with L0 server-pivot-v2 chat scope.
- **L5-3:** If (C), pick L5 §3.4 Option B (accept auto-upgrade; cognitive
  parallel breaks) or Option C (inline content copy; storage explosion).
- **L5 settled inheritance:** L4 writes continuously to MM; retention
  default; failure recording via ref:problem_trace; Global + Local L5;
  retrieval is L3 not L5. Confirm or contest.
- **MSUR ledger** lives in MM during execution (per WSD §5.4); persistence
  beyond task completion is v2 per Chat A R4 PB-R4-15. Confirm.
- **Replan history records on MM root** (per Chat A R4 D14) + per-segment
  provenance (per R3). Confirm.
- **Hint set captured on MM as NodeInstances** (per Chat A R3 hint
  system). Confirm MM schema for hint nodes.
- **R5 (L5 design open question)** Partial-MM consolidation on crash —
  resolve or defer to L4-implementation.
- **R3 (L5 design open question)** Cross-user Global L5 promotion criteria
  — defer to first cross-user feature or pick now.

## Out of scope

- L4 architecture (settled in Chat A — do not relitigate).
- Phase-numbering / sentinel chain / R0 mechanics (Chat C plan-authoring).
- L1/L3 reframes (separate L1/L3 reframe chat).
- L2 schema amendments (L2 chat).

## Outputs expected

- Revised `docs/dev/l5_mental_model_design_notes.md` reflecting picks.
- New `docs/_workbench/CHAT_B_DECISIONS.md` capturing per-decision rationale
  + cascades. Same shape as `CHAT_A_DECISIONS.md`.
- Updated `docs/_workbench/L5_FUTURE_WORK.md` with R-round-derived cascades.
- Updated `docs/_workbench/L0_FUTURE_WORK.md` if note-fork ships v1 (L0
  prereq).
- Updated `MindsOS/HANDOFF.md` §4 with Chat B closure summary.

## First response shape

1. Confirm required reading consumed (terse paths list).
2. Surface R0 — open questions, missed decisions, or framing concerns.
3. Stop. Wait for user re-litigation cue before R1.

Apply Chat A's saturation discipline: each round produces options +
pushbacks; user signs off; reanalyze; iterate until impl-locks only.
````

---

## Prompt 2 — L1/L3 Reframe Chat

````
You are running the **L1/L3 reframe chat**, handling four architectural
supersessions routed in by Chat A (closed 2026-05-28). This chat can run
in parallel with Chat B (L5) and the L2 chat.

## Project rules

Skeptical reviewer mode. Pushbacks > agreement. Options + pros/cons + your
pick for every substantive decision. Saturation discipline (zero reversals
on reanalysis = saturated round).

## Required reading at chat open

1. `MindsOS/HANDOFF.md` §2 (shipped L1 + L3 state) + §3.1.5 (Chat A closure).
2. `MindsOS/docs/_workbench/CHAT_A_DECISIONS.md` — full L4 settlement. The
   reframe items at R6 (D36, D38, D46, D48) state Chat A's directional
   preferences but do NOT ratify — your chat ratifies.
3. `MindsOS/docs/_workbench/L1_FUTURE_WORK.md` — L1-1 through L1-6 (reframes
   + naming reconciliation).
4. `MindsOS/docs/_workbench/L3_FUTURE_WORK.md` — L3-1 through L3-49 (reframes
   + new families + thread-safety audit + capacity registration contract
   changes).
5. `MindsOS/docs/dev/l4_intelligence_design_notes.md` for L3/L4 boundary
   context.
6. `MindsOS/projects/wsd/source/coordinated_change_L1_intergraph_and_layers.md`
   and `coordinated_change_L3_capacities_and_monitors.md` — WSD's proposed
   reframes in detail.
7. Phase 27 shipped state — read `mindsos_capacity/capacity_layer.py`,
   especially `CapacityLayer` and resident lifecycle code (`start_resident`,
   `stop_resident`, `_subscriptions`).
8. Phase 31 shipped state — same files; resident subscriptions design.

## Chat scope

Four routed decisions inherited from Chat A R6 (direction stated; you
ratify):

- **D36 — Monitor lifecycle ownership.** Phase 31 supersession: move from
  L3-owned residents to L4-owned Monitors. Chat A preference: retire L3
  `start_resident` / `stop_resident`. Plus L3-32 thread-safety audit.
- **D38 — Capacities-as-hyperedges.** Phase 27 supersession: capacities as
  hyperedges with DataStates as nodes. Major architectural reframe;
  cascades L1 + L3 + L4 invocation dispatch.
- **D46 — Universal `unhandled_inputs` contract.** Every L3 capacity MUST
  implement; Phase 27-33 audit required.
- **D48 — DataState taxonomy expansion.** Catalog domain-specific
  DataStates: NLU (DS_FRAME_INSTANCES, DS_FOL_ATOMS, DS_NLU_FULL_ANNOTATION),
  code (DS_CODE_AST, DS_CALL_GRAPH, DS_INTENT), cross-realm bridges.

Plus the L3 family additions Chat A authored that need formal contract:

- L3-32: Phase 27-33 thread-safety audit (`concurrent=True/False` annotation).
- L3-33: Decision/scoring capacity family (~15-20 new capacities from R1
  strict line).
- L3-34: Capacity registration contract gains `concurrent` + `inline` flags
  + optional `precondition_iri` + `effect_iri` (action contracts).
- L3-35: L3 capacity non-DataState return values (formalize for decision /
  scoring / metric / combination / comparator / evaluator / validate
  families).
- L3-36: Predicate L3 capacity family.
- L3-37 through L3-49: ALS + hint + process + adapter + promotion-rule +
  precedent retrieval + typed CapacityContext + cross-realm adapter
  families (all per Chat A R3-R5).

## Out of scope

- L4 architecture (settled).
- L5 design (Chat B).
- L2 schema amendments (L2 chat).
- Plan-of-record (Chat C).

## Outputs expected

- New ADRs for each supersession (Phase 27 reframe, Phase 31 reframe).
- `docs/_workbench/L1_L3_REFRAME_DECISIONS.md` per-decision rationale.
- Updated `L1_FUTURE_WORK.md` and `L3_FUTURE_WORK.md`.
- Migration plan for shipped capacities (Phase 27-33) — audit results +
  annotation rollout.
- New L3 capacity contract spec (`concurrent` + `inline` + action contracts +
  `unhandled_inputs`).
- Updated `HANDOFF.md` with reframe chat closure summary.

## First response shape

1. Confirm required reading consumed.
2. Surface R0 — note any conflicts between Chat A direction and shipped
   code reality. Map the 4 routed items to concrete supersession ADRs.
3. Stop. Wait for re-litigation cue.

This chat is likely multi-round and substantial in scope. WSD installation
chat is downstream — coordinate sequencing with Chat C plan-authoring.
````

---

## Prompt 3 — L2 Chat

````
You are running the **L2 chat**, handling path-mutability and L2 role-graph
schema amendments routed in by Chat A. Can parallelize with Chat B and
L1/L3 reframe chat.

## Project rules

Skeptical reviewer mode. Pushbacks > agreement. Options + pros/cons + pick.
Saturation discipline.

## Required reading at chat open

1. `MindsOS/HANDOFF.md` §2.2 (shipped L2 surfaces) + §3.1.5 (Chat A closure).
2. `MindsOS/docs/_workbench/CHAT_A_DECISIONS.md` — full L4 settlement; the
   L2 schema implications are throughout R3-R6.
3. `MindsOS/docs/_workbench/L2_FUTURE_WORK.md` — L2-1 through L2-27.
4. ADR-0150 + ADR-0094 — affected by Chat A picks.
5. `MindsOS/projects/wsd/source/coordinated_change_L2_lexicon_layers_and_role_graphs.md`
   for WSD's L2 proposals.
6. `MindsOS/projects/wsd/source/pending_adrs/L2_knowledge.md` for 8 §A
   pending ADRs.
7. Phase 13 shipped schemas — read `mindsos_knowledge/schemas/` and
   `mindsos_knowledge/identifiers.py`.

## Chat scope

- **L2-27 (D47 routed):** Path-mutability decision —
  mutable-with-version-history vs immutable-with-successor-IDs. Chat A
  preference is immutable-with-successor-IDs (advisory). You ratify.
- **L2-23:** `parameter-staging` + `pending-promotions` schemas (ALS v1
  role-graphs).
- **L2-25:** `promoted-pipelines` schema v2 — 5-state status enum
  (draft/tested/active/quarantined/retired) + `paired_pipelines` +
  `serves_task_types` many-to-many. ADR-0094 amendment (pipelines binary,
  no confidence field).
- **L2-26:** `task-patterns` schema v2 — `relevant_hints: list[IRI]` +
  `mapping_confidence_threshold: float` + `sufficient_predicate_iri: IRI` +
  `domain: str` field.
- **L2-1 through L2-8:** Role-graph additions — `sense-correlations`,
  `learned-parameters`, `parameter-staging`, `pending-promotions`,
  `capacity-gaps`, `world-axioms`, `training-runs` (FOL chat scope),
  `fol-rules` + `fol-ledger` (FOL chat scope).
- **L2-11:** Alignment role-graph naming reconciliation (3 conventions in
  shipped code — pick canonical form).
- **L2-19:** `domain_tag` on lexicon edges.
- **L2-22:** Memory schema extension for per-segment provenance.
- **L2-24:** Bootstrap-importer suite checklist.
- **ADR-0150 §am-1 amendment:** role-graph bound (currently 8 named +
  alignment-prefix). Plan single "L4-driven role-graph expansion" ADR
  covering all additions.

## Out of scope

- L4/L5 design.
- Reframes (L1/L3 reframe chat).
- L0 admin tooling (L0 chat).
- Plan-of-record (Chat C).

## Outputs expected

- New ADRs for L2 schema v2 (promoted-pipelines, task-patterns, etc.).
- ADR-0150 §am-1 amendment for role-graph expansion.
- `docs/_workbench/L2_CHAT_DECISIONS.md`.
- Updated `L2_FUTURE_WORK.md`.
- Coordinated with L1/L3 reframe chat output if their reframes affect L2
  primitives.
- Updated `HANDOFF.md` with L2 chat closure summary.

## First response shape

1. Confirm reading.
2. Surface R0 — schema decisions interact (e.g., FOL #4 split affects
   `learned-parameters` + `parameter_set_iri` everywhere). Map dependencies.
3. Stop. Wait for re-litigation cue.
````

---

## Prompt 4 — Chat C: Plan-Authoring (PHASE_MAP analog)

````
You are running **Chat C — plan-authoring**, the final chat producing
`L4_L5_PHASE_MAP.md` analogous to PHASE_MAP.md (the L0-L3 plan). Inherits
settled outputs from Chats A + B + L1/L3 reframe chat + L2 chat.

## Pre-flight check

Do NOT open until ALL of these are complete:
- Chat A (L4 design-resolution) — closed 2026-05-28.
- Chat B (L5 + note-fork) — closure required.
- L1/L3 reframe chat — closure required for at least D36 + D38 + D46.
- L2 chat — closure required for L2-25 + L2-27 + ADR-0150 §am-1 amendment.

If any are unfinished, abort and wait. Do not author phases against unsettled
foundations (R0-PB-1 pattern).

## Project rules

Skeptical reviewer mode. Options + pros/cons + pick. Saturation discipline.

## Required reading at chat open

1. `MindsOS/HANDOFF.md` — current state with all prior closures noted.
2. `MindsOS/confirmation_docs/PHASE_MAP.md` — the L0-L3 plan; format
   reference for what you're producing.
3. `MindsOS/confirmation_docs/PHASE_38_DESIGN_LOG.md` §4 — 19-item L0-L3
   carry-forward (this is your starting backlog stream A).
4. `MindsOS/docs/_workbench/CHAT_A_DECISIONS.md` — L4 settlement.
5. `MindsOS/docs/_workbench/CHAT_B_DECISIONS.md` — L5 settlement.
6. `MindsOS/docs/_workbench/L1_L3_REFRAME_DECISIONS.md` — reframe settlement.
7. `MindsOS/docs/_workbench/L2_CHAT_DECISIONS.md` — L2 settlement.
8. All `MindsOS/docs/_workbench/L*_FUTURE_WORK.md` files — full cascade
   backlog accumulated across prior chats.
9. `MindsOS/confirmation_docs/L4_L5_PLAN_NEXT_CHAT_PROMPT.md` — R0 slate
   that drove the whole multi-chat sequence (the plan-mechanics PBs from
   that slate are Chat C's scope: PB-2, PB-5, PB-6, PB-7, PB-8, PB-11).

## Chat scope

Produce `confirmation_docs/L4_L5_PHASE_MAP.md` covering:

- Phased rollout for L4 v1 implementation (inheriting Chat A scope ~800-
  1200 LOC L4 + 15-20 L3 capacity families + 10 ALS subsystems +
  bootstrap importer suite).
- Phased rollout for L5 v1 (inheriting Chat B note-fork decision).
- L1/L3 reframe phases (inheriting reframe chat outputs).
- L2 schema migration phases (inheriting L2 chat outputs).
- WSD installation chat phasing.
- FOL installation chat phasing.
- DWF installation phasing (knowledge acquisition; can parallel).
- 19-item L0-L3 carry-forward absorption strategy (R0-PB-2 three-stream split).

Plus the L4/L5-plan-prompt R0 PBs not absorbed by other chats:

- **R0-PB-2:** Carry-forward absorption (3-stream split).
- **R0-PB-5:** Phase numbering (continue 39+ vs reset L4-00).
- **R0-PB-6:** Sentinel chain disposition.
- **R0-PB-7:** Cookbook gaps (nlu-slice.md + code-slice.md).
- **R0-PB-8:** Model C remediation timing (probe shows 16 warnings, not
  50; substance changed — see CHAT_A_L4_BASELINE.md).
- **R0-PB-11:** Ship-shape default (per-phase explicit PB at R0).

## Out of scope

- Any L4/L5/L1/L3/L2 architectural picks (settled by prior chats).
- WSD/FOL installation-chat detail (downstream).

## Outputs expected

- `confirmation_docs/L4_L5_PHASE_MAP.md` (the main deliverable).
- Updated `HANDOFF.md` §10 reading-map entry.
- Final closure marker on this multi-chat sequence; all prior `_workbench/`
  documents can be migrated to permanent homes (`confirmation_docs/`,
  `docs/dev/`, archive) per `_workbench/README.md` lifecycle.
- Per-stream tracking surface decisions:
  - Stream A (L0/L3 cleanup carry-forwards): GitHub issues vs mini-PHASE_MAP
    vs git log? (R0-PB-2 fuzzy)
  - Stream B (L4/L5/reframe phases): the main map.
  - Stream C (docs/mechanics): how tracked.

## First response shape

1. Confirm all prerequisite chats closed; if not, stop.
2. Confirm required reading.
3. Surface R0 — open questions for the plan structure (phase numbering,
   sentinel chain, ship-shape default, carry-forward streams).
4. Stop. Wait for re-litigation cue.

After this chat closes, MindsOS exits design-saturation mode and re-enters
phase-numbered code-shipping mode.
````

---

## How to use these prompts

1. Open the new chat (Cowork project = MindsOS).
2. Copy the relevant prompt block.
3. Paste as your first message.
4. The new chat reads its required files + opens its R0.

The prompts intentionally do NOT repeat content from settled files —
future chats verify state from the source, not from the prompt. This
prevents drift between prompts and actual settled documents.

---

*End of NEXT_CHAT_PROMPTS.md.*
