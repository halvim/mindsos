---
phase: 25
phase_title: "Server: cross-user-read substrate (read_other_local + LocalPersister Protocol + SessionProtocol in KL)"
layer: L0 / cross
status: design-locked
date_locked: 2026-05-23
design_rerun: 2026-05-23  # multi-round re-litigation: Rounds 0→4 cascaded through PB-1..PB-47 with progressive scope collapse
branch: phase-25 (to-be-cut from origin/main HEAD = a6bd4fd Phase 24 squash)
tag_on_confirm: phase-25-confirmed
net_new: true   # NEW modules: mindsos_server/orchestrator.py, mindsos_server/persistence/, mindsos_knowledge/types.py
design_rounds: 5   # Rounds 0-4 with re-litigation; Round 5 concrete shapes in §5
total_picks: ~17   # 47 PB candidates surfaced; ~30 collapsed via re-litigation cascade
prior_phase: 24
next_phase: 26
---

# Phase 25 Design Log — Server: cross-user-read substrate

## §0. Scope summary

Phase 25 absorbs ONE of Phase 24's seven enumerated deferrals: the
**cross-user-read substrate** (`read_other_local` ctx mgr +
`LocalPersister` Protocol + `InMemoryLocalPersister` +
`SessionProtocol` in KL + per-user mutex registry first consumer +
`_installed_locals` refcount-install pattern).

The other six Phase 24 deferrals — source-user-Local propose path,
lazy migration, `MindsOSServer` class, SQLite/Falkor persisters,
freeze, DRAFT_FROZEN/UNFROZEN/MIGRATION_APPLIED/MIGRATION_FAILED
audit events — defer further to the first phase that ships a user-
Local-write surface (post-P25). Multi-round re-litigation through
this chat surfaced the recursive "no-caller" critique against
shipping those substrates at P25 without a live first consumer; the
cleanest split is "v1 ships cross-user-read with `read-local` admin
diagnostic as first consumer; everything else defers."

Phase 25 also closes a **latent Phase 24 FK bug** (PB-30 + Phase 24
PB-Z21 forward-shape gap): `pending_mutations.proposer_admin_user_id`
+ `releases.proposer_admin_user_id` FKs are `NO ACTION` (effectively
RESTRICT). Hard-deleting an admin with promotion history bubbles raw
`IntegrityError`. P25 extends `hard_delete_user` with a UNION pre-
check and `UserHasPromotionHistoryError` (ADR-0114 §am4).

Five design rounds with iterative re-litigation, ~17 final picks
locked from 47 candidates surfaced. Re-litigation cascade is the
load-bearing methodology lesson — each round both added new
pushbacks and reconsidered prior locks; many original Round 0/1
picks were reversed at Round 2/3 after probe-revealed substrate
constraints. Pattern: scope shrunk monotonically across rounds.

**This phase does NOT ship:** source-user-Local propose path (PB-1
revised); lazy migration + `apply_rewrite_map` + ADR-0120 KL impl
(PB-3 reversed); SQLiteLocalPersister + FalkorDBLocalPersister +
MetagraphDump shape (PB-4 reversed + PB-14 deferred); `MindsOSServer`
class (PB-38 — orchestrator ships as free functions; class defers);
lazy hydration / LRU eviction / ADR-0125 §am1 flip (PB-7 reversed →
eager; PB-37 → caller-Local install collapse); EVT_DRAFT_FROZEN /
EVT_DRAFT_UNFROZEN / EVT_MIGRATION_APPLIED / EVT_MIGRATION_FAILED
(PB-1 + PB-3 reversals); CAN_READ_PENDING_GLOBAL capability (PB-9 —
no consumer); admin reject-pending verb (PB-18 — reject lifecycle =
v2); freeze mechanism (PB-5 collapsed; PB-23 collapsed); edge-
endpoint mutation API decision (PB-21 collapsed; probe outcome
shelved in §6 for future phase); ADR-0118 §am3 (move-semantics
clarification, PB-2 deferred); FlushFailedError exit code 9 (PB-28
collapsed with logout-flush deferral).

Seven ADR touches at ship: ADR-0008 Status flip (Proposed → Accepted);
ADR-0011 §am2 (Protocol shape + class defer + InMemory ships + delete
returns bool + EVT extension); ADR-0040 first ship in KL; ADR-0006
§am2 (UserMutexRegistry first consumer); ADR-0013 §am (EVT_HARD_
DELETE_USER additive key); ADR-0114 §am4 (Phase 24 FK gap closure);
ADR-0125 (no change — stays Proposed).

## §1. Round-by-round design ledger

Five rounds of pushbacks + iterative re-litigation. The
re-litigation cascade is itself a methodology decision: each round
both surfaced new pushbacks AND revisited prior locks against new
constraints surfaced by probes. Pattern enforced via the user's
recurring instruction "I agree with all your suggestions…
reanalyze the plan and list your push backs, if important, with
options.... show me your choice…"

### Round 0 — Initial scope-shaping (PB-1..PB-12)

12 pushbacks surfacing structural gaps in the 7-item deferral list.
Initial picks (later many reversed in Rounds 2-3).

| PB | Original Pick | One-line |
|---|---|---|
| 1 | (a) split P25a + P25b | Scope = 50-70 picks if as-scoped |
| 2 | (a) move-semantics wins | ADR-0118 §1 vs ADR-0120 §1 #3 |
| 3 | (b) `apply_rewrite_map` at P25b | First-consumer rule (Phase 24 PB-4) |
| 4 | (c) SQLite persister | Local content needs to survive CLI restart |
| 5 | (c) freeze SQLite-side | No L1 vocabulary change |
| 6 | (b) server-side `_installed_locals` refcount | ADR-0008 verbatim |
| 7 | (c) lazy hydration + ADR-0125 partial-flip | LRU deferred |
| 8 | (c) both Protocols in KL | SessionProtocol + AuditWriterProtocol |
| 9 | (b) defer CAN_READ_PENDING_GLOBAL | No consumer |
| 10 | (a) + (c) deferred | Loop cost accepted; coalescing v2 |
| 11 | (c) `MindsOSServer.login` calls free function | Phase 19 surface preserved |
| 12 | (a) pending probe | Edge-endpoint mutation API |

