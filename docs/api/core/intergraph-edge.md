---
last_confirmed_phase: 05b
---

# `IntergraphEdge`

```python
from mindsos_core import IntergraphEdge
```

A directed binary edge between two nodes that live in *different*
graphs within the same metagraph. Phase 05b primitive (ADR-0148 first
draft); see `docs/concepts/intergraph-edges.md` for the conceptual
overview.

## Dataclass shape

```python
@dataclass(kw_only=True)
class IntergraphEdge:
    source_graph_id: str
    source_node_id: str
    target_graph_id: str
    target_node_id: str
    type_name: str
    compositional: bool = False
    edge_id: str = field(default_factory=generate_uuid)
    label: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
```

`@dataclass(kw_only=True)` per Phase 05a P8 pattern — field ordering
doesn't matter; symmetric across all L1 edge types.

## `__post_init__`

* Runs ADR-0021 cypher rel-type regex on `type_name` (P9 pattern from
  05a, applied at the dataclass boundary). Raises `CypherError` on
  mismatch.
* Sets `_initialized = True` (via `object.__setattr__`) to mark the
  instance as past-construction; the `__setattr__` override below
  uses this flag.

## `__setattr__` — `compositional` immutability (Pushback 22-A)

```python
def __setattr__(self, name, value):
    if name == "compositional" and getattr(self, "_initialized", False):
        raise CompositionalImmutableError(...)
    object.__setattr__(self, name, value)
```

The `compositional` field is set at construction; subsequent
re-assignment raises `CompositionalImmutableError`. Other field
mutations (`label`, `properties`) work normally — properties bag
mutation is the supported mutation API via
`Metagraph.update_intergraph_edge_properties` (which itself refuses
when `compositional=True`).

## Equality + hashing

By `edge_id` only. Two `IntergraphEdge` instances with the same
`edge_id` compare equal regardless of other fields (which is the
correct semantic for identity-keyed primitives — matches 05a
`MetaEdge` / `MetaHyperEdge`).

## Repr

`IntergraphEdge(<src_graph>.<src_node> -[<type>]-> <tgt_graph>.<tgt_node>[ compositional], id=<short>)`.
The `compositional` marker appears in the repr only when the flag is
`True`.

## Construction

In production code, construct via the metagraph factory:

```python
mg.add_intergraph_edge(
    source_graph_id, source_node_id,
    target_graph_id, target_node_id,
    type_name,
    *,
    compositional=False,
    label=None,
    properties=None,
    edge_id=None,
)
```

The factory runs the 14-step validation order locked in Pushback
16-A. Direct dataclass construction is allowed for tests / fixtures /
rehydration but bypasses the factory's existence checks (the
`__post_init__` cypher regex still fires). See
`Metagraph.add_intergraph_edge` for the validation pipeline.
