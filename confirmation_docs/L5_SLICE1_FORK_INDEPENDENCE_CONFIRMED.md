# L5 Slice 1 CONFIRMED — deep_copy fork independence (ADR-0201 §deep_copy)

**Branch:** `feat/l5-slice1-fork-independence` (tip `87dcff8`)
**Gate:** 4271 passed / 12 skipped / 1 xpassed / **0 failed** (containerized full, Linux, 32m05s, 2026-07-19) — baseline 4266 + 5 new; **0 regressions**.
**core_version:** stays `phase50` (behavior fix; no phase/role/category change).
**Sequences:** `confirmation_docs/CORE_WORKITEM_TASK_INTO_L5.md` Step 2 (Slice 1 of the L5 CR).

## Problem
`copy.deepcopy` preserves ids verbatim, so `MentalModel.deep_copy` produced a fork that was
**id-identical** to its origin (same `metagraph_id`, `graph_id`, identity entries), and a cloned
provenance XRef (`source/target_metagraph_id`) resolved back to the *origin's* metagraphs. Slice 2's
`raw_task` provenance XRef makes this live.

## The fix — three layers (the import boundary forces the split)
- **Core** (`mindsos_core/models/metagraph.py`):
  - `Metagraph.regenerate_ids() -> {old->new}` — reassigns `metagraph_id` + every `graph_id`
    (`identity.replace`, rekey `graphs`), remaps `IntergraphEdge.source/target_graph_id` and
    `IntergraphHyperEdge.anchors/members` (immutable post-init → `object.__setattr__`), and this
    metagraph's own XRef `source_metagraph_id`.
  - `remap_xref_targets(id_map)` — rewrites XRef `target_metagraph_id` + rebuilds `_xrefs_by_target`.
- **L1** (`mindsos_instances/registry.py`): `ElementRegistry.remap_ids(id_map)` reids each instance's
  `metagraph_id` / `template_id` / id-bearing override values. **Must be L1**: instances carry
  `metagraph_id` (element_instance.py:110) and **core cannot import `mindsos_instances`** (verified
  boundary), so core physically cannot reach them.
- **L5** (`mindsos_intelligence/mm.py`): `deep_copy` calls `regenerate_ids` + `registry.remap_ids`
  per sub-MM, merges the maps, then `remap_xref_targets` for the cross-sibling provenance link. Only
  layer that knows an MM is three sub-MMs.

## Decisions
- **Node / edge / instance IDs are NOT regenerated** — they're task-scoped and stay valid in the
  fork; CR test 4 requires distinct `metagraph_id` + `graph_id` only.
- **Not a capacity, not a floating helper** — id bookkeeping is core substrate (the capacity
  dispatcher is itself keyed by `metagraph_id`, so it can't be a dispatched capacity); the operation
  is a method on the id-owning class in each layer.
- **`object.__setattr__`** for model structural fields (edges/hyperedges/xrefs immutable post-init).

## Why 0 regressions despite being non-additive
No existing test pinned `deep_copy`'s shared-id behavior — `phase_46/test_deep_copy_is_independent`
checks only object distinctness + root independence, both still true. The only caller is
`fork_dream_mm` (ADR-0162 dream), whose documented intent is "a fresh independent MM" — fresh ids
*align* with it.

## Tests
`tests/phase_47/test_mm_fork_independence.py` (5): core `regenerate_ids`; cross-MM
`remap_xref_targets`; L1 `ElementRegistry.remap_ids`; end-to-end fork (CR test 4 — distinct
metagraph/graph ids + provenance XRef resolves within the fork, origin untouched); pre-existing
root/object independence still holds.

## Blast radius
`mindsos_core/models/metagraph.py` (2 methods), `mindsos_instances/registry.py`
(`remap_ids` + `_remap_value`), `mindsos_intelligence/mm.py` (`deep_copy`), 1 new test file.

## Next
Slice 2 (capacity writer) — delete the executor blackboard, `capacity_mm` becomes source of truth,
write the grounding DAG + `raw_task` provenance XRef (which now resolves correctly in a fork).

**Merge sha:** _(fill after merge to main)_
