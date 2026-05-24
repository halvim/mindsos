# Phase 26b — implementation notes

Phase: 26b
Phase title: Integration A end-to-end scripted scenario + B-26a-T4 closure
Branch: `phase-26b` (cut from `origin/main` HEAD = Phase 26a squash + docs-gap follow-up; tag `phase-26a-confirmed` resolves there)
Date: 2026-05-24
Design log: `confirmation_docs/PHASE_26b_DESIGN_LOG.md`
Tag at ship: `phase-26b-confirmed`

## §1 Scope shipped

* **`mindsos_server/persistence/bootstrap.py`** — appends `bootstrap_global_pair_from_falkordb(client) -> tuple[KnowledgeLayer, Metagraph]` symmetric load-or-mint pair helper. Closes B-26a-T4. Per Phase 26b design log R4-PB-1 (a) + R6-PB-1 (a) + ADR-0118 §am4 §"Decision §1+§2". Module docstring + `__all__` updated.
* **`mindsos_server/persistence/__init__.py`** — re-exports the new helper.
* **`mindsos_cli/commands/server.py`** — `_build_global_metagraphs(conn) → _build_global_metagraphs(conn, client)`; body rewrites to `bootstrap_global_pair_from_falkordb(client)` (canonical FalkorDB-loaded) + `rehydrate_pending_global(conn, pending_mg)` (pending SQLite-rehydrated per Z21.1). Propose (line 1711) + ship (line 1768) callsites reorder `client = _resolve_client()` open BEFORE pair helper; try/finally envelopes both helper + library call. Read-local callsite at 1568 UNCHANGED per R5-F7 (Phase 25 in-memory kl sufficient for diagnostic; not a Global-content consumer). Import list update: REMOVE `bootstrap_global` + `bootstrap_pending_global` + `rehydrate_global_metagraphs` from mindsos_admin imports; ADD `rehydrate_pending_global`; ADD `bootstrap_global_pair_from_falkordb` from mindsos_server.persistence.
* **`docs/decisions/adr/0118-per-user-transactional-promotion.md`** — §amendment-4 appended (3-clause two-store decomposition). Coordinated changes list locked. Closes the §am3 "active code" wording with §am4 clause-2 explicit demotion of pending Cypher write to forensic-only.
* **`confirmation_docs/PHASE_MAP.md`** — §26b row replaced. Scope expanded from "no feature additions" to NET-NEW (pair helper); fixture path corrected (`tests/phase_26a/` → `tests/phase_26b/`); substep count corrected (8/9 → 13); ADR delta populated (ADR-0118 §am4 NEW; ADR-0010 + ADR-0123 + ADR-0114 + ADR-0043 + ADR-0121 + ADR-0011 + ADR-0125 UNCHANGED).
* **10-site version bump** `+phase26a → +phase26b` (pyproject + 6 pkg `__init__` + `mindsos_cli/manifest.toml` + `docker-compose.yml` prod/test).
* **`tests/phase_26b/`** — NEW directory + 9 files:
  - `__init__.py`
  - `conftest.py` — function-scope `scenario_falkordb_clean` + `scenario_state_dir` fixtures per R2-PB-1 (a)
  - `_normalize.py` — 3 regex strip-set per R4-PB-3 (a) (UUID + ISO TS + INT TS field)
  - `_falkordb_assert.py` — direct-Cypher helpers (`open_client`, `resolve_canonical_metagraph_id`, `resolve_pending_metagraph_id`, `count_canonical_nodes`) per R1-PB-6 (a)
  - `fixtures/__init__.py`
  - `fixtures/_test_importer.py` — `TestImporter` ImporterProtocol-shape class reading sibling `.tsv` per R3-PB-6 (c)
  - `fixtures/_test_importer_data.tsv` — 10 rows `ConceptNode` per R5-F4
  - `test_integration_a.py` — single `test_integration_a` function + 13 step helpers + `ScenarioState` thread per R3-PB-7 (a)
  - `test_bootstrap_global_pair.py` — 5 unit tests of pair helper (mint→load stable canonical id; mint→load stable pending id; tuple-shape KL+Metagraph; pending role-set mirrors canonical; canonical-pre-existing + pending-missing heals)
  - `test_signature_build_global_metagraphs.py` — signature + body-source smoke
* **0 schema bumps** (`_SCHEMA_VERSION` stays at 4).
* **0 new audit events** (Phase 26a R7-F4 importer-pinning + R1-PB-6 (a) carry forward).
* **0 phase-baseline literal-decay updates expected** (no schema bump, no DEFAULT_INDEXES change, no SENTINEL_PATHS change). Probe at first test run.

