# L1 Core — Future Discussions & Work

**Date:** 2026-06-01 (updated post L1/L3 reframe chat closure)
**Status:** Living index.

---

## 1. WSD-driven architectural reframes (routed here per user Q2 = route reframes to L1/L3 chat)

| # | Item | Source | Owner chat / Status |
|---|---|---|---|
| ~~L1-1~~ | ~~**Capacities-as-hyperedges** architectural reframe~~ | WSD C-L1-2 + C-L3-1 | **CLOSED 2026-06-01 — ADR-0156 picks bipartite (Option A); not hyperedge** |
| L1-2 | **Schema-declared layers** (lexicon theoretical layers) — L1 primitive supporting L2 lexicon multi-layer semantics | WSD `coordinated_change_L1_intergraph_and_layers.md` §4 | L2 chat / future L1 chat |
| L1-3 | Path-engine inter-graph traversal — WSD path-finding crosses graph boundaries | WSD `pending_adrs/L1_core.md` §B | Future L1 chat |
| L1-4 | Named-DataState registry | WSD `pending_adrs/L1_core.md` §B | Absorbed into ADR-0158 (realm convention) — partial close |
| L1-5 | Reproducibility primitives for path execution | WSD `pending_adrs/L1_core.md` §B | Future L1 chat |

---

## 2. Internal naming reconciliation

| # | Item | Source | Owner chat / Status |
|---|---|---|---|
| ~~L1-6~~ | ~~**`IntergraphEdge` vs `InterGraphEdge` naming**~~ | HANDOFF §6.3; WSD C-L1-1 | **CLOSED 2026-06-01 — `IntergraphEdge` (shipped lowercase form) preserved; WSD installation absorbs at authoring time** |

---

## 3. New items from L1/L3 reframe chat closure (2026-06-01)

| # | Item | Source | Owner |
|---|---|---|---|
| L1-7 | **`IntergraphEdgeInstance` Phase 06 amendment** — `mindsos_instances` ships new instance subclass driven by ADR-0156 D38 = A bipartite reframe + Chat B D-B40 capacity-MM schema | ADR-0156 cascade | Phase X3 ship |
| L1-8 | **`IntergraphHyperEdgeInstance` Phase 06 amendment** — Chat B cascade gap absorbed: Chat B D-B41 (Pipeline composition via IntergraphHyperEdge) implied this instance class but didn't enumerate it | ADR-0156 cascade + Chat B drift catch | Phase X3 ship |
| L1-9 | **L1 schema IntergraphEdgeType for produces/consumes** — deferred to L1-3 future L1 chat; ADR-0156 validates at L3 register-time; v1 doesn't gate on L1 schema | ADR-0156 PB-D38-1 §11 | Future L1 chat |

---

## 4. Other Phase 38 carry-forwards touching L1

None directly — L1 carry-forwards from Phase 38 are absorbed into L2/L3 buckets. L1 Phase 11 closed with schema migration + integrity scanner.

---

## 5. Open coordination questions

| # | Question | Source / Status |
|---|---|---|
| ~~L1-Q1~~ | ~~If L1-1 is adopted, does `mindsos_instances` need new instance subclasses?~~ | **RESOLVED 2026-06-01 — yes, `IntergraphEdgeInstance` + `IntergraphHyperEdgeInstance` ship per L1-7 + L1-8** |
| L1-Q2 | Schema-declared layers (L1-2): does this require extending `mindsos_core/schema.py` or is it a metagraph-level property? | Open |

---

## 6. Chat C closure routing (2026-06-02)

Chat C plan-authoring closed 2026-06-02 (`confirmation_docs/POST_PHASE_38_PHASE_MAP.md`). Routing of open L1 items:

| Item | Routed to | Notes |
|---|---|---|
| L1-2 (Schema-declared layers) | **Future L1 chat** | Triggered by WSD installation surfacing concrete need (lexicon theoretical layers). |
| L1-3 (Path-engine inter-graph traversal) | **Future L1 chat** | No live consumer in Phase 39-49. |
| L1-4 (Named-DataState registry) | **Partial close** via ADR-0158 (Phase 40) | DataState realm convention covers naming; runtime registry deferred. |
| L1-5 (Reproducibility primitives) | **Future L1 chat** | No live consumer in Phase 39-49. |
| L1-7 (`IntergraphEdgeInstance` Phase 06 amendment) | **Phase 42 (X3)** | Ships per ADR-0156 cascade. |
| L1-8 (`IntergraphHyperEdgeInstance` Phase 06 amendment) | **Phase 42 (X3)** | Ships per Chat B D-B41 cascade gap absorbed into ADR-0156. |
| L1-9 (L1 IntergraphEdgeType for produces/consumes) | **Future L1 chat** | ADR-0156 validates at L3 register-time; v1 doesn't gate on L1 schema. |
| L1-Q2 (Schema-declared layers L1 mechanism) | **Future L1 chat** | Bundled with L1-2. |

---

## 7. Skill-acquisition-driven items (2026-06-18)

| # | Item | Source | Owner / Status |
|---|---|---|---|
| L1-10 | **Intra-graph / standalone-Graph compositional hyperedge.** Whole ⊣ {ordered, named parts} composition (e.g. `Cell ⊣ {Coordinate@position, ColorSymbol@color}`; `blackbird ⊣ {black, bird}`). **Finding:** the shipped `IntergraphHyperEdge` already supports this **same-graph** — `Metagraph.add_intergraph_hyperedge` enforces graph-existence per anchor/member but has **no cross-graph requirement** (unlike binary `IntergraphEdge` step 3 and `MetaHyperEdge`'s `len(graph_ids) ≥ 2`). With `compositional=True` (⇒ `ordered=True`, immutable per P8-A) it meets the full contract (one whole anchor, N ordered member parts, provenance-walkable). **So the genuine gaps are narrow:** (a) composition on a **standalone `Graph` not inside a metagraph** (plain `HyperEdge` has no `compositional`/`anchors`/`members`/`ordered`); (b) an ergonomic wrapper + naming so "intra-graph composition via a same-graph IntergraphHyperEdge" reads cleanly; (c) bless same-graph IntergraphHyperEdge as the sanctioned intra-graph composition mechanism. | Skill Acquisition manual §10 + `intelligence_demo/arc1/SOLVE_PIPELINE.md` (Pending primitive); char↔word + compound-word motivation | Future L1 chat; consumer-pinned by the ARC skill (contract first, build when pinned) |

---

*End of L1_FUTURE_WORK.md. Last updated 2026-06-18 (L1-10 skill-acquisition composition item).*
