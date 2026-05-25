# Phase 29 Design Log — L3 TYPE_COMPAT auto-discovery + SuccessorHop + walks + rediscover

**Phase:** 29
**Layer:** L3 (Intellectual Capacity)
**Date:** 2026-05-25
**PHASE_MAP §29 (canonical scope):** TYPE_COMPAT auto-discovery (ADRs
0069/0086); `SuccessorHop` + walks (Phase 28 R4 PB-45 atomic);
`CapacityLayer.rediscover` method; no new constraint behaviour
(Phase 28 R0 PB-11 superseded — see R0 PB-1).

## §1 Inheritance

* Phase 28 paperwork: PR #38 squash-merged to main (per memory
  `[[project-mindsos-phase-28]]`); tag `phase-28-confirmed` pending
  CI green; `PHASE_28_CONFIRMED.md` not yet committed at design
  close. Phase 29 design proceeded in parallel per Phase 28 R0 PB-0
  precedent; branch creation gated on Phase 28 squash-merge to main
  (R0 PB-9 gate 1); confirm-phase gates on `phase-28-confirmed` tag
  + tag-CI green (R0 PB-9 gate 2).
* Phase 28 cumulative baseline = **3073 passed, 37 skipped** in docker
  per memory (final reconciliation at impl Step 0 from
  `PHASE_28_CONFIRMED.md` if available, else post-confirm-phase
  output).

## §2 Round-by-round picks (6 rounds: R0 + R1 + R2 + R3 + R4 + R5)

### R0 — 11 PBs

| PB | Topic | Pick |
|----|-------|------|
| PB-1 | Constraint "enforcement at 29" scope | (a) ship NOTHING new; supersede Phase 28 R0 PB-11; ADR-0070 closure footer |
| PB-2 | `SuccessorHop` shape | (a) verbatim 6-field port; sentinel test on defaults |
| PB-3 | Cross-graph MetaEdge variant | (a) ship at Phase 29; probe schemas/MetaEdgeType at R4 |
| PB-4 | `CapacityLayer.rediscover` method | (a) ship both free fn + method |
| PB-5 | Discovery failure handling | (a) raise `DiscoveryFailedError` (sub of `CapacityRegistrationError`); document partial-write |
| PB-6 | ADR slate | (c) 0069 §Impl + 0086 §Impl + 0070 closure footer |
| PB-7 | `building.md` ownership | (b) push to Phase 30; amend Phase 28 R2 PB-21 |
| PB-8 | Phase 28 sentinel-flip inventory | probe at R4 |
| PB-9 | Branch gating | (a) 2-gate parent pattern |
| PB-10 | Test inventory + cumulative target | range lock; refine R3 |
| PB-11 | Inputs/outputs property shape | probe at R4 |

### R1 — 9 PBs

| PB | Topic | Pick |
|----|-------|------|
| PB-12 | Hard vs soft delete in rediscover | (a) parent-verbatim — **OBSOLETED at R4 probe 5** (hard-delete confirmed) |
| PB-13 | ADR-0086 admin-deleted-auto-edge ambiguity | (a) ship verbatim; §Impl footer notes gap |
| PB-14 | MetaEdge removal mechanism | (a) probe — **OBSOLETED at R4 probe 4** (public `remove_metaedge` exists) |
| PB-15 | `discover_for_datastate` dead trigger | (a) ship + dead-trigger sentinel test |
| PB-16 | ADR-0086 admin-override test specs | 2-case lock for `test_admin_override_preserved.py` |
| PB-17 | `__init__.py` re-export slate | +5 → ~84; final at R3 |
| PB-18 | Sentinel-paths additions | +1 (discovery.py) |
| PB-19 | PHASE_MAP §29 edits | 3 edits at ship |
| PB-20 | Phase 28 sentinel integrity probe | R4 probe |

### R2 — 7 PBs

| PB | Topic | Pick |
|----|-------|------|
| PB-21 | EDGE_TYPE_COMPAT EdgeType property whitelist | (a) probe; additive edit if needed — **R4 probe 1: NO edit needed** (whitelist already permits all 3 discovery props) |
| PB-22 | MetaEdgeType registration in bootstrap | (a) probe — **R4 probe 2: NO edit needed** (`Metagraph.schema is None`); reduced to sentinel test |
| PB-23 | `successors_of` return ordering | (a) unsorted parent verbatim; set-compare tests |
| PB-24 | Discovery invocation-point ordering | locked discipline: index + _declarations populated BEFORE discovery call |
| PB-25 | Test inventory provisional | ~15 files / ~36 cases / ~3109 cumulative |
| PB-26 | ADR-0086 §Impl footer wording | locked text |
| PB-27 | Partial-write surface | (b) raise without partial info; document; defer (a) |

