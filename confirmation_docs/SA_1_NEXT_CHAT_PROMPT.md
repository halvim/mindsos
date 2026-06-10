# SA-1 (Phase 50) — Ship-Chat Seed

> Authored 2026-06-09 at SKILL_ACQUISITION_PROCESS_CHAT closure. You are the **Phase 50 ship chat** — the first slot of `confirmation_docs/SKILL_ACQUISITION_PROCESS_PHASE_MAP.md`. Design is CLOSED; you start at R0 impl-locks, not design re-litigation (re-open a pick only on a grounding-driven reversal, with evidence — Phases 39–49 precedent).

## Read first

1. `confirmation_docs/SKILL_ACQUISITION_PROCESS_DESIGN_LOG.md` — the contract (S1–S13 + R2 refinements). Canonical.
2. `confirmation_docs/SKILL_ACQUISITION_PROCESS_PHASE_MAP.md` — your slot row (§2) + the v2-trigger ledger (§3) you must not pull forward.
3. `docs/decisions/adr/0182-node-value-serialization-contract.md` — you implement it; its §Consequences enumerates your L0 surface. The sentinel `tests/maintenance/test_adr_0182_sentinel.py` pins "no implementation shipped" — replace it with round-trip coverage.
4. `HANDOFF.md` §9 — pair-execution, gate-host discipline (separate checkout: confirm HEAD sha + `ls tests/phase_50`), docker rebuild, `python3`, 6-step confirm-phase, squash-before-confirm, tag at confirm commit.
5. Precedent files for your patterns: `mindsos_capacity/builtins/dream.py` (idempotent installer), `mindsos_server/capabilities.py` + `audit.py` (Phase-44 S8 additive pattern), `mindsos_knowledge/schemas/learned_parameters.py` + `bootstrap.py` (role-graph schema + `applies_after`).

## Scope (from the phase-map row; do not inflate)

- **ADR-0183** (skill-bundle + install-lifecycle contract) + **ADR-0150 §am-6** (`installed-skills`; closed set 12→13) — drafted at your R0.
- **ADR-0182 implementation:** `build_unwind_create_nodes` structured-value branch (`_value_json`) + node-loader decode + reserved-key roster + extend the L0-25 live test with a structured-value round-trip.
- `installed-skills` schema + bootstrap importer (Global-only; append-only action records per R2-2).
- `CAN_INSTALL_SKILL` / `CAN_UNINSTALL_SKILL`; `EVT_SKILL_INSTALLED` / `EVT_SKILL_UNINSTALLED` / `EVT_SKILL_INSTALL_REJECTED`.
- Manifest parser (TOML) + preflight (S4 roster) + install driver + `apply_installed_skills(cl)` free function + CLI activation flag + de-install (S11 as amended by R2-1: deprecate, don't delete).
- Trivial reference bundle in a **test-fixture package** (NOT `mindsos_capacity/builtins/`): 1 DataState + 1 CapacityContext-native `text.*` capacity + ~3 L2 content nodes. Install → verify → de-install → re-install.

**Pass criterion (verbatim, R0-SA-2):** validates install / de-install / provenance / idempotency ONLY. NOT "installed skill runs" — no dispatch work (Phase 49 PB-1a is WSD's).

## Version/ceremony

Phase 50 > high-water 49 → **10-surface bump 49→50** (8 `__version__` + pyproject + manifest `phase`+`version` + docker-compose tags + export-slate). Tag `phase-50-confirmed` at the confirm commit. Henrique may veto the Phase-50 numbering at R0 (design log R2-4) — ask before branching.

## Known impl-time items (tracked, not design-open)

Record-walk cost of append-only records (flip to mutable-status only with evidence); exact preflight error-report shape; deprecate-tag interaction with `include_deprecated` walks; where the CLI flag lives (`mindsos_cli/commands/` roster probe first).
