# Intergraph Edges — Design (Canonical)

> **For future chats: this document is the single canonical source for `IntergraphEdge` and `IntergraphHyperEdge` design.** If you are looking for the cat=c+a+t composition pattern, n-ary anchors, the compositional flag, persistence shape, schema validation, OCC/WAL strategy, or anything else about node↔node-across-graphs primitives — read this file. Do not chase pointers across PHASE_MAP §7, MEMORY.md, the WSD coordinated-change handoff, or older ADR drafts; they all defer here.
>
> **Status:** GREENLIT 2026-05-04 (Phase 05 design chat). Refined 2026-05-05 (Phase 05a row-refinement chat). 05b SHIPPED 2026-05-05/06 (740/2 in-container). 05c row LOCKED 2026-05-06 (4 reanalysis rounds; awaiting implementation). 05d row STUB authored 2026-05-06 (split via 05c P1-B for meta-vocabs). Two primitives + compositional flag pinned.
>
> **Replaces** the original Q13 open-question framing in `confirmation_docs/PHASE_MAP.md` §7. Q13 is CLOSED.

---

## 2026-05-06 amendment block (Phase 05c row-refinement chat locks)

The locks below override or refine specific items in the body of this document. **When in conflict, this block wins.** Future chats: read this block before §3.3 / §4 / §6 / §11.

### Ordered semantic (overrides §3.3 default + clarifies §11 open item)

