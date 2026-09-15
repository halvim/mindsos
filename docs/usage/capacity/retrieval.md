---
last_confirmed_phase: 30
---

# Retrieving Pipelines (L3)

This page covers the BFS pipeline finder per ADR-0071. See the
companion [Building](building.md) page for capacity registration and
invocation.

**Amendment status:** the Phase 30 surface this page originally described
is **superseded**. CORE-C3R1 (ADR-0071 §am-2, ADR-0206 §3) replaced the
linear pipeline with a converging DAG and replaced the no-route exception
with a returned `FindVerdict`; the snippets below are the amended surface.
The `last_confirmed_phase` marker in the front-matter predates that work
and is not bumped — core work since Phase 50 ships on `feat/*` branches
with `<name>-confirmed` tags, not phase numbers.

## What `find_pipeline` does

Given a `start_datastate` IRI and a `target_datastate` IRI,
`find_pipeline` performs a **breadth-first search** over the bipartite
`PRODUCES`/`CONSUMES` edge set (ADR-0156) and returns the **shortest
pipeline by capacity count** as a `Pipeline` dataclass. It deliberately
ignores `:CONSTRAINT` edges — constraint filtering is L4's
responsibility per ADR-0071.

## Algorithm shape

BFS is **datastate-keyed**, not capacity-keyed. The frontier consists
of DataState IRIs; `view.consumers_of(datastate)` (via `CONSUMES` edges)
returns candidate next-capacities; `view.outputs_of(capacity)` (via
`PRODUCES` edges) pushes the next frontier. The bipartite edge set is the
explicit structural substrate (ADR-0156); the algorithm walks via
consumers, not via the capacity-keyed `successors_of` primitive (which
exists for a different use case).

## Basic usage

```python
from mindsos_capacity import find_pipeline

verdict = find_pipeline(
    cl,
    start_datastate="datastate:text.raw",
    target_datastate="datastate:text.tokens",
)

assert verdict.found
pipeline = verdict.pipeline
assert len(pipeline) == 1
print(pipeline.steps[0].capacity_iri)
# capacity:perception:text.space_split
```

When `start_datastate == target_datastate`, the BFS short-circuits and
returns an empty-steps `Pipeline` — the requested target is already
present, which `verdict.already_held` reports directly.

When no chain exists within `max_depth` steps (default 8) the finder
returns a don't-know verdict rather than raising — no route is a fact
about the world, not a technical failure (ADR-0206 §3):

```python
from mindsos_capacity import FIND_BFS_EXHAUSTED

verdict = find_pipeline(
    cl,
    start_datastate="datastate:nothing.here",
    target_datastate="datastate:text.tokens",
)

assert not verdict.found
assert verdict.pipeline is None
assert verdict.reason == FIND_BFS_EXHAUSTED
```

## Session-scoped finding

Pass a `session` to walk the user's Local metagraph view; with no
session the BFS walks the Global view:

```python
verdict = find_pipeline(
    cl,
    session=session,
    start_datastate="datastate:text.raw",
    target_datastate="datastate:analysis.sentiment",
)
```

Local-only capacities are visible to the BFS only when a session is
supplied.

## Shortest-by-capacity-count invariant

`find_pipeline` returns the shortest path by **capacity count**, not by
edge count. The distinction matters when a capacity has multiple
outputs: BFS may enqueue several frontiers per capacity step, but each
frontier records exactly one `DAGStep`. The test
`tests/phase_30/test_find_pipeline_shortest_by_capacity_count.py` locks
this invariant against a branching-capacity fixture where capacity-count
and edge-count diverge.

## `Pipeline`, `DAGStep` and `DAGEdge`

CORE-C3R1 replaced the linear pipeline with a converging DAG: a step
carries its full declared input set, and the dataflow between steps is
carried by explicit edges rather than by a per-step `via`.

```python
@dataclass(frozen=True)
class DAGStep:
    capacity_iri: str
    input_datastates: Tuple[str, ...]
    output_datastates: Tuple[str, ...]

@dataclass(frozen=True)
class DAGEdge:
    producer: int   # producing step index, or START (-1) for a start DataState
    consumer: int
    datastate: str

@dataclass(frozen=True)
class Pipeline:
    start_datastates: Tuple[str, ...]
    target_datastate: str
    steps: Tuple[DAGStep, ...]
    edges: Tuple[DAGEdge, ...] = ()
```

All three are frozen — pipelines are values, not in-place-mutable plans.
`steps` is topologically ordered: every step appears after the steps that
produce its inputs, and iterating a `Pipeline` yields them in that order.
An empty `steps` tuple means the target was already available.

## What this slice does NOT do

- **No adapter synthesis.** Adapters present in L3 participate as
  ordinary capacities; the BFS does not invent new adapters.
- **No constraint filtering.** L4 reads `:CONSTRAINT` edges via
  `view.iter_constraints` and post-filters paths returned by the
  finder.
- **No cost / learned-confidence scoring.** Edge count is the only
  cost; ADR-0071 §Alternatives explicitly defers Dijkstra-style
  weighting to L4.
- **No `include_deprecated` filter.** Deferred per Phase 29 R5 PB-37
  carry-forward; will land when soft-delete becomes an L4 concern.

## CLI

```
mindsos capacity find --start datastate:text.raw \
                      --target datastate:text.tokens \
                      [--max-depth N] [--json]
```

The CLI builds a fresh in-memory `CapacityLayer` per invocation (no
persistence at Phase 30) — on an empty layer, BFS exhausts
immediately and the CLI exits 1 with a `bfs_exhausted` verdict. The
verb exists to lock the CLI surface; real-user workflows arrive at
Phase 31 when text builtins auto-register on layer construction.

Default output is a human-readable arrow chain
(`start_ds -> cap1 -> mid_ds -> cap2 -> target_ds`). The `--json`
flag emits the verbose `Pipeline` shape:

```json
{
  "start_datastates": ["datastate:text.raw"],
  "target_datastate": "datastate:text.tokens",
  "length": 1,
  "steps": [
    {
      "capacity_iri": "capacity:perception:text.space_split",
      "input_datastates": ["datastate:text.raw"],
      "output_datastates": ["datastate:text.tokens"]
    }
  ],
  "edges": [
    {
      "producer": -1,
      "consumer": 0,
      "datastate": "datastate:text.raw"
    }
  ]
}
```

### Exit codes

- `0` — pipeline found (or `start == target`).
- `1` — no route found. The `--json` payload's `error` is the verdict
  reason (a closed-set `FIND_*` constant, e.g. `bfs_exhausted`), never an
  exception class name; `message` is `verdict.detail` and is not parsed.
- `2` — usage error (missing `--start` or `--target`).

The Phase 30 CLI does **not** define exit 3 (invocation-envelope
failure); that arrives at Phase 31 alongside the `invoke` CLI verb.

## `mindsos capacity problem-trace tail`

```
mindsos capacity problem-trace tail [--limit N] [--json]
```

Peek at the N most-recent `ProblemTraceRecord`s on the current
`CapacityLayer`'s sink. Because the CLI builds a fresh layer per
invocation, the sink is always empty at Phase 30 — the verb exists to
lock the surface. Drain semantics belong to L4's lifecycle process per
ADR-0074.
