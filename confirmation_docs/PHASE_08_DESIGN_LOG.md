# Phase 08 Design Log

**Status:** Locked design (chat dated 2026-05-13).
**Target:** Phase 08 row text in `confirmation_docs/PHASE_MAP.md` §5 (replaces the 7-line stub `### Phase 08 — L1 Reconstruction (loaders, streaming, refresh)`).
**Scope:** L1 Reconstruction — function-shaped `load_graph` + `iter_load_graph`; class `MetagraphLoader` (+ module convenience `load_metagraph`) with `refresh(mg, role)`; sibling-package `mindsos_instances/reconstruction/instance_loader.py`; `after_load` observer plumbing; first L1 WAL consumer (recover-on-load); 2 new CLI verbs / 2 new CLI flag extensions; ADR-0124 flip; ADR-0125 untouched.
**Cascade position:** `05a → 05b → 05c → 05d → 06 → 07 → 08`. CASC-1 unblocked 08 when Phase 07 shipped (tag `phase-07-confirmed` on main; 1269 + 2 skipped in-container).

---

## Step 0 pre-design audit (resolved 2026-05-13)

Audited per Phase 07 Round-6 addendum §4 precedent. On-disk truth vs the handoff prompt's assumptions:

| Claim | Verdict | Evidence |
|---|---|---|
| Phase 07 squash-merged on main; tag `phase-07-confirmed` exists | **TRUE** | `git log origin/main --oneline -3` → `b07fdc6 Phase 07 — L1 Persistence (#14)`; tag present. |
| v3 baseline reconstruction sources exist at project root | **TRUE** | `/Layered Intelligence/mindsos_core/reconstruction/{graph_loader.py,metagraph_loader.py,instance_loader.py,xref_loader.py}` all present. v3 instance_loader actually lives at `/Layered Intelligence/mindsos_instances/reconstruction/instance_loader.py` per ADR-0132. |
| `mindsos_core/reconstruction/graph_loader.py` present in halvim_mindsos | **TRUE** | Phase 07 slim port; **function-shaped** `load_graph(client, gid, *, identity, schema)`. No `iter_load`, no class. |
| `mindsos_core/reconstruction/metagraph_loader.py` present | **FALSE** | Phase 08 introduces. |
| `mindsos_instances/reconstruction/` present | **FALSE** | Phase 08 introduces (per PB-4 + RR-13). |
| ADR-0124 Proposed | **TRUE** | `docs/decisions/adr/0124-streaming-loader-iter-load-and-refresh.md` frontmatter `status: Proposed`. |
| ADR-0125 Proposed | **TRUE** | `docs/decisions/adr/0125-lazy-local-hydration-with-lru-eviction.md` frontmatter `status: Proposed`; **`layer: Server`** (not L1). |
| State files at v=4 / v=3 / v=1 (graph / metagraph / schema) | **TRUE** | Phase 08 does not bump (M0 below). |
| Phase 06 ships `register_remove_observer` + `register_graph_added_observer` | **TRUE** | `mindsos_core/models/metagraph.py:345,368`. |
| Phase 07 ships `register_persist_observer` | **TRUE** | `mindsos_core/models/metagraph.py:382`. |
| `register_after_load_observer` exists | **FALSE** | Phase 08 introduces (per PB-4 + RR-9). |
| `IdentityRegistry.unregister()` exists as public method | **AUDIT REQUIRED** | Per RR-1 A — Phase 02 surface check at impl time; add additively if missing. |
| Phase 07 `cypher/builders.py` covers all 4 edge primitives for writes | **TRUE** | `build_unwind_create_intergraph_edges` + `build_unwind_create_intergraph_hyperedges` at lines 55-56; full coverage. |
| Phase 07 exception list | **TRUE** | `PersistenceError`, `IntegrityCheckError`, `OptimisticConcurrencyConflict`, `OptimisticConcurrencyExhausted`. No `ReconstructionError`, no `RefreshUnsafeError`, no `WALReplayerMissingError`, no `RoleMismatchError`. Phase 08 adds 3 new classes (R4-3). |
| Legacy `:MetagraphSettings` rows possible in halvim substrate | **FALSE** | Phase 07 writes via `_props_json` only (ADR-0130 supersedes ADR-0029). No legacy rows can exist. Strip the v3 migration code (RPB-6). |
| `automated_test_summary` in PHASE_07_CONFIRMED.md shows count: 0 | **TRUE; pre-existing parser gap** | `pytest -q` bare summary lines don't match the confirm-phase regex; same gap in 05d / 06; canonical counts live in tester_notes. NOT a Phase 08 row action. |
| `mindsos persistence verify --source=db --metagraph M` refused | **TRUE** | Phase 07 P49 A. Phase 08 unblocks (PB-7). |
| `MetagraphRepository.persist` programmatic-only in Phase 07 | **TRUE** | P60 A; CLI verb deferred. Phase 08 ships CLI wrap (PB-8). |

