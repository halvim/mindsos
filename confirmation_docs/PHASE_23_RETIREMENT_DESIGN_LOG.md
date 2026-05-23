# Phase 23 — Retirement Design Log

**Date:** 2026-05-22
**Decision class:** RETIRED (design-only; tag-free; zero-code-except-docstring)
**Squash-merge SHA:** TBD (filled in post-merge)
**ADR amendment:** ADR-0129 §amendment-1 (six clauses)

---

## §0 — Summary

Phase 23 ("Server: MetagraphSnapshot rollback infrastructure narrowed")
was chartered to ship a server-side context-manager wrapper around
`MetagraphSnapshot.of()` + `.restore_into()` — the snapshot
primitives shipped at Phase 10 (per ADR-0027), narrowed to
release-ship-only use per ADR-0129. The PHASE_MAP §23 row explicitly
opened retirement as an outcome at design time: "the wrapper has no
real consumer until Phase 24's `release_update` calls into it. Phase
23 may instead defer entirely to Phase 24 — phase chat decides at
design time."

Pre-impl probe at the Phase 23 chat established that (a) there is no
consumer of the wrapper anywhere in shipped code — `mindsos_server/release.py`
doesn't exist, `release_update` isn't written, ADR-0118 is still
Proposed; (b) the would-be wrapper is ~10 LOC of indirection over a
3-line idiomatic Python pattern (`snap = MetagraphSnapshot.of(mg)` +
`try: ... ; except: snap.restore_into(mg); raise`); (c) `MetagraphSnapshot`
has **zero production callers in any package** today — KL never
imported snapshot in halvim (the v3-baseline port didn't bring it in;
the planned migration window per ADR-0129 §"Coordinated migrations"
has nothing to migrate from). The ADR-0129 §"Decision" §"Public API
surface" runtime `DeprecationWarning` (via `inspect.stack()` heuristic)
is correspondingly vestigial.

Three design rounds, 13 picks total, all user-agreed. This log
records the ledger.

---

## §1 — Pre-impl probe findings

Probe commands per PHASE_23_NEXT_CHAT_PROMPT.md "Pre-impl probe" block,
plus deeper grep at round 2:

* **Phase 22 baseline intact.** `c25a1bc` is `origin/main` HEAD =
  `phase-22-confirmed` tag. All six packages at `+phase22`. Phase 22
  admin surfaces present (`admin_tx`, `_assert_not_sole_admin`, 6
  verbs, 3 new error classes).
* **Phase 10 snapshot module intact.** `mindsos_core/metagraph_snapshot.py`
  exposes `MetagraphSnapshot.of(mg)` (lines 167+) and
  `.restore_into(mg)` (lines 228+) with the M3 + P84 corrected
  allow-list (12 covered attributes per ADR-0027 §Revisions §1).
* **Phase 23 surfaces absent.** No `snapshot_around`, `snapshot_acquire`,
  `snapshot_wrapper`, `with_snapshot`, `RELEASE_SHIP_LOCK`, or
  `release_ship_lock` strings in `mindsos_server/` or `mindsos_cli/`.
* **Phase 24 precursors absent.** `mindsos_server/release.py` does
  not exist. `propose_for_promotion` / `release_update` / `pending_global`
  appear only in docstring text (`mindsos_admin/similarity.py` and
  `mindsos_admin/__init__.py` reserved-name notes) — zero callable
  code.
* **No `MetagraphSnapshot.of()` callers in production.** Grep across
  all `mindsos_*/` packages: zero hits. Only `tests/phase_10/` test
  scaffolding uses `.of()`. KL's package has zero references to
  `metagraph_snapshot` or `MetagraphSnapshot`.
* **DeprecationWarning unimplemented.** Zero `DeprecationWarning` or
  `inspect.stack` references in `mindsos_core/metagraph_snapshot.py`.
* **CI lint rule unimplemented.** No `tests/unit/test_layer_isolation*`
  file shipped with the snapshot-out-of-server scan. The Phase 10
  design Q "Phase 18+" deferral was silently missed across Phases
  18-22.
* **ADR-0007 status check.** Still `Accepted` with supersession-in-progress
  banner; flip to Superseded promised "when [ADR-0129's] coordinated
  changes ship in code" — that ship is Phase 24's `release_update`,
  not Phase 23 retirement.

