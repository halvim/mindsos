# Coordinated Change Handoff — L1 Core: `InterGraphEdge` Primitive + Schema-Declared Layers

**Date:** 2026-04-29
**Origin:** WSD subsystem design conversation (Word Sense Disambiguation project, Henrique Alvim).
**Purpose:** Surface two L1 Core extensions that the WSD design has surfaced as requirements. The L1 design chat should decide whether to ship together or sequence (see §6 below).
**Status:** Pre-implementation. Architectural specification only; no L1 code written yet.

---

## 0. How to use this document

Upload this document to the L1 design chat. It is self-contained — does not require WSD-design-chat context. The L1 chat should:

1. Read §1 (motivation) and §2 (summary) to orient.
2. Read §3 (`InterGraphEdge`) and §4 (Schema layers) for the concrete proposals.
3. Read §5 (coordinated implications across other layers) for ripple effects.
4. Read §6 (open questions for L1 to resolve) before designing.
5. Read §7 (what this does NOT change) to bound scope.
6. Decide on naming, persistence, ADR placement, ordering — all owned by L1.

---

## 1. Why this handoff exists

During WSD subsystem design, two L1 capabilities were identified as needed but absent (or under-specified) in the current L1 spec:

  1. **A typed cross-graph node-to-node edge primitive.** Existing L1 has `Edge` (intra-graph) and `MetaEdge` (graph-to-graph). Cross-graph node-to-node references currently rely on `ref:*` property prefix (ADR-0016), which works but loses graph-edge structure (no schema enforcement, no native traversal, no first-class edge identity).

  2. **A way to organize edges within a graph into named *layers* of purpose.** The lexicon graph in WSD design holds both *theoretical* relationships (hypernym, antonym, synset — from OEWN) and *empirical* relationships (co-occurrence, predicate-argument, frame-element — from corpus mining). These sets are conceptually distinct; admin tooling and per-subsystem queries benefit from being able to name and address them as units.

