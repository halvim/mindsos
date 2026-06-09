# Planning (the `planning.*` family + v0 catalog)

A task's strategy is a **Plan**: a recursive tree of **Milestones** built in
LifecyclePhase 2 (Chat B D-B23). The four `planning.*` capacities are L3
decisions the orchestrator dispatches; Phase 47 ships them as a **placeholder
v0 catalog** that WSD installation atomically replaces.

## The four capacities

- `planning.derive_initial_plan(mapping_result) → Plan` — seeds the Plan from
  the task-pattern mapping. v0 returns a single-Milestone Plan.
- `planning.decompose(milestone) → [Milestone]` — lazily expands a Milestone's
  children when it becomes active. v0 returns `[]`.
- `planning.is_leaf(milestone) → bool` — the leaf predicate that stops
  decomposition. v0 returns `True`.
- `planning.aggregate_outputs(child_outputs) → DataState` — combines child
  outputs into the parent's output. v0 returns the last child output (the
  default when no aggregator is declared).

## Plan-tree semantics

Decomposition is **lazy** — children are derived only when a Milestone becomes
active, so later sub-decomposition can use earlier Milestone outputs as context.
Siblings execute **sequentially** in DFS order (`sequence_index`); parallel
siblings are v2+. Child failure is **fail-fast** v1 (first child failure fails
the parent). Cold-start **max-depth is 3**, admin-tunable per task-pattern. Each
leaf Milestone is served by a **Pipeline** selected by the pipeline-finder.

## v0 catalog discipline

The Phase-47 v0 capacities (and the `phase1_v0` + `orchestration_v0`
placeholders) carry a `placeholder=True` registration marker. The production
guard is **opt-in installation**: the Global bootstrap never installs them, so a
bare system never holds them; only an explicit `install_*_v0` call does. WSD
installation replaces the whole v0 catalog atomically with the real `planning.*`
family — the same pattern by which the Phase-45 dream family ships v1 capacities
that downstream installation chats extend.
