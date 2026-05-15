# Phase 09 — Design Log

**Phase title:** L1 XRef (cross-metagraph refs).
**Locked:** 2026-05-14.
**Author chat:** design-refinement (this chat).
**Successor:** implementation chat on `phase-09` branch off `origin/main`.
**Row text:** `confirmation_docs/PHASE_MAP.md` §5 (replaces 7-line stub).
**Impl-chat handoff:** `confirmation_docs/PHASE_09_NEXT_CHAT_PROMPT.md` (overwrites design-side prompt; design-side preserved at `PHASE_09_DESIGN_CHAT_PROMPT.md`).

Mirror of `PHASE_08_DESIGN_LOG.md` structure: Step 0 audit + architectural distinction + M-series + numbered pushback rounds + lock table + cross-chat dependencies.

---

## Step 0 pre-design audit (resolved 2026-05-14)

Per PB17-B + PB19-B + PB13-C protocol. Audit gated Round 1.

**Phase 08 ship-state — ✅ PASS.**

- Tag `phase-08-confirmed` exists on `origin/main`.
- Squash-merge `d5b6e98 Phase 08 — L1 Reconstruction (#15)` on main.
- Post-tag hotfix `cc4d37f Phase 08 — B-08-T9: release.yml bash octal trap on NN=08` on main.
- Manifest `[mindsos] phase = "08"`, `version = "0.0.0+phase08"`.
- 3-package version-string parity at `0.0.0+phase08`.
- `confirmation_docs/PHASE_08_CONFIRMED.md` present + non-empty; 1374 + 2 skipped baseline.

**v3 XRef baseline sources at project-root — ✅ PASS.**

- `/Layered Intelligence/mindsos_core/models/xref.py` (74 LoC).
- `/Layered Intelligence/mindsos_core/persistence/xref_repository.py` (52 LoC).
- `/Layered Intelligence/mindsos_core/persistence/xref_migration.py` (87 LoC).
- `/Layered Intelligence/mindsos_core/reconstruction/xref_loader.py` (83 LoC).
- `/Layered Intelligence/mindsos_core/cypher/builders.py::build_create_xref` (~30 LoC). Persists `:XRef` node + `:XREF_OF` edge to source Metagraph anchor.

**halvim_mindsos has NO xref code yet — ✅ PASS.**

- `find halvim_mindsos -name '*xref*' -type f -not -path './.git/*'` returns 0.
- `mindsos_cli/commands/persistence.py:296` Phase 08 contains defensive `:XRef` query under try/except (Phase 09 closes the deferral).

**ADRs 0128 + 0142 status — both Proposed.**

- ADR-0128 at `/Layered Intelligence/docs/decisions/adr/0128-hybrid-xref-cross-metagraph-refs.md`. Layer L1. Amends 0016 + 0034.
- ADR-0142 at `/Layered Intelligence/docs/decisions/adr/0142-xref-cutover-for-ref-global.md`. Layer **L2** (not L1) — significant audit finding.

**Phase 08 observer infrastructure — ✅ PASS.**

- `Metagraph.register_after_load_observer` at `metagraph.py:420`.
- `_dispatch_after_load` with per-observer exception isolation at `_observers.py` (RR-9 A precedent).
- `attach_registry(mg)` extension subscribes after-load at `mindsos_instances/registry.py:317-332` (PB-4 A precedent).
- `MetagraphLoader.refresh` sets `mg._persist_client = self._client` before firing after_load (verified `metagraph_loader.py:324`). XRefLoader on refresh has client access.

**Phase 08 dependent-state check — anomaly identified.**

- `mindsos_cli/commands/persistence.py:296` defensive query uses `:XRef {metagraph_id: $mid}`.
- v3 baseline persists XRef with `source_metagraph_id`, NOT `metagraph_id`.
- Phase 09 closes this Phase 08 deferral per M11 (mirrors P60/P61 A inline-close pattern).

**State-file versions:** graph=4, metagraph=3, metagraph-schema=3, schema=2.

- `mindsos_cli/migrations/metagraph.py::CURRENT_VERSION = 3` (chain: v1→v2 schema_name + intergraph_edges; v2→v3 intergraph_hyperedges).
- Phase 09 bumps metagraph v=3 → v=4 adding `xrefs[]` array (M10).

**Manifest phase:** `[mindsos] phase = "08"`.

- Phase 09 bumps to `"09"` + version to `"0.0.0+phase09"`.

**Pre-existing `ref:global_*` data — 0 occurrences in `halvim_mindsos/tests/`.**

- 23 occurrences in `/Layered Intelligence/mindsos_core/` + `mindsos_knowledge/` (v3 root code). Migration is no-op on current halvim fixtures; still ships code for v3-data import + forward use.

