---
title: MetagraphSnapshot scope narrowed to release-ship
status: Accepted
date: 2026-04-27
layer: L1
amends: [0027, 0028, 0007]
---

# ADR-0129: `MetagraphSnapshot` scope narrowed to release-ship

**Status:** Accepted (2026-04-27 — module docstring on `mindsos_core.metagraph_snapshot` reflects the narrowed scope; KL drops snapshot for ordinary writes and uses the WAL graph from ADR-0122 instead)

**Date:** 2026-04-27

**Amends:** ADR-0027 (snapshot mutate-in-place — retained, scope narrowed), ADR-0028 (snapshot not serialisable — retained), ADR-0007 (Server-layer original use — Superseded by ADR-0118 + this ADR).

**Related:** ADR-0118 (per-user transactional promotion — narrows snapshot's role), ADR-0122 (WAL graph — replaces snapshot for ordinary multi-statement writes).

## Context

ADR-0027 introduced `MetagraphSnapshot.of(mg)` and `restore_into(mg)` as a Core helper for in-memory rollback during multi-statement operations. ADR-0007 used it for server-layer cross-user atomic promotion rollback. ADR-0028 made snapshots in-process-only (not serialisable).

The pivot (ADR-0118) replaces cross-user atomic promotion with per-user transactional `propose_for_promotion` plus release-boundary atomic `release_update`. Per-user transactional ops are bounded to a single user's Local + the pending-Global write; ADR-0122's WAL graph handles their rollback. The release-ship operation alone needs `MetagraphSnapshot` — for the canonical-Global rollback case.

Today's docs are inconsistent: ADR-0007 still describes the snapshot as the multi-Local rollback mechanism; ADR-0118 says the snapshot use is narrowed; KL still imports and uses snapshot for its own writes. The ADR layer hasn't reflected the consolidated model.

## Decision

Narrow `MetagraphSnapshot` to **release-ship only**. Specifically:

### What's retained

`MetagraphSnapshot` as a Core primitive remains. ADR-0027's contract (mutate-in-place) and ADR-0028's contract (in-process only, not serialisable) are unchanged.

### What's narrowed

**The snapshot's caller-side use.** Document and enforce:

- **Sole supported caller in v1: `mindsos_server.release.release_update`.** Used to snapshot canonical Global before the pending → canonical swap; restore on swap failure.
- **KL stops using `MetagraphSnapshot`.** KL's `propose_for_promotion` (per ADR-0118) uses WAL graph (per ADR-0122) for in-flight rollback.
- **L3 doesn't use `MetagraphSnapshot`.** Capacity-state writes are single-graph and use idempotent MERGE (per ADR-0023).
- **L4 doesn't use `MetagraphSnapshot`.** Confidence updates are per-property writes; no multi-statement rollback need.
- **L5 doesn't use `MetagraphSnapshot`.** Instance creation is additive; no rollback need.

### Public API surface

`MetagraphSnapshot` stays in `mindsos_core` and is exported. Documentation explicitly marks it as **server-layer-internal**:

```python
# mindsos_core/__init__.py — module docstring update:
"""
...
MetagraphSnapshot is exported but is intended for server-layer release-ship rollback only.
Other callers should use the WAL graph (ADR-0122) for multi-statement write safety.
"""
```

Static-analysis lint rule (added to `tests/unit/test_layer_isolation.py`): grep for `MetagraphSnapshot.of(` outside `mindsos_server/` raises a CI error in v2 (after the migration window). v1 emits a `DeprecationWarning` from `MetagraphSnapshot.of` when called from `mindsos_knowledge`, `mindsos_capacity`, `mindsos_intelligence` (pkg detected via `inspect.stack()`).

### Coordinated migrations

- **KL's `kl.promote()`** (the legacy method retained with `DeprecationWarning` per ADR-0118 §6.1) — leaves snapshot use as-is during transition. The slice's new `promotion_v2.py` does NOT use snapshot.
- **KL's tests in `tests/unit/knowledge/test_promotion.py`** — the `MetagraphSnapshot` fixture stays for the legacy promote tests; new pivot tests don't reference snapshot.
- **Server's `release.release_update`** (per pivot slice) — the slice doesn't yet bracket the FalkorDB write in a snapshot. Per ADR-0118 §"Decision" §2, this snapshot bracketing is a follow-up after audit gate (ADR-0115) lands. This ADR locks the architectural commitment that the bracketing belongs in `release_update`, not elsewhere.

### Status changes

- **ADR-0007:** flips to **Superseded** (banner already says supersession-in-progress; flips fully when this ADR's coordinated changes ship).
- **ADR-0027:** retained Accepted, with a note added pointing to this ADR.
- **ADR-0028:** retained Accepted, with a note added pointing to this ADR.

## Rationale

The split between (a) per-user transactional ops with WAL rollback and (b) release-ship with snapshot rollback maps to two genuinely-different rollback patterns:

- **Multi-statement write safety on FalkorDB** (no transactions): WAL pattern (ADR-0122) — append intent, apply, commit. Survives crashes.
- **Single all-or-nothing in-process state swap** (canonical → pending swap): in-memory deep-copy + restore. Doesn't need crash safety because release-ship is bounded to a single critical section under `RELEASE_SHIP_LOCK`; if the server crashes mid-ship, restart re-attempts the ship from scratch.

The narrowing is honest: snapshot was over-applied because it was the only rollback tool. WAL fills the multi-statement gap; snapshot retains its legitimate niche.

## Consequences

**Good:**

- Two rollback patterns by use case; each fits its problem.
- KL surface simplifies: no longer manages snapshot lifecycle for ordinary writes.
- The MetagraphSnapshot module's invariants (mutate-in-place, identity preservation) only need to hold for the single caller, simplifying future refactors.
- Static-analysis lint catches drift (snapshot use outside server).

**Tradeoffs:**

- Migration window: KL's legacy `kl.promote()` keeps using snapshot during the transition. Two rollback mechanisms coexist for one or two release cycles.
- The "deprecated when called from non-server packages" warning is heuristic (uses `inspect.stack()`). Not a hard wall; documented as a soft signal.
- Server's `release_update` snapshot bracketing is a follow-up PR (per ADR-0118). Until it lands, release-ship has the same rollback gap that ADR-0007 had — but the gap is narrowed from "every promotion" to "release-ship only," which is admin-rare.

**Coordinated changes:**

- `mindsos_core/metagraph_snapshot.py` — module docstring updated; deprecation warning added when called from non-server packages.
- `mindsos_knowledge/knowledge_layer.py` — legacy `kl.promote` keeps snapshot; new `propose_for_promotion` uses WAL.
- `mindsos_server/release.py` (per pivot slice) — gains snapshot bracketing as follow-up PR per ADR-0118.
- Tests: `tests/unit/test_layer_isolation.py` — new lint rule.
- ADR-0007 status: Superseded.
- ADR-0027, ADR-0028: cross-references to this ADR.

## Alternatives considered

1. **Delete `MetagraphSnapshot` entirely; use WAL for everything.** Rejected — release-ship's pending → canonical swap is exactly the all-or-nothing in-process pattern snapshot is good at; using WAL for it would add round-trips for no correctness benefit.
2. **Keep `MetagraphSnapshot` general-purpose; let KL keep using it.** Rejected — two rollback mechanisms in KL (WAL + snapshot) is worse than one. The pivot's `propose_for_promotion` uses WAL; snapshot use in KL would be vestigial.
3. **Move `MetagraphSnapshot` from `mindsos_core` into `mindsos_server`.** Rejected — the implementation remains a generic Metagraph operation (mutate-in-place deep-copy/restore); it just has a narrow caller. Keeping it in Core means future generic uses (a hypothetical "undo" in another layer) can adopt it without a Core PR.
4. **Make `MetagraphSnapshot` serialisable so cross-process rollback works.** Rejected — couples Core to a snapshot wire format; v1 doesn't have a multi-process deployment story; pivot v2 may revisit but not in v1 scope.

## Implementation references

- `mindsos_core/metagraph_snapshot.py` — module docstring + deprecation warning from non-server callers.
- `mindsos_core/__init__.py` — docstring note.
- `mindsos_knowledge/knowledge_layer.py` — legacy promote keeps snapshot during transition.
- `mindsos_server/release.py` — snapshot bracketing for canonical-Global rollback (follow-up per ADR-0118).
- Tests: `tests/unit/test_layer_isolation.py` — lint rule.
- Documentation: `docs/dev/internals/core.md` (snapshot section), `docs/api/core/metagraph-snapshot.md` (scope marked).

ADR moves from Proposed to Accepted when KL's pivot-path drops snapshot use, the lint rule lands, and `docs/dev/internals/core.md` reflects the narrowed scope.

## Revisions

### amendment-1 (2026-05-22 — Phase 23 retirement)

Phase 23 was chartered as the home for a server-side context-manager
wrapper around `MetagraphSnapshot.of` + `.restore_into` (per the
narrowed scope this ADR §"Decision" §"Sole supported caller in v1"
locks). The Phase 23 design chat retired the phase as design-only.
This amendment records the resulting documentary changes:

1. **Inline call shape locked.** Phase 24's `release_update` (per
   ADR-0118 §"Decision" §2) calls
   `snap = MetagraphSnapshot.of(canonical_global_mg)` before the
   per-role `pending_global_<role>` → `mindsos_global_<role>` copy.
   On exception during the per-role copy, `release_update` calls
   `snap.restore_into(canonical_global_mg)` and re-raises. **No
   separate wrapper module ships.** The contextmanager / wrapper API
   shape considered in earlier drafts is dropped: a 3-line `try:` /
   `except:` is honest about the pattern; a 5-LOC wrapper adds
   indirection for ~2 LOC of savings.

2. **Runtime `DeprecationWarning` retired.** The §"Decision" §"Public
   API surface" clause prescribed a `DeprecationWarning` from
   `MetagraphSnapshot.of` (detected via `inspect.stack()`) when called
   from `mindsos_knowledge`, `mindsos_capacity`, or `mindsos_intelligence`.
   This warning is **vestigial in halvim**: pre-impl probe at the
   Phase 23 retirement chat confirmed zero callers exist in any of
   those packages (KL never imported `MetagraphSnapshot` — halvim's
   v3-baseline port did not bring snapshot use into KL; L3/L4/L5
   are unshipped). The `inspect.stack()` heuristic adds runtime cost
   per `.of()` call for no realized signal. The warning is dropped.

3. **CI lint rule retained, rescheduled to Phase 24.** The static
   lint rule (`grep MetagraphSnapshot.of(` outside `mindsos_server/`)
   ships at Phase 24 alongside `release_update`. The original
   "Phase 18+" schedule (per Phase 10 design Q lock recorded in
   `mindsos_core/metagraph_snapshot.py`'s module docstring) was
   silently missed across Phases 18–22; Phase 24 absorbs as part of
   the same coordinated change that lands the sole supported caller.

4. **Migration window is vacuous.** §"Coordinated migrations" listed
   "KL's legacy `kl.promote()` keeps snapshot use as-is during
   transition" and "KL's tests in `tests/unit/knowledge/test_promotion.py`
   — the `MetagraphSnapshot` fixture stays for the legacy promote
   tests." Neither code path exists in halvim: `KL.promote()` was
   dropped at Phase 14 per ADR-0138 honoured by absence, and no
   `test_promotion.py` was ported. The migration window has nothing
   to migrate from; these clauses are documentary debt closed by
   this amendment.

5. **ADR-0007 flip timing unchanged.** ADR-0007's
   supersession-in-progress banner promises the flip to Superseded
   "when [ADR-0129's] coordinated changes ship in code." That ship
   is Phase 24's `release_update`, not the Phase 23 retirement.
   ADR-0007 stays Accepted (with banner) until Phase 24.

6. **Phase 23 retirement artifacts.** `confirmation_docs/PHASE_23_RETIREMENT_DESIGN_LOG.md`
   captures the three-round design chat (Phase 17 precedent format).
   PHASE_MAP §23 row → RETIRED with rationale; §24 row → concrete
   absorption note for the inline pattern + lint rule slot. No
   `phase-23-confirmed` tag; no version bump (design-only retirement
   per PHASE_MAP §1 design-only-phases exception clause).

### amendment-2 (Phase 24 ship — 2026-05-22) — snapshot vestigial in halvim's release_update; module retained as defensive primitive; CI lint rule dropped; §am1 #1-4 re-opened

**Trigger:** Phase 24 round 2 PB-7 + round 3 PB-13 design rounds.
The Phase 23 retirement chat locked the inline `MetagraphSnapshot.
of(canonical_global_mg)` / `.restore_into(canonical_global_mg)`
pattern in `release_update` (§am1 §1-3 + §4 lint rule). The Phase
24 design rounds probed the locked pattern against FalkorDB per-
graph atomicity + ADR-0125 lazy hydration + `MetagraphRepository.
persist` write-through semantics and concluded:

1. **The inline pattern doesn't roll back FalkorDB-side partial
   per-role copies.** FalkorDB gives per-graph atomicity, NOT per-
   loop atomicity. If role 3 of 11 fails during the pending →
   canonical copy, roles 1-2 are already canonical-mutated FalkorDB-
   side. The in-memory `MetagraphSnapshot` doesn't roll back the
   FalkorDB writes. Phase 23 retirement §am1 §1-3 locked a pattern
   that doesn't address the multi-role partial-failure case.
2. **The snapshot has no in-memory mutation to roll back either.**
   The Phase 24 round 3 probe against `mindsos_core/persistence/
   metagraph_repository.py::persist` confirmed it is write-through
   (reads in-memory → writes FalkorDB; doesn't mutate in-memory).
   `release_update`'s pending → canonical copy is a FalkorDB graph-
   to-graph operation that doesn't touch the in-memory canonical_
   global_mg at all. ADR-0125 lazy hydration handles cache
   invalidation in the reverse direction (FalkorDB → in-memory on
   demand).

**Therefore: snapshot is fully vestigial in halvim's release_update.**

**Amended behavior:**

1. **§am1 §1 inline pattern dropped.** `release_update` does NOT
   call `MetagraphSnapshot.of(canonical_global_mg)` or `.restore_
   into(canonical_global_mg)`. The function writes FalkorDB only;
   on partial-role failure, partial FalkorDB state stays; admin
   reruns `release_update` (rerun is idempotent because pending_
   global content is unchanged). ADR-0118 §am1 records the
   corrected semantics.
2. **§am1 §2 ordering vacuous.** "Snapshot taken AFTER audit gate
   + AFTER lock acquisition, BEFORE first per-role copy" — vacuous
   because snapshot is dropped.
3. **§am1 §3 rollback semantics vacuous.** "On exception during
   per-role copy: restore_into then re-raise" — vacuous because
   snapshot is dropped. Pending stays intact for retry is now
   independently locked at ADR-0118 §am1 + Phase 24 design log
   PB-26(b) audit-gate-snapshot-set pattern (`shipped_in_release IS
   NULL` is the natural pending predicate).
4. **§am1 §4 CI lint rule dropped.** The Phase 24-scheduled lint
   rule (`grep MetagraphSnapshot.of(` outside `mindsos_server/`)
   guards against drift toward a no-consumer module. With zero
   consumers in halvim, there's no drift to guard. The Phase 23
   retirement §7 #4 carry-forward re-opens; Phase 24 explicitly
   drops the lint rule rather than ship guard-against-nothing.
5. **§am1 §5 `DeprecationWarning` retirement** unchanged — still
   retired, still not implemented.
6. **§am1 §6 ADR-0007 flip timing unchanged.** ADR-0007 still
   flips Accepted → Superseded at Phase 24 ship — but the
   rationale shifts: not because `release_update` ships the
   bracketing (which §am1 promised), but because `release_update`
   ships the architectural replacement of cross-user atomic
   promotion (which is the actual scope of ADR-0007's
   supersession-in-progress banner). ADR-0118's pivot model lands;
   ADR-0007's premise is moot regardless of snapshot use.

**Module retention rationale (PB-13(a)):** `mindsos_core/metagraph_
snapshot.py` is retained as a defensive Core primitive despite zero
v1 consumer. Three justifications:

* Module is small (~300 LOC + Phase 10 tests) and harmless when
  unused.
* The `MetagraphSnapshot.of` / `.restore_into` mutate-in-place +
  identity-preserving contract (ADR-0027 / ADR-0028) is non-
  trivial; preserving the implementation reduces re-derivation
  cost if a future feature (undo / branching / time-travel
  debugging) needs it.
* Deletion is reversible from git but costs design cycles to
  debate; retention is the lower-cost default.

This ADR's own Status remains **Accepted** — the narrowing-to-
release-ship contract still holds in principle (no caller outside
release-ship should use snapshot); v1 simply has zero callers
including release-ship. Future ADR Supersession may follow if
operational demand surfaces (e.g., a v3 feature needs snapshot and
the module's preserve-for-future bet pays off; or the module is
deleted in a cleanup phase, at which point this ADR can flip to
Superseded with cross-reference).

**Vacuous migration window (§am1 §4) unchanged.** halvim KL never
ported `promote()` (Phase 14 PB-6 + ADR-0138 honoured by absence);
no `tests/unit/knowledge/test_promotion.py` exists; the migration
window has nothing to migrate from.

**Phase 23 retirement § 7 #1-4 re-opens.** Carry-forwards #1-3
(inline pattern) and #4 (CI lint rule) re-open per Phase 24 PB-1(b)
+ PB-13(a). Carry-forwards #5-7 (warning-retired + ADR-0007 flip
timing + version bump path) honoured unchanged.

**Phase 24 design log:** `halvim_mindsos/confirmation_docs/PHASE_24_
DESIGN_LOG.md` §1 Round 1 PB-1 (multi-role rollback flaw surface) +
Round 2 PB-7 (probe-pending snapshot drop) + Round 3 PB-13 (probe-
confirmed + module retained + lint rule dropped) + §8 Phase 23
retirement §7 carry-forward disposition table.