### Round 1 — Second-order substrate (PB-13..PB-24)

12 follow-on pushbacks on Round 0 locks. Probes surfaced more gaps;
PB-21 probe results closed the edge-endpoint question.

| PB | Original Pick | One-line |
|---|---|---|
| 13 | (b) ship lazy hydration + ADR-0125 §am1 | v1-vs-v2 parity admitted |
| 14 | (b) MetagraphDump JSON shape | Forward-binary-stable |
| 15 | (b) FK RESTRICT + explicit persister.delete | Auditable |
| 16 | (b) discard-and-rehydrate atomicity | Persister as atomicity primitive |
| 17 | (c) ATOM single-node v1 | Defer multi-node freeze schema |
| 18 | (b) skip EVT_DRAFT_UNFROZEN | Reject lifecycle = v2 |
| 19 | (c) EVT_RELEASE_SHIPPED.extra additive key | Discoverability |
| 20 | (b) soft-delete via ADR-0133 + replaced_by | Reuses Phase 11 substrate |
| 21 | (b) intra-Local edges dangle | PROBE-CONFIRMED: no edge-endpoint API in Core |
| 22 | (b) per-user mutex outer + admin_tx inner | ADR-0006 §am2 two-consumer ratification |
| 23 | (c→d) freeze metadata-only at v1 | No user-write enforcement site exists |
| 24 | (b) instance state + module RELEASE_SHIP_LOCK | Test isolation (later reversed) |

### PB-21 probe results (executed mid-Round 1)

Probed `mindsos_core/` for edge-endpoint mutation API:
- NO `rewrite_endpoint` / `update_endpoint` / `replace_endpoint` /
  `retarget_xref` / equivalent.
- `Edge`, `XRef`, `IntergraphEdge` dataclasses are technically
  mutable (no `frozen=True`) but no public API supports endpoint
  replacement. `IntergraphEdge.__setattr__` only guards
  `compositional` flag.
- Available primitives: `add_*`, `remove_*` (cascading),
  `deprecate_*` (Phase 11 soft-delete), `update_*_properties`
  (properties only).
- `ref:<role>` properties on Local nodes/edges ARE rewritable via
  existing `update_node_properties` / `update_edge_properties`.
- XRefs require remove+add (loses xref_id continuity); intra-Local
  edges incident on soft-deleted source nodes become structurally
  dangling under PB-20(b) soft-delete + Phase 11 reader-filter
  semantics (`include_deprecated=False` default).

Probe outcome shelved at this phase because Round 2/3 re-litigation
collapsed all lazy-migration scope (PB-3 + PB-12 + PB-20 + PB-21).
Probe result documented in §6 for first phase that ships
`apply_rewrite_map`.

### Round 2 — Probe-revealed gaps + first re-litigation pass (PB-25..PB-34)

First major re-litigation. PB-1 reversed (split → drop scope
further); chain effect collapsed most Round 0/1 picks.

| PB | Pick | One-line |
|---|---|---|
| 25 | (b) Protocol uses Metagraph; MetagraphDump defers | ADR-0011 §am2 |
| 26 | (d) read-local summary-only output | No MetagraphDump dependency |
| 27 | (b) install logic in MindsOSServer.login ONLY; free function unchanged | Later collapsed at PB-37 |
| 28 | (b) extract→save→kill ordering; FlushFailedError → exit 9 | Later collapsed at PB-37 |
| 29 | (b) ship refcount machinery + in-process test | Forward-substrate |
| 30 | (b) UNION pre-check + UserHasPromotionHistoryError | + Phase 24 FK gap closure |
| 31 | (b) full EVT_CROSS_USER_READ_INSTALL payload shape | Phase 24 PB-27 precedent |
| 32 | (b) reuse exit 2 for target-not-found | Phase 22 alignment |
| 33 | (c) fail_save_for hook + two consumers | Non-speculative substrate |
| 34 | (b) ship-as-scoped + retirement-escape clause | Phase 17/23 stop-test |

### Round 2 re-litigation reversals (Round 0/1 picks → re-litigated)

| Original | Reversal | Reason |
|---|---|---|
| PB-1 (a) split | **(d) drop scope further** | Cross-user-read is the only deferral with a real v1 first consumer |
| PB-3 (b) at P25b | **defer past P25 entirely** | No live consumer at P25 |
| PB-4 (c) SQLite persister | **InMemory only; SQLite defers** | No user-Local writes exist at P25 |
| PB-5 (c) freeze SQLite | **COLLAPSE** | Source-user propose defers |
| PB-7 (c) lazy hydration | **(a) eager hydration** | Lazy = eager observably at CLI v1 |
| PB-8 (c) both Protocols | **SessionProtocol only** | AuditWriterProtocol defers with apply_rewrite_map |
| PB-10 (a)+(c) | **COLLAPSE** | No migration loop |
| PB-12 / PB-21 | **COLLAPSE** | No apply_rewrite_map |
| PB-13 → PB-20, PB-23 | **COLLAPSE** | Per Round 2 cascade |
| PB-14, PB-15, PB-16, PB-17, PB-18, PB-19 | **COLLAPSE** | Per Round 2 cascade |

### Round 3 — Probe-revalidated cascades + second re-litigation pass (PB-35..PB-39)

Probes executed: `pending_mutations` + `releases` FK definition;
`hard_delete_user` current behavior; CLI exit code roster.

**Probe results (revalidations):**

- **Probe A (pending_mutations FK):** Both `pending_mutations.
  proposer_admin_user_id` + `releases.proposer_admin_user_id` are
  declared `REFERENCES users (user_id)` with NO `ON DELETE` clause
  → SQLite default `NO ACTION` (effectively RESTRICT). Latent Phase
  24 bug confirmed: hard_delete of an admin with promotion history
  bubbles raw `IntegrityError`.
