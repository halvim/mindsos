# PHASE 50 (SA-1) — Design Log

**Status:** ship chat opened 2026-06-10 off `main` `5177e34`
(post-closure-bookkeeping; design CLOSED at SKILL_ACQUISITION_PROCESS_CHAT
2026-06-09 — this log records impl-locks + grounding-driven refinements
only, per the Phases 39-49 precedent).
**Scope authority:** `SA_1_NEXT_CHAT_PROMPT.md` (seed) +
`SKILL_ACQUISITION_PROCESS_DESIGN_LOG.md` (contract) +
`SKILL_ACQUISITION_PROCESS_PHASE_MAP.md §2` (pass criterion) + ADR-0182
§Consequences (L0 surface).

---

## §1 — R0 decisions (Henrique, 2026-06-10)

| # | Decision | Pick |
|---|---|---|
| R0-1 | Phase-50 numbering + 10-surface bump 49→50 (R2-4 veto reserved) | **Confirmed** |
| R0-2 | PR split | **2 PRs as seeded** — PR1: ADR-0182 impl + `installed-skills` substrate + caps/audit + ADRs; PR2: manifest/preflight/driver/activation/CLI/reference bundle + bump. Seam real: PR2 strictly consumes PR1; PR1 independently gateable (sentinel→round-trip). |
| R0-3 | 5 uncommitted closure-bookkeeping files on `main` | **Committed to `main` first** (`5177e34`), then `phase-50` branched. |
| R0-4 (G1) | De-install deprecation mechanism | **Marker-only** — see §2. |

## §2 — G1: grounding correction to design-log R2-1 (refinement, not reversal)

R2-1 claimed node-level deprecation "already exists (`deprecated_at` +
ADR-0133 `include_deprecated` filter, `metagraph_view.py:213-282`)".
File-level reality: that citation is the **edge** filter; `deprecate_*`
APIs exist for the edge family only (`graph.py:612/652`,
`metagraph.py:2375/2417/2495`); `deprecate_version` is a docstring
phantom (named in `knowledge_layer.py:461`, defined nowhere); **no
shipped read path filters deprecated nodes**. What does exist:
`deprecated_at` is a reserved node-property key (`validation.py`), the
promotion validator reads it (`validators.py:287`), and `retire_version`
(`knowledge_layer.py:470`) is the direct-system-write precedent.

**Resolution:** v1 de-install stamps `deprecated_at` on bundle-tagged
nodes via direct system write — **visible-but-marked**. Node-level
`include_deprecated` read-filtering added to the v2-trigger ledger
(phase-map §3 gains a row at closure). "Deprecate, don't delete"
survives; R2-1's visibility claim doesn't. Reflected in ADR-0183 §8.

## §3 — Impl-locks (PB-50-*)

- **PB-50-1 driver home:** `mindsos_server/skills/` subpackage —
  `manifest.py` / `preflight.py` / `records.py` / `driver.py` /
  `activation.py`. Driver needs session-caps + audit (server) + KL
  writes + L3 entry points; ADR-0010 forbids domain→server imports, so
  server-side. All writes through ADR-0180 `make_writeable` (no
  install-specific write path; S6 honored literally).
- **PB-50-2 preflight shape:** `PreflightReport` dataclass
  (per-finding `code` + `message`; collect-all, not fail-fast);
  `SkillInstallRejectedError(report, reasons)`; reasons embedded in the
  `EVT_SKILL_INSTALL_REJECTED` payload.
- **PB-50-3 CLI:** new `mindsos skill` sub-app (`commands/skill.py`):
  `install` / `uninstall` / `list` / `activate`. Session-less,
  Global-only per the Phase 30-31 capacity-CLI precedent (ADR-0080
  carve-out; no `--session-token` — standing PB-30(a) carry-forward).
  `skill activate` is the PB-4 activation caller (verb, not a flag on
  `capacity invoke` — discoverability; same fresh-layer semantics).
  Falkor-backed when reachable (`--persist` flushes, `admin import`
  precedent); in-memory fallback otherwise.
- **PB-50-4 record IRI:** `installed-skills-v1:record:<bundle>:<version>:<seq>`
  via `skill_install_record_iri` + `(role, "SkillInstallRecord")` minter
  dispatch; `seq` = max(existing)+1 over the record walk (R2-2 cost
  note tracked, not hit at v1 scale).
- **ADR-0182 codec home:** `mindsos_core/persistence/value_codec.py` —
  `encode_node_value` / `decode_node_value` shared by
  `graph_repository` (rows) + `graph_loader` (decode); reconstruction
  already imports `persistence.client`, so import-legal. Canonical
  encode matches `_encode_props_json` discipline.
- **StorageMode:** record NodeType declares
  `STORAGE_MODE_FIELDS = {SkillInstallRecord: {"value"}}`, tier INLINE
  (learned-parameters NPB8-1 precedent); oversize fails loud at the
  ADR-0182 rule-4 boundary — correct v1 behavior.
- **L4 slots:** carried in the record `value` only (S2 opaque-slot
  contract; no L4 registry write surface exists to target).
- **`requires_mindsos_phase` source:** parsed from the
  `+phaseNN` suffix of `mindsos_server.__version__`
  (`current_mindsos_phase()`); injectable for tests.

