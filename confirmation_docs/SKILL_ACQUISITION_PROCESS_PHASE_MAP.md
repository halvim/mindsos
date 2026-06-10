# SKILL_ACQUISITION_PROCESS — Phase Map

**Authored:** 2026-06-09 at design closure (per PB-A: each downstream chat authors its own phase-map). Design authority: `SKILL_ACQUISITION_PROCESS_DESIGN_LOG.md` (S1–S13 + R2). This map does not restate the design — it sequences it.

---

## §1 — Settled contract (one-paragraph summary; log is canonical)

A **skill bundle** = versioned TOML manifest + data files; code arrives via normal MindsOS release; the manifest references installer entry points by import path (S1). Layer slots: L2 content + L3 DataStates/capacities/monitors + L4 opaque key-value fills; L1 and L5 slots empty at v1 (S2). Installs are **Global-only, admin-gated** (`CAN_INSTALL_SKILL`/`CAN_UNINSTALL_SKILL`; all writes via ADR-0180 `make_writeable`) (S3, S6). Lifecycle: preflight-atomic install (collision scan; abort whole bundle) → durable L2 content + install record → per-process activation via `apply_installed_skills(cl)` (CLI flag at v1) (S4, S7). Install state = append-only action records in the new Global **`installed-skills`** role-graph (ADR-0150 §am-6; first consumer of ADR-0182 `_value_json`) (S5, R2-2). Idempotency = builtins triple at artifact + bundle level; upgrades rejected at v1 (S8). De-install = reverse-dep refuse + **deprecate** bundle-tagged content + record flip + audit; no in-process deregistration (S11, R2-1). Bundle L3 bodies are CapacityContext-native, never dict (S9 = L3-59(a)). Promotion loop (`parameter-staging` → `pending-promotions` → `learned-parameters`) is a **second producer of the same artifacts** under the same contract; mechanism ships in WSD (S10).

## §2 — Slots

| Slot | Phase | Scope | Pass criteria | Gate |
|---|---|---|---|---|
| **SA-1** | **Phase 50** (tag `phase-50-confirmed`; 10-surface bump 49→50 per R2-4) | ADR-0183 + ADR-0150 §am-6; **ADR-0182 implementation** (`build_unwind_create_nodes` structured-value branch + loader decode + reserved-key roster + replace `tests/maintenance/test_adr_0182_sentinel.py` with round-trip coverage); `installed-skills` schema + bootstrap importer (+`applies_after`); `CAN_INSTALL_SKILL`/`CAN_UNINSTALL_SKILL` + `EVT_SKILL_INSTALLED`/`EVT_SKILL_UNINSTALLED`/`EVT_SKILL_INSTALL_REJECTED` (Phase-44 S8 pattern); manifest parser + preflight + install driver + `apply_installed_skills` + de-install; trivial reference bundle (1 DataState + 1 CapacityContext-native `text.*` capacity in a test-fixture package + ~3 L2 content nodes) installed/de-installed/re-installed end-to-end. | **Narrow per R0-SA-2:** validates install / de-install / provenance / idempotency ONLY. Does NOT validate "installed skill runs" (v0 lifecycle dispatches no real capacity — Phase 49 PB-1a); no dispatch work. Cumulative pytest green on the Linux gate (HANDOFF §9 discipline: confirm gate-box HEAD + `ls tests/phase_50`). | Standard pair-execution + 6-step confirm-phase. |

One ship slot only. Everything else this chat touched is either closure doc-edits (no gate) or WSD-owned.

## §3 — Deferred / v2-trigger ledger

| Item | Trigger | Owner |
|---|---|---|
| Full plugin (bundle-shipped code) | First skill whose code cannot ship in a MindsOS release | Future chat; requires sandbox (L0-5, WSD-routed) first |
| Local-tier skill installs | First per-user-skill consumer | Future chat |
| Bundle upgrade path (vN → vN+1 in place) | First real skill revision (likely WSD v1.x) | WSD or maintenance |
| Hard delete of de-installed content | Storage pressure or admin need | Maintenance (`CAN_HARD_DELETE_ARCHIVED` precedent) |
| Rich (non-opaque) L4 manifest slots | WSD installation forces the real shape | WSD_INSTALLATION_CHAT |
| Dangling capacity-IRI references in old episodes after de-install | Observed in practice | v1.5 retention work |
| Promotion-loop mechanism (writers/consumers of `parameter-staging`/`pending-promotions`) | WSD ALS ships | **WSD_INSTALLATION_CHAT** (contract: design log S10) |

## §4 — Routing amendments landed at this closure

1. `POST_PHASE_38_PHASE_MAP.md` §6 — promotion-loop ownership note added to the WSD row (closes the R0-SA-1 routing gap).
2. HANDOFF §2.1 + §5.3 — `IntergraphEdge` naming marked closed (L1-6, ratified here).
3. `L3_FUTURE_WORK.md` L3-59(a) — closed (contract = design log S9).
4. L0-26 — unchanged (already routes impl to this map's SA-1).

## §5 — WSD inheritance contract (what WSD_INSTALLATION_CHAT consumes from here)

1. WSD ships as **release + bundle**: role-graphs (`world-axioms`), schemas, importers, capacity bodies = release code (own ADRs, incl. ADR-0150 §am for any role-set expansion); content + registrations + L4 fills = bundle(s) through the SA-1 driver.
2. All WSD capacity bodies CapacityContext-native (S9); WSD slot 1 also does the mechanical corpus migration + union-drop (L3-59(b)).
3. WSD replaces the v0 `planning.*`/`phase1`/`orchestration` catalogs atomically (q4) and defines the real L4 manifest slot shapes (supersedes S2's opaque slots by ADR amendment).
4. Promotion-loop mechanism ships in WSD under the S10 producer-agnostic contract (same tiers/audit/provenance/preflight).
5. Absorbed L0 admin-surface items (PB-T roster) remain WSD-side — the SA-1 driver does not pre-build them.

*End of SKILL_ACQUISITION_PROCESS_PHASE_MAP.md.*
