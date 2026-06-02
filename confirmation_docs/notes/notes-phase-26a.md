# Phase 26a — implementation notes

Phase: 26a
Phase title: FalkorDB persistence wiring (Integration A substrate)
Branch: `phase-26a` (cut from `origin/main` HEAD = Phase 25 squash `94c747d`)
Date: 2026-05-23
Design log: `confirmation_docs/PHASE_26a_DESIGN_LOG.md`
Tag at ship: `phase-26a-confirmed`

## §1 Scope shipped

* **`mindsos_core/persistence/bootstrap.py`** — `DEFAULT_INDEXES` gains 19th entry `("node", "Metagraph", "name")` per ADR-0123 §am1.
* **`mindsos_core/reconstruction/metagraph_loader.py`** — NEW method `MetagraphLoader.find_by_name(name: str) -> str | None`. O(1) lookup backed by the new index.
* **`mindsos_server/persistence/bootstrap.py`** — NEW module. `bootstrap_kl_from_falkordb(client: Client) -> KnowledgeLayer` load-or-mint wrapper per R4-PB-1 (b) + R5-PB-4 (a) + R6-PB-2 (b).
* **`mindsos_server/persistence/__init__.py`** — re-exports `bootstrap_kl_from_falkordb` alongside `LocalPersister` + `InMemoryLocalPersister`.
* **`mindsos_admin/promotion.py`** — `propose_for_promotion` signature gains positional `client: Client` second-arg. New `_PROPOSE_MERGE_CYPHER` constant + per-item Cypher MERGE write per ADR-0118 §am3 corrected template (metagraph_id+graph_id+node_id keys).
* **`mindsos_server/release.py`** — `release_update` + `_release_update_locked` signatures gain positional `client`. `_copy_role_pending_to_canonical` gains `client` kwarg + `_RELEASE_MERGE_CYPHER` per-role copy MERGE per §am3.
* **`mindsos_admin/audit_gate.py`** — `run` signature gains positional `client: Client` second-arg. TYPE_CHECKING import for forward symmetry; reads pending in-memory per Phase 24 PB-Z11(a) (no Cypher read at v1).
* **`mindsos_cli/commands/server.py`** — NEW `_resolve_client()` CLI helper (per-CLI fresh `FalkorClient`; caller closes per Phase 07 P4 A). `_resolve_kl()` now accepts optional `client` and calls `bootstrap_kl_from_falkordb` when provided. Propose-for-promotion + release-ship verbs open + close client around the call.
* **`mindsos_cli/commands/admin.py`** — `_run_single_importer` wires `MetagraphRepository.persist(mg)` after importer mutates the metagraph; opens + closes Client per Phase 07 P4 A. Module docstring updated to close the Phase 14a round-3 lock deferral.
* **3 ADR amendments** — ADR-0118 §am3 (NEW; wiring + corrected Cypher + concurrency caveats); ADR-0010 §am2 (NEW; admin → core ALLOWED); ADR-0123 §am1 (NEW; Metagraph.name index).
* **8-site version bump** `+phase25 → +phase26a` (pyproject + 6 pkg __init__ + manifest.toml).
* **7 test files** at `tests/phase_26a/`: __init__, conftest, test_default_indexes_19, test_metagraph_loader_find_by_name, test_bootstrap_kl_from_falkordb, test_import_isolation_phase26a, test_signatures_client_kwarg, test_e2e_persist_smoke.
* **2 phase-baseline literal-decay updates** — `tests/phase_07/test_bootstrap.py` (18 → 19; node-count 15 → 16); `tests/phase_09/test_indexes_phase09.py` (18 → 19).
* **0 schema bumps** (`_SCHEMA_VERSION` stays at 4).
* **0 new audit events** (importer audit emission deferred per R1-PB-6 (a) probe-and-pin).

## §2 Design-log §am-impl addendum — Round 7 picks reconciled

R7 pre-impl probe surfaced 4 literal-level findings (no structural reversals; R6 saturation held):

