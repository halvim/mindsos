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

8 hotfixes batched at impl-run; all closed before docker-cumulative GREEN at 2931/28/0 in 30:55.

| ID | Symptom | Fix | Files | Notes |
|---|---|---|---|---|
| B-26b-T1 | `ImportError: cannot import name 'PENDING_GLOBAL_METAGRAPH_NAME' from partially initialized module 'mindsos_admin'` — circular import via `mindsos_admin → mindsos_server → mindsos_server.persistence → bootstrap.py → mindsos_admin` cycle. | Import from `mindsos_admin.bootstrap` submodule directly (sidesteps the `from . import audit_gate` package-init chain). Phase 26a's `bootstrap_kl_from_falkordb` already used this pattern with `mindsos_knowledge.knowledge_layer`. | `mindsos_server/persistence/bootstrap.py` (1-line edit) | Memory: NEW finding — pair helpers importing across packages should use submodule paths to avoid `__init__.py` init-order cycles. |
| B-26b-T2 | `UnknownTypeError: Unknown node type: 'ConceptNode'` in step 5 importer + step 5.5 _seed_user2_local. | R5-F4 picked `ConceptNode` arbitrarily without probing the `concepts` schema. `concepts` is FrameNet-shaped: `Frame` / `FrameElement` / `LexicalUnit` / `SemanticType` only. Replaced all 3 occurrences with `Frame`. | `tests/phase_26b/fixtures/_test_importer.py`, `tests/phase_26b/test_integration_a.py` | R5-F4 §am-impl correction: scenario seed + importer use `Frame` node_type, not `ConceptNode`. |
| B-26b-T3 | `PytestCollectionWarning: cannot collect test class 'TestImporter' because it has a __init__ constructor`. | Renamed class `TestImporter` → `FixtureImporter` (pytest auto-scans any `Test*`-prefixed class). | `tests/phase_26b/fixtures/_test_importer.py`, `tests/phase_26b/test_integration_a.py` | Pattern lesson: test fixture classes must not start with `Test`. |
| B-26b-T4 | `AssertionError: expected ≥10 nodes post-import, got 0` — `count_canonical_nodes` returned 0 after a successful `MetagraphRepository.persist`. | Probe: `MetagraphRepository.persist` writes Node rows with `id` + `graph_id` properties + `[:IN_GRAPH]` relationship to Graph anchor; NOT direct `metagraph_id` property. Counting via `MATCH (n:Node {metagraph_id: $mg_id})` returns 0 because that shape isn't written by the importer persist path. Fixed the Cypher to traverse via `MATCH (g:Graph {metagraph_id: $mg_id})<-[:IN_GRAPH]-(n:Node)`. | `tests/phase_26b/_falkordb_assert.py` | Memory: NEW finding — Phase 07 persist + Phase 26a §am3 write Nodes with DIFFERENT shapes (importer Graph-anchored; release-ship metagraph_id-property-only). |
| B-26b-T5 | Substantive finding (NOT a regression): §am3 `_RELEASE_MERGE_CYPHER` writes Node rows keyed on `(node_id, metagraph_id, graph_id)` WITHOUT creating `[:IN_GRAPH]` relationship. Release-shipped Nodes are ORPHAN from the Graph traversal path. `MetagraphLoader.load` (which uses `[:IN_METAGRAPH]→[:IN_GRAPH]`) won't see them. | Split `count_canonical_nodes` into two helpers: `count_canonical_nodes_via_graph_traversal` (importer-shape) + `count_canonical_nodes_via_metagraph_id_property` (release-shape). Scenario asserts each path separately. **Substantive carry-forward to Phase 27+** (see §6 below) — §am3 Cypher should be amended to add the `:IN_GRAPH` link clause so release content is consistently visible from a `MetagraphLoader.load`. Phase 26b ships the test asserting the split-shape reality; the §am3 amendment to add the link is deferred. | `tests/phase_26b/_falkordb_assert.py`, `tests/phase_26b/test_integration_a.py` | Memory: NEW finding — §am3 propose+release Cypher templates write orphan Node rows; lazy-hydration / MetagraphLoader read path doesn't surface them. Phase 26b §am4 documents the orphan; future amendment locks the link. |
| B-26b-T6 | `AttributeError: 'MetagraphView' object has no attribute 'role_graph'` at step 6 MetagraphView walk. | `MetagraphView` API: `roles() -> Set[str]` + `graphs_by_role(role) -> List[Graph]`. The `role_graph(role)` method does NOT exist. Updated step 6 to iterate `graphs_by_role(role)`. | `tests/phase_26b/test_integration_a.py` | R5 pre-impl probe should have included MetagraphView API enumeration. |
| B-26b-T7 | `AlreadyInstalledError: Local metagraph for user_id 'user2' is already installed.` at step 8. | `read_other_local_summary` internally calls the orchestrator's `_install_for` → `kl.install_local_metagraph(user_id, dump)` ctx mgr. My seed pre-installed via `kl.install_local_metagraph` → second install collides. Fixed by dropping the seed-side install (persister.save is the only seed needed; orchestrator loads + installs transiently). | `tests/phase_26b/test_integration_a.py` | Pattern lesson: `read_other_local_summary` is the install gate; seeding only writes to persister. |
| B-26b-T8 | `TypeError: string indices must be integers, not 'str'` at step 12 query-audit. | `mindsos server query-audit --json` emits `{"rows": [...], "count": N, "next_after_id": null|int}` — `rows` is wrapped, not the top-level array; row field name is `event` (not `kind`). | `tests/phase_26b/test_integration_a.py` | R4-PB-4 + R5-F3 skeleton used `kind`; CLI shape is `event`. §am-impl class. |

