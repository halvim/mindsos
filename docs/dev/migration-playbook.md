---
last_confirmed_phase: 15b
---

# Schema migration playbook

When you author or tighten a `Schema` for a role-graph that already has
persisted data, the **schema migration scanner**
([ADR-0134](../decisions/adr/0134-schema-migration-scanner.md)) is the
detection tool that surfaces persisted-data violations against the new
schema. The scanner shipped at Phase 11 and was ratified at Phase 15b
(ADR-0134 §amendment-3; Status `Accepted`).

This page documents the Python API surface + one anchored usage
example paraphrased from Phase 11's test surface. Migration
*application* recipes (drop-and-reimport, in-place rewrite,
accept-as-stale) are pending the first real-migration consumer; the
scanner is detection-only by design (ADR-0134 §"What it does NOT
do").

## When to reach for the scanner

- You're about to ship a tightened role-graph `Schema` (e.g., adding
  a required property, removing an obsolete node type) and need to
  know which persisted elements violate the new contract before the
  schema lands.
- You're authoring a release-ship audit gate
  ([ADR-0144](../decisions/adr/0144-similarity-at-release-ship-audit-gate.md))
  that compares the canonical Global's schema against a previous
  release.
- You're at an admin-CLI boundary (Phase 26+ when state-file access
  for the KL surface ships) and want to scan a populated metagraph
  against an older schema definition.

The scanner is **not** invoked at write-time. Loader-side enforcement
of unknown edge types is a separate surface (ADR-0134 §amendment-1 +
§amendment-2; `unknown_edge_type_policy` kwarg on
`mindsos_core.reconstruction.load_graph_with_report` /
`load_metagraph_with_report`).

## API surface

The scanner lives at `mindsos_core/schema/migration.py`. Single entry
point dispatches on target type:

```python
from mindsos_core.schema.migration import (
    migrate_from,
    SchemaViolation,
    SchemaMigrationError,
    ViolationKind,
    DetailMode,
)

violations: list[SchemaViolation] = migrate_from(
    old_schema,        # the previous Schema the data was validated under
    target,            # a Graph or a Metagraph
    *,
    new=None,          # optional explicit new Schema; defaults to target.schema
    detail="summary",  # "summary" (default, aggregated) or "each" (per-element)
    old_schema_name=None,  # optional policy warning surface (Metagraph only)
)
```

### Return shape

```python
@dataclass(frozen=True)
class SchemaViolation:
    kind: ViolationKind           # one of five literals (below)
    type_name: str                # the affected node/edge/hyperedge type
    element_id: str               # "" in summary mode; element id in each mode
    graph_id: str                 # always set; identifies which graph
    property_name: str            # "" for removed_*_type kinds
    count: int                    # aggregate in summary; 1 in each
    detail: str                   # human-readable one-liner
```

### `ViolationKind` taxonomy

The scanner emits one of five violation kinds:

- `removed_node_type` — a node type present in `old_schema` is absent
  from the new schema; every persisted node of that type is flagged.
- `removed_edge_type` — same, for edges.
- `removed_hyperedge_type` — same, for hyperedges. (Added at Phase 11
  PB-7 C; not in ADR-0134 §1's original four-kind list. See
  ADR-0134 §amendment-3 §3a.)
- `tightened_property` — a property type changed (e.g., `INT` → tighter
  variant); persisted values that don't fit the new type are flagged.
- `missing_required_property` — a new required property was added to a
  type that exists in both old + new schemas; persisted elements
  missing the property are flagged.

Note: type *additions* (new node/edge type in new but not old) are
not violations — the scanner cares about shrinkages + tightenings
only.

### `DetailMode` semantics

- `summary` (default): one `SchemaViolation` per `(kind, type_name,
  graph_id, property_name)` quadruple; `count` aggregates the
  matching elements; `element_id` is empty. Pathological inputs (10k
  violations of one kind) produce one summary entry instead of 10k.
- `each`: one `SchemaViolation` per offending element; `element_id`
  carries the node / edge / hyperedge id; `count` is always 1. Use
  this when you need a migration script to identify specific
  elements.

### `old_schema_name` policy

When `target` is a `Metagraph` and `old_schema_name` is set, the
scanner emits a logger WARNING for each contained graph whose
`schema_name` differs from `old_schema_name`. The graph is skipped
(not added to violations). Useful when scanning a heterogeneous
metagraph that contains graphs from different schema versions — the
warning lets callers see which graphs were skipped without treating
the schema mismatch as a violation.

### Errors

`SchemaMigrationError` (subclass of `CoreError`) is raised when:

- `target` is neither a `Graph` nor a `Metagraph`.
- `detail` is not `"summary"` or `"each"`.

## Usage example — single-graph scan against a tightened schema

The pattern below is paraphrased from
`tests/phase_11/test_migrate_from_metagraph.py` (the Phase 11 test
surface that exercises `migrate_from` end-to-end).

