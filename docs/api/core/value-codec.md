---
last_confirmed_phase: 50
source: mindsos_core/persistence/value_codec.py
---

# `mindsos_core.persistence.value_codec`

The node-value serialization codec (ADR-0182, Phase 50). It lets a
`Node.value` hold a structured `dict` / `list` and still round-trip
through FalkorDB, without breaking the fast path for ordinary primitive
values.

```python
from mindsos_core.persistence.value_codec import (
    encode_node_value,
    decode_node_value,
)
```

The codec is a pure two-function module — no re-export from
`mindsos_core` or `mindsos_core.persistence`. It is wired into the
persist path (`persistence/graph_repository.py`) and the load path
(`reconstruction/graph_loader.py`); application code rarely calls it
directly.

## Why it exists

A `Node.value` is `Any` JSON-serialisable type (see [node.md](node.md)).
FalkorDB properties are scalar, so a `dict` or `list` value cannot be
stored in the `value` column. ADR-0182 extends the ADR-0130
`_props_json` pattern to `value`: a node persist row carries **both** a
`value` column and a nullable `_value_json` column, and exactly one is
populated.

## The five rules (ADR-0182)

1. **Primitive fast path.** `str | int | float | bool | None` are stored
   verbatim in `value`, with `_value_json` NULL. Existing rows and the
   loader fast path are untouched.
2. **Structured split.** `dict` / `list` values JSON-encode into
   `_value_json` (canonical: sorted keys, no ASCII escaping, compact
   separators) with `value` NULLed.
3. **Discriminator on load.** A non-NULL `_value_json` is the signal to
   decode; otherwise `value` passes through unchanged.
4. **Fail loud at save.** A non-JSON-encodable value (or a dict/list with
   non-encodable interior) raises `PersistenceError` at the persist
   boundary — never silently at load.
5. **Queryability is the writer's obligation.** A JSON-encoded value is
   opaque to Cypher filtering and to the ADR-0181 index strategy. Any
   field that must be queryable/indexable is lifted by the *writer* into
   a flat primitive node property. This codec does no automatic lifting.

## `encode_node_value`

```python
def encode_node_value(value: Any) -> Tuple[Any, Optional[str]]:
    ...
```

Splits `value` into the `(value, _value_json)` persist pair. Returns
`(value, None)` for JSON primitives (rule 1) and `(None, <canonical
JSON>)` for `dict` / `list` (rule 2). Any other type — or a dict/list
whose interior is not JSON-encodable — raises `PersistenceError`
(rule 4).

## `decode_node_value`

```python
def decode_node_value(raw_value: Any, value_json: Optional[str]) -> Any:
    ...
```

Recovers the in-memory `value` from a loaded row (rule 3). If
`value_json` is `None`, returns `raw_value` (the pre-ADR-0182 fast path).
Otherwise decodes and returns the JSON. A corrupt `_value_json` column
raises `PersistenceError`.

## First production consumer

The Phase-50 `installed-skills` role-graph is the first consumer: a
`SkillInstallRecord.value` is a structured dict (manifest digest,
artifact roster, installer outcomes), persisted via this codec, with the
filterable fields (`bundle_name`, `status`, `action`, …) lifted flat per
rule 5. The `subminds` role-graph's `SubMindDefinition.value` is a second
consumer.

## Related

- [API: `Node`](node.md) — the `value` field this codec serialises.
- [ADR-0182](../../decisions/adr/0182-node-value-serialization-contract.md) — the serialization contract.
- [ADR-0130](../../decisions/adr/0130-property-bag-on-metagraph-graph.md) — the `_props_json` pattern this extends.
