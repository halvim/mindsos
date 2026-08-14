# ADR-0201 — Amendment 5: the fold manifest carries the member correlation, and the empty domain is a stop

**Status:** Accepted (2026-08-15). Records the shape-(a) substrate ship
(`core-collection-member-dont-know`, owner-ruled to shape (a) 2026-08-14, and
`core-empty-fold-domain`, ruled alongside it). The reducer-side and
DataState-side halves of the shape-(a) contract are ADR-0209; this amendment
owns what changed in **this ADR's vocabulary**: one manifest field and one
`RunStopped` token.

## Context

Two facts about a fold run cannot be said by the run's own nodes — the same
class of fact amendment 4 built the manifest for.

**1. Which member produced which verdict.** The fold's seeded list preserves
member order, and the shipped renderer correlated member ↔ verdict by full
verdict-value equality against that list. Two demo findings (N-F1/N-F2,
`decision-records` bijection ship) proved value-equality is not injective —
and shape (a) makes the breaking case *legal*: two members that both refuse
in-band may carry identical refusal values, while their pages must differ.
A value contract ("a refusal value must identify its member") was proposed
and withdrawn as unenforceable — legitimate identical duplicates exist, so a
uniqueness check false-positives and anything weaker is a convention, the
class twice found insufficient (coordination §44 Q1). Ref-path parsing was
separately rejected: references resolve by `graph_id`, never role or
ref-path (S-F2).

**2. That there was nothing to fold at all.** A claim with zero exposures ran
end to end and concluded payable-from-nothing (`core-empty-fold-domain`,
demo-critical sweep F1): the map wrote `[]`, nothing in core refused an empty
fold domain, and the reducer received an empty list as legitimate input. The
demo's reducer now refuses — but that is content policy in one consumer's
body, and the next consumer reintroduces the hole. Owner ruling: **at the
fold, not per reducer.**

`RUN_STOPPED_REASONS` had the same shipped-without-ADR gap `RunManifest` had
before amendment 4: three ADRs *mention* `RunStopped`
(0201-am-4, 0207, 0208) and none owned the reason vocabulary (verified by
grep, coordination §45). It is owned here, in the vocabulary ADR's line.

## Decision

**1. `MANIFEST_MEMBER_GRAPH_IDS` (`"member_graph_ids"`).** A fold run's
manifest value carries the ordered `graph_id` of each map member's grounding
graph, in member order. Position *i* of the fold's seeded list correlates to
`member_graph_ids[i]` **structurally** — no value equality, no ref-path
parsing. Three shipped precedents composed, none invented: the manifest
exists to carry what the graph cannot say (amendment 4 / probe D);
references resolve by `graph_id` (S-F2); `case_label` is the threading
precedent for a run-scoped fact arriving via `execute_pipeline`. A LIST in
the node **value** survives the store in order (S-F1), which is what member
order needs; the primitives-only rule binds properties, not the value.

- The key is **absent** on every non-fold run. Absent ≠ empty: `[]` is a
  fold over zero members; absence is a run that never had a member set.
  Presence is also how a reader may recognise a fold run without the
  parentless-list heuristic.
- A member's id is the graph of the run that **produced its `sub_target`**
  (ADR-0209 ruling D3): flat member — the accepted attempt's graph (rejected
  retries persist nothing); sub-plan member — the producing run's graph,
  read off the graphs themselves (a `PRODUCES` edge into a
  `DataStateInstance` of the `sub_target` type), never off a ref-path.
- The ids ride the executor's blackboard between map and fold
  (`execution.member_graph_ids_key`), because a Slice-3b targeted re-run
  reuses the retained blackboard and re-executes one member: the id list
  must splice exactly as the retained outputs splice, and a carrier with any
  other lifetime desynchronises from the values it correlates.
- The ids are recorded only when the run grounds **and** collects graphs
  (`mm` and `capacity_graphs` both present) — an id pointing at a graph
  nobody keeps is a reference into nothing.
- ⚠ The spelling collides with the MetaHyperEdge persistence **row key**
  `member_graph_ids` (`mindsos_core/cypher/builders.py`). Different layer,
  different object; recorded so a grep for the bare string is not misread.
  (`mindsos_instances` once renamed a field over this exact string.)

**2. `RUN_STOPPED_EMPTY_DOMAIN` (`"empty_domain"`)**, the fourth member of the
closed `RUN_STOPPED_REASONS` set, with its `RUN_STOPPED_PHRASES` entry
(*"there was nothing to decide from - the collection had no members"*), so
the manifest snapshot and every renderer translation arrive with no renderer
change. An empty domain is a structural fact about the **run**; a reducer
"concluding" from it would manufacture an epistemic claim out of machinery
state — the S2 / ADR-0208 inversion. Mechanics:

- `_run_fold_milestone` never hands a reducer an empty domain. It orders a
  **pre-dispatch stop** through `execute_pipeline`
  (`stop_before_dispatch=`), so the fold run still grounds: manifest (with
  `member_graph_ids=[]`), seeded empty list, then the terminal `RunStopped`
  minted **alone** — no `CapacityInstance`, because no capacity ran (guard
  G3, the `record_cancelled` argument verbatim). The writer method is
  `record_empty_domain`; `record_stopped` refuses the token exactly as it
  refuses `cancelled`.
- The stop's `stopped_detail` is prose-by-contract (S-3): no IRI, no
  internal ref — the render-time G6 scan treats a leaked ref as core
  leaking into a prose field, and it is right to.

## Consequences

- The demo renderer's value-equality bijection is **demoted to a
  cross-check**, not deleted: once it reads `member_graph_ids` as primary,
  identical bare verdicts become legal on the manifest path, and
  `test_identical_bare_verdicts_do_not_collapse_onto_one_member` is
  **re-scoped to the no-manifest path, never deleted** (the value check
  still refuses ambiguity where the manifest is absent or stale). The
  parentless-list fold-detection heuristic (`dr_render.py`) retires in the
  same demo ship. Deferred to the demo lane by owner ruling D5 (2026-08-15).
- A **partial fold** (the machinery half,
  `core-member-machinery-failure-partial-record` — NOT built by this ship)
  gets its clean form: position *i* has a `graph_id`, the entry is absent,
  that graph carries a `RunStopped` ⟹ a stop block in place; anything else
  ⟹ raise. The demo's unmatched-member raise is re-scoped **when that
  ships**, not before.
- `execution.run`'s fold docstring paragraph — *"which member produced which
  verdict stays structural rather than becoming a manifest field"* — was
  reversed by this amendment and rewritten in the same commit;
  `tests/phase_48/test_fold_grounding.py`'s header carried the same sentence
  and is corrected with it.
