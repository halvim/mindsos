"""Phase 10 test tree — L1 Snapshot + soft-delete substrate + RemovalImpact + XRef setters.

Test tiers per design lock RR-5 (~85 files total post-P78 revision +
P82 + P86 + P87 adjustments):

* Snapshot tier (~8 files) — ``MetagraphSnapshot.of`` + ``.restore_into``
  + identity preservation + dirty-state capture + allow-list coverage
  (M3 + P84-corrected allow-list).
* Remove-graph tier (~10 files) — cascade × force × impact-non-empty
  matrix (8 cells per Step 9 sanity).
* Soft-delete setter tier (~20 files) — 4 setters × 5 element kinds.
* Iterator + loader filter tier (~13 files) — include_deprecated default
  False; ADR-0133 §"Default read filter" enforcement; load-then-iterate
  gotcha test.
* XRef setter tier (~6 files) — PX2 quartet + replay bypass + inverse
  index restoration.
* State-file v=5 tier (~6 files) — migration + round-trip + audit +
  B-09-T4 serializer/deserializer symmetry.
* WAL replay tier (~8 files) — 1 per new kind × 8 kinds.
* CLI patch tier (~4 files) — xref-list 10-field JSON; default columns
  when non-default; Phase 09 8-field dynamic regression guard; doctor
  parity.
* Shared classes tier (~10 files) — RemoveGraphBlockedError class shape;
  BlockedReason enum; SoftDeleteKind enum; _resolve_at helper;
  metagraph_equality walker extension; persist drain order; loader
  dirty-clear; snapshot-load gotcha; replayer module path.

Per Phase 10 PB-8 — fixture scale ≤10 elements per type; no slow tier.
"""
