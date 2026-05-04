---
last_confirmed_phase: 04
---

# `mindsos_core.schema.Schema`

A `Schema` gathers `NodeType` and `EdgeType` declarations and exposes
validation hooks called by the `Graph` primitive on `add_*` and
`update_*`.

## Constructor

```python
class Schema:
    def __init__(self, *, strict: bool = False) -> None: ...
```

Phase 04 keeps the parent project's ctor verbatim: a `Schema` has no
`name` field. The `mindsos schema` CLI uses the state-file basename
(`schema-<name>.json`) as the schema's identity at the persistence
layer.

## Registration

```python
def add_node_type(nt: NodeType) -> NodeType
def add_edge_type(et: EdgeType) -> EdgeType
```

Both raise `UnknownTypeError` on duplicate registration.

`add_edge_type` additionally:

1. Validates `et.name` as a Cypher rel-type identifier
   (`^[A-Z][A-Z0-9_]{0,63}$`) via
   `mindsos_core.cypher.identifiers.validate_edge_type_identifier`. Bad
   names raise `CypherError`.
2. Verifies every name in `allowed_sources` / `allowed_targets` is a
   registered `NodeType`. Unknown ones raise `UnknownTypeError`.

## Queries

```python
@property
def node_types(self) -> Mapping[str, NodeType]
@property
def edge_types(self) -> Mapping[str, EdgeType]

def require_node_type(name: str) -> NodeType    # raises UnknownTypeError
def require_edge_type(name: str) -> EdgeType    # raises UnknownTypeError
```

The `*_types` properties return shallow copies — registration order is
not preserved through them. The CLI / persistence layer always sorts by
name.

## Validation

```python
def validate_edge(
    edge_type_name: str,
    source_type_name: str,
    target_type_name: str,
) -> None    # UnknownTypeError on out-of-set source/target

def validate_node_properties(
    type_name: str, properties: Mapping[str, Any],
) -> None    # PropertyShapeError under strict mode

def validate_edge_properties(
    type_name: str, properties: Mapping[str, Any],
) -> None    # PropertyShapeError under strict mode
```

`validate_*_properties` are no-ops when `strict=False` (only the
generic `validate_user_properties` rules apply — primitives + reserved
keys). Under `strict=True`:

* Unknown keys are allowed only if the declared `property_types` map is
  empty (per-type opt-out).
* `PropertyType.INT` does NOT match `bool` values.
* `PropertyType.FLOAT` matches both `float` and `int` (FalkorDB
  coercion).
* `ref:*` keys are skipped (handled upstream by
  `validate_user_properties`).

## Exceptions raised

| Exception            | Inherits from | Raised when |
|---------------------|---------------|-------------|
| `UnknownTypeError`   | `CoreError`   | duplicate registration; unregistered type lookup; edge endpoint not in allowed set. |
| `PropertyShapeError` | `CoreError`   | strict-mode property type mismatch; undeclared key under strict typing; reserved key in user property bag (`id`, `type`, etc.); non-primitive value; `ov__` prefix. |
| `CypherError`        | `CoreError`   | edge type name fails `^[A-Z][A-Z0-9_]{0,63}$`. |

All three inherit from `CoreError` (NOT from `SchemaError` — the
structural-vs-semantic distinction is catchable separately).

## Phase 04 implementation notes

* **`Graph.add_*` `_validate` kwarg.** Each `Graph.add_node` /
  `add_edge` / `add_hyperedge` accepts `_validate: bool = True`. The
  default runs `validate_user_properties` on the property bag.
  `_validate=False` is used ONLY by the rehydration path
  (`mindsos_cli.commands.graph._state_to_graph`) to tolerate Phase 03
  v=1 state files that may contain reserved-key or non-primitive
  properties. Schema-level checks (type registration, strict
  PropertyType maps) ALWAYS run regardless of this flag — the kwarg
  gates the user-property contract only.

  Phase 08's `_restore_*` reconstruction helpers will subsume this
  kwarg pattern; Phase 04's `_validate` is the bridge.

* **`update_node_properties` / `update_edge_properties`.** Both
  validate the **full** merged candidate bag (no `_validate=False`
  escape hatch on update). A node loaded from a Phase 03 v=1 state
  file with reserved-key properties will fail on default merge;
  recovery is via `--replace` (which strips non-ref keys, preserves
  `ref:*` keys, and applies the validated user-supplied bag).
  Phase 04 does NOT bump `Node._version` on update — the
  optimistic-concurrency contract from ADR-0127 ships in Phase 07.

* **No `Schema.name` field.** The `Schema` class ctor stays
  parent-shape: `__init__(*, strict: bool = False)`. Persistence
  identity is the state-file basename (`schema-<name>.json`); the CLI
  layer threads the name through, but the `Schema` instance itself
  doesn't carry it.
