# Pending ADRs from WSD Goal-Finalization Chat (2026-04-30)

This folder contains per-layer files capturing decisions surfaced during the WSD goal-finalization chat that need ratification in the appropriate layer-specific design chat. Each file is **paste-ready** for resuming the relevant layer's design conversation.

## Files

- `L0_server.md` — orthogonal Server layer (auth, sessions, audit, minimal UI, sandbox).
- `L1_core.md` — graph / metagraph primitives, intergraph traversal, DS migration protocol.
- `L2_knowledge.md` — knowledge-role metagraph, `world-axioms` sub-graph, value-typed promoted-pipelines.
- `L3_capacity.md` — capacity graph (DSes as nodes, capacities as hyperedges), atomic capacity contracts, user-authored capacity sandbox contract.
- `L4_intelligence.md` — orchestration, promotion-rule selection, dream scheduling, blame attribution, migration phase orchestration.

## File structure (each file)

Every layer file follows the same structure:

- **§A — Required ADRs.** Decisions to formalize and document as numbered ADRs in `mindsos/docs/decisions/adr/`.
- **§B — Required schema / code changes.** Concrete modifications to land in the layer's modules.
- **§C — Interfaces exposed to other layers.** Cross-layer contract additions.
- **§D — Open sub-questions.** Items the design chat must resolve before implementation.

## How to use

1. Open the relevant layer's design chat (or start a new one).
2. Paste the relevant file's contents as initial context (also reference `WSD_GOAL_FINALIZATION_OUTPUT.md` for the broader picture).
3. Work through §A → §B → §C → §D in order. §A drives ADR drafts; §B drives code/schema changes; §C drives interface contracts; §D is the live discussion list.
4. As ADRs are drafted and ratified, port them to `mindsos/docs/decisions/adr/` with proper numbering and remove from this file.

## Status

All items in these files are **PROPOSED** as of goal-finalization closure (2026-04-30). Status moves to:
- **ACCEPTED** when ratified in the layer design chat and committed to numbered ADR.
- **REJECTED / SUPERSEDED** if the design chat finds a better approach.
- **DEFERRED** if scoped out of v1.

Update each item's status in this folder until they're all ported into the canonical ADR location.

## Companion artifacts (project root)

- `WSD_GOAL_FINALIZATION_OUTPUT.md` — full output summary; load alongside the per-layer file.
- `WSD_USE_CASES.md` — 16 architectural stress-test use cases.
- `MINDSOS_DEMO_EXAMPLES.md` — synthetic-domain demo examples (post-v1 priority).
- `MINDSOS_BUSINESS_PROBLEMS.md` — commercial use case catalog (post-v1 priority).

---

**End of README.**
