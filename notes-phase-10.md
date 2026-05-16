# Phase 10 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

The phase title as it appears in `confirmation_docs/PHASE_MAP.md` §3 / §4 / §5.
Example: `Tooling infrastructure`

L1 Snapshot + soft-delete substrate + RemovalImpact + XRef setters

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

══════════════════════════════════════════════════════════════════════
Phase 10 — L1 Snapshot + soft-delete substrate + RemovalImpact +
XRef setters. SHIPPED 2026-05-16.
══════════════════════════════════════════════════════════════════════

## Headline numbers

* Phase 10 isolated suite: 162 passes (`tests/phase_10/`) — 145 unit +
  17 integration (14 non-diagnostic + 3 zzz-prefixed diagnostic).
* Cumulative: 1664 collected = 1662 passed / 0 failed / 2 skipped /
  109 warnings in 1057s (17m37s) inside the test image.
* Cumulative delta from Phase 09 (1503) = +162 isolated +
  prior-phase patch deltas (no count change from B-10-T3 patches,
  +6 from B-10-T7: -4 doc sentinels parametrised out, +2 module
  sentinels in, +8 prior failures fixed).
* 3-package version parity: mindsos_core / mindsos_cli /
  mindsos_instances all at 0.0.0+phase10; manifest.toml
  [mindsos] phase = "10"; image tags mindsos:phase10-{prod,test}.

## What landed (mapped to design locks M*/N*/RR*/RPB*/PB*)

* `MetagraphSnapshot.of(mg)` + `restore_into(mg)` at
  `mindsos_core/metagraph_snapshot.py` — slim-port from v3 baseline
  (4 strips + 2 additions per PB-1) + P84 allow-list expansion
  (_intergraph_edges + _intergraph_hyperedges + _schema_name + _schema)
  + P85 `_GraphSnap.properties` + P86 `_GraphSnap.soft_delete_dirty`.
  12-attribute Metagraph-side allow-list per M3. Identity-preserving
  restore via IdentityRegistry.clear() + register() (RF amend at port).
* `RemovalImpact` + `RemoveGraphBlockedError` + `BlockedReason` str-Enum
  per ADR-0135 amendments 1-3.
  `remove_graph(*, cascade=True, force=False) -> RemovalImpact`
  (P67 cascade restored + P75 unified exception + P81 cascade-vs-force
  independence).
* Soft-delete substrate (ADR-0133) — `deprecated_at` + `disputed_at`
  on Edge/HyperEdge/MetaEdge/MetaHyperEdge (M5); XRef restores
  `target_stale` + `deprecated_at` (P53 reversal). 20 setter methods
  (8 Graph + 8 Metagraph + 4 XRef per PX2). Iterator + loader filter
  pass (P68 merge of original P11 scope into Phase 10).
* 22 cypher builders (M16 PB-4a per-method): 16 edge-side + 4 XRef +
  2 impact-query. `_compute_removal_impact` uses in-memory
  `_xrefs_by_target` (PB-5a + ADR-0135 amendment-3).
* 10 WAL replayer kinds (M8 + RR-1): 4 collapsed element-side + 4 XRef
  + 2 Phase 09 carry. Wrapper grows 2 → 10 via
  `register_soft_delete_replayers` (new module
  `persistence/soft_delete.py` per RR-16a) + extended
  `register_xref_replayers` (2 → 6). P88: RR-1 payload schema extended
  with `scope_id` for collapsed element-side kinds.
* State-file v=4 → v=5 (M11): metagraph + graph; per-element
  soft-delete fields persist as ISO strings + bool; `_v4_to_v5`
  per-kind migrations idempotent (RR-7); serializer + deserializer
  paired (B-09-T4 symmetry); P64 mirror clears dirty on deserialize.
* `mindsos persistence xref-list` 8 → 10 fields (M24 + RR-6): JSON
  unconditional 10; Rich table grows columns only when non-default.
