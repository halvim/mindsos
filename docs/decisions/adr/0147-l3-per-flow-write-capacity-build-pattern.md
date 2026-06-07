---
title: Per-flow build pattern for L3 write capacities
status: Accepted
date: 2026-04-27
layer: L3
---

# ADR-0147: Per-flow build pattern for L3 write capacities

**Status:** Accepted (flipped Proposed → Accepted at Phase 35 ship per
§amendment-1; halvim, 2026-05-27)

**Date:** 2026-04-27

**Related:** ADR-0145 (per-target write categories), ADR-0146 (write invocation contract), ADR-0143 (`KLWriteHandle`), ADR-0138 (KL drops write API).

## Context

ADR-0138 + ADR-0145 commit to relocating KL's shipped writes (and adding net-new write capacities for the upper-layer role-graphs) into L3. Six minimum capacities are needed for L4 v1:

- `capacity:consolidate:mm` (memories)
- `capacity:trace:problem` (problem-trace)
- `capacity:promote:pipeline` (pipelines via server)
- `capacity:promote:pattern` (patterns via server)
- `capacity:state:capture` (capacity-state)
- `capacity:author:concept` (concepts; templates for lexicon/alignment follow)

Building all six up front means designing each in a vacuum (without a real L4 consumer). The opposite extreme — building just-in-time as L4 hits each role — risks unbounded fragmentation. The pattern question: which side errs?

## Decision

**Per-flow build.** Each write capacity is built when the L4 flow that consumes it closes design.

- L4 design proceeds flow-by-flow (consolidation flow → pipeline-finder flow → triage flow → dreaming flow → etc.).
- When a flow closes, the L3 capacities it requires get built and tested as part of that flow's PR (or immediately preceding it).
- Schemas for the role-graph the capacity writes also tighten in the same pass (per the `DESIGN_UPPER_LAYER_ROLES.md` 2-week-no-edit rule).
- Tests for the capacity exercise the failure modes of ADR-0146.

### Recommended sequence

The flow order is L4's call, but a defensible default:

1. **Consolidation flow** → `capacity:consolidate:mm`. Memories are read by retrieval capacities; building memories first unblocks retrieval testing.
2. **Pipeline-finder flow** → `capacity:promote:pipeline` + `capacity:promote:pattern`. These wrap server functions; lightweight L3 work.
3. **Trace flow** → `capacity:trace:problem`. L4's failure-handling loop needs this.
4. **Author flow** → `capacity:author:concept` (+ lexicon, alignment templates). User-driven; can lag others.
5. **State capture flow** → `capacity:state:capture`. Last; needed only when L4 supports capacity-state snapshots.

### What "build" means per capacity

For each capacity:

- L3 capacity node + IRI per ADR-0145 category.
- Implementation following ADR-0146 contract (`WriteOutcome` return).
- Uses `KLWriteHandle` per ADR-0143.
- Calls KL validators (ADR-0139) in preconditions.
- Tests: success path + each failure mode in §"Failure-mode table" of ADR-0146.
- L1 mutation primitives (`add_node`, `add_xref`, etc.) called directly through `handle.graph()`.
- Schema for the target role-graph tightens to the level the capacity exercises.

### Existing KL writes — relocation order

The shipped `add_local_node`, `add_local_edge`, `add_local_alignment` correspond to `capacity:author:concept` / `capacity:author:lexicon-entry` / `capacity:author:alignment`. They relocate as part of step 4 (author flow), not sooner. KL retains them with `DeprecationWarning` until the author flow lands, so existing 217 tests don't break in the meantime.

## Rationale

Per-flow build avoids vacuum design. Each capacity gets a real consumer that tells it what fields, what failure modes, what idempotence semantics matter. Designing six capacities in advance based on speculative L4 needs invites rework.

The risk with per-flow is sequencing pressure: L4 design might block on capacity availability. Mitigation: each capacity is small (~100–200 LOC + tests); building one is a day-scale task, not a week-scale one. The L4 chat can include capacity build in the same PR as the flow it serves.

The pre-existing KL writes (author-side) keep working under deprecation warnings until the author flow closes. This means the relocation is not all-or-nothing — existing tests stay green throughout the migration window.

## Consequences

**Good:**

