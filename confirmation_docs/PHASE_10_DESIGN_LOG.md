# Phase 10 Design Log — L1 Snapshot + soft-delete substrate + RemovalImpact + XRef setters

> Authored 2026-05-15 during Phase 10 row-refinement chat. Captures the full design path: 6 pre-design pushback rounds + Step 0 audit + 4 design rounds (M / PB / RPB / RR). **64 active picks** locked. Implementation chat handoff: `PHASE_10_NEXT_CHAT_PROMPT.md`.

---

## Architectural distinction

Phase 10 closes three deferrals carried forward from earlier phases:

1. **Phase 09 P53 reversal** — XRef `target_stale: bool` + `deprecated_at: datetime | None` fields restored to the dataclass (Phase 09 dropped them as inert until setters shipped).
2. **Phase 09 RPB-3 deferral** — Reverse-dangling XRef cleanup setter ships (`mark_xref_stale`). Auto-firing trigger stays deferred to Server first-start hook (Phase 18+).
3. **ADR-0130 Graph-side acceptance** — Phase 09 accepted Metagraph-side only; Graph-side closes inline with snapshot as the in-phase consumer.

Plus four new feature surfaces:

4. **`MetagraphSnapshot.of(mg)` + `restore_into(mg)`** — slim-port from v3 (`/Layered Intelligence/mindsos_core/metagraph_snapshot.py`, 271 LoC). Per-attribute deep-copy + identity-preserving restore. Caller scope narrowed by ADR-0129 to release-ship rollback only; Phase 10 ships docstring + module-level deprecation note (no CI lint rule yet).
5. **`RemovalImpact` + `Metagraph.remove_graph(force, RemovalImpact return)`** — slim-port from v3 + raise `RemoveGraphBlockedError` on `force=False` + non-empty impact + drop `cascade` kwarg (always cascade incident meta-edges).
6. **Soft-delete substrate** — `deprecated_at` + `disputed_at` fields on Edge/HyperEdge/MetaEdge/MetaHyperEdge dataclasses + 20 setter methods on Graph/Metagraph quartet pattern. **No iterator filter pass** (deferred to Phase 11). Setters emit `DeprecatedFilterPendingWarning` once per process.
7. **8 new WAL replayer kinds** — 4 collapsed for edge-side soft-delete (`element_deprecate` / `element_undeprecate` / `element_dispute` / `element_undispute`) + 4 XRef-specific (`xref_mark_stale` / `xref_unmark_stale` / `xref_deprecate` / `xref_undeprecate`). Wrapper grows 2 → 10.

