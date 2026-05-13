---
last_confirmed_phase: 07
---

# Repositories — `GraphRepository`, `MetagraphRepository`, `InstanceRepository`

## `GraphRepository`

Persist + update + remove on a single `Graph`. Caller owns the
`Client` lifecycle (P6 A).

```python
from mindsos_core.persistence import GraphRepository

repo = GraphRepository(client)
repo.persist(graph, metagraph_id=parent_mg_id)  # optional metagraph_id link
new_v = repo.update_node_properties(graph_id, node_id, {"k": "v"})
new_v = repo.update_node_properties(graph_id, node_id, {"k": "v"},
                                    expected_version=3)  # OCC opt-in
repo.remove_node(graph_id, node_id, removed_by="alice@example.com")
```

`update_*_properties` always bumps `_version` (P7 C); when
`expected_version` is supplied the MATCH predicate carries it; zero
rows ⇒ `OptimisticConcurrencyConflict`. `remove_*` writes a
per-(graph, element) `:Tombstone` row then DETACH-DELETEs the
element (P69 A). Read-path soft-delete filter lands in Phase 10.

### Persist-time check (ADR-0123 §2)

After each UNWIND batch, `persist` runs an indexed scan to surface
duplicate ids; non-empty result ⇒ `IntegrityCheckError`.

## `MetagraphRepository`

Programmatic-only at Phase 07 (P60 A) — no CLI verb consumes this;
metagraph sync CLI lands Phase 08 per M14 + P12 D.

```python
from mindsos_core.persistence import MetagraphRepository

repo = MetagraphRepository(client)
repo.persist(metagraph)
```

`persist` orchestrates the 4-step lifecycle (P96 A):

1. **Core writes** — anchor (`:Metagraph` with `_props_json` +
   optional `schema_name` plain property per P100 A) + contained
   graphs (via `GraphRepository`) + MetaEdges + MetaHyperEdges +
   IntergraphEdges + IntergraphHyperEdges. MetaEdges + IntergraphEdges
   are grouped by `type_name` (one UNWIND per rel type since FalkorDB
   can't parameterise rel-type names).
2. **WAL commit** — mechanism-only at Phase 07; no L1 consumer.
3. **Observers fire** — `mg._persist_observers` invoked with `mg`.
   Phase 07 consumer:
   `mindsos_instances.persistence.InstanceRepository.persist_all`,
   wired via `mindsos_instances.attach_registry(mg)`.
4. **Return.**

Observer failure leaves Core+WAL state consistent; instance
persistence may be partial. Tester convention (P33 A): re-run
`persist` (MERGE-idempotent).

### `_props_json` encoding (ADR-0130 + P62 A)

Canonical JSON encoding:

```python
json.dumps(metagraph.properties, sort_keys=True, ensure_ascii=False,
           separators=(",", ":"))
```

**No size cap** (Phase 07 P83 C). The narrow chained driver-exception
catch maps oversized writes to `PersistenceError`:

```python
try:
    client.run_query(anchor_query, params)
except (redis.exceptions.ResponseError,
        falkordb.exceptions.FalkorDBError) as e:
    raise PersistenceError(f"_props_json write failed: {e}") from e
```

`schema_name` (the existing `mg.schema_name` dataclass field) is
persisted as a plain Cypher property on the `:Metagraph` row (P100 A);
NO `:MetagraphSchema` labeled node; NO `:HAS_SCHEMA` edge.

## `InstanceRepository` (sibling — `mindsos_instances.persistence`)

```python
from mindsos_instances.persistence import InstanceRepository

repo = InstanceRepository(client)
repo.persist_element_instance(inst, metagraph_id)
repo.persist_composite_instance(comp, metagraph_id)
# or, bulk via the observer entry point used by attach_registry:
repo.persist_all(registry)
```

Subscribes to `Metagraph.register_persist_observer` via
`mindsos_instances.attach_registry(mg)` (idempotent — re-attach does
not double-subscribe). The observer reads `mg._persist_client` at
fire time (set transiently by `MetagraphRepository.persist`); `None`
means a pure in-memory persist with no DB writes (no-op).