| # | Pick | Finding | Impl reconciliation |
|---|---|---|---|
| R7-F1 | persist is MERGE-idempotent everywhere | builders.py lines 62/83/100/155/267/343 all `MERGE` not `CREATE` | bootstrap_kl_from_falkordb simplified — re-persist after partial load is safe; no "first bootstrap?" flag |
| R7-F2 | exception handling inconsistent in persist() | `_safe_run` wraps anchor only; lines 153/174/195/228 raw `_client.run_query` | wrapper catches `PersistenceError` only at v1; raw driver exceptions surface unchanged; documented as known gap |
| R7-F3 | ImporterProtocol has `target_roles` not `target_metagraph_id` | importers/__init__.py:13 | CLI envelope (`_run_single_importer`) owns Metagraph; importer mutates; CLI persists |
| R7-F4 | Importers don't emit audit | grep admin.py + importers/ → only docstring `audit` mentions | step 4 audit-table expectation pinned to "no audit row" per R1-PB-6 (a) |
| B-26a-T3 §am-impl | Client kwarg optional-with-default | Phase 24 tests fail with `missing positional argument` if `client` is strict-required | Relax to `Optional[Client] = None`; guard Cypher writes on `if client is not None`. Matches Phase 25 `hard_delete_user(persister: LocalPersister \| None = None)` precedent. Phase 26a CLI verbs still pass live Client explicitly; Phase 24 tests omit it and exercise SQLite + in-memory path only. R5-PB-3 (a) "per-CLI fresh client" still holds for the live-client case. |

Plus one no-op:

* ADR-0125 stays Proposed (Phase 26a wires Global to FalkorDB; per-user Local lazy-hydration still defers to first user-Local-write phase).

## §3 Smoke results

Host-native syntax check (`python3 -m py_compile`): **TODO [Linux]** — sandbox-side Python 3.10 missing `datetime.UTC`; run on Linux host.

Host-native pytest on `tests/phase_26a/`: **TODO [Linux]** — `python3 -m pytest tests/phase_26a/ -v`.

Host-native pytest cumulative `tests/`: **TODO [Linux]**.

Docker pytest on `mindsos:phase26a-test`: **TODO [Linux]** — `docker compose --profile test build mindsos-test && docker compose run --rm mindsos-test pytest tests/phase_26a/ tests/`.

Manual smoke recipe (host-native per `feedback_smoke_harness_host_native.md`):

```bash
# 1. Bootstrap admin (writes server.db; no FalkorDB needed)
mindsos server bootstrap admin-caller
mindsos server login admin-caller

# 2. Import dolce (NOW persists to FalkorDB per Phase 26a)
mindsos admin import dolce --source /path/to/dolce.owl

# 3. Verify FalkorDB has the Global Metagraph anchor
# (against the configured FalkorDB; default localhost:6379 graph 'mindsos')
# Expected: one :Metagraph node with name=mindsos_global

# 4. Run propose + release end-to-end (exercises §am3 Cypher writes)
# Construct a small PromotionProposal JSON and use:
mindsos server release propose-for-promotion --proposal-json /path/to/proposal.json
mindsos server release ship

# 5. Verify canonical_global node landed in FalkorDB
```

## §4 Hotfix ledger