* ADRs (chunk-10 commit at project-root per RPB-7): 0027 §Revisions
  a-1; 0128 §Revisions a-3; 0130 Graph-side §Acceptance flip + P69
  caveat; 0133 Proposed → Accepted + D1-rev; 0135 Proposed →
  Accepted + 3 amendments per P77.

## Hotfix ledger (B-10-T1..T7 — ALL closed)

* B-10-T1 — 6 integration test failures: XRef tests need explicit
  `XRefLoader(client).load_into(mg)` after `MetagraphLoader.load`
  (Phase 09 idiom; after_load observer needs explicit
  `attach_xref_loader`). WAL recovery tests had raw-Cypher field-name
  typos.
* B-10-T2 — WAL recovery tests switched to `WriteAheadLog.begin()`
  direct API (Phase 09 test_xref_wal_recovery pattern). NEW 3
  diagnostic tests `test_zzz_diagnostic_xref_persist.py` (zzz-prefix
  forces last-run ordering) localise any future persist/load defect
  to a specific pipeline stage.
* B-10-T3 — 15 prior-phase tests asserted Phase-09-era literals
  (`CURRENT_VERSION == 4`, "no deprecated_at field" negative-shape,
  8-field XRef shape, v=5 forward-version refused). Patched 6 files
  to dynamic CURRENT_VERSION + inverted negative-shape asserts to
  positive (Phase 10 supersedes Phase 09 P53 strip).
  Audit class: feedback_phase_baseline_literal_audit.md.
* B-10-T4 — confirm-phase subprocess timeout bumped 900s → 1800s.
  Phase 10 cumulative crossed ~17m (1050s observed in manual run; the
  confirm-phase --build overhead pushed past 900s). Constant
  `_CONFIRM_PHASE_TIMEOUT_SECONDS` at confirm_phase.py.
  Bump history: 600s (P06) → 900s (P07 M12) → 1800s (P10 B-10-T4).
  Phase 11+ should monitor + bump again if needed.
* B-10-T5 — Dockerfile prod + test stages both add
  `COPY notes-phase-*.md ./` so docker invocation of
  `confirm-phase --notes-file ...` finds the file at /app. Phase 02-09
  worked only because tester ran host-native (pip install -e .); the
  docker invocation path needs the explicit COPY.
* B-10-T6 — confirm-phase `_PYTEST_SUMMARY_RE` widened to match BOTH
  framed `===== N passed =====` (pytest -v) AND bare `N passed, ...`
  (pytest -q). Parser had been silently emitting
  `pytest_summary: no pytest summary line found` and zeroing counts
  since Phase 09. NOT a regression — was masking real failures the
  whole time. Phase 09 + 10 prior CONFIRMED docs' zero-count rows
  were therefore parser-bug artefacts.
* B-10-T7 — 8 cumulative failures exposed by T6 regex fix, all closed:
  - 4 = phase-baseline literal audit re-strike. Three tests in
    `tests/phase_09/test_doctor_phase09.py` (asserting "09" /
    "0.0.0+phase09" / mindsos:phase09-prod) rewritten as manifest
    self-consistency (phase ↔ version ↔ compose tag, dynamic).
    `tests/phase_07/test_doctor_phase07.py::test_confirm_phase_timeout_is_900s`
    (`== 900` literal broken by B-10-T4 bump) patched to `>= 900`
    (floor, not exact) and renamed accordingly.
  - 4 = NEW audit class feedback_sentinel_paths_runtime_only.md.
    RPB-8 incorrectly added 4 mkdocs source paths
    (docs/concepts/soft-delete.md + docs/api/core/soft-delete.md +
    docs/api/core/metagraph-snapshot.md + docs/dev/internals/snapshots.md)
    to `tests/_shared/sentinel_paths.py`. Dockerfile does NOT COPY
    docs/ into either runtime stage. Removed the 4 doc entries; kept
    the 2 Python module entries (mindsos_core/metagraph_snapshot.py +
    mindsos_core/persistence/soft_delete.py) which ARE imported at
    CLI runtime.

