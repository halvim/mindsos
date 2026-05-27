# Code review checklist

Phase 34 ship (R1 PB-D). Closes ADR-0143 §Accept criterion (c) — the
"never mutates" rule on `KLWriteHandle` lives here.

Three items. Future phases append.

## 1. `KLWriteHandle` never mutates (ADR-0143 §Constraint)

The handle exposes accessors + validators only:

* `metagraph()` — read-only state inspection.
* `graph()` — returns the L1 `Graph` reference; mutation happens via
  `graph().add_node(...)` on the L1 surface, not on the handle.
* `mint_iri(...)` — pure IRI construction.
* `validate_node(...)` / `validate_xref(...)` — Phase 36 wires; pure
  validators.
* `write_and_validate(...)` — composite that calls `graph().add_node`
  through L1; the handle still does not own a mutation method.

**Reject** any PR that adds `KLWriteHandle.add_node`, `.add_xref`,
`.set_property`, or any method that calls a L1 mutation primitive
through `self.*` instead of `self.graph().*`. Capacity bodies that need
mutation reach for `handle.graph()` and call L1 directly, or use
`handle.write_and_validate(...)` which encapsulates the L1 call site.

The handle is a `@dataclass(frozen=True)` — that prevents field
mutation but does NOT prevent method accretion. The discipline is
social; this checklist is the enforcement.

## 2. Write capacities have `outputs=()` (pipeline terminators)

Per ADR-0146 §amendment-1 clause 4 + Phase 33 R2 PB-K. Write capacities
consume but emit no DataState into the flow graph; Phase 30's BFS
pipeline finder treats them as dead-ends; `runtime.invoke`'s Phase 34
bypass branch surfaces the `WriteResult` via
`InvocationResult.write_outcome` instead of `.outputs`.

**Reject** any PR that registers a write capacity with non-empty
`outputs=(...)`. Use the bypass; L4 invokes writes directly, not via
pipeline discovery.

## 3. Capacity bodies extract `session` + `kl` via `context.get(...)`

Per ADR-0146 §amendment-1 clause 2 (Phase 33) + Phase 34 R0 PB-5. The
capacity callable signature is `(**inputs, context=context)`; `session`
and `kl` (when present) live in `context`, not as positional args.

**Reject** any PR that:

* Adds positional `session` or `kl` params to capacity body signatures
  (`def my_capacity_impl(session, kl, **inputs): ...`).
* Routes `session` or `kl` through `**inputs` instead of `context`.
* Constructs a fresh `KnowledgeLayer` inside the body
  (`kl = KnowledgeLayer.bootstrap()`) instead of reading from context.

The CapacityLayer constructor (`CapacityLayer(kl=...)`) is the
single-source-of-truth wiring; `invoke()` injects into context
conditionally; bodies extract via `context.get("kl")` and raise
`RuntimeError` if missing (programmer error per ADR-0146 §Decision).
