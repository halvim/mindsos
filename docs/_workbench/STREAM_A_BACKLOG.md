# Stream A — Backlog Index

**Purpose.** In-repo mini-index of bug-fix-shaped maintenance PRs flowing out of band of the Phase 39-49 Stream B sequence. Each item ships as a PR to `main` with no `phase-N-confirmed` tag, no `mindsos confirm-phase` invocation, no version bump.

**Convention.** One line per item. Owner = the chat or contributor responsible. Slot = when in the Stream B timeline this item can/should land. Status = pending | in_progress | landed.

**Inherits from.** `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §5` (Stream A scope definition). `confirmation_docs/PHASE_38_DESIGN_LOG.md §4` (origin of items #1, #6, #7, #8, #9).

---

## Pre-Phase-39 prerequisites (MUST land before Phase 39 branches off main)

| # | Item | Origin | Owner | Status |
|---|---|---|---|---|
| A1 | **`release.yml` retention amendment** — clarify in workflow comments that retention selection ranks by `[mindsos] phase` integer parsed from tag name, NOT by tag creation time (PB-R). Audit confirmed `select_retention` already parsed by phase integer (line 134 sorts by `(phase, letter)` tuple); A1 made the rule explicit in `release.yml` header + retention-step comments + added acknowledgment line in `mindsos confirm-phase` text-mode output. | Chat C plan-authoring PB-R | Maintenance | landed |
| A9 | **`tests_server/integration/test_layer_isolation.py` alignment with ADR-0010 §am-1** — remove `mindsos_admin` from `_DOMAIN_PACKAGES` (reclassified Phase 24 ship 2026-05-22 as server-side curation toolkit per Round 0 PB-Z22); add `mindsos_capacity` per Phase 27 forward-reference catch-up. Docstring + tuple + comment updates. Sibling test `tests/phase_15a/test_import_isolation_phase15a.py` already aligned at Phase 24; this one was missed. Surfaced at A0 §4 cumulative gate 2026-06-02. Verified: 3429 passed / 8 skipped / 0 failed cumulative gate; landed in commit `fe1c0d8`. | A0 §4 cumulative gate (post-A0-4) | Maintenance | landed |

---

## Interleaved with Stream B (land any time)

| # | Item | Origin | Slot | Owner | Status |
|---|---|---|---|---|---|
| A2 | **`mindsos capacity invoke --session-token` CLI flag** — hybrid auto-detect `~/.mindsos/token` + explicit override. ~10 LOC + 4 failure-mode test cases. Ships symmetrically with FalkorDBLocalPersister (Phase 44). | PHASE_38 §4 #1 (Phase 30 PB-30(a); Phase 38 R3-PB-B revert) | Pre-Phase-44 ideal; can pair with Phase 44 if absorbed | Maintenance or Phase 44 chat | pending |
| A3 | **Per-user Local-scoped `ProblemTraceSink` dict** — was L4-pointing since Phase 28 R2 PB-29(a); may absorb into Phase 44 R0 (Local-write substrate). | PHASE_38 §4 #6 | Pre-Phase-44 or Phase 44 absorb | Maintenance or Phase 44 chat | pending |
| A4 | **`--install-builtins=<family,...>` CLI flag on `capacity invoke`** — waits for second builtins family to ship (Phase 45 dream family, or WSD installation `predicate.*` etc.). | PHASE_38 §4 #7 (Phase 32+; "when a second builtins family ships") | Post-Phase-45 ideal | Maintenance | pending |
| A5 | **`handle.validate_xref` body** — wires per ADR-0139 §amendment-1 clause 3 alongside first XRef-writing L3 capacity. | PHASE_38 §4 #8 | Triggered by first XRef-writing capacity (likely WSD installation) | Maintenance or WSD installation chat | pending |
| A6 | **1 remaining unconsumed L2 validator: `validate_local_to_global_ref`** — three of four originally-unconsumed validators have consumers now (per L2_FUTURE_WORK L2-10); this one remains. First per-flow consumer likely lands at Phase 44 (Local-write substrate); validator may absorb there. | PHASE_38 §4 #9 (subset; 3 of 4 absorbed) | Pre-Phase-44 or Phase 44 absorb | Maintenance or Phase 44 chat | pending |
| A7 | **`concepts/promotion-bridge.md` Phase 24 §6 amendment verification + backfill** — flagged at Phase 38 as appearing unapplied. | PHASE_38 §4 #17 | Any time | Maintenance | pending |
| A8 | **`mindsos_instances` missing from `[mindsos] packages` list in `mindsos_cli/manifest.toml`** — package exists on disk but doctor parity loop won't iterate over it. One-line addition. Surfaced by Phase 43 pre-R0 probe R0a-8 (2026-06-02). | Phase 43 pre-R0 R0a-8 / N-now-E | Any time pre-Phase-44 | Maintenance | pending |

---

## Items that LEFT Stream A (routed to other phases)

The following items appeared in early Stream A drafts but moved out per Chat C R-round refinements:

- **PHASE_38 §4 #2 (Falkor-backed L3 bootstrap + state-file serialization)** — moved to Phase 44 (L0 substrate ~80-120 LOC; not bug-fix-shape). Per R3 PB-U.
- **PHASE_38 §4 #3 (FalkorDBLocalPersister)** — moved to Phase 44 (L0 substrate ~200-400 LOC + Cypher contracts + ADR). Per R3 PB-U.
- **L2-35 alignment shipped-code reconciliation** (`identifiers.py:303` body + docstring + Phase 36 test) — moved to Phase 39 scope (bundled with rename PR; saves one merge + one tester pass). Per R6 IL-7.

## Items that were RETIRED from any backlog

- **PHASE_38 §4 #4 (`add_type_compat` admin API + bulk rediscover verb)** — retired per ADR-0156 supersession of ADR-0086 (L1/L3 reframe chat 2026-06-01).
- **PHASE_38 §4 #5 (`include_deprecated` parameter discipline)** — folded into ADR-0156 scope (Phase 42 X3 ship).
- **PHASE_38 §4 #15 (PHASE_MAP §5 row appendices in parent tree)** — dropped; parent tree archived to `_archive_Layered_Intelligence/`; forensic-only.
- **PHASE_38 §4 #16 (`usage/knowledge/memories.md` §6 drift)** — resolved implicitly by Phase 39 rename (page renamed or deleted).
- **PHASE_38 §4 #18 (`notes-phase-NN.md` per-phase parity)** — ongoing convention discipline, not a backlog item.
- **PHASE_38 §4 #19 (CHANGELOG `last_design_only_phase` convention)** — ongoing convention discipline, not a backlog item.

---

*Live index. Update on each item's status change. Drop closed items after one tester confirms landing on `main`.*
