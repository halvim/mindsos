---
phase: 26b
phase_title: "Integration A end-to-end scripted scenario + B-26a-T4 closure"
layer: cross (server + admin + CLI + tests)
status: design-locked
date_locked: 2026-05-24
design_rerun: 2026-05-24  # 6 rounds + R5 pre-impl probe per Phase 25/26a discipline
branch: phase-26b (to-be-cut from origin/main HEAD = Phase 26a squash + docs-gap follow-up; tag phase-26a-confirmed resolves there)
tag_on_confirm: phase-26b-confirmed
net_new: true   # NEW: bootstrap_global_pair_from_falkordb (symmetric pair helper closes B-26a-T4); MODIFIED: _build_global_metagraphs signature+body + 2 callsite reorders; ADR-0118 §am4
design_rounds: 6   # R0-R4 design + R5 pre-impl probe + R6 §am-impl
total_picks: 28  # R0:12 + R1:8 + R2:8 + R3:8 + R4:8 + R5:10 reconciliations + R6:1 (R6-PB-1) — picks across rounds with some R2-R4 reversal-revisits
prior_phase: 26a
next_phase: 27
---

# Phase 26b Design Log — Integration A end-to-end + B-26a-T4 closure

## §0. Scope summary + correction note

Phase 26b is the second half of the Phase 26 split locked at Phase 26a design log R1-PB-1 (c). Phase 26a wired FalkorDB persistence at the substrate level (`bootstrap_kl_from_falkordb` + `MetagraphLoader.find_by_name` + 19th `DEFAULT_INDEXES` entry + §am3 Cypher MERGE templates + `client: Client` kwarg cascade through propose / release / audit_gate + admin importer FalkorDB persist). Phase 26b runs the integration scenario over the wired substrate AND closes B-26a-T4 (the ephemeral-metagraph_id gap surfaced at Phase 26a host smoke).

The B-26a-T4 closure is the substantive code change: rewire `_build_global_metagraphs(conn) → _build_global_metagraphs(conn, client)` to use a new symmetric pair helper `bootstrap_global_pair_from_falkordb(client) -> tuple[KnowledgeLayer, Metagraph]` (R4-PB-1 (a) + R6-PB-1 (a)). The scenario test harness composes Phase 18/19/20/21/22/24/25/26a CLI verbs end-to-end via the Typer CliRunner pattern.

**Correction note (R2-PB-5 (a)):** Phase 26a's design log §6 + notes-phase-26a §6 + Phase 26a's earlier PHASE_MAP §26b row cited the test importer fixture at `tests/phase_26a/fixtures/_test_importer.py`. R0-PB-2 (a) relocated to `tests/phase_26b/fixtures/_test_importer.py` (co-located with the only consumer; Phase 26a tag-frozen surface stays frozen). PHASE_MAP §26b row updated at this ship; Phase 26a docs left as historical record.

Phase 26b does NOT ship: cross-process LocalPersister (Phase 25 ADR-0011 §am2 deferral holds); `apply_rewrite_map` consumer (admin-direct ATOM-only scope; no L4/L5 reader); generic `mindsos admin import test-importer` CLI verb (deferred to PHASE_MAP §38 per R1-PB-8 (b) + R3-PB-1 (a)); FalkorDB-side pending node DELETE (§am3 pending Cypher write demoted to forensic-only per R1-PB-1 (b); pending content authority = SQLite per Z21.1).

## §1. Round-by-round design ledger

**R0 — 12 PBs surfaced from required reading.** Substantive: PB-1 source-of-truth conflict (FalkorDB vs SQLite for canonical/pending); PB-2 importer fixture file location mis-cited by handoff; PB-3 pair helper home + name-constant import direction; PB-4 scenario extension with FalkorDB-read assertions; PB-5 ADR-0118 §am4 needed; PB-6 Phase 26a smoke re-run timing; PB-7 audit-events table format + EVT_AUDIT_QUERY self-emit; PB-8 Optional[Client]=None hatch under §am4; PB-9 `_resolve_kl()` callsite audit; PB-10 user2 Local seed substrate; PB-11 normalizer strip-set; PB-12 tag regex audit.

