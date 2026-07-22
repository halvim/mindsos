# CORE CHANGE REQUEST — carry `resolved_reference` from Phase 1 into Phase 2

**Filed:** 2026-07-18 · joint arc1+arc3 core chat
**Consumer of record:** arc1 (D1.6 / D1.8 — the resolved task must reach planning)
**Status:** proposed — NOT built. Needs owner approval before any code.
**Version impact:** none. `core_version` stays `phase50` (additive; no new DataState, no
declaration change, no `__all__` delta).

**Context:** this is the one piece of CR#4's Slice 2 that the full lifecycle needs and that
D8-B/3b did **not** ship. The capacity/knowledge-MM writers (Slices 0/1/2/3) stay deferred
(no consumer under (a)-only learning); this carves out the ~4-line drop fix alone.

---

## The defect (verified against shipped code, 2026-07-18)

`interpret()` computes `resolved_reference` — the resolved task — and returns it on
`InterpretationResult` (`mindsos_intelligence/phase_1.py:281`). But `phase_1.run` (the
full-lifecycle entry) discards it:

```python
# phase_1.py:290-297 (verbatim) — run() builds Phase1Result, NO resolved_reference
return Phase1Result(
    structured_input=r.structured_input,
    hint_set_ref=hint_set.iri,
    goal=r.goal,
    task_pattern_iri=r.task_pattern_iri,
    mapping_confidence=r.mapping_confidence,
    mapping_result_ref=mr.iri,
)
```

`Phase1Result` (`phase_1.py:83-89`) has no `resolved_reference` field. Phase 2 then receives
only `(mapping_result_ref, task_pattern_iri)`:

```python
# orchestrator.py:167 → plan_construction.build(dispatcher, writer, p1.mapping_result_ref, p1.task_pattern_iri)
# plan_construction.py:39-43
def build(dispatcher, writer, mapping_result_ref, task_pattern_iri) -> PlanResult:
    dispatcher.dispatch(
        DERIVE_PLAN_IRI, {DS_MAPPING_RESULT: {"task_pattern_iri": task_pattern_iri}}
    )
```

So `planning.derive_initial_plan` plans against a `task_pattern_iri` and a confidence — **it
never sees the task**. The resolve chain fetched the ARC task JSON (`[arc_resolve,
fetch_task]`) and it was dropped one function later.

### Why it bites now

CR#2 (§am-3) shipped `_run_skill_verb`, which routes `arc solve task 7` through
`run_lifecycle` → `phase_1.run`. So the shipped verb path hits this drop. arc1's *intake*
path (`interpret()` directly) is unaffected — it reads `InterpretationResult.resolved_
reference`. **Only the lifecycle path loses the task.** D1.6's `resolve_target_datastate =
arc.raw_task` is therefore inert on the lifecycle today: the task is resolved and discarded.

## The fix — 4 edits, no contract change

The task rides the `mapping_result` **dict** that `derive_initial_plan` already consumes
(`inputs=(DS_MAPPING_RESULT,)`, `planning_v0.py:124`). No new DataState, no declaration
change, no second input.

1. **`phase_1.py`** — add to `Phase1Result`:
   ```python
   resolved_reference: Any = None
   ```
2. **`phase_1.py` `run()`** — populate it:
   ```python
   return Phase1Result(..., mapping_result_ref=mr.iri,
                        resolved_reference=r.resolved_reference)
   ```
3. **`orchestrator.py`** — pass it to Phase 2:
   ```python
   plan_result = plan_construction.build(
       self._dispatcher, writer, p1.mapping_result_ref, p1.task_pattern_iri,
       resolved_reference=p1.resolved_reference)
   ```
4. **`plan_construction.py` `build()`** — fold it into the dispatch payload:
   ```python
   def build(dispatcher, writer, mapping_result_ref, task_pattern_iri, *,
             resolved_reference=None) -> PlanResult:
       dispatcher.dispatch(DERIVE_PLAN_IRI, {DS_MAPPING_RESULT: {
           "task_pattern_iri": task_pattern_iri,
           "resolved_reference": resolved_reference}})
   ```

arc1's Local `derive_initial_plan` (one of its 7 shadow caps) then reads
`mapping_result["resolved_reference"]` — the task JSON — and plans against it.

## Why additive-inert (this one genuinely is)

- `resolved_reference` defaults to `None`. Every existing caller passes nothing → the
  payload gains one `None` key. The v0 `_derive_initial_plan` reads only `task_pattern_iri`
  (`planning_v0.py:89`), so it ignores the new key.
- No DataState IRI added, no `_CapacityBase` declaration touched, no `_validate_inputs`
  surface (the payload is a *value* inside `DS_MAPPING_RESULT`, not a new input key).
- `keyword-only` on `build()` → positional callers unbroken.
- The `interpret()`-only path (arc intake) is untouched.

Clears the design-log §0 additive-inertness gate.

## Design note — value in the dict, not a new input

Adding `resolved_reference` as a *second declared input* to `derive_initial_plan` would trip
the strict `_validate_inputs` no-unexpected contract and force a declaration change on every
brain's planning cap. Folding it into the already-declared `DS_MAPPING_RESULT` payload keeps
the contract fixed and lets each brain's planning body opt in by reading the key. This
mirrors how `mapping_confidence` already rides that same dict.

## Tests

Extend `tests/phase_47/` (or the phase-1 suite):

1. `phase_1.run` with a profile whose resolve returns a value → `Phase1Result.resolved_
   reference` is that value (today: field absent).
2. `run_lifecycle` → the `derive_initial_plan` dispatch payload's `DS_MAPPING_RESULT` carries
   `resolved_reference`.
3. v0 path (no resolve) → payload key is `None`; `_derive_initial_plan` output byte-identical.
4. A Local `derive_initial_plan` reading `resolved_reference` receives the resolved value
   end-to-end through `run_lifecycle`.

## Blast radius

`mindsos_intelligence/phase_1.py` (1 field + 1 kwarg), `mindsos_intelligence/orchestrator.py`
(1 arg), `mindsos_intelligence/plan_construction.py` (1 kwarg + payload key). No schema, no
role/category/count change, no `__all__` delta, no DataState.

## ADR

Amend the Phase-47 orchestrator ADR (ADR-0172, six-phase lifecycle) recording that Phase 1's
`resolved_reference` is threaded into Phase 2 via the `mapping_result` payload. Cross-ref
ADR-0195 (`resolved_reference` origin).

## Why core and not the brain

`Phase1Result`, `orchestrator`, and `plan_construction` are all core. No brain can thread a
value through core's own Phase-1→Phase-2 handoff. Every brain that resolves a reference into
the lifecycle hits this — arc1 first, arc3 next.
