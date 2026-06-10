# Phase 50 — Confirmation

> Hand-assembled from the green cumulative gate (per the env invariant the
> `confirm-phase` tool is absent on the gate host and would re-run the 32-min
> suite; this phase reuses the gate already run on the squashed tree). CI's
> smoke check verifies "exists and non-empty".

---

## phase_number

50

## phase_title

SA-1 — skill-bundle install lifecycle (ADR-0183) + ADR-0182 node-value
serialization implementation + `installed-skills` role-graph (ADR-0150 §am-6;
closed set 13) + `mindsos skill` CLI + reference bundle

## git_sha

00d69a8

## image_build_hash

unknown (image not built locally — run `docker compose build`)

## falkordb_version

falkordb/falkordb:v4.18.3@sha256:30c530c193ac48cb6ea8c6cae745f793d2c098a0a138f7b3e46c1d90848845ba

## automated_test_summary

- count: 3982
- passed: 3970
- skipped: 11
- failed: 0
- xpassed: 1
- pytest_summary: 3970 passed, 11 skipped, 1 xpassed, 109 warnings in 1942.40s (0:32:22)

## tester_notes

Phase 50 (SA-1) is the **first downstream phase** after the completed
Phases 39–49 plan — the single ship slot of
`SKILL_ACQUISITION_PROCESS_PHASE_MAP.md` (design settled 2026-06-09; this
chat ran R0 impl-locks only). Two PRs on `phase-50` off `main` `5177e34`;
record `PHASE_50_DESIGN_LOG.md`.

Shipped (by surface):

- **ADR-0182 implementation (L0).** `mindsos_core/persistence/value_codec.py`
  (`encode_node_value` / `decode_node_value`; canonical JSON per the
  `_encode_props_json` discipline; `PersistenceError` on non-encodable —
  rule 4) + the `_value_json` SET branch in `build_unwind_create_nodes` +
  the `graph_repository` row split + the `graph_loader` decode +
  reserved-key adds in `_CORE_KEYS` and `RESERVED_PROPERTY_KEYS`. The
  MAINTENANCE M3 sentinel (`tests/maintenance/test_adr_0182_sentinel.py`)
  is **deleted**, replaced by behavior coverage
  (`tests/phase_50/test_adr_0182_value_codec.py`, 32 tests) + a
  structured-value case in the L0-25 live round-trip test.
- **`installed-skills` role-graph** (ADR-0150 §am-6; closed role-set
  **12 → 13**): `Discipline.APPEND_ONLY`, Global-only, single
  `SkillInstallRecord` NodeType (STORAGE_MODE_FIELDS `value` → inline);
  IRI builder/minter/parser; bootstrap rosters
  (`_GLOBAL_NAMED_ROLES` / `_APPLIES_AFTER_BY_ROLE` / `_GLOBAL_ROLE_ORDER`);
  ~13 corpus roster-pin updates (PR1 gate caught the last 4 in
  py3.10-uncollectable modules — single root cause, commit 1b).
- **Capabilities + audit** (Phase-44 S8 additive pattern):
  `CAN_INSTALL_SKILL` + `CAN_UNINSTALL_SKILL` (ADMIN_CAPS 10 → 12);
  `EVT_SKILL_INSTALLED` / `EVT_SKILL_UNINSTALLED` /
  `EVT_SKILL_INSTALL_REJECTED`. Latent Phase-44 drift fixed:
  `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` appended to `ALL_AUDIT_EVENTS`.
- **Install lifecycle (ADR-0183; `mindsos_server/skills/`).** TOML manifest
  parser + SHA-256 digest; collect-all preflight (`PreflightReport`: tier /
  phase / requires_bundles / closed-role / L3-IRI-collision-with-ownership-
  waiver / realm checks); install driver (S7 ordering; every write through
  the ADR-0180 `make_writeable` gate — no install-specific write path;
  append-only action records; ADR-0182 first production consumer); S8
  idempotency triple (same-digest no-op, digest-mismatch reject, upgrade
  reject, failed-run repair); de-install (reverse-dependency refuse +
  **marker-only deprecation** + record flip + audit; no deregistration);
  `apply_installed_skills(cl, kl)` free-function activation;
  `mindsos skill install / uninstall / list / activate` CLI (session-less
  Global-only per the capacity-CLI precedent; Falkor-backed with
  `--persist`).
- **Reference bundle** `tests/fixtures/skill_bundle_ref/` (test-fixture
  package, NOT builtins): 1 DataState (`text.ref_shouted`) + 1
  CapacityContext-native capacity (`text.ref_shout`) + 3 L2 content nodes.
  `tests/phase_50/test_skill_install_driver.py` exercises the pass
  criterion verbatim — install / de-install / provenance / idempotency
  ONLY (install → no-op reinstall → de-install → re-install →
  fresh-process activation; NOT "installed skill runs" — Phase 49 PB-1a is
  WSD's). `test_skill_record_falkor_live.py` proves durable provenance:
  the record's structured `value` survives a live persist → load
  round-trip through `_value_json`.
- **10-surface version bump 49→50** (8 `__version__` + pyproject +
  manifest `phase`+`version` + docker-compose tags + export-slate pins).

Grounding-driven findings (full list `PHASE_50_DESIGN_LOG.md` §2/§4):

- **G1 (refinement to design-log R2-1).** "Node-level deprecation already
  exists" was falsified at file level — the cited filter is the ADR-0133
  *edge* filter; `deprecate_version` is a docstring phantom; no read path
  filters deprecated nodes. v1 de-install stamps `deprecated_at` via
  direct system write (`retire_version` precedent) — **visible-but-marked**;
  node-level read-filtering added to the phase-map §3 v2 ledger.
- **I4/I5 — bundle-author rules (binding on WSD):** L2 content properties
  must avoid `RESERVED_PROPERTY_KEYS` (`label` is reserved); schema
  **type membership** is enforced even at strict=False — content must use
  the target role's declared NodeTypes.
- **I6:** S4's same-bundle ownership waiver is load-bearing — S11 ships no
  deregistration, so in-process reinstall-after-uninstall would
  self-collide on its own L3 IRIs without it. Reinstall by the owning
  bundle re-claims its tagged L2 nodes (clears the G1 marker) — also
  subsumes the failed-run repair branch.
- **I1 (process):** a Cowork-sandbox `git stash` left a stale
  `.git/index.lock` that blocked the Mac commit — pair-execution
  discipline (no sandbox git mutations) re-confirmed the hard way.

Scope discipline: nothing pulled forward from the §3 v2-trigger ledger (no
bundle-shipped code, Local installs, upgrade path, hard delete, rich L4
slots, or dispatch work).

Gate: PR1 cumulative 3928/4(roster pins)/11 + commit 1b targeted re-gate
89/0; PR2 full cumulative **3970 passed / 11 skipped / 0 failed /
1 xpassed** (the standing L0-25 orphan-scan xfail, xpassed since the
MAINTENANCE gate) on the Linux docker gate (32:22).

**Next chat = WSD_INSTALLATION_CHAT** (`projects/wsd/FUTURE_CHAT_PROMPT.md`,
banner updated; inheritance contract `SKILL_ACQUISITION_PROCESS_PHASE_MAP.md
§5`). DWF parallelizable (L2-only).

## timestamp_utc

2026-06-10T00:00:00Z

## mkdocs_pages_updated

- docs/decisions/adr/0183-skill-bundle-install-lifecycle.md (new)
- docs/decisions/adr/0150-l2-knowledge-lifecycle.md (§amendment-6)