**ADR transitive expansion (hop ≤ 2, stop ≤ 0020) — PB13-C.**

- ADR-0128 references: 0016 (foundational, STOP), 0034 (Accepted), 0118 (Server), 0122 (Accepted), 0123 (Accepted), 0048 (L2), 0130 (Proposed — flip candidate), 0030 (Accepted), 0021 (Accepted).
- ADR-0142 references: 0128, 0138 (Proposed, L2), 0143 (Proposed, L2), 0145 (Proposed, L3).
- Phase 09-affecting: 0128 (flip M0); 0130 (flip M7); 0132 (orthogonal — stay Proposed per M8).
- Server/L2/L3-side ADRs (0118 / 0125 / 0138 / 0142 / 0143 / 0145) stay Proposed.

**Cutover sizing (PB15-B numeric criteria):**

- (a) `ref:global` call-sites in shipped Phase 02-08 code: **0** (< threshold 5).
- (b) Persisted types touched: **1** (XRef itself; < threshold 2).
- (c) Migration script needed: YES (~60 LoC v3 source).

Result: **single Phase 09**; no 09a/09b split.

**Sign-off gate (PB14-B):** ADR amendments + cutover-sizing decision required → audit findings produced → user sign-off received before opening Round 1.

---

## Architectural distinction (load-bearing — read before any Phase 09 decision)

XRef is a **5th edge primitive**, separate from the 4 documented at `reference_mindsos_four_edge_primitives.md` (MetaEdge / MetaHyperEdge / IntergraphEdge / IntergraphHyperEdge):

- The 4 primitives connect graphs-or-nodes **within a single metagraph**.
- **XRef connects elements across metagraphs** (Local → Global, Local → Other-Local).

ADR-0128's hybrid model: intra-metagraph refs stay `ref:<role>` property strings (ADR-0016 retained); cross-metagraph refs become first-class `:XRef` rows in the source metagraph. Phase 09 ships the cross-metagraph primitive.

Anchoring: v3 baseline persists `:XRef` node + `:XREF_OF` edge to the **source Metagraph anchor** (NOT the source element). Reverse lookup is via the `(target_metagraph_id, target_id)` compound index, not via edge traversal. Edge anchors lifecycle (cascade on metagraph removal — Phase 10 work).

---

## Meta-plan locks (M-series) — pre-Round-1

### M0 — ADR-0128 disposition.

Flip Proposed → **Accepted** inline this phase with §Revisions log section (PB22-C). 5 amendments itemized per PB12-C cap (≤5 × ≤30 words each). Phase 07 chunk-7 + Phase 08 M3 A precedent.

### M1 — ADR-0142 disposition.

Stays **Proposed**. P09 ships only L1 commitment (migration job); L2 fallback (`MetagraphView.follow_ref`) ships P14; Server first-start hook ships P18+. ADR-0142 frontmatter `layer: L2` retained; acceptance-criteria amended to declare 3-commitment split.

### M2 — Anchor-edge name.

**`:XREF_OF`** — v3 baseline + repository docstring authoritative. ADR-0128 prose says `:HAS_XREF` (incorrect; amended per M0 §Revisions). Edge connects `:XRef → :Metagraph` (source anchor), not `:XRef → :Node`. Lifecycle role (forward cascade on metagraph removal); reverse lookup via property index alone.

### M3 — `target_stale` + `deprecated_at` fields.

**Keep both as inert v3-baseline data.** Field surface ≠ operation surface. Dataclass + builder + loader + `_CORE_XREF_FIELDS` all carry the fields verbatim from v3 source. Operations that SET these fields (`Metagraph.remove_graph(force=True)` for `target_stale`; soft-delete write path for `deprecated_at`) ship in Phase 10. Net-cost-cheapest path (0 deltas vs v3 source).

### M4 — Validation contract.

`add_xref(target_metagraph: Metagraph | None = None, ...)` kwarg shipped. When caller passes `target_metagraph`, validate target exists via `target_metagraph.identity.has(target_id)`; raise `XRefIntegrityError` on miss. When `target_metagraph=None`, accept the write as "soft" (no validation). `XRefIntegrityError` class lives in `mindsos_core/exceptions.py` inheriting from `PersistenceError`. Registry-hook path (server resolver) deferred to Phase 18+. PB24-B faithful to ADR-0128 §Validation paragraph.

### M5 — Cutover migration trigger surface.

**Programmatic-only** at P09 (`migrate_in_memory(mg, *, target_metagraph_id, default_ref_type="SPECIALISES")` callable). No CLI verb. Real consumer is Server first-start hook (P18+). Phase 07 P60 A precedent: programmatic-only at primitive phase; CLI verb lands when consumer demands.

