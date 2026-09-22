---
last_confirmed_phase: 03
verified_at: 5be37bb
---

# `mindsos_core.Graph`

The `Graph` primitive — node / edge / hyperedge collections with identity
guards and Cypher rel-type validation. It shipped as a slim Phase 03 port;
schema enforcement, the graph-level property bag, soft-delete and the
property updaters have since landed on it and are documented below
(see `docs/concepts/graphs-and-metagraphs.md`).

## Constructor

```python
Graph(
    name: str,
    *,
    role: Optional[str] = None,
    graph_id: Optional[str] = None,
    identity: Optional[IdentityRegistry] = None,
    schema: Optional[Schema] = None,
    properties: Optional[Dict[str, Any]] = None,
)
```

| Parameter | Type | Description |
|---|---|---|
| `name` | `str` | Human-readable graph name. |
| `role` | `Optional[str]` | Optional semantic role (e.g. `"ontology"`, `"lexicon"`). Knowledge Layer (Phase 13+) consumes this. |
| `graph_id` | `Optional[str]` | Optional explicit id (used during Phase 08 reconstruction; tester-facing graphs auto-mint). |
| `identity` | `Optional[IdentityRegistry]` | Shared registry (used when contained in a `Metagraph`). Defaults to a fresh per-graph registry. |
| `schema` | `Optional[Schema]` | Attached schema; when present, node / edge / hyperedge properties are validated on add and update. |
| `properties` | `Optional[Dict[str, Any]]` | Graph-level property bag (ADR-0130). |

When `graph_id` is None, the auto-minted id is registered against the
identity registry. When supplied (reconstruction path), the caller is
responsible for registering it.

## Methods

### `add_node(value, type_name, *, properties=None, node_id=None) -> Node`

Create and register a new node.

| Param | Description |
|---|---|
| `value` | Any JSON-serialisable type. Primary display value. |
| `type_name` | Node type as a string. No validation in Phase 03 (Phase 04 Schema validates). |
| `properties` | Open property dict; defensive-copied; no validation in Phase 03. |
| `node_id` | Optional explicit id. Default is fresh UUID4. Used for IRI passthrough. Duplicate ids raise `IdentityError`. |

### `add_edge(source, target, type_name, *, label=None, properties=None, edge_id=None) -> Edge`

Create and register a new directed edge.

`type_name` is validated against `EDGE_TYPE_IDENTIFIER_RE` (ADR-0021)
before construction; invalid identifiers raise `CypherError`. Source /
target must already be in the graph; otherwise `IdentityError`.

### `add_hyperedge(nodes, type_name, *, label=None, properties=None, edge_id=None) -> HyperEdge`

Create and register a new n-ary hyperedge over `nodes` (any iterable).
`type_name` is required and is validated like an edge's.
Empty member set raises `SchemaError` (via `HyperEdge.__post_init__`).
Members must already be in the graph; otherwise `IdentityError`.

### `remove_node(node_id, *, cascade=True) -> None`

Remove a node. With `cascade=True`, incident edges and hyperedges are
removed as well. With `cascade=False`, raises `SchemaError` if any edge
or hyperedge still references the node.

### `remove_edge(edge_id) -> None` / `remove_hyperedge(edge_id) -> None`

Remove a single edge or hyperedge by id. Unknown ids raise
`IdentityError`.

## Attributes

| Attribute | Type | Description |
|---|---|---|
| `graph_id` | `str` | Stable id for the graph. |
| `name` | `str` | Human-readable graph name. |
| `role` | `Optional[str]` | Semantic role tag. |
| `identity` | `IdentityRegistry` | Per-graph (or shared from Metagraph) registry. |
| `nodes` | `Dict[str, Node]` | Keyed by `node_id`. |
| `edges` | `Dict[str, Edge]` | Keyed by `edge_id`. |
| `hyperedges` | `Dict[str, HyperEdge]` | Keyed by `edge_id`. |
| `schema` | `Optional[Schema]` | Attached schema, or `None`. |
| `properties` | `Dict[str, Any]` | Graph-level property bag. |

## Beyond the Phase 03 slim port

Every surface the Phase 03 row deferred has shipped on `Graph` except the
`_restore_*` helpers, which were never built (reconstruction builds graphs
through the public `add_*` methods instead):

* `schema` and `properties` constructor parameters, and property validation
  on add / update.
* `update_node_properties` / `update_edge_properties` /
  `update_hyperedge_properties`, each with `replace=False`, and
  `update_hyperedge_type`.
* Soft-delete (ADR-0133): `iter_edges` / `iter_hyperedges` /
  `get_edges_for_node`, all taking `include_deprecated=False`, plus
  `deprecate_edge` / `undeprecate_edge` / `dispute_edge` /
  `undispute_edge` and the four `*_hyperedge` counterparts. See
  [soft-delete.md](soft-delete.md).
* `register_remove_observer(callback)` — fires on node / edge removal.
