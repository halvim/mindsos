# Memory entry to manually add to ~/Library/Application Support/Claude/.../memory/

The Write tool in this session sandbox can't reach the host memory folder
(`/Users/henriquealvim/Library/Application Support/Claude/local-agent-mode-sessions/.../memory/`).

If you want future chats to auto-load the Phase 25 design context as a
memory entry, manually:

1. Create file: `project_mindsos_phase_25_design.md` in your memory folder.
2. Paste the content below as the body.
3. Add this line to MEMORY.md:
   `- [Phase 25 design lock](project_mindsos_phase_25_design.md) — ~17 picks across 5 rounds; iterative re-litigation cascade; 7 ADR touches; orchestrator ships as free functions; Phase 24 latent FK bug closed`

---

## File: `project_mindsos_phase_25_design.md`

```markdown
---
name: project-mindsos-phase-25-design
description: MindsOS Phase 25 — Server cross-user-read substrate (read_other_local + LocalPersister + SessionProtocol in KL) DESIGN-LOCKED 2026-05-23; ~17 picks across 5 rounds; 47 PB candidates surfaced; ~30 collapsed via iterative re-litigation cascade through Rounds 0→4; 7 ADR touches at ship; Phase 24 latent FK bug discovered + closed (ADR-0114 §am4); orchestrator ships as free functions (class defers); login/logout pass-through (caller-Local untouched at v1).
metadata:
  type: project
---

# MindsOS Phase 25 — DESIGN-LOCKED 2026-05-23 (awaiting impl chat)

**Status:** design-locked; PR not yet open; tag `phase-25-confirmed`
pending impl + ship. Design log at
`halvim_mindsos/confirmation_docs/PHASE_25_DESIGN_LOG.md`.

## Scope at design lock

Absorbs ONE of Phase 24's seven enumerated deferrals: **cross-user-
read substrate**. The other six defer further to first user-Local-
write phase per multi-round re-litigation (PB-1 reversed: split → drop).

**What ships:**

* `mindsos_server/orchestrator.py` (NEW ~120 LOC) — `read_other_local`
  ctx mgr + `InstallRecord` + `_install_for` + `_release` +
  `_node_counts`; module-level `_installed_locals` + `_install_lock`
  + `_mutex_registry` (UserMutexRegistry first consumer per ADR-0006
  §am2). Per-call `persister` + `kl` kwargs (no init pattern per
  PB-40).
* `mindsos_server/persistence/local_persister.py` (NEW ~80 LOC) —
  `LocalPersister` Protocol (Metagraph not MetagraphDump per ADR-0011
  §am2) + `InMemoryLocalPersister` + `fail_save_for` hook.
  `delete(user_id) -> bool` (PB-39).
* `mindsos_knowledge/types.py` (NEW ~30 LOC) — `SessionProtocol`
  runtime_checkable per ADR-0040 first ship; KL stays zero-imports
  from `mindsos_server`.
* `mindsos_server/admin.py` — `hard_delete_user` gains UNION pre-
  check on pending_mutations + releases proposer FKs; raises
  `UserHasPromotionHistoryError` (closes Phase 24 latent FK bug per
  ADR-0114 §am4); adds `persister.delete(user_id)` + `local_dump_
  existed: bool` in EVT_HARD_DELETE_USER.extra (PB-39). +
  `read_other_local_summary` + `ReadOtherLocalSummary` +
  `RoleGraphSummary` dataclasses.
* `mindsos_server/exceptions.py` — +`FlushFailedError` +
  `UserHasPromotionHistoryError`.
* `mindsos_server/audit.py` — lock EVT_CROSS_USER_READ_INSTALL
  payload-shape docstring (PB-31; 6-key payload).
* `mindsos_cli/commands/server.py` — new `mindsos server admin
  read-local <target_user_id>` verb; +exit code 10 for
  UserHasPromotionHistoryError; hard_delete_user verb passes
  persister.
* 16 test files at `tests/phase_25/`.
* 7 ADR touches at ship.
* Version bump `+phase24 → +phase25` across 9 sites.

## What's deferred to first user-Local-write phase

* Source-user-Local propose path
* Lazy migration + apply_rewrite_map + ADR-0120 Status flip
* MindsOSServer class first-construction (PB-38 — free functions at v1)
* SQLiteLocalPersister + FalkorDBLocalPersister
* MetagraphDump dataclass shape
* Login-time install + logout-time flush (PB-37 — caller-Local
  never touched at v1)
* 4 EVT_* (DRAFT_FROZEN + DRAFT_UNFROZEN + MIGRATION_APPLIED +
  MIGRATION_FAILED)
* Freeze mechanism
* ADR-0118 §am3 (move-semantics)
* Edge-endpoint mutation API decision (PB-21 probe shelved)
* AuditWriterProtocol in KL
* MindsOSServer.start_session release-walk loop

## What's deferred to v2 HTTP-daemon phase

* Lazy hydration + LRU eviction (ADR-0125 stays Proposed)
* LOCAL_HYDRATED + LOCAL_EVICTED audit constants
* Multi-process refcount-bump branch reachable in production

## What's deferred to v2 quorum-approve phase

* REJECTED + WITHDRAWN release lifecycle states
* Admin reject-pending verb + EVT_DRAFT_UNFROZEN first caller

## ADR delta at ship — 7 touches

* **ADR-0008** Status flip Proposed → Accepted (first consumer)
* **ADR-0011** §am2 (5 clauses: Protocol uses Metagraph; delete
  returns bool; InMemory ships; class defers; login/logout install/
  extract defer)
* **ADR-0040** first ship (SessionProtocol in KL)
* **ADR-0006** §am2 (UserMutexRegistry first consumer)
* **ADR-0013** §am (EVT_HARD_DELETE_USER additive
  `local_dump_existed`)
* **ADR-0114** §am4 (Phase 24 latent FK gap closure)
* **ADR-0125** unchanged (Proposed; v2 HTTP daemon)

## Multi-round re-litigation methodology (load-bearing lesson)

Phase 25's design discipline diverged from Phase 24's: **iterative
re-litigation through 5 rounds with reversal-cascade**. Each round
both added new pushbacks AND reconsidered prior locks against new
constraints. User's recurring instruction "I agree with all your
suggestions… reanalyze the plan and list your push backs… show me
your choice" drove the iteration.

**Cascade outcomes:**
* 47 PB candidates surfaced; ~17 final picks locked; ~30 collapsed
* Round 0 PB-1 picked (a) split; reversed at Round 2 to (d) drop scope
* Round 0 PB-3, PB-4, PB-5, PB-7, PB-8, PB-10, PB-12 — all
  collapsed/reversed at Round 2/3 cascade
* Round 1 PB-13..PB-21, PB-23 — mostly collapsed per cascade
* Round 2 PB-27, PB-28 — collapsed at Round 3 PB-37 (login/logout
  pass-through)
* Round 1 PB-24 — reversed at Round 3 PB-38 (module-level state OK
  with test-fixture-reset)

**Methodology lesson:** for phases absorbing many deferrals from a
prior phase, the "no caller until X" critique applies recursively.
Each deferral has its own first-consumer phase; bundling them
together does not create the consumer.

## Phase 24 latent FK bug discovered during PB-30 probe

`pending_mutations.proposer_admin_user_id` +
`releases.proposer_admin_user_id` FKs are declared `REFERENCES users
(user_id)` with NO `ON DELETE` clause → SQLite default `NO ACTION`
(effectively RESTRICT). Hard-deleting an admin with promotion
history bubbles raw `IntegrityError`. Phase 24 test suite never
exercised this. Closed at P25 via ADR-0114 §am4.

## Retirement stop-test (PB-34 + PB-47)

Asked: should P25 retire design-only like Phase 17/23? Answered NO.
Phase 17/23 retired because their locks were *incorrect* against
probe. P25's locks are *correct* — substrate IS what future phases
will consume; thin v1-utility (admin diagnostic on empty Locals) is
materially different from retiring-because-vacuous. Retirement-
escape clause stays available in design log §7 IF impl surfaces
substrate as misdesigned.

## Round 6 — pre-impl re-analysis (Phase 24 Round 0 precedent)

Next chat (impl) should run Round 6 pre-impl re-analysis before
implementing — Phase 24 Round 0 surfaced 16 substantive picks AFTER
design-lock. Likely Round 6 candidates:

* `KnowledgeLayer.local_metagraph(user_id)` getter — exists per
  Phase 14 PB-9 lock; verify signature.
* `Metagraph.graphs_by_role` attribute name vs alternative.
* `Metagraph.xrefs` + `Metagraph.intergraph_edges` attribute names
  (probe-confirmed at PB-21 — should exist).
* `_resolve_persister` + `_resolve_kl` CLI helper singleton pattern.
* `hard_delete_user(persister: Optional[LocalPersister] = None)`
  signature evolution — test backward-compat sweep.
* `mindsos_admin` package — does it already import from
  `mindsos_knowledge.types`? Phase 25 adds it; verify no circular
  import.

## How to find things

* Design log:
  `halvim_mindsos/confirmation_docs/PHASE_25_DESIGN_LOG.md` —
  47-PB-candidate cascade ledger; §2 final locks (17-pick
  consolidation); §4 ADR delta; §5 implementation references with
  CONCRETE CODE SHAPES for every NEW/MODIFIED surface; §6 out-of-
  scope; §7 saturation note; §8 Phase 24 carry-forwards.
* Impl chat handoff prompt:
  `halvim_mindsos/confirmation_docs/PHASE_25_NEXT_CHAT_PROMPT.md`
  (replaced; old design-chat prompt now historical).
* PHASE_MAP §25 row — concise rollup with cross-refs.
* Phase 24 design-pass precedent:
  `halvim_mindsos/confirmation_docs/PHASE_24_DESIGN_LOG.md` (Round
  0 PB-Z1..Z22 methodology).
```