The probe matched both the Phase 17 retirement shape ("phase row's
scope is at odds with what shipped") and the Phase 15b shape
("scope premise is vacuous against shipped state").

---

## §2 — Round 1: scope decision (PB-1, PB-2, PB-3)

### PB-1 — Retire Phase 23 entirely?

Three options.

* (a) Ship the wrapper at P23 as pre-positioning + tests against a
  mock consumer.
* (b) **Retire Phase 23**; absorb the ~10 LOC wrapper into Phase 24
  alongside `release_update`'s direct call into `MetagraphSnapshot.of()`
  / `.restore_into()`. Design-only PR.
* (c) Ship a Protocol / type stub at P23 + lock impl at P24.

**Pick: (b) — retire.** Drift risk in (a)/(c) is the same reason
Phase 17 + Phase 37 retired. Phase 22's PB-Z pre-positioning worked
**because the home file (`admin.py`) already existed and had related
verbs**. Phase 23's home (`release.py`) doesn't exist; the wrapper
would sit in vacuum. Phase 24 will land `release.py`, `release_update`,
`RELEASE_SHIP_LOCK`, AND the snapshot bracketing in one cohesive ship
— splitting across phases creates handoff overhead exceeding the
wrapper itself.

### PB-2 — If we ship (PB-1(a)), where does the wrapper module live?

Three options: (a) `mindsos_server/snapshot_wrapper.py` new module;
(b) `mindsos_server/release.py` (but Phase 24 populates it — awkward
partial ownership); (c) inside `mindsos_server/admin.py` next to
`admin_tx` (composition argument).

**Pick: moot** — PB-1(b) wins. (a) would be least bad if PB-1(a) had
won; (c) confuses the two-store boundary (admin_tx = SQLite tx;
snapshot wrapper = FalkorDB graph state — different stores, no
composition).

### PB-3 — ADR-0129 lint rule + DeprecationWarning: where do they land if Phase 23 retires?

Three options: (a) defer both to Phase 24 with `release_update`; (b)
Phase 23 reframes to "enforcement-only" slice and ships them; (c)
both land at Phase 24.

**Pick: (a) — defer to Phase 24.** ADR-0129 §"Coordinated migrations"
explicitly schedules `release_update` snapshot bracketing as the
follow-up after audit gate (ADR-0115); the lint rule + warning belong
with the same ship. (b) reproduces the same drift problem — the
warning's intended migration consumer doesn't exist; reframing P23
to enforcement-only still pre-positions tests for absent code.

**Round 1 picks summary:** PB-1(b) retire; PB-2 moot; PB-3(a) defer.

---

## §3 — Round 2: retirement mechanics (PB-A, PB-B, PB-C, PB-D, PB-E)

Second-pass probe finding triggered round 2: `MetagraphSnapshot.of()`
has **zero callers in any production package**. KL never adopted
snapshot in halvim. The DeprecationWarning + lint rule from ADR-0129
target a migration that doesn't need to happen — there are no
violators to warn or lint against.

### PB-A — Are ADR-0129's runtime warning + lint rule vestigial?

Three options: (a) keep both per PB-3(a) (status quo); (b) retire
runtime warning, keep + reschedule lint to Phase 24; (c) retire both
— rely on §"What's narrowed" social enforcement.

**Pick: (b).** Static lint is cheap and catches the only realistic
drift vector (a future L3/L4/L5 dev reaching for `.of()`); the
runtime warning is dead code with `inspect.stack()` overhead on every
`.of()` call for a signal that has no current target. Drop the
warning; retain the lint; reschedule to Phase 24.

### PB-B — Lock the wrapper-vs-inline API shape now in ADR-0129 §amendment-1?

Three options: (a) §amendment-1 locks the inline pattern
(`MetagraphSnapshot.of` + try/except + `.restore_into`; no wrapper);
(b) defer call shape to Phase 24 design chat; (c) §amendment-1 names
a `contextmanager` wrapper as the supported form.

**Pick: (a).** A wrapper that's half the LOC of its own callsite is
overhead. Inline is honest about the 3-line pattern. Locking now
closes a Phase 24 design round.

### PB-C — PHASE_MAP §24 absorption note specificity?

Three options: (a) generic ("Phase 23 retired; Phase 24 absorbs");
(b) concrete (exact code shape from PB-B + lint rule from PB-A +
audit-gate sequencing per ADR-0118); (c) maximally specific (also
list Phase 24 test set).

**Pick: (b).** (a) leaves Phase 24 to re-derive; (c) over-locks
tests Phase 24 chat should own. Concrete absorption note: snapshot
taken AFTER audit gate passes and AFTER `RELEASE_SHIP_LOCK` acquired,
BEFORE first per-role copy; restore on exception; re-raise; no
cross-user state touched.

### PB-D — PHASE_MAP touch scope?

Three options: (a) §23 row only; (b) §23 + §24 row + §3 phase index
entry; (c) (b) plus a `phase-23-retired` tag.

**Pick: (b).** §3 phase index is the scannable surface; leaving it
stale confuses future phase chats. (c) is overkill — design-only
retirement doesn't earn a tag per §1 design-only-phases clause;
Phase 17 and Phase 37 retirements didn't get tags either.

### PB-E (polish) — Touch `mindsos_core/metagraph_snapshot.py` module docstring?

Current docstring says "Phase 10 design Q lock defers the CI lint
rule to Phase 18+." Phase 18 shipped without it; stale-by-four-phases.
After PB-A(b), lint reschedules to Phase 24.

**Pick: yes — one-line edit in the retirement PR.** Cheap; first
thing devs read.

**Round 2 picks summary:** PB-A(b) retire warning, keep+reschedule
lint; PB-B(a) lock inline; PB-C(b) concrete absorption; PB-D(b)
§23 + §24 + §3; PB-E yes one-line docstring touch.

---

## §4 — Round 3: exit-artifact polish (PB-α, PB-β, PB-γ, PB-δ, PB-ε)

Third-pass probe finding triggered round 3: ADR-0007 is still
`Accepted` (with banner promising Superseded flip "when [ADR-0129's]
coordinated changes ship in code" — that's Phase 24 code, not Phase
23 retirement). ADR-0027 has §Revisions §1 (Phase 10 covered-fields)
and doesn't need a touch. Phase 17 retirement precedent files show
BOTH a `PHASE_17_RETIREMENT_DESIGN_LOG.md` AND a next-chat-prompt —
locked scope from round 2 missed the design log.

### PB-α — Ship `PHASE_23_RETIREMENT_DESIGN_LOG.md`?

Three options: (a) ship the design log mirroring Phase 17 precedent;
(b) skip — §amendment-1 carries enough rationale; (c) embed into PR
body only (ephemeral).

**Pick: (a).** Phase 17 set the precedent; PR bodies are ephemeral;
future audits reading PHASE_MAP §23 RETIRED follow the link.

### PB-β — Flip ADR-0007 Accepted → Superseded now (P23) or at P24?

Two options: (a) flip at Phase 24 with code (current banner promise);
(b) flip at Phase 23 retirement.

**Pick: (a).** Keep flip atomic with code ship; banner is accurate.
ADR-0129 §amendment-1 §5 records this explicitly.

### PB-γ — Touch PHASE_22_DESIGN_LOG.md §Forward subsection?

Two options: (a) edit to reflect retirement; (b) leave (historical
artifact).

**Pick: (b).** Design logs are snapshots, not live docs. Phase 17
retirement didn't retroactively edit Phase 16's design log. Don't
pollute history.

### PB-δ — Fix PHASE_MAP §3 footer "One design-only phase (14a)"?

Three options: (a) enumerate (14a + 15b + 23) + retired (17 + 23);
(b) generic "multiple design-only"; (c) leave.

**Pick: (a).** The count is referenced for tooling decisions;
stale-by-three breeds confusion.

### PB-ε — Exit artifact `PHASE_24_NEXT_CHAT_PROMPT.md` scope: substantive or one-pager?

Three options: (a) substantive (~200-250 lines per Phase 22 precedent);
(b) minimal one-pager; (c) split across multiple per-ADR handoff docs.

**Pick: (a).** Matches Phase 22's handoff weight. Phase 24's scope
(full ADR-0118 + ADR-0141 + ADR-0144 §Placement + RELEASE_SHIP_LOCK +
audit gate + 4 PromotionItemKinds + release manifest + lazy migration
+ inline snapshot pattern) is the largest unshipped phase — skimping
the handoff invites Phase 24 to burn design rounds re-deriving
locked decisions. (c) over-fragments.

**Round 3 picks summary:** PB-α(a) ship design log; PB-β(a) ADR-0007
flip stays at Phase 24; PB-γ(b) leave Phase 22 log; PB-δ(a) fix
footer; PB-ε(a) substantive Phase 24 handoff.

---

## §5 — Final picks ledger (13 picks across 3 rounds)

| Round | PB | Pick | One-line reason |
|---|---|---|---|
| 1 | 1 | (b) retire Phase 23 | No consumer pre-P24; wrapper is ~10 LOC; Phase 17/37 precedent. |
| 1 | 2 | moot | PB-1(b) wins; no module is created. |
| 1 | 3 | (a) defer lint+warning to P24 | ADR-0129 §Coord-migrations bundles them with `release_update`. |
| 2 | A | (b) retire warning, keep+reschedule lint | Warning is vestigial; static lint is cheap drift insurance. |
| 2 | B | (a) lock inline pattern in §amendment-1 | Wrapper saves nothing over 3-line inline. |
| 2 | C | (b) concrete §24 absorption note | Avoids re-derivation at Phase 24 chat. |
| 2 | D | (b) update §23 + §24 + §3 phase index | §3 is the scannable map. |
| 2 | E | yes, one-line docstring touch | Phase 10's "Phase 18+" deferral stale by 4 phases. |
| 3 | α | (a) ship retirement design log | Phase 17 precedent; forensic trail. |
| 3 | β | (a) ADR-0007 flip stays at Phase 24 | Atomic with code ship. |
| 3 | γ | (b) leave PHASE_22 design log alone | Historical snapshot, not live doc. |
| 3 | δ | (a) fix design-only-phases count in §3 footer | Cheap; stale by 3. |
| 3 | ε | (a) substantive Phase 24 handoff | Phase 24 is largest unshipped phase. |

---

## §6 — Cross-refs

* **ADR-0129 §amendment-1** — six-clause documentary amendment
  recording (1) inline pattern lock, (2) runtime warning retirement,
  (3) lint rule reschedule, (4) vacuous migration window, (5)
  ADR-0007 flip timing unchanged, (6) retirement artifacts.
* **ADR-0027** — covered-fields contract unchanged (§Revisions §1
  Phase 10 lock stands).
* **ADR-0007** — Status stays `Accepted (supersession-in-progress)`;
  flips to Superseded at Phase 24 when `release_update` code lands.
* **ADR-0118** — Status stays `Proposed`; flips to Accepted at Phase
  24 ship.
* **PHASE_MAP.md** — §23 row → RETIRED with rationale; §24 row →
  concrete absorption note; §3 phase index Phase 23 row strike +
  footer count fix.
* **`mindsos_core/metagraph_snapshot.py`** — module docstring one-line
  fix (Phase 18+ → Phase 24 reschedule note).
* **`confirmation_docs/PHASE_24_NEXT_CHAT_PROMPT.md`** — substantive
  handoff documenting absorbed scope + locked §amendment-1 contract.
* **Phase 17 retirement** (`PHASE_17_RETIREMENT_DESIGN_LOG.md`,
  ADR-0150 §am3) — precedent for design-only retirement format.
* **Phase 37 retirement** (ADR-0140 §am1) — precedent for
  pre-emptive retirement during a related phase's chat.
* **Phase 15b design-only** — precedent for zero-code design-only
  PR shape.

---

## §7 — Carry-forwards to Phase 24

These are NOT carry-forwards in the usual sense (Phase 23 ships no
code that defers downstream work). They are **locked decisions** that
Phase 24's design chat consumes:

1. Inline `MetagraphSnapshot.of(canonical_global_mg)` + try/except +
   `.restore_into(canonical_global_mg)` call shape in `release_update`.
   No wrapper module. No contextmanager.
2. Snapshot is taken AFTER audit gate passes AND AFTER
   `RELEASE_SHIP_LOCK` is acquired, BEFORE the first per-role
   `pending_global_<role>` → `mindsos_global_<role>` copy.
3. On exception during any per-role copy: `snap.restore_into(canonical_global_mg)`
   then re-raise. Pending stays intact for retry (no pending cleanup
   on rollback per ADR-0118 §"Decision" §2).
4. CI lint rule (`grep MetagraphSnapshot.of(` outside `mindsos_server/`)
   ships at Phase 24 alongside `release_update`. Location: `tests/unit/test_layer_isolation.py`
   per ADR-0129 §Decision, or halvim's equivalent location (Phase 24
   chat picks).
5. Runtime `DeprecationWarning` via `inspect.stack()` is **retired** —
   do not implement.
6. ADR-0007 flips Accepted → Superseded at Phase 24 ship (per its
   supersession-in-progress banner).
7. Version bump path: `+phase22 → +phase24` (skip the `+phase23`
   slot — pure design-only retirements don't earn a version bump per
   PHASE_MAP §1 design-only-phases clause; precedent: Phase 14a +
   Phase 15b (both design-only, both skipped their version slots).
   **Caveat:** Phase 17 DID earn `+phase16 → +phase17` because it
   shipped 5-LOC of code (the `versions_in_role` enumerator) inside
   the retirement chat — Phase 17 was "design-only-with-code." Phase
   23's retirement is closer to Phase 14a / 15b shape (zero code
   except a one-line docstring fix that doesn't change any runtime
   contract). The docstring fix is too thin to justify a `+phase23`
   bump.
