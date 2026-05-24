---
phase: 26a
phase_title: "FalkorDB persistence wiring (Integration A substrate)"
layer: cross (Core + admin + server)
status: design-locked
date_locked: 2026-05-23
design_rerun: 2026-05-23  # multi-round re-litigation: R0 plan-level → R1 → R2 (substrate reversal) → R3 → R4 (KL.bootstrap finding) → R5 (3 reversals) → R6 (bounded probe) → R7 (pre-impl)
branch: phase-26a (to-be-cut from origin/main HEAD = Phase 25 squash 94c747d)
tag_on_confirm: phase-26a-confirmed
net_new: true   # NEW: mindsos_server/persistence/bootstrap.py + MetagraphLoader.find_by_name + 19th DEFAULT_INDEXES entry + client kwarg through propose/release/audit_gate
design_rounds: 7   # R0-R7 (R6 + R7 = saturation + pre-impl probe per Phase 25 precedent)
total_picks: 22  # R0:6 + R1:6 + R2:5 + R3:4 + R4:3 + R5:5 + R6:3 + R7:4 §am-impl picks; 2 voided across rounds (R1-PB-2 + R4-PB-1 home portion)
prior_phase: 25
next_phase: 26b
---

# Phase 26a Design Log — FalkorDB persistence wiring

## §0. Scope summary

Phase 26a is the first half of the original Phase 26 split. The original PHASE_MAP §26 row read "Integration A: L0+L1+L2 end-to-end scripted scenario" + "no feature additions" + "scope creep risk" — but **three independent documentary commitments** named Phase 26 as the persistence-wiring slot:

1. **ADR-0118 §am2 closing line:** *"When Phase 26 wires server-driven FalkorDB persistence, the Cypher templates in clauses 1 + 2 above become active code via a `client: Client` parameter added to the propose / release / audit_gate signatures."*
2. **`mindsos_cli/commands/admin.py` Phase 15a docstring (line 20-24):** *"Phase 15a does NOT persist the resulting Metagraph ... persistence of the imported Global is deferred to Phase 26 per Phase 14a round-3 lock."*
3. **Phase 15a carry-forward:** "server persistence ships at Phase 18+" already missed → implicit slide to Phase 26.

Plus a structural finding: PHASE_MAP §26 step 4 ("Import a 10-row fixture into Global") was **structurally impossible to verify cross-subprocess** without importer persistence — the scripted scenario as written assumed persistence works; it didn't.

R1-PB-1 (c) split Phase 26 into 26a (FalkorDB persistence wiring) + 26b (Integration A scenario over wired substrate). 26a closes all three documentary commitments at one ship.

Phase 26a does NOT ship: `apply_rewrite_map` (no consumer at 26a/b given admin-direct-ATOM-only scope per ADR-0118 §am1 narrow scope; defer per Phase 25 carry-forward); SQLite / FalkorDB Local persisters (Phase 25 deferral holds); concurrent admin write coordination (gap documented in §am3 §"Concurrency caveats"); WAL coordination (per Phase 07 `mechanism only, no caller`).

## §1. Round-by-round design ledger

Eight rounds of pushbacks + re-litigation. The cascade is itself the methodology — Phase 25 R6+R7 §am-impl precedent applied with R5+R7 surfacing structural reversals via post-Round-pick probes.

**R0 — Plan-level pushbacks (6 PBs).** PHASE_MAP §26 vs ADR-0118 §am2 contradiction; 7-step scenario un-implementable as written (missing CLI verbs for KL bootstrap, fixture seed, MetagraphView walk); audit query assertion wrong (only 4 of 7 steps audit); "scenario runs in under N seconds" empty without harness choice; Phase 25 cross-user-read coverage gap; ADR re-litigation always (§am2 re-litigated regardless of META-PB-1 outcome).

R0 picks: META-PB-1 (d) re-litigate §am2 [LATER REVERSED at R1-PB-1 (c)]; META-PB-2 (a) Python pytest harness with CLI where verbs exist; META-PB-3 (a)+(c) per-step audit expectations table; META-PB-4 (b) drop N; META-PB-5 (b) 2-user scenario in 26b; META-PB-6 (b) always re-litigate §am2.

**R1 — Triple documentary commitment finding (6 PBs).** R1-PB-1 surfaced that admin.py importer docstring + Phase 14a round-3 lock + ADR-0118 §am2 ALL name Phase 26 for persistence — not just §am2 alone. Triangulation flipped R0 META-PB-1 pick (d) "defer indefinitely" to **R1-PB-1 (c) split 26a + 26b**. R1-PB-2 invented "extend Phase 07 JSON state files" substrate [LATER VOIDED at R2-PB-1 (a) after probe].

