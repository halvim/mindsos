---
last_confirmed_phase: 04
---

# `mindsos_core.schema` — `NodeType` / `EdgeType` / `PropertyType`

## `PropertyType`

```python
class PropertyType(str, Enum):
    STRING       = "string"
    INT          = "int"
    FLOAT        = "float"
    BOOL         = "bool"
    LIST_STRING  = "list[string]"
    LIST_INT     = "list[int]"
    LIST_FLOAT   = "list[float]"
    LIST_BOOL    = "list[bool]"
```

Drawn verbatim from the parent project. Phase 04 ships the full
8-variant vocabulary — splitting (e.g. shipping primitives in Phase 04
and lists in Phase 05) was rejected because the variants are paired in
one Enum and removing them later creates Phase 04→05 forward debt.

The `.value` of each member is the canonical wire form persisted in
`schema-<name>.json` and accepted by the CLI's `--prop-type k=<value>`
flag.

### Type-coercion rules under strict validation

| Declared           | Accepts                                | Rejects |
|--------------------|----------------------------------------|---------|
| `STRING`           | `str`                                  | `int`, `bool`, `list`, `None` |
| `INT`              | `int` (excluding `bool`)               | `bool`, `float`, `str` |
| `FLOAT`            | `float`, `int` (FalkorDB coercion)     | `bool`, `str` |
| `BOOL`             | `bool`                                 | `int`, `str`, `0`, `1` |
| `LIST_STRING`      | homogeneous `list[str]`, empty list    | mixed lists |
| `LIST_INT`         | homogeneous `list[int]` (no `bool`)    | mixed; `[True]` |
| `LIST_FLOAT`       | `list[int|float]` (no `bool`)          | `[True]` |
| `LIST_BOOL`        | homogeneous `list[bool]`               | `[1, 0]` |

Empty lists are always accepted regardless of declared list type.

## `NodeType`

```python
@dataclass(frozen=True)
class NodeType:
    name: str
    property_types: Dict[str, PropertyType] = field(default_factory=dict)
    description: Optional[str] = None
```

Frozen dataclass. The `property_types` mapping is read by
`Schema.validate_node_properties` under strict mode.

* **Empty `property_types` map** = the node type opts out of strict
  property typing for itself, even if the owning Schema has
  `strict=True`. Useful for "open" types in an otherwise strict
  schema.
* `name` is a free-form identifier — no Cypher safety rule applies
  (Cypher labels for nodes are validated separately by
  `mindsos_core.cypher.identifiers.validate_label_identifier`, but the
  Phase 04 Schema does not enforce that — it accepts any non-empty
  `name`).

## `EdgeType`

```python
@dataclass(frozen=True)
class EdgeType:
    name: str
    allowed_sources: FrozenSet[str] = field(default_factory=frozenset)
    allowed_targets: FrozenSet[str] = field(default_factory=frozenset)
    property_types: Dict[str, PropertyType] = field(default_factory=dict)
    description: Optional[str] = None
```

Frozen dataclass. The `name` MUST match
`^[A-Z][A-Z0-9_]{0,63}$` (the Cypher rel-type regex per ADR-0021) —
this is enforced at registration time by `Schema.add_edge_type`.

* **Empty `allowed_sources` / `allowed_targets`** = "any registered
  NodeType is allowed" — used for unconstrained edges.
* The `property_types` map is enforced under strict mode (same rules as
  `NodeType.property_types`).
