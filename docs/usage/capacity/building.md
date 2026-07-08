---
last_confirmed_phase: 30
---

# Building Capacities (L3)

This page walks through the Phase 28+30 capacity-building API end-to-end:
construct a `CapacityLayer`, register `DataState` nodes, register
`Capacity` declarations, and invoke them through the L3 façade. The
companion page [Retrieval](retrieval.md) covers the BFS pipeline finder
shipped at Phase 30.

!!! note "Phase 30 scope"
    Phase 30 ships the Python-side `CapacityLayer.invoke` method and a
    minimal `mindsos capacity` CLI (`find` + `problem-trace tail`). The
    CLI does **not** yet ship `invoke` as a verb — that arrives at
    Phase 31 alongside text builtins that auto-register on layer
    construction. Phase 30 CLI is programmer-facing: it constructs a
    fresh in-memory `CapacityLayer` per invocation, so any registered
    capacity comes from the Python session that imports
    `mindsos_capacity`, not from a CLI registration verb.

## 1. Construct a layer

```python
from mindsos_capacity import CapacityLayer, CATEGORY_PERCEPTION

cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
```

`CapacityLayer(categories=...)` bootstraps the Global metagraph with
the named category role-graphs plus a shared `capacity:datastates`
graph. The full 13-category bootstrap (`CapacityLayer()` with no
`categories` kwarg) is the production path; the example above narrows
to a single category for clarity. Local metagraphs are created lazily
on first write under a session.

## 2. Register `DataState` nodes

A `DataState` declares the shape of a value that flows between
capacities — input or output. Register one node per shape:

```python
from mindsos_capacity import DataState, ShapeDescriptor

raw_text = DataState(
    name="text.raw",
    shape=ShapeDescriptor.scalar("str", opaque_tag="text.raw"),
)
tokens = DataState(
    name="text.tokens",
    shape=ShapeDescriptor.list_of("str", opaque_tag="text.tokens"),
)

cl.register_datastate(raw_text)
cl.register_datastate(tokens)
```

Without a `session` kwarg the registration targets the Global metagraph
(ADR-0080 bootstrap carve-out — `session=None` permits Global writes).
Passing a `session` targets the Local metagraph of `session.user_id`.

### Group DataStates (ADR-0199)