- **Probe B (hard_delete_user):** Phase 22 verb has no pending_
  mutations pre-check, no releases pre-check, no `persister.delete`
  call. Sessions are auto-CASCADE'd via `sessions.user_id REFERENCES
  users(user_id) ON DELETE CASCADE`.
- **Probe C (exit codes):** Admin codes 1-6 (P20-P22); release codes
  7-8 (P24); next free = 9.

| PB | Pick | One-line |
|---|---|---|
| 35 | ABSORBED INTO PB-30 | Phase 24 FK fix folded into hard_delete_user extension |
| 36 | implied by PB-37/38 | Phase 19 wrapping decision |
| 37 | (b) login/logout pass-through; persister consumed ONLY by cross-user-read | Caller's own Local never touched at v1 |
| 38 | (b) free-function orchestrator + module-level `_installed_locals` | MindsOSServer class defers; PB-24 reversed |
| 39 | (b) additive `local_dump_existed: bool` in EVT_HARD_DELETE_USER.extra | Phase 24 PB-BB precedent |

**Round 3 cascade reversals from Round 2:**

| Round 2 Pick | Round 3 Reversal | Reason |
|---|---|---|
| PB-27 (b) install in MindsOSServer.login | **RE-COLLAPSED — pass-through** | Caller-Local never touched at v1 (PB-37) |
| PB-28 (b) extract→save→kill | **RE-COLLAPSED — pass-through** | No flush at v1 (PB-37) |
| PB-24 (b) instance-level state | **REVERSED — module-level state acceptable** | Test-fixture-reset pattern handles isolation; PB-38 free-function ethos |

### Round 4 — Saturation (PB-40..PB-47)

Real load-bearing pushback (PB-40) + saturation declaration.

| PB | Pick | One-line |
|---|---|---|
| 40 | (b) per-call `persister` + `kl` kwargs; drop `init_orchestrator` global-init pattern | Phase 22 `admin_tx(conn)` per-call precedent |
| 41 | saturation lock — `_install_lock = threading.Lock()` wraps dict access | UserMutexRegistry precedent |
| 43 | saturation lock — allow self-target in read_other_local | Degenerate case; saves error branch |
| 46 | saturation lock — `mindsos server admin read-local`; subgroup split defers | Phase 22 PB-14 split-on-second-consumer precedent |
| 47 | (b) holds — Phase 25 ships; retirement-escape valve stays in design log | Substrate is correct + has live test path |

**Saturation declared after Round 4.** No further load-bearing
pushback surfaces after PB-47.

### Round 5 — Concrete shapes

See §5 Implementation references for production code shapes (orchestrator
+ persister + types + admin extension + CLI verb), §3 Test files for
test specs, §4 ADR delta enumeration.

## §2. Final locks consolidated (~17 picks reference)

| # | Pick | ADR cite / precedent |
|---|---|---|
| 6 | server-side `_installed_locals` refcount-install | ADR-0008 §Decision |
| 9 | defer CAN_READ_PENDING_GLOBAL | No consumer at P25 |
| 11 (narrowed) | MindsOSServer thin façade — **further collapsed at PB-38 to free functions** | ADR-0011 §am1 §1.2 |
| 22 (narrowed) | per-user mutex first consumer = read_other_local; v1 contention impossible | ADR-0006 §am2 |
| 24 (REVERSED) | module-level state acceptable with test fixture reset | Phase 22 admin_tx precedent |
| 25 | Protocol uses Metagraph at v1; MetagraphDump defers | ADR-0011 §am2 |
| 26 | read-local summary-only output | No MetagraphDump dependency |
| 29 | ship refcount machinery + in-process double-acquire test | ADR-0008 conformance even at v1 single-process |
| 30 | UNION pre-check + UserHasPromotionHistoryError | + Phase 24 FK bug closure |
| 31 | full EVT_CROSS_USER_READ_INSTALL payload shape | Phase 24 PB-27 precedent |
| 32 | reuse exit 2 for target-not-found; +exit 10 for UserHasPromotionHistoryError | Phase 22 alignment |
| 33 | fail_save_for hook ships with I-S3 test consumer | Non-speculative substrate |
| 34 | ship-as-scoped + retirement-escape clause in design log | Phase 17/23 stop-test |
| 37 | login/logout pass-through; persister consumed ONLY by cross-user-read | Caller-Local never touched at v1 |
| 38 | free-function orchestrator + module-level `_installed_locals`; class defers | ADR-0011 §am1 §1.2 |
| 39 | additive `local_dump_existed: bool` in EVT_HARD_DELETE_USER.extra | Phase 24 PB-BB precedent |
| 40 | per-call persister + kl kwargs; no `init_orchestrator` | Phase 22 admin_tx(conn) per-call |
| 41 / 43 / 46 | saturation locks | Mechanical bookkeeping |
| 47 | ship-as-scoped holds | Substrate correct + has live consumer |

## §3. Cross-chat dependencies

### Backward (Phase 25 inherits)

- **Phase 14 (KL bootstrap)** — `install_local_metagraph` /
  `extract_local_metagraph` + `KnowledgeLayer.local_metagraph(user_id)`
  getter consumed by orchestrator's `_install_for` / `_release`.
  ADR-0042 §am1 constructor-parameter Global lifecycle unchanged.
- **Phase 18 (server user store + auth)** — `CAN_READ_OTHER_LOCALS`
  cap declared (ADR-0002 §am1); `EVT_CROSS_USER_READ_INSTALL`
  constant declared (PB-34); both first-fire at P25.
- **Phase 19 (sessions)** — login + logout + session_from_token +
  kill_my_own_sessions free functions stay canonical (ADR-0011 §am1
  §1.1 amends). P25 does NOT wrap them in a class (PB-38).
- **Phase 21 (audit log reader)** — `_require_or_audit` consumed at
  `read_other_local` entry; `write_audit` consumed for
  `EVT_CROSS_USER_READ_INSTALL`.
- **Phase 22 (admin ops)** — `hard_delete_user` extended at P25 (PB-
  30 + PB-39); `admin_tx` BEGIN IMMEDIATE pattern wraps the
  extended verb body.
- **Phase 24 (server + admin promotion)** — `pending_mutations` +
  `releases` tables consumed by hard_delete_user pre-check (PB-30
  Phase 24 FK gap closure); `UserMutexRegistry` declared at
  `mindsos_server/locks.py` — P25 is its first consumer (PB-22).

### Forward (Phase 25 → later phases)

- **Phase 26 (Integration A)** — composes P25 CLI verbs into end-to-
  end scripted scenarios; release-ship + cross-user-read combine.
- **First user-Local-write phase** (post-P25; likely source-user-
  propose or first L3 user-write capacity) — consumes:
  - `MindsOSServer` class first-construction
  - `SQLiteLocalPersister` + `FalkorDBLocalPersister`
  - `MetagraphDump` shape (ADR-0011 §am2 §1.3 future)
  - Source-user-Local propose path + freeze mechanism
  - Lazy migration + `apply_rewrite_map` per ADR-0120 (KL impl);
    ADR-0120 Status flip Proposed → Accepted at that phase
  - `EVT_DRAFT_FROZEN` + `EVT_DRAFT_UNFROZEN` + `EVT_MIGRATION_
    APPLIED` + `EVT_MIGRATION_FAILED` audit constants
  - ADR-0118 §am3 (move-semantics vs stay-semantics clarification)
  - Edge-endpoint mutation API decision (PB-21 probe outcome
    shelved here for that phase)
  - `AuditWriterProtocol` in `mindsos_knowledge/types.py`
- **v2 HTTP-daemon phase** — consumes:
  - Lazy hydration + LRU eviction (ADR-0125 §am1 future flip)
  - `LOCAL_HYDRATED` + `LOCAL_EVICTED` audit constants
  - Multi-CLI-process refcount-bump branch becomes reachable in
    production
- **v2 quorum-approve phase** — consumes:
  - REJECTED + WITHDRAWN release lifecycle states
  - Admin reject-pending verb + `EVT_DRAFT_UNFROZEN` first caller

### Memory + feedback rules consumed

- `feedback_pushback_format_with_picks.md` — 47 PB candidates
  surfaced across 5 rounds with iterative re-litigation; picks per
  pushback + final picks summary per round.
- `feedback_pre_impl_probe_check_existing_modules.md` — probes
  executed: edge-endpoint mutation API in mindsos_core (PB-21);
  pending_mutations + releases FK definition (PB-30); hard_delete_
  user current shape (PB-30); CLI exit-code roster (PB-32).
- `feedback_phase_baseline_literal_audit.md` — schema_version stays
  4 (no DDL change at P25); other phase-baseline literals unchanged.
- `feedback_l1_api_signature_probe_before_writing_tests.md` —
  Round 6 (pre-impl re-analysis at impl chat) must probe:
  - `KnowledgeLayer.local_metagraph(user_id)` getter — exists per
    Phase 14 PB-9 lock; verify signature.
  - `Metagraph.graphs_by_role` vs alternative attribute name.
  - `Metagraph.xrefs` + `Metagraph.intergraph_edges` attribute
    names (probe-confirmed at PB-21 execution).
- `feedback_pk_column_per_table_probe.md` — `pending_mutations.
  mutation_id` + `releases.release_id` PK columns for verification
  queries (Phase 24 hotfix B-22-T1 lesson).

## §4. ADR delta at Phase 25 ship

**7 ADR touches** at ship: 1 Status flip + 4 §amendments + 1 first-
ship + 0 new ADR drafts.

| ADR | Action | Body change |
|---|---|---|
| **0008** | Status: Proposed → Accepted | First consumer ships (`read_other_local` ctx mgr); §Decision InstallRecord shape ships verbatim (`user_id`, `installed_by_session: str | None`, `transient: bool`, `refcount: int`); §Consequences I-S3 test ships (`test_read_other_local_transient_no_flush_is3`); refcount-bump branch test-only at v1 production (single-process CLI; tested via in-process double-acquire fixture). |
| **0011** | §am2 | (1) Protocol shape uses `Metagraph | None` not `MetagraphDump | None` at v1; MetagraphDump dataclass defers to first SQLite/Falkor phase. (2) `delete(user_id) -> bool` (was `-> None`); consumed by EVT_HARD_DELETE_USER.extra `local_dump_existed` (PB-39). (3) InMemoryLocalPersister ships with `fail_save_for: set[str]` hook; SQLite + Falkor + MetagraphDump defer. (4) `MindsOSServer` class first-construction defers per §1.2: orchestrator ships as free functions at v1 (PB-38). (5) §"On login" + §"On logout" install/extract sequences defer to first user-Local-write phase (PB-37 — caller-Local never touched at v1). |
| **0040** | First ship | `mindsos_knowledge/types.py::SessionProtocol` ships verbatim from §Decision (`session_id: str`, `user_id: str`, `actor_role: Literal["user","admin"]`, `capabilities: Iterable[str]`, `has(capability: str) -> bool`); KL maintains zero imports from `mindsos_server` (import-isolation test `test_import_isolation_phase25.py` confirms). |
| **0006** | §am2 | UserMutexRegistry first consumer: `mindsos_server.orchestrator.read_other_local` (acquired per-target inside ctx mgr). v1 single-process CLI makes contention unreachable in production; in-process double-acquire test exercises the bump branch (PB-29). Acquisition order: per-user mutex outer + admin_tx inner (matches Phase 24 RELEASE_SHIP_LOCK + admin_tx pattern). |
| **0013** | §am | EVT_HARD_DELETE_USER.extra_json gains additive key `local_dump_existed: bool` (PB-39). Backward-compatible per Phase 22 PB-16 additive-extra precedent. Roster now: `{prior_role, was_disabled, sessions_killed, local_dump_existed}`. |
| **0114** | §am4 | Phase 24 latent FK gap closure: `pending_mutations.proposer_admin_user_id` + `releases.proposer_admin_user_id` FKs are `NO ACTION` (effectively RESTRICT). Phase 25 `hard_delete_user` gains UNION pre-check; raises `UserHasPromotionHistoryError(target_user_id, pending_ids, release_ids)`. Admin's recourse: `admin-demote` + `admin-disable` for retire-with-history; hard_delete forbidden when promotion history exists. CLI exit code 10 (NEW) for `UserHasPromotionHistoryError`. |
| **0125** | (no change) | Stays Proposed. Lazy hydration defers to v2 HTTP-daemon phase per PB-37 (caller-Local install collapsed entirely; v1 doesn't observe a lazy-vs-eager difference at CLI). |

**ADR-0010 unchanged.** New `mindsos_server/orchestrator.py` →
`mindsos_knowledge/types.py` import is `server → knowledge` (ALLOWED
per ADR-0010 §am1 DAG). No new edges; no DAG amendment needed.

**ADR-0120 unchanged.** Stays Proposed. KL impl (`apply_rewrite_map`)
defers to first user-Local-write phase; ADR-0120 Status flip waits
for that phase.

PHASE_MAP §25 row rewrite at ship per §1 row-rewrite rule — records
the locked ~17-pick scope; replaces the speculative "SessionProtocol
seam in L2 + hydrate/extract hooks" with the actual cross-user-read
substrate scope.

## §5. Implementation references

### File layout

```
mindsos_server/
├── orchestrator.py                    # NEW ~120 LOC — read_other_local +
│                                       #  InstallRecord + _install_for + _release
│                                       #  + _node_counts; module-level
│                                       #  _installed_locals + _install_lock +
│                                       #  _mutex_registry (UserMutexRegistry)
├── persistence/                       # NEW package
│   ├── __init__.py                    # 5 LOC — re-exports
│   └── local_persister.py             # NEW ~80 LOC — LocalPersister Protocol +
│                                       #  InMemoryLocalPersister + fail_save_for
├── admin.py                           # MODIFIED — hard_delete_user gains
│                                       #  pending+releases UNION pre-check +
│                                       #  persister.delete + local_dump_existed
│                                       #  in extra; +read_other_local_summary +
│                                       #  +ReadOtherLocalSummary +
│                                       #  +RoleGraphSummary dataclasses
├── exceptions.py                      # MODIFIED — +FlushFailedError (ADR-0011)
│                                       #  +UserHasPromotionHistoryError
├── audit.py                           # MODIFIED — lock EVT_CROSS_USER_READ_
│                                       #  INSTALL payload shape docstring
│                                       #  per PB-31
└── __init__.py                        # MODIFIED — +exports for
                                        #  read_other_local + InstallRecord +
                                        #  LocalPersister + InMemoryLocalPersister
                                        #  + UserHasPromotionHistoryError +
                                        #  FlushFailedError + ReadOtherLocalSummary