## §2 Design-log §am-impl addendum — Round 5 + Round 6 picks reconciled

R5 pre-impl probe (10 findings; 4 §am-impl + 6 confirmations):

| # | Pick | Finding | Impl reconciliation |
|---|---|---|---|
| R5-F1 | R4-PB-4 row 2 audit event name | `mindsos_server/audit.py:61` defines `EVT_ADMIN_CREATE_USER` (Phase 18 consumer); `EVT_ADMIN_ENABLE_USER` exists for a different verb | scenario step 9 audit assertion: `EVT_ADMIN_CREATE_USER ×2` (one per user1 + user2 create) |
| R5-F2 | R4-PB-4 row 6 audit event name | `mindsos_server/audit.py:115` defines `EVT_CROSS_USER_READ_INSTALL` (Phase 18 PB-34 declared; Phase 25 first-fire); extra_json shape includes `target_role_graph_node_counts` dict | scenario step 9 audit assertion: `EVT_CROSS_USER_READ_INSTALL` with `target_role_graph_node_counts={"concepts":1}` from R5-F4 seed |
| R5-F3 | R2-PB-6 (b) propose payload | `mindsos_knowledge/schemas/lexicon.py:22` defines `LEXICON_NODE_TYPES = (NODE_LEMMA, NODE_SENSE, NODE_SYNSET, NODE_SENSE_EXAMPLE)` — Lemma is leaf-simplest | propose payload `{kind:"ATOM", node:{node_type:"Lemma", value:"test_lemma_phase26b", target_role:"lexicon", properties:{}}}` |
| R5-F4 | R3-PB-3 (d) Local seed role | no Phase 25 test populates a Local Metagraph with explicit role-graph nodes; no precedent | use `concepts` role + node_type `ConceptNode`; documented as scenario-arbitrary; Phase 14 Local role-set enumeration deferred |

R6 §am-impl pass — 1 PB + impl bundle:

| # | Pick | Resolution |
|---|---|---|
| R6-PB-1 | Pair helper pending-mint persist | (a) persist-on-mint; symmetric with canonical; first-ever bootstrap persists empty pending Metagraph so subsequent CLI invocations resolve stable pending `metagraph_id` via find_by_name |

## §3 Smoke results

Host-native syntax check (`python3 -m py_compile`): **TODO [Linux]**.

Host-native pytest on `tests/phase_26b/`: **TODO [Linux]** — `python3 -m pytest tests/phase_26b/ -v`.

Host-native pytest cumulative `tests/`: **TODO [Linux]**.

Docker pytest on `mindsos:phase26b-test`: **TODO [Linux]** — `docker compose --profile test build mindsos-test && docker compose run --rm mindsos-test pytest tests/phase_26b/ tests/`.

Manual smoke recipe (Phase 26a smoke replay + Phase 26b stable-id verification; per `feedback_smoke_harness_host_native.md`):

```bash
# 1. Phase 26a baseline replay (no Phase 26b code yet — checkout phase-26a-confirmed)
git checkout phase-26a-confirmed
docker compose up -d falkordb
mindsos server bootstrap admin
mindsos server login admin
mindsos admin import dolce --source /path/to/dolce.owl  # populate canonical
# Resolve canonical metagraph_id via FalkorDB:
redis-cli -p 6379 GRAPH.QUERY mindsos "MATCH (m:Metagraph {name:'global_knowledge'}) RETURN m.id"
#   ↳ remember this id as $ID_PRE

# 2. Phase 26b checkout + replay
git checkout phase-26b
docker compose --profile test build mindsos
mindsos server release propose-for-promotion --input-json proposal.json
mindsos server release ship
# Re-resolve canonical metagraph_id:
redis-cli -p 6379 GRAPH.QUERY mindsos "MATCH (m:Metagraph {name:'global_knowledge'}) RETURN m.id"
#   ↳ id_post should EQUAL $ID_PRE  ✓ B-26a-T4 closed
```

## §4 Hotfix ledger

(populated at first test run)

| ID | Symptom | Fix | Files | Notes |
|---|---|---|---|---|

## §5 Ship checklist progress