- No vacuum design; each capacity matches a concrete consumer.
- L4 design and L3 capacity design happen in lockstep, eliminating contract mismatches.
- Schemas tighten flow-by-flow alongside capacities; one cognitive load per pass.
- Existing 217 KL-write tests keep passing until the author flow lands.

**Tradeoffs:**

- L4 chats grow by carrying L3 capacity work. Acceptable: capacities are small.
- "Where's the full list of L3 write capacities?" has no single source of truth until all six land. Mitigation: track in `docs/dev/coordinated-changes/L3-capacity.md` as flows close.
- The deprecation window for shipped KL writes (`DeprecationWarning`s) is open-ended until step 4. Acceptable: warnings are visible in CI; backlog item on the L4 roadmap.
- `capacity:state:capture` may lag indefinitely if L4's capacity-state design stays contested.

## Alternatives considered

1. **Build all six up front.** Rejected — vacuum design; rework risk.
2. **Build one reference capacity as template; defer rest.** Considered. Defensible but doesn't address the "design vs reality" mismatch — the reference capacity is still vacuum-designed. Per-flow gets each one matched to its consumer.
3. **Build per-role-graph (not per-flow).** Rejected — same role-graph can be touched by multiple L4 flows with different requirements; flow is the right unit.
4. **Build all capacities now as stubs (no implementation); fill in per flow.** Considered. Useful for surfacing the shape early. Held — risk that stubs ossify into wrong contracts before consumers exist.

## Implementation references

- Per-flow tracking: `docs/dev/coordinated-changes/L3-capacity.md` — table of (flow, capacity, status).
- KL deprecation: add `DeprecationWarning` to `add_local_node`, `add_local_edge`, `add_local_alignment`, `promote`, `similarity_report` immediately (covered by code-scaffolding pass).
- `docs/HANDOFF_L3_WRITE_DESIGN_2026-04-27.md` lists the 6 capacities with status and owners.
- ADR moves to Accepted when (a) at least 2 capacities are built per-flow and shipped, (b) the per-flow tracking page is populated, (c) the deprecation warnings on shipped KL writes are visible in CI.

## §Implementation (Phase 33 — partial; halvim, 2026-05-26)

Phase 33 ships TWO write capacities per the per-flow build discipline
(narrow-scope Pick at Phase 33 design Round 0 PB-1):

- `capacity:consolidate:mm` — for the L4 consolidation flow (TBD).
- `capacity:trace:problem` — for the L4 trace flow (TBD).

§Accept criterion (a) PARTIALLY satisfied — 2 capacities built; per-flow
framing is *anticipatory* (capacities exist before L4 flows that consume
them, so the contract may amend when first consumer surfaces). The
remaining 4 capacities (promote:pipeline, promote:pattern, author:concept,
state:capture) defer to their L4-flow phases per the §Decision pattern.

§Accept criterion (b) satisfied — `halvim_mindsos/docs/dev/coordinated-changes/
L3-capacity-write-flows.md` NEW page populated with 6 rows (2 shipped, 4
deferred).

§Accept criterion (c) — VACUOUS for halvim. Halvim's KL never shipped the
write API (ADR-0138 honoured by absence at Phase 14 per PB-6;
`add_local_node` / `add_local_edge` / `add_local_alignment` / `promote` /
`similarity_report` were never present). There is nothing to deprecate;
no DeprecationWarning fires in CI. This criterion is held vacuously
satisfied for halvim builds.

**Status stays Proposed** until either (a) the remaining 4 capacities
ship per-flow, OR (b) per-flow framing is amended after first L4
consumer surfaces. ADR-0147 flips Accepted at the later of those.

## §Implementation (Phase 34 — partial; halvim, 2026-05-26)

