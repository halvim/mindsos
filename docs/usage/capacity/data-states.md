---
last_confirmed_phase: 27
---

# Data states

A **DataState** names a representation shape — the "type" at every point in a pipeline. DataStates are purely structural; they are **human-authored only** (not synthesized).

!!! info "Quick facts"
    - Layer: **L3 Capacity**
    - Shared across Global and Local
    - Structural: no per-instance metadata
    - Stored in a dedicated `capacity:datastates` graph

## Declaring a DataState

```python title="datastate_basic.py"
from mindsos_capacity import DataState, ShapeDescriptor

raw = DataState(
    name="text.raw",
    shape=ShapeDescriptor.scalar("str", opaque_tag="text.raw"),
    description="An uninterpreted string of text.",
    provenance_category="perception",
)

tokens = DataState(
    name="text.tokens",
    shape=ShapeDescriptor.list_of("str", opaque_tag="text.tokens"),
    description="A list of whitespace-delimited surface tokens.",
    provenance_category="perception",
)
```

## ShapeDescriptor factories

```python title="shape_descriptors.py"
ShapeDescriptor.scalar("str")
ShapeDescriptor.scalar("int", opaque_tag="n")
ShapeDescriptor.list_of("str")
ShapeDescriptor.record({"lemma": "str", "pos": "str"})
ShapeDescriptor.opaque("text.embedding.384d")
```

Every descriptor has a `signature()` for comparison — two DataStates with matching signatures are strictly compatible.