A DataState whose value is a set/list of individually-addressable members
declares `group=True` + `member_ds` (the member type's IRI). Group and member
are **distinct** types — the finder never bridges them; L4 owns the loop that
unpacks a group to feed member-consuming capacities.

```python
obj = DataState(name="object", shape=ShapeDescriptor.scalar("object"))
objects = DataState(
    name="objects", shape=ShapeDescriptor.list_of("object"),
    group=True, member_ds=obj.iri,
)
```

## 3. Register a `Capacity` declaration

A `Capacity` pairs a graph-level identity (IRI + category + I/O
DataState IRIs) with a Python callable. The callable receives the
inputs by IRI as kwargs and returns a mapping of output IRIs to values
(or a single value when the capacity declares exactly one output).

```python
from mindsos_capacity import Capacity

space_split = Capacity(
    name="text.space_split",
    category=CATEGORY_PERCEPTION,
    inputs=(raw_text.iri,),
    outputs=(tokens.iri,),
    implementation=lambda **kw: {tokens.iri: kw[raw_text.iri].split()},
)

cl.register_capacity(space_split)
```

`register_capacity` emits the bipartite topology edges (ADR-0156):
one `PRODUCES` IntergraphEdge per declared output (capacity→DataState)
and one `CONSUMES` IntergraphEdge per declared input (DataState→
capacity). The pipeline-finder walks these edges; the `inputs`/`outputs`
lists are no longer stored as node properties.

### Same-type operands (ADR-0198)

A capacity consuming N operands of **one** DataState type (e.g. a binary
comparator over two objects) declares `operand_arity={ds.iri: N}`. At invoke
that key must carry a length-N list, which the body reads positionally. Core
checks **length only** — per-slot typing and operand roles (from/to,
container/contained) are the body's concern. Arity keys must be declared
inputs, else `register_capacity` raises.

```python
same_object = Capacity(
    name="same_object", category=CATEGORY_PERCEPTION,
    inputs=(obj.iri,), outputs=(verdict.iri,),
    operand_arity={obj.iri: 2},
    implementation=lambda **kw: {verdict.iri: kw[obj.iri][0] == kw[obj.iri][1]},
)
cl.register_capacity(same_object)
cl.invoke(same_object.iri, inputs={obj.iri: [o_a, o_b]})
```

### MM reads must be declared (ADR-0200)

A reactive body receives the mental-model read handle (`context.mm_handle`)
only if its declaration sets `reads_mm=True`. The default (`False`) yields
`mm_handle=None`, so read-data must arrive as declared inputs. Set
`reads_mm=True` only for capacities that legitimately navigate the MM
(retrieval, trace).

## 4. Invoke (Phase 30)

`CapacityLayer.invoke` is the reactive invocation entry point per
ADR-0072. It returns an `InvocationResult` envelope:

```python
result = cl.invoke(
    space_split.iri,
    inputs={raw_text.iri: "the quick brown fox"},
    task_id="task-1",
)

assert result.success is True
assert result.outputs[tokens.iri] == ["the", "quick", "brown", "fox"]
assert result.error is None
```

On a raised exception, the envelope captures it (never propagates):

```python
def boom(**_):
    raise RuntimeError("intentional")

bad = Capacity(
    name="text.boom",
    category=CATEGORY_PERCEPTION,
    inputs=(raw_text.iri,),
    outputs=(tokens.iri,),
    implementation=boom,
)
cl.register_capacity(bad)

result = cl.invoke(
    bad.iri,
    inputs={raw_text.iri: "x"},
    task_id="task-2",
    step_id="step-1",
)

assert result.success is False
assert isinstance(result.error, RuntimeError)

# A ProblemTraceRecord was emitted to the layer's sink:
records = cl.problem_trace.records()
assert len(records) == 1
assert records[0].error_kind == "exception:RuntimeError"
```

### Foot-gun — `task_id=None`

If you omit `task_id`, the envelope is still returned with
`success=False` on exception, **but no ProblemTraceRecord is emitted**.
L4's lifecycle process is the canonical caller and will always supply
`task_id`; pre-L4 callers should too if they want anomaly forensics.

### Unknown IRI raises

Unknown IRIs are caller bugs, not envelope failures, per ADR-0072
§Decision's "L3 raises for its own invariants" carve-out:

```python
from mindsos_capacity import CapacityRegistrationError

with pytest.raises(CapacityRegistrationError):
    cl.invoke("capacity:perception:no.such", inputs={})
```

## 5. Local-wins specialisation

If a Local capacity registered with the same IRI as a Global capacity
exists for the session's user, the Local declaration wins on
`invoke` lookup — mirroring KL's specialisation rule (ADR-0061):

```python
sess = make_session("alice")  # any SessionProtocol-conforming object

# Same IRI as global; Local impl overrides.
local_echo = Capacity(
    name="text.space_split",
    category=CATEGORY_PERCEPTION,
    inputs=(raw_text.iri,),
    outputs=(tokens.iri,),
    implementation=lambda **kw: {tokens.iri: ["LOCAL"]},
)
cl.register_capacity(
    local_echo,
    session=sess,
    ref_to_global=local_echo.iri,
    ref_type="SPECIALISES",
)

res = cl.invoke(local_echo.iri, inputs={raw_text.iri: "x"}, session=sess)
assert res.outputs[tokens.iri] == ["LOCAL"]
```

When `session=None`, lookup goes straight to Global.

## Next

See [Retrieval](retrieval.md) for the Phase 30 BFS pipeline finder
that locates the shortest capacity chain from a `start_datastate` to a
`target_datastate`.
