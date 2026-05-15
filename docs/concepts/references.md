---
last_confirmed_phase: 09
---

# References — hybrid model (intra-metagraph strings + cross-metagraph XRef)

MindsOS has two kinds of cross-element reference, with different cost
profiles and different mechanisms. Phase 09 ships the cross-metagraph
mechanism (`XRef`); the intra-metagraph mechanism (`ref:<role>`
property strings) was shipped earlier and is retained.

The split is locked by [ADR-0128](../decisions/adr/0128-hybrid-xref-cross-metagraph-refs.md).

## At a glance

| Scope | Mechanism | Storage | Validation | Auto-upgrade cost |
|------|-----------|---------|------------|-----|
| **Intra-metagraph** (within a single Metagraph) | `ref:<role>` property strings ([ADR-0016](../decisions/adr/0016-cross-graph-references-via-property-prefix.md)) | Property on the source `:Node`/`:Edge`/`:HyperEdge` row | Core does not validate ([ADR-0034](../decisions/adr/0034-core-never-validates-refs.md)); KL invariants cover it | n/a — intra-metagraph refs do not auto-upgrade |
| **Cross-metagraph** (Local → Global, Local → Other-Local) | `XRef` first-class primitive ([ADR-0128](../decisions/adr/0128-hybrid-xref-cross-metagraph-refs.md)) | `:XRef` row + `:XREF_OF` edge to source `:Metagraph` anchor | Optional write-time check via `target_metagraph` kwarg | O(K log N) indexed walk |

## Intra-metagraph: `ref:<role>` property strings

Properties on Nodes/Edges/HyperEdges keyed `ref:<role>` carry the id
of the target element (in another contained graph of the same
metagraph). `iter_ref_properties(props)` enumerates them.

```python
from mindsos_core import Graph, Metagraph

mg = Metagraph(name="mylocal")
ont = Graph(name="ontology", role="ontology")
lex = Graph(name="lexicon", role="lexicon")
mg.add_graph(ont)
mg.add_graph(lex)

ont.add_node("animal", type_name="Concept", node_id="animal")
lex.add_node("dog", type_name="Word", node_id="dog",
             properties={"ref:concept": "animal"})
```

Cheap, no auto-upgrade, KL invariants unchanged. Stays as Phase 03's
shipped mechanism.

## Cross-metagraph: `XRef` primitive

XRefs link an element in *this* metagraph to an element in *another*
metagraph (typically Local → Global, or Local → Other-Local).

```python
from mindsos_core import Graph, Metagraph

local = Metagraph(name="local-1")
g = Graph(name="myont", role="ontology")
local.add_graph(g)
g.add_node("doggo", type_name="Concept", node_id="doggo")

local.add_xref(
    source_id="doggo",
    target_metagraph_id="mg-global-id",
    target_role="lexicon",
    target_id="dog",
    ref_type="SPECIALISES",
)
```

The `:XRef` row persists in the source metagraph, anchored by a
`:XREF_OF` edge to the source `:Metagraph` anchor (so the cascade-
on-Metagraph-removal story is forward-only — Phase 10 ships the
cleanup of reverse-dangling XRefs).

### Optional write-time validation

Pass `target_metagraph` to `add_xref` to check the target id exists
under the named role:

```python
from mindsos_core.exceptions import XRefIntegrityError

try:
    local.add_xref(
        source_id="doggo",
        target_metagraph_id=global_mg.metagraph_id,
        target_role="lexicon",
        target_id="ghost",                     # not registered
        ref_type="SPECIALISES",
        target_metagraph=global_mg,            # validate
    )
except XRefIntegrityError as e:
    print(f"Caught: {e}")
```

Without `target_metagraph`, the XRef is "soft" — Core accepts the
write. The pivot's migration handler is the typical caller of the
soft form.

### Iteration

`Metagraph.iter_xrefs(*, source_id=None, target_metagraph_id=None,
target_id=None, ref_type=None)` yields filtered XRefs. Filters
AND-compose; unset filters act as wildcards.

```python
# Forward walk: every XRef from source `doggo`.
for x in local.iter_xrefs(source_id="doggo"):
    print(x)

# Reverse walk: every XRef pointing at `dog` in the Global metagraph.
for x in local.iter_xrefs(
    target_metagraph_id="mg-global-id", target_id="dog",
):
    print(x)

# Multi-filter AND.
for x in local.iter_xrefs(source_id="doggo", ref_type="SPECIALISES"):
    print(x)
```

Indexed via `(target_metagraph_id, target_id)` compound + per-source
forward index, so reverse walks are O(K log N) instead of O(N).

### CLI surface

Phase 09 ships a read-only verb:

```
mindsos persistence xref-list --metagraph LOCAL [--source-id SID] \
    [--target-metagraph TMID] [--target-id TID] [--ref-type RT] [--json]
```

Default output is a Rich table with truncated IDs (first 8 chars).
`--json` opt-in emits machine-readable JSON.

Write verbs (`xref-add`, `xref-remove`) are not shipped at L1 —
when L2/L3 consumers surface them, the corresponding CLI verbs land.

## Migrating legacy `ref:global_*` properties

Pre-Phase-09 user data may contain `ref:global_<role>=<id>` property
strings + a sibling `ref_type` property representing what is now an
XRef. The migration callable converts them in place:

```python
from mindsos_core.persistence.xref_migration import migrate_in_memory

n_created = migrate_in_memory(
    mg=local,
    target_metagraph_id="mg-global-id",
    default_ref_type="SPECIALISES",
)
print(f"Migrated {n_created} legacy refs to XRef rows")
```

Idempotent: tracked via `mg.properties["xref:migrated_at"]`. Per-XRef
content-tuple dedup means re-running after a partial-crash is safe.

The migration callable is programmatic-only at Phase 09 — the
production trigger is the Server first-start hook, which lands in a
later phase ([ADR-0142](../decisions/adr/0142-xref-cutover-for-ref-global.md)).

## Why two mechanisms?

Three workloads informed the split:

1. **Intra-metagraph traversal** is read-frequently and never
   auto-upgrades. Property strings are cheap; making them first-class
   buys nothing.
2. **Cross-metagraph reverse-walk** ("which Locals point at this
   Global node?") is O(N nodes × M properties) under property scan;
   becomes O(K log N) with the `(target_metagraph_id, target_id)`
   index.
3. **Auto-upgrade migration** at release boundaries walks every Local
   for cross-metagraph rewrites. The indexed XRef walk dominates the
   property scan as user count grows.

## Related ADRs

- [ADR-0016](../decisions/adr/0016-cross-graph-references-via-property-prefix.md) — `ref:*` property prefix (intra-metagraph; retained).
- [ADR-0034](../decisions/adr/0034-core-never-validates-refs.md) — Core never validates refs (narrowed by ADR-0128 §Validation for XRefs).
- [ADR-0128](../decisions/adr/0128-hybrid-xref-cross-metagraph-refs.md) — hybrid XRef primitive (Phase 09; Proposed → Accepted in Phase 14 once L2 consumes it).
- [ADR-0130](../decisions/adr/0130-property-bag-on-metagraph-graph.md) — property bag on Metagraph/Graph (Phase 09 flips Accepted; adds `xref:` namespace).
- [ADR-0142](../decisions/adr/0142-xref-cutover-for-ref-global.md) — cutover plan for `ref:global_*` user data (3 commitments; Phase 09 ships L1 commitment only).