Phase 10 is **substrate-only** for soft-delete. The "looks broken" UX trap (setter mutates field; iterators don't filter) is defended by once-per-process `DeprecatedFilterPendingWarning` from each setter + loud documentation. Phase 11 ships the iterator + GraphLoader filter as a single signature change.

---

## Step 0 audit (11 probes; 2026-05-15)

1. **Phase 09 squash-merge on main + tag exists.** `PHASE_09_CONFIRMED.md` references `phase-09-confirmed` tag on main; squash-merge `abc659f`. CONFIRMED.
2. **v3 baseline files present at `/Layered Intelligence/mindsos_core/`.** `metagraph_snapshot.py` (271 LoC) CONFIRMED. `models/metagraph.py::RemovalImpact` + `remove_graph(*, cascade=True, force=False)` CONFIRMED. Soft-delete substrate present in 8 files per SOFT_DELETE_AUDIT_NOTE.md (with 5 documented defects SD1-SD5 to address at port).
3. **State-file v=4 literal grep.** `grep _state_version == 4|METAGRAPH_STATE_VERSION == 4|GRAPH_STATE_VERSION == 4` across `halvim_mindsos/tests/` = **0 hits**. Tests use dynamic `<kind>_migrations.CURRENT_VERSION` refs (B-05d-T1 pattern carried).
4. **Halvim `xref.py` deferred fields absence.** CONFIRMED (Phase 09 P53). 8 fields total; `target_stale` + `deprecated_at` absent. Phase 10 P53 reversal restores to 10 fields.
5. **`IdentityRegistry.clear()` exists in halvim.** CONFIRMED at `mindsos_core/models/identity.py:201`. Snapshot's `mg.identity.clear() + register()` path works as-is.
6. **CompositionalMetaEdge N3-D Dropped.** CONFIRMED at `halvim/mindsos_core/models/metagraph.py:35` comment "DROPPED entirely (N3-D + P3 lock)". No live class. D1 amendment to ADR-0133 strips the compositional clause; class survives via ADR-0148 (IntergraphEdge consumer).
7. **Schema constraint grep for `deprecated_at` / `disputed_at` keys.** Port-time reserved-key collision check. Recommended: implementation chat greps `tests/` for these property-bag keys (expect zero).
8. **WAL replayer wrapper signature audit.** Phase 09 P51/P61/P66 per-Client substrate accepts +8 registrations cleanly. Wrapper `register_all_l1_replayers(client)` composes `register_soft_delete_replayers(client)` + extended `register_xref_replayers(client)` (4 → 8 kinds). Implementation chat verifies.
9. **`_persist_client` access pattern audit.** Phase 09 transient field signature stable for Phase 10 setters. Implementation chat verifies.
10. **`CompositionalImmutableError` class usage audit in halvim.** D1-rev confirmation: class **survives** at `mindsos_core/exceptions.py:120`. `mindsos_core/__init__.py:24` comment "re-shipped from R3-B 05a strip; consumer = IntergraphEdge.compositional". ADR-0133 amendment-2 clarifies.
11. **ADR status table.** Six ADRs in scope:
    - 0027 Accepted (2026-04-22) → Accepted + §Revisions amendment-1.
    - 0028 Accepted (2026-04-22) → unchanged.
    - 0129 Accepted (2026-04-27) → unchanged (Phase 10 ships docstring + module-level note).
    - 0130 Accepted Phase 09 (Metagraph-side) → Accepted (full; Graph-side closure).
    - 0133 Proposed (2026-04-27) → Proposed + §Revisions amendments-1+2 (flips Phase 11 with filter pass).
    - 0135 Proposed (2026-04-27) → **Accepted** + §Revisions amendments-1+2+3.
    - Plus ADR-0128 amendment-3 (Phase 09 Proposed; flips Phase 14 with `MetagraphView.follow_ref` consumer).

---

## Pre-design pushback rounds (6 rounds)

Surfaced before M-picks. Sequence:

**Round 1 — initial brief critique** (10 pushbacks + 10 picks):
- A2 (6-ADR scope; not 4 from brief) + B2 (substrate-only soft-delete) + C1 (single row; revisit if scale demands) + D1 (strip CompositionalMetaEdge clause) + E1 (edge-only soft-delete per ADR-0133) + F1 (WAL-only `remove_graph` crash safety) + G1 (no summary line growth) + H1 (add audit notes to mandatory reads) + I1 (correct ADR filenames) + J2 (state-file bump covers all soft-delete carriers).

**Round 2 — operational refinements** (8 pushbacks + 9 picks):
- K1 (return-only `remove_graph`; no raise) + L1 (hard signature change for `remove_graph`) + M2 (4 collapsed WAL kinds for soft-delete) + N1 (snapshot allow-list explicit per-attribute) + O1 (reverse-dangling setter only; trigger Server-phase) + P1 (`DeprecatedFilterPendingWarning`) + Q (defer ADR-0129 lint rule) + R (ship `incoming_ref_properties` O(N) scan as documented gotcha) + S (consolidate MEMORY.md before chat-end).

**Round 3 — secondary refinements** (5 pushbacks + 12 picks):
- T1 (defer ADR-0130 Graph-side; later overridden by audit) + AA1 (drop `cascade` kwarg; later reframed by audit) + BB1 (no CLI verb for soft-delete in Phase 10) + V3 (explicit per-attribute snapshot restore semantics) + DD2 (consolidate MEMORY.md now, not chat-end) + EE/FF/GG/HH/II/JJ/KK (lower-priority items locked).

**Round 4 — Step 0 audit + audit-driven overrides** (5 pushbacks + 6 picks):
- Audit findings: v3 baseline files EXIST (Round-1 #2 false claim); v3 baseline `remove_graph` RAISES not returns (overrides K1 → PA1); v3 `cascade=True` semantics is auto-cascade-meta-edges not tombstone control (reframes AA1 → PB1); v3 snapshot already handles `Graph.properties` (overrides T1 → T-rev.A; ADR-0130 scope returns to 6). SD defects 1-3 fix at port; SD4 N/A; SD5 deferred. PT1 (top-level snapshot path) + PK1 (strip `_piggyback`).

**Round 5 — implementation-detail follow-ups** (2 load-bearing + 4 clarifications):
- RA1 (`include_deprecated` parameter NOT shipped in Phase 10) + RB1 (snapshot captures `_xrefs_dirty`) + RC (setter matrix lock) + RD (8 doc surfaces) + RE (schema reserved keys) + RF (IdentityRegistry.clear() docstring drift).

**Round 6 — final pre-M-pick refinements** (3 load-bearing + 1 ADR-text clarification):
- PX2 (XRef quartet API symmetric to edge primitives — `mark_xref_stale` + `unmark_xref_stale` + `deprecate_xref` + `undeprecate_xref`; 4 XRef setters not 2) + PY1 (`at: datetime | None = None` parameter where None → now() at write time; v3 Metagraph overload-style rejected) + PZ1 (per-step WAL entries on `remove_graph(force=True)`) + D1-rev (ADR-0133 amendment-2 clarifies `CompositionalImmutableError` class retained per ADR-0148).

**Total setter count after Round 6:** 20 (8 Graph + 8 Metagraph + 4 XRef). **WAL replayer kinds:** 8 new.

---

## Design rounds (M / PB / RPB / RR)

### Round 1 — M-picks (24 picks: M0–M24)

ADR posture + scope + signatures + persistence + tests + tooling. See PHASE_MAP §5 Phase 10 row "Locked decisions" section for full text. Key open option resolved: **M17b** (inline WAL + DB write when `_persist_client` set; else mark `_soft_delete_dirty`).

### Round 2 — PB-picks (10 picks: PB-1..10)

Strategic refinements:

- PB-1: Slim-port boundary (4 strips + 2 additions; ~280 LoC).
- PB-2: Setter `at` parameter convention; `_resolve_at` helper; `datetime.now(timezone.utc)` modernization.
- PB-3: No new observer hook for soft-delete (PB-3a). Open: option-list. Lock: a.
- PB-4: Per-method cypher builders (PB-4a; 22 builders). Open: option-list. Lock: a.
- PB-5: `_compute_removal_impact` in-memory only (PB-5a). Open: option-list. Lock: a.
- PB-6: `MetagraphLoader.load` clears `_soft_delete_dirty` (PB-6a). Open: option-list. Lock: a.
- PB-7: Snapshot ↔ MetagraphLoader.load gotcha documented (no code change).
- PB-8: Test fixture scale ≤10 per type; no stress tier.
- PB-9: Tests assert by KEY for state-file v=5.
- PB-10: All 20 setters return mutated element dataclass.

### Round 3 — RPB-picks (11 picks: RPB-1..11)

Cross-cutting:

- RPB-1: WAL replayer body bypasses public setter; no warning fires on replay.
- RPB-2: WAL replay FIFO across 8 new kinds by `created_at`.
- RPB-3: `_v4_to_v5(state)` body shape: explicit per-item walk; idempotent.
- RPB-4: `_soft_delete_dirty: Dict[str, Set[str]]` keyed by element kind.
- RPB-5: `MetagraphRepository.persist(mg)` drain order: edges → hyperedges → metaedges → metahyperedges → xrefs.
- RPB-6: Test ratio ~55-60 unit + ~12-15 integration = ~70 files (3:1).
- RPB-7: Single chunk-10 ADR commit at project-root (5 ADR file edits).
- RPB-8: Sentinel-path entries: 5 new (snapshot module + 4 doc pages).
- RPB-9: Step 0 audit probe inventory: 11 probes.
- RPB-10: `RemoveGraphBlockedError(CoreError)` shape; sibling to Phase 09 `XRefIntegrityError`.
- RPB-11: `_soft_delete_dirty` joins snapshot allow-list (M3 extension).

### Round 4 — RR-picks (19 picks: RR-1..19)

Fine-grained:

- RR-1: WAL payload shapes per kind (8 kinds).
- RR-2: Setter docstrings reference Phase 11 filter pass.
- RR-3: `DeprecatedFilterPendingWarning` class shape + module-level `simplefilter('once', ...)`.
- RR-4: `metagraph_equality.py` walker extension + `assert_soft_delete_state_equal` helper.
- RR-5: Test file structure flat at `tests/phase_10/` (~70 files; tiers enumerated).
- RR-6: Phase 09 `xref-list` patched 8 → 10 fields.
- RR-7: Migration body locations (`mindsos_cli/migrations/metagraph.py` + `graph.py`).
- RR-8: JSON shape (ISO-8601 strings + bool + null).
- RR-9: ADR §Revisions format (7 amendments total).
- RR-10: `tests/phase_10/conftest.py` re-exports `falkor_client`.
- RR-11: Doctor parity-against-manifest assertions.
- RR-12: State-file CURRENT_VERSION audit scope.
- RR-13: `tests/_shared/soft_delete_fixture.py` NEW.
- RR-14: Typer help-text auto-generation.
- RR-15: `mkdocs.yml` nav adds 4 entries.
- RR-16: Per-kind replayer module ownership; NEW `mindsos_core/persistence/soft_delete.py` (RR-16a; no class). Open option resolved.
- RR-17: `MetagraphRepository.persist(mg)` drain extension.
- RR-18: State-file deserializer extension.
- RR-19: State-file serializer extension.

---

## Locked picks table (consolidated)

| Round | Pick ID | Topic | Resolution |
|-------|---------|-------|------------|
| Pre-design | A2 | ADR scope | 6 ADRs (later returns to 5 effective via T1 → T-rev.A reversal) |
| Pre-design | B2 | Soft-delete depth | Substrate-only Phase 10; filter Phase 11 |
| Pre-design | C1 | Split or single row | Single row |
| Pre-design | D1 | CompositionalMetaEdge clause | Strip from ADR-0133; class retained per ADR-0148 (D1-rev) |
| Pre-design | E1 | Soft-delete scope | Edge-only per ADR-0133 |
| Pre-design | F1 | `remove_graph` rollback | WAL-only |
| Pre-design | G1 | Summary line growth | None |
| Pre-design | H1 | Audit notes in mandatory reads | Added |
| Pre-design | I1 | ADR filename corrections | Applied |
| Pre-design | J2 | State-file bump scope | All soft-delete carriers; v=4 → v=5 both kinds |
| Pre-design | K1 → PA1 | `remove_graph(force=False)` posture | Raise `RemoveGraphBlockedError` (overrides K1 return-only) |
| Pre-design | L1 | `remove_graph` signature | Hard change |
| Pre-design | M2 (Round-2) | WAL replayer kinds | 4 collapsed for soft-delete + 4 XRef = 8 |
| Pre-design | N1 | Snapshot deep-copy | Explicit allow-list |
| Pre-design | O1 | Reverse-dangling trigger | Setter only; trigger Server-phase |
| Pre-design | P1 | `DeprecatedFilterPendingWarning` | Once per process |
| Pre-design | Q | ADR-0129 lint rule | Defer; ship only deprecation warning |
| Pre-design | R | `incoming_ref_properties` scan | Slow + documented |
| Pre-design | S → DD2 | MEMORY.md consolidation | Before Step 0 audit |
| Pre-design | T1 → T-rev.A | ADR-0130 Graph-side | Accept (consumer = snapshot) |
| Pre-design | AA1 → PB1 | `cascade` kwarg | Drop kwarg; always cascade meta-edges |
| Pre-design | BB1 | Soft-delete CLI | None in Phase 10 |
| Pre-design | V3 | Snapshot restore semantics | Per-attribute deep-copy + identity-preserving |
| Pre-design | EE | ADR-0027 amendment shape | §Revisions section |
| Pre-design | FF | `_v4_to_v5` body | Explicit per-item walk |
| Pre-design | GG | `disputed_at` ship | Yes (symmetric with `deprecated_at`) |
| Pre-design | HH | Warning fires once per process | `simplefilter('once', ...)` |
| Pre-design | II | Snapshot CLI | None; `docs/dev/internals/snapshots.md` not `docs/usage/core/` |
| Pre-design | JJ | Net-new flag | Partial |
| Pre-design | KK | Test footprint | ~70 files |
| Pre-design | RA1 | `include_deprecated` parameter | NOT shipped Phase 10 |
| Pre-design | RB1 | Snapshot captures `_xrefs_dirty` | Yes |
| Pre-design | RC | Setter matrix | 20 setters (8 Graph + 8 Metagraph + 4 XRef) |
| Pre-design | RD | Doc footprint | 8 surfaces |
| Pre-design | RE | Schema reserved keys | `deprecated_at` + `disputed_at` added |
| Pre-design | RF | IdentityRegistry.clear() docstring | Amend at port |
| Pre-design | PX2 | XRef setter API | Quartet (mark/unmark stale + deprecate/undeprecate) |
| Pre-design | PY1 | `at` parameter convention | None → now() at write time |
| Pre-design | PZ1 | `remove_graph(force=True)` WAL | Per-step entries |
| Pre-design | D1-rev | ADR-0133 amendment-2 | Strip clause; class retained per ADR-0148 |
| Pre-design | PT1 | Snapshot path | `mindsos_core/metagraph_snapshot.py` top-level |
| Pre-design | PK1 | `_piggyback` mechanism | Strip at port |
| M0..M24 | — | M-picks | See PHASE_MAP row |
| PB-1..10 | — | PB-picks | See PHASE_MAP row |
| RPB-1..11 | — | RPB-picks | See PHASE_MAP row |
| RR-1..19 | — | RR-picks | See PHASE_MAP row |

**Total active picks:** 64 design picks + ~40 pre-design pushback decisions = ~100 decisions documented.

---

## Cross-chat dependencies (forward-coupling)

- **Phase 11** — owns iterator/loader `include_deprecated` filter pass. Closes ADR-0133 acceptance. Removes `DeprecatedFilterPendingWarning` class. Adds soft-delete CLI verbs. May extend WAL replayer wrapper if new kinds ship.
- **Phase 14** — ships ADR-0142 commitment 2 (`MetagraphView.follow_ref` walking XRefs + respecting `target_stale`). FLIPS ADR-0128 Proposed → Accepted at end of Phase 14.
- **Phase 18+** — ships ADR-0129 release_update snapshot bracketing + ADR-0142 commitment 3 (Server first-start hook fires `mark_xref_stale` on archived target detection). Ships ADR-0129 CI lint rule (`grep MetagraphSnapshot.of outside mindsos_server/`).
- **Phase 33+** — ships ADR-0142 commitment 1 (L3 capacities write XRef + respect `target_stale` semantics per ADR-0145).

## Cross-chat dependencies (backward — Phase 09 inheritance closed)

- ✅ Phase 09 P53 — XRef `target_stale` + `deprecated_at` fields restored.
- ✅ Phase 09 RPB-3 — reverse-dangling cleanup setter ships (`mark_xref_stale`); auto-trigger still deferred to Server.
- ✅ Phase 09 M7 (ADR-0130 §7 Q4) — Graph-side property bag accepted via snapshot consumer.
- ✅ Phase 09 ADR-0128 amendment-3 — clarified that "cleanup" means setter exists for upper layers; firing trigger lives in Server.

## Carry-forward open items (NOT closed Phase 10)

- ADR-0128 stays Proposed until Phase 14.
- ADR-0133 stays Proposed until Phase 11.
- ADR-0142 stays Proposed until P14 + P18+ ship commitments 2 + 3.
- ADR-0129 release_update bracketing follow-up PR (Phase 18+).
- ADR-0129 CI lint rule (Phase 18+ or whichever phase introduces non-server callers).
- L2 `MetagraphView.follow_ref` (Phase 14).
- L3 write capacities producing XRefs (Phase 33+).
- Snapshot persistence to disk (out of scope; ADR-0028 explicit).

---

## Implementation chat handoff

See `confirmation_docs/PHASE_10_NEXT_CHAT_PROMPT.md` for the prompt body. The implementation chat:

1. Verifies Step 0 audit probes 7–10 (schema constraint grep + WAL wrapper signature + `_persist_client` access pattern + `CompositionalImmutableError` class usage).
2. Audits `mg.remove_graph(` callsite count in halvim (19 files identified at row-design time; signature change is breaking).
3. Surveys ~25-step implementation order following Phase 09 cadence.
4. Performs tester confirmation in same chat per Phase 09 precedent.
5. Files any in-flight pushbacks (P67+ slot reserved per Phase 09 P50-P66 pattern).
6. Records hotfixes (B-10-T*) for any in-container regressions.
7. Files new feedback memories at chat-end for any new audit classes that surface.

---

*End of Phase 10 design log. 2026-05-15.*