mindsos_knowledge/
└── types.py                           # NEW ~30 LOC — SessionProtocol
                                        #  (ADR-0040 first ship; runtime_checkable)

mindsos_cli/commands/server.py         # MODIFIED — +read-local verb
                                        #  (admin_read_local_cmd);
                                        #  +_admin_exit_for extension
                                        #  (UserHasPromotionHistoryError → 10);
                                        #  hard_delete_user verb passes persister;
                                        #  +_resolve_persister + _resolve_kl
                                        #  module-level helpers

tests/phase_25/                        # NEW (~16 files)
├── __init__.py
├── conftest.py                        # autouse: reset _installed_locals;
│                                       #  fixtures: persister, kl, seeded_admin
├── test_session_protocol_satisfied.py
├── test_local_persister_protocol_inmemory_roundtrip.py
├── test_local_persister_inmemory_fail_save_hook.py
├── test_read_other_local_transient_no_flush_is3.py
├── test_read_other_local_refcount_bump_in_process.py
├── test_read_other_local_audit_event_payload.py
├── test_read_other_local_self_target_allowed.py
├── test_read_local_cli_happy.py
├── test_read_local_cli_permission_denied.py
├── test_read_local_cli_target_not_found.py
├── test_hard_delete_user_pending_blocks.py
├── test_hard_delete_user_releases_blocks.py
├── test_hard_delete_user_persister_delete_called.py
├── test_evt_hard_delete_user_local_dump_existed.py
└── test_import_isolation_phase25.py

