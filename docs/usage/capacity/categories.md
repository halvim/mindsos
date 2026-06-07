---
last_confirmed_phase: 33
---

# Functional categories

L3 partitions capacities into **13 functional categories** (ADR-0065 + ADR-0145 partial-flip at Phase 33). Every `Capacity` / `Monitor` / `Adapter` MUST declare exactly one home category; the IRI form `capacity:<category>:<name>` reflects it.

Each category gets its own role-graph (`capacity:<category>`) under both Global and Local metagraphs. The shared `capacity:datastates` role-graph (ADR-0064) sits alongside — one DataState node per shape, referenced by every category that produces or consumes it.

## The 13 categories

| Category | Constant | What lives here |
|---|---|---|
| Perception | `CATEGORY_PERCEPTION` | Surface parsing — raw text → tokens, sentences, spans |
| Comprehension | `CATEGORY_COMPREHENSION` | Lexical / syntactic understanding |
| Derivation | `CATEGORY_DERIVATION` | Logical / arithmetic derivation over known facts |
| Decomposition | `CATEGORY_DECOMPOSITION` | Splitting goals or problems into sub-problems |
| Combination | `CATEGORY_COMBINATION` | Joining partial results into larger structures |
| Path-finding | `CATEGORY_PATH_FINDING` | Graph traversal — shortest path, BFS, DFS |
| Retrieval | `CATEGORY_RETRIEVAL` | Reading from KL — concepts, lexicon, alignments |
| Scoring | `CATEGORY_SCORING` | Ranking / confidence over candidates |
| Trace | `CATEGORY_TRACE` | Reading **and writing** problem-trace records (`capacity:trace:problem` Phase 33) |
| Signalling | `CATEGORY_SIGNALLING` | Cross-capacity signalling — events, watches, broadcasts |
| Interaction | `CATEGORY_INTERACTION` | I/O at session boundary — user prompts, CLI input |
| Learning-methods | `CATEGORY_LEARNING_METHODS` | Parameter-update functions — the *learning* mechanics, not the *learned* state (which lives in L4) |
| **Consolidate** (Phase 33) | `CATEGORY_CONSOLIDATE` | Writing consolidated memories — MM CompositeInstance → ConsolidatedMemory record (`capacity:consolidate:mm`) |

The enumeration is canonical; `FUNCTIONAL_CATEGORIES` is the frozenset of all 13. Extending requires an ADR-0065 amendment.

!!! note "Write capacities — categories not yet shipped"
    ADR-0145 enumerates **5 per-target write categories**: `consolidate`
    (shipped at Phase 33 + first occupant), `trace` (existing category
    + first *write* occupant at Phase 33), `promote`, `author`, and
    `state`. Per ADR-0147 per-flow build discipline, `promote` /
    `author` / `state` defer to their L4-flow phases. See
    `docs/dev/coordinated-changes/L3-capacity-write-flows.md` for the
    tracker. ADR-0145 stays Proposed until all 5 categories ship.

!!! note "Alignment-lookup is a RETRIEVAL capacity, not a 13th category"
    Phase 15b PB-23 deferred this decision to Phase 28's design pass.
    Resolution: alignment-lookup reads alignment edges from KL's
    `alignments` role-graph — it is a retrieval capacity that ships in
    the `retrieval` category, not a new top-level category. See
    ADR-0065 §Implementation (Phase 28) for the closure.

## Picking the right category

* Read input, no derivation → **Perception** or **Comprehension**.
* Walk a graph → **Path-finding**.
* Score / rank → **Scoring**.
* Read from KL → **Retrieval**.
* Side-effect on the world → **Interaction** or **Signalling**.

When two categories seem to fit, pick the one your capacity's **output** belongs to (the consumer's perspective is what L4's pipeline-finder follows across the bipartite PRODUCES/CONSUMES edges per ADR-0156).

## Multi-graph membership (ADR-0085)

A capacity has exactly one **home** category (its IRI determines this), but may eventually appear as a member of additional category graphs. Phase 28 ships home-graph registration only; additional-membership API ships with first consumer (per ADR-0085 §Implementation).

## Topology + constraints

Capacity flow topology is the explicit **bipartite** `PRODUCES` /
`CONSUMES` IntergraphEdge set emitted at `register_capacity` time
(ADR-0156, Phase 42; supersedes the Phase 29 type-compatibility
auto-discovery substrate).
The 5-kind **CONSTRAINT** enforcement layer ships per ADRs
0068/0070/0092. The 12-category enumeration itself is stable.

## See also

* [Overview](overview.md) — `CapacityLayer` construction, registration, Local-wins.
* [Data states](data-states.md) — shapes referenced by `inputs` / `outputs`.
* [Building capacities](building.md) — substantive walkthrough lands at Phase 29 (deferred per PHASE_MAP doc-to-phase row).