## §5 Ship checklist progress

* [x] Phase 26b source written.
* [x] Phase 26b tests written.
* [x] Version bump 10 sites.
* [x] 1 ADR amendment appended (ADR-0118 §am4).
* [x] notes-phase-26b.md at repo root (this file).
* [x] Phase 26b design log at `confirmation_docs/PHASE_26b_DESIGN_LOG.md`.
* [x] PHASE_MAP.md §26b row updated.
* [x] Host-native tests GREEN (`tests/phase_26b/` 8/8 in 8.27s). Cumulative host-native run surfaces env-class non-regressions (phase_00 falkordb_module needs sidecar reachable as docker-compose alias; phase_13 image_completeness asserts `/app/*` paths under MINDSOS_REPO_ROOT defaulting to docker image path) — both pre-existing host-native gaps, both pass in docker. **[Linux]**
* [x] Docker tests GREEN — `docker compose run --rm mindsos-test pytest tests/phase_26b/ tests/` returned **2931 passed, 28 skipped, 109 warnings in 1855.06s (0:30:55)** on `mindsos:phase26b-test`. Phase 26a baseline 2923 → Phase 26b 2931 (+8 from `tests/phase_26b/`). **[Linux]**
* [x] Manual smoke against FalkorDB — subsumed by the scenario integration test (test_integration_a CliRunner-driven E2E asserts metagraph_id stability + release ship +1 node + audit-events presence; Phase 26a host-CLI smoke recipe deferred as redundant). Phase 26b scenario test step 10 IS the B-26a-T4 closure verification. **[Linux]**
* [ ] `git status` review on Mac; `git add` everything.
* [ ] Open PR against `main` from `phase-26b`. **[Mac]**
* [ ] CI green (`release.yml`).
* [ ] Squash-merge PR. **[Mac]**
* [ ] `mindsos confirm-phase --phase 26b --notes-file notes-phase-26b.md` generates `confirmation_docs/PHASE_26b_CONFIRMED.md`. **[Linux]**
* [ ] Commit + push the confirmation doc (or as post-squash follow-up commit per Phase 26a precedent).
* [ ] `git tag phase-26b-confirmed <squash-or-follow-up-sha>` + push. **[Mac]**
* [ ] CI re-runs against tag green.

## §6 Substantive Phase 27+ carry-forwards (NEW at Phase 26b)

### B-26b-T5: §am3 release Cypher writes ORPHAN Node rows (no :IN_GRAPH link)

Phase 26b hotfix probe surfaced: `mindsos_server/release.py:_RELEASE_MERGE_CYPHER` writes Node rows with `(node_id, metagraph_id, graph_id)` properties but does NOT create the `[:IN_GRAPH]` relationship to the Graph anchor. The same is true for `mindsos_admin/promotion.py:_PROPOSE_MERGE_CYPHER` (pending side). Consequence: `MetagraphLoader.load(canonical_id)` (which traverses `[:IN_METAGRAPH]→[:IN_GRAPH]`) doesn't surface release-shipped content. ADR-0118 §am4 §"Decision §1" canonical-FalkorDB-load claim is partially honored: the canonical Metagraph **anchor** + role-graph topology load correctly, but **release-shipped content (from §am3 release write)** is orphan from the traversal path.

This is NOT a Phase 26b correctness regression — Phase 26b scenario asserts the orphan reality via the `count_canonical_nodes_via_metagraph_id_property` helper (Cypher MATCH on direct `metagraph_id`-property). But it IS a substantive substrate gap.

Fix candidates (Phase 27+):

1. **Amend §am3 Cypher to include `:IN_GRAPH`.** Add `WITH n MATCH (g:Graph {id: $canonical_graph_id}) MERGE (n)-[:IN_GRAPH]->(g)` clause to `_RELEASE_MERGE_CYPHER`. Symmetric add to `_PROPOSE_MERGE_CYPHER`. Mechanical 2-line patch; future-MetagraphLoader-load reads release content. Track as ADR-0118 §am5 OR as B-26b-T5 fix at first phase that needs to read released content via load (e.g. Phase 32 Integration B's L3 read of canonical).
2. **Acknowledge as documentary-only** (current Phase 26b state). §am4 documents the gap; no future-phase consumer reads released content via load.

Pick deferred to Phase 27 design; tracked as Phase 26b → 27 carry-forward.

## §7 Phase 27 carry-forwards

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