R0 picks: PB-1 (a) FalkorDB sole source-of-truth [LATER NARROWED at R1-PB-1 (b)]; PB-2 (a) `tests/phase_26b/fixtures/_test_importer.py`; PB-3 (d) single pair helper with required-kwargs [LATER REVERSED at R4-PB-1 (a) after ADR-0010 §am1 probe]; PB-4 (c) extend scenario + add step 10 stable-id assertion; PB-5 (a) ADR-0118 §am4 ships at 26b; PB-6 (b) Round 6 pre-impl probe; PB-7 (a)+(c) `emits_audit_in_same_call` column + EVT_AUDIT_QUERY filter; PB-8 (a) keep Optional[Client]=None hatch; PB-9 (c) audit 3 callsites; PB-10 (b) python-API install_local_metagraph seed [LATER REFRAMED at R1-PB-2 (a)]; PB-11 (b) minimal strip-set; PB-12 (a) Round 6 regex probe.

**R1 — 8 PBs derived from R0 picks landing.** R1-PB-1 surfaced ghost-node accumulation in FalkorDB-pending under R0-PB-1 (a) (the FalkorDB-side `_clear_pending_for_snapshot` doesn't exist; pending Cypher writes accumulate forever; audit_gate compares against ghosts). R1-PB-2 surfaced R0-PB-10 (b) structural break — InMemoryLocalPersister doesn't survive subprocess boundaries. R1-PB-3 noted pair helper still needs server→admin for `bootstrap_pending_global` import [LATER R4-PB-1 (a) corrected: server→admin already ALLOWED per ADR-0010 §am1]. R1-PB-4 surfaced SQLite remains load-bearing for ship snapshot; R0-PB-1 (a) was over-broad → TWO-STORE framing. R1-PB-5 Phase 24 test impact; R1-PB-6 step 10 assertion mechanism; R1-PB-7 ADR-0114 cascade; R1-PB-8 PHASE_MAP §38 deferred verbs.

R1 picks (with R4 reversals): R1-PB-1 (b) NARROW: canonical=FalkorDB load; pending=SQLite rehydrate; pending Cypher write demoted to forensic; R1-PB-2 (a) step 6 in-process python; R1-PB-3 (d) required kwargs [LATER R4-PB-1 (a) VOIDED]; R1-PB-4 (a) ADR-0118 §am4 three-clause text; R1-PB-5 (a)+(c) Phase 24 tests untouched + one 26b CLI-integration test asserts contract divergence; R1-PB-6 (a) direct Cypher via `tests/phase_26b/_falkordb_assert.py` helper; R1-PB-7 (b) no ADR-0114 touch; R1-PB-8 (b) discover deferred verbs during impl.

**R2 — 8 PBs.** R2-PB-1 conftest cleanup scope (function-scope for cross-subprocess); R2-PB-2 importer + propose role choice (disjoint avoids audit_gate); R2-PB-3 in-process step 6 persister wiring (helper signature); R2-PB-4 §am4 text precision (3-clause lock); R2-PB-5 PHASE_MAP §26b vs frozen Phase 26a docs; R2-PB-6 step-7 payload schema dependency; R2-PB-7 eager-load perf; R2-PB-8 round projection (R4 saturation; R5 probe; R6 §am-impl).

R2 picks: R2-PB-1 (a) function-scope conftest cleanup; R2-PB-2 (a) importer=concepts + propose=lexicon (disjoint); R2-PB-3 (a) `_seed_user2_local` helper; R2-PB-4 (a) §am4 3-clause text locked; R2-PB-5 (a) update PHASE_MAP at ship + leave Phase 26a docs historical; R2-PB-6 (b) defer payload to R5 probe; R2-PB-7 (a)+(d) accept eager load + lightweight scenario importer; R2-PB-8 (a) R4 saturation; R5 probe; R6 §am-impl.

**R3 — 8 PBs.** R3-PB-1 step-4 importer wiring choice (Python-API bypass — no CLI verb); R3-PB-2 admin session juggling for step 6+; R3-PB-3 Local seed role choice (no Phase 25 precedent); R3-PB-4 scenario substep count creep (8→~12); R3-PB-5 audit table content (R4 skeleton); R3-PB-6 TSV file format (sibling .tsv); R3-PB-7 test file structure (single function + helpers + ScenarioState); R3-PB-8 ScenarioState field list (impl detail).

R3 picks: R3-PB-1 (a) Python-API bypass for step 4; R3-PB-2 (a) two-token model (admin + user1); R3-PB-3 (d) defer role to R5 probe; R3-PB-4 (a) renumber 13 substeps honestly; R3-PB-5 (a) R4 skeleton + R5 probe + R6 §am-impl; R3-PB-6 (c) sibling .tsv via `source: Path` ctor arg; R3-PB-7 (a) single function + step helpers + `ScenarioState`; R3-PB-8 (b) impl detail.

**R4 — saturation pass. 8 PBs.** R4-PB-1 (a) REVERSES R1-PB-3 (d): ADR-0010 §am1 already ALLOWS server→admin (Phase 24 PB-Z22); pair helper signature simplifies to `bootstrap_global_pair_from_falkordb(client)`; names + helpers imported internally. R4-PB-2 (a) lock concrete body. R4-PB-3 (a) lock 3 normalizer regexes. R4-PB-4 (a) lock 13-row audit-events skeleton. R4-PB-5 (a) lock 10-target R5 probe list. R4-PB-6 confirmation: no ADR-0010 touch. R4-PB-7 (a) conditional R4 saturation; R5.5 reserved. R4-PB-8 confirmation: zero Phase 24 test literal-decay.

**R5 — pre-impl probe pass (10 findings).** No structural reversals; R4 saturation HOLDS; R5.5 reserved-but-not-triggered. 4 §am-impl reconciliations + 6 confirmations:
- **R5-F1 §am-impl:** R4-PB-4 row 2 — `EVT_ADMIN_ENABLE_USER` → `EVT_ADMIN_CREATE_USER` (Phase 18 user-create event).
- **R5-F2 §am-impl:** R4-PB-4 row 6 — `EVT_READ_OTHER_LOCAL` → `EVT_CROSS_USER_READ_INSTALL` (Phase 18 PB-34 declaration; Phase 25 first-fire).
- **R5-F3 §am-impl:** R2-PB-6 (b) propose payload concrete: `Lemma` node into `lexicon` role.
- **R5-F4 §am-impl:** R3-PB-3 (d) Local seed role = `concepts` + node_type `ConceptNode` (no Phase 25 precedent; scenario-arbitrary; `ensure_global_role_graph` works for any role).
- **R5-F5 confirmation:** R0-PB-12 (a) `_TAG_RE = re.compile(r"^phase-(\\d{1,3})([a-z])?(?:-v(\\d+))?-confirmed$")` matches `phase-26b-confirmed`; no regex patch.
- **R5-F6 confirmation:** R4-PB-1 (a) `from mindsos_admin import bootstrap_pending_global, PENDING_GLOBAL_METAGRAPH_NAME` resolves; pair helper imports clean.
- **R5-F7 confirmation:** R0-PB-9 (c) read-local CLI callsite stays in-memory; kl is transient vehicle for install_local_metagraph; not Global-content consumer. Only 2 of 3 `_resolve_kl()` callsites need client thread (1712 + 1768; NOT 1568).
- **R5-F8 confirmation:** R4-PB-5 #8+#9 `MetagraphLoader.load` + `MetagraphRepository.persist` empty-Metagraph safe (load gated by find_by_name returning non-None; persist guards all sub-writes with `if metagraph.X` checks).
- **R5-F9 confirmation:** R0-PB-6 (b) Phase 26a smoke replay path ready (`mindsos admin import dolce` exists).
- **R5-F10 confirmation:** R2-PB-1 (a) repo-root `tests/conftest.py` registers markers only; no autouse fixtures; Phase 26a conftest defines only `in_memory_client` (not autouse). Pure additive Phase 26b conftest.

**R6 — §am-impl pass (1 PB + impl bundle).** R6-PB-1 (a) pair helper persists pending Metagraph anchor on first-ever mint (symmetric with canonical) so subsequent CLI invocations resolve a stable pending `metagraph_id`. Else pending mints fresh per invocation — defeats B-26a-T4 closure on pending side. Impl bundle delivered in design log §5.

## §2. Final locks (consolidated picks across R0-R6)

| Topic | Final pick | Source round |
|---|---|---|
| Substrate decomposition | Two-store: canonical=FalkorDB; pending=SQLite per Z21.1; SQLite=ship-manifest authority | R1-PB-1 (b) + R1-PB-4 (a) |
| Pair helper signature | `bootstrap_global_pair_from_falkordb(client) -> tuple[KnowledgeLayer, Metagraph]`; names+helpers imported internally | R4-PB-1 (a) [REVERSES R1-PB-3 (d)] |
| Pair helper pending mint | persist-on-mint for both canonical AND pending (symmetric) | R6-PB-1 (a) |
| `_build_global_metagraphs` body | concrete locked at §5 | R4-PB-2 (a) |
| ADR-0118 §am4 text | 3-clause locked: canonical FalkorDB / pending SQLite forensic-only-write / SQLite ship-manifest | R2-PB-4 (a) + R6 §C |
| Optional[Client]=None hatch | Preserved for Phase 24 unit tests; production CLI MUST pass live | R0-PB-8 (a) + R1-PB-5 (a) |
| `_resolve_kl()` callsite updates | 2 of 3 (1712 propose + 1768 ship; NOT 1568 read-local) | R0-PB-9 (c) + R5-F7 |
| Scenario in-process step 4 | Python-API TestImporter bypass; no CLI subprocess | R3-PB-1 (a) |
| Scenario in-process step 6 | python-API `read_other_local_summary` call; in-process persister + kl | R1-PB-2 (a) + R2-PB-3 (a) |
| user2 Local seed | `_seed_user2_local` helper; 1 node `ConceptNode` in `concepts` role | R2-PB-3 (a) + R5-F4 |
| Propose payload | `ATOM` Lemma into `lexicon` (disjoint from import role) | R2-PB-2 (a) + R5-F3 |
| Test importer | `tests/phase_26b/fixtures/_test_importer.py` + sibling `.tsv`; `source: Path` ctor arg | R0-PB-2 (a) + R3-PB-6 (c) |
| Scenario substep count | 13 (renumbered from "8 step" nominal) | R3-PB-4 (a) |
| Test file structure | single `test_integration_a` + 13 step helpers + ScenarioState | R3-PB-7 (a) |
| Conftest cleanup scope | function-scope FalkorDB wipe; no autouse-fixture conflicts | R2-PB-1 (a) + R5-F10 |
| Step 10 stable-id assertion | direct Cypher via `tests/phase_26b/_falkordb_assert.py` helper | R0-PB-4 (c) + R1-PB-6 (a) |
| Normalizer | 3 regex strip-set (UUID + ISO TS + INT TS field) | R0-PB-11 (b) + R4-PB-3 (a) |
| Audit-events table | 13-row table with R5-corrected event names; `emits_audit_in_same_call` column; EVT_AUDIT_QUERY filter | R0-PB-7 (a)+(c) + R4-PB-4 + R5-F1 + R5-F2 |
| ADR-0114 cascade | no touch; §am4 of ADR-0118 implicitly closes | R1-PB-7 (b) |
| ADR-0010 touch | no touch; §am1 + §am2 already cover server→admin + admin→core | R4-PB-6 |
| Deferred CLI verbs | discover during impl; PHASE_MAP §38 update at ship | R1-PB-8 (b) + R3-PB-1 (a) |
| Saturation discipline | R4 conditional saturation; R5 probe; R5.5 reserved; R6 §am-impl + 1 PB | R2-PB-8 (a) + R4-PB-7 (a) |

## §3. ADR delta at Phase 26b ship

| ADR | Status | Change |
|---|---|---|
| ADR-0118 §am4 | NEW | Two-store decomposition; canonical content authority = FalkorDB via `bootstrap_global_pair_from_falkordb`; pending content authority = SQLite per Z21.1; SQLite remains ship-manifest authority; §am3 pending Cypher write demoted to forensic-only; closes B-26a-T4 ephemeral-metagraph_id gap |
| ADR-0010 | UNCHANGED | §am1 + §am2 already cover `server → admin` (Phase 24 PB-Z22) + `admin → core` (Phase 26a) edges needed by pair helper imports |
| ADR-0123 | UNCHANGED | §am1 `Metagraph(name)` index ships at 26a; pair helper consumes; no further amendment |
| ADR-0114 | UNCHANGED | `releases.manifest_json` shape unchanged; §am4 of ADR-0118 implicitly closes any documentary-debt clause around persistence-deferral |
| ADR-0043 | UNCHANGED | KL stays in-memory; server owns I/O — the pair helper IS the server's I/O at Phase 26b |
| ADR-0121 | UNCHANGED | FalkorDB substrate decision honored |
| ADR-0011 | UNCHANGED | Local persister SQLite/Falkor still deferred per §am2 |
| ADR-0125 | UNCHANGED | Lazy hydration / LRU still Proposed; Global loaded eagerly per ADR-0125 Proposed semantics |

## §4. Versions of all files involved

10 version-literal sites bumped `+phase26a → +phase26b`:
* `pyproject.toml` (+ description prose rewritten for Phase 26b scope)
* `mindsos_admin/__init__.py`
* `mindsos_cli/__init__.py`
* `mindsos_cli/manifest.toml` (+ `phase = "26b"`)
* `mindsos_core/__init__.py`
* `mindsos_instances/__init__.py`
* `mindsos_knowledge/__init__.py`
* `mindsos_server/__init__.py`
* `docker-compose.yml` (2 sites — prod + test image tags)

0 schema bumps (`_SCHEMA_VERSION` stays at 4).
0 new audit events (R7-F4 + R1-PB-6 (a) Phase 26a importer pinning carries forward).
0 new ADR cascades beyond ADR-0118 §am4.

Phase-baseline literal-decay updates: probe at first test run; none expected since no schema bump / no DEFAULT_INDEXES change / no SENTINEL_PATHS change. Phase 26a precedent: `tests/phase_07/test_bootstrap.py` + `tests/phase_09/test_indexes_phase09.py` updated for `18 → 19` index count; Phase 26b expects no index count change.

## §5. Implementation references

| File | Change |
|---|---|
| `mindsos_server/persistence/bootstrap.py` | MODIFIED — appends `bootstrap_global_pair_from_falkordb(client) -> tuple[KnowledgeLayer, Metagraph]`; adds imports of `bootstrap_pending_global` + `PENDING_GLOBAL_METAGRAPH_NAME` from `mindsos_admin` + `Metagraph` from `mindsos_core`; updates module docstring + `__all__` |
| `mindsos_server/persistence/__init__.py` | MODIFIED — re-exports `bootstrap_global_pair_from_falkordb` |
| `mindsos_cli/commands/server.py` | MODIFIED — `_build_global_metagraphs(conn) → _build_global_metagraphs(conn, client)`; body rewrites to call pair helper + `rehydrate_pending_global`; propose+ship callsites reorder `client = _resolve_client()` open BEFORE pair helper, try/finally envelopes; admin-import list shrinks (`bootstrap_global` + `bootstrap_pending_global` + `rehydrate_global_metagraphs` REMOVED; `rehydrate_pending_global` ADDED) |
| `docs/decisions/adr/0118-per-user-transactional-promotion.md` | MODIFIED — §amendment-4 appended (3-clause decomposition; coordinated changes list) |
| `confirmation_docs/PHASE_MAP.md` | MODIFIED — §26b row replaced (scope expanded; fixture path; substep count; ADR delta; deferred-CLI-verb note) |
| `confirmation_docs/PHASE_26b_DESIGN_LOG.md` | NEW FILE (this file) |
| `notes-phase-26b.md` | NEW FILE |
| `tests/phase_26b/__init__.py` | NEW FILE |
| `tests/phase_26b/conftest.py` | NEW FILE (scenario_falkordb_clean + scenario_state_dir fixtures) |
| `tests/phase_26b/_normalize.py` | NEW FILE (3 regex strip-set) |
| `tests/phase_26b/_falkordb_assert.py` | NEW FILE (open_client + resolve_canonical_metagraph_id + resolve_pending_metagraph_id + count_canonical_nodes) |
| `tests/phase_26b/fixtures/__init__.py` | NEW FILE |
| `tests/phase_26b/fixtures/_test_importer.py` | NEW FILE (TestImporter ImporterProtocol; sibling-TSV reader) |
| `tests/phase_26b/fixtures/_test_importer_data.tsv` | NEW FILE (10 rows; ConceptNode rows for `concepts` role) |
| `tests/phase_26b/test_integration_a.py` | NEW FILE (`test_integration_a` + 13 step helpers + ScenarioState) |
| `tests/phase_26b/test_bootstrap_global_pair.py` | NEW FILE (5 unit tests + 1 integration test) |
| `tests/phase_26b/test_signature_build_global_metagraphs.py` | NEW FILE (signature + body-source smoke) |
| `pyproject.toml` + 6 pkg `__init__.py` + `mindsos_cli/manifest.toml` + `docker-compose.yml` | MODIFIED — 10-site version bump `+phase26a → +phase26b` |

## §6. Carry-forwards from Phase 26b to Phase 27

* **FalkorDB-side pending content cleanup.** §am4 demoted pending Cypher write to forensic-only; no FalkorDB-side DELETE companion to the §am3 pending MERGE write. Long-running deployments accumulate forensic-only pending nodes indefinitely. If audit_gate or any future consumer ever reads FalkorDB-side pending content, add a `_clear_pending_for_snapshot` FalkorDB-side companion. Tracked as PHASE_MAP §38 (future hygiene phase) candidate.
* **Deferred CLI verbs surfaced by scenario design.** `mindsos admin import test-importer` (R3-PB-1 (a)); `mindsos kl status --json` (R1-PB-6 (b) discarded alt); `mindsos knowledge walk --role <role>` (step 6 CLI form); `mindsos kl seed-fixture` (step 5.5 CLI form). All to be added to PHASE_MAP §38 at ship.
* **Phase 14 Local role-set enumeration.** R3-PB-3 (d) + R5-F4: no Phase 25 precedent for which Local roles exist; scenario picks `concepts` arbitrarily. First L4/L5 phase touching Local content must enumerate the canonical Local role-set.
* **Eager-load cost.** ADR-0125 lazy-hydration still Proposed; production CLI invocations against heavy-Global FalkorDB (post-Dolce/OEWN import) pay full-load cost per invocation. Promotion of ADR-0125 to Accepted + `lazy=True` kwarg in `bootstrap_kl_from_falkordb` + pair helper at the first phase that demonstrably needs it.

## §7. Carry-forwards beyond Phase 26b

* **Concurrent admin write coordination.** ADR-0118 §am3 §"Concurrency caveats" subsection notes per-graph atomicity + no cross-graph transaction primitive; Phase 32 (Integration B) or dedicated concurrency-discipline phase addresses. UNCHANGED at Phase 26b.
* **Local persister persistence.** ADR-0011 §am2 SQLite/Falkor Local persister defer to first user-Local-write phase. R1-PB-2 (a) Phase 26b workaround: scenario step 6 runs in-process. First production user-Local-write phase MUST ship a real persister AND CLI verbs that expose it.
* **L4/L5 reader of FalkorDB-pending.** §am4 clause 2 documents the gap; future readers may consume. Until then, write-without-reader cost is FalkorDB storage only (cheap).