Both extensions surface from a specific design problem (WSD's sense-correlations integration with the lexicon graph) but generalize to recurring needs across MindsOS layers.

---

## 2. Summary

Two additive L1 changes:

  - **`InterGraphEdge`** — new edge primitive connecting two specific *nodes* from two *different graphs* within the same metagraph. Distinct from `Edge` (intra-graph) and `MetaEdge` (graph-to-graph). Coexists with `ref:*` properties (does not deprecate ADR-0016, though long-term migration could be considered).

  - **Schema-declared layers** — new Schema mechanism allowing edge types to be grouped into named layers. Each edge type belongs to exactly one layer (or to no layer = default). Layers enable layer-aware queries, admin tooling, and per-subsystem filtering. Backward compatible: schemas without layer declarations work as today.

Both changes are additive. No existing API contracts break. Existing primitives (`Edge`, `MetaEdge`, `ref:*`) retain current semantics.

---

## 3. Change 1 — `InterGraphEdge` primitive

### 3.1 Motivation

Three concrete use cases surface from current MindsOS design:

  - **Knowledge Layer (L2): Local→Global node references.** Currently uses `ref:*` properties + proxy nodes (per L2 §7 invariant I7). Works but lacks schema typing on the cross-graph link itself.
  - **Mental Model Layer (L5): MM instances reference L2 / L3 / L4 nodes.** Uses `ref:global_<role>=<iri>` properties. Same limitation.
  - **WSD subsystem design (this chat):** Originally needed for linking sense-correlations graph senses to lexicon graph senses. **This specific case has been resolved by collapsing to a single lexicon graph with layers (Change 2 below) — InterGraphEdge is no longer required for sense-correlations.** But the pattern recurs in the two cases above.

Without a typed cross-graph edge primitive, every layer above L1 reinvents the property-based pattern with bespoke conventions. A first-class primitive cleans this up.

### 3.2 Specification

`InterGraphEdge` is a new L1 primitive. Properties:

  - **Source node** — must be in some graph G_src.
  - **Target node** — must be in some graph G_tgt.
  - **G_src ≠ G_tgt** — must be different graphs.
  - **Both graphs must be in the same metagraph** — cross-metagraph InterGraphEdges are explicitly out of scope (open question; see §6).
  - **`type_name`** — typed, validated against schema like regular Edges.
  - **Properties** — same shape as Edge properties (key-value, with reserved-key restrictions).
  - **Identity** — fresh UUID at creation, like Edge.

Conceptual position relative to existing primitives:

  | Primitive | Endpoints | Scope |
  |---|---|---|
  | `Edge` | two nodes in **same graph** | intra-graph |
  | `MetaEdge` | two **graphs** (treated as nodes) | metagraph-level (graph-to-graph) |
  | **`InterGraphEdge`** (new) | two **nodes from different graphs** | metagraph-level (node-to-node, spans graphs) |
  | `HyperEdge` | n-ary set of nodes in same graph | intra-graph |
  | `MetaHyperEdge` | n-ary set of graphs | metagraph-level |

**Note on naming:** the term `InterGraphEdge` was preferred over alternatives (`CrossGraphEdge`, `BridgeEdge`, `SpanEdge`, `MetaNodeEdge`) for clarity and Latin-prefix consistency with `Inter-` semantics. L1 chat may revise.

### 3.3 API sketch

```python
# Create — node arguments carry graph context implicitly
ie = mg.add_intergraph_edge(
    source_node,                  # must already be in some graph in mg
    target_node,                  # must already be in some other graph in mg
    type_name="REFERENCES",
    properties={"role": "anchor"},
)

# Or with explicit graph arguments if node objects don't carry graph identity:
ie = mg.add_intergraph_edge(
    source_graph=lexicon, source_node_id=sense_a_id,
    target_graph=concepts, target_node_id=frame_id,
    type_name="EVOKES_FRAME",
)

# Query — symmetric with Edge queries but at metagraph level
for ie in mg.iter_intergraph_edges(source_node=sense_a):
    ...

# Schema validation
schema = mg.schema_for_intergraph_edges()
schema.add_intergraph_edge_type(IntergraphEdgeType(
    "EVOKES_FRAME",
    allowed_source_types=frozenset({"Sense"}),
    allowed_target_types=frozenset({"Frame"}),
    allowed_source_graphs=frozenset({"lexicon"}),  # optional: restrict by graph role
    allowed_target_graphs=frozenset({"concepts"}),
))
```

### 3.4 Persistence sketch (Cypher)

Two viable patterns; L1 chat picks:

  - **Pattern A — direct typed relationship.** `(:Node {graph_id: src_g})-[:INTERGRAPH_EDGE {type_name, ...}]->(:Node {graph_id: tgt_g})`. Endpoints carry their own graph_id property. Pro: simple, fast traversal. Con: deviates from Core's "Edge endpoints in same graph" Cypher invariant.

  - **Pattern B — anchor node + member edges.** `(:InterGraphEdge {type_name, ...})-[:SOURCE]->(:Node {graph_id: src_g})` and `(:InterGraphEdge ...)-[:TARGET]->(:Node {graph_id: tgt_g})`. Pro: stays consistent with existing HyperEdge anchor pattern (per L1 §2). Con: extra hop on traversal.

Recommend Pattern B for consistency with `HyperEdge` (which already uses the anchor pattern per L1 handoff §2) — but L1 chat decides.

### 3.5 Coexistence with `ref:*` properties (ADR-0016)

`ref:*` properties remain valid. `InterGraphEdge` is preferred for *new* typed cross-graph relationships where:

  - The relationship has semantic content beyond pure identity reference (e.g., `EVOKES_FRAME`, `MAPS_TO_DOLCE`).
  - Schema enforcement is wanted (allowed types, allowed graph roles).
  - Native graph traversal is wanted (vs property-key prefix scan).

`ref:*` remains appropriate for:

  - Pure identity references (e.g., MM instance pointing back to the L2 node it instantiated).
  - Existing Local→Global proxy patterns in KL (no immediate migration required).

**Migration path** (out of v1 scope; flagged for future): KL Local→Global proxies could migrate to `InterGraphEdge` typed `LOCAL_TO_GLOBAL_REF`. This would be a substantial L2 refactor; not blocking on the current proposal. Decision deferred to L2 chat after L1 changes land.

### 3.6 Snapshot / restore

`MetagraphSnapshot.of(mg)` (per L1 §3.10) must capture and restore InterGraphEdges with the rest of the metagraph state. Same semantics as Edge / MetaEdge snapshot — deep copy at snapshot time, in-place restore.

### 3.7 Reserved properties

Same reserved-property-key set as Edge (per L1 §5): `id`, `uuid`, `node_id`, `edge_id`, `graph_id`, `metagraph_id`, `instance_id`, `type`, `type_name`, `kind`, `label`, `role`, `value`, `source_id`, `target_id`. Plus possibly: `source_graph_id`, `target_graph_id` if those are auto-set by L1.

### 3.8 ADR shape

Suggested: `0148-intergraph-edge-primitive.md`. Decision: introduce `InterGraphEdge` as L1 primitive. Co-located with existing edge ADRs (0014, 0016).

---

## 4. Change 2 — Schema-declared layers

### 4.1 Motivation

Concrete need from WSD design: the lexicon graph holds two conceptually distinct edge sets:

  - **Theoretical layer** — definitional relationships from curated lexical resources (OEWN/WordNet): `HYPERNYM_OF`, `HYPONYM_OF`, `SYNSET_MEMBER`, `ANTONYM_OF`, `MERONYM_OF`, etc.
  - **Empirical layer** — observed-from-corpus relationships: `COOCCURS_SAMESENT`, `COOCCURS_DEPARC`, `SUBJECT_OF`, `DOBJECT_OF`, `AGENT_OF`, `PATIENT_OF`, `INSTRUMENT_OF`, etc.

Different L3 capacities query different layers (WSD scoring may want only empirical; FOL inference may fuse both). Different ALS audit policies may apply per layer (theoretical edges from a curated import are different from empirical edges learned from user data). Admin tooling benefits from layer-level operations ("show me all empirical edges of this sense", "freeze the theoretical layer", "version the empirical layer separately").

Without a layer mechanism, these distinctions get encoded ad-hoc (edge-type prefix conventions, separate role-graphs, etc.). A first-class layer concept centralizes the abstraction.

The need generalizes — other graphs can use layers too:

  - **Concepts graph** — FrameNet roles vs PropBank vs VerbNet layers.
  - **Ontology graph** — DOLCE vs domain-specific ontologies layers (if multi-foundational ever ships per FOL handoff #11).
  - **Memories graph** — different memory-source layers (live-task vs dream-derived).

### 4.2 Specification

A **layer** is a named group of edge types declared at schema level. Each edge type belongs to exactly one layer (or to no layer = "default" / unlayered). Layers don't overlap; an edge type is in zero or one layer.

Schema gains:

  - `add_layer(layer_name: str, edge_type_names: Iterable[str]) → None` — declares which edge types are in this layer. Asserts that no edge type already belongs to another layer. Asserts that all referenced edge types exist in the schema.
  - `layer_for_edge_type(edge_type_name: str) → str | None` — query.
  - `edge_types_in_layer(layer_name: str) → frozenset[str]` — query.
  - `iter_layers() → Iterable[str]` — list all declared layer names.

Graph (or Repository) gains:

  - `iter_layer_edges(layer_name: str) → Iterable[Edge]` — runtime query helper. Iterates edges whose `type_name` belongs to the named layer.
  - `count_layer_edges(layer_name: str) → int` — count helper.

Layer membership is **type-level**, not edge-level. Two edges of the same type cannot be in different layers. (Trade-off: simpler, more enforceable. Cost: if you want type-X edges split across layers, you need two distinct edge types — likely the right discipline anyway.)

### 4.3 API sketch

```python
schema = Schema(strict=True)
schema.add_node_type(NodeType("Sense"))
schema.add_edge_type(EdgeType("HYPERNYM_OF", frozenset({"Sense"}), frozenset({"Sense"})))
schema.add_edge_type(EdgeType("ANTONYM_OF", frozenset({"Sense"}), frozenset({"Sense"})))
schema.add_edge_type(EdgeType("COOCCURS_SAMESENT", frozenset({"Sense"}), frozenset({"Sense"})))
schema.add_edge_type(EdgeType("SUBJECT_OF", frozenset({"Sense"}), frozenset({"Sense"})))

schema.add_layer("theoretical", ["HYPERNYM_OF", "ANTONYM_OF"])
schema.add_layer("empirical", ["COOCCURS_SAMESENT", "SUBJECT_OF"])

# Runtime queries
for edge in lexicon_graph.iter_layer_edges("empirical"):
    ...
print(lexicon_graph.count_layer_edges("theoretical"))

# Schema introspection
schema.layer_for_edge_type("HYPERNYM_OF")  # -> "theoretical"
schema.edge_types_in_layer("empirical")    # -> {"COOCCURS_SAMESENT", "SUBJECT_OF"}
```

### 4.4 Persistence

Two options:

  - **Option A — schema-level metadata.** Layer declarations are part of the Schema object's serialized state. Persisted alongside other schema metadata when the metagraph is persisted (per L1 §3.6).
  - **Option B — graph-level metadata via `:MetagraphSettings`-style anchor nodes.** Layer declarations live as singleton settings nodes in the graph (similar to `_kl_active_graph_ids` per L1 §3.10).

Recommend Option A — layers are schema-level abstractions, belong with other schema. Option B is appropriate if layers need to be configurable without re-deploying schema.

### 4.5 Backward compatibility

Schemas without layer declarations work as today. Edge types not assigned to any layer are treated as "default layer" (or returned by `layer_for_edge_type` as `None`). Existing graphs (lexicon, ontology, concepts, alignments) continue working without change until their importers / schema-builders are updated to declare layers.

### 4.6 Scope: edges only, not nodes

For v1, layers apply to **edge types only**. Node-type layers (e.g., theoretical-class nodes vs empirical-class nodes) are conceivable but unnecessary for current use cases. Defer to v2 if needed.

### 4.7 Schema migration

When a schema gains layer declarations after edges already exist:

  - Existing edges of layer-declared types are *implicitly* in their declared layer (no migration of edge data needed; layer is type-level).
  - Existing edges of types not in any layer remain unlayered (as `None`).
  - No data rewrite required.

### 4.8 ADR shape

Suggested: `0149-schema-declared-edge-layers.md`. Decision: introduce schema-level edge-type layer declarations with type-level membership.

---

## 5. Coordinated implications across other layers

Both L1 changes ripple upward. Listed by layer for the L1 chat to flag for downstream coordination:

### L2 — Knowledge Layer

  - **Lexicon schema gains layer declarations** for `theoretical` and `empirical`. Coordinated with OEWN importer (declares its edges as `theoretical`) and a new empirical-layer importer (separate L3 work for WSD).
  - **The L2 §12 `sense-correlations` role-graph entry becomes obsolete.** WSD design has settled on adding empirical edges to lexicon graph rather than creating a separate role-graph. The L4 design notes' role-graph table needs corresponding update.
  - **InterGraphEdge** is *not* required for any current L2 work. Future migration of `ref:*` proxies to typed cross-graph edges is a v2-or-later L2 task; coordinated separately.

### L3 — Capacity Layer

  - **Read-side capacities for lexicon need layer-aware helpers.** WSD scorer capacities (per Decision 2 decomposition: candidate-gen strategies + scorer strategies) query empirical layer; FOL capacities query theoretical or both. Capacity implementations should use `iter_layer_edges("empirical")` and similar rather than ad-hoc filtering.
  - **No new L3 capacity types needed** for either change. Existing read APIs work as-is; layer-aware helpers are convenience.

### L4 — Intelligence Layer

  - **Layer-aware audit policies in ALS** (Audited Learning Subsystem; sibling design surfaced in WSD chat). Theoretical-layer edges typically don't need ALS gating (they come from curated imports); empirical-layer edges do (they're learned from user data). Coordinated change to ALS audit policy design once L1 ships.
  - **L4 design notes role-graph table update** to reflect that sense-correlations is now a layer in lexicon, not a separate role-graph.

### L5 — Mental Model Layer

  - **Possible InterGraphEdge use:** MM `ref:global_*` properties pointing to L2 nodes could migrate to typed `InterGraphEdge` (`MM_REFERENCES_LEXICON`, `MM_REFERENCES_CONCEPTS`, etc.). Not required for v1; deferred decision for L5 chat.

### L0 — Server Layer

  - **No direct impact.** Server's audit log and persistence machinery work over generic Edge/MetaEdge; if InterGraphEdge persists via Pattern B (anchor pattern), no Server-side changes needed.
  - **Possible future audit category** for InterGraphEdge writes if any layer above ships writes to them via Server-mediated APIs.

---

## 6. Open questions for L1 chat

  1. **Naming.** Confirm `InterGraphEdge` or pick alternative (`CrossGraphEdge`, `BridgeEdge`, etc.). Confirm `add_layer` / `iter_layer_edges` API names.

  2. **InterGraphEdge persistence pattern** — anchor node (Pattern B in §3.4) or direct typed relationship (Pattern A)? Recommendation is B for consistency with HyperEdge.

  3. **Cross-metagraph InterGraphEdges** — out of v1 scope per §3.2, but L1 chat may want to address it explicitly (forbid? defer to v2?).

  4. **Schema layer persistence** — Option A (schema-level metadata) or Option B (graph-level settings node)?

  5. **Layer membership exclusivity** — type-level (one layer per type) or edge-level (each edge declares its layer)? Proposal is type-level for simplicity. L1 chat may want edge-level for more flexibility (with cost in schema simplicity).

  6. **Default layer** — if an edge type is not declared in any layer, is it in a "default" layer with name `"default"` (queryable as such) or simply unlayered (`None`)? Proposal is `None` (unlayered), but a `"default"` layer makes uniform queries easier.

  7. **InterGraphEdge schema validation** — should schema enforce *which graph roles* an InterGraphEdge type may span (e.g., `EVOKES_FRAME` only between graphs of role `lexicon` and role `concepts`)? Proposal is yes (see API sketch §3.3); confirm.

  8. **Repository / Loader / Snapshot impact** — both changes touch persistence. L1 chat should scope work in `mindsos_core/persistence/` accordingly.

  9. **Sequencing.** Ship both changes in one L1 PR, or sequence (Schema layers first, then InterGraphEdge)? Schema layers is the more urgent need (blocking the WSD single-graph design). InterGraphEdge is needed eventually but no immediate deadline.

  10. **ADR numbering** — confirm `0148-intergraph-edge-primitive.md` and `0149-schema-declared-edge-layers.md` (or whatever next available numbers are).

---

## 7. What this does NOT change

To be explicit about the scope boundary:

  - **`Edge` semantics unchanged.** Still intra-graph only. Both endpoints in same graph.
  - **`MetaEdge` semantics unchanged.** Still graph-to-graph only. Connects two graph objects within a metagraph.
  - **`MetaHyperEdge` semantics unchanged.** Still n-ary across graphs.
  - **`HyperEdge` semantics unchanged.**
  - **`ref:*` property mechanism unchanged** (ADR-0016). Continues to work for cross-graph node references where typed-edge structure is not needed.
  - **Existing schema mechanism unchanged** (`add_node_type`, `add_edge_type`, `PropertyType`). Layer declaration is additive.
  - **Existing reserved-property-key set unchanged** (other than possibly adding `source_graph_id` / `target_graph_id` for InterGraphEdge auto-set fields).
  - **No existing graph or metagraph data needs migration.** Both changes are additive; existing data stays valid.
  - **No L2/L3/L4 code is mandated to change immediately.** The downstream coordinated changes listed in §5 are recommended next steps once L1 ships, but existing code continues working.

---

## 8. Recommended implementation phasing

L1 chat decides; suggesting an order that minimizes risk:

  1. **Phase A — Schema layers.** Smallest, additive, unblocks WSD single-graph design. Schema mechanism + Graph helpers + persistence.
  2. **Phase B — InterGraphEdge primitive.** Larger touch surface (new primitive class + persistence + snapshot/restore). Useful but not blocking immediate WSD work.

Phase A could ship first; Phase B follows. Or both together in one PR if L1 chat prefers consolidation.

---

## 9. Open items the WSD chat is tracking

For traceability — the WSD design conversation that surfaced these requirements is still working through:

  - SCMS architecture (Sense Confidence Monitoring Subsystem) — coupled WSD/FOL monitors with BSP turn-based execution.
  - ALS architecture (Audited Learning Subsystem) — generalized parameter training with admin-gated promotion.
  - Lexicon graph empirical layer — bootstrap importer + dream miner + audit policy.
  - Use cases (UC-WSD-*) — pending architectural settling.

None of these block on the L1 changes; the WSD design proceeds in parallel with reasonable assumptions. L1 chat decisions on the open questions in §6 will be folded back into WSD design as they land.

---

**End of handoff.**

When L1 design settles these changes, please update this document or write a follow-up handoff so the WSD design chat can absorb the final API.
