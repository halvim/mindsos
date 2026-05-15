"""Phase 09 — L1 XRef (cross-metagraph refs).

Tests for the slim-port XRef primitive + WAL-wrapped repository +
clear-first loader + per-Client replayer registration + state-file
v=4 + xref-list CLI + migration callable. Lock list:

* M0 — ADR-0128 stays Proposed; flips Accepted in P14 per P50.
* M2 — Anchor edge :XREF_OF (to source Metagraph anchor).
* M3 + P53 — DROP target_stale + deprecated_at fields until P10.
* M4 + P59 — target_metagraph kwarg validates BEFORE WAL entry opens.
* M5 — programmatic-only migration callable.
* M6 — read-only xref-list CLI verb only.
* M7 — flip ADR-0130 Accepted (item H — adds xref: to namespacing).
* M9 — flag key xref:migrated_at (renames v3 server:xref_migrated_at).
* M10 — state-file metagraph v=3 → v=4 (adds xrefs[]).
* M11 — patch _metagraph_has_dependent_state metagraph_id → source_metagraph_id.
* M15 — 4 new :XRef indexes (bootstrap 14 → 18).
* M16 — full WAL integration on add_xref/remove_xref (per-Client replayer).
* M17 + P52 — replace 9-line summary with structured Dependent state: line.
* M18 — XRefLoader subscribes via attach_xref_loader(mg) helper.
* PB-2 — iter_xrefs filters AND-composed.
* PB-6 — add_xref accepts duplicates (no dedup).
* PB-7 + PB-9 — refresh re-fires after_load → loader clears + reloads.
* PB-8 — MERGE-based xref_add replayer; DETACH DELETE xref_remove replayer.
* RPB-1 — WAL recovery FIFO across kinds.
* RPB-2 — migration inherits WAL crash safety per add_xref.
* RPB-7 — 5-8 integration tests + 20-30 unit tests (≥25 file target).
* RR-3 — XRefIntegrityError(PersistenceError).
* RR-4 — assert_metagraphs_equal extension + assert_xref_contents_equal sibling.
* RR-7 — _v3_to_v4 single-step migration.
* RR-8 — 8-field xrefs[] JSON shape (sorted by xref_id).
* RR-11 — conftest.py re-exports falkor_client.
* RR-13 — make_source_and_target_metagraphs helper.
* RR-16 — per-kind replayer module ownership.
* RR-17 — MetagraphRepository.persist drains _xrefs_dirty.
* RR-18 — state-file deserializer direct-assign + manual inverse-index rebuild.
* P51 + P61 + P66 B — per-Client replayer registration.
* P54 — dirty-tracking; persist only writes dirty entries.
* P55 — refresh clears _xrefs_dirty alongside mg.xrefs.
* P57 — XRef dataclass kw_only=True.
* P62 — recover() raises WALReplayerMissingError on unknown kinds.
* P63 — xref-list direct-DB query (no load_metagraph fire).
* P64 — deserializer leaves _xrefs_dirty empty.
"""
