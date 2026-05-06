---
last_confirmed_phase: 05b
---

# Intergraph edges

Phase 05b ships **`IntergraphEdge`** — a directed binary edge between
two nodes that live in *different* graphs within the same metagraph.
The metagraph owns the edge (registers it in the unified
`IdentityRegistry` per ADR-0020; persists it in the metagraph state
file). Per the locked Pushback 1-C scope split, 05b ships the binary
primitive only; **`IntergraphHyperEdge`** (n-ary) lands in Phase 05c.

The motivating use case is *typed cross-graph relationships* —
linking a lexicon-graph node `cat` to a concepts-graph node `Cat#1`
via an `EVOKES` edge, where the edge itself is not part of either
graph but is semantically owned by the metagraph that contains both.
The cat=c+a+t compositional pattern (a word node identity-bound to
its constituent letter nodes) ships fully in Phase 05c with the
`IntergraphHyperEdge` primitive; 05b's binary `IntergraphEdge`
already supports the `compositional: bool` flag for use cases where
1-to-1 identity binding is sufficient.

## Where IntergraphEdge fits in the L1 primitive set

| Construct | Endpoints | Container | Phase |
|---|---|---|---|
| `Edge` | Node ↔ Node | one Graph | 03 |
| `HyperEdge` | n × Node | one Graph | 03 |
| `MetaEdge` | Graph ↔ Graph | one Metagraph | 05a |
| `MetaHyperEdge` | n × Graph | one Metagraph | 05a |
| **`IntergraphEdge`** | **Node ↔ Node, across graphs** | **one Metagraph** | **05b** |
| `IntergraphHyperEdge` | n × Node ↔ m × Node | one Metagraph | 05c |
| `XRef` | Node ↔ Node | *across* metagraphs | 09 |

`IntergraphEdge` carries five required fields (`source_graph_id`,
`source_node_id`, `target_graph_id`, `target_node_id`, `type_name`)
plus optional `label`, `properties` (namespaced bag), `edge_id`
(auto-minted), and a `compositional: bool` flag (default `False`).

## The `compositional` flag

When `compositional=True`, the edge is identity-bearing — its existence
defines what its endpoints *are* in the metagraph's working semantics.
Removing or mutating such an edge would silently corrupt the
composition. The L1 enforcement is strict:

* `Metagraph.remove_intergraph_edge(edge_id)` raises
  `CompositionalImmutableError`.
* `Metagraph.update_intergraph_edge_properties(edge_id, ...)` raises
  the same.
* `Metagraph.remove_graph(graph_id)` runs an atomic precheck pass over
  all incident `intergraph_edges`; if any has `compositional=True`,
  the whole `remove_graph` raises `CompositionalImmutableError` with
  the offending `edge_id` *before* any mutation. State unchanged.
* The flag itself is immutable post-construction. `IntergraphEdge`
  overrides `__setattr__` to refuse any post-init write to
  `compositional`.

There is no demotion verb in 05b. To eliminate a compositional edge,
the tester must `mindsos metagraph reset --name <MG> --force --yes`
and rebuild the metagraph from scratch. Phase 10 may add a `--force`
bypass under the full ADR-0135 surface; until then, compositional
truly means immutable.

## Cross-graph identity invariants

Per ADR-0020, every metagraph shares one `IdentityRegistry` across
its contained graphs and its own elements. The `add_intergraph_edge`
factory enforces 14 validation steps (locked in Pushback 16-A), with
node existence checked against `source_graph.nodes` directly (no
belt-and-suspenders registry check — the registry is always a
superset of the per-graph node set under ADR-0020).

Cross-metagraph intergraph edges are **out of contract**. An
`IntergraphEdge` whose source and target nodes live in different
metagraphs cannot be added — each metagraph has its own
`IdentityRegistry`, and the source/target node lookup against
`mg.graphs[gid].nodes` fails. The cross-metagraph case is what
`XRef` (Phase 09) covers.

## Schema validation via MetagraphSchema

Phase 05b also ships `MetagraphSchema`, a metagraph-attached schema
container that carries `IntergraphEdgeType` declarations. See
`docs/usage/core/metagraph-schema.md` for the full surface; the short
version is:

* `MetagraphSchema(strict=False)` constructor mirrors Phase 04
  `Schema` (basename-keyed; reusable across N metagraphs).
* `IntergraphEdgeType` constrains `allowed_source_types` /
  `allowed_target_types` (Node `type_name`) and
  `allowed_source_graphs` / `allowed_target_graphs` (Graph `role`).
* `Metagraph.attach_schema(ms, schema_name=...)` runs eager
  validation over every existing intergraph edge; first violation
  raises with the offending `edge_id` and leaves state unchanged.

Schema mutation while attached is a documented carry-forward Phase 04
footgun: adding a new `IntergraphEdgeType` after attach does NOT
trigger re-validation. Tester must re-attach to surface drift.

## Persistence (Phase 05b in-memory + JSON; Phase 07 FalkorDB)

In Phase 05b, `IntergraphEdge` instances live in
`mg.intergraph_edges: Dict[str, IntergraphEdge]` and persist to the
metagraph state file at `metagraph-<name>.json` (state-file v=2 — the
05a→05b cumulative one-way migration adds the `intergraph_edges`
array and the optional `schema_name` reference). Phase 07 will ship
the FalkorDB Cypher emit using **Pattern B** (anchor-node):

```
(:IntergraphEdge {edge_id, type_name, properties..., _compositional})
  -[:SOURCE]->(:Node {node_id: source_node_id})
(:IntergraphEdge ...)
  -[:TARGET]->(:Node {node_id: target_node_id})
(:Metagraph {metagraph_id})-[:OWNS]->(:IntergraphEdge ...)
```

The `_compositional` reserved key in `RESERVED_PROPERTY_KEYS`
(Pushback 18-A + 6 carry-forward) reserves the future Cypher property
name; the dataclass field itself is the unprefixed
`IntergraphEdge.compositional`.
