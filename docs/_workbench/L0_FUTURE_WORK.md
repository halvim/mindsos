# L0 Server — Future Discussions & Work

**Date:** 2026-05-31 (updated post Chat B closure)
**Status:** Living index. Append as new items surface. Each item names the source and the owner chat (which future chat resolves it).

---

## 1. Phase 38 carry-forwards (L0-bucket)

| # | Item | Source | Owner chat |
|---|---|---|---|
| L0-1 | **`FalkorDBLocalPersister`** — load-bearing per Phase 38 R3-PB-A; `mindsos_server/persistence/local_persister.py:57-58` documents deferral | PHASE_38_DESIGN_LOG §4 #3 | Chat C plan-authoring; ships as Phase 39 candidate |
| L0-2 | `SQLiteLocalPersister` — pairs with L0-1 | Same | Same |
| L0-3 | `mindsos capacity invoke --session-token` CLI flag — Phase 30 PB-30(a) deferred | PHASE_38_DESIGN_LOG §4 #1; confirmed by probe `mindsos_cli/commands/capacity.py:30-31` | Chat C; bundled with L0-1/L0-2 |

---

## 2. WSD-driven additions

| # | Item | Source | Owner chat |
|---|---|---|---|
| L0-4 | **`user_settings` table** for ALS training prefs — read by L4 at start of every dream cycle; minimal user UI | WSD `coordinated_change_L0_user_settings.md` | Chat A (decides v1/v2); WSD installation chat (ships) |
| L0-5 | Capacity sandbox (per-capacity I/O extraction, reproducibility) | WSD `pending_adrs/L0_server.md` §A | WSD installation chat |
| L0-6 | Admin promotion machinery extension for ALS Global cycle aggregation | WSD §4.5 — cross-user aggregation runs in L0 admin tools, not in per-session L4 | Chat A (resolve location); WSD installation chat (ship) |
| L0-7 | Audit gate extension for ALS promotion (versioned `learned-parameters` writes) | WSD §4.4-§4.5 | WSD installation chat |

---

## 3. FOL-driven additions

| # | Item | Source | Owner chat |
|---|---|---|---|
| L0-8 | **External blob store + IRI manifest pattern** for model artefacts (S3/MinIO + content-addressed hashes) | FOL pushback #8 (High severity) | Chat A (decides v1 scope); FOL installation chat (ships) |
| L0-9 | Concurrency model decision (single-process / multi-process / distributed) — affects auth/session lifecycle, prover backend invocation, write semantics | FOL pushback #12 (High severity; "must-decide-soon") | Chat A R1 (resolve) |

---

## 4. Server-pivot v2 carry-forwards

