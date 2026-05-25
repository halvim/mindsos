---
last_confirmed_phase: 28
---

# Capacity Layer (L3) — overview

The **Capacity Layer** (L3) is where MindsOS keeps the functions that acquire and manipulate knowledge — perception, comprehension, derivation, decomposition, combination, path-finding, retrieval, scoring, trace, signalling, interaction, and learning-methods. State lives in L2 (KnowledgeLayer); behaviors live here.

!!! info "Quick facts"
    - Layer: **L3 Capacity** (between L2 KnowledgeLayer and L4 Intelligence)
    - Owns: one Global + N per-user Local metagraphs
    - In-memory first; FalkorDB persistence helpers ship with first consumer
    - Capacities are **fixed-not-learned** — state lives in L4 / L5

## Anatomy

A Capacity Layer instance owns:

| Surface | What it holds | Phase |
|---|---|---|
| Global Metagraph | One shared L3 metagraph with 12 category role-graphs + the shared `capacity:datastates` graph | 28 |
| Local Metagraphs | One per active user, lazily created on first write | 28 |
| Capacity registry | Maps every IRI to its Python declaration (Local-wins over Global) | 28 |
| Capability gate | Enforces `CAN_WRITE_GLOBAL` on Global-scoped writes; carve-out for pre-server bootstrap | 28 |
| DataState registry | Shared per metagraph; one `DataState` node per shape | 28 |
| TYPE_COMPAT auto-discovery | Wires producer→consumer edges from inputs/outputs lists | 29 |
| Constraint edges | Admin-authored CONSTRAINT edges between capacities | 28 (API); 29 (enforcement) |
| Pipeline finder | BFS through TYPE_COMPAT for a target DataState | 30 |
| Invocation runtime | `invoke` returns `InvocationResult`; emits ProblemTraceRecord on failure | 30 |
| Residents | Long-running monitor capacities | 31 |
| Built-in text capacities | `text.space_split`, `text.sentence_split`, etc. | 31 |
| Write capacities | Five admin-side write capacities (consolidate, trace, promote, author, state) | 33-35 |

## Constructing a `CapacityLayer`

```python title="capacity_basic.py"
from mindsos_capacity import CapacityLayer

cl = CapacityLayer()
gmg = cl.global_metagraph()
alice_mg = cl.local_metagraph("alice")
```

Constrain the categories at construction time (useful in tests):

```python
from mindsos_capacity import CATEGORY_PERCEPTION, CATEGORY_PATH_FINDING

cl = CapacityLayer(categories=(CATEGORY_PERCEPTION, CATEGORY_PATH_FINDING))
```

Or hand in a pre-built Global Metagraph (the future
`bootstrap_capacity_from_falkordb` helper will use this form):

```python
from mindsos_capacity import create_global

global_mg = create_global()
cl = CapacityLayer(global_metagraph=global_mg)
```

## Registering DataStates and Capacities

DataStates are registered first (capacities reference them by IRI):

```python title="register_datastate.py"
from mindsos_capacity import DataState, ShapeDescriptor

raw = DataState(name="text.raw", shape=ShapeDescriptor.scalar("str"))
cl.register_datastate(raw)
```

Capacities (reactive / monitor / adapter) follow:

```python title="register_capacity.py"
from mindsos_capacity import Capacity, CATEGORY_PERCEPTION

cap = Capacity(
    name="text.space_split",
    category=CATEGORY_PERCEPTION,
    inputs=(raw.iri,),
    outputs=("datastate:text.tokens",),
    implementation=lambda **kw: {"datastate:text.tokens": kw[raw.iri].split()},
)
cl.register_capacity(cap)
```

The IRI form is `capacity:<category>:<name>` (ADR-0066); collisions within a metagraph raise `CapacityRegistrationError`. The `category` MUST be one of the [12 functional categories](categories.md) (ADR-0065).

## Global vs. Local — Local wins on collision

When a user registers a capacity with the same IRI as a Global one (typically with `ref_to_global` + `ref_type`), the Local declaration **wins** at lookup (ADR-0061):

```python title="local_specialization.py"
from mindsos_server.session import Session

alice = Session.for_testing("alice", is_admin=False)
cl.register_datastate(raw, session=alice)
cl.register_capacity(
    Capacity(
        name="text.space_split",
        category=CATEGORY_PERCEPTION,
        inputs=(raw.iri,),
        outputs=("datastate:text.tokens",),
        implementation=lambda **kw: {"datastate:text.tokens": kw[raw.iri].split(",")},
    ),
    session=alice,
    ref_to_global="capacity:perception:text.space_split",
    ref_type="SPECIALISES",
)
```

## Capability gate (ADR-0078 + ADR-0080)

Writes to the Global metagraph are gated on `CAN_WRITE_GLOBAL`:

* **`session is None`** → permitted (ADR-0080 bootstrap carve-out — the admin / library path before the server is online).
* **`session` with `CAN_WRITE_GLOBAL`** → permitted.
* **`session` without `CAN_WRITE_GLOBAL`** → `PermissionError`.

User sessions (`Session.for_testing(uid, is_admin=False)`) lack the capability; admin sessions (`is_admin=True`) carry it. The capability string is `"CAN_WRITE_GLOBAL"` (matches `mindsos_server.capabilities.CAN_WRITE_GLOBAL` per ADR-0078 §amendment-1).

## What ships at Phase 28 vs. later

| Capability | Phase | Notes |
|---|---|---|
| Register / lookup / Local-wins / capability gate | **28** | This page |
| 12 functional categories — see `categories.md` | 28 (+ 29 amend) | |
| TYPE_COMPAT auto-discovery + constraint enforcement | 29 | |
| Pipeline finder + invocation runtime + ProblemTraceRecord | 30 | |
| Residents + text builtins + pathfinding | 31 | |
| Write capacities + symmetric write contract + per-flow validators | 33-35 | |

See `confirmation_docs/PHASE_28_DESIGN_LOG.md` for the full Phase 28 design rounds.