R1 picks (with R2 reversals): R1-PB-1 (c) split into 26a+26b; **R1-PB-2 (ii) VOIDED**; R1-PB-3 (b) 26b grows to include propose/release; R1-PB-4 (b) raw assert+normalizer; R1-PB-5 (b) deferred-CLI-verb TODO → PHASE_MAP §38; R1-PB-6 (a) probe + pin importer audit emission.

**R2 — Substrate reversal (5 PBs).** Probe of `mindsos_core/persistence/metagraph_repository.py` line 113 showed `MetagraphRepository.persist()` writes via FalkorDB Cypher (`run_query` at lines 153/174/195/228/322/437/476). CLAUDE.md says verbatim *"graphs live in FalkorDB (per ADR-0121)."* R1-PB-2 (ii) "extend JSON state files" was substrate misclassification — conflated L1's pre-Phase-07 `~/.mindsos/<kind>-<name>.json` state-metadata convention with graph persistence.

R2 picks: **R2-PB-1 (a) reverse to FalkorDB substrate** via existing `MetagraphRepository` / `MetagraphLoader` per ADR-0121; R2-PB-2 single new ADR-0118 §am3 amendment (ADR-0121 unchanged; ADR-0043 unchanged); R2-PB-3 (b) unit tests + 2-3 E2E smoke in 26a; R2-PB-4 (c) suffix scheme 26a+26b; probe regex at R6; R2-PB-5 (c)+(d) concurrency caveats subsection in §am3 + inline TODO at write site.

**R3 — Wiring shape locks (4 PBs).** R3-PB-1 (d) hybrid `_resolve_client()` CLI helper + explicit `client` kwarg through library signatures [LATER R5-PB-3 voids module-level lazy-init portion]. R3-PB-2 (c) tiny custom test `ImporterProtocol` extension for 26a smoke fixtures (10-row TSV); R3-PB-3 (d) per-session FalkorDB container + per-test `GRAPH.LIST`+`GRAPH.DELETE`; R3-PB-4 (a) extend ADR-0010 §am1 table explicitly with `admin → core ALLOWED` row.

**R4 — KL.bootstrap in-memory finding (3 PBs).** Probe of `mindsos_knowledge/knowledge_layer.py:154` showed `KL.bootstrap()` is pure in-memory (mints fresh `Metagraph(name=...)`; calls `ensure_global_role_graph` in loop; zero FalkorDB). Cross-subprocess scenarios need load-from-FalkorDB on KL init — a seam R3 didn't account for.

R4 picks: R4-PB-1 (b) server-side wrapper `mindsos_server.bootstrap_kl_from_falkordb(client)` in `mindsos_server/orchestrator.py` [LATER R6-PB-2 (b) moved to `mindsos_server/persistence/bootstrap.py`]; R4-PB-2 (a) preserve in-memory shape + split-by-role mapping at persist boundary [LATER R5-PB-2 voids split-by-role half]; R4-PB-3 (b) project R5 as probable saturation; hold one more round.

**R5 — Substrate facts surface 3 structural reversals (5 PBs).** Probes of `mindsos_core/persistence/client.py` + `metagraph_repository.py` + `metagraph_loader.py` revealed:
- **F1:** `Client.run_query` is graph-agnostic (no graph_name parameter); per Phase 07 P4 A: *"Per-command connection lifecycle ... No long-lived process-scope clients."*
- **F2:** `MetagraphRepository.persist()` persists whole Metagraph keyed by `metagraph_id` FK into one FalkorDB graph; all Metagraphs coexist in one graph.
- **F3:** `MetagraphLoader.load(metagraph_id)` raises `PersistenceError` on missing.
- **F4:** ADR-0118 §am2 Cypher template `MATCH (src) IN mindsos_pending_global_<role>` assumes per-FalkorDB-graph-per-role layout — **structurally incompatible with the actual substrate.**

R5 picks: **R5-PB-1 (a) §am3 rewrites §am2 Cypher to metagraph_id+graph_id FK form** (third structural reversal in five rounds); **R5-PB-2 (a) drops split-by-role mapping** — persist whole Metagraph keyed by metagraph_id; one FalkorDB graph holds all Metagraphs; **R5-PB-3 (a) `_resolve_client()` lifecycle per-CLI-fresh** — Phase 07 P4 A invariant explicitly forbids module-level singleton (R3-PB-1 (d) "module-level lazy-init" half VOIDED); R5-PB-4 (a) `MetagraphLoader.find_by_name(name) -> str | None` NEW method; R5-PB-5 (c) bounded R6 probe pass capped to structural-level; literal drift → §am-impl.