## Three audit-class memories surfaced / extended this phase

* feedback_phase_baseline_literal_audit.md — extended with B-10-T7
  re-strike. Step 0 of any phase ship MUST grep ALL tests/ for
  phase-string / index-count / summary-shape / timeout-second literals,
  not just _state_version literals.
* feedback_confirm_phase_timeout.md — bump history captured (600 →
  900 → 1800); always pre-build the test image before confirm-phase.
* feedback_sentinel_paths_runtime_only.md (NEW). Never add docs/*.md
  to SENTINEL_PATHS — docs are mkdocs-build-time sources, not CLI
  runtime inputs. Rule: only add a sentinel entry if there is a
  matching Dockerfile COPY in BOTH prod + test stages.
* feedback_confirm_phase_file_paths.md — notes-phase-NN.md lives at
  REPO ROOT (Phase 02-09 precedent); PHASE_NN_CONFIRMED.md auto-
  generated into confirmation_docs/. Phase 10 mistake-class: I
  initially mis-instructed relocating notes under confirmation_docs/
  and conflating with the OUTPUT file. Both wrong; both fixed.

## Smoke tests (manual, in-container)

All PASS per design locks M3 / M5 / M8 / M11 / M24 / RR-1 / RR-6 /
RR-7 / RR-19 / RR-16a + ADR-0135 amendments 1-3. Boxes 01-08 cover
doctor self-test + 3-pkg version parity, xref-list 10-field JSON,
soft-delete setter quartet smoke, remove_graph matrix (cascade x force
matrix incl. P81 force-does-not-override-cascade-gate), WAL recovery
of soft-delete kinds, snapshot.restore_into identity preservation,
state-file v=4→v=5 round-trip, and 14-bucket cypher index presence.

## Cross-chat dependencies (CLOSED)

* Phase 09 P53 — XRef target_stale + deprecated_at RESTORED.
* Phase 09 RPB-3 — mark_xref_stale setter ships (firing trigger still
  deferred to Server first-start hook P18+).
* ADR-0130 Graph-side — Accepted via P69 snapshot-preservation-basis
  caveat.

## Carry-forward to Phase 11+ (out of Phase 10 scope)

* ADR-0128 stays Proposed until Phase 14 (MetagraphView.follow_ref
  consumer).
* ADR-0129 CI lint rule deferred to Phase 18+.
* Soft-delete CLI verbs deferred per P76.
* IntergraphEdge / IntergraphHyperEdge soft-delete deferred per P83.
* Server first-start `mark_xref_stale` auto-trigger deferred to
  Phase 18+ per O1.
* L3 capacities producing XRefs deferred to Phase 33+ per ADR-0145.

## In-flight pushbacks resolved during impl (P67-P88)

Pre-impl (P67-P78): cascade restore + filter merge + ADR-0130 caveat +
PA1 raise + probe-8 pre-verify + SoftDeleteKind enum + per-method
builder discipline + warning strip + unified exception + CLI defer +
ADR-0135 amendments + ADR-0133 flip + housekeeping bundle.

During impl (P79-P88): snapshot-pre-soft-delete-dirty-field ordering
(P79); iterator P80/P82 (Graph iterators ship); IntergraphEdge OUT of
M5 (P83); M3 allow-list expansion for halvim primitives (P84);
Graph.properties backfill (P85); Graph-side dirty split (P86); loader
full integration (P87); WAL payload schema scope_id extension (P88).

## Next action

Awaits squash-merge of phase-10 → main, then
`git tag phase-10-confirmed <main-sha>` per
feedback_release_workflow_ordering.md (tag MUST point at the main
commit containing this CONFIRMED doc, not the phase-10 branch tip).
══════════════════════════════════════════════════════════════════════