| ID | Symptom | Fix | Files | Notes |
|---|---|---|---|---|
| B-26a-T2 | `docker compose run --rm mindsos-test pytest tests/` failed 6 doctor/compose tests with `assert 'mindsos:phase26a-prod' in '... mindsos:phase25-prod ...'`. The 9-site version-bump checklist had a 10th site I missed: `docker-compose.yml` has 2 image-tag literals (`prod` + `test`). | `docker-compose.yml` lines 39, 69: `mindsos:phase25-{prod,test}` → `mindsos:phase26a-{prod,test}`. | `docker-compose.yml` | Memory `feedback_phase_baseline_literal_audit.md` extension — add `docker-compose.yml` to the version-bump checklist as 10th site for future phases. |
| B-26a-T3 | 32 Phase 24 tests failed `TypeError: propose_for_promotion() / release_update() missing 1 required positional argument: 'client'`. Phase 24 tests use SQLite + in-memory only; they don't care about FalkorDB; adding `InMemoryClient()` to satisfy a strict-required signature is mechanical noise. | Make `client` parameter optional with `Optional[Client] = None` default + guard Cypher writes on `if client is not None`. Matches Phase 25 `hard_delete_user(persister: LocalPersister \| None = None)` precedent — backward-compatible additive change; new behavior opt-in via passing live Client. Phase 26a tests still exercise wiring (smoke tests construct + pass `FalkorClient` explicitly). | `mindsos_admin/promotion.py`, `mindsos_server/release.py` (release_update + _release_update_locked + _copy_role_pending_to_canonical), `mindsos_admin/audit_gate.py` | Design log §1 R5-PB-3 (a) said "positional client second-arg"; B-26a-T3 relaxed to "positional client second-arg with None default + opt-in Cypher write." Documentary §am-impl below in §2. ADR-0118 §am3 text uses "positional" wording; reads correctly under both interpretations (positional ≠ required). |

## §5 Ship checklist progress

* [x] Phase 26a source written.
* [x] Phase 26a tests written.
* [x] Version bump 8 sites.
* [x] 3 ADR amendments appended.
* [x] notes-phase-26a.md at repo root (this file).
* [x] Phase 26a design log at `confirmation_docs/PHASE_26a_DESIGN_LOG.md`.
* [x] PHASE_MAP.md §26 retired + §26a + §26b rows added.
* [ ] Host-native tests GREEN (`tests/phase_26a/` then cumulative `tests/`). **[Linux]**
* [ ] Docker tests GREEN. **[Linux]**
* [ ] Manual smoke against FalkorDB. **[Linux]**
* [ ] `git status` review on Mac; `git add` everything.
* [ ] Open PR against `main` from `phase-26a`. **[Mac]**
* [ ] CI green (`release.yml`).
* [ ] Squash-merge PR. **[Mac]**
* [ ] `git tag phase-26a-confirmed <squash-sha>` + push. **[Mac]**
* [ ] CI re-runs against tag green.
* [ ] `mindsos confirm-phase --phase 26a --notes-file notes-phase-26a.md` generates `confirmation_docs/PHASE_26a_CONFIRMED.md`. **[Linux]**
* [ ] Commit + push the confirmation doc.

**Regex-tolerance verification needed at first test run** per Phase 26a R2-PB-4 (c): `tools/release.yml`, `mindsos confirm-phase --init-notes` parser, `_retention._TAG_RE`, doctor self-test, `printf '%0Nd'` consumers (per memory `feedback_tag_regex_audit.md` 6-site checklist + `feedback_workflow_bash_octal_trap.md`). The `26a` suffix scheme matches Phase 04-v2 + 05a-d precedent so existing patches probably suffice; verify and patch any literal `^[0-9]{2}$` regex.

## §6 Phase 26b carry-forwards (substrate-ready; CLI orchestration deferred)

### `_build_global_metagraphs(conn)` ephemeral-Metagraph gap (B-26a-T4 candidate; Phase 26b scope)

**Surfaced during Phase 26a host smoke.** The CLI helper
`mindsos_cli/commands/server.py:1613::_build_global_metagraphs(conn)` —
called by `release propose-for-promotion` (line 1711) + `release ship`
(line 1768) — builds **fresh in-memory Metagraphs** each CLI
invocation via `bootstrap_global(importers=()) → bootstrap_pending_
global(canonical_mg) → rehydrate_global_metagraphs(conn, ...)`. It
does NOT call `bootstrap_kl_from_falkordb`. Each invocation mints
brand-new random `metagraph_id` values for canonical + pending.

