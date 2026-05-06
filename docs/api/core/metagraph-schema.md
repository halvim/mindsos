---
last_confirmed_phase: 05b
---

# `MetagraphSchema`

```python
from mindsos_core import MetagraphSchema, IntergraphEdgeType
```

Phase 05b's metagraph-level schema container. Per the locked
Pushback 1-C scope split, 05b's `MetagraphSchema` carries
`IntergraphEdgeType` only; Phase 05c will add `MetaEdgeType` /
`MetaHyperEdgeType` / `IntergraphHyperEdgeType` to the same container
class.

See `docs/usage/core/metagraph-schema.md` for the CLI surface.

## Constructor

```python
MetagraphSchema(*, strict: bool = False)
```

Mirrors Phase 04 `Schema` exactly: no `name` field on the class — the
state-file basename is the identity that the CLI persists by.
`strict` ships from day one (Pushback 10-A); gates property-type
validation only (Pushback 5-A).

## Registration API

```python
ms.add_intergraph_edge_type(iet: IntergraphEdgeType) -> IntergraphEdgeType
```

Validates `iet.name` against ADR-0021 cypher rel-type regex
(`^[A-Z][A-Z0-9_]{0,63}$`); raises `UnknownTypeError` on duplicate
name; raises `CypherError` on regex mismatch.

```python
ms.require_intergraph_edge_type(name: str) -> IntergraphEdgeType
```

Lookup by name; raises `UnknownTypeError` if missing.

```python
ms.intergraph_edge_types  # → Mapping[str, IntergraphEdgeType] (defensive copy)
```

## Validation API

```python
ms.validate_intergraph_edge(
    type_name: str,
    source_node_type: str,
    target_node_type: str,
    source_graph_role: str | None,
    target_graph_role: str | None,
) -> None
```

Always runs (independent of `strict`). Enforces type-existence +
`allowed_source_types` + `allowed_target_types` + `allowed_source_graphs`
+ `allowed_target_graphs`. Empty frozenset on any allowed-* axis means
"any" (mirrors `EdgeType` empty-set semantics). `Graph.role=None` is
unmatchable when the corresponding `allowed_*_graphs` constraint is
non-empty (Python set membership: `None not in frozenset({"x"})`).

Raises `UnknownTypeError` with a message naming which constraint
failed.

```python
ms.validate_intergraph_edge_properties(
    type_name: str, properties: Mapping[str, Any]
) -> None
```

Per Pushback 5-A — early-returns when `not strict`. Phase 04
`Schema.validate_node_properties` precedent: under strict mode,
unknown keys are refused only if the type's `property_types` map is
non-empty (empty = type author opted out of strict typing for this
type). `ref:*` keys pass through (validated upstream as UUID strs).

## `IntergraphEdgeType`

```python
@dataclass(frozen=True)
class IntergraphEdgeType:
    name: str
    allowed_source_types: FrozenSet[str] = frozenset()
    allowed_target_types: FrozenSet[str] = frozenset()
    allowed_source_graphs: FrozenSet[str] = frozenset()
    allowed_target_graphs: FrozenSet[str] = frozenset()
    property_types: Dict[str, PropertyType] = field(default_factory=dict)
    description: Optional[str] = None
```

Mirrors Phase 04 `EdgeType` constraint surface (allowed sources /
targets) + adds Pushback 4-A's role-based graph constraints. Frozen
dataclass; immutable post-construction. The `property_types` map uses
the Phase 04 8-variant `PropertyType` vocabulary.

## Reuse across N metagraphs

Per Pushback 11-A, `MetagraphSchema` is reusable across N metagraphs
via name reference. The metagraph state file v=2 carries
`schema_name: str | null` pointing to a `metagraph-schema-<name>.json`
state file. Multiple metagraphs may attach the same schema simultaneously.

Per Pushback 12-A, only one schema may be attached per metagraph at a
time. Per Pushback 32-D, re-attaching the same schema by name re-runs
eager validation (NOT a silent no-op) — surfaces drift from Pushback
23-A schema-mutation footgun.

See `Metagraph.attach_schema(schema, *, schema_name)` and
`Metagraph.detach_schema()` for the binding API.
