---
last_confirmed_phase: 03
---

# `mindsos_core.Node`

A typed vertex with identity and an open property bag. Phase 03 slim
port — drops the `_version` OCC field (Phase 07).

## Dataclass fields

| Field | Type | Default | Description |
|---|---|---|---|
| `value` | `Any` | — | Primary display value. Any JSON-serialisable type (str / int / float / bool / None / list / dict). |
| `type_name` | `str` | — | Node type name. Phase 04's `Schema` validates against a declared `NodeType` vocabulary; Phase 03 stores verbatim. |
| `node_id` | `str` | UUID4 | Stable id for the lifetime of the object. Caller may supply an IRI / content-addressed id for stable references (KL importers). |
| `properties` | `Dict[str, Any]` | `{}` | Open property dict. |

## Identity semantics

`Node.__hash__` hashes `node_id`; `__eq__` compares `node_id`. Two nodes
with the same id but different attributes are `==` — graph-internal
membership checks treat them as the same node.

## Construction patterns

```python
from mindsos_core import Node

# Auto-minted UUID4 id.
n = Node(value="Alice", type_name="Person")

# IRI-passthrough id (KL importers).
n = Node(value="Person", type_name="DolceClass",
         node_id="dolce-dul-4.0:Person")

# With properties.
n = Node(value="Alice", type_name="Person",
         properties={"age": 30, "tags": ["staff", "remote"]})
```

In practice, code constructs nodes via `Graph.add_node(...)` rather than
direct instantiation, so the registry is updated.

## What's not in Phase 03

* `_version` field (ADR-0127 OCC) — Phase 07 with persistence.