### M6 — XRef CRUD CLI surface.

**Read-only `xref-list` only** (PB25-B). Verb: `mindsos persistence xref-list --metagraph M [--source-id SID] [--target-metagraph TMID] [--target-id TID] [--ref-type RT] [--json]`. No `xref-add` / `xref-remove` CLI in P09. Write verbs land when L2/L3 consumer surfaces them.

### M7 — ADR-0130 (property bag) disposition.

Flip Proposed → **Accepted** inline. Closes PHASE_MAP §7 Q4. `Metagraph.properties` already shipped at `metagraph.py:307`; XRef migration consumes it via `mg.properties["xref:migrated_at"]` flag.

### M8 — ADR-0132 (instancing sibling pkg) disposition.

Stays **Proposed**. Orthogonal to P09 XRef work; no opportunistic flip (cost-of-touching-things heuristic).

### M9 — Migration flag property key.

`mg.properties["xref:migrated_at"]` — split-the-difference between ADR-0128 prose (`xref:migrated_from_strings_at` — verbose) and v3 baseline (`server:xref_migrated_at` — wrong namespace; `server:` prefix implies Server-set but the L1 migration code sets it). ADR-0128 §Migration paragraph amended per M0 §Revisions.

### M10 — State-file disposition.

Bump metagraph state-file **v=3 → v=4** adding `xrefs[]` array. Mirrors Phase 05c `_v2_to_v3` `intergraph_hyperedges` pattern. Carries `feedback_state_version_audit_scope.md` cost (grep ALL `tests/` for `_state_version == 3` + `METAGRAPH_STATE_VERSION == 3`).

### M11 — Phase 08 dependent-state check repair.

Phase 09 patches `mindsos_cli/commands/persistence.py:296` from `:XRef {metagraph_id: $mid}` to `:XRef {source_metagraph_id: $mid}` (v3 baseline names; `source_metagraph_id` distinguishes from `target_metagraph_id`). Inline-close Phase 08 deferral; mirrors Phase 08 P60/P61 A pattern (close prior-phase deferrals during consumer phase).

### M12 — Round count target.

**3 rounds** (M-picks → PB → RPB → RR). Phase 05b/c primitive-rails cadence; narrower than Phase 08's 4 rounds. Addendum slot opens if late edge cases surface.

### M13 — Test budget.

**Uncapped** per Phase 08 RPB-7 user override (`feedback_test_budget_unlimited.md`). Inherited unconditionally.

### M14 — Doc footprint.

**4 items:** rewrite `docs/concepts/references.md` for hybrid model + NEW `docs/api/core/xref.md` + AMEND `docs/dev/internals/core.md` (XRef section) + APPEND `docs/changelog/CHANGELOG.md`. Rails-only phase; smaller doc surface than Phase 08's 5 items.

### M15 — Index inventory.

**4 new `:XRef` indexes**: `(id)`, `(source_metagraph_id)`, `(source_id)`, `(target_metagraph_id, target_id)`. Bootstrap grows 14 → 18. FalkorDB v4.18.3 grouping-per-label quirk (B-07-T4 carry): substring-check test, not row-count.

### M16 — WAL integration.

**Full WAL** for `add_xref` + `remove_xref`. Each call wraps in `with wal.entry(kind="xref_add"|"xref_remove", payload=...):` context manager. Phase 09 = first phase to register actual WAL replayers (Phase 08 shipped `recover()` as silent no-op). Recovery test ships (write → simulate crash via skipped commit → recover → verify XRef exists).

### M17 — `load --metagraph M` summary shape extension.

10-line flat summary (Phase 08 R4-5 A 9-line + `XRefs: N` insertion between `IntergraphHyperEdges` and `ElementInstances`). Additive breaking change; flagged in PHASE_MAP §Breaking changes; Phase 08 tests patched (mirror B-08-T1 dynamic-read pattern).

### M18 — XRefLoader subscription mechanism.

Observer subscription via `register_after_load_observer` per Phase 08 RR-10 A. Subscription site = new helper `mindsos_core/reconstruction/xref_loader.attach_xref_loader(mg)` mirroring `mindsos_instances.attach_registry`. Helper takes no `client` arg; observer reads `mg._persist_client` at fire time (transient set by `MetagraphLoader.load` + `.refresh` per Phase 08 line 226 + 324).

---

## Round 1 — Pushbacks (PB-1 .. PB-9) — LOCKED 2026-05-14

### PB-1 — Slim-port boundary inventory.

