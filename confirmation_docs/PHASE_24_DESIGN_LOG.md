---
phase: 24
phase_title: "Server + admin: per-user transactional promotion + release-boundary atomicity (ATOM admin-direct only)"
layer: L0 / admin
status: design-locked
date_locked: 2026-05-22
design_rerun: 2026-05-22  # Round 0 pre-impl re-analysis: PB-Z1..PB-Z20 (12 picks)
branch: phase-24
tag_on_confirm: phase-24-confirmed
net_new: true   # new modules: mindsos_admin/promotion.py, mindsos_admin/audit_gate.py, mindsos_server/release.py, mindsos_server/locks.py; new SQLite tables (pending_mutations + releases); schema bump v3 → v4
design_rounds: 6   # 5 original + 1 pre-impl re-analysis (Round 0)
total_picks: 40    # 28 original + 12 Round 0 picks
prior_phase: 22
phase_23_status: retired-design-only-2026-05-22
next_phase: 25
---

# Phase 24 Design Log — Server + admin: per-user transactional promotion + release-boundary atomicity

## §0. Scope summary

Phase 24 lands the **pivot model** (ADR-0118) in code for the
narrowest shippable surface: **admin-direct ATOM promotion only**,
with full release-ship machinery (audit gate + release manifest +
RELEASE_SHIP_LOCK + FAILED-row forensics). Source-user-Local
promotion (admin-on-behalf-of-user) and lazy migration both defer to
Phase 25 alongside the cross-user-read substrate they consume
(ADR-0008 §am1 + ADR-0011 §am1 + ADR-0042 §am1). The
PromotionItemKind enum ships with all four values (ATOM /
STRUCTURE / SUBGRAPH / PIPELINE) for forward-shape contract; only
ATOM has a validator at P24.

Phase 24 closes the ADR-0118 / ADR-0141 / ADR-0144 §Placement
Proposed-status triad with code, plus three indirect Supersessions
(0049 / 0053 / 0056 per their Phase 16 §am1 lock) and the long-
banner-flagged ADR-0007 Supersession. Three new ADRs are drafted at
this phase: 0114 (release manifest + version DB schema), 0115 (audit
gate + impact report), 0120 (cross-layer rewrite handler contract).
The other reserved ADRs (0113 / 0116 / 0117 / 0119) defer to later
phases — their content gates on substrate Phase 24 doesn't ship
(version-bump-under-the-hood; soft-delete which Phase 11 already
shipped; compositional metaedge which Phase 05a dropped; composition
dedup which gates on STRUCTURE).

Five design rounds / 28 picks. The largest scope was surfaced in
round 1 PB-1 (ADR-0129 §am1 multi-role rollback flaw); subsequent
rounds shrunk P24 from "all 4 PromotionItemKinds + lazy migration +
6 ADRs + 5-state release lifecycle" to "admin-direct ATOM +
SHIPPED/FAILED only + 3 ADRs drafted + 2 caps". Phase 23's
retirement (2026-05-22) locked 7 carry-forwards in
PHASE_23_RETIREMENT_DESIGN_LOG.md §7; six are honoured; one is
re-opened at round 3 PB-13 after the round 2 PB-7 probe surfaced
that the locked inline `MetagraphSnapshot` pattern has zero
consumers in halvim.

This phase **does NOT** ship: lazy migration code path
(`MindsOSServer.start_session` rewrite-map walk) — deferred to P25
alongside `MindsOSServer` orchestrator + `LocalPersister.load`; STRUCTURE
/ SUBGRAPH / PIPELINE PromotionItemKind validators — deferred to
post-Core-CompositionalMetaEdge phase + post-L3-ship phase
respectively; `register_promotion_kind()` extensibility registry
(PIVOT §7.1) — hardcoded ATOM dispatch at P24, registry deferred to
first multi-kind phase; source-user-Local propose (admin-on-behalf-
of-user) — gates on Phase 25 cross-user read substrate; force-
override on blocking audit findings — v2 per ADR-0118 §Tradeoffs;
quorum-approve release lifecycle (PROPOSED / APPROVED / REJECTED /
WITHDRAWN states) — v2; `CAN_READ_PENDING_GLOBAL` capability —
deferred to first direct-read consumer phase; pending-Global graph
inspection admin verb — v2; multi-state release lifecycle DB
records — schema CHECK constraint = `('SHIPPED', 'FAILED')` only at
v4; `MetagraphSnapshot` module deletion — module retained as
defensive Core primitive; CI lint rule guarding snapshot use outside
mindsos_server — dropped (no consumer means no drift to guard).

Eleven ADR touches at this ship: three new ADRs drafted (0114 /
0115 / 0120), four Status flips (0118 + 0141 → Accepted; 0144
fully Accepted; 0007 → Superseded), three indirect Supersessions
(0049 + 0053 + 0056 per Phase 16 §am1 lock), one §amendment closing
a Proposed-status (0144 §am1 retires; §am2 documents §Placement
flip), three documentary §amendments (0129 §am2 snapshot-vestigial
correction + 0118 §am1 admin location + 0141 §am1 admin location),
one cap-roster §amendment (0002 §am2 + 7 caps → 9 caps), one
rename-ratification §amendment (0006 §am1 RELEASE_SHIP_LOCK
canonical name).

## §1. Round-by-round design ledger

Five rounds of pushbacks before lock. Picks per pushback + final
picks summary per `feedback_pushback_format_with_picks.md`.
Phase 24's pick density (28 picks across 5 rounds) is consistent
with Phase 22's 27/5; Phase 18's 38 picks across 4 rounds remains
the high-water.

### Round 1 — Scope-shaping pushbacks (PB-1..PB-6)

#### PB-1 — ADR-0129 §am1 inline snapshot doesn't cover multi-role partial-failure

Phase 23 retirement §7 #1-3 locked the inline `MetagraphSnapshot.of` /
`.restore_into` pattern in `release_update`. PB-1 surfaces the
load-bearing flaw: FalkorDB gives per-graph atomicity NOT per-loop
atomicity; if role 3 of 11 fails during the pending → canonical
copy, roles 1-2 are already canonical-mutated FalkorDB-side. The
in-memory snapshot doesn't roll back the FalkorDB writes. Same
phantom-promotion bug ADR-0118 was designed to eliminate, transplanted
to release-ship.

Options:
- (a) WAL-bracketed per-role copy (over-engineering for admin-rare op).
- (b) **Per-role independence; no multi-role rollback; admin reruns
  on partial-ship.** Each role's copy is independent at FalkorDB level;
  partial completion stays in canonical; admin reruns release_update.
  Snapshot retained for in-memory cache invalidation only (refined to
  zero-consumer at PB-7 probe).
