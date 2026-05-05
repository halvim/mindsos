---
last_confirmed_phase: 05a
---

# Graphs and metagraphs

> **Phase 05a confirms the Metagraph + MetaEdge + MetaHyperEdge section.**
> Per round-3 P3 lock, ``CompositionalMetaEdge`` was dropped entirely
> (ADR-0117 Withdrawn in 05a); the compositional concept moves to a flag
> on the intergraph primitives in 05b/05c (see
> ``confirmation_docs/INTERGRAPH_EDGES_DESIGN.md``).

## What MindsOS Core ships

The Core Layer (`mindsos_core`) owns five fundamental data primitives.
Phase 03 ships the first four:

| Primitive | Role | Container |
|---|---|---|
| `Node` | A typed vertex with identity + open property bag. | a `Graph` |
| `Edge` | A directed, typed binary relationship between two nodes. | a `Graph` |
| `HyperEdge` | An n-ary relationship across an arbitrary set of nodes. | a `Graph` |
| `Graph` | A typed collection of nodes / edges / hyperedges with optional `role`. | (Phase 05) a `Metagraph` |
| `Metagraph` | *Phase 05.* A graph of graphs with binary and n-ary meta-edges between them. | — |

The Core Layer owns no reasoning, no derivation, no domain logic — those
belong to higher layers (ADR-0014).

## A `Graph` at a glance

```python
from mindsos_core import Graph

g = Graph(name="people", role="ontology")

alice = g.add_node("Alice", "Person")
acme = g.add_node("Acme", "Org")

g.add_edge(alice, acme, "WORKS_AT", label="employed since 2024")
g.add_hyperedge([alice, acme], label="project-X")
```

* `name` is human-readable; the graph also carries an auto-minted UUID4
  `graph_id` (or one supplied for reconstruction).
* `role` is optional — used by the Knowledge Layer (Phase 13+) to tag a
  graph as `"ontology"`, `"lexicon"`, `"concepts"`, etc.
* Every node / edge / hyperedge id is registered against the graph's
  `IdentityRegistry`; duplicate ids raise `IdentityError`.

## Identity

A `Graph` owns an `IdentityRegistry` instance shared across its nodes,
edges, and hyperedges. When a Phase 05 `Metagraph` contains the graph,
the registry can be supplied externally and shared across every contained
graph (ADR-0020 — registry is metagraph-scoped, not graph-scoped).

## Node / Edge / HyperEdge atomic elements

* **`Node`** — `value`, `type_name`, `node_id`, `properties`. The `value`
  is any JSON-serialisable type (str, int, list, dict, …); the
  `type_name` is verbatim in Phase 03 (Phase 04 introduces a `Schema`
  vocabulary that validates against declared `NodeType`s).
* **`Edge`** — `source`, `target`, `type_name`, `label`, `edge_id`,
  `properties`. The `type_name` is the Cypher relationship type and is
  validated against the conservative regex `^[A-Z][A-Z0-9_]{0,63}$`
  (ADR-0021) — invalid identifiers raise `CypherError`.
* **`HyperEdge`** — `nodes` (a `set`), `label`, `edge_id`, `properties`.
  Empty member sets raise `SchemaError`. When persisted (state file or
  future Cypher), members are canonicalised by sorted `node_id` so two
  state files of the same hyperedges produce byte-identical output.

## What's not in Phase 03

Per the Phase 03 row's slim-port deferral list, the following are **not**
shipped in Phase 03 and arrive in their own phases:

| Surface | Phase |
|---|---|
| `Optional[Schema]` typing + per-add validation | 04 |
| Graph-level `properties` bag (ADR-0130) | 10 |
| `Node._version` / OCC bumps (ADR-0127) | 07 |
| Soft-delete fields on Edge / HyperEdge (ADR-0133) | 10 |
| Reconstruction `_restore_*` helpers | 08 |
| `update_node_properties` / `update_edge_properties` | 04 |
| `Metagraph` + `MetaEdge` + `MetaHyperEdge` | 05a |
| `Metagraph.properties` (ADR-0130) | 05a |
| `IntergraphEdge` (binary) + `MetagraphSchema` | 05b |
| `IntergraphHyperEdge` (n-ary) | 05c |
| `CompositionalMetaEdge` | DROPPED (P3 lock; ADR-0117 Withdrawn in 05a) |

## Metagraphs (Phase 05a)

A `Metagraph` is a graph whose nodes are `Graph` objects. It owns:

* A collection of contained `Graph` instances, each with a `metagraph_name`
  back-pointer in its state file.
* `MetaEdge` — a directed, typed graph↔graph edge.
* `MetaHyperEdge` — an n-ary typed graph-set edge (n ≥ 2 per P15).
* A namespaced property bag (ADR-0130; namespaced keys like `kl:`,
  `server:`, `l3:`, `l4:`, `l5:`).

The metagraph shares its `IdentityRegistry` with every contained graph
(ADR-0020), so no two elements anywhere in the metagraph can share an id.

### Two-app CLI surface (Q4-B + P2)

* `mindsos graph` — for **standalone** graphs. Mutations refused on
  metagraph-owned graphs (Q4-B); reads (`inspect`, `list-*`)
  warn-and-show.
* `mindsos metagraph` — for **metagraph-owned** elements (graphs
  contained in a metagraph, metaedges, metahyperedges, metagraph
  property bag).

When the boundary surfaces during a tester session, refusal stderr
suggests the equivalent `mindsos metagraph ...` invocation (P2).

### `add_graph` invariants (P16)

Per round-3 lock, after `mg.add_graph(g)`:

* `g.identity is mg.identity` (shared reference, not clone).
* `g.id_strategy` is **untouched** — a metagraph can contain graphs with
  mixed id strategies. The metagraph's strategy applies only to
  metagraph-level mints.

### Recovery commands

* `mindsos graph detach-metagraph --name G` — DM-A. Clears a dangling
  back-pointer when the metagraph state file is missing or corrupted.
* `mindsos metagraph remove-graph --name MG --graph G` — clean removal
  from metagraph (clears back-pointer + cascades incident metaedges).
* `mindsos metagraph reset --name MG --force --yes` — Q6-A + P5. Strips
  back-pointers from all referencing graphs (warning) and deletes the
  metagraph.