docs/usage/server/read-local.md         # DEFERRED to Phase 38 doc-review
                                        #  per Phase 18-22 documentation-defer
                                        #  pattern
docs/concepts/cross-user-read.md        # DEFERRED to Phase 38

# Version bump +phase24 → +phase25 across 9 sites:
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

### Concrete shapes (the round-5 lock)

Concrete code shapes for every NEW/MODIFIED surface are inlined in
this design log §5 reference. The next chat (impl) consumes these
shapes verbatim with one Round 6 pre-impl re-analysis pass for any
gaps the design chat couldn't see (Phase 24 Round 0 precedent).

**`mindsos_knowledge/types.py::SessionProtocol`:**

```python
from typing import Iterable, Literal, Protocol, runtime_checkable


@runtime_checkable
class SessionProtocol(Protocol):
    """ADR-0040 §Decision verbatim. KL-side duck-typed Session shape."""
    session_id: str
    user_id: str
    actor_role: Literal["user", "admin"]
    capabilities: Iterable[str]

    def has(self, capability: str) -> bool: ...
```

**`mindsos_server/persistence/local_persister.py`:**

```python
@runtime_checkable
class LocalPersister(Protocol):
    """ADR-0011 §am2 — Protocol uses Metagraph at v1; MetagraphDump defers."""
    def load(self, user_id: str) -> Optional[Metagraph]: ...
    def save(self, user_id: str, metagraph: Metagraph) -> None: ...
    def delete(self, user_id: str) -> bool: ...


class InMemoryLocalPersister:
    def __init__(self) -> None:
        self._store: dict[str, Metagraph] = {}
        self.fail_save_for: set[str] = set()  # PB-33 test-fault-injection

    def load(self, user_id: str) -> Optional[Metagraph]:
        return self._store.get(user_id)

    def save(self, user_id: str, metagraph: Metagraph) -> None:
        if user_id in self.fail_save_for:
            raise FlushFailedError(user_id)
        self._store[user_id] = metagraph

    def delete(self, user_id: str) -> bool:
        return self._store.pop(user_id, None) is not None
```

**`mindsos_server/orchestrator.py`:**

