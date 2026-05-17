# Phase 11 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

The phase title as it appears in `confirmation_docs/PHASE_MAP.md` §3 / §4 / §5.
Example: `Tooling infrastructure`

L1 Loader policy + schema migration scanner (ADR-0134)

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

══════════════════════════════════════════════════════════════════════
Phase 11 — L1 Loader policy + schema migration scanner (ADR-0134).
SHIPPED 2026-05-16.
══════════════════════════════════════════════════════════════════════

## Headline numbers

* Phase 11 isolated suite: 118 collected — 4 skipped in container
  (test_adr_0134_amendments.py — ADR file lives in parent dir,
  not COPYd into runtime image; pytest.skip per design).
* Cumulative: ~1780 collected (1662 Phase 10 baseline + 118 Phase 11)
  / 0 failed inside the test image.
* Step-0 audit predicted 0 prior-phase cascade; impl confirmed:
  zero prior-phase test patches needed. Cleanest pre-impl audit of
  any phase to date. See PHASE_11_DESIGN_LOG.md §3.
* 3-package version parity: mindsos_core / mindsos_cli /
  mindsos_instances all at 0.0.0+phase11; manifest.toml
  [mindsos] phase = "11"; image tags mindsos:phase11-{prod,test}.

## What landed (mapped to PB-1..17 + 4 step-list PBs)

* mindsos_core/schema/migration.py (~310 LoC) — migrate_from(old,
  target, *, new, detail, old_schema_name). Detection-only per PB-1 A.
  Per-Graph + per-Metagraph dispatch per PB-17 C. Schema-level
  coverage only (NodeType + EdgeType + HyperEdgeType) per PB-7 C;
  MetagraphSchema scanner deferred to Phase 12+. 5 violation kinds.
  summary / each detail modes per PB-8 A.
* mindsos_core/reconstruction/load_report.py (~140 LoC) — LoadReport
  + MetagraphLoadReport. PB-9 B — drop count on report, NOT on Graph.
  No state-file bump.
* Loader policy plumbing (graph_loader.py + metagraph_loader.py).
  Additive sibling pattern per PB-12 B + PB-13 A — existing
  load_graph / load_metagraph / MetagraphLoader.load signatures
  UNCHANGED. New: load_graph_with_report, load_metagraph_with_report,
  MetagraphLoader.load_with_report. Per-call kwarg + env var
  MINDSOS_UNKNOWN_EDGE_POLICY (PB-14 A). Default warn.
  Per-distinct-type WARN with counts per PB-10 A (ADR-0134
  §amendment-1). No-op when no schema attached per PB-11. Policy on
  loader call surface, NOT FalkorConfig (ADR-0134 §amendment-2
  corrects original ADR mis-placement).
* UnknownEdgeTypeError in mindsos_core/exceptions.py.
  SchemaMigrationError raised by scanner on bad input.
* CLI — `mindsos schema migrate-check` with --graph G | --metagraph M
  mutex, --old <name> | --old-file <path> mutex, --new <name> opt-in,
  --detail summary|each, --json, --exit-zero. Exit 1 on violations
  default (PB-15). `mindsos persistence load --unknown-edges=...`
  surfaces drop count in Rich + JSON output paths.
* ADRs — ADR-0134 §Revisions amendments-1 + 2 added. Stays Proposed
  per PB-5 A; flips Accepted Phase 12+ when KL consumer lands.
  ADR-0021/22/23/0123 untouched (already Accepted).
* PHASE_MAP §Phase 11 row rewritten per PB-1+3+12+16. Risks marked
  OBSOLETE per detection-only lock.

## Hotfix ledger (B-11-T*)

* B-11-T1 — ModuleNotFoundError 'tomli' at collection time for
  tests/phase_11/test_doctor_phase11.py. Python 3.12 test image
  ships tomllib in stdlib. Fix: try/except tomllib → tomli fallback
  (same pattern as mindsos_core/config.py). One commit; CI re-ran
  green.
* B-11-T2 — Smoke-test surfaced false-negative scan. CLI helper
  _load_migrate_check_target read e['id']/n['id'] but state-file
  serializer writes 'edge_id'/'node_id'. Test fixture
  _write_minimal_graph_state used the same wrong keys, masking the
  defect. Two-file fix: helper uses correct keys; fixture corrected;
  added explicit edge-level regression test
  (test_graph_mode_edge_level_violation_surfaces_b_11_t2). Smoke
  re-run produced expected violation_count=1.

No other hotfixes.

## Manual smoke verification

* Smoke 1 — mindsos schema migrate-check --help (verb registered).
* Smoke 2 — mindsos persistence load --help (--unknown-edges flag
  registered).
* Smoke 3 — end-to-end migrate-check against temp v1tmp/v2tmp/
  smoketmp. After B-11-T2 fix, correctly produced removed_edge_type
  violation with count=1 and exit_code=1. --exit-zero flipped exit
  to 0 as designed (PB-15).

## Carry-forward (out of scope)

* Apply-style migration (Phase 14+ when first cross-layer consumer
  needs it).
* MetagraphSchema scanner (MetaEdge / IntergraphEdge / etc. types) —
  Phase 12+.
* Versioned schemas with named migrations — Phase 12+.
* Schema.diff(old) helper — defer until doc-generator consumer
  exists.
* `mindsos persistence verify --repair` flag (ADR-0123 v2) —
  Phase 14+.
* cypher-build debug CLI — killed per PB-3; no carry-forward.
* ADR-0134 §amendment-3 — reserved for first KL consumer's
  structural feedback.

## Cross-chat dependencies

### Closed (Phase 10 → Phase 11)

* phase-10-confirmed tag was the Phase 11 branch point.
* All Phase 10 surfaces (MetagraphSnapshot, RemovalImpact,
  soft-delete) unmutated; Phase 11 builds adjacent.

### Forward (Phase 11 → Phase 12+)

* L2 (KL): consumer for migrate_from output drives ADR-0134
  Proposed → Accepted flip.
* L2 (KL): if first KL hardening bumps MetagraphSchema, requires
  MetagraphSchema scanner.
* docs/dev/migration-playbook.md ships as stub; full content owed
  when first cross-layer consumer arrives.