### R3 — 4 PBs

| PB | Topic | Pick |
|----|-------|------|
| PB-28 | Admin-authored TYPE_COMPAT surface | (a) document-only via direct `Graph.add_edge`; ADR-0086 §Impl flags absent capability gate |
| PB-29 | R4 pre-impl probe shortlist | locked 8-item probe |
| PB-30 | Hotfix ledger preamble | (a) reserve B-29-T1..T3 — **R4 PB-32 reduced to B-29-T1 only** |
| PB-31 | Cross-metagraph rediscover scope | (a) defer; carry-forward |

### R4 — pre-impl probes + 5 PBs

Probe results (8 items):

| # | Probe | Result |
|---|-------|--------|
| 1 | EDGE_TYPE_COMPAT EdgeType property whitelist | ✓ Phase 28 already permits via_datastate/strictness/adapter_id/discovered_automatically. Note: parent property key is `adapter_id` not `adapter_capacity` — kept parity (dataclass field maps `adapter_capacity ← edge.properties["adapter_id"]`). |
| 2 | Metagraph schema at Phase 28 bootstrap | **`Metagraph.schema is None`** — `create_global` / `create_local` don't attach a schema. MetaEdge add bypasses schema validation. PB-22 OBSOLETE. |
| 3 | `Metagraph.add_metaedge` signature | Takes graph IDs (`source_graph_id: str`, `target_graph_id: str`), not Graph objects. Halvim divergence — `_add_edge` adapted to pass `.graph_id`. |
| 4 | `Metagraph.remove_metaedge` public method | ✓ EXISTS. PB-14 OBSOLETE. |
| 5 | `Graph.remove_edge` semantics | HARD delete. PB-12 OBSOLETE. |
| 6 | Phase 28 sentinel-flip inventory for Phase 29 surface | ✓ Zero hits. No flips needed at Phase 29. |
| 7 | `_CapacityBase.to_properties()` shape | ✓ Writes `inputs`/`outputs` as `List[str]`. |
| 8 | Phase 28 baseline cumulative count | 3073 / 37 per memory; reconcile at impl Step 0. |

PBs:

| PB | Topic | Pick |
|----|-------|------|
| PB-32 | Probe-driven scope reductions | carry-forwards 10→8; hotfix slots 3→1; PB-14 + PB-12 OBSOLETE; PB-22 → sentinel-test-only |
| PB-33 | `add_metaedge` signature adaptation | locked discipline: pass `source_graph.graph_id` + `target_graph.graph_id` |
| PB-34 | Future MetagraphSchema risk | (a) sentinel `metagraph.schema is None`; design-log flag |
| PB-35 | `successors_of` deprecated filter | (c) opt-in `include_deprecated=False` default — **REVERSED at R5 PB-37** |
| PB-36 | `_drop_auto_edges` filter | (a) filter both `discovered_automatically=True` AND `deprecated_at is None` — **REVERSED at R5 PB-38** |

### R5 — pre-impl readiness + 8 PBs

| PB | Topic | Pick |
|----|-------|------|
| PB-37 | `successors_of` deprecated filter (revise R4 PB-35) | (a) parent-verbatim; drop opt-in; add carry-forward (new item 9 below) |
| PB-38 | `_drop_auto_edges` filter (revise R4 PB-36) | (a) parent-verbatim |
| PB-39 | `producers_of` / `consumers_of` filter | locked parent-verbatim (consistent with PB-37+38) |
| PB-40 | `iter_constraints` no expansion | locked |
| PB-41 | Test inventory final lock | 15 files / 39 cases (≈36 est. ± parametrize expansion) / 3109 passed + 40 skipped cumulative |
| PB-42 | ADR footer text previews | 3 footers locked |
| PB-43 | PHASE_MAP §29 edit text | 3 edits locked |
| PB-44 | `notes-phase-29.md` outline | 8-section locked |

