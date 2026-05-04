# Intergraph Edge — Design Note

> **Status:** Open question (PHASE_MAP §7 Q13). **Affects Phase 05.**
> **Raised:** 2026-05-04 by Henrique, during Phase 03 chat.
> **Adjudication required:** before Phase 05 implementation begins.
> **Default if not adjudicated:** defer indefinitely; close with status-quo
> (alignments-as-graph + XRef + MetaHyperEdge).

---

## 1. The proposal

A **fourth** edge primitive in L1 Core: a node↔node edge that crosses
graph boundaries *within a single metagraph*. Distinct from every
existing graph-spanning construct in L1.

| Construct | Endpoints | Container | Phase |
|---|---|---|---|
| `Edge` | Node ↔ Node | one Graph | 03 |
| `HyperEdge` | n × Node | one Graph | 03 |
| `MetaEdge` | Graph ↔ Graph | one Metagraph | 05 |
| `MetaHyperEdge` | n × Graph | one Metagraph | 05 |
| `CompositionalMetaEdge` | Graph ↔ Graph (unwraps to internal members) | one Metagraph | 05 |
| `XRef` | Node ↔ Node | *across* metagraphs | 09 |
| **`IntergraphEdge` (proposed)** | **Node ↔ Node** | **one Metagraph (across two graphs in it)** | **TBD** |

The gap the proposal would fill: a Person node in `people` graph wants
to point at a School node in `institutions` graph, both inside the
same metagraph, *without* reifying the relationship as a third-party
node in an `attendance` graph.

---

## 2. Phase-placement options

### 2.1 Ship in Phase 03 (alongside Edge / HyperEdge)

**Pros**
- Structural symmetry with `Edge`.
- All graph primitives live in `mindsos_core/models/`.

**Cons**
- Phase 03 has no `Metagraph` (Phase 05) — the type the edge needs to
  live inside doesn't exist.
- Persistence / snapshot / schema implications can't be designed
  without 05 / 07 context.
- Expands a phase already doing a port.

### 2.2 Discuss + design in Phase 05; ship if greenlit *(recommended)*