Verbatim from v3 + explicit Phase 07/08 substrate exception list. Verbatim surfaces: `XRef` dataclass (M3 fields retained), `XRefRepository.persist/remove`, `XRefLoader._fetch_xrefs` query, `xref_migration.migrate_in_memory` body (minus M9 flag rename), `_CORE_XREF_FIELDS` frozenset. Exception list: `:XREF_OF` cypher uses Phase 07 `build_create_xref` builder location convention; `build_create_xref` signature kw-only matches Phase 07/08 builder convention; FalkorDB v4.18.3 `CREATE INDEX IF NOT EXISTS` rejection (B-07-T1 carry); test scaffolding uses `tests/phase_NN/conftest.py` `falkor_client` re-export (B-08-T2 carry).

### PB-2 — `mg.iter_xrefs` filter semantics.

**AND across all passed filters** (unset = wildcard). Pythonic / SQL `WHERE` default; predictable composition. 4-filter combinatorial space: source_id × target_metagraph_id × target_id × ref_type.

### PB-3 — Round-trip walker extension shape.

**Both equality helpers ship:** `assert_metagraphs_equal` extended with XRef id-set + field-by-field on matched IDs (for persist/load round-trip), plus new sibling `assert_xref_contents_equal(xrefs1, xrefs2)` for content-tuple comparison (for migration tests where UUIDs differ between source and target).

### PB-4 — Migration callable parameterization.

V3-verbatim signature: `migrate_in_memory(mg, *, target_metagraph_id, default_ref_type="SPECIALISES")`. Caller supplies `target_metagraph_id` explicitly. No L1 sentinel for `GLOBAL_METAGRAPH_ID`; tests pass synthetic value; Server consumer (P18+) supplies real value.

### PB-5 — `xref-list` verb signature.

Full 4-filter parity with `iter_xrefs`: `mindsos persistence xref-list --metagraph M [--source-id SID] [--target-metagraph TMID] [--target-id TID] [--ref-type RT] [--json]`. Exit codes 0/1/2 per Phase 07 P64 A. Long-flag keyword arguments self-documenting; consistency with Phase 08 `--metagraph M` pattern.

### PB-6 — `add_xref` idempotency / dedup policy.

**No dedup** (v3-verbatim). Each `mg.add_xref(...)` mints fresh UUID4 → distinct row. Calling twice with same content args → 2 distinct XRefs. Caller responsibility to `iter_xrefs` first if dedup needed. Migration's per-XRef `already` check (v3 `xref_migration.py:63-69`) handles dedup at the only site where it matters.

### PB-7 — XRefLoader behavior on `MetagraphLoader.refresh`.

**Re-load all XRefs on refresh.** Refresh fires `_dispatch_after_load` → XRefLoader observer re-fires. Per Phase 08 R4-7 A identity preservation (node IDs preserved across refresh), XRef.source_id remains valid post-refresh. No selective-clear complexity (refresh-aware filtering).

### PB-8 — WAL replayer behavior contract.

**MERGE-based replayer** for `xref_add`: reads WAL payload + re-runs `build_create_xref(...)` (MERGE handles idempotency). `xref_remove` replayer: reads `{xref_id}` payload + runs `MATCH (x:XRef {id: $xid}) DETACH DELETE x` (idempotent). v3 `build_create_xref` already uses MERGE (`cypher/builders.py:415`).

### PB-9 — XRefLoader collision-safety on refresh.

**`XRefLoader.load_into(mg)` clears first.** Single-mode behavior: clears `mg.xrefs` + `_xrefs_by_source` + `_xrefs_by_target` + unregisters XRef IDs from `mg.identity` before re-populating from DB. Full-reset-on-every-fire semantic. No `MetagraphLoader.refresh` patch required (would have introduced cross-layer coupling Phase 08 RR-8 A deliberately avoided). ~5 LoC delta vs v3 verbatim. PB32 reversal: locked at A, not the originally-picked C.

---

## Round 2 — Pushbacks (RPB-1 .. RPB-8) — LOCKED 2026-05-14

### RPB-1 — WAL recovery ordering across multiple replayers.

**FIFO across kinds.** WAL entries replay in write-order (by `created_at` per Phase 07 `:WALEntry` schema) regardless of `kind`; each entry dispatches to its kind's replayer. Kind-grouping would invert causal sequences (remove-then-add → add-then-remove).

### RPB-2 — Migration callable's WAL interaction.

**Bare `mg.add_xref` calls; each inherits WAL crash safety per M16.** Migration of N legacy refs = N independent WAL entries. Crash mid-migration → `recover()` replays partial entries → re-run migration completes the rest (idempotent per ADR-0128 + v3 baseline flag).