Phase 34 R0 PB-9 + R1 PB-B: per-flow discipline is honoured at the
IRI-builder registry level. `_IRI_BUILDERS` in `mindsos_knowledge/
identifiers.py` ships with EXACTLY 2 entries (the 2 shipped write
capacities' roles — `ROLE_EPISODIC_MEMORIES` + `ROLE_PROBLEM_TRACE`; renamed from `ROLE_MEMORIES` per Phase 39 ADR-0044 §amendment-3). Phase 35+
adds entries alongside `capacity:promote:pipeline` etc. as flows close.
The registry is the right pattern but the population is deliberately
minimal — the alternative (pre-populating all 7 upper-layer role
entries) was rejected as YAGNI + violates per-flow discipline (registry
entries imply wired capacities; an unused entry would suggest a wired
capacity that doesn't exist).

**Status stays Proposed.** Phase 35 is the canonical flip target per
`halvim_mindsos/confirmation_docs/PHASE_MAP.md` §35.

(Phase 35 ship update: Status now Accepted per §amendment-1 below.)

**Stub-phase carve-out vs §Decision alternative #4.** Phase 33's stub
capacities resemble the rejected "build all six as stubs" alternative
in tone but differ in substance: only 2 capacities ship (not all 6),
their bodies are NOT vacuum-designed mock implementations (they call
the contract-typed `KLWriteHandle` which raises until Phase 34 wires
it), and input shapes are explicitly deferred via opaque placeholder
DataStates (R1 PB-B Pick). Phase 34's body fill happens AS the L4
flow design closes — preserving the per-flow discipline at the body
level even though the capacity declaration ships at Phase 33.

## §amendment-1 (Phase 35 ship; halvim, 2026-05-27 — flip Proposed → Accepted)

ADR-0147 Status flipped Proposed → Accepted at Phase 35. Three clauses
close the §Acceptance gate and lock the per-flow rule going forward.

**Clause 1 — §Acceptance criterion (a) clarified, NOT rewritten.**
Per the §Implementation Phase 33 + 34 footers' existing "anticipatory"
characterization, the 2 shipped capacities
(`capacity:consolidate:mm` + `capacity:trace:problem`) **shipped
through the `KLWriteHandle` contract surface** (`writeable() →
mint_iri() → write_and_validate()`) and exercise the contract
end-to-end. That is the contract-viability evidence §Acceptance
criterion (a) was gating on. The anticipatory framing is hereby
PROMOTED from descriptive §Implementation footer caveat to binding
§Accept-satisfying evidence: "built per-flow and shipped" reads as
"shipped through the contract surface", and anticipatory + per-flow
both satisfy (a).

§Acceptance criterion (b) — tracker page populated — already
satisfied at Phase 33 (`docs/dev/coordinated-changes/L3-capacity-write-flows.md`
shipped with 6+ rows; updated each phase a capacity moves).

§Acceptance criterion (c) — KL deprecation warnings visible in CI —
remains vacuously satisfied for halvim per §Implementation Phase 33
footer (KL never shipped the write API to begin with; nothing to
deprecate).

**Clause 2 — Anticipatory carve-out (Phase 33+34 capacities).**
`capacity:consolidate:mm` and `capacity:trace:problem` are explicitly
classed as **anticipatory**: they shipped before their consuming L4
flows (consolidation flow + trace flow) closed design. Their tracker
rows stay `wired` (no new legend state); the tracker page's "Note"
subsection cross-references this clause for the provenance context.
This is a one-time exception: the next L3 write capacity must wait
for its L4 flow per Clause 3.

**Clause 3 — Per-flow discipline strict going forward.** All future
L3 write capacities (the 4 currently `deferred` rows in the tracker
— `capacity:promote:pipeline`, `capacity:promote:pattern`,
`capacity:author:concept`, `capacity:state:capture` — and any new
category) ship **only after their consuming L4 flow closes design**.
The §Decision wording remains binding; no anticipatory builds are
permitted post-Phase 35.

## §Implementation (Phase 35 — Accepted; halvim, 2026-05-27)

ADR-0147 Status flipped Proposed → Accepted at Phase 35. §amendment-1
clauses 1-3 close §Acceptance criterion (a) via the
"shipped-through-contract-surface" reading. Per-flow build remains
strict for the 4 deferred capacities; tracker page
(`docs/dev/coordinated-changes/L3-capacity-write-flows.md`) is the
canonical "where's the full list" source per §Consequences mitigation.

Phase 35 is **design-only**: zero source changes, zero new write
capacities, zero new exports. ADR + PHASE_MAP §35 inline-amendment +
tracker note + sentinel tests are the entire ship surface.

Cross-phase note: Phase 36 (ADR-0139, validator home) does NOT
re-open ADR-0147; semantic validators integrate into the existing
shipped capacities' bodies + `write_and_validate` per ADR-0139 §Decision,
under the per-flow discipline locked here.

## §Amendment (Phase 42 — ADR-0159)

The per-flow build pattern is unchanged; only the context access path becomes typed. Body migration deferred to Phase 46 (PB-23).
