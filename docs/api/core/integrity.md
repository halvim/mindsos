---
last_confirmed_phase: 07
---

# Integrity scanner — `verify_invariants` + `verify_invariants_graph`

Per ADR-0123 §3 — every Core invariant lives in Python; FalkorDB has
no UNIQUE / FK constraints. The scanner is the gap-closer.

## `verify_invariants(mg) -> IntegrityReport`

```python
from mindsos_core.persistence import verify_invariants

report = verify_invariants(metagraph)
if report:
    print(report.summary())
    print(f"duplicate ids: {report.duplicate_ids}")
    print(f"cross-graph leaks: {report.cross_graph_edges}")
```

5 buckets:

| Bucket | Type | Detects |
|--------|------|---------|
| `duplicate_ids` | `list[(label, [ids])]` | Same id under more than one element per label. |
| `cross_graph_edges` | `list[(edge_id, source_graph_id)]` | `:Edge` rows whose source / target Nodes live in different Graphs (Edge is intra-graph by ADR; use `IntergraphEdge` for cross-graph). |
| `orphan_hyperedges` | `list[hyperedge_id]` | `:HyperEdge` rows with zero members. |
| `orphan_metaedges` | `list[metaedge_id]` | `:MetaEdge` / `:MetaHyperEdge` rows referencing graphs not in the metagraph. |
| `dangling_tombstones` | `list[tombstone_id]` | Phase 10 territory — empty in Phase 07. |

`IntegrityReport.__bool__` returns `True` iff any bucket is non-empty.
`summary()` returns a one-line human description; `"clean"` when no
findings.

## `verify_invariants_graph(graph) -> PartialIntegrityReport`

Phase 07 P98 A — graph-scoped sibling that powers
`mindsos persistence verify --source=db --graph G`. Returns 3 of 5
buckets:

| Bucket | Type | Graph-scoped meaning |
|--------|------|----------------------|
| `duplicate_ids` | `list[(label, [ids])]` | Restricted to graph-local labels (`:Node` / `:Edge` / `:HyperEdge`). |
| `orphan_hyperedges` | `list[str]` | Same as full scanner. |
| `dangling_tombstones` | `list[str]` | Phase 10; empty in 07. |

The 2 Metagraph-context buckets (`cross_graph_edges`,
`orphan_metaedges`) are absent here; CLI reports them as
`[skipped — requires --source=memory --metagraph M]`.

## CLI integration

```
$ mindsos persistence verify --metagraph alice
summary: clean

$ mindsos persistence verify --graph alice-lexicon --source=db
summary: 1 orphan hyperedge(s)
orphan_hyperedges: ['he-abc123']
[skipped] cross_graph_edges, orphan_metaedges — requires --source=memory --metagraph M
```

Exit codes per P64 A: `0` clean / `1` CLI usage error / `2` system
error (DB unreachable) / `3` drift findings.

## Forward-compat note

The Phase 07 `--source=db` partial scanner closes when Phase 08 ships
the metagraph_loader — that unlocks the full 5-bucket scanner against
FalkorDB. At that point, `verify --source=db --metagraph M` becomes
supported and the `[skipped]` line goes away.
