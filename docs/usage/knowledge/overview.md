---
last_confirmed_phase: 13
---

# L2 role-graph schemas — overview

Phase 13 ships nine schema builders that collectively close the L2
schema dispatch table per Phase 12's `ROLE_*` constants. Four seed
roles (ported from v3); five upper-layer roles (NET-NEW). All schemas
default to `strict=False` per ADR-0149; tightening waits for the
inventory helper + 2-week-no-edit observation rule per ADR-0149
§Revisions.

## The 9 schemas

| Role | Builder | Tier | Doc |
|---|---|---|---|
| `ontology` | `build_ontology_schema` | seed | [ontology.md](ontology.md) |
| `lexicon` | `build_lexicon_schema` | seed | [lexicon.md](lexicon.md) |
| `concepts` | `build_concepts_schema` | seed | [concepts.md](concepts.md) |
| `alignment:<a>:<b>` | `build_alignment_schema` | seed (parametric) | [alignment.md](alignment.md) |
| `promoted-pipelines` | `build_promoted_pipelines_schema` | upper | [promoted-pipelines.md](promoted-pipelines.md) |
| `task-patterns` | `build_task_patterns_schema` | upper | [task-patterns.md](task-patterns.md) |
| `memories` | `build_memories_schema` | upper (Local) | [memories.md](memories.md) |
| `problem-trace` | `build_problem_trace_schema` | upper | [problem-trace.md](problem-trace.md) |
| `capacity-state` | `build_capacity_state_schema` | upper (Local) | [capacity-state.md](capacity-state.md) |

`alignment` is parametric — one builder serves all role-pair alignment
graphs (`alignment:lexicon<->concepts`, `alignment:ontology<->lexicon`,
etc.). The graph *name* differs per pair; the *schema* is identical.

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