```python
# Module-level state per PB-38 + PB-40
_installed_locals: dict[str, InstallRecord] = {}
_install_lock = threading.Lock()
_mutex_registry = UserMutexRegistry()  # ADR-0006 §am2 first consumer


@dataclass
class InstallRecord:
    """ADR-0008 §Decision verbatim."""
    user_id: str
    installed_by_session: Optional[str]   # None = transient
    transient: bool
    refcount: int


@contextmanager
def read_other_local(
    conn: sqlite3.Connection,
    admin_session: Session,
    target_user_id: str,
    *,
    persister: LocalPersister,
    kl: KnowledgeLayer,
) -> Iterator[Metagraph]:
    """Admin reads target user's Local with refcount-install per ADR-0008.

    PB-43: self-target allowed (degenerate case).
    PB-22: per-target mutex acquired via UserMutexRegistry.
    PB-31: single audit row at acquire (release implicit).
    PB-33: never flush on transient teardown (ADR-0008 I-S3).
    """
    _require_or_audit(
        conn, admin_session, CAN_READ_OTHER_LOCALS,
        verb="read_other_local",
    )

    with _mutex_registry.user_mutexes([target_user_id]):
        mg, was_existing, refcount_after = _install_for(
            target_user_id, transient=True,
            persister=persister, kl=kl,
        )

        write_audit(
            conn, actor=admin_session.user_id,
            event=EVT_CROSS_USER_READ_INSTALL,
            target=target_user_id,
            extra={
                "admin_user_id": admin_session.user_id,
                "target_user_id": target_user_id,
                "transient": True,
                "install_was_existing": was_existing,
                "refcount_after_acquire": refcount_after,
                "target_role_graph_node_counts": _node_counts(mg),
            },
        )

        try:
            yield mg
        finally:
            _release(target_user_id, persister=persister, kl=kl)


def _install_for(
    user_id: str, *, transient: bool,
    persister: LocalPersister, kl: KnowledgeLayer,
) -> Tuple[Metagraph, bool, int]:
    """Returns (metagraph, was_existing, refcount_after_acquire)."""
    with _install_lock:
        existing = _installed_locals.get(user_id)
        if existing is not None:
            existing.refcount += 1
            if not transient and existing.transient:
                existing.transient = False  # sticky upgrade per ADR-0008
            mg = kl.local_metagraph(user_id)
            return mg, True, existing.refcount

        dump = persister.load(user_id)
        if dump is None:
            mg = Metagraph(name=f"local_{user_id}")
        else:
            mg = dump
        kl.install_local_metagraph(user_id, mg)
        _installed_locals[user_id] = InstallRecord(
            user_id=user_id,
            installed_by_session=None,
            transient=transient,
            refcount=1,
        )
        return mg, False, 1


def _release(
    user_id: str, *,
    persister: LocalPersister, kl: KnowledgeLayer,
) -> None:
    with _install_lock:
        record = _installed_locals.get(user_id)
        if record is None:
            return
        record.refcount -= 1
        if record.refcount > 0:
            return

        mg = kl.extract_local_metagraph(user_id)
        if not record.transient:
            # v1: dead code per PB-37 (no sticky installs ever);
            # forward-shape for first user-Local-write phase
            try:
                persister.save(user_id, mg)
            except FlushFailedError:
                kl.install_local_metagraph(user_id, mg)
                record.refcount = 1
                raise

        del _installed_locals[user_id]
```

**`mindsos_server/admin.py` extension — `hard_delete_user`:**

```python
def hard_delete_user(
    conn: sqlite3.Connection,
    session: Session,
    *,
    target_user_id: str,
    persister: Optional[LocalPersister] = None,  # NEW PB-30/39 (None for backward-compat)
) -> HardDeleteUserResult:
    _require_or_audit(conn, session, CAN_HARD_DELETE_ARCHIVED, verb="hard_delete_user")
    with admin_tx(conn):
        # ── existing pre-checks (target exists, not sole admin) ──
        ...

        # ── NEW Phase 25 pre-check (PB-30 + Phase 24 FK gap closure) ──
        history_rows = conn.execute(
            """
            SELECT 'pending' AS kind, mutation_id AS id
              FROM pending_mutations WHERE proposer_admin_user_id = ?
            UNION ALL
            SELECT 'release', release_id
              FROM releases WHERE proposer_admin_user_id = ?
            """,
            (target_user_id, target_user_id),
        ).fetchall()
        pending_ids = [r[1] for r in history_rows if r[0] == "pending"]
        release_ids = [r[1] for r in history_rows if r[0] == "release"]
        if pending_ids or release_ids:
            raise UserHasPromotionHistoryError(
                target_user_id, pending_ids, release_ids,
            )

        # ── existing session-kill audit emission ──
        ...

        # ── NEW PB-39: persister.delete + local_dump_existed ──
        local_dump_existed = False
        if persister is not None:
            local_dump_existed = persister.delete(target_user_id)

        write_audit(
            conn, actor=session.user_id, event=EVT_HARD_DELETE_USER,
            target=target_user_id,
            extra={
                "prior_role": actor_role,
                "was_disabled": was_disabled,
                "sessions_killed": len(session_ids),
                "local_dump_existed": local_dump_existed,  # NEW PB-39
            },
        )

        conn.execute("DELETE FROM users WHERE user_id = ?", (target_user_id,))

    return HardDeleteUserResult(
        target_user_id=target_user_id,
        prior_role=actor_role,
        was_disabled=was_disabled,
        sessions_killed=len(session_ids),
        local_dump_existed=local_dump_existed,  # NEW PB-39
    )
```

**`mindsos_server/admin.py` extension — `read_other_local_summary`:**

```python
@dataclass(frozen=True)
class RoleGraphSummary:
    role: str
    node_count: int
    edge_count: int
    hyperedge_count: int


@dataclass(frozen=True)
class ReadOtherLocalSummary:
    target_user_id: str
    role_graphs: list[RoleGraphSummary]
    xref_count: int
    intergraph_edge_count: int


def read_other_local_summary(
    conn: sqlite3.Connection,
    session: Session,
    *,
    target_user_id: str,
    persister: LocalPersister,
    kl: KnowledgeLayer,
) -> ReadOtherLocalSummary:
    """Admin diagnostic: summary of target user's Local content.

    PB-26 lock — summary-only output (per-role node/edge/hyperedge
    counts + xref count + intergraph_edge count). Full detail dump
    defers to first phase shipping MetagraphDump.
    """
    row = conn.execute(
        "SELECT 1 FROM users WHERE user_id = ?", (target_user_id,),
    ).fetchone()
    if row is None:
        raise UserNotFoundError(target_user_id)

    with read_other_local(
        conn, session, target_user_id,
        persister=persister, kl=kl,
    ) as mg:
        role_graphs = [
            RoleGraphSummary(
                role=role,
                node_count=len(g.nodes),
                edge_count=len(g.edges),
                hyperedge_count=len(g.hyperedges),
            )
            for role, g in sorted(mg.graphs_by_role.items())
        ]
        return ReadOtherLocalSummary(
            target_user_id=target_user_id,
            role_graphs=role_graphs,
            xref_count=len(mg.xrefs),
            intergraph_edge_count=len(mg.intergraph_edges),
        )
```

