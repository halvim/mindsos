# Planning (the shipped `planning.*` v0 catalog)

> ⚠ **This page describes the SHIPPED PLACEHOLDER CATALOG, not the current design.**
> The current design of planning is
> **[ADR-0206](../decisions/adr/0206-planning-decomposition-confidence.md) — "Planning as
> a loop"**: the steps are `request → hint → map → plan`, *plan* is a loop
> (`search → find → decompose → repeat`), a plan is a **DAG of milestones** rather than a
> DFS tree, and **confidence — not a depth bound — is the stopping rule**. ADR-0206 is
> **Proposed and unbuilt** (CORE-C4 has not started), so what is below is what the code
> does today: four placeholders that ADR-0206 §8 deletes. The lazy-DFS + max-depth-3 model
> described under *Plan-tree semantics* is **retired by ADR-0206 §4**. See ADR-0172
> §amendment-2.

A task's strategy is a **Plan**: a recursive tree of **Milestones** built in
LifecyclePhase 2 (Chat B D-B23). The four `planning.*` capacities are L3
decisions the orchestrator dispatches; Phase 47 ships them as a **placeholder
v0 catalog** that **core** deletes — CORE-C4R3 / C4R7, not a subsystem
(`RULES.md` §8).

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

⚠ **Every sentence in this section is retired by ADR-0206.** §4 retires `MAX_DEPTH`: a
breakdown is always possible (a capacity is a one-step pipeline at confidence 1.0), so the
confidence threshold is the stopping rule and a depth bound is unnecessary — and
decomposition emits **one layer at a time**, recursing only where confidence is missing,
rather than expanding lazily on activation. §2 makes a plan a **DAG**: sequential and
parallel are the presence or absence of an edge, not DFS order and a `sequence_index`.

## v0 catalog discipline

The Phase-47 v0 capacities (and the `phase1_v0` + `orchestration_v0`
placeholders) carry a `placeholder=True` registration marker. The production
guard is **opt-in installation**: the Global bootstrap never installs them, so a
bare system never holds them; only an explicit `install_*_v0` call does.

⚠ **Who replaces them has changed.** This page used to say WSD installation replaces the
v0 catalog. It does not: WSD is a subsystem and owns nothing architectural (`RULES.md` §8).
The real `planning.*` family is **core** work — **CORE-C4R3** builds it and **CORE-C4R7**
deletes every `placeholder=True` capacity, per ADR-0206 §4 + §8 and
`confirmation_docs/CORE_RECONCILIATION_PLAN.md` §5.