**Pros**
- Metagraph context exists.
- Sits next to MetaEdge / MetaHyperEdge where the design question
  actually arises ("do we need *node*-level graph-spanning edges in
  addition to graph-level meta-edges?").
- ADR can be drafted with the full primitive set on the table.
- Persistence implications can be scoped before Phase 07.

**Cons**
- Design discussion delays a phase that already has 4 primitives.

### 2.3 Fold into XRef as a generalization (Phase 09)

Lift XRef from "cross-metagraph" to "cross-graph", with
intra-metagraph as a special case.

**Pros**
- One primitive instead of two.
- Existing XRef repository / loader / refcount machinery extends.

**Cons**
- XRef's whole design point is "the target is somewhere I can't see
  synchronously" — that's not true for nodes in the same metagraph.
- Collapsing them muddies the contract.
- ADR-0128 / 0142 would need rewrites.

### 2.4 New dedicated phase between 05 and 07

**Pros**
- Clear ownership.

**Cons**
- PHASE_MAP renumbering is expensive (many cross-references).
- Doesn't change the fact the design discussion is a Phase 05 question.

### 2.5 Defer indefinitely; close with status-quo

Status quo: alignments-as-a-graph + reification. Each cross-graph
relationship is a third-party node in a dedicated graph (e.g.
`alignments`) that carries refs to both endpoints. This is what
L2 actually does today.

**Pros**
- Zero L1 surface change.
- Existing pattern works and is in active use across DOLCE / OEWN /
  FrameNet / Alignments importers.

**Cons**
- Extra hop on every cross-graph traversal.
- Reification feels heavy for "this Person attends this School."

---

## 3. Recommendation

**Phase 05 — discuss, draft ADR, then decide whether to ship.** The
design questions only have answers once Metagraph exists. Don't
decide now; pre-commit a design slot in Phase 05.

---

## 4. Pushbacks against adding the primitive at all

These argue for the default-defer outcome. The Phase 05 chat must
answer each before greenlighting.

### 4.1 Cypher persistence has no home

Today: `(:Graph)-[:OWNS]->(:Node | :Edge | :HyperEdge)`. Which graph
`OWNS` an intergraph edge?

- **Source's graph?** Asymmetric — target's graph doesn't see the edge in
  its `OWNS` traversal.
- **Both graphs?** Duplication; integrity scanner needs new rules to
  reconcile.
- **The metagraph?** New ownership relation `(:Metagraph)-[:OWNS]->`,
  breaks "graph is the unit of locality" invariant.

This is an ADR question, not an implementation question.

### 4.2 Snapshots break per-graph locality

Each graph reconstructs independently today. An intergraph edge means
reconstructing graph A pulls in a node from graph B that A doesn't own.
Either:

- Snapshots become metagraph-scoped → cascades into Phase 10's
  `MetagraphSnapshot` design, which ADR-0129 *already narrowed* to
  release-ship only.
- Intergraph edges are excluded from snapshots → they're second-class.

### 4.3 Schema validation has no answer

Phase 04's `EdgeType.allowed_source_types` / `allowed_target_types`
validates against the *containing graph's* schema. An intergraph edge
has two schemas:

- Pick one (which? source's graph?) → asymmetric.
- Require both → when do you align? Schema-evolution becomes coupled.
- Invent a metagraph-level schema → expands Phase 04 surface significantly.

### 4.4 OCC / WAL ownership becomes ambiguous

Phase 07's W1–W6 mitigations assume edge writes are graph-scoped
(per-graph mutex / lock granularity). Cross-graph edges either:

- Hold two locks → deadlock surface.
- Escalate to metagraph-level lock → contention ceiling.

### 4.5 Migration cost vs user-visible win

L2 alignments are *already* nodes in an `alignments` graph that
reference nodes in `oewn` / `dolce` / `concepts` via ref properties
(which become XRef in Phase 09). Adding native intergraph edges means
migration of:

- DOLCE importer (Phase 15)
- OEWN importer (Phase 15)
- FrameNet importer (Phase 15)
- Alignments importer (Phase 15)
- The `alignments` role-graph schema (Phase 13)

User-visible win: "save one hop on alignment traversal." Worth all of
the above?

### 4.6 Existing constructs may already cover the use case

Three existing patterns handle "cross-graph" already:

- **(a) Reification via 3rd-party graph** (alignments pattern, status quo).
- **(b) `MetaHyperEdge`** if you only need graph-level association.
- **(c) `XRef`** if you'll tolerate the cross-metagraph framing for an
  in-metagraph case.

Before designing a 9th primitive, force a use case that none of these
three serves cleanly.

---

## 5. Concrete asks before Phase 05 begins

If the Phase 05 chat surfaces this and the user wants to proceed:

1. **Write down ≥ 3 concrete use cases** for IntergraphEdge that the
   alignments-graph pattern doesn't already serve. ("Save a hop" alone
   is not a use case.)
2. **Specify whether endpoints in different graphs is *intentional*** vs
   an artifact of role-graph splitting. If the latter, the answer is
   "merge the graphs."
3. **Pick a Cypher OWNS resolution** (§4.1) before ADR drafting begins.
4. **Decide snapshot scope cascade** (§4.2): expand `MetagraphSnapshot`
   or accept second-class status.

If any of these is unanswered, the recommendation is to defer.

---

## 6. Cross-references

- PHASE_MAP §7 Q13 — the canonical open-question entry pointing here.
- Phase 05 row — flagged with this design question; cannot proceed until
  adjudicated.
- ADR-0128 / 0142 — XRef design (§2.3 alternative interaction).
- ADR-0129 — `MetagraphSnapshot` scope narrowing (§4.2 interaction).
- ADR-0017 — Schema strict validation (§4.3 interaction).
- ADRs 0121–0127 — Persistence / WAL / OCC (§4.4 interaction).

---

*Document owner: Phase 05 chat. Updated by adjudicating chat with
final decision (ship vs defer) + linked ADR if ship.*