**`mindsos_server/exceptions.py` additions:**

```python
class FlushFailedError(Exception):
    """LocalPersister.save raised; session intact for retry per ADR-0011 §"On logout"."""
    def __init__(self, user_id: str):
        self.user_id = user_id
        super().__init__(
            f"Local persistence flush failed for user_id={user_id!r}; "
            f"session intact; retry recommended."
        )


class UserHasPromotionHistoryError(Exception):
    """Phase 25 PB-30 + Phase 24 latent FK gap closure (ADR-0114 §am4)."""
    def __init__(self, user_id, pending_ids, release_ids):
        self.user_id = user_id
        self.pending_ids = list(pending_ids)
        self.release_ids = list(release_ids)
        super().__init__(
            f"user_id={user_id!r} has promotion history: "
            f"{len(self.pending_ids)} pending mutation(s), "
            f"{len(self.release_ids)} release(s). "
            f"Use admin-demote + admin-disable to retire; hard_delete "
            f"forbidden when promotion history exists (ADR-0114 §am4)."
        )
```

**`mindsos_server/audit.py` PB-31 payload-shape docstring:**

```python
#: EVT_CROSS_USER_READ_INSTALL — first fires at Phase 25 (PB-31 payload shape lock).
#:
#: extra_json shape:
#:     {
#:         "admin_user_id":                str,
#:         "target_user_id":               str,
#:         "transient":                    bool,           # True at v1 (only transient)
#:         "install_was_existing":         bool,           # False at v1 prod (single-process)
#:         "refcount_after_acquire":       int,            # always 1 at v1 prod
#:         "target_role_graph_node_counts": dict[str, int], # role → node count
#:     }
EVT_CROSS_USER_READ_INSTALL = "EVT_CROSS_USER_READ_INSTALL"
```

**`mindsos_cli/commands/server.py` `_admin_exit_for` + new verb:**

```python
def _admin_exit_for(exc: Exception) -> int:
    if isinstance(exc, PermissionDeniedError):       return 3
    if isinstance(exc, LastAdminError):              return 4
    if isinstance(exc, AlreadyAnAdminError):         return 5
    if isinstance(exc, SessionNotFoundError):        return 6
    if isinstance(exc, UserHasPromotionHistoryError): return 10   # NEW P25
    if isinstance(exc, (UserNotFoundError, NotAnAdminError, ValueError)):
        return 2
    return 1


@admin_app.command(name="read-local")
def admin_read_local_cmd(
    target_user_id: str = typer.Argument(...),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Admin diagnostic: summary of target user's Local metagraph."""
    with _resolve_and_open() as conn:
        _ensure_migrated(conn)
        session = _resolve_session(conn)
        persister = _resolve_persister()
        kl = _resolve_kl()
        try:
            summary = read_other_local_summary(
                conn, session,
                target_user_id=target_user_id,
                persister=persister, kl=kl,
            )
        except (PermissionDeniedError, UserNotFoundError) as exc:
            typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(code=_admin_exit_for(exc)) from exc

    if json_out:
        typer.echo(json.dumps(asdict(summary), indent=2))
    else:
        typer.echo(f"Local for user_id={summary.target_user_id}:")
        for rg in summary.role_graphs:
            typer.echo(
                f"  role={rg.role}: {rg.node_count} nodes, "
                f"{rg.edge_count} edges, {rg.hyperedge_count} hyperedges"
            )
        typer.echo(f"  xrefs: {summary.xref_count}")
        typer.echo(f"  intergraph_edges: {summary.intergraph_edge_count}")
```

### CLI exit-code roster after P25

| Code | Class | Phase |
|---|---|---|
| 1 | defensive | — |
| 2 | UserNotFoundError, NotAnAdminError, ValueError | P20 |
| 3 | PermissionDeniedError | P21 |
| 4 | LastAdminError | P22 |
| 5 | AlreadyAnAdminError | P22 |
| 6 | SessionNotFoundError | P22 |
| 7 | EmptyReleaseError | P24 |
| 8 | BlockingFindingError | P24 |
| 9 | (reserved for FlushFailedError) | DEFERRED per PB-37 |
| **10** | **UserHasPromotionHistoryError** | **P25 NEW (PB-30)** |

### Capability + audit-event rosters after P25

**Capabilities:** unchanged (9 total per Phase 24; no new caps).
`CAN_READ_OTHER_LOCALS` consumed for first time by `read_other_local`.

**Audit events:** unchanged constant roster (no new events).
`EVT_CROSS_USER_READ_INSTALL` (declared P18 PB-34) fires for first
time at P25; payload shape locked per PB-31.

`EVT_HARD_DELETE_USER.extra_json` gains additive key `local_dump_existed`
(PB-39); roster: `{prior_role, was_disabled, sessions_killed,
local_dump_existed}`.

## §6. Scope boundaries (out-of-scope at Phase 25 ship)

- **Source-user-Local propose path** (`PromotionItem.source_user_id
  is not None`) — deferred to first user-Local-write phase. Phase
  25's `mindsos_admin.propose_for_promotion` still raises
  `NotImplementedError` for source-user-set proposals (unchanged
  from Phase 24).
- **Lazy migration code path** (session-start rewrite-map walk +
  `apply_rewrite_map` KL impl) — deferred to first user-Local-write
  phase per PB-3 reversed. ADR-0120 stays Proposed; first KL impl
  ships at that phase with ADR-0120 Status flip.
- **`MindsOSServer` class first-construction** — deferred per PB-38
  + ADR-0011 §am1 §1.2. v1 ships free-function orchestrator surface
  in `mindsos_server/orchestrator.py`.
- **`SQLiteLocalPersister` + `FalkorDBLocalPersister`** — deferred
  to first user-Local-write phase. v1 ships InMemoryLocalPersister
  only.