**R6 — Bounded probe pass (3 PBs).** R6 probes WAL coordination, exception handling, Metagraph.name index, wrapper module home. R6-F1 = no WAL coordination needed (mechanism-only at Phase 07; no caller). R6-F2 = inconsistent exception handling in `persist()` (literal-level §am-impl). R6-F3 = `Metagraph.name` has NO index (substantive). R6-F4 = `mindsos_server/persistence/` sub-package already exists (substantive home decision).

R6 picks: R6-PB-1 (a) add 19th `("node", "Metagraph", "name")` index per ADR-0123 §am1; **R6-PB-2 (b) `mindsos_server/persistence/bootstrap.py` home** (R4-PB-1 (b) "orchestrator.py" home VOIDED); R6-PB-3 (c) R6 = design-saturation; R7 = pre-impl re-analysis (Phase 25 precedent).

**R7 — Pre-impl probe pass (4 §am-impl picks).** R7-F1 = `persist()` is MERGE-idempotent everywhere (`MERGE` not `CREATE` at builders.py lines 62/83/100/155/267/343) → bootstrap_kl_from_falkordb simplified. R7-F2 = `_find_role_graph` keys on `role` attribute (line 738). R7-F3 = `ImporterProtocol.target_roles: tuple[str, ...]` — no `target_metagraph_id`; CLI envelope owns Metagraph. R7-F4 = importers don't emit audit; step 4 audit-table expectation = "no audit row."

**No new structural reversals at R7.** R6 saturation held; impl proceeds.

## §2. Final locks (consolidated picks across R0-R7)

22 substantive picks; 2 voided across rounds (R1-PB-2 (ii) at R2-PB-1; R4-PB-1 (b) home portion at R6-PB-2).

| Topic | Final pick | Source round |
|---|---|---|
| Phase 26 scope | Split 26a (wiring) + 26b (scenario) | R1-PB-1 (c) |
| Substrate | FalkorDB via existing `MetagraphRepository` / `MetagraphLoader` (ADR-0121 unchanged) | R2-PB-1 (a) |
| Client wiring | Explicit `client` kwarg through library; per-CLI fresh `FalkorClient` via `_resolve_client()` | R3-PB-1 (d) + R5-PB-3 (a) |
| KL bootstrap seam | Server-side wrapper `mindsos_server.persistence.bootstrap.bootstrap_kl_from_falkordb(client)` | R4-PB-1 (b) + R6-PB-2 (b) |
| Load-or-mint logic | `find_by_name → load OR mint+persist`; persist is MERGE-idempotent | R5-PB-4 (a) + R7-F1 |
| Persist mapping | Whole Metagraph keyed by metagraph_id FK; one FalkorDB graph | R5-PB-2 (a) |
| Cypher templates | §am3 corrected to metagraph_id+graph_id+node_id MERGE keys | R5-PB-1 (a) |
| Metagraph.name index | Added as 19th `DEFAULT_INDEXES` entry per ADR-0123 §am1 | R6-PB-1 (a) |
| ADR-0010 admin→core | Explicit table extension at §am2 | R3-PB-4 (a) |
| Concurrency caveats | §am3 subsection + inline `# TODO(concurrency)` at write sites | R2-PB-5 (c)+(d) |
| 26a tests | Unit + 2-3 E2E FalkorDB smoke | R2-PB-3 (b) |
| 26b harness | Python pytest; CLI subprocesses where verbs exist | R0 META-PB-2 (a) |
| 26b audit assertion | Per-step expectations table; importer = no audit | R0 META-PB-3 (a)+(c) + R1-PB-6 (a) + R7-F4 |
| 26b 2-user scenario | 2nd user + admin read-local | R0 META-PB-5 (b) |
| 26b propose+release | Sub-scenario adds to 26b coverage | R1-PB-3 (b) |
| Golden diff | Raw `assert ==` + normalizer (no syrupy) | R1-PB-4 (b) |
| Deferred CLI verb TODOs | PHASE_MAP §38 | R1-PB-5 (b) |
| Naming scheme | 26a + 26b suffix per Phase 04-v2 + 05a-d precedent | R2-PB-4 (c) |
| 26a smoke fixture | Custom test ImporterProtocol extension; 10-row TSV | R3-PB-2 (c) |
| FalkorDB lifecycle | Per-session container; per-test cleanup | R3-PB-3 (d) |
| Saturation | R6 = design; R7 = pre-impl probe; impl post-R7 | R6-PB-3 (c) |
| R7 §am-impl literals | 4 reconciliations per §am-impl pattern | R7-F1..F4 |

## §3. ADR delta at Phase 26a ship