- (c) Bundle multi-role into one Cypher (FalkorDB constraint precludes).
- (d) Ship the bug (reintroduces ADR-0118's defeated failure mode).

**Pick: (b).** ADR-0129 §amendment-2 to document. Re-opens Phase 23
retirement §7 #1-3 — the inline pattern stays in concept, but its
purpose changes from "FalkorDB rollback" (impossible) to "in-memory
cache invalidation guard" (refined to zero-consumer post-PB-7).

#### PB-2 — Phase scope is 4 phases of work crammed into one

PHASE_MAP §24 row as written claims P24 lands 6 undrafted ADRs + 4
PromotionItemKinds + lazy migration + 8 audit events + 3 capabilities
+ release manifest + RELEASE_SHIP_LOCK + audit gate + ADR-0010 lint
rule + 3 Status flips. As-scoped is 60-80 picks across 7-9 rounds.

Options:
- (a) Ship as-scoped (7-9 design rounds).
- (b) Split P24a (release infra) + P24b (lazy migration + kinds).
- (c) Split P24a (design-only ADRs) + P24 (code) per Phase 14a precedent.
- (d) **Drop scope via PB-3 / PB-4 / PB-5 / PB-6; let realistic-only
  scope shrink P24 naturally.**

**Pick: (d).** Post-shrink scope is ~35-40 picks; revisit split if it
exceeds 50.

#### PB-3 — STRUCTURE / SUBGRAPH / PIPELINE gate on missing substrate

STRUCTURE per PIVOT §6.B.2 requires `CompositionalMetaEdge` Core
subclass (Phase 05a Dropped per `project_mindsos_phase_05a` memory).
PIPELINE is cross-layer L3+L2 (L3 unshipped per PHASE_MAP §33-35).
SUBGRAPH has no extractor in halvim. ATOM works against shipped
substrate.

Options:
- (a) **ATOM only.** STRUCTURE → post-Core-retrofit phase. SUBGRAPH →
  own phase. PIPELINE → post-L3.
- (b) ATOM + SUBGRAPH (modest extractor work).
- (c) ATOM + STRUCTURE (Core retrofit at server phase — wrong layer).
- (d) All four (won't fit).

**Pick: (a).** PromotionItemKind enum still ships with 4 values
(forward-shape contract); only ATOM has a validator. Future kinds
register their validator at their respective ship phase.

#### PB-4 — Lazy migration has no caller until Phase 25

ADR-0118 §"Decision" §3 specifies session-start hydration walks the
release chain. But Phase 19 sessions are SQLite token rows; no
"session-start workspace hydration" code path exists.
`MindsOSServer` + `LocalPersister.load` + `KL.install_local_metagraph`
are Phase 25 substrates per ADR-0008/0011/0042 §am1. Implementing
lazy migration at P24 means stubbing a code path with no caller —
Phase 14 PB-6 precedent ("KL no write API honoured by absence")
applies.

Options:
- (a) **Defer lazy migration entirely to P25.** Honoured by absence.
- (b) Stub LazyMigrator class with method called from nowhere (dead-
  code risk).
- (c) Pull Phase 25 session-start hydration forward into P24.

**Pick: (a).** ADR-0118 §am1 documents "lazy migration first-consumer
Phase 25." `releases.manifest_json` shape (PB-22) anchors the format
P25 will consume.

#### PB-5 — Reserved ADR drafting: minimum 0114 + 0115 + 0120

Six undrafted ADRs in PIVOT §7 (0113-0117 + 0119 + 0120). With PB-3/
PB-4 scope:
- 0113 (mutation auto-bumps version): gates on version DB + lazy
  migration scope. **Defer.**
- 0114 (release manifest + version DB schema): load-bearing.
  **Draft.**
- 0115 (audit gate + impact report): `release_update` calls it.
  **Draft.**
- 0116 (edge soft-delete): Phase 11 already shipped. **Documentary-
  debt; defer.**
- 0117 (CompositionalMetaEdge immutability): Phase 05a Dropped.
  **Defer.**
- 0119 (composition-signature dedup): gates on STRUCTURE. **Defer.**
- 0120 (cross-layer rewrite handler contract): contract yes, impl
  no. **Draft contract; impl at P25.**

Options: (a) draft 0114 + 0115 + 0120 only / (b) draft all six
(paperwork) / (c) bundle 0114 into 0118 / (d) bundle 0115 into 0144.

**Pick: (a).** Minimum-load-bearing.

#### PB-6 — Audit event naming: keep `EVT_*` convention

PIVOT §7.6 uses `AuditEventType(StrEnum)` with dotted values
(`"promotion.proposed"`). Phase 18-22 ships `EVT_*` string constants
(`"EVT_LOGIN"`). PIVOT enum is design-doc, never shipped.

Options: (a) **keep EVT_* convention** / (b) migrate to StrEnum
(breaking Phase 18-22 surfaces) / (c) coexist (two surfaces).

**Pick: (a).** Shipped precedent wins over paper-only PIVOT §7.6
enum. Halvim has consistently diverged from pivot-doc where shipping
precedent contradicted (ADR-0140 §am1, ADR-0144 §am1).

#### Round 1 picks summary

| PB | Pick | One-line |
|---|---|---|
| 1 | (b) per-role independence; no multi-role rollback | Inline snapshot can't roll back FalkorDB; ADR-0129 §am2 needed. |
| 2 | (d) let PB-3/4/5 shrink scope | Post-shrink ~35-40 picks; revisit at 50+. |
| 3 | (a) ATOM only | STRUCTURE / SUBGRAPH / PIPELINE gate on unshipped substrate. |
| 4 | (a) defer lazy migration to P25 | No caller; Phase 14 PB-6 precedent. |
| 5 | (a) draft 0114 + 0115 + 0120 only | Other reserved ADRs documentary or gate on unshipped. |
| 6 | (a) keep EVT_* convention | Shipped precedent wins over PIVOT §7.6 paper-enum. |

### Round 2 — Module placement + lifecycle scope (PB-7..PB-12)

#### PB-7 — `MetagraphSnapshot` may be vestigial in halvim's `release_update`

ADR-0125 lazy local hydration + ADR-0028 in-memory-only snapshot +
PB-1(b) per-role independence taken together: if release_update
writes FalkorDB only and never mutates the in-memory canonical_
global_mg, snapshot has nothing to restore. Probe needed against
`mindsos_core/persistence/metagraph_repository.py`.

Options:
- (a) **Drop snapshot from release_update** (pending probe).
- (b) Keep defensively as cache-invalidation guard.
- (c) Keep IF metagraph_repository mutates in-memory mirror.

**Pick: (a) pending probe.** Probe at round 3 confirmed: `MetagraphRepository.persist`
reads in-memory → writes FalkorDB; doesn't mutate in-memory. Lazy
hydration per ADR-0125 is reverse direction. **Snapshot fully
vestigial.** Lock locked at round 3 PB-13.

#### PB-8 — ADR-0118 §1 names `kl.propose_for_promotion()`; halvim ships `mindsos_admin.propose_for_promotion()`

ADR-0118 §"Decision" §1 code block: `kl.propose_for_promotion`.
PHASE_MAP §24 + Phase 16 PB-1c reframe + ADR-0144 §am1 admin-
relocation precedent + ADR-0138 (KL drops write API) all say
`mindsos_admin/promotion.py`. ADR-0141 §"Decision" says
`mindsos_server.propose_for_promotion(...)` — third-way drift.

Options: (a) **ADR-0118 §am1 + ADR-0141 §am1** documenting
`mindsos_admin.propose_for_promotion(admin_session, proposal) ->
PromotionResult` / (b) move surface to mindsos_server / (c) move to
mindsos_knowledge (contradicts ADR-0138).

**Pick: (a).** Admin owns the surface; symmetric with ADR-0144 §am1 +
ADR-0140 §am1 admin-relocation precedents.

#### PB-9 — Audit gate code home: `mindsos_admin/audit_gate.py`

ADR-0115 isn't drafted; PB-5 picked drafting at P24. Audit gate
calls `compute_similarity` (mindsos_admin) for one finding; future
calls peer-dep / composition / user-impact checks. `release_update`
(mindsos_server) calls audit_gate. New package edge introduced
either way (`mindsos_server → mindsos_admin`).

Options:
- (a) **`mindsos_admin/audit_gate.py`** parallel to similarity.
- (b) `mindsos_server/audit_gate.py` colocated with release.
- (c) Inline in `mindsos_server/release.py`.

**Pick: (a).** ADR-0144 §am1 symmetry; admin owns audit machinery;
`server → admin` edge is the right direction (server composes admin
machinery).

#### PB-10 — Release lifecycle states: `SHIPPED` + `FAILED` only at P24

PIVOT §7.5 `releases.status` lists 5 states (PROPOSED / APPROVED /
SHIPPED / REJECTED / WITHDRAWN). ADR-0118 §Tradeoffs flags quorum-
approve as v2; single-command `release_update` has no approve step
at v1.

Options: (a) **SHIPPED + FAILED only** / (b) ship all 5 (PIVOT §7.5
fidelity) / (c) SHIPPED only, no FAILED (loses partial-ship audit).

**Pick: (a).** Honest scope; ADR-0114 draft enumerates 2 values;
CHECK constraint enforces; PIVOT §7.5 documentary §amendment (in
ADR-0114 draft body).

#### PB-11 — Source-user-Local promotion path defers to P25 too

`PromotionItem.source_user_id is not None` requires reading the
source user's Local. Cross-user read is Phase 25 substrate per
ADR-0008 §am1. Same gate as PB-4 lazy migration.

Options: (a) **admin-direct ATOM only at P24** / (b) Phase 19 sessions
hack / (c) pull cross-user read forward.

**Pick: (a).** PromotionItem dataclass ships full shape per PB-18;
source-user code path raises `NotImplementedError`. EVT_DRAFT_FROZEN /
EVT_DRAFT_UNFROZEN defer to P25. P24 audit event slate shrinks to 4
(PROMOTION_PROPOSED + PROMOTION_REJECTED + RELEASE_SHIPPED +
RELEASE_FAILED) not PIVOT §7.6's 8.

#### PB-12 — RELEASE_SHIP_LOCK substrate: `threading.RLock` outer + `admin_tx` inner

ADR-0006 amended-in-place by ADR-0118 (GLOBAL_PROMOTE_LOCK →
RELEASE_SHIP_LOCK); substrate unstated. Phase 22 `admin_tx`
precedent is SQLite-side.

Options:
- (a) **threading.RLock outer + admin_tx inner.** RLock wraps
  release_update body; admin_tx wraps releases-row + pending_mutations
  stamp.
- (b) threading.RLock only (admin_tx redundant at single-process v1).
- (c) admin_tx-only on a release_lock SQLite row (no FalkorDB
  serialization).

**Pick: (a).** Each lock at its store's scope; matches shipped
precedents.

#### Round 2 picks summary

| PB | Pick | One-line |
|---|---|---|
| 7 | (a) drop snapshot pending probe | Probe at R3 confirmed vestigial. |
| 8 | (a) ADR-0118 §am1 + ADR-0141 §am1 → mindsos_admin | Closes three-way drift on surface location. |
| 9 | (a) `mindsos_admin/audit_gate.py` | ADR-0144 §am1 symmetry; one new server→admin edge. |
| 10 | (a) SHIPPED + FAILED only | Honest scope; PIVOT §7.5 amends in ADR-0114 draft. |
| 11 | (a) admin-direct ATOM only at P24 | Source-user gates on P25; 4 audit events not 8. |
| 12 | (a) RLock outer + admin_tx inner | Each lock at its store's scope. |

### Round 3 — Snapshot fate + module homes + extensibility (PB-13..PB-17)

#### PB-13 — ADR-0129 fate + lint rule fate

Probe confirmed PB-7(a): `MetagraphRepository.persist` is write-
through (in-memory → FalkorDB, no in-memory mutation). Lazy
hydration per ADR-0125 handles cache invalidation. Snapshot in
`release_update` is fully vestigial; ADR-0129's narrowing-to-
release-ship narrows to zero consumers. CI lint rule (Phase 23
retirement §7 #4 carry-forward) guards a no-consumer module.

Options:
- (a) **ADR-0129 §am2 retains module as defensive Core primitive;
  lint rule dropped.** Re-opens Phase 23 retirement §7 #4.
- (b) ADR-0129 → Superseded; module flagged for cleanup-phase deletion.
- (c) Delete `mindsos_core/metagraph_snapshot.py` at P24 (~Phase 10
  test removal too).

**Pick: (a).** Module is small + harmless + reversibly preserved for
future undo/branching feature. ADR-0007 still flips Superseded
(cross-user atomic premise dead). ADR-0129 stays Accepted with §am2.

#### PB-14 — CLI verb home for new P24 verbs

Phase 22 ships `mindsos server admin <verb>` for 6 user-management
verbs. P24's two verbs are admin-only but release-lifecycle, not
user-lifecycle.

Options:
- (a) Extend `mindsos server admin` (`admin propose-for-promotion` +
  `admin release-ship`).
- (b) **New `mindsos server release` subgroup** (`release propose` +
  `release ship`).
- (c) Split (admin propose + release ship).

**Pick: (b).** Semantic separation; user-management ≠ release-
lifecycle. v2 verbs (approve / withdraw / reject) cluster under
`release` without namespace refactor. Exit-code namespace extends
5/6 → 7/8 for the 2 new verbs.

#### PB-15 — Pending-Global graph bootstrap timing

~10 roles per ADR-0042 each get a parallel `mindsos_pending_global_
<role>`.

Options: (a) **eager at install time** (extend bootstrap_global to
create both) / (b) implicit on first propose (lazy + first-write race) /
(c) separate `bootstrap_pending_global` admin verb.

**Pick: (a).** 10 empty graphs is negligible; implicit creation adds
first-write race that needs test coverage; eager matches Phase 15a
importers pattern.

#### PB-16 — `register_promotion_kind()` registry scope

PIVOT §7.1 specifies extensibility registry. With PB-3(a) ATOM-only,
the registry has one entry until STRUCTURE phase.

Options: (a) **hardcoded ATOM dispatch at P24** / (b) ship registry
now with ATOM as first registered kind / (c) protocol-only with
hardcoded impl.

**Pick: (a).** YAGNI; registry retrofit is small (~20 LOC at first
multi-kind phase). PIVOT §7.1 documentary amendment in ADR-0114
draft (or PIVOT footer): "registry mechanism deferred to first multi-
kind phase."

#### PB-17 — `releases.parent_release_id` ship at P24

PIVOT §7.5 chain pointer; P25 lazy migration walks the chain.

Options: (a) **ship column at P24** (full table shape) / (b) defer to
P25 (forward migration) / (c) ship NULL-populated only.

**Pick: (a).** Full table shape at introducing phase; one extra SELECT
inside admin_tx to populate.

#### Round 3 picks summary

| PB | Pick | One-line |
|---|---|---|
| 13 | (a) ADR-0129 §am2; module retained; lint rule dropped | Phase 23 §7 #4 re-opens; vestigial-with-rationale. |
| 14 | (b) `mindsos server release {propose,ship}` | Future-proofs v2 verbs without namespace refactor. |
| 15 | (a) eager pending-Global bootstrap | Extends `bootstrap_global`; ~10 empty graphs. |
| 16 | (a) hardcoded ATOM dispatch | YAGNI; registry retrofit cheap. |
| 17 | (a) ship parent_release_id at P24 | Full table shape; P25 walk uses without migration. |

### Round 4 — Implementation shapes (PB-18..PB-23)

#### PB-18 — `PromotionProposal` + `PromotionItem` dataclass shape

PIVOT §7.1 specifies full multi-item shape. ATOM admin-direct uses
~20% of fields; rest dead at P24.

Options: (a) **ship full PIVOT §7.1 shape** (forward-contract) / (b)
narrowed `AtomPromotionItem` (breaking change later) / (c)
PromotionProposal as dict.

**Pick: (a).** Phase 18-22 result-dataclass precedent; future kinds
populate.

#### PB-19 — NodeSpec / EdgeSpec / MetaEdgeSpec scope

PIVOT §7.1 references; doesn't define. ATOM needs NodeSpec.

Options: (a) define NodeSpec + stub EdgeSpec + MetaEdgeSpec / (b)
**NodeSpec only; EdgeSpec / MetaEdgeSpec as forward-refs** / (c) use
mindsos_core.Node directly (loses validate-then-apply).

**Pick: (b).** PromotionItem.edges typed `list["EdgeSpec"]` PEP 563
forward-ref; STRUCTURE phase resolves. NodeSpec at P24: `(node_type:
str, value: Any, properties: Mapping[str, Any], target_role: str)`.

#### PB-20 — Audit-gate blocking-finding handling

`compute_similarity` `"blocking"` (≥0.85) vs `"review"` (0.5-0.85)
classification.

Options: (a) auto-abort raise without `releases` row / (b) --force
override (pulls v2 forward) / (c) **auto-abort + write FAILED row
with `error_class="blocking_similarity_findings"`**.

**Pick: (c).** Strict-default per ADR-0144; FAILED row preserves
attempt audit trail; --force is v2 per ADR-0118 §Tradeoffs. CLI exit
code 8.

#### PB-21 — `release_update` with empty pending

Options: (a) **EmptyReleaseError raise; no row** / (b) no-op SHIPPED
row with mutations_count=0 / (c) no-op without row.

**Pick: (a).** Empty release is likely-bug; strict-fail surfaces
mismatch. CLI exit code 7. `releases` table semantically "things that
changed canonical."

#### PB-22 — `manifest_json` SHIPPED content shape

Options: (a) **full shape** with empty rewrite_map at P24 / (b)
minimum (mutation_ids + audit_event_id) / (c) NULL.

**Pick: (a).** Forensic + lazy-migration contract anchored;
`{ included_mutation_ids, rewrite_map, roles_affected, audit_event_
id, shipped_at }`. P25 populates rewrite_map.

#### PB-23 — Capability roster: 2 new caps at P24

Inferred 3 (CAN_PROPOSE_MUTATION + CAN_APPROVE_RELEASE +
CAN_READ_PENDING_GLOBAL); CAN_READ_PENDING_GLOBAL has no direct-read
consumer at P24 (audit gate is server-internal).

Options: (a) **2 caps (CAN_PROPOSE_MUTATION + CAN_APPROVE_RELEASE);
defer CAN_READ_PENDING_GLOBAL** / (b) all 3 / (c) 1 cap + reuse
CAN_WRITE_GLOBAL.

**Pick: (a).** ADR-0002 §am2 adds 2 caps; roster 7 → 9.
CAN_READ_PENDING_GLOBAL lands at first direct-read consumer phase.

#### Round 4 picks summary

| PB | Pick | One-line |
|---|---|---|
| 18 | (a) full PIVOT §7.1 PromotionProposal shape | Forward-contract; future kinds populate. |
| 19 | (b) NodeSpec only; EdgeSpec / MetaEdgeSpec as forward-refs | YAGNI; STRUCTURE phase resolves. |
| 20 | (c) auto-abort + FAILED row | Strict-default + forensic audit trail. |
| 21 | (a) EmptyReleaseError raise | Likely-bug surface; releases stays semantic. |
| 22 | (a) full manifest_json with empty rewrite_map | Forensic contract anchored. |
| 23 | (a) 2 new caps; defer CAN_READ_PENDING_GLOBAL | YAGNI; roster 7 → 9. |

### Round 5 — Concurrency + correctness (PB-24..PB-28)

#### PB-24 — Audit gate runs two `compute_similarity` passes

Cross-mg form (`target_mg=canonical`) compares candidates → target_mg
only; misses pending-vs-pending duplicates. Two duplicate proposals
ship as two canonical nodes. **Real gap none of R1-R4 picks closed.**

Phase 16 intra-mg mode (`target_mg=None`) includes candidate-vs-
candidate per PB-M2 (`Finding.matched_is_candidate`). Two passes solve
it.

Options:
- (a) Single cross-mg pass only (ships bug).
- (b) **Two-pass audit gate**: intra-pending (`target_mg=None`) +
  cross-mg (`target_mg=canonical`). Blocking from either aborts.
- (c) propose_for_promotion intra-pending check (doubles compute cost
  at propose rate).
- (d) DB UNIQUE on payload hash (misses near-duplicates).

**Pick: (b).** Audit gate canonical choke point per ADR-0144; one
extra call at release-rare frequency. PIVOT §7.8 `SimilarityWarning`
extends with `source: "intra_pending" | "cross_mg"` discriminator;
ADR-0115 draft documents.

#### PB-25 — `propose_for_promotion` two-store write ordering

SQLite (pending_mutations) + FalkorDB (pending_global_<role>).

Options:
- (a) **SQLite first inside admin_tx; FalkorDB inside body.** Order:
  BEGIN IMMEDIATE → INSERT pending_mutations → FalkorDB write →
  COMMIT. On FalkorDB raise: admin_tx rolls back SQLite.
- (b) FalkorDB first, then SQLite (orphan tracking-row gap).
- (c) WAL pattern (over-engineering at propose rate).

**Pick: (a).** Rare orphan case (FalkorDB succeeds + SQLite commit
fails): detectable via reconciliation query.

#### PB-26 — `propose` vs `release_update` concurrency

Both touch pending_global_<role> + pending_mutations. RELEASE_SHIP_
LOCK guards release_update only; propose can race audit-gate read.

Options:
- (a) propose acquires RELEASE_SHIP_LOCK (coarse).
- (b) **Audit-gate snapshot pattern**: release_update first SQLite
  read inside admin_tx is `SELECT mutation_id FROM pending_mutations
  WHERE shipped_in_release IS NULL`; that frozen set carries through
  audit + FalkorDB copy + SHIPPED-stamp. Late-arriving proposes stay
  pending for next release. Lock-free propose.
- (c) Two locks (PROPOSE_LOCK + RELEASE_SHIP_LOCK).

**Pick: (b).** Cleanest cut-point; scales better than coarse propose-
lock.

#### PB-27 — Audit-row `extra_json` payloads for 4 new `EVT_*` events

Options: (a) **lock 4 shapes at P24 design** / (b) denormalize counts
as columns / (c) compact JSON only.

**Pick: (a).** Phase 22 PB-16 precedent. Locked shapes:

- `EVT_PROMOTION_PROPOSED`: `{ proposer_admin_user_id: str,
  mutation_ids: list[int], items_count: int, kinds: list[str],
  roles_affected: list[str] }`
- `EVT_PROMOTION_REJECTED`: `{ proposer_admin_user_id: str,
  mutation_ids: list[int], reason: str }`
- `EVT_RELEASE_SHIPPED`: `{ release_id: int, mutations_shipped_count:
  int, roles_affected: list[str], parent_release_id: int | None }`
- `EVT_RELEASE_FAILED`: `{ release_id: int | None, failed_at_role:
  str | None, error_class: str, mutations_attempted_count: int,
  roles_shipped_before_failure: list[str] }`

#### PB-28 — FAILED `releases.manifest_json` content shape

PB-1(b) per-role independence means partial-FalkorDB-state is real.

Options:
- (a) **FAILED-specific manifest_json shape**:
  ```
  {
    included_mutation_ids: [],
    rewrite_map: {},
    roles_affected: list[str],        # roles where FalkorDB-side
                                       # copy landed before failure
    failed_at_role: str,
    error_class: str,
    mutations_attempted_count: int,
    shipped_at: null,
    failed_at: str (ISO-8601 UTC)
  }
  ```
- (b) NULL manifest_json on FAILED (loses forensic detail).
- (c) Same shape as SHIPPED with empty fields (loose).

**Pick: (a).** Forensic value of partial-ship roles is high;
manifest_json is the only place this state is recorded. ADR-0114
draft documents both shapes (SHIPPED vs FAILED).

#### Round 5 picks summary

| PB | Pick | One-line |
|---|---|---|
| 24 | (b) two-pass audit gate | Closes pending-vs-pending duplicate gap. |
| 25 | (a) SQLite first inside admin_tx | admin_tx rolls back on FalkorDB fail. |
| 26 | (b) audit-gate snapshot pattern | Lock-free propose; `shipped_in_release IS NULL` is natural cut. |
| 27 | (a) 4 EVT_* shapes locked | Phase 22 precedent. |
| 28 | (a) FAILED-specific manifest_json | Per-role independence makes partial-ship state load-bearing. |

### Round 0 — Pre-impl re-analysis (PB-Z1..PB-Z20)

Pre-impl re-analysis chat (2026-05-22, post-design-lock). User instructed
"reanalyze the plan and list your pushbacks, if important, with options."
Three iterations of pushbacks landed; user accepted all 12. Picks lock
the rerun-recovery substrate + ADR Status-flip uniformity + DAG
enumeration. No re-litigation of Rounds 1-5 locks; refinements only.

#### PB-Z1 — Partial-ship rerun structurally blocked by audit gate

Round 1 PB-1(b) "per-role independence; admin reruns on partial-ship"
combined with Round 5 PB-24(b) two-pass audit gate produces a silent
correctness gap: on partial-ship FAILED, the audit gate's cross-mg
pass on rerun fires blocking findings against the SAME admin's
prior-shipped canonical content (probe-confirmed at `mindsos_admin/
similarity.py:271` — cross-mg does NOT self-exclude by node_id).
Admin is locked out of rerunning by their own partial-success. PB-
1(b)'s "admin reruns" handwave silently assumed manual FalkorDB
DELETE before retry.

Options: (a) Accept; ship operational-recovery doc + admin verb at P25 /
**(b) MERGE-semantics + audit-gate suppression on rerun** / (c) `_
release_id_partial_ship` Cypher property / (d) Ship-as-is; admin
manual cleanup documented.

**Pick: (b).** Rerun becomes first-class without new schema; matches
FalkorDB MERGE semantics. ADR-0114 §am3 + ADR-0118 §am2 absorb.

#### PB-Z2 — Per-role copy MERGE vs MOVE semantics unspecified

Resolution gates PB-Z1 pick: MERGE-semantics rerun needs per-role-
clear NOT to happen before all roles ship; MOVE-semantics needs
per-role clear immediately. Incompatible interpretations.

Options: **(a) all-roles-then-clear** / (b) per-role clear / (c) no
clear at all.

**Pick: (a).** Symmetric with PB-Z1(b); pending == admin curation
buffer; clearing happens only on full release success.

#### PB-Z3 — admin_tx rollback discards roles-shipped list

PB-26(b)'s admin_tx wraps SELECT → audit → FalkorDB copies → INSERT
releases → UPDATE pending stamp. On copy failure, admin_tx ROLLBACK
undoes SQLite side. Writing the FAILED row with `roles_shipped_before_
failure` requires a list tracked across the exception boundary.

Options: **(a) two admin_tx blocks + Python local list** / (b) eager-
write FAILED row updated in-place / (c) per-role admin_tx (defeats
PB-26(b)) / (d) WAL pattern.

**Pick: (a).** Two admin_tx blocks: outer wraps happy path; on
exception, exit; open second admin_tx for FAILED row write using
Python-local roles_shipped list. KeyboardInterrupt window admitted
in §6 as single-process out-of-scope.

#### PB-Z4 — PB-13(a) "drop the lint rule" loses drift guard

The lint rule's purpose was preventing future `MetagraphSnapshot.of(`
calls outside `mindsos_server/`, not detecting existing. Module is
publicly importable from `mindsos_core`; zero-cost grep test was
the only guard.

Options: (a) Accept PB-13(a) drop / **(b) zero-consumer assertion
test** / (c) Delete the module entirely.

**Pick: (b).** `tests/phase_24/test_metagraph_snapshot_zero_consumers.py`
greps `MetagraphSnapshot\.(of\|restore_into)` across `mindsos_*/`
(excluding `mindsos_core/metagraph_snapshot.py` + tests of it) and
asserts empty result. PB-13(a) reframes from "lint rule dropped" to
"zero-consumer assertion ships."

#### PB-Z5 — ADR-0010 not amended for admin↔server edges

§4 ADR delta says "ADR-0010 is **not** amended" but adding a new
allowed edge IS an amendment to ADR-0010's isolation contract.
ADR-0010 §Decision says only "KL must not import mindsos_server."
Codifying admin's DAG position via test alone leaves the canonical
contract under-specified.

Options: (a) Accept; test is contract / **(b) ADR-0010 §am1 at this
ship** / (c) New ADR.

**Pick: (b).** Pure documentary; extends §4 ADR delta 11 → 12;
enumerates: admin → server forbidden; server → admin allowed (this
ship's new edge); admin → knowledge allowed (existing); knowledge →
admin forbidden.

#### PB-Z6 — Inconsistent Status-flip treatment

ADRs 0114/0115/0118/0129/0141/0144 YAML already `Accepted` and 0007
`Superseded` (pre-flipped at design pass); but ADRs 0049/0053/0056
still YAML `Accepted` despite §4 ADR delta listing all three as
"Accepted → Superseded at this ship." Six pre-flipped, three not.

Options: (a) Accept asymmetry; flip 0049/0053/0056 in impl PR / (b)
Walk back the six pre-flips / **(c) Pre-flip 0049/0053/0056 to match
uniform design-pass-Status convention.**

**Pick: (c).** Phase 18/20/22 established pre-flip convention; (a)
accepts incoherence; (b) walks back precedent. (c) one convention
for all 10 Status flips.

#### PB-Z7 — Audit-gate rerun-suppression node-id source

PB-Z1(b) accepted suppression but didn't pin where the gate gets the
canonical node-ids it should exclude. PB-28 FAILED shape currently
lists only `roles_shipped_before_failure: list[str]` (role names),
unconstructible into a node-id exclusion set.

Options: **(a) Extend FAILED manifest_json** with `failed_release_
canonical_node_ids: dict[role, list[node_id]]` / (b) FalkorDB-side
marker property / (c) Re-derive from `included_mutation_ids` (broken
— Z1(b) locks `included_mutation_ids = []` on FAILED).

**Pick: (a).** Symmetric with PB-Z3(a)'s local-list tracking. ADR-
0114 §am3 absorbs.

#### PB-Z8 — pending_global FalkorDB clear timing

PB-Z2(a) "all-roles-then-clear" didn't pin: clear-via-DELETE-inside-
admin_tx, async cleanup, or never-clear. Each has consequences for
audit-gate semantics on subsequent ships.

Options: **(a) After-all-roles clear inside same admin_tx, SHIPPED-
only path** / (b) Never clear; JOIN-filter in audit gate (compute_
similarity signature change needed) / (c) Async cleanup verb.

**Pick: (a).** Pending stays bounded; compute_similarity signature
unchanged; matches ADR-0118 §2 "clears pending" literal. FAILED path
leaves pending intact (rerun consumes it).

#### PB-Z9 — Per-role copy Cypher: MERGE-on-id, probe-confirmed required

Probe (`mindsos_admin/similarity.py:271`): cross-mg form does NOT
self-exclude by node_id (requires `comparison_mg is mg` which is
False on cross-mg). PB-Z1(b) suppression machinery is required
regardless of copy semantics; AND copy must be MERGE-on-node_id so
rerun is FalkorDB-side idempotent (no duplicate canonical nodes).

Options: **(a) Per-role MERGE-on-node_id Cypher template** / (b)
CREATE-new-id (creates duplicates on rerun).

**Pick: (a).** Pending node_id IS canonical node_id; lifecycle
preserves identity. ADR-0118 §am2 absorbs.

#### PB-Z10 — ADR + import-isolation test same-commit sequencing

Implementer discipline: PB-Z5(b)'s ADR-0010 §am1 prose and `tests/
phase_24/test_import_isolation_phase24.py` must land in the same
commit so the test references the locked contract. Not a re-decision.

**Pick:** same-commit discipline; no options.

#### PB-Z11 — ADR-0115 signature shape: single pending_global Metagraph

ADR-0115 §1 code says `pending_global[role]` (Mapping syntax); Phase
14's pattern + canonical_global symmetry suggests a SINGLE pending_
global Metagraph with N role-graphs.

Options: **(a) Single pending_global Metagraph parallel to canonical**
/ (b) Per-role pending Metagraphs (10+ separate Metagraph objects;
breaks MetagraphView consumption contract) / (c) Mapping wrapped
around the same underlying Metagraph.

**Pick: (a).** Documentary correction in ADR-0115 §1 + design log §5.

#### PB-Z12 — `ensure_global_role_graph` reuse for pending bootstrap

Phase 14's `ensure_global_role_graph(metagraph, role)` accepts the 6
Global roles + `alignment:` prefix. With Z11(a) (single pending_
global Metagraph), the helper works as-is — pending IS its own
Metagraph object, identical role-graph schemas as canonical.

Options: (a) Add `ensure_pending_global_role_graph` helper / **(b)
Reuse existing helper with pending Metagraph as `metagraph` arg** /
(c) Add `pending:<role>` prefix support.

**Pick: (b).** No new bootstrap surface; ~10 LOC `bootstrap_global`
extension creates pending Metagraph then loops `ensure_global_role_
graph(pending_mg, role)` for each role.

#### PB-Z13 — Propose-time FalkorDB write: incremental Cypher

PB-Z11(a) locks topology; PB-Z3(a) locks SQLite-first ordering; but
the FalkorDB write shape was unspecified. Full `MetagraphRepository.
persist()` iterates all nodes/edges (probe-confirmed write-through);
admin batches of N proposes cost O(N²) cumulative.

Options: **(a) Incremental Cypher MERGE-on-id at propose-time** /
(b) Full persist (acceptable cost at admin-rare frequency) / (c)
Defer in-memory mutation; reload via lazy hydration.

**Pick: (a).** Symmetric with PB-Z9(a)'s release-time MERGE template.
ADR-0118 §am2 absorbs.

#### PB-Z14 — (consolidated under PB-Z13)

Pending Metagraph persistence concerns absorbed into PB-Z13's
incremental-Cypher pick. No standalone pushback.

#### PB-Z15 — Rerun detection algorithm

PB-Z7(a) supplies the suppression-set source; PB-Z15 pins which
FAILED rows release_update consults. Naive "every FAILED ever"
suppresses stale node-ids from year-old recovered attempts.

Options: **(a) Suppression set = union over FAILED rows with
`release_id > (last SHIPPED release_id)`** / (b) Most-recent FAILED
only / (c) Time-bound / (d) Per-mutation tracking.

**Pick: (a).** "Newer than last SHIPPED" watermark; SHIP advances;
older FAILEDs naturally retire. ADR-0114 §am3 absorbs.

#### PB-Z16 — EmptyComparisonError propagation behavior

ADR-0144 §am2 says "v1 default is to propagate" but design log
never locked the FAILED-path behavior. Without locking,
EmptyComparisonError surfaces as uncaught exception bypassing
FAILED-row write.

Options: **(a) Propagate as FAILED with `error_class="empty_
comparison"`** / (b) Catch + skip degenerate pair / (c) Re-raise as
BlockingFindingError (loses error_class distinction).

**Pick: (a).** ADR-0114 §am3 documents `error_class` enum closure:
`blocking_similarity_findings | empty_comparison | FalkorDBWriteError`.
Adding new error_class requires ADR §am.

#### PB-Z17 — (consolidated; empty-release FAILED row deferred)

Considered + dropped at Round 0+ analysis. PB-21(a) `EmptyReleaseError`
+ CLI exit code 7 + no row suffices. No standalone pushback.

#### PB-Z18 — (consolidated; PromotionItemKind forward-shape unchanged)

Considered at Round 0+ analysis; PB-18(a) full PIVOT §7.1 shape +
PB-19(b) NodeSpec-only + EdgeSpec/MetaEdgeSpec forward-refs hold.
No re-opening of Round 4 picks.

#### PB-Z19 — (consolidated; diagnostics CLI deferred to P25)

`mindsos server release list-failed` + `show` deferred. Existing
`query-audit --event-type EVT_RELEASE_FAILED` suffices at v1.

#### PB-Z20 — Pending-clear DELETE template must be node-id-scoped

PB-Z8(a) accepted but Cypher shape unspecified. Naive `MATCH (n)
DETACH DELETE n` against pending_global_<role> deletes concurrent
propose's new node, silently breaking PB-26(b) lock-free guarantee.

Options: **(a) Node-id-scoped DELETE: `MATCH (n) WHERE n.node_id IN
$snapshot_node_ids DETACH DELETE n`** / (b) Add `pending_node_id`
column to pending_mutations / (c) Lock pending writes during release_
update.

**Pick: (a).** Node-ids extracted from `pending_mutations.payload_json`
for the snapshot set, grouped by `target_role`. Concurrent propose's
new node has a different node_id and survives. ADR-0114 §am3 absorbs.

#### Round 0 picks summary

| PB | Pick | One-line |
|---|---|---|
| Z1 | (b) MERGE + audit-gate suppression on rerun | Rerun becomes first-class without new schema |
| Z2 | (a) all-roles-then-clear | Pending == admin curation buffer; clear on full success |
| Z3 | (a) two admin_tx blocks + Python local list | Keep PB-26(b) atomicity; KeyboardInterrupt window admitted |
| Z4 | (b) zero-consumer assertion test | Guard prevents drift, not detects post-hoc |
| Z5 | (b) ADR-0010 §am1 at this ship | Close canonical contract under-spec; 11 → 12 ADR touches |
| Z6 | (c) pre-flip 0049/0053/0056 | One convention for all 10 Status flips |
| Z7 | (a) FAILED manifest_json gains failed_release_canonical_node_ids | Suppression set source pinned |
| Z8 | (a) after-all-roles clear inside admin_tx (SHIPPED only) | Pending bounded; compute_similarity unchanged |
| Z9 | (a) per-role MERGE-on-node_id Cypher template | Idempotent rerun at FalkorDB level |
| Z10 | (—) ADR + test same-commit discipline | Implementer note |
| Z11 | (a) single pending_global Metagraph parallel to canonical | ADR-0115 signature correction |
| Z12 | (b) reuse `ensure_global_role_graph` with pending Metagraph arg | No new helper |
| Z13 | (a) incremental Cypher MERGE at propose | Avoids O(N²) cumulative cost |
| Z15 | (a) suppression set = FAILED rows since last SHIPPED | Natural watermark; SHIP advances |
| Z16 | (a) EmptyComparisonError → FAILED with error_class="empty_comparison" | Locks ADR-0144 §am2 default |
| Z20 | (a) DELETE scoped to snapshot node-ids via payload_json | Preserves PB-26(b) lock-free propose |

## §2. Final locks consolidated (28-pick reference)

| # | Pick | ADR cite / precedent |
|---|---|---|
| 1 | (b) per-role independence; admin reruns on partial-ship | ADR-0129 §am2 |
| 2 | (d) post-PB shrink; no formal split | PB-3 / PB-4 / PB-5 / PB-11 |
| 3 | (a) ATOM only at P24 | PHASE_MAP §24 amends |
| 4 | (a) lazy migration → P25 | ADR-0118 §am1 + Phase 14 PB-6 precedent |
| 5 | (a) draft 0114 + 0115 + 0120 only | PIVOT §7 ADR plan |
| 6 | (a) keep EVT_* convention | Phase 18-22 shipped precedent |
| 7 | (a) drop snapshot from release_update | ADR-0129 §am2; probe confirmed |
| 8 | (a) `mindsos_admin.propose_for_promotion` | ADR-0118 §am1 + ADR-0141 §am1 |
| 9 | (a) `mindsos_admin/audit_gate.py` | ADR-0144 §am1 symmetry |
| 10 | (a) SHIPPED + FAILED only | ADR-0114 draft; PIVOT §7.5 amends |
| 11 | (a) admin-direct ATOM only at P24 | ADR-0008 §am1 + ADR-0118 §am1 |
| 12 | (a) RLock outer + admin_tx inner | ADR-0006 § (RLock) + Phase 22 admin_tx |
| 13 | (a) ADR-0129 §am2; module retained; lint rule dropped | Phase 23 §7 #4 re-opens |
| 14 | (b) `mindsos server release {propose,ship}` | Phase 22 admin subgroup ≠ release subgroup |
| 15 | (a) eager pending-Global bootstrap | Phase 15a `bootstrap_global` extends |
| 16 | (a) hardcoded ATOM dispatch | YAGNI; PIVOT §7.1 registry amend |
| 17 | (a) ship parent_release_id at P24 | PIVOT §7.5 full table shape |
| 18 | (a) full PIVOT §7.1 PromotionProposal shape | Phase 18-22 dataclass precedent |
| 19 | (b) NodeSpec only; EdgeSpec / MetaEdgeSpec forward-refs | PEP 563 |
| 20 | (c) auto-abort + FAILED row | ADR-0144 §Decision strict-default |
| 21 | (a) EmptyReleaseError raise | `releases` table semantic |
| 22 | (a) full manifest_json SHIPPED shape | Phase 25 consumer contract |
| 23 | (a) 2 new caps (PROPOSE_MUTATION + APPROVE_RELEASE) | ADR-0002 §am2; 7→9 caps |
| 24 | (b) two-pass audit gate | Phase 16 PB-M2 intra-mg + cross-mg |
| 25 | (a) SQLite first inside admin_tx | Phase 22 admin_tx precedent |
| 26 | (b) audit-gate snapshot pattern | `shipped_in_release IS NULL` natural cut |
| 27 | (a) 4 EVT_* shapes locked at design | Phase 22 PB-16 precedent |
| 28 | (a) FAILED-specific manifest_json shape | Per-role independence forensics |
| Z1 | (b) MERGE + audit-gate suppression on rerun | Round 0 — rerun-recovery first-class |
| Z2 | (a) all-roles-then-clear | Round 0 — pending bounded |
| Z3 | (a) two admin_tx blocks + Python local list | Round 0 — atomicity preserved |
| Z4 | (b) zero-consumer assertion test | Round 0 — drift guard |
| Z5 | (b) ADR-0010 §am1 at this ship | Round 0 — DAG enumeration |
| Z6 | (c) pre-flip 0049/0053/0056 | Round 0 — Status-flip uniformity |
| Z7 | (a) FAILED manifest_json + failed_release_canonical_node_ids | Round 0 — suppression set source |
| Z8 | (a) after-all-roles clear, SHIPPED-only path | Round 0 — pending lifecycle |
| Z9 | (a) per-role MERGE-on-node_id Cypher | Round 0 — copy template locked |
| Z11 | (a) single pending_global Metagraph | Round 0 — topology lock |
| Z13 | (a) incremental Cypher at propose | Round 0 — write template |
| Z15 | (a) FAILED rows since last SHIPPED watermark | Round 0 — rerun detection |
| Z16 | (a) EmptyComparisonError → FAILED error_class="empty_comparison" | Round 0 — error_class enum closure |
| Z20 | (a) node-id-scoped DELETE template | Round 0 — concurrency-safe clear |

## §3. Cross-chat dependencies

### Backward (Phase 24 inherits)

- **Phase 10 (snapshot primitives)** — `MetagraphSnapshot.of` +
  `.restore_into` retained as defensive Core primitive. Zero
  consumer at P24 per PB-13(a).
- **Phase 11 (soft-delete substrate)** — Phase 24 inherits;
  ADR-0116 documentary debt deferred.
- **Phase 14 (KL bootstrap)** — `ensure_global_role_graph` /
  `ensure_local_role_graph` consumed by `mindsos_admin/bootstrap.py`
  extension at PB-15(a) eager pending-Global creation.
- **Phase 15a (admin importers)** — `mindsos_admin/bootstrap.py::
  bootstrap_global` extends for pending-Global symmetry.
- **Phase 16 (similarity surface)** — `compute_similarity` cross-mg
  form (PB-K2) consumed by audit gate. Cross-mg + intra-mg both at
  release-time per PB-24.
- **Phase 18 (server user store + auth)** — capabilities roster;
  ADR-0002 §am1 UPPER-casing.
- **Phase 19 (sessions)** — SessionTTL injection; admin_session
  validation pattern.
- **Phase 20 (admin reset)** — `mindsos_server/admin.py` module
  precedent.
- **Phase 21 (audit log reader)** — `_require_or_audit` (mindsos_
  server/authz.py) + EVT_AUDIT_QUERY happy-path-audit pattern.
- **Phase 22 (admin ops)** — `admin_tx` BEGIN IMMEDIATE wrapper
  reused for pending_mutations + releases writes; six-verb subgroup
  precedent (extended at PB-14(b) to `release` subgroup, not
  `admin`).
- **Phase 23 (RETIRED 2026-05-22)** — ADR-0129 §am1 6 clauses
  honoured (#1-3 re-opened via §am2; #4 lint rule dropped per
  PB-13(a); #5-6-7 honoured); 7 carry-forwards consumed (#1-3 +
  #4 re-opened; #5-7 honoured).

### Forward (Phase 24 → later phases)

- **Phase 25 (SessionProtocol + MindsOSServer + LocalPersister +
  lazy migration)** — Consumes Phase 24's `releases.manifest_json`
  shape per PB-22(a). Implements source-user-Local propose path
  (P24 raises NotImplementedError for `source_user_id is not None`).
  Lands the 4 deferred audit events (EVT_DRAFT_FROZEN +
  EVT_DRAFT_UNFROZEN + EVT_MIGRATION_APPLIED + EVT_MIGRATION_FAILED).
  Adds `CAN_READ_PENDING_GLOBAL` capability at first direct-read
  consumer (admin inspection verb at v2 or P25 if MindsOSServer
  needs it).
- **Post-Core-CompositionalMetaEdge phase** — STRUCTURE
  PromotionItemKind validator + ADR-0117 + ADR-0119.
- **Post-L3-ship phase (33-35)** — PIPELINE PromotionItemKind
  validator (cross-layer L3+L2).
- **First multi-kind phase** — `register_promotion_kind()` registry
  retrofit per PB-16(a).
- **Phase 26 (Integration A)** — composes P24 CLI verbs; release-
  ship under RELEASE_SHIP_LOCK + audit-gate integration scenario.
- **Phase 38 (doc consolidation)** — `docs/usage/server/promotion.md`
  + `docs/usage/server/release.md` + `docs/concepts/release-model.md`
  per Phase 18-22 documentation-deferral pattern.

### Memory + feedback rules consumed

- `feedback_pushback_format_with_picks.md` — 28 picks across 5
  rounds; pick + final picks summary per round.
- `feedback_pre_impl_probe_check_existing_modules.md` — probe
  confirmed:
  * P24 surfaces absent (`release.py`, `promotion.py` in mindsos_
    admin / mindsos_server)
  * Phase 10/16/22 surfaces intact
  * ADRs 0113-0117/0119/0120 not drafted; ADR-0115 not drafted
  * `MetagraphRepository.persist` write-through (PB-7 probe)
- `feedback_phase_baseline_literal_audit.md` — schema_version 3 → 4
  bump; Phase 19 dynamic-baseline (`TestAll6PkgsAtCurrentPhase`
  against manifest version) handles `+phase22 → +phase24` (skip
  +phase23) automatically.
- `feedback_l1_api_signature_probe_before_writing_tests.md` — probe
  required for:
  * `compute_similarity(mg, candidates, *, role, target_mg=None,
    threshold_blocking=0.85, threshold_review=0.5)` confirmed at
  * `admin_tx(conn)` Phase 22 pattern
  * `write_audit(conn, *, actor, event, target, extra)` Phase 21
    pattern
  * `_require_or_audit(conn, session, capability, event, target)`
    Phase 21 pattern
- `feedback_test_image_rebuild_after_source_change.md` — rebuild
  `mindsos-test` after new module additions.
- `feedback_smoke_harness_host_native.md` — host-native smoke is
  canonical; docker --rm has no ~/.mindsos mount.
- `feedback_pk_column_per_table_probe.md` — `pending_mutations.
  mutation_id` + `releases.release_id` PK columns; verification
  queries use literal column names.

## §4. ADR delta at Phase 24 ship

**13 ADR touches** (was 11 at Round-5 lock; Round 0 added 2): 3 new
drafts + 4 Status flips + 3 indirect Supersessions + 4 documentary
§amendments + 1 cap-roster §amendment + 1 rename-ratification
§amendment + 1 DAG-enumeration §amendment (Round 0 PB-Z5(b)).

**Round 0 amendments added:**

* **ADR-0010 §am1** (PB-Z5(b)) — DAG enumeration extended for
  mindsos_admin: admin → server forbidden; server → admin allowed
  (this ship's new edge); admin → knowledge allowed (existing);
  knowledge → admin forbidden.
* **ADR-0114 §am3** (PB-Z7/Z8/Z15/Z16/Z20) — rerun-recovery substrate
  locks: FAILED manifest_json + `failed_release_canonical_node_ids`;
  rerun suppression-set query (FAILED rows since last SHIPPED);
  after-all-roles clear inside admin_tx (SHIPPED only) with node-id-
  scoped DELETE template; `error_class` enum closure.
* **ADR-0118 §am2** (PB-Z9/Z13) — Cypher template locks: per-role
  MERGE-on-node_id at release-time; incremental Cypher MERGE-on-id
  at propose-time (not full persist).
* **ADRs 0049/0053/0056** (PB-Z6(c)) — pre-flipped Accepted →
  Superseded in YAML frontmatter + body header to match the design-
  pass-Status convention used for 0114/0115/0118/0129/0141/0144/0007
  (12 of 12 Status flips uniform at impl start).

Original 11 touches (Rounds 1-5 lock):

| ADR | Action | Reason |
|---|---|---|
| **0114** | NEW draft (Proposed → Accepted at this ship) | Release manifest + version DB schema; `pending_mutations` + `releases` SQLite tables; schema v3 → v4. |
| **0115** | NEW draft (Proposed → Accepted at this ship) | Audit gate + impact report; two-pass similarity per PB-24; auto-abort + FAILED row per PB-20. |
| **0120** | NEW draft (Proposed; contract only at P24; impl at P25/Cap-rewrite phase) | Cross-layer rewrite handler contract. |
| **0118** | Status: Proposed → Accepted + §am1 | §am1: surface relocated `kl.propose_for_promotion` → `mindsos_admin.propose_for_promotion` (PB-8); lazy migration first-consumer Phase 25 (PB-4); source-user path defers to P25 (PB-11). |
| **0141** | Status: Proposed → Accepted + §am1 | §am1: surface relocated `mindsos_server.propose_for_promotion` → `mindsos_admin.propose_for_promotion` (PB-8); KL no `promote()` to delete in halvim per ADR-0138 honoured by absence (Phase 14 PB-6). |
| **0144** | Status: full Accept + §am1 retires + §am2 | §am2: §Placement Accepted at this ship; audit gate consumes `compute_similarity` two-pass form per PB-24 (cross-mg + intra-mg); §am1 partial-flip retires. |
| **0129** | §am2 | §am2: snapshot in `release_update` confirmed vestigial via PB-7 probe; module retained as defensive Core primitive; CI lint rule (Phase 23 §7 #4) dropped (no consumer means no drift to guard); ADR-0007 flip timing unchanged. |
| **0007** | Status: Accepted-with-banner → Superseded | Cross-user atomic promotion premise replaced by ADR-0118 per the supersession-in-progress banner; `release_update` ships at P24 closing the banner's promise. |
| **0049** | Status: Accepted → Superseded | Per Phase 16 §am1 lock; audit-gate similarity at release-ship replaces freshness gate. |
| **0053** | Status: Accepted → Superseded | Per Phase 16 §am1 lock; per-candidate atomic rollback replaced by per-role atomic ship + admin rerun. |
| **0056** | Status: Accepted → Superseded | Per Phase 16 §am1 lock; promotion-result order semantic replaced by manifest_json contract. |
| **0002** | §am2 | §am2: + `CAN_PROPOSE_MUTATION` + `CAN_APPROVE_RELEASE` capabilities; ADMIN_CAPS membership extends; USER_CAPS stays empty; roster 7 → 9. `CAN_READ_PENDING_GLOBAL` deferred per PB-23. |
| **0006** | §am1 | §am1: ratification of in-place rename `GLOBAL_PROMOTE_LOCK` → `RELEASE_SHIP_LOCK` per ADR-0118 §Consequences; substrate `threading.RLock` confirmed (PB-12). |

ADR-0010 is **not** amended. The new `mindsos_server → mindsos_admin`
import edge is allowed per CLAUDE.md "Server imports downward into
the stack" plus mindsos_admin's non-layer-stack position (separate
top-level per ADR-0140 §am1). Layer-isolation enforcement extends via
test (`tests/phase_24/test_import_isolation_phase24.py`) — codifies:
- `mindsos_server` MAY import from `mindsos_admin` (one-way edge);
  asserts release.py imports mindsos_admin.audit_gate.
- `mindsos_admin` MUST NOT import from `mindsos_server`.
- `mindsos_knowledge` MUST NOT import from `mindsos_admin` or
  `mindsos_server` (per ADR-0010).
- `mindsos_admin` MAY import from `mindsos_knowledge` (existing
  Phase 15a + Phase 16 pattern).

PHASE_MAP §24 row rewrite at ship per §1 row-rewrite rule — records
the 28-pick contract; replaces the speculative "all 4 PromotionItemKinds
+ lazy migration + 6 ADRs" with the locked admin-direct-ATOM-only
scope.

PHASE_MAP §25 row update at ship — absorbs source-user-Local propose
path + lazy migration + 4 deferred audit events +
CAN_READ_PENDING_GLOBAL cap (when first consumer ships).

## §5. Implementation references

```
mindsos_admin/                            # extends Phase 15a + 16 pkg
├── __init__.py                           # +exports: propose_for_promotion + PromotionResult +
│                                         #  PromotionProposal + PromotionItem + PromotionItemKind +
│                                         #  NodeSpec + audit_gate.run + AuditGateResult +
│                                         #  related errors
├── promotion.py                          # NEW: propose_for_promotion(admin_session, proposal) ->
│                                         #  PromotionResult; ATOM dispatch hardcoded; admin-direct
│                                         #  only; source_user_id != None raises
│                                         #  NotImplementedError; two-store write per PB-25(a)
├── audit_gate.py                         # NEW: run(admin_session, pending_set, *, canonical_global,
│                                         #  pending_global) -> AuditGateResult; two-pass
│                                         #  compute_similarity per PB-24(b); blocking → abort
├── bootstrap.py                          # MODIFIED: bootstrap_global extends to create
│                                         #  pending_global_<role> alongside canonical (PB-15(a))
├── exceptions.py                         # MODIFIED: +DuplicateProposalError (not used at P24;
│                                         #  reserved for future propose-time dedup);
│                                         #  +BlockingFindingError; +EmptyReleaseError;
│                                         #  +PendingMutationNotFoundError
└── (all other Phase 15a+16 files unchanged)

mindsos_server/                           # extends Phase 18-22 pkg
├── __init__.py                           # +exports: release_update + ReleaseResult +
│                                         #  RELEASE_SHIP_LOCK + 4 EVT_* + 2 CAPS
├── release.py                            # NEW: release_update(admin_session) -> ReleaseResult;
│                                         #  RLock outer + admin_tx inner; audit-gate snapshot
│                                         #  set (PB-26(b)); auto-abort + FAILED row (PB-20(c));
│                                         #  EmptyReleaseError raise (PB-21(a))
├── locks.py                              # NEW: RELEASE_SHIP_LOCK = threading.RLock() (PB-12(a))
├── capabilities.py                       # MODIFIED: +CAN_PROPOSE_MUTATION + CAN_APPROVE_RELEASE
│                                         #  (PB-23(a)); ADMIN_CAPS extends; ADR-0002 §am2
├── audit.py                              # MODIFIED: +EVT_PROMOTION_PROPOSED +
│                                         #  EVT_PROMOTION_REJECTED + EVT_RELEASE_SHIPPED +
│                                         #  EVT_RELEASE_FAILED (PB-27(a))
└── _schema.py                            # MODIFIED: _SCHEMA_VERSION 3 → 4;
                                          #  + _DDL_PENDING_MUTATIONS + _DDL_RELEASES +
                                          #  forward-only migration step

mindsos_cli/commands/server.py            # MODIFIED: +release_app Typer subgroup with
                                          #  propose-for-promotion + release-ship verbs
                                          #  (PB-14(b)); +_release_exit_for mapper; exit codes
                                          #  7-8 extension

tests/phase_24/                           # ~22 test files (estimated)
├── __init__.py
├── conftest.py                           # promotion_proposal + atom_admin_direct_proposal +
│                                         #  pending_global_seeded + empty_pending + canonical_global_
│                                         #  with_duplicates fixtures
├── test_propose_for_promotion_atom.py    # happy path + pending_mutations row + pending_global
│                                         #  FalkorDB node + EVT_PROMOTION_PROPOSED audit
├── test_propose_for_promotion_source_user_deferred.py  # source_user_id != None →
│                                         #  NotImplementedError (PB-11)
├── test_propose_kinds_dispatch.py        # STRUCTURE/SUBGRAPH/PIPELINE → NotImplementedError
│                                         #  (PB-3 + PB-16); ATOM works
├── test_propose_two_store_atomicity.py   # FalkorDB fail → admin_tx rolls back SQLite (PB-25)
├── test_release_update_happy.py          # 1 pending → SHIPPED row + canonical mutated +
│                                         #  pending cleared + EVT_RELEASE_SHIPPED audit
├── test_release_update_empty.py          # EmptyReleaseError (PB-21)
├── test_release_update_audit_gate_blocking.py  # similarity > 0.85 → FAILED row +
│                                         #  EVT_RELEASE_FAILED (PB-20)
├── test_release_update_audit_gate_intra_pending.py  # 2 duplicate pending → blocking
│                                         #  (PB-24(b))
├── test_release_update_audit_gate_cross_mg.py  # candidate-vs-canonical → blocking
├── test_release_update_per_role_partial_failure.py  # role 3 of 5 fails → FAILED row +
│                                         #  manifest_json.roles_shipped_before_failure
│                                         #  (PB-1 + PB-28)
├── test_release_update_propose_concurrency.py  # propose runs during release_update;
│                                         #  audit-gate-snapshot set excludes late propose
│                                         #  (PB-26)
├── test_release_ship_lock.py             # RLock serializes 2 release_updates
├── test_pending_global_bootstrap.py      # bootstrap_global creates both canonical and
│                                         #  pending_global_<role> (PB-15)
├── test_pending_mutations_schema.py      # 4 columns + indexes + CHECK constraint
├── test_releases_schema.py               # 4 columns + parent_release_id + status CHECK
│                                         #  (SHIPPED/FAILED only)
├── test_evt_promotion_proposed_payload.py  # payload shape per PB-27
├── test_evt_release_shipped_payload.py
├── test_evt_release_failed_payload.py
├── test_manifest_json_shipped_shape.py   # PB-22
├── test_manifest_json_failed_shape.py    # PB-28
├── test_capability_denial_propose.py     # CAN_PROPOSE_MUTATION
├── test_capability_denial_release.py     # CAN_APPROVE_RELEASE
├── test_cli_release_subgroup.py          # `mindsos server release propose-for-promotion` +
│                                         #  `mindsos server release ship` (PB-14)
├── test_import_isolation_phase24.py      # server → admin OK; admin → server forbidden;
│                                         #  KL → server forbidden; ADR-0010 §am1 codified
│                                         #  (PB-Z5(b) + PB-Z10 same-commit-as-ADR-0010-§am1)
├── test_metagraph_snapshot_zero_consumers.py  # NEW (PB-Z4(b)) — greps
│                                         #  MetagraphSnapshot.(of|restore_into) across
│                                         #  mindsos_*/ asserting empty result
├── test_release_update_rerun_after_failed.py  # NEW (PB-Z1(b) + PB-Z15(a)) — rerun after
│                                         #  FAILED uses suppression set + MERGE-on-id
│                                         #  idempotency; ships successfully
├── test_release_update_merge_idempotent_on_rerun.py  # NEW (PB-Z9(a)) — rerun's MERGE
│                                         #  against prior-shipped canonical is no-op
├── test_release_update_concurrent_propose_survives_clear.py  # NEW (PB-Z20(a)) —
│                                         #  node-id-scoped DELETE doesn't touch concurrent
│                                         #  propose's new node
├── test_release_update_empty_comparison_propagates.py  # NEW (PB-Z16(a)) —
│                                         #  EmptyComparisonError → FAILED row with
│                                         #  error_class="empty_comparison"
├── test_audit_gate_suppression_set.py    # NEW (PB-Z7(a)) — suppression set populated from
│                                         #  FAILED manifest_json.failed_release_canonical_node_ids
└── test_propose_incremental_write.py     # NEW (PB-Z13(a)) — propose's FalkorDB write is
                                          #  one-shot MERGE-on-id, not full metagraph persist

docs/usage/server/promotion.md            # DEFERRED to Phase 38 doc-review per pattern
docs/usage/server/release.md              # DEFERRED to Phase 38
docs/concepts/release-model.md            # DEFERRED to Phase 38 per Phase 14a §3 PB-M1
                                          #  ownership lock

# Version bump +phase22 → +phase24 across 9 sites / 11 lines (skip +phase23):
mindsos_core/__init__.py
mindsos_knowledge/__init__.py
mindsos_admin/__init__.py
mindsos_instances/__init__.py
mindsos_cli/__init__.py
mindsos_server/__init__.py
pyproject.toml [project] version + description
mindsos_cli/manifest.toml [mindsos] phase + version
docker-compose.yml image tags (2 occurrences: mindsos / mindsos-test)
```

## §6. Scope boundaries (out-of-scope at Phase 24 ship)

- **Source-user-Local propose path** (`PromotionItem.source_user_id is
  not None`) — deferred to Phase 25 alongside cross-user-read substrate
  (ADR-0008 §am1). P24 raises `NotImplementedError`.
- **Lazy migration code path** (session-start rewrite-map walk) —
  deferred to Phase 25 per PB-4(a) + Phase 14 PB-6 precedent.
  Manifest_json shape per PB-22(a) anchors the Phase 25 consumer
  contract.
- **STRUCTURE PromotionItemKind validator** — gates on Core
  CompositionalMetaEdge subclass (Phase 05a Dropped); deferred to
  post-Core-retrofit phase. P24 raises `NotImplementedError`. ADR-0117
  + ADR-0119 deferred.
- **SUBGRAPH PromotionItemKind validator** — gates on subgraph
  extractor (no precedent in halvim); deferred to own phase. P24
  raises `NotImplementedError`.
- **PIPELINE PromotionItemKind validator** — cross-layer L3+L2;
  gates on L3 ship (Phases 33-35 unshipped). Deferred to post-L3
  phase. P24 raises `NotImplementedError`.
- **`register_promotion_kind()` extensibility registry** (PIVOT §7.1)
  — hardcoded ATOM dispatch at P24 per PB-16(a). Registry retrofits
  at first multi-kind phase.
- **`CAN_READ_PENDING_GLOBAL` capability** — no direct-read consumer
  at P24 (audit gate is server-internal). Deferred to first consumer
  phase per PB-23(a).
- **Force-override on blocking findings** (`release_update(...,
  *, force=True)`) — v2 per ADR-0118 §Tradeoffs override-path-is-v2.
  P24 auto-aborts on blocking + writes FAILED row per PB-20(c).
- **Quorum-approve release lifecycle** (PROPOSED / APPROVED /
  REJECTED / WITHDRAWN states) — v2 per ADR-0118 §Tradeoffs. P24
  ships SHIPPED + FAILED only per PB-10(a).
- **`MetagraphSnapshot` module deletion** — module retained as
  defensive Core primitive per PB-13(a). Cleanup-phase deletion
  reserved for future.
- **CI lint rule guarding `MetagraphSnapshot` use** — dropped per
  PB-13(a) (no consumer means no drift). Phase 23 retirement §7 #4
  carry-forward re-opened.
- **ADRs 0113 / 0116 / 0117 / 0119 drafts** — substrate-gated;
  deferred. ADR-0113 needs lazy migration + version DB; ADR-0116
  is documentary debt (Phase 11 shipped); ADR-0117 needs
  CompositionalMetaEdge; ADR-0119 needs STRUCTURE.
- **HTTP transport for release verbs** — no HTTP roadmap per
  PHASE_MAP §1.
- **Pending-Global graph inspection admin verb** — v2.
- **WAL-bracketed per-role release-ship** — rejected at PB-1(a)
  in favour of per-role independence + admin rerun. Reserved if
  operational demand surfaces.
- **`pending_mutations.mutation_type` extension to non-PROMOTION
  values** (EDGE_ADD / EDGE_DEPRECATE per PIVOT §7.5) — CHECK
  constraint = `('PROMOTION')` at P24; extends at future-phase
  consumer. Phase 18 PB-28 actor_role CHECK precedent.

## §7. Design saturation note

Phase 24's 28-pick density is consistent with Phase 22's 27 (and
the precedent set during the R1 PB-2(d) anti-split lock). Round 5
introduced one PB-24 correctness gap (duplicate-pending detection)
that R1-R4 picks did not surface — this is the load-bearing learning
of Phase 24's design saturation: pivot-doc surfaces (PIVOT §7.1's
audit gate) read at single-pass-cross-mg semantics from the design
text; the gap surfaces only by inspection of Phase 16's
`compute_similarity` cross-mg vs intra-mg discriminator.

Round 1 PB-1 surfaced the Phase 23 retirement §7 carry-forward
re-open (multi-role rollback flaw); the inline pattern was a
documented lock that the retirement chat didn't probe against
FalkorDB per-graph atomicity semantics. PB-7 probe + PB-13 closed
the loop with snapshot fully vestigial in halvim. The Phase 24
chat's willingness to re-open locked carry-forwards is the
intended outcome of CLAUDE.md's "ADR decisions could be changed if
we get to new decisions in this chat" — Phase 24's load-bearing
contribution is closing the spec drift the retirement chat
accidentally locked.

No further pushback surfaces surfaced after PB-28; design rounds
close at saturation.

## §8. Carry-forwards from Phase 23 retirement

Phase 23 retirement §7 (PHASE_23_RETIREMENT_DESIGN_LOG.md) locked 7
carry-forwards. Phase 24 disposition:

| # | Carry-forward | Phase 24 disposition |
|---|---|---|
| 1 | Inline `MetagraphSnapshot.of` / `restore_into` call shape in `release_update` | **RE-OPENED at PB-1(b); REFINED at PB-13(a).** PB-7 probe confirmed snapshot vestigial; ADR-0129 §am2 drops the inline pattern. Module retained as defensive Core primitive. |
| 2 | Snapshot taken AFTER audit gate + AFTER lock acquisition, BEFORE first per-role copy | **Vacuous (snapshot dropped).** ADR-0129 §am2 documents. |
| 3 | On exception during per-role copy: `restore_into` then re-raise; pending stays intact | **Vacuous (snapshot dropped).** Pending stays intact for retry is independently locked at PB-1(b) per-role independence + PB-26(b) audit-gate snapshot pattern. |
| 4 | CI lint rule `grep MetagraphSnapshot.of(` outside `mindsos_server/` ships at Phase 24 | **RE-OPENED at PB-13(a); DROPPED.** No consumer means no drift to guard. |
| 5 | Runtime `DeprecationWarning` retired | **Honoured.** Phase 24 does not implement. |
| 6 | ADR-0007 flips Accepted → Superseded at Phase 24 ship | **Honoured.** §4 ADR delta. |
| 7 | Version bump `+phase22 → +phase24` (skip `+phase23`) | **Honoured.** §5 implementation references. |

Phase 23 retirement §7 #1-4 re-openings are documented in ADR-0129
§am2 (Phase 24 ship). Net effect on the retirement chat's
contribution: design-only retirement format precedent confirmed
useful; the specific contract locked (#1-3 inline pattern) was
under-probed and revised at Phase 24. Phase 17 retirement (5-LOC
shipped) and Phase 23 retirement (0-LOC) bracket the design-only-
phase shape; Phase 24 establishes that a design-only retirement
chat's locks are not load-bearing against a downstream phase's
implementation probe.
