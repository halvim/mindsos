---
last_confirmed_phase: 14
---

# L2 KnowledgeLayer — overview

Phase 14 ships the L2 entry point: the `KnowledgeLayer` class with
Global + Local metagraph lifecycle, `MetagraphView` read-only access,
and `ensure_*_role_graph` bootstrap helpers. Phase 13 closed the
schema dispatch table; Phase 14 makes those schemas usable by
attaching them to role-graphs in metagraphs.

For the architectural model of Global + Local (and the lifecycle
hooks), see [global-local.md](../../concepts/global-local.md).

## Bootstrap

```python
from mindsos_knowledge import KnowledgeLayer

# First install (admin)
kl = KnowledgeLayer.bootstrap()
# → KnowledgeLayer with Global containing 6 named role-graphs;
#   0 Locals.

# Server startup (warm restart)
loaded_global = ...  # read from FalkorDB
kl = KnowledgeLayer(global_metagraph=loaded_global)
```

The 6 Global named role-graphs ensured at bootstrap are listed
in [global-local.md](../../concepts/global-local.md#global). The
2 Local named role-graphs (`memories`, `capacity-state`) are
ensured per-user on the first `kl.local_metagraph(user_id)` or
`kl.install_local_metagraph(...)` call.

Alignment pair-graphs (`alignment:<a>:<b>`) are **not** created at
bootstrap — Phase 15's Alignments importer mints them on demand.

## Read access

```python
global_view = kl.global_view()              # MetagraphView
local_view = kl.local_view("alice")          # MetagraphView (auto-creates Local)

# Discovery
global_view.roles()                           # {ROLE_ONTOLOGY, ...}
global_view.graphs_by_role("ontology")        # [<Graph>]
global_view.alignment_graph("ontology", "lexicon")  # <Graph> | None

# Element access
global_view.get_node("ontology", "dolce-dul-4.0:PhysicalObject")
list(global_view.iter_nodes("ontology", type_="DolceClass"))
global_view.get_edges("ontology", node_id, edge_type="subClassOf")
global_view.step("ontology", node_id)         # incident edges (alias)
```

Per [ADR-0138 Proposed](../../decisions/adr/0138-kl-drops-write-api.md),
honoured by Phase 14 PB-6: **no write methods on KL**. Mutation goes
through L1 (the `Graph` reference returned by
`MetagraphView.graphs_by_role(role)[0]`), and at Phase 33-35 through
`KLWriteHandle` per [ADR-0143 Proposed](../../decisions/adr/0143-kl-write-handle-pattern.md).

## Per-user Local lifecycle

```python
# Server-driven (Phase 25 wires this to login/logout)
kl.install_local_metagraph("alice", loaded_local)     # at login
local = kl.extract_local_metagraph("alice")            # at logout

# Library/test convenience (no server)
local = kl.local_metagraph("alice")                    # lazy auto-create
```

`install_local_metagraph` raises `AlreadyInstalledError` if a Local
is already installed; `extract_local_metagraph` raises
`NotInstalledError` on miss. Both per ADR-0042 §Decision.

## What Phase 14 does NOT ship

| Feature                             | Phase | ADR / lock              |
|-------------------------------------|-------|-------------------------|
| Per-edge alignment-anchor IRI builder | 15  | Phase 14 PB-1           |
| MetagraphSchema scanner             | 15    | Phase 14 PB-1           |
| `follow_ref` cross-metagraph helper | 25 / L3 phases | Phase 14 PB-10 |
| `step(... version=...)` kwarg       | 17    | Phase 14 PB-15          |
| Validators (semantic invariants)    | 36    | ADR-0139 / Phase 14 PB-14 |
| CLI verbs over KL                   | 17    | Phase 14 PB-13          |
| Write capacities (L3-side)          | 33-35 | ADR-0138 + ADR-0143     |
| `request_promotion` user-flow       | 16    | ADR-0137 / Phase 14 calibration |

## Schemas (Phase 13 surface — unchanged)

Phase 13's 9 schema builders + dispatch are unmutated. The full
list:

## The 9 schemas

| Role | Builder | Tier | Doc |
|---|---|---|---|
| `ontology` | `build_ontology_schema` | seed | [ontology.md](ontology.md) |
| `lexicon` | `build_lexicon_schema` | seed | [lexicon.md](lexicon.md) |
| `concepts` | `build_concepts_schema` | seed | [concepts.md](concepts.md) |
| `alignment:<a>:<b>` | `build_alignment_schema` | seed (parametric) | [alignment.md](alignment.md) |
| `promoted-pipelines` | `build_promoted_pipelines_schema` | upper | [promoted-pipelines.md](promoted-pipelines.md) |
| `task-patterns` | `build_task_patterns_schema` | upper | [task-patterns.md](task-patterns.md) |
| `episodic_memories` | `build_episodic_memories_schema` | upper (Local) | [episodic-memories.md](episodic-memories.md) |
| `problem-trace` | `build_problem_trace_schema` | upper | [problem-trace.md](problem-trace.md) |
| `capacity-state` | `build_capacity_state_schema` | upper (Local) | [capacity-state.md](capacity-state.md) |

`alignment` is parametric — one builder serves all role-pair alignment
graphs (`alignment:concepts:lexicon`, `alignment:lexicon:ontology`,
etc.; sorted role atoms separated by `:` per ADR-0154 + D-L2-1,
Phase 39 L2-35 reconciliation). The graph *name* differs per pair;
the *schema* is identical.

## Dispatch

```python
from mindsos_knowledge import schema_for_role

s = schema_for_role("lexicon")          # one of the 8 named roles
s = schema_for_role("alignment:a<->b")  # alignment-prefix branch
s = schema_for_role("unknown")          # raises UnknownRoleError
```

## CLI

```bash
mindsos knowledge schema show --role lexicon [--json]
mindsos knowledge schema validate --role memories \
    --graph-file ~/.mindsos/graph-mymemories.json \
    [--json] [--exit-zero]
```

Phase 13's `validate` runs L1 structural validation only (NodeType
registered, EdgeType endpoint type check, HyperEdgeType member type
check). Semantic validation (cross-role refs etc.) ships in Phase 36
per ADR-0139.

## Strict-tighten roadmap

Per ADR-0149 §Revisions: a per-role flip to `strict=True` requires
(a) running the inventory helper (deferred to first-consumer phase),
(b) a 2-week-no-edit observation period, and (c) an explicit ADR-0149
§Revisions amendment. The `test_strict_false_sentinel.py` regression
catches any flip that bypasses this process.
