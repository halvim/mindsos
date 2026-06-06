# Phase 41 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

The phase title as it appears in `confirmation_docs/PHASE_MAP.md` §3 / §4 / §5.
Example: `Tooling infrastructure`

L3 — X2: Monitor lifecycle retirement from L3 (ADR-0155)

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

Rail B slot 2 (L3 reframe X2). Impl of settled design (L1_L3_REFRAME §D36, saturated R3; ADR-0155 already Accepted on disk — no Proposed→Accepted flip). Hard-break retirement: Phase 31 resident infrastructure removed.

Shipped (production — SURGICAL removals, NOT whole-module deletes):
- capacity_layer.py: removed start_resident / stop_resident / active_subscriptions methods + the _subscriptions field; added iter_monitors() -> List[Monitor] (filters the shared IRI-keyed _declarations; Local-wins inherited).
- runtime.py: removed ResidentSubscription dataclass (kept Phase-30 invoke / ProblemTraceSink / ProblemTraceRecord); dropped now-unused Monitor/Callable/Dict/ResidentError imports.
- exceptions.py: removed ResidentError (kept the other 7 classes).
- identifiers.py: KIND_RESIDENT("resident") -> KIND_MONITOR("monitor") + NODE_KINDS; capacity.py Monitor.node_kind follows. node_kind triad now REACTIVE/MONITOR/ADAPTER.
- __init__ exports 114 -> 112 (-ResidentSubscription, -ResidentError, -KIND_RESIDENT, +KIND_MONITOR).

Tests: 9 Phase-31 resident test files deleted whole; tests/phase_31/_fixtures.py PRUNED to its text-builtin helpers (NOT deleted — shared by 5 surviving text tests); tests/phase_27 node_kind rename; export-slate 114->112 across phase_29/31/33/34 + membership flipped present->absent in phase_31/phase_33 (sentinel-flip convention). 4 new tests/phase_41/ (resident_infrastructure_retired, iter_monitors, kind_monitor_rename, adr_amendment_sentinels).

Docs: ADR-0073 (+ §amendment-1) flipped to Superseded; ADR-0155 §Implementation (2026-06-05, Phase 41) marker appended; glossary "Resident" entry + summary/capacity.md ADR-0073 row + dev/internals/capacity.md prose annotated.

Scope decisions / deviations from PHASE_MAP §4 row (full record: PHASE_41_DESIGN_LOG.md):
- IPB-1: PHASE_MAP "Phase 31 module deletes whole (~6-8 files)" undercounts. Actual = 9 whole-deletes; production retirement was surgical (runtime/exceptions/capacity_layer host Phase-30 occupants), not whole-module. Deleting whole would have destroyed invoke()/ProblemTraceSink + 7 exceptions.
- IPB-2: _fixtures.py is shared by 5 text tests -> pruned, not deleted.
- IPB-4: PHASE_MAP "Modules touched"/"confirms" lists docs/concepts/monitors.md, which DOES NOT EXIST (phantom). Doc amendment redirected to glossary/summary/internals.
- IPB-3: HANDOFF §3.1 was already amended by Chat C (line 118 carries iter_monitors + retirement note) — nothing to finalize.
- IPB-5: CHANGELOG stops at Phase 38 (39/40/43/44 added no entry); Phase 41 follows suit — no CHANGELOG line, for consistency.
- PB-2: PHASE_MAP grep-zero pass criterion is unsatisfiable repo-wide (ADR-0155 itself + superseded ADR-0073 + sentinel test legitimately contain the strings). Retirement sentinel scoped to the shipped package: importability assertion + grep over mindsos_capacity/**/*.py (excl. sentinel). User-confirmed PB-2.
- PB-4: KIND_RESIDENT->KIND_MONITOR is a VALUE change ("resident"->"monitor"), not just a symbol rename. node_kind migration is empty at v1 (no persisted Monitor instances).
- PB-6: ADR-0073 -> Superseded by ADR-0155 (user-confirmed).
- PB-7: iter_monitors has no v1 consumer — L4 MonitorSubscriptionRegistry + the cl.iter_monitors() consumer ship Phase 46. Acceptable per Stream-B DAG (mirrors Phase 40 family_rules ahead of its consumer).
- PB-8: no version bump (slot 41 <= high-water 44); CONFIRMED.md records the phase44 image. Manifest untouched.

S2 lesson applied (Phase 40 §10): export-slate membership consumers (phase_31/phase_33 asserted ResidentSubscription/ResidentError present) + the shared _fixtures.py were swept at R0 BEFORE the gate — no Phase-40-style gate-1 cascade. Full hard-break blast radius grepped across mindsos_*/tests/docs at R0.

Cumulative gate: 3660 passed / 8 skipped / 0 failed (Linux docker). 8 skips pre-existing (no live FalkorDB sidecar for integration tests).

Next: Rail B continues with Phase 42 (X3 — bipartite topology + capacity registration contract v2 + Phase 27 dont-know audit, which also reconciles the PB-8 FAMILY_RULES vocabulary routed from Phase 40). L4 substrate (Phase 46) implements MonitorSubscriptionRegistry + consumes cl.iter_monitors().