- **`MetagraphDump` dataclass shape** — deferred to first SQLite/
  Falkor persistence phase per ADR-0011 §am2 §1.1. Protocol uses
  `Metagraph` directly at v1.
- **Login-time install + logout-time flush** — deferred per PB-37
  (caller's own Local never touched at v1; KL has no write API;
  lazy migration deferred; no commands write to caller's Local).
  `MindsOSServer.login`/`logout` would be pass-through to Phase 19
  free functions — and since the class itself defers (PB-38), Phase
  19 free functions stay canonical unchanged.
- **Lazy hydration + LRU eviction (ADR-0125)** — deferred to v2
  HTTP-daemon phase. ADR-0125 stays Proposed. CLI per-command-
  process model means lazy = eager observably at v1 (no behavior
  difference).
- **`CAN_READ_PENDING_GLOBAL` capability** — deferred to first
  direct-read consumer phase per PB-9.
- **Admin reject-pending verb + WITHDRAWN/REJECTED release lifecycle
  states + EVT_DRAFT_FROZEN/UNFROZEN** — deferred to v2 quorum-
  approve phase as a cluster per PB-18.
- **EVT_MIGRATION_APPLIED + EVT_MIGRATION_FAILED audit constants** —
  deferred with `apply_rewrite_map` per PB-3 reversed.
- **Freeze mechanism (`pending_mutations.frozen_user_local_node_id`
  populated path)** — deferred per PB-5 collapsed. v4 column stays
  NULL-only at P25.
- **ADR-0118 §am3 (move-semantics vs stay-semantics clarification)**
  — deferred to first phase that ships `apply_rewrite_map`. PB-2
  pick reasoning shelved.
- **Edge-endpoint mutation API decision (PB-21 probe outcome
  shelved)** — at the future apply_rewrite_map phase, the conservative
  pick is PB-21(b): source node soft-deleted via ADR-0133
  `deprecated_at`; intra-Local edges incident on the source node
  left dangling-against-deprecated; EVT_MIGRATION_APPLIED.extra
  gains `dangling_edges_left: list[edge_id]` as diagnostic.
- **`AuditWriterProtocol` in `mindsos_knowledge/types.py`** —
  deferred with `apply_rewrite_map` per PB-8 reversed.
- **`MindsOSServer.start_session` release-walk loop** — deferred
  per PB-3 reversed. First lands at user-Local-write phase.
- **CLI `mindsos server local-status` verb (ADR-0125 §3)** —
  deferred with lazy hydration to v2 daemon phase.

## §7. Design saturation note

Phase 25's design discipline diverged from Phase 24's in one
meaningful way: **iterative re-litigation through multiple rounds**.
Phase 24 had 5 rounds + 1 post-design-lock Round 0 pre-impl re-
analysis. Phase 25 had 5 rounds with re-litigation woven INTO each
round (the user instruction "I agree with all your suggestions…
reanalyze the plan and list your push backs" was applied recurringly).

The pattern surfaced **cascading scope-collapse**: most Round 0
picks were reversed at Round 2/3 after probes revealed substrate
constraints (probe-confirmed at PB-21 + PB-30 + PB-32). The honest
end-state was significantly narrower than the initial Round 0 split-
pick: from "split P25a + P25b" → "ship cross-user-read substrate
only; defer everything else to first user-Local-write phase."

**Methodology lesson:** for phases that absorb many deferrals from
a prior phase, the "no caller until X" critique applies recursively.
Each deferral has its own first-consumer phase; bundling them
together does not create the consumer — it just shifts substrate-
without-consumer to a different phase. Phase 25's collapse pattern
is the cleanest application of Phase 14 PB-6's "honoured by absence"
discipline observed in the codebase so far.

**Retirement stop-test (PB-34 + PB-47):** at saturation, the
question "should P25 retire design-only like Phase 17/23?" was
answered NO — Phase 17/23 retired because their locks were
*incorrect* against probe (vestigial / vacuous). Phase 25's locks
are *correct* — the substrate IS what future phases will consume;
it just has thin v1-utility (admin diagnostic verb on always-empty
Locals). Shipping correct-substrate-with-thin-utility is materially
different from retiring-because-vacuous. The retirement-escape
clause stays available IF implementation surfaces the substrate as
misdesigned.

No further pushback surfaces after PB-47 (Round 4 saturation lock).

## §8. Carry-forwards from Phase 24

Phase 24 design log §3 forward dependencies enumerated Phase 25
consumers. Phase 25 disposition:

| # | Carry-forward (Phase 24 design log §3) | Phase 25 disposition |
|---|---|---|
| 1 | Source-user-Local propose path | **DEFERRED** to first user-Local-write phase per PB-1 revised |
| 2 | Lazy migration (`MindsOSServer.start_session` rewrite-map walk + `apply_rewrite_map` KL impl + ADR-0120 Status flip) | **DEFERRED** per PB-3 reversed |
| 3 | `EVT_DRAFT_FROZEN` + `EVT_DRAFT_UNFROZEN` + `EVT_MIGRATION_APPLIED` + `EVT_MIGRATION_FAILED` audit constants | **DEFERRED** with their consumers |
| 4 | `CAN_READ_PENDING_GLOBAL` capability | **DEFERRED** per PB-9 (no consumer at P25) |
| 5 | `MindsOSServer` orchestrator class | **DEFERRED** per PB-38 (free functions ship instead) |
| 6 | `LocalPersister` Protocol + first persister impl | **SHIPPED** at P25 (InMemory only); SQLite + Falkor defer |
| 7 | Cross-user read substrate (`read_other_local` + `_installed_locals` + ADR-0008 refcount) | **SHIPPED** at P25 — primary scope |

Plus the Phase 24 latent FK bug NOT enumerated in Phase 24 §3 but
**discovered at P25 PB-30 probe**: `pending_mutations.proposer_admin
_user_id` + `releases.proposer_admin_user_id` are `NO ACTION` FKs;
hard_delete bubbles raw IntegrityError. Closed at P25 ship via ADR-
0114 §am4.

Phase 14 PB-6 "honoured by absence" precedent applied at 5 deferral
sites in Phase 25 (carry-forwards #1-5 above). Phase 25 ratifies
this discipline: substrate ships when its first consumer is live,
not earlier.