* [x] Phase 26b source written.
* [x] Phase 26b tests written.
* [x] Version bump 10 sites.
* [x] 1 ADR amendment appended (ADR-0118 §am4).
* [x] notes-phase-26b.md at repo root (this file).
* [x] Phase 26b design log at `confirmation_docs/PHASE_26b_DESIGN_LOG.md`.
* [x] PHASE_MAP.md §26b row updated.
* [ ] Host-native tests GREEN (`tests/phase_26b/` then cumulative `tests/`). **[Linux]**
* [ ] Docker tests GREEN. **[Linux]**
* [ ] Manual smoke against FalkorDB (Phase 26a baseline replay + Phase 26b stable-id verification per §3). **[Linux]**
* [ ] `git status` review on Mac; `git add` everything.
* [ ] Open PR against `main` from `phase-26b`. **[Mac]**
* [ ] CI green (`release.yml`).
* [ ] Squash-merge PR. **[Mac]**
* [ ] `mindsos confirm-phase --phase 26b --notes-file notes-phase-26b.md` generates `confirmation_docs/PHASE_26b_CONFIRMED.md`. **[Linux]**
* [ ] Commit + push the confirmation doc (or as post-squash follow-up commit per Phase 26a precedent).
* [ ] `git tag phase-26b-confirmed <squash-or-follow-up-sha>` + push. **[Mac]**
* [ ] CI re-runs against tag green.

## §6 Phase 27 carry-forwards

### Phase 27 = L3 DataStates + capacity primitives (PHASE_MAP §27)

No direct Phase 26b → Phase 27 substrate dependency. Phase 27 is the first L3 phase; its dependencies (Phases 02, 05, 06) all shipped pre-Phase-15. Phase 26b's two-store decomposition + pair helper are L0/L1/L2 surface; L3 reads through L2's KnowledgeLayer (Phase 27 onward will inherit `bootstrap_global_pair_from_falkordb` consumers automatically as the CLI release flow exercises both ADR-0118-substrate and L3-substrate via the same Client).

### Phase 26b carry-forwards into the broader-PHASE_MAP §38 (deferred CLI verbs)

Add to §38 at this ship:

* `mindsos admin import test-importer` — generic test-importer CLI verb (Phase 26b step 4 alt; R3-PB-1 (a) closure).
* `mindsos kl status --json` — exposes canonical metagraph_id + role-graph node counts; would avoid the direct-Cypher `_falkordb_assert.py` helper at step 10 (R1-PB-6 (b) discarded alternative).
* `mindsos knowledge walk --role <role>` — scenario step 5 CLI form (currently in-process).
* `mindsos kl seed-fixture` — scenario step 5.5 CLI form (currently in-process; gated on Local persister persistence per ADR-0011 §am2).

### Phase 14 Local role-set enumeration

Phase 26b R3-PB-3 (d) + R5-F4: no Phase 25 precedent for which Local roles exist; scenario picks `concepts` arbitrarily. **First L4/L5 phase touching Local content must enumerate the canonical Local role-set** (analogous to Phase 14's `_GLOBAL_NAMED_ROLES` lock for Global).

### Eager-load cost mitigation (ADR-0125 promotion)

Phase 26b §am4 documents the eager-load cost (full `MetagraphLoader.load(metagraph_id)` per CLI invocation; scales with Global content size). ADR-0125 lazy hydration / LRU still Proposed; promotion + `lazy=True` kwarg in `bootstrap_kl_from_falkordb` + pair helper at the first phase that demonstrably needs it.

## §7 Implementation references

See `confirmation_docs/PHASE_26b_DESIGN_LOG.md` §5 for the canonical scope per R0-R6 picks; the §am-impl addendum above (§2) documents R5 probe-vs-pick reconciliations + R6 PB-1 closure.

Key ADR cross-references:
* **ADR-0118 §am4** — three-clause two-store decomposition; canonical content authority = FalkorDB via `bootstrap_global_pair_from_falkordb`; pending content authority = SQLite per Z21.1; SQLite remains ship-manifest authority; §am3 pending Cypher write demoted to forensic-only.
* **ADR-0010 §am1 + §am2** — unchanged; `server → admin` (Phase 24 PB-Z22) + `admin → core` (Phase 26a) edges already enumerated cover the pair helper's imports.
* **ADR-0123 §am1** — unchanged; `Metagraph(name)` index ships at 26a; pair helper's `find_by_name` consumer.
* **ADR-0043** — unchanged. KL stays in-memory; server owns I/O — the pair helper IS the server's I/O at Phase 26b.
* **ADR-0121** — unchanged. FalkorDB substrate decision honored.
* **ADR-0125** — Proposed; lazy hydration deferral notes captured in §am4 "Eager-load cost" subsection.
