---
last_confirmed_phase: 03
---

# Graphs and metagraphs

> **Phase 03 confirms the Graph + atomic-elements section.** The metagraph
> framing (Metagraph / MetaEdge / MetaHyperEdge / CompositionalMetaEdge)
> arrives in Phase 05 — see PHASE_MAP §3 row 05.

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
| Graph-level `properties` bag (ADR-0130) | 05 or 10 |
| `Node._version` / OCC bumps (ADR-0127) | 07 |
| Soft-delete fields on Edge / HyperEdge (ADR-0133) | 10 |
| Reconstruction `_restore_*` helpers | 08 |
| `update_node_properties` / `update_edge_properties` | 04 |
| `Metagraph` and its meta-edge primitives | 05 |