**Consequence at Phase 26a:** `release propose-for-promotion` CLI verb
calls succeed at the SQLite + in-memory layer; the §am3 Cypher MERGE
writes (lines 467-487 in `mindsos_admin/promotion.py`) land in
FalkorDB but keyed on ephemeral metagraph_ids that no subsequent
invocation references — effectively orphaned writes. Same gap for
`release ship`.

**Phase 26a release scope per design log R1-PB-1 (c):** "26a wires
persistence first; Phase 26b runs the integration scenario over the
wired substrate." The propose+release CLI orchestration is exactly
the Phase 26b sub-scenario per PHASE_MAP §26b step 7: "Propose ATOM
+ release ship sub-scenario — exercises Phase 24's propose/release
surface with Phase 26a wiring." Phase 26a ships the LOW-LEVEL
substrate; Phase 26b rewires `_build_global_metagraphs` to:

1. Replace `bootstrap_global(importers=())` with
   `bootstrap_kl_from_falkordb(client).global_metagraph()` so
   canonical has a STABLE metagraph_id across CLI invocations.
2. Add a parallel `bootstrap_pending_global_from_falkordb(client)`
   wrapper that find_by_name's a `pending_knowledge` Metagraph (or
   similar canonical name) and mints+persists on miss, symmetric
   with the Global path.
3. Plumb `client` through `_build_global_metagraphs(conn, client)`
   so the helper itself becomes Phase 26a-Client-aware.

**Smoke evidence for Phase 26a release-state:**

* `bootstrap_kl_from_falkordb` mint+load round-trip preserves
  `metagraph_id` (host smoke step 4 + step 6 returned same id
  `401ff013-...`).
* `MetagraphRepository.persist()` MERGE-idempotency confirmed via
  pytest E2E `test_repository_persist_is_idempotent_across_calls`.
* `MetagraphLoader.find_by_name` resolves correctly (both inline
  `{name: $name}` and WHERE-clause forms confirmed against live
  FalkorDB; step 5 diagnostic A+B both returned the matching row).
* ADR-0123 §am1 `Metagraph.name` index confirmed operational via
  `CALL db.indexes()` showing `Metagraph [id, name]`.

**Phase 26b should NOT treat this as a regression of Phase 26a.** It
is the integration-half of the split. Phase 26a substrate is healthy;
Phase 26b orchestration is the next phase's work.

### Other Phase 26b carry-forwards (from design log §6)

* Scripted scenario 8 steps locked at R1-PB-3 + R0 META-PB-5 +
  R1-PB-6 + R3-PB-2.
* Golden-output normalizer helper at `tests/phase_26b/_normalize.py`
  per R1-PB-4 (b).
* Per-step audit expectations table per R0 META-PB-3 (a) + R7-F4.
* Test-importer fixture at `tests/phase_26a/fixtures/_test_importer.py`
  (NEW per R3-PB-2 (c) — 10-row TSV; Phase 26a defers actual file
  creation to Phase 26b's scenario-build).
* PHASE_MAP §38 deferred-CLI-verb TODOs accumulate from 26b findings.

## §7 Implementation references

See `confirmation_docs/PHASE_26a_DESIGN_LOG.md` §5 for the canonical scope per R0-R7 picks; the §am-impl addendum above (§2) documents R7 probe-vs-pick reconciliations.

Key ADR cross-references:
* **ADR-0118 §am3** — wiring + corrected Cypher (metagraph_id+graph_id+node_id MERGE keys; supersedes §am2 per-FalkorDB-graph naming); §"Concurrency caveats" subsection.
* **ADR-0010 §am2** — admin → core ALLOWED row added to DAG table.
* **ADR-0123 §am1** — 19th DEFAULT_INDEXES entry rationale.
* **ADR-0043** — unchanged. KL stays in-memory; server owns I/O — "I/O" at Phase 26a now means real FalkorDB writes via `MetagraphRepository` orchestrated by server's `bootstrap_kl_from_falkordb` wrapper.
* **ADR-0121** — unchanged. FalkorDB substrate decision honored (R1-PB-2 (ii) "extend Phase 07 JSON state files" reversed at R2-PB-1 (a) after probe).