**Implication:** Phase 08 is a **slim port + glue + 2 new CLI verbs + 2 new flag extensions** phase. No state-file bumps. No new top-level Python package. Does introduce a new top-level sibling-package subpackage (`mindsos_instances/reconstruction/`) which costs **no** `feedback_new_top_level_package.md` 5-site audit (it's a subdir, not a new package). Sentinel-paths grows by ~15-20 entries (R4-14).

---

## Architectural distinction (load-bearing — read before any Phase 08 decision)

Phase 07 left two reconstruction holes that Phase 08 must fill cleanly:

1. **Single-Graph load** shipped (function-shaped `load_graph(client, gid)`); **metagraph load did not** (P12 D / M14 deferral). Phase 08 ships `MetagraphLoader` class + module convenience `load_metagraph()`.
2. **Write side complete** for all 4 edge primitives + Metagraph anchor + Instances (via observer); **read side covers single-Graph contents only**. Phase 08 ships the metagraph-context reads (MetaEdges, MetaHyperEdges, IntergraphEdges, IntergraphHyperEdges) + instance reads (sibling-package via observer).

**Phase 08 model:**

- **JSON state files stay authoritative.** No state-file bump (M0 carried from Phase 07).
- **`mindsos persistence` subapp gains 2 metagraph-scoped verbs** (`sync --metagraph M`, `load --metagraph M`) and **unblocks one verify flag** (`verify --source=db --metagraph M`). All other existing CLI surface unchanged.
- **`MetagraphLoader` is an orchestrator only** (RR-8 A). It calls `load_graph` / `iter_load_graph` for contained graphs, reads MetaEdges / MetaHyperEdges / IntergraphEdges / IntergraphHyperEdges inline, then fires `after_load(mg)`. Instance hydration happens sibling-side via `mindsos_instances.attach_registry()`'s subscription to that observer (mirrors Phase 07 M9 + P96 A architecture).
- **ADR-0124 flips** Proposed → Accepted; **ADR-0125 stays Proposed** (server-side; no L1 consumer in Phase 08 per PB-1 A).

**Architectural consequence:** Phase 09 (XRef) inherits the observer pattern — XRefLoader will subscribe via `after_load` (RR-10 A), no new sub-loader handle on MetagraphLoader. Phase 09 also gets `load_metagraph` round-trip for free.

---

## Meta-plan locks (M-series) — pre-Round-1

These govern the chat itself, not the row content.

### M0 — State-file disposition.
**Pick: B (carried from Phase 07).** No JSON state-file bump. Phase 08 is FalkorDB-side reads; JSON stays at v=4 (graph) / v=3 (metagraph) / v=1 (schema). Audit confirmed via `_state_version` literal grep (Phase 06 P38 A / Phase 07 #35 precedent).

### M1 — v3 baseline disposition.
**Pick: A (slim-port + glue).** Source: `/Layered Intelligence/mindsos_core/reconstruction/metagraph_loader.py` (236 LOC) + `/Layered Intelligence/mindsos_instances/reconstruction/instance_loader.py`. Stripped during port: XRef sub-loader (Phase 09), legacy `:MetagraphSettings` migration (RPB-6), per-load `schema` validation (R4-4 — kwarg accepted but ignored).

### M2 — Phase split.
**Pick: B (single Phase 08).** No 08a/08b. Net-new code is bounded (~12-15 source files + 6-8 test files); cascade cadence preserved.

### M3 — ADR re-litigation policy.
**Pick: A (status flip on consumer ship + impl-refs amendment).** ADR-0124 flips Proposed → Accepted in Phase 08 with P27 C wording (*"Accepted when L1 mechanism ships + `core.md` documents it; consumer integration tracked separately"*); §Implementation references amended for actual paths (RR-6 A). ADR-0125 untouched (PB-1 A). Phase 07's "ADR file edits in Phase override Phase 06 P45 B" precedent applies.

### M4 — Round count target.
**Pick: 3 rounds (per PB-13).** Actual stop: **4 rounds** (Round 4 surfaced material edge cases — exception classes, load order, identity-preservation tests — that warranted explicit pickking). Per RPB-11 B, no pre-budgeted Round-5 addendum slot; implementation chat may surface natural reshapes (P26+ pattern from Phase 07 if needed).

### M5 — Test budget.
**Pick: uncapped (per RPB-7 user override).** No projection; do as many as needed. Cumulative baseline ≥ 1269 + Phase 08 additions; tester records actual count in `PHASE_08_CONFIRMED.md`.

### M6 — InMemoryClient unit coverage policy.
**Pick: B (per RPB-13).** Use InMemoryClient call-recording for "right Cypher emitted" unit assertions on load paths; reserve `@pytest.mark.integration` for round-trip fidelity against real FalkorDB. Mirror Phase 07's mix.

### M7 — Fixture sharing.
**Pick: A (per RR-13).** Ship `tests/_shared/metagraph_equality.py:assert_metagraphs_equal` + `tests/_shared/large_graph_factory.py:make_large_graph_fixture` for reuse across Phase 08-11.

### M8 — Streaming CLI surface.
**Pick: A (per PB-10).** Programmatic-only in Phase 08; CLI always full-loads. iter_load consumers are L4 release-migration + Phase 15 importers. No `--stream` flag.

### M9 — `inspect-state` metagraph drill-down.
**Pick: B (per RR-11).** Phase 08 `inspect-state` stays global. Per-metagraph drill-down deferred to Phase 11.

### M10 — Round-5 addendum slot.
**Pick: B (per RPB-11).** Not pre-budgeted. Phase 08 has no equivalent of Phase 07's recovery-sweep gating. If implementation chat needs reshapes, surface them naturally (Phase 06/07 P45+ precedent).

### M11 — Test fixture scale defaults.
**Pick: B+C (per RPB-12).** 1K-node fixtures default; opt-in 10K via `pytest.mark.slow`. Memory-scale validation is structural (PB-12 C), not pressure-based.

### M12 — Edge-primitive load ordering.
**Pick: A (per R4-1).** Locked sequence inside `MetagraphLoader.load`: recover() → anchor → contained Graphs → MetaEdges → MetaHyperEdges → IntergraphEdges → IntergraphHyperEdges → `after_load(mg)` fires.

### M13 — Exception class additions.
**Pick: A (per R4-3).** Phase 08 adds 3 new exception classes to `mindsos_core/exceptions.py`: `RefreshUnsafeError`, `WALReplayerMissingError`, `RoleMismatchError`. Generic read failures reuse `PersistenceError`. No `ReconstructionError` umbrella (Phase 07's `PersistenceError` is sufficient).

### M14 — Design-log structure.
**Pick: A (per R4-9).** Single `PHASE_08_DESIGN_LOG.md` (this file). Step 0 + Rounds 1-4 + lock table + cross-chat dependencies. No addendum sibling.

### M15 — Implementation-chat handoff prompt.
**Pick: B (per R4-10).** Overwrite existing `PHASE_08_NEXT_CHAT_PROMPT.md` with the implementation handoff after lock. Design prompt's role ends with Round 4 lock.

---

## Round 1 pushbacks (PB-1 — PB-14) — LOCKED 2026-05-13

Round 1 targeted the handoff plan's stub + 7 design-question seeds. Strongest finding: the stub conflates Phase 08 (L1) with ADR-0125 (Server) territory.

### PB-1 — ADR-0125 categorisation error.
**Pick: A.** Strip ADR-0125 from Phase 08 deliverables. ADR-0125 frontmatter is `layer: Server`; body says *"Server-layer ADR; not a Core change."* LRU eviction lives in `mindsos_server/local_registry.py` (Phase 18+). Phase 08 ships **zero** consumers of LRU. The stub's risk line "`refresh` must respect LRU eviction" is forward-coupling, not a Phase 08 deliverable. ADR-0125 stays Proposed; flip lands with Server in Phase 18+.

### PB-2 — Loader shape (function vs class).
**Pick: C (hybrid).** Function-style `load_graph(client, gid, *, identity, schema)` + new `iter_load_graph(client, gid, *, identity, batch_size)` (stateless single-source reads); class `MetagraphLoader(client)` with `.load()` + `.refresh()` (orchestration). Preserves Phase 07 P77 B function-style precedent for single-Graph reads; class is justified for metagraph composition + sub-loader observer wiring. ADR-0124 body amends to "function or method."

### PB-3 — `iter_load` signature reduction.
**Pick: A.** Graph-scoped only: `iter_load_graph(client, gid, *, identity=None, batch_size=10_000) -> Iterator[Graph]`. ADR-0124's `iter_load(metagraph_id, graph_id, ...)` signature amends to drop redundant `metagraph_id` slot (shared-registry concern is caller's responsibility via `identity=`). Metagraph-of-many-small-graphs streaming is Phase 11+ scope.

### PB-4 — Instance reconstruction architecture.
**Pick: A.** Symmetric with Phase 07 M9 + P96 A. Adds `register_after_load_observer` to `Metagraph` (mirrors `register_persist_observer`). `mindsos_instances/reconstruction/instance_loader.py` ships sibling-side per ADR-0132. `mindsos_instances.attach_registry()` extends to subscribe `after_load` observer (idempotent per Phase 06 P49 B helper). MetagraphLoader fires the observer ONCE after Core + all sub-reads complete (RPB-9).

### PB-5 — `RefreshUnsafeError` enforcement.
**Pick: B.** Ship `RefreshUnsafeError` exception class only (per ADR-0124 §"Constraint"). No per-role mutation-flag tracking on Metagraph in Phase 08. ADR-0124 acceptance criterion (P27 C "mechanism ships + `core.md` documents") is satisfied. Enforcement deferred to future phase; loud risk line + future-work entry.

### PB-6 — WAL first L1 consumer.
**Pick: B.** `MetagraphLoader.load(mid)` (and module function `load_metagraph(client, mid)`) ALWAYS calls `recover(client, mid)` BEFORE its reads. Defensive contract: no-op today (no replayers registered at L1), meaningful once L0/L2 register. Symmetric with Phase 07 4-step persist ordering. First L1 WAL consumer ships in Phase 08 via the load path. NOT applied to `load_graph` (standalone Graph has no metagraph recovery context — RPB-5).

### PB-7 — `verify --source=db --metagraph M` unblock.
**Pick: A.** Phase 08 drops Phase 07 P49 A refusal. CLI flow: `--source=db --metagraph M` calls `load_metagraph(client, mid)` then runs the existing 5-bucket scanner in memory. ~2 new CLI tests; zero new scanner code.

### PB-8 — Metagraph `sync` CLI verb.
**Pick: A.** Ship `mindsos persistence sync --metagraph M [--replace]` in Phase 08. The programmatic `MetagraphRepository.persist` exists since Phase 07; Phase 08 wraps with CLI verb. `--replace` semantics defined per RPB-4 C.

### PB-9 — `load` verb CLI shape.
**Pick: A.** Extend `load` with mutually-exclusive `--graph G | --metagraph M` (Typer constraint; exit 1 on combo per R4-6). Mirrors Phase 07 `verify --graph | --metagraph` mutex pattern.

### PB-10 — Streaming CLI surface.
**Pick: A.** Programmatic-only in Phase 08. CLI `load --metagraph M` (and `load --graph G`) always full-load. No `--stream` flag. iter_load consumers are L4 release-migration and Phase 15 importers. Defer CLI exposure to Phase 11+ if concrete operator workflow surfaces.

### PB-11 — Schema reattach during load.
**Pick: A.** `load_metagraph` reads the `schema_name` plain Cypher property (Phase 07 P100 A) and sets `mg.schema_name = X`; does NOT auto-attach the actual MetagraphSchema content. Schema JSON remains authoritative (L2 concern). Tester recipe: `mindsos metagraph attach-schema ...` after `persistence load --metagraph M` if vocab needed in memory.

### PB-12 — Memory-budget test methodology.
**Pick: C.** Structural assertion: each yielded `Graph` from `iter_load_graph` has `len(g.nodes) ≤ batch_size`; bounded memory follows by construction. CI-stable. Real memory-pressure validation deferred to a future "scale test" phase. PSUTIL / tracemalloc thresholds are CI-flaky.

### PB-13 — Round count target.
**Pick: 3 rounds (closed at 4 rounds; Round 4 surfaced material edge cases).**

### PB-14 — ADR-0124 acceptance criterion wording.
**Pick: C.** Flip ADR-0124 with both forms — P27 C wording in the acceptance statement ("mechanism + core.md") AND list actual `Implementation references` per RR-6 A. Body lists impl refs; acceptance criterion uses P27 C wording.

---

## Round 2 pushbacks (RPB-1 — RPB-14) — LOCKED 2026-05-13

Round 2 surfaced cross-cutting + correctness concerns the Round 1 picks raised.

### RPB-1 — `iter_load_graph` cross-batch edge fidelity.
**Pick: A.** Defer all edges/hyperedges to a final batch; intermediate batches are nodes-only + intra-batch edges (none, since the batch is a node-subset). Final batch yields any deferred cross-batch edges + hyperedges. ADR-0124's cross-batch claim is honored. Test fixture: 30 nodes, batch_size=10, edge node-3 → node-23; assembled graph contains it (RPB-8 explicit test).

### RPB-2 — `refresh` graph-drop choreography.
**Pick: A.** refresh uses proper `mg.remove_graph(gid)` API. Phase 06 `register_remove_observer` cascade fires (drops dependent SubGraphInstances / GraphInstances / ElementInstances). Then load fires; `after_load` rehydrates instances from DB. Observer-clean throughout; mirrors Phase 07 4-step persist.

### RPB-3 — `recover()` failure handling on load.
**Pick: C.** Narrow-catch the "no replayer registered" case (raises new `WALReplayerMissingError` per R4-3). Propagate everything else (driver errors, real failures). Test: register fake replayer + uncommitted WAL entry → recover replays; without replayer + uncommitted entry → load proceeds (no-op recover); driver error → propagates as `PersistenceError`.

### RPB-4 — `sync --metagraph M --replace` scope.
**Pick: C.** Refuses if any ElementInstance / CompositeInstance / XRef / uncommitted `:WALEntry` row references the target Metagraph. Raises `PersistenceError` with operator guidance: *"Metagraph M has dependent instances/xrefs/uncommitted-WAL; drop them or truncate before --replace."* Exit code 2. Mirrors Phase 07 P91 A pattern for `sync --graph G --replace` × uncommitted WAL.

### RPB-5 — `load_graph` recovery asymmetry.
**Pick: A.** `load_graph` does NOT call recover() — standalone Graph has no metagraph_id recovery context. Only `load_metagraph` recovers. Documented asymmetry in row Risks line.

### RPB-6 — Legacy `:MetagraphSettings` migration.
**Pick: A.** Strip v3's `_migrate_legacy_settings(mg)` code entirely. Phase 07 substrate is fresh (writes via `_props_json` only per ADR-0130). No legacy rows possible.

### RPB-7 — Test budget projection.
**Pick: uncapped (per user override 2026-05-13).** No cap, no projection. Do as many tests as needed. Per `feedback_test_budget_unlimited.md`.

### RPB-8 — `iter_load_graph` test methodology specifics.
**Pick: A.** Three tests: (i) structural `len(g.nodes) ≤ batch_size` per yield; (ii) equivalence `assemble(iter_load_graph(gid, batch_size=B)) == load_graph(gid)` for B ∈ {1, 100, ∞}; (iii) explicit cross-batch edge fidelity (30-node fixture, batch_size=10, edge across batches; assembled graph contains it).

### RPB-9 — `after_load` observer dispatch ordering.
**Pick: A.** Single fire after Core + all sub-reads complete (per M12 locked sequence). Subscriber chain handles cascade. Phase 09 extends by adding xref-load step BEFORE the fire (no new observer needed).

### RPB-10 — `iter_load_graph` and Intergraph primitives.
**Pick: A.** `iter_load_graph` loads ONLY intra-graph edges/hyperedges. Cross-graph primitives (IntergraphEdge / IntergraphHyperEdge) load via `MetagraphLoader.load` only (after all contained Graphs loaded, per M12 sequence). Narrow surface; documented.

### RPB-11 — Round-5 addendum policy.
**Pick: B.** No pre-budgeted Round-5 slot. Phase 08 has no Phase 07-equivalent gating (clean resync; no state-file bump; no new top-level package). Implementation chat surfaces reshapes if needed.

### RPB-12 — Streaming fixture size.
**Pick: B + C.** 1K-node fixtures default for correctness tests (batch_size=100 → 10 batches, exercises cross-batch). One `pytest.mark.slow` opt-in 10K fixture for stress visibility (not gating CI). 10K-vs-1K is a memory test, not a correctness test.

### RPB-13 — Integration-test density.
**Pick: B.** InMemoryClient call-recording for "right Cypher emitted" unit assertions on load paths; round-trip fidelity = `@pytest.mark.integration` against real FalkorDB. Mirrors Phase 07 P22 C pattern.

### RPB-14 — Lift read Cypher into `cypher/builders.py`?
**Pick: B.** Reads stay inline in loader modules (v3 + Phase 07 graph_loader precedent). Builders stay write-side; their value is ADR-0021 rel-type validation, which read paths don't need (untyped `MATCH (s)-[e]->(t)` patterns; `type_name` decoded from property).

---

## Round 3 pushbacks (RR-1 — RR-15) — LOCKED 2026-05-13

Round 3 closed implementation-level details + sub-loader composition + doc footprint.

### RR-1 — `IdentityRegistry.unregister()` availability.
**Pick: A.** Audit Phase 02 surface at implementation time. If `unregister()` exists as public method, use it. If missing, Phase 08 adds it additively (matches the Phase 04 / 06 pattern for adding public methods without state-file impact). Document in row's `Modules touched` after impl audit.

### RR-2 — `load_metagraph` internal streaming strategy.
**Pick: D.** `load_metagraph(client, mid, *, batch_size=None, identity=None, schema=None)`. Default `batch_size=None` → full-load every contained Graph (via `load_graph`). `batch_size=int` → uses `iter_load_graph` per contained graph + assemble. Self-documenting; opt-in. OEWN-scale callers pass `batch_size=10_000`.

### RR-3 — Override allow-list validation at instance load.
**Pick: A.** InstanceLoader validates each rehydrated instance's `overrides` against the Phase 06 per-subclass allow-list (P36 A). Offending overrides raise `PersistenceError` with the bad key surfaced. Substrate-side direct edits become loud failures, not silent corruption.

### RR-4 — Orphan template at instance load.
**Pick: B.** Log `_log.warning("orphan instance %r: template_id=%r missing in metagraph %r; skipping")` and skip the instance. Phase 06 cascade-on-graph-remove normally prevents this; an orphan at load = substrate corruption surfaced as a `verify` finding bucket. Loud warning + verify-side visibility.

### RR-5 — Class `MetagraphLoader` vs convenience function `load_metagraph`.
**Pick: B.** Ship BOTH. Class `MetagraphLoader(client)` with `.load(mid)` + `.refresh(mg, role)`; module-level convenience `load_metagraph(client, mid, *, batch_size=None, identity=None, schema=None)` = `MetagraphLoader(client).load(mid, batch_size=..., identity=..., schema=...)`. Symmetric with Phase 07 `load_graph()` function-style. Trivial duplication; serves both use cases.

### RR-6 — ADR-0124 implementation-references update.
**Pick: A.** Phase 08 amends ADR-0124 §Implementation references to actual paths: `mindsos_core/reconstruction/graph_loader.py::iter_load_graph` (function), `mindsos_core/reconstruction/metagraph_loader.py::MetagraphLoader.refresh` (method), `mindsos_core/reconstruction/metagraph_loader.py::MetagraphLoader.load` (method), module convenience `load_metagraph(client, mid)`. Plus `mindsos_instances/reconstruction/instance_loader.py::InstanceLoader.load_into` (observer subscriber). Phase 07 #45 precedent: ADR file edits within the consumer phase override Phase 06 P45 B.

### RR-7 — `load --metagraph M --to-json` sibling path.
**Pick: A.** Writes `~/.mindsos/metagraph-<name>.fromdb.json` (sibling; NEVER overwrites canonical `metagraph-<name>.json`). Direct Phase 07 P85 B precedent application.

### RR-8 — MetagraphLoader sub-loader composition.
**Pick: A.** MetagraphLoader is an orchestrator only. NO `_instance_loader` / `_xref_loader` handles. Sub-loaders subscribe via `after_load` observer (instance in Phase 08; xref in Phase 09 per RR-10). MetagraphLoader's responsibilities: anchor read → contained Graph reads (via `load_graph` / `iter_load_graph`) → MetaEdges → MetaHyperEdges → IntergraphEdges → IntergraphHyperEdges → fire `after_load(mg)`. ~80 LOC class.

### RR-9 — `_dispatch_after_load` dispatcher.
**Pick: A.** New helper `mindsos_core/_observers.py::_dispatch_after_load(observers, mg)`. Mirrors Phase 07 `_dispatch_after_persist` shape: per-observer exception isolation (one failing after_load observer logs + continues; doesn't tear down the load).

### RR-10 — Phase 09 XRefLoader architectural slot.
**Pick: A.** Phase 09 XRefLoader subscribes via `after_load` observer (same shape as Phase 08 InstanceLoader). MetagraphLoader stays orchestration-only. Pattern locked in Phase 08; Phase 09 inherits cleanly. Document as "Foreshadowing for Phase 09" in row.

### RR-11 — `inspect-state --metagraph M` drill-down.
**Pick: B.** Phase 08 `inspect-state` stays global. Per-metagraph drill-down deferred to Phase 11 (integrity scanner + schema migration territory).

### RR-12 — `load_graph` refactor to call `iter_load_graph`.
**Pick: A.** Phase 08 refactors Phase 07's `load_graph()` to internally call `iter_load_graph(client, gid, batch_size=None_sentinel) + assemble`. ADR-0124's "load() becomes a thin wrapper of list(iter_load(...))" claim honored. Single source of truth. RPB-1 A's "edges trail final batch" semantics make the refactor clean: `load_graph = assemble(iter_load_graph(client, gid, batch_size=None))` where `None` means "yield in a single batch."

### RR-13 — Test fixture additions.
**Pick: A.** Ship two new modules:
- `tests/_shared/metagraph_equality.py::assert_metagraphs_equal(mg1, mg2)` — walker for round-trip equivalence (used in load_metagraph + sync_metagraph CLI integration tests).
- `tests/_shared/large_graph_factory.py::make_large_graph_fixture(client, gid, n_nodes, *, edge_density)` — builder for N-node streaming fixtures.

Sentinel-paths grows accordingly (R4-14 A).

### RR-14 — `mindsos persistence` subapp help-text bump.
**Pick: A.** Help-text bumped Phase 07 → Phase 08; description mentions metagraph round-trip (`sync --metagraph M` + `load --metagraph M`). Mechanical.

### RR-15 — Phase 08 documentation footprint.
**Pick: A.** Five doc-footprint items:
1. **Amend** `docs/usage/core/persistence.md` — new verbs/flags + recipes (metagraph round-trip + refresh + streaming usage); `last_confirmed_phase: 08`.
2. **Amend** `docs/dev/internals/core.md` — NEW "Reconstruction layer" section with subsections (load_graph / iter_load_graph / MetagraphLoader / refresh / WAL recover-on-load / observer-driven instance load); `last_confirmed_phase: 08`.
3. **NEW** `docs/api/core/loaders.md` — full API reference for `load_graph` + `iter_load_graph` + `MetagraphLoader` + module function `load_metagraph` + `refresh` + 3 new exception classes; `last_confirmed_phase: 08`.
4. **Edit** `docs/decisions/adr/0124-streaming-loader-iter-load-and-refresh.md` — status flip Proposed → Accepted; signature amendment for `iter_load` → `iter_load_graph`; impl-refs update per RR-6 A.
5. **Append** `docs/changelog/CHANGELOG.md` — Phase 08 entry.

`mkdocs.yml` nav entry added for `docs/api/core/loaders.md`.

---

## Round 4 pushbacks (R4-1 — R4-16) — LOCKED 2026-05-13

Round 4 closed edge cases + mechanical bumps. The pushback well ran dry by R4-16.

### R4-1 — Edge primitive load ordering.
**Pick: A.** Locked sequence inside `MetagraphLoader.load` (also enforced in M12): recover() → anchor → contained Graphs → MetaEdges → MetaHyperEdges → IntergraphEdges → IntergraphHyperEdges → fire `after_load(mg)`. Endpoint-before-edge invariant preserved. Document in row.

### R4-2 — `refresh` empty-role + role-mismatch edge cases.
**Pick: D.** Empty-role (no graphs in mg with `role=$role`): `_log.warning("refresh: no graphs with role=%r in metagraph %r; no-op")` + no-op return. Role-mismatch (in-memory g.role differs from DB row's role for same gid): raise `RoleMismatchError` with both roles surfaced; corruption is loud. Tests cover both paths.

### R4-3 — Exception class strategy.
**Pick: A.** Phase 08 adds 3 new exception classes to `mindsos_core/exceptions.py`:
- `RefreshUnsafeError` — ADR-0124 §Constraint; class only, not raised in Phase 08 per PB-5.
- `WALReplayerMissingError` — per RPB-3 C; raised internally during `recover()`, narrow-caught by `load_metagraph`.
- `RoleMismatchError` — per R4-2 D; raised by `refresh` on DB role drift.

All inherit from `PersistenceError`. Generic read failures continue to use `PersistenceError`.

### R4-4 — `schema=None` kwarg forward-compat.
**Pick: B.** Phase 08 load surfaces accept `schema=None` as no-op kwarg (parity with Phase 07 `load_graph`). Documented "ignored at L1; L2 may consume in later phases." Drops nothing; tests verify no validation occurs.

### R4-5 — `load --metagraph M` stdout summary shape.
**Pick: A.** 9-line flat key:value format (mirrors Phase 07 P52 A):
```
Metagraph: <name>
Metagraph id: <mid>
Graphs: <N>
MetaEdges: <N>
MetaHyperEdges: <N>
IntergraphEdges: <N>
IntergraphHyperEdges: <N>
ElementInstances: <N>
CompositeInstances: <N>
```
`--json` opt-in for machine-readable output (mirror P52 A + P99 A).

### R4-6 — `verify --source=db --graph G --metagraph M` flag combination.
**Pick: A.** Typer mutually-exclusive constraint; exit 1 on combo (CLI usage error per Phase 07 P64 A exit-code split). Pattern: small wrapper in CLI handler that asserts `(graph is None) != (metagraph is None)` when `--source=db`.

### R4-7 — Identity-preservation contract test for `refresh`.
**Pick: A + C.** Two tests:
- (A) Explicit: capture `pre_id_mg = id(mg)`, `pre_id_reg = id(mg.identity)`; call `refresh(mg, role)`; assert both unchanged.
- (C) Downstream-ref-survives: external object holds `proxy = weakref.proxy(mg.identity)`; refresh; `proxy` still resolves (proves L2/L4 cached refs survive).

### R4-8 — WAL recover ordering in `load_metagraph`.
**Pick: A.** recover() runs FIRST (step 0 of load sequence). Locked sequence per M12 / R4-1. Test: register fake replayer; pre-insert uncommitted `:WALEntry` for mg; call `load_metagraph(client, mid)`; assert replayer fired before any read query.

### R4-9 — Design-log document structure.
**Pick: A.** Single `PHASE_08_DESIGN_LOG.md` (this file). No addendum sibling. Rounds 1-4 + Step 0 + lock table + cross-chat dependencies all in one document.

### R4-10 — Implementation-chat handoff prompt naming.
**Pick: B.** Overwrite existing `PHASE_08_NEXT_CHAT_PROMPT.md` with the implementation handoff after Round 4 lock. Design prompt's role ends here. Phase 07 precedent.

### R4-11 — `MetagraphLoader.__init__` constructor surface.
**Pick: A.** `MetagraphLoader(client)` minimal. No `identity` / `batch_size` / `schema` on the constructor; all kwargs are per-call (on `.load(mid, *, batch_size, identity, schema)` and `.refresh(mg, role, *, schema)`). Stateless orchestrator.

### R4-12 — `mindsos_core/reconstruction/__init__.py` exports.
**Pick: A.** Export 6 symbols:
- `load_graph` (Phase 07 — preserved; refactored internally per RR-12 to call iter_load_graph).
- `iter_load_graph` (NEW).
- `MetagraphLoader` (NEW).
- `load_metagraph` (NEW; module convenience function).
- `RefreshUnsafeError` (NEW; from `mindsos_core.exceptions`).
- (NEW: `WALReplayerMissingError` + `RoleMismatchError` re-exported from exceptions for caller convenience).

`__all__` populated explicitly.

### R4-13 — `mindsos_instances/__init__.py` re-exports.
**Pick: B.** `mindsos_instances/__init__.py` does NOT re-export `InstanceLoader` at top level. Deep-import only (`mindsos_instances.reconstruction.InstanceLoader`). `attach_registry` remains the canonical API; InstanceLoader is internal to the observer subscription.

### R4-14 — `tests/_shared/sentinel_paths.py` Phase 08 entries.
**Pick: A.** Eager-add every Phase 08 path (~15-20 entries: ~8 source files + 6-8 test files + 2 shared-fixture modules + 1 doc page). Per Phase 07 P25 A + `feedback_new_top_level_package.md`.

### R4-15 — Manifest bump.
**Pick: A.** `[mindsos] phase = "08"`, `version = "0.0.0+phase08"`. 3-package version-string parity per Phase 06 P62 A (`mindsos_cli`, `mindsos_core`, `mindsos_instances` all bump).

### R4-16 — Compose image tags.
**Pick: A.** `mindsos:phase08-prod` / `mindsos:phase08-test`. Doctor `_COMPOSE_IMAGE_RE` already accepts `phase\d{2}` form since Phase 05a; no regex extension needed.

---

## Consolidated lock table (59 picks)

| Pick | Surface area | Resolution |
|---|---|---|
| **M0** | State-file disposition | No JSON state-file bump |
| **M1** | v3 baseline disposition | Slim-port + glue |
| **M2** | Phase split | Single Phase 08 |
| **M3** | ADR re-litigation | Flip 0124 only; 0125 untouched |
| **M4** | Round count | 4 rounds (target was 3) |
| **M5** | Test budget | Uncapped (per user override) |
| **M6** | InMemoryClient unit policy | Call-recording for unit; integration for round-trip |
| **M7** | Fixture sharing | metagraph_equality + large_graph_factory |
| **M8** | Streaming CLI | Programmatic-only |
| **M9** | inspect-state drill-down | Global only; defer to Phase 11 |
| **M10** | Round-5 addendum | Not pre-budgeted |
| **M11** | Test fixture scale | 1K default + opt-in 10K `slow` |
| **M12** | Edge-primitive load order | Locked sequence |
| **M13** | Exception classes | 3 new (`RefreshUnsafeError`, `WALReplayerMissingError`, `RoleMismatchError`) |
| **M14** | Design-log structure | Single document, 4 rounds |
| **M15** | Impl-chat handoff naming | Overwrite existing prompt |
| **PB-1** | ADR-0125 territory | Strip; stays Proposed |
| **PB-2** | Loader shape | Function load_graph/iter_load_graph + class MetagraphLoader |
| **PB-3** | iter_load signature | Graph-scoped only |
| **PB-4** | Instance load arch | `register_after_load_observer` |
| **PB-5** | RefreshUnsafeError | Class only; no enforcement |
| **PB-6** | WAL first L1 consumer | recover-on-load in load_metagraph |
| **PB-7** | verify --source=db --metagraph M | Unblock |
| **PB-8** | sync --metagraph M CLI | Ship in Phase 08 |
| **PB-9** | load CLI shape | Mutex `--graph G | --metagraph M` |
| **PB-10** | Streaming CLI | Deferred |
| **PB-11** | Schema reattach | `schema_name` only; no auto-attach |
| **PB-12** | Memory budget test | Structural batch-size assert |
| **PB-13** | Round count | 3 (closed at 4) |
| **PB-14** | ADR-0124 acceptance | P27 C wording + impl-refs list |
| **RPB-1** | Cross-batch edges | Defer to final batch |
| **RPB-2** | refresh drop choreography | Proper `remove_graph()` API |
| **RPB-3** | recover() failure | Narrow-catch `WALReplayerMissingError` |
| **RPB-4** | sync-metagraph --replace | Refuses on deps |
| **RPB-5** | load_graph recovery | None; documented asymmetry |
| **RPB-6** | Legacy MetagraphSettings | Strip |
| **RPB-7** | Test budget | Uncapped |
| **RPB-8** | iter_load test methodology | Structural + equivalence + cross-batch |
| **RPB-9** | after_load dispatch | Single fire post-everything |
| **RPB-10** | iter_load + Intergraph | Intra-graph only |
| **RPB-11** | Round-5 addendum | Not pre-budgeted |
| **RPB-12** | Fixture size | 1K default + opt-in 10K |
| **RPB-13** | Integration density | InMemoryClient for unit |
| **RPB-14** | Read Cypher in builders | Stay inline |
| **RR-1** | IdentityRegistry.unregister | Audit + add if missing |
| **RR-2** | load_metagraph streaming kwarg | `batch_size=None` opt-in |
| **RR-3** | Override allow-list at load | Validate strict |
| **RR-4** | Orphan template at load | Log + skip + verify visibility |
| **RR-5** | Class + function dual | Ship both |
| **RR-6** | ADR-0124 impl-refs | Update in Phase 08 |
| **RR-7** | `load --metagraph M --to-json` | `metagraph-<name>.fromdb.json` sibling |
| **RR-8** | MetagraphLoader composition | Orchestrator only |
| **RR-9** | `_dispatch_after_load` | New helper with exception isolation |
| **RR-10** | Phase 09 XRefLoader | Via after_load observer |
| **RR-11** | inspect-state drill-down | Defer to Phase 11 |
| **RR-12** | load_graph refactor | Via iter_load_graph + assemble |
| **RR-13** | Test fixtures | metagraph_equality + large_graph_factory |
| **RR-14** | persistence help text | Bump + metagraph round-trip mention |
| **RR-15** | Doc footprint | 5 items (3 amend + 1 NEW + 1 changelog) |
| **R4-1** | Edge load order | Locked sequence |
| **R4-2** | refresh edge cases | Empty-role no-op; role-mismatch raise |
| **R4-3** | Exception classes | 3 new; reuse PersistenceError otherwise |
| **R4-4** | schema kwarg | No-op forward-compat |
| **R4-5** | load --metagraph summary | 9-line flat format |
| **R4-6** | --graph × --metagraph mutex | Typer constraint; exit 1 |
| **R4-7** | Identity-preservation test | Explicit + downstream-ref |
| **R4-8** | recover order | First (step 0) |
| **R4-9** | Design log structure | Single document |
| **R4-10** | Impl-chat handoff | Overwrite existing prompt |
| **R4-11** | MetagraphLoader constructor | `(client)` minimal |
| **R4-12** | reconstruction `__init__` exports | 6 symbols |
| **R4-13** | instances `__init__` re-export | No (deep-import only) |
| **R4-14** | sentinel_paths | Eager-add ~15-20 |
| **R4-15** | Manifest bump | phase=08, version=0.0.0+phase08 |
| **R4-16** | Compose tags | mindsos:phase08-{prod,test} |

---

## Convergence note

Round 4 §16 honest acknowledgment: pushback well is dry. Round 1 produced 14 picks; Round 2 produced 14 (1 cap reversal per user override on RPB-7); Round 3 produced 15 picks; Round 4 produced 16 picks (mostly closing edge cases + mechanical bumps).

User confirmed convergence with "I agree with all your suggestions… reanalyze the plan and list your push backs, if any, with options.... show me your choice…" pattern across 4 iterations. Each round's reversals smaller. Remaining unknowns are row-text-internal (exact Cypher queries inside MetagraphLoader methods, exact test names, exact `__all__` ordering). Those belong to implementation chat.

---

## User overrides

1. **RPB-7 — test budget**: user override 2026-05-13 — "caping the test number is not import... do as many as needed." Removed projection 85-115; Phase 08 uncapped per `feedback_test_budget_unlimited.md`.

No other user overrides. User agreed with each pass.

**Implicit precedent inherited from Phase 07:** the user's 2026-05-12 instruction "ADR decisions can be changed if decided in this chat" continues to apply — Phase 08 flips ADR-0124 (M3 A) and amends its body / impl-refs without deferring to Phase 38.

---

## Cross-chat dependencies

**Forward (Phase 08 produces):**

- 1 new module in `mindsos_core/reconstruction/metagraph_loader.py` (class `MetagraphLoader` + function `load_metagraph`).
- 1 modified module in `mindsos_core/reconstruction/graph_loader.py` (adds `iter_load_graph`; refactors `load_graph` to call it).
- 1 modified module in `mindsos_core/reconstruction/__init__.py` (exports 6 symbols).
- 1 new submodule in `mindsos_instances/reconstruction/__init__.py` + `instance_loader.py` (sibling package; observer subscriber).
- 1 modified module in `mindsos_instances/registry.py` (`attach_registry` extends to subscribe `after_load` observer; idempotent per Phase 06 P49 B helper).
- 1 modified module in `mindsos_core/_observers.py` (`_dispatch_after_load` helper).
- 1 modified module in `mindsos_core/models/metagraph.py` (`register_after_load_observer` method + `_after_load_observers` list + `_after_load_handles` registry).
- 1 modified module in `mindsos_core/exceptions.py` (3 new exception classes).
- 1 modified module in `mindsos_core/models/identity.py` (additive `unregister()` method if Step-0 audit finds it missing; otherwise no-op).
- 1 modified module in `mindsos_cli/commands/persistence.py` (3 CLI surface changes: `sync --metagraph M [--replace]`, `load --metagraph M [--to-json]`, `verify --source=db --metagraph M` unblock; mutex enforcement on `--graph G | --metagraph M` for both `load` and `verify`).
- 1 modified module in `mindsos_cli/app.py` (help-text bump per RR-14).
- 1 modified `mindsos_cli/manifest.toml` (`phase=08`, `version=0.0.0+phase08`).
- 1 modified `pyproject.toml` (version bump).
- 1 modified `Dockerfile` (comment lines + COPY `mindsos_instances/reconstruction/`).
- 1 modified `docker-compose.yml` (image tags `mindsos:phase08-*`).
- 3 new test-shared modules: `tests/_shared/metagraph_equality.py`, `tests/_shared/large_graph_factory.py`, plus sentinel-paths additions in `tests/_shared/sentinel_paths.py`.
- 6-8 new test modules under `tests/phase_08/`.
- 1 ADR flipped Proposed → Accepted (ADR-0124) with body amendments per PB-3 + PB-14 C + RR-6 A.
- 5 doc-footprint items per RR-15.

**Backward (Phase 08 consumes):**

- Phase 07 slim port at `halvim_mindsos/mindsos_core/persistence/` and `halvim_mindsos/mindsos_core/reconstruction/graph_loader.py`.
- Phase 07 `register_persist_observer` pattern (mirror for `register_after_load_observer`).
- Phase 07 `attach_registry(mg)` idempotent helper (extends to subscribe `after_load` observer per Phase 06 P49 B).
- Phase 07 `MetagraphRepository.persist` (programmatic side; Phase 08 wraps with CLI verb).
- Phase 07 5-bucket `verify_invariants(mg)` integrity scanner (Phase 08 unblocks `--source=db --metagraph M`).
- Phase 07 WAL `recover(client, mid)` (Phase 08 wires first L1 consumer in `load_metagraph`).
- Phase 06 `register_remove_observer` + `register_graph_added_observer` (refresh choreography uses proper `remove_graph()` API per RPB-2 A).
- v3 baseline at `/Layered Intelligence/mindsos_core/reconstruction/metagraph_loader.py` (slim-port source; XRef sub-loader + legacy `:MetagraphSettings` migration stripped).
- v3 baseline at `/Layered Intelligence/mindsos_instances/reconstruction/instance_loader.py` (slim-port source).
- ADR-0030 (Client protocol; Phase 08 doesn't change).
- ADR-0124 (Phase 08 flips Accepted; consumer ships).
- ADRs 0122 / 0123 / 0126 / 0127 (Phase 07 Accepted; Phase 08 inherits).
- ADR-0130 (`_props_json` on Metagraph; Phase 08 reader handles).
- ADR-0132 (instancing sibling package; Phase 08 reconstruction subpackage respects boundary).

**Unblocks:** Phase 09 (XRef — Phase 08 establishes after_load observer pattern; Phase 09 XRefLoader subscribes per RR-10 A). Phase 10 (Snapshot — `verify --source=db --metagraph M` now full-bandwidth). Phase 14 (L2 KL bootstrap — `load_metagraph` is the foundation for KL install_metagraph).

---

*End of PHASE_08_DESIGN_LOG.md. Implementation chat consumes this + the row text in PHASE_MAP.md §5 + the NEXT_CHAT_PROMPT.md handoff.*
