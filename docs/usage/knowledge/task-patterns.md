---
last_confirmed_phase: 43
---

# `request-patterns` role schema

> ⚠ **This page said `task-patterns` and was two schema generations out of date.**
> The role is **`request-patterns`** (`ROLE_REQUEST_PATTERNS`,
> `mindsos_knowledge/identifiers.py:66`). The node type is **`RequestPattern`** —
> `TaskPattern` exists nowhere in the code. And the node has carried **13 properties since
> Phase 43** (ADR-0152 §2 schema v2), not the three this page listed. The *file name* and the
> nav title still say "task patterns"; renaming them is a doc-wide change tracked as
> `docs-name-a-role-that-does-not-exist` in `STATE.pending_designs`.
>
> ⚠ **`SubgoalTemplate`, `DECOMPOSES_INTO` and `PREREQUISITE_OF` are DEAD, and they are NOT
> the decomposition mechanism.** They have **zero writers and zero readers** in the tree. On
> 2026-08-20 a lane read this schema and concluded `RequestPattern -DECOMPOSES_INTO->
> SubgoalTemplate` was how the system decomposes a request. It is not. Decomposition is
> **[ADR-0206](../../decisions/adr/0206-planning-decomposition-confidence.md) §4** —
> `planning.decompose` emitting one layer at a time plus `decision.select_decomposition`
> choosing one, under a confidence rule — and it is **unbuilt** (CORE-C4R3). CORE-C2R7 retires
> `SubgoalTemplate` and renames this role `request_knowledge` (ADR-0206 §7).

**2 NodeTypes, 2 EdgeTypes**, `strict=False` (ADR-0149), mutation discipline
`immutable_successor` (ADR-0153 §1). **Dual-scope** since ADR-0150 §amendment-8: authored or
learned **Local**, promoted by an admin to **Global**.

## NodeTypes

### `RequestPattern` — 13 properties (ADR-0152 §2 schema v2)

**Content** (`REQUEST_PATTERN_CONTENT_FIELDS`) — `pattern_name`, `task_shape_recognizer`,
`sufficient_predicate_iri`, `domain`, `paired_pipelines`.

**Metadata** (`REQUEST_PATTERN_METADATA_FIELDS`) — `relevant_hints`,
`mapping_confidence_threshold`, `n_observations`, `confidence`, `provenance`,
`routing_override`, `created_at`, `last_updated_at`.

⚠ ADR-0206 §7 changes two of these. `relevant_hints` and `paired_pipelines` are already
reference lists but are stored as **properties**, so nothing can walk them: `relevant_hints`
becomes **edges** carrying the confidence, and `paired_pipelines` is **retired, not converted**
— a plan reaches a pipeline through plan → milestone → pipeline, and a direct request→pipeline
link would recreate the duplication ADR-0205's ladder removes.

### `SubgoalTemplate` — dead

Advisory `subgoal_kind` and `ordering_hint`. ADR-0152 §2 deferred its content/metadata
partition and it was never made. See the banner.

## EdgeTypes

`DECOMPOSES_INTO`, `PREREQUISITE_OF` — both dead. See the banner.

## Where it's used

**Zero writers.** ADR-0206's Context states it plainly: *"`request-patterns` — which carries
`relevant_hints`, `paired_pipelines`, `mapping_confidence_threshold` and `confidence` — has no
writers."* **CORE-C4R6** is the item that builds one.

**One reader, and it reads no properties.** `mindsos_intelligence/phase_1.py`
(`_map_target_resolves`) checks that a `map` step's target IRI resolves in this role, Local then
Global (ADR-0150 §am-8). A below-threshold mapping confidence or an unresolvable target raises
`InterpretationError`.

## Builder

`build_request_patterns_schema` — `mindsos_knowledge/schemas/request_patterns.py`.

## Strict-tighten status

`strict=False` (ADR-0149).