## §3 Locked ship state

* **Branch:** `phase-29` off `origin/main` (gated on Phase 28 squash-merge).
* **1 NEW source file** in `mindsos_capacity/`: `discovery.py`.
* **4 EDITED files** in `mindsos_capacity/`: `views.py`,
  `capacity_layer.py`, `exceptions.py`, `__init__.py`.
* **15 NEW test files** in `tests/phase_29/` totaling ~36 cases.
* **1 sentinel-paths addition** (`mindsos_capacity/discovery.py`).
* **12-site version bump** `+phase28 → +phase29`.
* **3 ADR amendments** in parent tree (Model C): 0069 §Impl, 0086 §Impl,
  0070 closure footer.
* **Docs:** mkdocs.yml nav phase-tag bump (no new page).
* **PHASE_MAP §29** edited per R1 PB-19 (3 row edits at ship).

## §4 §am-impl footers — reconciliations of obsoleted/revised picks

* **R1 PB-12 (hard vs soft delete in rediscover) → OBSOLETED at R4 probe 5.**
  Probe confirmed `Graph.remove_edge` is hard-delete (no tombstone
  accumulation). `_drop_auto_edges` uses it as-is; no compact-verb
  carry-forward needed.
* **R1 PB-14 (MetaEdge removal: private poke vs public) → OBSOLETED at R4 probe 4.**
  Probe confirmed `Metagraph.remove_metaedge` is a public method
  (exists since Phase 05a). `_drop_auto_edges` calls the public method;
  no Phase 30+ carry-forward "add public method" needed.
* **R2 PB-22 (MetaEdgeType registration) → REDUCED at R4 probe 2.**
  Probe confirmed `Metagraph.schema is None` at Phase 28 — MetaEdge
  add bypasses MetaEdgeType validation. No bootstrap edit needed.
  Reduced to a sentinel test
  (`test_metagraph_schema_is_none_at_phase_29.py`) locking the
  precondition for any future phase that may attach a MetagraphSchema.
* **R4 PB-35 (`successors_of` deprecated filter, pick (c)) → REVERSED to (a) at R5 PB-37.**
  Asymmetric vs Phase 28's `iter_capacities` no-filter posture;
  parent-verbatim wins. `include_deprecated` discipline becomes
  carry-forward item 9.
* **R4 PB-36 (`_drop_auto_edges` filter, pick (a)) → REVERSED to (a-parent) at R5 PB-38.**
  Aligned with R5 PB-37 reversal; filter only on
  `discovered_automatically=True`, no `deprecated_at` check.

## §5 Carry-forwards (to Phase 30+) — final 9-item list

1. `docs/usage/capacity/building.md` substantive content — Phase 30
   (alongside CLI + invoke).
2. `mindsos capacity` CLI Typer group — Phase 30 (invoke anchor).
3. ADR-0086 admin-deleted-auto-edge resolution — first reported foot-gun.
4. Pipeline finder + invocation + `InvocationResult` / `call_capacity`
   + `ProblemTraceRecord` — Phase 30 (flips Phase 28 sentinels).
5. Residents + text builtins + pathfinding — Phase 31.
6. Write capacities + symmetric contract + per-flow validators —
   Phases 33-35.
7. Additional-graph membership API per ADR-0085 — first concrete consumer.
8. Bulk rediscover verb (across all metagraphs) — first admin caller.
9. `include_deprecated` parameter discipline across L3 walks —
   Phase 30+ when soft-delete becomes a real L4 concern (R5 PB-37
   reversal toward parent fidelity).

## §6 Hotfix ledger

Pre-impl prediction (R3 PB-30 → R4 PB-32 reduced):

* **B-29-T1** (reserved contingency slot — no hypothesised class
  survives R4 probes).

Any B-29-T* will be appended at confirm-phase ship time per
`[[feedback-batch-fix-dont-iterate]]`.

## §7 Memory edits at ship

* NEW `[[project-mindsos-phase-29]]`.
* UPDATE `[[project-mindsos-phase-28]]` carry-forwards — close items
  1 (TYPE_COMPAT discovery) + 2 (`SuccessorHop` + walks) + 3
  (`building.md` deferred further to Phase 30).
* UPDATE `MEMORY.md` index with the new Phase 29 entry.

Implementation log + ship checklist: `notes-phase-29.md`.
