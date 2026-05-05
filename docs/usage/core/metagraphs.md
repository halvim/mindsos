---
last_confirmed_phase: 05a
---

# Working with metagraphs

The `mindsos metagraph` subapp manages graph-of-graphs containers
(`Metagraph`), graph-level relationships (`MetaEdge`, `MetaHyperEdge`),
and the metagraph's own ADR-0130 namespaced property bag.

## Subcommands

| Verb | What it does |
|---|---|
| `create --name MG [--metagraph-id ID] [--prop k=v]...` | Create an empty metagraph. CR-A: properties accepted at create time. |
| `inspect --name MG [--json]` | Counts + properties + contained-graph names. P10 JSON shape locked. |
| `list [--json]` | Enumerate every metagraph in `$MINDSOS_STATE_DIR`. |
| `reset (--name MG \| --all) [--force] [--yes] [--json]` | Delete; Q6-A orphan check refuses if any graph references the target; `--force --yes` strips back-pointers. P5: destructive flags require `--yes`. |
| `add-graph --name MG --graph G` | Attach a standalone graph; Q5-A id-collision check; N7-A refuses if `G` already metagraph-owned. P18: graph back-pointer written FIRST then metagraph. |
| `remove-graph --name MG --graph G` | Detach + cascade incident metaedges/metahyperedges. P19: always-cascade. |
| `add-metaedge --name MG --source-graph G1 --target-graph G2 --type T [--label L] [--prop k=v]... [--metaedge-id ID]` | Create a directed graph↔graph edge. P15: refuses self-loop. |
| `remove-metaedge --name MG --metaedge-id ID` | |
| `add-metahyperedge --name MG --type T --member G1 --member G2 [--member ...] [--label L] [--prop k=v]... [--metahyperedge-id ID]` | Create an n-ary graph-set edge. P15: refuses < 2 members. |
| `remove-metahyperedge --name MG --metahyperedge-id ID` | |
| `set-prop --name MG (--on-metagraph \| --metaedge-id ID \| --metahyperedge-id ID) --prop k=v ... [--replace]` | P17 3-way mutex. `--on-metagraph` operates on the metagraph's own property bag. |
| `list-metaedges --name MG [--json]` | |
| `list-metahyperedges --name MG [--json]` | |

## State-file layout (v=1)

`metagraph-<name>.json` shape:

```json
{
  "_state_version": 1,
  "metagraph_id": "<uuid4>",
  "name": "<name>",
  "properties": {"kl:active_graph_ids": "...", ...},
  "contained_graphs": ["graph-name-a", "graph-name-b"],
  "metaedges": [
    {"edge_id": "...", "source_graph": "graph-name-a",
     "target_graph": "graph-name-b", "type_name": "REFINES",
     "label": "...", "properties": {...}}
  ],
  "metahyperedges": [
    {"edge_id": "...", "type_name": "TRIO",
     "member_graphs": ["graph-name-a", "graph-name-b", "graph-name-c"],
     "label": "...", "properties": {...}}
  ]
}
```

`contained_graphs` sorted by name. Metaedge / metahyperedge entries
sorted by `edge_id`. Metahyperedge `member_graphs` sorted by graph name
(Q3-A) for byte-stable output.

## Migration: graph state file v=3 → v=4

Phase 05a bumps the **graph** state file to v=4 (adds optional
`metagraph_name` back-pointer field). Phase 04-v2 binaries cannot read
v=4 files (strict-version contract). Recovery:

* `rm -rf ~/.mindsos/graph-*.json` (clean wipe), OR
* hand-edit JSON downgrade: drop the `metagraph_name` field and set
  `_state_version: 3`.

The cumulative migration chain at `mindsos_cli/migrations/graph.py`
forward-migrates v=1 / v=2 / v=3 files to v=4 on first load (default
`metagraph_name=null`); the on-disk file is upgraded only on the next
save.

## Metagraph-owned graphs (Q4-B)

Once a graph joins a metagraph, the standalone `mindsos graph` CLI
**refuses mutations** (`add-node`, `add-edge`, `add-hyperedge`,
`set-prop`, `update-hyperedge-type`, `attach-schema`, `detach-schema`,
`reset`). Reads (`inspect`, `list-nodes`, `list-edges`,
`list-hyperedges`) warn-and-show.

The refusal stderr (P2) suggests the equivalent `mindsos metagraph ...`
invocation. Recovery: `mindsos graph detach-metagraph --name G` clears
the back-pointer (use only when the metagraph state file is missing or
unrecoverable; otherwise prefer `mindsos metagraph remove-graph`).

## Recovery patterns

### Dangling back-pointer

A graph state file with a `metagraph_name` pointing at a
metagraph that no longer exists (deleted file, corruption,
`reset --force` from a different session).

```
mindsos graph detach-metagraph --name <graph>
```

Operates on the raw JSON; bypasses metagraph rehydration. Exits 1 if no
back-pointer set.

### Identity-collision footgun

Two graphs with overlapping element ids cannot be added to the same
metagraph (Q5-A eager check). If you hit this:

* `mindsos schema list` and `mindsos graph list-nodes --name <graph>`
  to identify the colliding ids.
* Either rename one of the colliding nodes (Phase 09 XRef machinery
  arrives), or reset one graph and re-create with fresh ids.

### Lost metagraph state file

If `metagraph-mg.json` is deleted but graphs still reference it:

```
mindsos graph detach-metagraph --name <each-graph>
mindsos metagraph create --name mg
mindsos metagraph add-graph --name mg --graph <each-graph>
```

## Property bag (ADR-0130) — N1-A1

The metagraph carries a namespaced property bag. Keys must follow the
namespace convention: `kl:`, `server:`, `l3:`, `l4:`, `l5:` (validated
via Phase 04 `validate_user_properties`). Reserved keys at metagraph
scope (P13): `metagraph_id`, `_state_version`, `contained_graphs`,
`metaedges`, `metahyperedges`, `metagraph_name`.

Mid-life property updates use `mindsos metagraph set-prop --name MG
--on-metagraph --prop k=v` (P17 marker flag). At create time, use
`--prop k=v` (CR-A).

## Forward references

* **05b** — `MetagraphSchema` + `MetaEdgeType` + `MetaHyperEdgeType` +
  `IntergraphEdgeType` + binary `IntergraphEdge` + `compositional` flag.
  Metagraph state-file bumps to v=2.
* **05c** — n-ary `IntergraphHyperEdge` + `IntergraphHyperEdgeType`.
  Metagraph state-file bumps to v=3.
* **Phase 10** — soft-delete substrate on all 4 edge variants
  (Edge, HyperEdge, MetaEdge, MetaHyperEdge); RemovalImpact return on
  `remove_graph`; Graph-level property bag.
