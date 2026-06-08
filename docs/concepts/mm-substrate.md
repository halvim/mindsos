# Mental Model substrate (L4)

The Mental Model (MM) is a task's complete working state. L4 reads only from the
MM; the **no shadow state outside the MM** invariant is what makes a dream
deep-copy a self-contained, re-executable task (Chat B D-B11). The L4 substrate
that builds and guards the MM ships at Phase 46.

## Three sub-metagraphs

An MM is a metagraph of three sub-metagraphs (ADR-0165 / Chat B D-B10):

- **knowledge-MM** — L2 instances pinned for the task (ontology / lexicon /
  concepts / alignment / episodic).
- **capacity-MM** — L3 `CapacityInstance` + `DataStateInstance` with
  produces/consumes intergraph edges (the bipartite topology, instantiated).
- **intelligence-MM** — L4-authored chain artifacts (HintSet → MappingResult →
  Plan → Pipeline → PipelineRun → TaskRun, authored from Phase 47), provenance,
  orchestration state, hint values.

A thin root holds pointers only: the three sub-MM references plus `task_run_ref`,
`ref:problem_trace`, and `outcome_ref`. Chat B schemas are instantiated as
written; physical composite-collapse is a post-Phase-49 benchmark-gated option.

## Reader-writer lock

One writer-preferred reader-writer lock per active MM, at root granularity
(ADR-0164). Concurrent reads run in parallel; a write excludes all readers and
writers across the three sub-MMs. Root granularity avoids the cross-sub-MM
deadlock a per-sub-MM scheme would reopen; a per-sub-MM split is a reserved v2
throughput optimization.

## Resolution and instantiation

The MM resolver (ADR-0166) is the concrete `MMHandle`. On a cache-miss it
dispatches the requested IRI by namespace to the owning sub-MM, fetches the
source node at its current version, instantiates one node (lazy single-node),
and returns it. Growth is monotone within a task; instances are never evicted
mid-task. Each instance pins its source as an `(iri, version_int)` tuple
captured at instantiation, so the task reads a stable snapshot regardless of
later knowledge writes. Lazy inline-on-retire (the D'1 retention mechanism)
lands at Phase 48 with `kl.read_at_version` / `kl.retire_version`.

## Dream deep-copy

`MentalModel.deep_copy` produces a fresh, independent MM — the substrate
primitive a dream re-executes against (ADR-0162). The live re-execution, ALS
signal firing, and replan-injection consumption that ride on it land at Phase
47/48.
