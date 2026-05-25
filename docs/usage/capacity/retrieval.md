---
last_confirmed_phase: 30
---

# Retrieving Pipelines (L3)

This page covers the Phase 30 BFS pipeline finder per ADR-0071. See
the companion [Building](building.md) page for capacity registration
and invocation.

## What `find_pipeline` does

Given a `start_datastate` IRI and a `target_datastate` IRI,
`find_pipeline` performs a **breadth-first search** over the TYPE_COMPAT
graph (auto-discovered by Phase 29's registration hooks) and returns
the **shortest pipeline by capacity count** as a `Pipeline` dataclass.
It deliberately ignores `:CONSTRAINT` edges — constraint filtering is
L4's responsibility per ADR-0071.

## Algorithm shape

BFS is **datastate-keyed**, not capacity-keyed. The frontier consists
of DataState IRIs; `view.consumers_of(datastate)` (Phase 29 walks API)
returns candidate next-capacities; each capacity's outputs push the
next frontier. The "auto-discovered TYPE_COMPAT graph" wording in
ADR-0071 §Decision refers to the structural substrate; the algorithm
walks via consumers, not via the capacity-keyed `successors_of`
primitive (which exists for a different use case).

## Basic usage

```python
from mindsos_capacity import find_pipeline

pipeline = find_pipeline(
    cl,
    start_datastate="datastate:text.raw",
    target_datastate="datastate:text.tokens",
)

assert len(pipeline) == 1
print(pipeline.steps[0].capacity_iri)
# capacity:perception:text.space_split
```

When `start_datastate == target_datastate`, the BFS short-circuits and
returns an empty-steps `Pipeline` — the requested target is already
present.

When no chain exists within `max_depth` steps (default 8):

```python
from mindsos_capacity import PipelineNotFoundError

with pytest.raises(PipelineNotFoundError):
    find_pipeline(
        cl,
        start_datastate="datastate:nothing.here",
        target_datastate="datastate:text.tokens",
    )
```

## Session-scoped finding

Pass a `session` to walk the user's Local metagraph view; with no
session the BFS walks the Global view:

```python
pipeline = find_pipeline(
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
frontier records exactly one `PipelineStep`. The test
`tests/phase_30/test_find_pipeline_shortest_by_capacity_count.py` locks
this invariant against a branching-capacity fixture where capacity-count
and edge-count diverge.

## `Pipeline` and `PipelineStep`

```python
@dataclass(frozen=True)
class PipelineStep:
    capacity_iri: str
    input_datastates: Tuple[str, ...]
    output_datastates: Tuple[str, ...]
    via_datastate: Optional[str]  # source DataState entering this step

@dataclass(frozen=True)
class Pipeline:
    start_datastate: str
    target_datastate: str
    steps: Tuple[PipelineStep, ...]
```

Both are frozen — pipelines are values, not in-place-mutable plans.
Iteration over `Pipeline` yields its steps in execution order.

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
immediately and the CLI exits 1 with `PipelineNotFoundError`. The
verb exists to lock the CLI surface; real-user workflows arrive at
Phase 31 when text builtins auto-register on layer construction.

Default output is a human-readable arrow chain
(`start_ds -> cap1 -> mid_ds -> cap2 -> target_ds`). The `--json`
flag emits the verbose `Pipeline` shape:

```json
{
  "start_datastate": "datastate:text.raw",
  "target_datastate": "datastate:text.tokens",
  "length": 1,
  "steps": [
    {
      "capacity_iri": "capacity:perception:text.space_split",
      "input_datastates": ["datastate:text.raw"],
      "output_datastates": ["datastate:text.tokens"],
      "via_datastate": "datastate:text.raw"
    }
  ]
}
```

### Exit codes

- `0` — pipeline found (or `start == target`).
- `1` — `PipelineNotFoundError` (no path within `max_depth`).
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