| ADR | Status | Change |
|---|---|---|
| ADR-0118 §am3 | NEW | Wiring at 26a; corrected Cypher (metagraph_id+graph_id+node_id MERGE keys; supersedes §am2 per-FalkorDB-graph naming); §"Concurrency caveats" subsection; closes §am2 "FalkorDB persistence deferral" clause |
| ADR-0010 §am2 | NEW | DAG enumeration extended: `admin → core ALLOWED` explicit row added |
| ADR-0123 §am1 | NEW | 19th `DEFAULT_INDEXES` entry `("node", "Metagraph", "name")` for `find_by_name` hot path |
| ADR-0043 | UNCHANGED | KL stays in-memory; server owns I/O — "I/O" at Phase 26a now means real FalkorDB writes via `MetagraphRepository` |
| ADR-0121 | UNCHANGED | FalkorDB substrate decision honored (R1-PB-2 (ii) "extend Phase 07 JSON state files" reversed at R2-PB-1 (a)) |
| ADR-0114 | UNCHANGED | `releases.manifest_json` semantics unchanged; SQLite stays manifest substrate |
| ADR-0011 | UNCHANGED at 26a | InMemoryLocalPersister still v1 only; SQLite/Falkor Local persisters defer to first user-Local-write phase |
| ADR-0125 | UNCHANGED | Lazy hydration / LRU still Proposed; Global loaded eagerly via Loader at Phase 26a |

## §4. Versions of all files involved

8 version-literal sites bumped `+phase25 → +phase26a`:
* `pyproject.toml`
* `mindsos_admin/__init__.py`
* `mindsos_cli/__init__.py`
* `mindsos_cli/manifest.toml` (+ `phase = "26a"` field bump)
* `mindsos_core/__init__.py`
* `mindsos_instances/__init__.py`
* `mindsos_knowledge/__init__.py`
* `mindsos_server/__init__.py`

2 baseline-literal-decay test updates (Phase 26a ADR-0123 §am1 cascade):
* `tests/phase_07/test_bootstrap.py` — index count 18 → 19; node-count 15 → 16
* `tests/phase_09/test_indexes_phase09.py` — index count 18 → 19

## §5. Implementation references

| File | Change |
|---|---|
| `mindsos_core/persistence/bootstrap.py` | MODIFIED — `DEFAULT_INDEXES` gains 19th entry |
| `mindsos_core/reconstruction/metagraph_loader.py` | MODIFIED — NEW method `find_by_name(name)` |
| `mindsos_server/persistence/bootstrap.py` | NEW FILE — `bootstrap_kl_from_falkordb(client)` |
| `mindsos_server/persistence/__init__.py` | MODIFIED — re-export new wrapper |
| `mindsos_admin/promotion.py` | MODIFIED — `client: Client` positional 2nd; `_PROPOSE_MERGE_CYPHER` constant + write per item |
| `mindsos_server/release.py` | MODIFIED — `client` positional through `release_update` + `_release_update_locked` + `_copy_role_pending_to_canonical`; `_RELEASE_MERGE_CYPHER` constant + per-item write |
| `mindsos_admin/audit_gate.py` | MODIFIED — `client` positional 2nd; TYPE_CHECKING import for forward symmetry |
| `mindsos_cli/commands/server.py` | MODIFIED — NEW `_resolve_client()` helper; `_resolve_kl(client=None)` accepts optional client; propose + release verb callsites updated |
| `mindsos_cli/commands/admin.py` | MODIFIED — `_run_single_importer` wires Repository.persist; docstring updated |
| `docs/decisions/adr/0118-per-user-transactional-promotion.md` | MODIFIED — §am3 appended |
| `docs/decisions/adr/0010-layer-isolation.md` | MODIFIED — §am2 appended |
| `docs/decisions/adr/0123-indexes-and-verify-integrity.md` | MODIFIED — §Revisions added; §am1 appended |
| `confirmation_docs/PHASE_MAP.md` | MODIFIED — §26 retired; §26a + §26b rows added |
| `notes-phase-26a.md` | NEW FILE |
| `confirmation_docs/PHASE_26a_DESIGN_LOG.md` | NEW FILE (this file) |
| `tests/phase_26a/__init__.py` + 7 test files | NEW DIR + 8 files |
| `tests/phase_07/test_bootstrap.py` | MODIFIED — index count baseline update |
| `tests/phase_09/test_indexes_phase09.py` | MODIFIED — index count baseline update |

## §6. Carry-forwards from Phase 26a to Phase 26b