### RPB-3 — `:XREF_OF` cascade contract on Metagraph removal.

**Forward-cascade only.** When Phase 10 ships `Metagraph` removal operations, `DETACH DELETE m` cascade-removes XRefs whose `source_metagraph_id = m.id` via `:XREF_OF`. XRefs whose `target_metagraph_id = m.id` (pointing INTO m) become dangling; Phase 10 handles reverse-dangling-XRef cleanup (sets `target_stale = True` per M3 inert field forward-compat). Phase 09 ships forward anchor only.

### RPB-4 — Migration trigger relationship to load sequence.

**No auto-trigger.** M5 lock: caller (test / Server P18+ / tester REPL) invokes `migrate_in_memory` explicitly after `load_metagraph`. P09 ships the callable + one test demonstrating explicit-call pattern. No `load_metagraph(migrate_legacy=True)` kwarg.

### RPB-5 — `xref-list` filter on `--target-metagraph` without `--target-id`.

**Trust FalkorDB v4.18.3 compound-index prefix matching.** `WHERE x.target_metagraph_id = $tm` against the `(target_metagraph_id, target_id)` compound index uses standard openCypher prefix-match semantics. No separate single-property index.

### RPB-6 — Test fixture scale.

Standard fixtures ≤ 10 XRefs (matches Phase 08 `cli08` size); migration stress 1K XRefs `@pytest.mark.slow` opt-in. Phase 08 RPB-12 B+C precedent.

### RPB-7 — Integration test density.

5-8 integration tests (`@pytest.mark.integration`) + 20-30 unit tests. Integration headlines: CRUD round-trip; migration; WAL replay; `xref-list` verb; cross-metagraph; state-file v=4 sync; identity preservation under refresh. Phase 08 ratio (6 + 32) is the proven scale.

### RPB-8 — ADR file edit chunking.

**Single chunk-N commit at project-root.** Covers ADR-0128 flip + 5 amendments + §Revisions section, ADR-0130 flip, ADR-0142 acceptance-criteria notes. One commit; Phase 07 chunk-7 precedent. Lands outside halvim_mindsos git tracking per Model C hybrid (`feedback_docs_source_of_truth.md`).

---

## Round 3 — Pushbacks (RR-1 .. RR-18) — LOCKED 2026-05-14

### RR-1 — WAL replayer payload shape.

`xref_add` payload = 10-field XRef dict; `xref_remove` payload = `{xref_id}`. Replayer body converts `deprecated_at` ISO string ↔ datetime on dispatch (Phase 06 instance precedent).

### RR-2 — WAL replayer registration site (superseded by RR-16).

Original pick: `bootstrap.py::register_wal_replayers(client)` called by `FalkorClient.__init__`. Reanalysis surfaced architecture mismatch (Phase 07 WAL is module-level singleton, not per-Client). Re-picked at RR-16.

### RR-3 — `XRefIntegrityError` parent class.

`PersistenceError`. Phase 08 R4-3 A 3-class precedent. PersistenceError is the L1 sentinel; no umbrella `XRefError` added (one occupant).

### RR-4 — Round-trip walker extension shape.

Two-function form: extend `assert_metagraphs_equal` for XRef id-set + field-by-field on matched IDs; new sibling `assert_xref_contents_equal` for content-tuple (migration tests). ~30 LoC delta to existing `tests/_shared/metagraph_equality.py`.

### RR-5 — `xref-list` verb signature (final).

`mindsos persistence xref-list --metagraph M [--source-id SID] [--target-metagraph TMID] [--target-id TID] [--ref-type RT] [--json]`. Exit codes 0/1/2 per Phase 07 P64 A.

### RR-6 — `xref-list` output format.

Rich table default + `--json` opt-in (Phase 07 P99 A `inspect-state` pattern). Columns: `xref_id` (first 8 chars per v3 `__repr__` precedent), `source_id` (first 8), `target_metagraph_id` (first 8), `target_role`, `target_id` (first 8), `ref_type`, plus `target_stale` + `deprecated_at` when set (M3 inert fields surfaced when non-default).

### RR-7 — State-file `_v3_to_v4` migration body.

```python
def _v3_to_v4(state: Dict) -> Dict:
    """Phase 08 → Phase 09: introduce ``xrefs``."""
    state["xrefs"] = state.get("xrefs") or []
    return state
```

Mirrors Phase 05c `_v2_to_v3` `intergraph_hyperedges` pattern verbatim. Idempotent.

### RR-8 — `xrefs[]` JSON serialization shape.