```python
from mindsos_core.models.graph import Graph
from mindsos_core.schema.schema import Schema
from mindsos_core.schema.types import (
    EdgeType,
    NodeType,
    PropertyType,
)
from mindsos_core.schema.migration import migrate_from


# Old schema — what the persisted data was validated under.
old = Schema(
    node_types={"Person": NodeType(property_types={"name": PropertyType.STRING})},
    edge_types={"knows": EdgeType()},
)

# New schema — adds a required "email" property to Person and drops
# the "knows" edge type entirely.
new = Schema(
    node_types={
        "Person": NodeType(property_types={
            "name": PropertyType.STRING,
            "email": PropertyType.STRING,  # newly required
        })
    },
    edge_types={},  # "knows" removed
)

# Persisted data: a Graph constructed under the OLD schema.
g = Graph(name="people", schema=old)
g.add_node("Person", properties={"name": "Alice"})  # no email — will be flagged
g.add_node("Person", properties={"name": "Bob"})    # no email — will be flagged
# (Add edges of type "knows" similarly; they'll be flagged as removed.)

# Scan: pass OLD as positional, GRAPH as target, NEW via kwarg.
violations = migrate_from(old, g, new=new, detail="summary")

for v in violations:
    print(f"[{v.kind}] {v.type_name}.{v.property_name} "
          f"({v.count}× in {v.graph_id}): {v.detail}")
```

Expected output (order may vary):

```
[missing_required_property] Person.email (2× in people): property 'email' (type 'STRING') required by new schema; missing from persisted 'Person' elements
[removed_edge_type] knows. (N× in people): element type 'knows' removed from new schema
```

Switch `detail="each"` to get one violation per offending element
(with `element_id` populated) when authoring a migration script that
needs to address specific persisted rows.

## Metagraph-wide scan

When `target` is a `Metagraph`, the scanner walks every contained
graph that has a schema attached:

```python
from mindsos_core.models.metagraph import Metagraph

mg = Metagraph(name="global_knowledge")
# ... populate mg with role-graphs ...

# Optional: warn about graphs whose schema_name differs from the old.
violations = migrate_from(
    old,
    mg,
    detail="summary",
    old_schema_name="ontology-v1",  # warn-and-skip mismatched graphs
)
```

The scanner uses each graph's own `graph.schema` as the new schema
unless an explicit `new=` kwarg overrides. Graphs whose `schema is
None` are skipped (no diff to compute).

## CLI surface (Phase 11)

Phase 11 also shipped CLI verbs that wrap the API:

- `mindsos schema migrate-check --old <prior> --new <current>
  --metagraph <M> [--json]` — runs `migrate_from` against a populated
  metagraph and reports violations.
- `mindsos persistence load --unknown-edges=warn|error|ignore` —
  loader-side enforcement per ADR-0134 §amendment-1 + §amendment-2.

See `docs/dev/internals/core.md` §"Phase 11 — Loader policy + schema
migration scanner" for CLI invocation detail.

## Migration recipes — pending first real-migration consumer

> **Section pending.** Scanner output (`list[SchemaViolation]`) is
> the input to migration tooling that the caller authors. Common
> patterns will land here as the first real-migration consumer
> materialises:
>
> - **Drop-and-reimport** — for importer-curated role-graphs where
>   re-running the importer is cheaper than rewriting persisted rows.
> - **In-place rewrite** — for role-graphs where persisted data must
>   be preserved (e.g., `memories`, `problem-trace`) and a migration
>   script consumes `detail="each"` violations to update rows.
> - **Accept-as-stale** — for role-graphs where the new schema's
>   tightening is forward-only and existing rows are knowingly
>   grandfathered.
>
> The scanner itself stays detection-only per ADR-0134 §"What it
> does NOT do." When this section lands, it ships with `tests/`
> examples exercising each pattern.

## See also

- [ADR-0134 — Schema migration scanner + loader warning](../decisions/adr/0134-schema-migration-scanner.md)
  — §amendment-3 (Phase 15b) documents the shipped API and ratifies
  the Accepted flip.
- [ADR-0017 — Schema strictness opt-in](../decisions/adr/0017-schema-strictness-opt-in.md)
  — the strictness semantics the scanner respects via
  `_value_matches_type`.
- [ADR-0149 — L2 role schemas strict=False](../decisions/adr/0149-l2-role-schemas-strict-false-and-tightening-rule.md)
  — the tightening rule that defines when an L2 role-graph schema is
  considered "tightened" vs an additive change.
- Phase 11 test surface:
  `tests/phase_11/test_migrate_from_unit.py` (per-Graph) and
  `tests/phase_11/test_migrate_from_metagraph.py` (per-Metagraph) —
  the end-to-end exercise that anchors this page.
- `docs/dev/internals/core.md` §"Phase 11 — Loader policy + schema
  migration scanner" — internals detail + CLI invocation reference.