| # | Item | Source | Owner chat |
|---|---|---|---|
| L0-10 | ~~Note-fork mechanism~~ — **RETIRED 2026-05-31 by Chat B D-B1.** L5 ships with D'1 (version-IRI freeze + pin-at-instantiation + lazy inline-on-retire) instead; no L0 note-fork mechanism needed v1 or v2 (unless a new consumer surfaces). | Closed |
| L0-11 | Cross-layer rewrite handler for L4 v2 — when alice's draft is promoted, rewrites refs in KL + Capacity; L4 process-state refs to drafts won't be rewritten until L4 ships its handler | L4 handoff §11 (2026-04-26); R0-PB-10 | Chat A (confirm v1 single-tenant); L4-v2 follow-up chat (ship) |
| L0-12 | **L0 admin-tooling library export for Global ALS cycle** — per Chat A R3 D9.4: Global aggregation runs in L0 admin tools (no Global L4). Ship the subsystem-walker + per-subsystem aggregate flow as a library that admin tools import. | Chat A R3 D9.4 | L0 chat + WSD installation |
| L0-13 | **Capacity-gaps admin tooling polished for v1** — under R3 open task-type space, this is a primary admin surface; UI/API for occurrence-counting, prioritization, "mark out-of-scope", "link to existing pattern", PII anonymization considered. | Chat A R3 + R4 D16 | WSD installation |
| L0-14 | **HITL clarification channel + interactive-mode detection** — system asks user for clarification when mapping_confidence is LOW; session declares `interactive=True/False` at start; L0 routes. | Chat A R3 + R4 routing | L0 chat |
| L0-15 | **New audit event constants** — `EVT_PIPELINE_QUARANTINED`, `EVT_PIPELINE_DELETED`, `EVT_TASK_PATTERN_AUTHORED`, `EVT_HINT_EXTRACTOR_FAILED`, `EVT_ALS_APPLY_APPROVED`, etc. Phase 21 audit substrate amendment. | Chat A R3 | L0 chat + WSD installation |
| L0-16 | **Hint catalog admin tooling** — similar to capacity-gaps queue surface; admin reviews + curates hint capacities + lifecycle (active / deprecated / retired). | Chat A R3 hint system | L0 chat + WSD installation |
| L0-17 | **Simplified-execution-mode CLI flag** (`mindsos capacity invoke --bypass-lifecycle`) — admin testing path; bypasses Phase 1/2/4/5 + ALS signals + consolidation. | Chat A R4 D12 | Maintenance chat or WSD installation |
| L0-18 | **L0 scheduler infrastructure (v1 must-have)** — default Global ALS cycle cadence (weekly off-hours); admin-tunable + manual trigger. Originally v2; reclassified v1 per R3 PB-R3-33 pick B. | Chat A R3 PB-R3-33 | L0 chat |
| L0-19 | **Admin config field for Global dream priorities** — per R4 D18 + PB-R4-14: per-user priorities in L0 user_settings; admin Global defaults in L0 admin config; audit-log tracks changes. | Chat A R4 D18 + PB-R4-14 | L0 chat |
| L0-20 | **L0 query API on audit log for L3 capacities** — enables `retrieval.by_admin_decision_similarity` (L3-48) to read precedent data. Read-only structured query. v2 may promote to dedicated L2 `admin-decisions` role-graph if load-bearing. | Chat A R5 PB-R5-10 | L0 chat + WSD installation |
| L0-21 | **New KL public API: `kl.read_at_version(iri, version)`** — version-pinned read against Phase 11 side-by-side graphs. Required by L3 fallback reads under D'1 (Chat B D-B14 PB-A' rule-3) + by episode resolution (D'1 retention). | Chat B D-B14 + D-B16 | L0/KL chat |
| L0-22 | **New KL operation hook: `kl.retire_version()`** — fires lazy-inline marker consulted on episode read (Chat B D-B2 PB-J.a). Distinct from `kl.deprecate_version()` flagging (deprecated content stays readable side-by-side; only retire actually releases KL-held content). | Chat B D-B2 | L0/KL chat |
| L0-23 | **`capacity-gaps` queue extended with `promotion-candidates` sub-queue** — dream-found promotion candidates surfaced to admin via L0-13 surface; admin verdicts feed audit log (authoritative) + Memory.`rejected_promotions` (denormalized index). | Chat B D-B47 (PB-WW) + cascade to L0-13 | L0 chat + WSD installation |

---

## 5. Open coordination questions

| # | Question | Source |
|---|---|---|
| L0-Q1 | Where does ALS Global cycle aggregation run if L4 is per-user-session and there's no Global L4? Implicit: in admin tools (L0). Make explicit in Chat A. | CHAT_A_L4_BASELINE PB-E |
| L0-Q2 | Audit gate semantics under multi-process concurrency (if L0-9 picks B/C) — concurrent writes to `pending-promotions` across processes | L0-9 cascade |

---

## 6. Chat C closure routing (2026-06-02)

Chat C plan-authoring closed 2026-06-02 (`confirmation_docs/POST_PHASE_38_PHASE_MAP.md`). Routing of open L0 items:

| Item | Routed to | Notes |
|---|---|---|
| L0-1 (`FalkorDBLocalPersister`) | **Phase 44** via L0_SUBSTRATE_CHAT | Rail C ship. |
| L0-2 (`SQLiteLocalPersister`) | **Phase 44** via L0_SUBSTRATE_CHAT | Rail C ship; pairs with L0-1. |
| L0-3 (`--session-token` CLI flag) | **Stream A (item A2)** or Phase 44 absorb | Per `_workbench/STREAM_A_BACKLOG.md`. |
| L0-4 (`user_settings` table for ALS) | **WSD_INSTALLATION_CHAT** | Per PB-T (admin-surface absorb into WSD). |
| L0-5 (capacity sandbox) | **WSD_INSTALLATION_CHAT** | Per PB-T. |
| L0-6 (Global ALS cycle library) | **WSD_INSTALLATION_CHAT** | Per PB-T. |
| L0-7 (audit gate ALS extension) | **WSD_INSTALLATION_CHAT** | Per PB-T. |
| L0-8 (external blob store) | **FOL_INSTALLATION_CHAT** | FOL pushback #8. |
| L0-9 (concurrency model) | **RESOLVED Chat A R1 D32** | Single-process multi-threaded. |
| L0-10 (note-fork) | **RETIRED** (Chat B D-B1 2026-05-31). | — |
| L0-11 (cross-layer rewrite handler) | **L4-v2 follow-up chat** | Opens after Phase 49 confirmed. |
| L0-12 (Global ALS cycle library export) | **WSD_INSTALLATION_CHAT** | Per PB-T. |
| L0-13 (capacity-gaps admin tooling) | **WSD_INSTALLATION_CHAT** | Per PB-T. |
| L0-14 (HITL clarification channel) | **WSD_INSTALLATION_CHAT** | Per PB-T (consumer is L4 Phase 1 step 5b + WSD task-pattern authoring). |
| L0-15 (audit event constants for ALS/promotion) | **WSD_INSTALLATION_CHAT** | Per PB-T. |
| L0-16 (hint catalog admin tooling) | **WSD_INSTALLATION_CHAT** | Per PB-T. |
| L0-17 (`--bypass-lifecycle` CLI flag) | **MAINTENANCE_CHAT** | Per PB-T routing exception. |
| L0-18 (L0 scheduler infrastructure) | **WSD_INSTALLATION_CHAT** | Per PB-T. |
| L0-19 (admin config for Global dream priorities) | **WSD_INSTALLATION_CHAT** | Per PB-T. |
| L0-20 (audit-log query API for L3) | **WSD_INSTALLATION_CHAT** | Per PB-T (consumer is `retrieval.by_admin_decision_similarity`). |
| L0-21 (`kl.read_at_version`) | **Phase 44** via L0_SUBSTRATE_CHAT | Rail C. |
| L0-22 (`kl.retire_version`) | **Phase 44** via L0_SUBSTRATE_CHAT | Rail C. |
| L0-23 (capacity-gaps `promotion-candidates` sub-queue) | **WSD_INSTALLATION_CHAT** | Per PB-T. |
| L0-Q1 | Resolved via PB-T (admin-tools home in WSD installation chat scope). | — |
| L0-Q2 | Closed — L0-9 resolved as single-process multi-threaded; multi-process v2. | — |

**No separate L0_ADMIN_SURFACE_CHAT** — per PB-T, admin-surface items absorb into WSD installation chat (design-with-consumer).

---

---

## 7. Maintenance carry-forwards (surfaced Phase 44)

| # | Item | Source | Owner chat |
|---|---|---|---|
| L0-24 | **Pre-existing import cycle `admin ↔ persistence ↔ mindsos_admin`.** `mindsos_admin/promotion.py:68` top-level `from mindsos_server.admin import admin_tx` is reached while `admin.py` is mid-init on a cold `mindsos_server` import → `ImportError: cannot import name 'admin_tx'`. Masked in the full suite by server-phase conftest import-order warming; bites isolated subsets (`pytest tests/phase_44/`, `pytest tests/phase_18`). **Fix:** lazy-import `admin_tx` inside the consuming function(s) in `promotion.py` (codebase pattern — `mindsos_core/persistence/client.py:140`); then remove the `tests/phase_44/conftest.py` warm-up band-aid; re-run full cumulative gate. ~1-3 lines, behavior-preserving. Full diagnosis: `PHASE_44_DESIGN_LOG.md §12`. | Phase 44 (surfaced, not introduced — pre-existing) | **MAINTENANCE_CHAT** |
| L0-25 | **FalkorDBLocalPersister live-FalkorDB integration test + scoped-delete coverage.** Phase 44 unit tests use `InMemoryClient` (no real round-trip); the save→load round-trip + the scoped `metagraph_id`-keyed delete Cypher are unvalidated against a live FalkorDB. Also: the delete's metaedge/metahyperedge/XRef sweep is a best-effort first cut needing completeness verification. Per `PHASE_44_DESIGN_LOG.md §7`. | Phase 44 (PR1.2) | **MAINTENANCE_CHAT** or WSD installation |

---

*End of L0_FUTURE_WORK.md.*