Plain dict per XRef: `{xref_id, source_metagraph_id, source_id, target_metagraph_id, target_role, target_id, ref_type, properties, target_stale, deprecated_at}`. `deprecated_at` serialized as ISO string per Phase 06 precedent; `null` when `None`. 10 keys; mirrors WAL `xref_add` payload shape (RR-1 symmetry).

### RR-9 — ADR-0128 §Revisions log content.

Single §Revisions section appended at bottom of ADR-0128 listing 5 amendments dated 2026-05-14, per PB12-C cap (≤5 × ≤30 words):

1. `add_xref(source_id: str, ...)`. Source is a stable id, not a Node/Edge/HyperEdge object.
2. Anchor edge name = `:XREF_OF` (to Metagraph anchor), not `:HAS_XREF` (to source element). Lifecycle role; reverse lookup via property index.
3. XRef dataclass retains 2 inert fields from v3: `target_stale: bool = False`, `deprecated_at: Optional[datetime] = None`. Setters ship in Phase 10.
4. Migration flag key = `mg.properties["xref:migrated_at"]` (not `xref:migrated_from_strings_at`; not v3's `server:xref_migrated_at`).
5. Validation: `add_xref(target_metagraph: Metagraph | None = None, ...)` kwarg. When passed, validate target exists; raise `XRefIntegrityError`. Soft when absent. Server-side registry hook deferred.

### RR-10 — Sentinel paths additions.

4 entries to `tests/_shared/sentinel_paths.py`: `mindsos_core/models/xref.py`, `mindsos_core/persistence/xref_repository.py`, `mindsos_core/persistence/xref_migration.py`, `mindsos_core/reconstruction/xref_loader.py`. New-files-only per `feedback_new_top_level_package.md` site 3.

### RR-11 — `tests/phase_09/conftest.py` `falkor_client` re-export (mechanical).

Pattern verbatim from Phase 08 B-08-T2: `from tests._shared.falkordb_fixture import falkor_client` at top of `tests/phase_09/conftest.py`. Integration tests in `tests/phase_09/` get the fixture without per-file imports.

### RR-12 — `mindsos_cli/migrations/metagraph.py` chain extension (mechanical).

Add `_v3_to_v4` function + append to `MIGRATIONS` list + bump `CURRENT_VERSION = 4`. Audit grep `_state_version == 3` + `METAGRAPH_STATE_VERSION == 3` across ALL `tests/` (per `feedback_state_version_audit_scope.md`).

### RR-13 — Cross-metagraph test fixture (mechanical).

New `tests/_shared/cross_metagraph_fixture.py::make_source_and_target_metagraphs() -> tuple[Metagraph, Metagraph]`. Used by 5-8 integration tests (RPB-7). Both metagraphs seeded with minimal graphs + nodes; function-scoped pytest fixture.

### RR-14 — `mindsos persistence` help text (mechanical).

Typer auto-generates from `xref-list` verb docstring. No manual help-string edits.

### RR-15 — `mkdocs.yml` nav (mechanical).

Add `docs/api/core/xref.md` entry under "API > Core" section. Mirrors Phase 08 `docs/api/core/loaders.md` addition.

### RR-16 — WAL replayer registration site (corrects RR-2).

Per-kind module owns its registration:

- `mindsos_core/persistence/xref_repository.py::register_xref_replayers(client)` registers `xref_add` + `xref_remove` replayers via `mindsos_core.persistence.wal.register_replayer(kind, callback)`.
- Thin central wrapper `mindsos_core/persistence/bootstrap.py::register_all_l1_replayers(client)` composes per-kind registration functions.
- `FalkorClient.__init__` calls `bootstrap(self)` + `register_all_l1_replayers(self)` after Phase 07 P2 A bootstrap.
- Phase 10/11 add `register_tombstone_replayers(client)` / `register_integrity_replayers(client)` parallel; wrapper grows.

Replayer body captures `client` via closure (replayer signature is `(payload: Dict[str, Any]) -> None` per Phase 07 `wal.py:56`; no client arg).

Tests use `clear_replayers()` between cases (Phase 07 precedent in `test_wal.py:14`).

### RR-17 — `MetagraphRepository.persist(mg)` extension.

Inline iteration: after persisting metagraph anchor + dependent state, `MetagraphRepository.persist` iterates `mg.xrefs.values()` and calls `XRefRepository(self._client).persist(xref)` per XRef. Intra-package coupling (XRef lives in `mindsos_core` proper); no after-persist observer indirection (which is justified for sibling-package `mindsos_instances` but not here). MERGE idempotency in `build_create_xref` handles redundant writes from path-1 (programmatic `add_xref`) then path-2 (bulk `MetagraphRepository.persist`).

### RR-18 — State-file deserializer populates `mg.xrefs` + inverse indexes.

Direct assignment: deserializer reads `xrefs[]` from state-file v=4, constructs `XRef` objects, assigns to `mg.xrefs` dict, manually rebuilds `mg._xrefs_by_source` + `mg._xrefs_by_target` inverse indexes. Bypasses `mg.add_xref` (which would trigger DB write). Inverse indexes built once at deserialization, not lazily. Mirrors Phase 05c/05d intergraph-primitive deserialization pattern.

---

## Lock table

### Pre-Round-1 (M-picks)

| ID | Decision |
|---|---|
| M0 | Flip ADR-0128 → Accepted; §Revisions log section appended. |
| M1 | ADR-0142 stays Proposed; L1 commitment only ships in P09. |
| M2 | Anchor edge `:XREF_OF` (to Metagraph anchor). |
| M3 | Keep `target_stale` + `deprecated_at` inert (v3 verbatim). |
| M4 | `target_metagraph` kwarg on `add_xref`; `XRefIntegrityError` shipped. |
| M5 | Programmatic-only migration callable. |
| M6 | Read-only `xref-list` CLI verb only. |
| M7 | Flip ADR-0130 → Accepted (closes §7 Q4). |
| M8 | ADR-0132 stays Proposed. |
| M9 | Migration flag key = `xref:migrated_at`. |
| M10 | Metagraph state-file v=3 → v=4 (add `xrefs[]`). |
| M11 | Patch Phase 08 dependent-state check (`metagraph_id` → `source_metagraph_id`). |
| M12 | 3-round target. |
| M13 | Test budget uncapped. |
| M14 | 4 doc-footprint items. |
| M15 | 4 new `:XRef` indexes (bootstrap grows 14 → 18). |
| M16 | Full WAL integration for `add_xref` / `remove_xref`. |
| M17 | 10-line `load --metagraph M` summary (additive breaking change). |
| M18 | XRefLoader subscribes via `register_after_load_observer`; helper `attach_xref_loader(mg)`. |

### Round 1 (PB)

| ID | Decision |
|---|---|
| PB-1 | Slim-port verbatim + explicit Phase 07/08 substrate exception list. |
| PB-2 | `iter_xrefs` filters AND-composed. |
| PB-3 | Two-function walker extension (id-set + content-tuple). |
| PB-4 | Migration callable v3-verbatim signature; caller supplies `target_metagraph_id`. |
| PB-5 | `xref-list` full 4-filter long-flag signature. |
| PB-6 | `add_xref` accepts duplicates; no dedup. |
| PB-7 | XRefLoader re-loads all XRefs on refresh (after_load re-fire). |
| PB-8 | MERGE-based WAL replayer for `xref_add`; DETACH-DELETE for `xref_remove`. |
| PB-9 | `XRefLoader.load_into` clears `mg.xrefs` + inverse indexes + unregisters IDs before re-populating. |

### Round 2 (RPB)

| ID | Decision |
|---|---|
| RPB-1 | WAL recovery FIFO across kinds. |
| RPB-2 | Migration inherits WAL crash safety via per-`add_xref` WAL entry. |
| RPB-3 | Forward-cascade only via `:XREF_OF`; reverse-dangling is Phase 10. |
| RPB-4 | No auto-trigger; migration is caller responsibility. |
| RPB-5 | Trust FalkorDB compound-index prefix matching for `--target-metagraph` without `--target-id`. |
| RPB-6 | ≤10 XRefs in standard fixtures; 1K `@pytest.mark.slow` opt-in stress. |
| RPB-7 | 5-8 integration tests + 20-30 unit tests. |
| RPB-8 | Single chunk-N ADR-file-edit commit at project-root. |

### Round 3 (RR)

| ID | Decision |
|---|---|
| RR-1 | WAL payloads: 10-field dict for `xref_add`; `{xref_id}` for `xref_remove`. |
| RR-2 | (Superseded by RR-16.) |
| RR-3 | `XRefIntegrityError(PersistenceError)`. |
| RR-4 | Two-function walker extension. |
| RR-5 | `xref-list` final signature. |
| RR-6 | Rich table default + `--json` opt-in. |
| RR-7 | `_v3_to_v4` single-step migration body. |
| RR-8 | 10-field JSON dict per `xrefs[]` entry; ISO datetime. |
| RR-9 | ADR-0128 §Revisions section with 5 amendments. |
| RR-10 | 4 sentinel-path entries. |
| RR-11 | `tests/phase_09/conftest.py` re-exports `falkor_client`. |
| RR-12 | Migration chain extension `_v3_to_v4` + `CURRENT_VERSION = 4`. |
| RR-13 | `tests/_shared/cross_metagraph_fixture.py`. |
| RR-14 | Typer auto-generates help text. |
| RR-15 | `mkdocs.yml` nav adds `docs/api/core/xref.md`. |
| RR-16 | Per-kind replayer module ownership; central `register_all_l1_replayers` wrapper. |
| RR-17 | `MetagraphRepository.persist` inline-iterates `mg.xrefs` for persistence. |
| RR-18 | Deserializer direct assignment + manual inverse-index rebuild. |

**Total: 54 picks** (19 M + 9 PB + 8 RPB + 18 RR; RR-2 superseded; 53 active locks).

---

## Cross-chat dependencies

### Inherited from Phase 08 (CASC-1)

- Tag `phase-08-confirmed` on `origin/main`; squash-merge `d5b6e98`; B-08-T9 hotfix `cc4d37f`.
- 1374 + 2 skipped in-container baseline.
- `Metagraph.register_after_load_observer` + `_dispatch_after_load` per-observer isolation.
- `MetagraphLoader.load` + `MetagraphLoader.refresh` set `mg._persist_client` transiently before firing after_load.
- 9-line `load --metagraph M` flat summary (extended to 10 lines per M17).
- `mindsos_cli/commands/persistence.py:264-301` `_metagraph_has_dependent_state` — Phase 09 patches `:XRef {metagraph_id: $mid}` → `{source_metagraph_id: $mid}` per M11.
- 14-index bootstrap (Phase 09 grows to 18 per M15).
- WAL `recover()` first L1 consumer in Phase 08; silent no-op without replayers (RPB-3 C). Phase 09 is FIRST phase to register actual replayers per M16 + RR-16.
- `pytest.mark.slow` + `pytest.mark.integration` markers (Phase 08 RPB-12 / RPB-13 precedent).
- `mindsos_instances.attach_registry(mg)` extension model (Phase 06 + 08); Phase 09's `attach_xref_loader(mg)` mirrors.
- `tests/_shared/metagraph_equality.py` + `tests/_shared/large_graph_factory.py` (Phase 08 RR-13 A); Phase 09 extends the equality helper + adds `cross_metagraph_fixture.py`.

### Project-root coordination (Model C hybrid; `feedback_docs_source_of_truth.md`)

- ADR file edits land at `/Layered Intelligence/docs/decisions/adr/`, outside halvim_mindsos git tracking. Single chunk-N commit per RPB-8 A.
- v3 source files at `/Layered Intelligence/mindsos_core/` + `mindsos_knowledge/` stay read-only. Slim-port copies into halvim_mindsos.

### Forward-coupling (Phase 10+ inherits)

- **Phase 10 (snapshot + soft-delete + RemovalImpact)** ships setters for M3 inert fields (`target_stale`, `deprecated_at`); ships reverse-dangling-XRef cleanup on Metagraph removal (RPB-3 A).
- **Phase 11 (cypher integrity scanner + schema migration)** extends `register_all_l1_replayers` per RR-16 with `register_integrity_replayers`; may extend XRef integrity rules in 5-bucket scanner.
- **Phase 14 (L2 KnowledgeLayer + MetagraphView)** ships ADR-0142 commitment 2: `MetagraphView.follow_ref()` consults XRef + `LegacyRefWarning` read-fallback.
- **Phase 18+ (Server)** ships ADR-0128 §Validation registry hook; ships ADR-0142 commitment 3 (first-start boot hook calling `migrate_in_memory`); flips ADR-0142 → Accepted when all 3 commitments shipped (M1).
- **Phase 33+ (L3 write capacities, ADR-0145)** ships ADR-0142 commitment 1 (new writes write XRef only via `KLWriteHandle.graph().add_xref(...)`).

### Test scaffolding (Phase 08 carry-forward)

- `tests/phase_09/conftest.py` re-exports `falkor_client` per B-08-T2 precedent.
- `tests/conftest.py` already registers `pytest.mark.slow` + `pytest.mark.integration` (Phase 07 + Phase 08).
- Step-0 audit at implementation chat: grep ALL `tests/` for `_state_version == 3` + `METAGRAPH_STATE_VERSION == 3` per `feedback_state_version_audit_scope.md` (M10 state-file bump triggers this).

### Compose + image tag (mechanical)

- `docker-compose.yml` image tags `mindsos:phase09-prod` / `mindsos:phase09-test`. Doctor `_COMPOSE_IMAGE_RE` regex `phase\d{2}` form unchanged (accepts `phase09`).
- Phase 04-v2 tag-regex audit checklist (`feedback_tag_regex_audit.md` 6 sites including B-08-T9 release.yml octal trap fix): no new amendments. Release CI safe (B-08-T9 permanent fix).