## §4 — Impl-time grounding findings (I-*)

- **I1 (process).** A Cowork-sandbox `git stash` experiment left a
  stale zero-byte `.git/index.lock` the sandbox could not remove,
  blocking the Mac PR1 commit until manually cleared. Lesson re-learned
  the hard way: **no git mutations from the Cowork sandbox, ever** —
  pair-execution discipline exists for this exact reason (HANDOFF §9).
- **I2 (latent drift fix).** `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY`
  was declared at Phase 44 but never appended to `ALL_AUDIT_EVENTS`
  (violating the tuple's "new events append" contract). Appended at
  Phase 50 alongside the 3 new events; pinned by
  `test_phase_44_event_drift_fixed`.
- **I3 (gate).** PR1 cumulative gate: 4 failures, single root cause —
  roster pins living in modules the py3.10 sandbox could not collect
  (CLI roles list ×2, `_IRI_BUILDERS` registry ×2). Fixed in PR1
  commit 1b; targeted re-gate 89/89. Gate-driven follow-up budget: 1
  commit (within the Phase-43 §10.5 envelope).
- **I4 (bundle-author rule).** L2 content properties must avoid
  `RESERVED_PROPERTY_KEYS` — the reference bundle's `label` prop was
  rejected by `validate_user_properties`; renamed `description`.
  Recorded for WSD bundle authoring.
- **I5 (bundle-author rule).** Schema **type membership** is enforced
  even at `strict=False` (`strict` governs property shapes only) —
  bundle content must use the target role's declared NodeTypes
  (reference bundle: `Frame` in `concepts`, `TaskPattern` in
  `task-patterns`). Recorded for WSD bundle authoring.
- **I6 (S4 ownership waiver).** S4's "collision **not owned by a prior
  version of the same bundle**" clause is load-bearing: S11 ships no
  deregistration, so an in-process reinstall-after-uninstall
  self-collides on its own L3 IRIs. Preflight waives collisions for
  IRIs present in ANY prior record of the same bundle (roster union
  over the record walk).
- **I7 (G1 symmetry).** Reinstall by the owning bundle **re-claims**
  its tagged L2 nodes by clearing `deprecated_at` (direct system
  write) — the inverse of the uninstall stamp; also subsumes the S8
  failed-run repair branch (owned partials no-op).
- **I8 (bug caught at smoke).** Activation originally filtered records
  with an object-identity check across two record walks (`is` on
  freshly-built dataclass views) — silently activated nothing. Fixed to
  seq-sorted latest views; pinned by the activation tests.
- **I9 (env).** Sandbox Python is 3.10 vs repo ≥3.12 (`datetime.UTC`):
  server-importing corpus cannot be smoked in-sandbox; smokes ran under
  a test-runner-side `datetime.UTC` shim; the docker gate (py3.12) is
  canonical. Recurs every phase — noted for future ship chats.
- **I10 (post-confirm manual smoke, 2026-06-10).** Installer entry
  points must be importable in the **consumer's process** — the
  `mindsos` console script does not put `/app` on `sys.path`, so the
  reference bundle's `tests.fixtures...` entry point needs
  `PYTHONPATH=/app` when driven via the in-container CLI (real bundles
  reference release-shipped `mindsos_*` modules, always importable —
  R2-3 unaffected). The failed first attempt also confirmed atomicity:
  the exception aborted before `--persist`, leaving the live Global
  untouched. The full live CLI lifecycle then ran green across five
  separate processes (install/persist seq-1 → fresh-process list →
  activate → uninstall/persist seq-2 → fresh-process list) — the
  durable ADR-0182 provenance round-trip, manually confirmed.

## §5 — Scope discipline

Nothing pulled forward from the phase-map §3 v2-trigger ledger (no
bundle-shipped code, no Local installs, no upgrade path, no hard
delete, no rich L4 slots, no dispatch work). Pass criterion exercised
verbatim: install / de-install / provenance / idempotency — the
end-to-end reference-bundle cycle (install → no-op reinstall →
de-install → re-install → fresh-process activation) lives in
`tests/phase_50/test_skill_install_driver.py`; durable provenance via
the live Falkor round-trip (`test_skill_record_falkor_live.py` — the
ADR-0182 first-consumer proof); ADR-0182 sentinel replaced by
behavior coverage (`test_adr_0182_value_codec.py` + the L0-25 live
extension).

## §6 — Version bump

10-surface bump 49→50 (slot 50 > high-water 49 per Phase-40 PB-2):
8 × `__version__` + `pyproject.toml` + `mindsos_cli/manifest.toml`
(`phase` + `version`) + `docker-compose.yml` image tags + the 3
export-slate `__version__` pins (phase_30/31/34).

## §7 — Gate record

- PR1 gate (cumulative, Linux docker, 2026-06-10): 3928 passed /
  4 failed (I3 roster pins) / 11 skipped / 1 xpassed (pre-existing
  L0-25 orphan-scan xfail, also xpassed at the MAINTENANCE gate).
- PR1 commit 1b targeted re-gate: 89 passed / 0 failed.
- PR2 gate (cumulative, Linux docker, 2026-06-10): **3970 passed /
  11 skipped / 0 failed / 1 xpassed** (the standing L0-25 orphan-scan
  xfail). Zero gate-driven follow-up commits on PR2.