- **`IntergraphHyperEdgeType.ordered: bool = True`** (P18-A; overrides design §3.3's stated `False` default). `ordered=True` is permissive list semantics: preserves insertion order, allows duplicates within a side (cat=letter case). `ordered=False` is opt-in via CLI `--unordered` flag.
- **`ordered=True` semantic**: anchors/members preserved as-given at construction. List equality. Duplicates allowed within a side.
- **`ordered=False` semantic**: anchors/members canonicalized at construction — sort lexicographically by `(graph_id, node_id)` then dedup. Duplicate inputs accepted (deduped silently); cardinality check runs on canonicalized values, so `[a,a,a] + [b,b]` → `[a] + [b]` → fails 1-1 cardinality check with structured error.
- **No-schema construction default**: when no MetagraphSchema attached OR no IntergraphHyperEdgeType registered for the type_name, treat as `ordered=True` (permissive; no canonicalization). Re-attach with conflicting `ordered` setting refuses per §3.3 / §4.1 / §11 eager-validation contract.

### Compositional + ordered=False refusal (new constraint)

- **`compositional=True` + `ordered=False` is refused** at the `add_intergraph_hyperedge` API boundary (P8-A; validation step 8.5 in the 16-step order). Rationale: compositional implies identity-bearing composition (cat=c+a+t — order/duplicates matter); set semantics is incompatible. Refusal is at construction-time, not at type-construction (the same type can serve both compositional and non-compositional callers — but only when `ordered=True`).

### __setattr__ immutability scope (refines §4.3)

- **`compositional` field**: always immutable post-`__post_init__` (raises `CompositionalImmutableError` on any post-init write).
- **`anchors` / `members` / `properties` fields**: immutable post-init **only when `compositional=True`**. Non-compositional hyperedges support factory-mediated mutation; factories use `object.__setattr__` to bypass the `__setattr__` gate for legitimate updates. Direct user mutation of these fields on a non-compositional hyperedge still raises (set-via-factory contract).
- **`anchors` / `members` field type**: stored as `Tuple[Tuple[str, str], ...]` post-`__post_init__` (tuple-conversion at construction regardless of compositional flag — eliminates list-mutation hole even for non-compositional hyperedges; updates produce new tuples).
- **`type_name` / `edge_id` / `label`**: set-at-create only (raise on post-init mutation). Mirror 05b precedent.

### Update API (extends §4 + §6)

- **`Metagraph.update_intergraph_hyperedge(intergraph_hyperedge_id, *, anchors=None, members=None, properties=None, replace_properties=False)`** (P10-C) — single combined factory, **replace-only semantics** (no patch). Refuses if `compositional=True` (`CompositionalImmutableError`). Re-runs full 16-step validation order on resolved replacement values; atomic rollback on failure (no in-memory mutation). Any field passed as `None` retains current value.
- **CLI**: `mindsos metagraph update-intergraph-hyperedge --name MG --intergraph-hyperedge-id ID [--anchor-graph G --anchor-node N]... [--member-graph G --member-node N]... [--prop k=v]... [--replace-properties] [--json]`. Paired-flags syntax matches `add-intergraph-hyperedge`.
- **Update under detached schema** (P20-A): structural-only validation (cardinality, overlap, regex; NO schema/role/property-type checks). Subsequent re-attach surfaces drift per §3.3 eager-validation contract.
- **Update collapsing to 1-1 cardinality**: refused (P19-A). No in-place hyperedge→edge downgrade — tester recovery is `remove-intergraph-hyperedge` + `add-intergraph-edge --intergraph-edge-id <orig>` (loses edge_id stability across the type boundary). Future-work entry filed at `_source_backup/root/mindsos_future_plans.md` "Intergraph primitive structural mutation" / "In-place hyperedge→edge downgrade with edge_id stability".

### Symmetric IntergraphEdge endpoint update — REJECTED for v1

- 05c chat's round-3 P11→P13-B retreat: **no `update_intergraph_edge_endpoints` factory + CLI verb on the binary primitive in 05c.** Triggering 05b-v2 supersession judged disproportionate to the symmetry benefit when the existing workaround (remove + add with `--intergraph-edge-id <orig>` override per Push14-A) preserves edge_id stability. Documented in 05b CHANGELOG amendment (lands on `phase-05c` branch). Future-work entry filed at `_source_backup/root/mindsos_future_plans.md` "Intergraph primitive structural mutation" / "Discoverable endpoint-update verb for IntergraphEdge".

### CLI paired flags (overrides §6 slash-separator)

- **`--anchor-graph G --anchor-node N`** repeatable, paired by parsing index (P4-A). Symmetric for `--member-graph` / `--member-node`. Mismatched counts (e.g., 3 `--anchor-graph` + 2 `--anchor-node`) refuse with structured error before any mutation. **Slash form `--anchor G/N` from §6 is NOT shipped** — ambiguous when graph names contain `/`.

### 16-step validation order (extends §4.2)

Locked at `Metagraph.add_intergraph_hyperedge` (full text in `PHASE_MAP.md` §5 Phase 05c row appendix §A):

1-2. Graph existence per anchor/member.
3-4. Node existence per anchor/member.
5. Cypher rel-type regex on `type_name` (at `__post_init__`).
6. Schema type-existence lookup (extracts `type.ordered`).
7. **Canonicalize anchors + members** per `type.ordered` (sort+dedup if False; preserve insertion if True).
8. **Cardinality check** on canonical (n≥1, m≥1, NOT 1-1).
9. **Anchor-member overlap forbidden** check.
10. **P8-A refusal**: `compositional=True` + `type.ordered=False` → `SchemaError`.
11-13. Property + schema validation.
14. Mint id.
15. Construct dataclass.
16. Register + insert.

Update path: runs 1-13 on resolved replacement values; skips 14 + 16; replaces tuple in-place via `object.__setattr__` on existing edge.

### Phase placement update (overrides §8)

CASC-1 strict-sequential cascade is now **05a → 05b → 05c → 05d → 06** (was 05a → 05b → 05c → 06).

| Phase | Ships |
|---|---|
| **05a** (Metagraph port) | `Metagraph` + `MetaEdge` + `MetaHyperEdge`. ADR-0117 Withdrawn. **SHIPPED 2026-05-05** (528/2). |
| **05b** (binary intergraph + MetagraphSchema) | `IntergraphEdge` + `MetagraphSchema` + `IntergraphEdgeType` + compositional flag. ADR-0148 first draft. **MetaEdgeType + MetaHyperEdgeType were never in 05b's shipped scope** (Pushback 1-C narrowed pre-implementation). **SHIPPED 2026-05-05/06** (740/2). |
| **05c** (n-ary intergraph) | `IntergraphHyperEdge` + `IntergraphHyperEdgeType` + replace-only update verb. ADR-0148 amended. ADR-0014 second amendment. Metagraph state file v=2 → v=3. Metagraph-schema state file v=1 → v=2. **Row LOCKED 2026-05-06.** |
| **05d** (NEW; meta-vocabs) | `MetaEdgeType` + `MetaHyperEdgeType` schema vocab on `MetagraphSchema`. Eager-attach extension to walk metaedges + metahyperedges (Push9-A from 05b expires here). ADR-0017 amended. ADR-0014 third amendment. Metagraph-schema state file v=2 → v=3. **Row STUB authored 2026-05-06; awaits dedicated row-refinement chat.** Inherits MetaEdge.type_name field audit task (P3 deferred from 05c — may trigger 05a-v2 if absent). |

### State file shapes (overrides §5 + adds 05d row)

| File | 05a | 05b | 05c | 05d |
|---|---|---|---|---|
| `metagraph-<n>.json` | v=1 | v=2 (adds intergraph_edges + schema_name) | **v=3 (adds intergraph_hyperedges)** | v=3 (no change) |
| `metagraph-schema-<n>.json` | n/a | v=1 (adds intergraph_edge_types) | **v=2 (adds intergraph_hyperedge_types)** | v=3 (adds meta_edge_types + meta_hyperedge_types) |

Strict version contract on both files (P16-A): older binary loading newer file rejects with `this CLI supports vN` structured message. Recovery via hand-edit JSON downgrade.

### §11 open items — resolved

- **`IntergraphHyperEdgeType.ordered: bool` semantic** — RESOLVED above (type-driven set-vs-list; default True; `ordered=False` canonicalizes at construction; compositional+ordered=False refused).
- **`compositional=True` cascade through `Metagraph.remove_graph`** — IMPLEMENTED in 05c per design intent. Atomic precheck pass walks BOTH `mg.intergraph_edges` AND `mg.intergraph_hyperedges`; raises `CompositionalImmutableError` with `edge_kind` + `edge_id` on first incident; state unchanged on raise.
- **Index design for `iter_intergraph_*` performance** — STILL Phase 07 territory. 05c ships in-memory iteration only.
- **ADR-0148 final wording** — first draft in 05b row appendix §B; amendment in 05c row appendix §B. File edit Phase 38 per locked precedent.

---

---

## 1. The two primitives

L1 ships **two** node-to-node edge primitives that span graphs within a single metagraph:

| Primitive | Endpoints | Cardinality | Container | Phase |
|---|---|---|---|---|
| `IntergraphEdge` | Node ↔ Node, across two graphs | strictly 1-to-1 | one Metagraph | **05b** |
| `IntergraphHyperEdge` | n anchor-nodes ↔ m member-nodes, across one or more graphs | n ≥ 1, m ≥ 1, NOT 1-to-1 | one Metagraph | **05c** |

The cardinality split is enforced at the API boundary: `IntergraphHyperEdge` raises `SchemaError` for 1-to-1 inputs ("use IntergraphEdge for 1-to-1"). 1-to-1 always uses `IntergraphEdge`; anything else (1-n, n-1, n-m where total ≥ 3, or any side > 1) uses `IntergraphHyperEdge`.

Both primitives are **metagraph components** — owned by the `Metagraph`, registered in its unified `IdentityRegistry`, persisted in its state file, validated by its schema. **The metagraph is the canonical entry point for everything intergraph-related.** Loose rule: if you have the `Metagraph`, you have everything you need; you should not need to query individual edge objects in isolation.

Reference table for context (existing primitives):

| Construct | Endpoints | Container |
|---|---|---|
| `Edge` (Phase 03) | Node ↔ Node | one Graph |
| `HyperEdge` (Phase 03) | n × Node | one Graph |
| `MetaEdge` (Phase 05a) | Graph ↔ Graph | one Metagraph |
| `MetaHyperEdge` (Phase 05a) | n × Graph | one Metagraph |
| `XRef` (Phase 09) | Node ↔ Node | *across* metagraphs |
| **`IntergraphEdge` (Phase 05b)** | **Node ↔ Node** | **one Metagraph** |
| **`IntergraphHyperEdge` (Phase 05c)** | **n × Node ↔ m × Node** | **one Metagraph** |

`CompositionalMetaEdge` (originally proposed at the graph level under ADR-0117) has been **dropped**. The compositional concept moves to a `compositional: bool` flag on `IntergraphEdge` / `IntergraphHyperEdge`. **ADR-0117 was Withdrawn in 05a per round-1 P3 amendment** (one phase earlier than originally planned in this doc; code drops the class in 05a, ADR status matches). See §9.

---

## 2. Field lists

### 2.1 `IntergraphEdge` — 10 fields

| # | Field | Type | Notes |
|---|---|---|---|
| 1 | `source_graph_id` | `str` | Graph in this metagraph. |
| 2 | `source_node_id` | `str` | Node in `source_graph_id`. Must exist in metagraph's unified `IdentityRegistry`. |
| 3 | `target_graph_id` | `str` | Graph in this metagraph. **Must differ from `source_graph_id`** — same-graph case is `Edge`. |
| 4 | `target_node_id` | `str` | Node in `target_graph_id`. |
| 5 | `type_name` | `str` | Required. Cypher rel-type regex per ADR-0021 (`^[A-Z][A-Z0-9_]{0,63}$`). |
| 6 | `edge_id` | `str` | Auto-minted via `Metagraph.id_strategy` (ADR-0131); UUID4 default. |
| 7 | `properties` | `Dict[str, Any]` | Namespaced; ADR-0130 reserved-key-aware. |
| 8 | `label` | `Optional[str]` | Human-readable; default `None`. Parallel to `MetaEdge.label`. |
| 9 | `compositional` | `bool` | Default `False`. **Immutable post-create** (Push6-A): set at construction; cannot flip. If `True`, removal/mutation/deprecation raise `CompositionalImmutableError`. Persists as `_compositional` reserved property in JSON / Cypher. |
| 10 | `deprecated_at` | `Optional[datetime]` | ADR-0133 soft-delete substrate. **Dormant in 05b** (kept on dataclass, no CLI/iterator filtering); Phase 10 wires it. |
| 11 | `disputed_at` | `Optional[datetime]` | Same. **Dormant in 05b**; Phase 10 wires it. |

(Total: 11 fields including both soft-delete fields. The "10 fields" count groups `deprecated_at` + `disputed_at` as one soft-delete substrate.)

**No `metagraph_id` field on the dataclass.** The metagraph is the canonical container; it owns the edge via `mg.intergraph_edges[edge_id]`. The metagraph state file's top-level `metagraph_id` provides context for any persisted edge. Edges held in isolation outside their metagraph are out-of-contract.

### 2.2 `IntergraphHyperEdge` — 9 fields

| # | Field | Type | Notes |
|---|---|---|---|
| 1 | `anchors` | `List[Tuple[str, str]]` | n ≥ 1 `(graph_id, node_id)` pairs. List preserves order (cat≠tac for compositional cases). Same-graph anchors allowed; cross-graph anchors allowed. |
| 2 | `members` | `List[Tuple[str, str]]` | m ≥ 1 `(graph_id, node_id)` pairs. List preserves order. Same-graph members allowed; cross-graph members allowed. |
| 3 | `type_name` | `str` | Required. Cypher rel-type regex per ADR-0021. |
| 4 | `edge_id` | `str` | Auto-minted via `Metagraph.id_strategy`. |
| 5 | `properties` | `Dict[str, Any]` | Namespaced; reserved-key-aware. |
| 6 | `label` | `Optional[str]` | Human-readable; default `None`. |
| 7 | `compositional` | `bool` | Default `False`. **Immutable post-create**. Same semantic as `IntergraphEdge.compositional`. |
| 8 | `deprecated_at` | `Optional[datetime]` | Dormant in 05c; Phase 10 wires. |
| 9 | `disputed_at` | `Optional[datetime]` | Same. |

**Cardinality enforcement** (`__post_init__`):
- `len(anchors) ≥ 1`
- `len(members) ≥ 1`
- `len(anchors) > 1 OR len(members) > 1` (NOT 1-to-1; raises `SchemaError("use IntergraphEdge for 1-to-1")`).

**Anchor-member overlap forbidden**: if any `(graph_id, node_id)` pair appears in both `anchors` and `members`, raises `SchemaError`.

**Duplicates within a side allowed**: e.g., word "letter" with `members=[(lg,l), (lg,e), (lg,t), (lg,t), (lg,e), (lg,r)]` is valid — words with repeated characters need this.

**No `metagraph_id` field** (same rationale as §2.1).

### 2.3 New reserved property keys (cumulative impact)

The slim port's `RESERVED_PROPERTY_KEYS` set extends across phases:

- **05b adds**: `source_graph_id`, `source_node_id`, `target_graph_id`, `target_node_id`, `_compositional`.
- **05c adds**: `anchors`, `members`. (`_compositional` already added in 05b; reused.)

`type_name`, `edge_id`, `label`, `deprecated_at`, `disputed_at`, `metagraph_id`, `graph_id`, `node_id` are already reserved per Phase 04 / Phase 04-v2.

---

## 3. Resolved design decisions (§4 of the original concerns)

The original design note raised six unresolved concerns. All are resolved below. Sources are tagged: **[WSD]** = the WSD coordinated-change handoff (2026-04-29); **[MEM]** = MEMORY.md index entry tagged decisions (2026-05-04 Phase 05 design chat); **[05a]** = this Phase 05a row-refinement chat (2026-05-05).

### 3.1 OWNS persistence — RESOLVED

**Question:** which graph owns the Cypher edge?

**Answer:** Neither graph. The metagraph owns it. Cypher uses **Pattern B (anchor-node pattern)**:

```
(:IntergraphEdge {edge_id, type_name, properties..., _compositional})
  -[:SOURCE]->(:Node {node_id: source_node_id})
(:IntergraphEdge ...)
  -[:TARGET]->(:Node {node_id: target_node_id})
(:Metagraph {metagraph_id})-[:OWNS]->(:IntergraphEdge ...)
```

For `IntergraphHyperEdge`, extend with multiple `:ANCHOR` and `:MEMBER` relationships:

```
(:IntergraphHyperEdge {edge_id, type_name, properties..., _compositional})
  -[:ANCHOR]->(:Node {node_id: anchor[i].node_id})  -- one per anchor
(:IntergraphHyperEdge ...)
  -[:MEMBER]->(:Node {node_id: member[j].node_id})  -- one per member
(:Metagraph {metagraph_id})-[:OWNS]->(:IntergraphHyperEdge ...)
```

The anchor-node `(:IntergraphEdge)` / `(:IntergraphHyperEdge)` is owned by the `(:Metagraph)`, not by either contained `(:Graph)`. Symmetric with how parent code's `MetaEdge` is owned by the metagraph at the model level. **[WSD §3.4 + MEM "metagraph-owned"]**

Source/target node references include their owning `graph_id` as a property, so traversers can recover graph context without an extra hop.

### 3.2 Snapshots — RESOLVED

**Question:** snapshots break per-graph locality if cross-graph node-edges exist.

**Answer:** Snapshots are already metagraph-scoped (ADR-0027 / ADR-0028). `IntergraphEdge` and `IntergraphHyperEdge` go in the metagraph snapshot with the rest. **No expansion to per-graph snapshot needed.** ADR-0129 (snapshot scope narrowed to release-ship in Phase 10) is unaffected by this decision. **[WSD §3.6]**

### 3.3 Schema validation — RESOLVED

**Question:** two competing graph schemas for one cross-graph edge — which wins?

**Answer:** Neither. Validation lives in a new `MetagraphSchema` (additive, attached to `Metagraph` rather than to a contained `Graph`). **[MEM "A1 additive MetagraphSchema"]**

`MetagraphSchema` carries:
- `MetaEdgeType` and `MetaHyperEdgeType` (validate `MetaEdge` / `MetaHyperEdge` from 05a) — **05b**.
- `IntergraphEdgeType` (validates `IntergraphEdge`) — **05b**.
- `IntergraphHyperEdgeType` (validates `IntergraphHyperEdge`) — **05c**.

Each `IntergraphEdgeType` carries:
- `allowed_source_types: frozenset[str]`, `allowed_target_types: frozenset[str]` — node-type constraints.
- `allowed_source_graphs: frozenset[str]`, `allowed_target_graphs: frozenset[str]` — graph-role constraints (e.g., `EVOKES_FRAME` only between `lexicon`-role and `concepts`-role graphs). Per **[MEM "C1 allowed_source_pairs"]**.
- `property_types: Dict[str, PropertyType]` — same 8-variant vocabulary as Phase 04 `EdgeType`.

`IntergraphHyperEdgeType` analogous, with `allowed_anchor_types` / `allowed_member_types` / `allowed_anchor_graphs` / `allowed_member_graphs` plus an optional `ordered: bool = False` flag for whether order matters within `anchors` / `members`. **[05a]**

The two graph-level schemas don't conflict because the intergraph-edge type vocabulary is metagraph-scoped, not graph-scoped.

### 3.4 OCC / WAL — RESOLVED

**Question:** per-graph mutex vs metagraph-level lock?

**Answer:** **Two-lock canonical ordering** for binary, **n-lock canonical ordering** for n-ary. Acquire all involved-graph locks in canonical order (sort by `graph_id` string). Release in reverse order. Standard deadlock-avoidance pattern; latency degrades linearly with n for `IntergraphHyperEdge`. **[MEM "E1 two-lock canonical ordering"]**

Phase 07 implements; Phase 05b / 05c lock the contract.

### 3.5 Migration — RESOLVED

**Question:** importer migration cost for "save one hop" win?

**Answer:** **No migration of existing importers is required.** `ref:*` properties (ADR-0016) remain valid for pure identity references and existing patterns. `IntergraphEdge` is introduced for *new* typed cross-graph relationships. Existing alignments-graph reification (DOLCE / OEWN / FrameNet / Alignments importers) stays as-is. L2 migration of `ref:*` proxies to typed intergraph edges is a deferred-indefinitely L2 task. **[WSD §3.5]**

### 3.6 Existing constructs — RESOLVED

**Question:** does the existing pattern set already cover the use cases?

**Answer:** No, but not for "save one hop." The cat=c+a+t composition use case (one word node compositionally bound to n letter nodes) is not served cleanly by any existing primitive:
- `MetaHyperEdge` is graph-level (between graphs, not nodes).
- `XRef` is cross-metagraph.
- `ref:*` properties have no compositional immutability semantic.
- Alignments-graph reification doesn't enforce compositional invariants.

`IntergraphHyperEdge` with `compositional=True` fills this gap. Three patterns coexist; `IntergraphEdge` / `IntergraphHyperEdge` supplement, do not replace. **[05a]**

---

## 4. Validation rules (Metagraph add boundary)

### 4.1 `Metagraph.add_intergraph_edge(...)` — 05b

- `source_graph_id` and `target_graph_id` must reference graphs contained in `self.graphs`.
- `source_graph_id ≠ target_graph_id` (same-graph use `Graph.add_edge`).
- `source_node_id` exists in `source_graph_id`'s `Graph.nodes` AND in `self.identity` (unified registry).
- `target_node_id` exists in `target_graph_id`'s `Graph.nodes` AND in `self.identity`.
- `type_name` passes ADR-0021 cypher rel-type regex.
- If `MetagraphSchema` attached and strict: `IntergraphEdgeType` lookup; `allowed_source_types` / `allowed_target_types` / `allowed_source_graphs` / `allowed_target_graphs` enforced.
- `properties` validated via `validate_user_properties(scope="intergraph_edge")`.
- `edge_id` auto-minted; registered in `self.identity`.

### 4.2 `Metagraph.add_intergraph_hyperedge(...)` — 05c

All of 4.1 plus:
- `anchors` and `members` cardinality (§2.2 `__post_init__` rules).
- All anchor/member `(graph_id, node_id)` pairs must reference graphs/nodes in this metagraph.
- Anchor-member overlap forbidden.

### 4.3 Compositional immutability

When `compositional=True`:
- `Metagraph.remove_intergraph_edge` (and `remove_intergraph_hyperedge`) raises `CompositionalImmutableError`.
- `set_intergraph_edge_properties` (mutation API) raises same.
- `deprecate_intergraph_edge` (Phase 10) raises same.
- The flag itself is immutable post-create (Push6-A). `False → True` flip not allowed (catch-22: a `True` edge can't be removed, so flipping in error wedges the metagraph).

To "promote" a non-compositional edge to compositional: `remove` (allowed for non-compositional) + `add_intergraph_edge(..., compositional=True)`.

---

## 5. Storage on Metagraph

In-memory:
- `mg.intergraph_edges: Dict[str, IntergraphEdge]` keyed by `edge_id` — 05b ships.
- `mg.intergraph_hyperedges: Dict[str, IntergraphHyperEdge]` keyed by `edge_id` — 05c ships.

Iterators (with index lookups in Phase 07):
- `mg.iter_intergraph_edges(*, source_node_id=None, target_node_id=None, source_graph_id=None, target_graph_id=None, type_name=None, include_deprecated=False)`.
- `mg.iter_intergraph_hyperedges(*, anchor_node_id=None, member_node_id=None, type_name=None, include_deprecated=False)`.

State file (`metagraph-<n>.json`) carries `intergraph_edges` array (05b adds) and `intergraph_hyperedges` array (05c adds). 05a's metagraph state file is v=1 with neither array; 05b bumps to v=2 (adds `intergraph_edges` + optional `schema_name` for `MetagraphSchema`); 05c bumps to v=3 (adds `intergraph_hyperedges`).

---

## 6. CLI surface

### 05b adds (under `mindsos metagraph` subapp):

- `add-intergraph-edge --name <MG> --source-graph <G> --source-node <N> --target-graph <G> --target-node <N> --type <REL_TYPE> [--label L] [--prop k=v]... [--compositional] [--edge-id ID]`
- `remove-intergraph-edge --name <MG> --edge-id ID`  (refuses if `compositional=True`)
- `set-prop --name <MG> --intergraph-edge-id ID --prop k=v ... [--replace]`  (mutex extends; refuses if `compositional=True`)
- `list-intergraph-edges --name <MG> [--json]`

### 05c adds:

- `add-intergraph-hyperedge --name <MG> --anchor <G>/<N> [--anchor <G>/<N>...] --member <G>/<N> [--member <G>/<N>...] --type <REL_TYPE> [--label L] [--prop k=v]... [--compositional] [--hyperedge-id ID]`
- `remove-intergraph-hyperedge --name <MG> --hyperedge-id ID`  (refuses if `compositional=True`)
- `set-prop --name <MG> --intergraph-hyperedge-id ID --prop k=v ... [--replace]`  (mutex extends further; refuses if `compositional=True`)
- `list-intergraph-hyperedges --name <MG> [--json]`

`--compositional` is a top-level flag on `add-*` commands (R2-A). Defaults to False. Mirrors `mindsos schema create --strict` precedent.

---

## 7. Compositional flag — the cat=c+a+t example

The motivating use case for the compositional flag is **identity-bearing composition**: a node whose existence is defined by its constituents.

```
word-graph:
  - cat   (node)
  - dog
  - hat

letter-graph:
  - c
  - a
  - t
  - d
  - o
  - g
  - h

# Compositional intergraph hyperedge: cat = c+a+t
mg.add_intergraph_hyperedge(
    anchors=[("word-graph", "cat")],
    members=[("letter-graph", "c"), ("letter-graph", "a"), ("letter-graph", "t")],
    type_name="COMPOSED_OF",
    compositional=True,
)
```

**Identity property:** removing any single member changes what the anchor *is*. `cat` minus `t` is not `ca`; it's a degenerate identity that the system refuses to represent silently. The `compositional=True` flag enforces this:

- Attempting `remove_intergraph_hyperedge(cat_edge_id)` raises `CompositionalImmutableError`.
- Attempting `set_intergraph_hyperedge_properties(...)` raises same.
- Attempting to deprecate (Phase 10) raises same.
- Removing `letter-graph` itself, or removing the `t` node from `letter-graph`, will fail at the metagraph level (the compositional hyperedge references survive removal-impact checks).

**Ordering matters in cat=c+a+t.** The `members` field is `List[Tuple[str, str]]`, not `Set` — `[c, a, t]` ≠ `[t, a, c]` for word composition. The `IntergraphHyperEdgeType.ordered: bool` flag (05c) lets schema declare per-type whether ordering is semantic. For `COMPOSED_OF`-typed compositions, `ordered=True`.

**Duplicates in members allowed.** Word "letter" has `members=[(lg,l), (lg,e), (lg,t), (lg,t), (lg,e), (lg,r)]` — `t` and `e` appear twice. Push8-A.

**N-ary anchors** (Push1-A): the cat case has `len(anchors)=1`; n-ary anchors are supported for cases like cross-language cognates ("cat" in word-graph + "kat" in dutch-graph, both compositionally bound to the same letter set in some shared character-graph).

**Anchor-member overlap forbidden** (Push7-A): a node cannot appear in both `anchors` and `members` of the same `IntergraphHyperEdge`. Self-referential compositions are out of contract.

---

## 8. Phase placement

| Phase | Ships |
|---|---|
| **05a** (Metagraph port) | `Metagraph` + `MetaEdge` + `MetaHyperEdge`. **Neither IntergraphEdge nor compositional flag.** **ADR-0117 Withdrawn here per round-1 P3 amendment** (was originally Reserved through 05a). **SHIPPED 2026-05-05.** |
| **05b** (binary intergraph + MetagraphSchema) | `IntergraphEdge` + `MetagraphSchema` + `MetaEdgeType` + `MetaHyperEdgeType` + `IntergraphEdgeType`. ADR-0148 (intergraph edge family ADR) drafted + Accepted. **ADR-0117 was already Withdrawn in 05a — 05b skips that flip.** Metagraph state file v=1 → v=2. Plus carry-forward from 05a deferrals: `_compositional` reserved-key (P6) + `Metagraph.mint_id` (P7). |
| **05c** (n-ary intergraph) | `IntergraphHyperEdge` + `IntergraphHyperEdgeType`. ADR-0148 amended to include n-ary. Metagraph state file v=2 → v=3. |

CASC-1 strict sequential: 05a → 05b → 05c. Phase 06 (Instancing — `mindsos_instances`) depends on Phase 05a only; it can ship in parallel with 05b/05c if needed (re-evaluate at 05a confirm).

---

## 9. ADR plan

- **ADR-0117** (originally Reserved for graph-level `CompositionalMetaEdge`) — **Withdrawn in 05a per round-1 P3 amendment** (was: "Withdrawn in 05b" in this doc's original wording; the 05a chat moved the flip up by one phase to match the code drop). The graph-level CompositionalMetaEdge primitive does not ship. The compositional concept moves to the `compositional: bool` flag on intergraph primitives. Annotation block in the ADR file (when written in Phase 38) cites Phase 05a as the supersession point, NOT Phase 05b.
- **ADR-0148** (NEW; drafted in 05b, amended in 05c) — "Intergraph Edge family." Decision: introduce `IntergraphEdge` (binary, 1-to-1, node↔node across graphs in one metagraph) and `IntergraphHyperEdge` (n-ary, NOT 1-to-1) as L1 primitives. Both carry a `compositional: bool` flag (immutable post-create) for identity-bearing composition. Persistence via Pattern B anchor-node Cypher. Schema validation via `MetagraphSchema`. OCC via canonical-ordered locking.
- **ADR-0014** (Layer boundary) — **amended** to extend Core's primitive list with `IntergraphEdge` and `IntergraphHyperEdge`. Amendment text drafted in 05b row appendix; file edit deferred to Phase 38 (locked precedent from Phase 04 / Phase 04-v2).
- **(Removed)** "ADR-0117 stays Reserved through 05a" — superseded by P3 amendment; ADR-0117 was Withdrawn in 05a.

---

## 10. Cross-references

This document is canonical. Other documents point here:
- `confirmation_docs/PHASE_MAP.md` §7 Q13 — CLOSED, points here.
- `confirmation_docs/PHASE_MAP.md` §3 phase index — 05b / 05c rows reference this doc.
- `confirmation_docs/PHASE_MAP.md` §5 — 05b row + 05c row reference this doc for primitive specs.
- `MEMORY.md` index entry (see `project_mindsos_intergraph_edge_question.md`) — points here as canonical.
- `Other Related Projects/Word Sense Disambiguation/coordinated_change_L1_intergraph_and_layers.md` — superseded for L1 framing; points here for canonical spec.
- `docs/HANDOFF_L1_REDESIGN_2026-04-27.md` §M8 / §12.10 / §13 — annotated; CompositionalMetaEdge dropped per this doc.

Background sources this doc supersedes / consolidates:
- The original Q13 design note (this file's prior form, 2026-05-04 first draft).
- The WSD coordinated-change handoff §3 (proposed `InterGraphEdge`; greenlit and refined here; lowercase `Intergraph` naming wins per Push9-A).
- The MEMORY.md index entry's tagged decisions (A1, B2, C1, D1, E1, G2, metagraph-owned) — explained in §3 above.

---

## 11. Open items deferred to 05b / 05c implementation chats

- **ADR-0148 final wording.** Drafted in 05b row appendix; full text written in 05b chat. File edit Phase 38.
- **`IntergraphHyperEdgeType.ordered: bool` semantic** — pinned for 05c implementation; defer details to 05c.
- **Index design for `iter_intergraph_*` performance** — Phase 07 owns; 05b ships in-memory iteration only.
- **`compositional=True` cascade through `Metagraph.remove_graph`** — when a graph is removed, walk its incident intergraph edges/hyperedges; if any are `compositional=True`, the removal must propagate `CompositionalImmutableError`. 05b/05c implement this in `Metagraph.remove_graph` slim port (extending the already-existing N4-A skeleton).

---

*Document owner: 05b chat (binary primitive, MetagraphSchema, ADR-0148 first draft); 05c chat (n-ary primitive, ADR-0148 amendment). 05a chat does not edit this doc; 05a confirmation triggers no changes here.*