* Scripted scenario (8 steps locked at R1-PB-3 + R0 META-PB-5 + R1-PB-6 + R3-PB-2): bootstrap → user1+user2 create → login user1 → KL bootstrap (Phase 26a wired) → import via test fixture → MetagraphView walk → admin read-local user2 → propose ATOM + release ship → logout → query-audit.
* Golden-output normalizer helper at `tests/phase_26b/_normalize.py` (R1-PB-4 (b) raw assert pattern).
* Per-step audit expectations table (R0 META-PB-3 (a) + R7-F4).
* PHASE_MAP §38 deferred-CLI-verb TODOs accumulate from 26b's "scenario step needs a verb that doesn't exist" findings.

## §7. Carry-forwards beyond Phase 26b

* **Concurrent admin write coordination** — documented in ADR-0118 §am3 §"Concurrency caveats" subsection; resolution deferred to Phase 32 (Integration B) or dedicated concurrency-discipline phase.
* **FalkorDB cutover for Local persisters** — Phase 25 deferral holds; SQLite + Falkor Local persisters defer to first user-Local-write phase.
* **`apply_rewrite_map` impl in KL** — Phase 25 deferral holds; no consumer at 26a/b given admin-direct-ATOM-only scope.
* **Audit emission for importers** — pinned to "no audit" at Phase 26b step 4 per R1-PB-6 (a) + R7-F4; future audit-coverage phase may revisit (would cascade through ADR-0013 §am4 + Phase 15a baseline literals).
* **Importer-side incremental persist (vs full Metagraph persist)** — Phase 26a flushes whole Metagraph via `MetagraphRepository.persist()` after importer mutates; if importer scale grows beyond O(small), incremental write pattern from propose-time (§am3 §"Decision §1") may be retrofitted.

## §8. B-26a-T4 candidate carried to Phase 26b — `_build_global_metagraphs` ephemeral-Metagraphs gap

**Surfaced during Phase 26a host smoke (post-ship; NOT a Phase 26a hotfix).** The CLI helper `mindsos_cli/commands/server.py:1613::_build_global_metagraphs(conn)` — called by `release propose-for-promotion` (line 1711) + `release ship` (line 1768) — builds **fresh in-memory Metagraphs** each CLI invocation via `bootstrap_global(importers=()) → bootstrap_pending_global(canonical_mg) → rehydrate_global_metagraphs(conn, ...)`. It does NOT call `bootstrap_kl_from_falkordb`. Each invocation mints brand-new random `metagraph_id` values for canonical + pending.

**Why this is a Phase 26b scope item, not a Phase 26a hotfix:**

* Phase 26a design log §0 explicit scope: "wires importer + propose + release + audit_gate to FalkorDB" at the substrate level — `bootstrap_kl_from_falkordb` + `find_by_name` + `MetagraphRepository.persist` MERGE-idempotency + §am3 Cypher templates.
* PHASE_MAP §26b step 7 explicit scope: "Propose ATOM + release ship sub-scenario per Phase 26a R1-PB-3 (b) — exercises Phase 24's propose/release surface with Phase 26a wiring." The CLI-orchestration-of-propose+release IS Phase 26b's job.
* Phase 26a ships the LOW-LEVEL bootstrap_kl_from_falkordb wrapper; Phase 26b will rewire `_build_global_metagraphs(conn) → _build_global_metagraphs(conn, client)` to use it for stable metagraph_ids across invocations.

**Phase 26a smoke confirms the substrate works correctly:** mint+load round-trip preserves metagraph_id (host smoke step 4+6 both returned `401ff013-...`); MetagraphRepository.persist() MERGE-idempotency confirmed via pytest E2E; ADR-0123 §am1 index operational via `CALL db.indexes()`. The Phase 26b rewire of `_build_global_metagraphs` will use this proven substrate.

**Expected Phase 26b rewire shape:**

```python
def _build_global_metagraphs(conn, client):
    canonical_kl = bootstrap_kl_from_falkordb(client)
    canonical_mg = canonical_kl.global_metagraph()
    # NEW Phase 26b: pending-side load-or-mint wrapper symmetric with bootstrap_kl_from_falkordb
    pending_mg = bootstrap_pending_global_from_falkordb(client, canonical_mg)
    rehydrate_global_metagraphs(conn, canonical_mg, pending_mg)
    return canonical_mg, pending_mg
```

Plus updates to the two callsites at server.py:1711 + 1768 to thread `client` through.

**Implication for Phase 26a release:** Phase 26a CAN ship as-is. The propose+release CLI verbs work at the SQLite+in-memory layer (Phase 24 contract preserved); the FalkorDB writes from §am3 templates land but are orphaned without the Phase 26b orchestration rewire. This is the intended split per the Phase 26a design.
