You are the **MAINTENANCE_CHAT** for the MindsOS project.

CONTEXT: Phases 39–49 are ALL SHIPPED (tag `phase-49-confirmed`). Per the 2026-06-09 downstream-plan reanalysis (Cowork session with Henrique), the recommended downstream order was revised: **this chat opens FIRST**, before SKILL_ACQUISITION_PROCESS_CHAT, because two of its items are load-bearing for the skill-install contract. DWF_INSTALLATION_CHAT opens after you close (not fully parallel — single-tester gate serialization per `POST_PHASE_38_PHASE_MAP.md §1` + your M3 ADR amends the persister contract DWF would ingest against).

You are NOT a numbered phase. Ship as Stream-A-style maintenance commits on `main` (A0/A9 precedent, HANDOFF §3.1.10): per-item commits, cumulative gate before fast-forward, no 9-surface manifest bump unless you touch a bump surface (you should not).

SCOPE (5 items — resist expansion; anything bigger gets routed, not absorbed):

- **M1 — L0-24 import-cycle fix.** `mindsos_admin/promotion.py:68` top-level `from mindsos_server.admin import admin_tx` → lazy-import inside the consuming function(s) (codebase pattern `mindsos_core/persistence/client.py:140`); remove the `tests/phase_44/conftest.py` warm-up band-aid; re-run isolated subsets (`pytest tests/phase_44/`, `tests/phase_18`) + full cumulative gate. ~1–3 lines. Full diagnosis `PHASE_44_DESIGN_LOG.md §12`; item text `docs/_workbench/L0_FUTURE_WORK.md` L0-24.

- **M2 — L0-25 live-Falkor round-trip coverage.** `FalkorDBLocalPersister` save→load + scoped delete against a live FalkorDB (Phase 44 unit tests used `InMemoryClient` only). R0 decision: ship here vs re-route to WSD installation (L0_FUTURE_WORK marks both as acceptable). If the metaedge/metahyperedge/XRef delete-sweep completeness check balloons, ship the round-trip test only and route the sweep audit to WSD.

- **M3 — L0-26 decide-and-document ONLY (no implementation).** The node persister stores node `value` as a primitive (`cypher/builders.py::build_unwind_create_nodes`); structured values (L5 Episode 6-field dict, future install-provenance/bundle-manifest records) don't durably round-trip. Author the serialization-contract ADR now (options per L0-26: extend ADR-0130 `_props_json` to node level / decomposed primitive nodes / dedicated blob store) so SKILL_ACQUISITION designs against a fixed contract. **Implementation lands with its first consumer** — skill-acquisition phase-map slot 1 (trivial-bundle reference install) — per the consumer discipline that ran Phases 39–49 (Phase 44 CR-2, ADR-0181 decide-and-document precedent). Couples with the Phase-48-deferred durable checkpoint store; scope the ADR to the contract, not the store.

- **M4 — Routing record for the CapacityContext read-path migration (union-drop).** Phase 48 deferred it as "Phase 49 / WSD / v1.5"; Phase 49 shipped no feature surface; **no `L*_FUTURE_WORK.md` file carries it** (verified 2026-06-09 — grep "union", "read-path", "PB-23" across `docs/_workbench/` returns nothing). Add an L3_FUTURE_WORK item recording: contract authority = SKILL_ACQUISITION R0 (bundle capacity bodies are authored CapacityContext-native, never dict); mechanical corpus migration = WSD installation slot 1. Doc-only.

- **M5 — WSD/FOL ANALYSIS delta addendum.** `projects/wsd/ANALYSIS.md` + `projects/fol/ANALYSIS.md` are dated 2026-05-28 — pre-Phase-43-through-49 — and are the PRIMARY consumer inputs to SKILL_ACQUISITION. Author `projects/ANALYSIS_DELTA_2026-06.md` (do NOT rewrite the originals; addendum + banner pointer in each original). **Verify every claim against shipped code, not HANDOFF prose** (NPB11-META lesson, `PHASE_43_DESIGN_LOG.md §10.1` — one 2026-06-09 audit agent asserted the resident lifecycle still exists; grep showed Phase 41 removed it). Findings to verify + absorb:
  - WSD ANALYSIS §2: "L4/L5 nothing shipped" → Phases 46–48 shipped `mindsos_intelligence` + L5 v1. (VERIFIED)
  - `sense-correlations` "ship once for both" → withdrawn at Phase 43; regression guard `test_5_item_exclusion_regression_guard` forbids it. (VERIFIED)
  - `learned-parameters` WSD/FOL alignment → Phase 43 shipped single role-graph; FOL #4 3-way split deferred — NOT aligned at v1. (VERIFIED via schema docstring)
  - C-L3-2 monitor-lifecycle conflict listed open → resolved in WSD's favor by ADR-0155/Phase 41 (`start_resident`/`stop_resident` gone from `mindsos_capacity` — grep-verified 2026-06-09). The C-bin ledger needs a full re-pass: some conflicts are now resolved, some moot.
  - R0-PB-9 "ship both" claim in WSD ANALYSIS §4 → only `learned-parameters` shipped. (VERIFIED)
  - `InterGraphEdge` vs `IntergraphEdge` → still open; routed to SKILL_ACQUISITION R0 per HANDOFF §2.1. Note it; don't resolve it here.
  - Re-grep both ANALYSIS docs for: TYPE_COMPAT/discovery (retired Phase 42), `PlanRun` (renamed `PipelineRun`), `memories` (renamed), resident (renamed monitor). (UNVERIFIED counts — do the grep)

READ FIRST: `HANDOFF.md` §1, §3.1.19–3.1.22, §6, §9 (ship-env invariants: separate gate checkout — confirm HEAD sha; no `gh`/`mindsos` CLI on gate host; `python3`; BSD sed → perl); `docs/_workbench/L0_FUTURE_WORK.md` L0-24/25/26 verbatim; `PHASE_44_DESIGN_LOG.md §12`; `PHASE_49_DESIGN_LOG.md` PB-RT.

FIRST ACTIONS: prereq check (`git tag --list | grep phase-49-confirmed`; `main` at the Phase-49 confirm commit; never `git add -A`); open `confirmation_docs/MAINTENANCE_CHAT_LOG.md` with the 5-item slate; probe before locking M2's in-vs-out pick.

CLOSURE: update L0_FUTURE_WORK closure markers (L0-24 closed; L0-25 closed-or-routed; L0-26 → "ADR on disk, impl routed to skill-acquisition slot 1"); add the M4 item; commit the delta addendum; then hand off to `SKILL_ACQUISITION_PROCESS_NEXT_CHAT_PROMPT.md` (carries a 2026-06-09 amendment that depends on your M3 + M5 outputs).
