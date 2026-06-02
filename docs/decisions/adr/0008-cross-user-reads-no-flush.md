# ADR-0008: Admin cross-user reads never flush (I-S3) with refcount install pattern

- **Status:** Accepted
- **Date:** 2026-04-22
- **Related:** ADR-0002, ADR-0006, ADR-0009

## Context

Two features of the server need to read another user's Local without a login on that user's behalf: the admin `read_other_local()` context manager (diagnostic reads) and the promotion orchestrator (pulling candidate drafts from each author). In both cases:

- The target user may be **online** — their Local is already installed in KL because of their active session.
- The target user may be **offline** — no install exists; we must fetch from the persister, install transiently, and tear down when done.
- We must **never silently flush** a user's Local on teardown of a read-only operation. Flushing on extract would overwrite FalkorDB with a read-side view that may be racing with the user's own edits or with a promotion.

## Decision

Model installations with an explicit `InstallRecord` per `user_id` held in `MindsOSServer._installed_locals: dict[str, InstallRecord]`:

```python
@dataclass
class InstallRecord:
    user_id: str
    installed_by_session: str | None   # None for transient admin/promote installs
    transient: bool                    # True => extract without flush on refcount→0
    refcount: int                      # incremented per concurrent reader
```

Entry and exit helpers enforce the invariants:

- **On enter.** If no record exists, install the Local (hydrate via `LocalPersister.load`), set `transient=True`, `refcount=1`. If a record exists, bump `refcount` by 1. Record the bump for later release.
- **On exit.** Decrement `refcount`. If the record is `transient` and `refcount == 0`, call `KL.extract_local_metagraph(user_id)` **without** flushing to the persister, then drop the record. If `transient=False` (user is logged in), never flush on extract.

Codified as **invariant I-S3**: *Admin cross-user reads never flush.* Enforced in server code (Core can't distinguish read from write).

The `read_other_local(admin_session, target_user_id)` context manager and the promotion orchestrator's `_acquire_installs_for_promotion` / `_release_installs_for_promotion` helpers are the only two pathways that create transient installs.

## Rationale

- **Safety over convenience.** A "helpful" auto-flush on extract would occasionally trash a user's work; the cost of explicit never-flush is a single boolean per record.
- **Refcounting lets concurrent admins coexist.** Two overlapping `read_other_local` calls on the same target increment and decrement cleanly without double-installing or premature extract.
- **Reuse over re-install.** If the target is online, the already-installed Local is reused with its refcount bumped; we tear down back to the session's own hold at refcount 1. This avoids the hydrate-flush cost of re-fetching.
- **One code path for "online or offline."** The helpers don't branch on the target's session state; they branch on `transient`. Whether the install was born transient or sticky is the only bit that matters.

## Consequences

- Every admin read path must go through the helpers; raw calls to `install_local_metagraph`/`extract_local_metagraph` are forbidden outside this module and flagged in review.
- `InstallRecord.transient` is a load-bearing flag — the test suite has a `persister.fail_save_for.add(user_id)` hook that proves no save is attempted during `read_other_local` teardown (test: `test_similarity_report_no_flush_on_teardown_is3`).
- Promotion's install pattern composes cleanly: the author who happens to be the admin themselves sees `refcount` bump from 1 to 2 and back to 1, with their install staying non-transient.
- Future read-only admin features (audit-driven bulk export, forensic walks) get the same treatment for free.

## Alternatives considered

1. **Always install fresh, always flush on extract.** Rejected — data loss risk; also incurs hydrate cost per access.
2. **Copy-on-read into an isolated Local.** Rejected — doubles memory, and cross-metagraph refs would point at the copy, not the real target.
3. **Per-operation flag ("flush=False")** passed into KL extract. Considered; rejected because KL shouldn't know about the concept of "admin read." The decision is a server-layer concern.
4. **Background GC of stale transient installs.** Overkill for current scale; the sweeper reaps sessions, and transient installs are always inside a `with` block.

## Revisions

### amendment-1 (Phase 22 ship — 2026-05-22) — first-consumer phase shifted P22 → P25

**Trigger:** Phase 22's design pass (round 1, PB-1) discovered that
this ADR's §Decision cannot be honored at Phase 22 even though
PHASE_MAP §22 row originally listed cross-user read as a Phase 22
feature. §Decision REQUIRES:

* `MindsOSServer._installed_locals: dict[str, InstallRecord]` —
  but `MindsOSServer` is a CLASS first-constructed at Phase 25 per
  ADR-0011 §amendment-1 (Phase 19 PB-13 absorption).
* `KL.install_local_metagraph` / `KL.extract_local_metagraph` —
  the KL hydration / extraction surface ships at Phase 25 per the
  SessionProtocol seam (ADR-0011 / ADR-0040 / ADR-0042).
* `LocalPersister.load` — Protocol first-construction at Phase 25
  per ADR-0011 §amendment-1.

None of these mechanisms ship before Phase 25; Phase 22 has no
substrate to refcount-install against. Shipping a stub at Phase 22
would either (a) silently violate §Decision by skipping the
refcount-install model entirely, or (b) raise NotImplementedError
on every call — neither delivers value, both create contract debt.

**Amended behavior:**

* **First consumer of `read_other_local(admin_session, target_user_id)`
  + `_acquire_installs_for_promotion` shifts from Phase 22 to Phase 25.**
  Co-located with `MindsOSServer` construction + `LocalPersister`
  Protocol first-shipment so the §Decision mechanism (refcount-install,
  transient flag, never-flush-on-teardown) lands with a working
  substrate at one site.
* **`CAN_READ_OTHER_LOCALS` capability constant remains at Phase 18
  PB-4** (already in ADMIN_CAPS per ADR-0002 §amendment-1). No
  capability shift; the gate is wire-format-ready at Phase 18, the
  consumer is not.
* **Audit constant `EVT_CROSS_USER_READ_INSTALL` remains pre-declared
  at Phase 18 PB-34**; first-fires at Phase 25 when the verb lands.
* **PHASE_MAP §22 row** no longer lists "cross-user read with
  refcount-install (ADR-0008)" as a Phase 22 Feature; the feature
  moves to Phase 25's row at Phase 22 ship.

**Rationale:** This is a phase-placement amendment, not a §Decision
change. The refcount-install + never-flush-on-teardown model is
preserved verbatim; only the first-consumer slot moves to where
its dependencies are available. Precedent: Phase 19 PB-2 / PB-13
shifted `LocalPersister` + `MindsOSServer` to Phase 25 for identical
"dependency available at later slot" reasoning.

**Out-of-scope:** §Decision's invariant I-S3 ("Admin cross-user reads
never flush") is unchanged; §Rationale unchanged; §Consequences
unchanged. The test `test_similarity_report_no_flush_on_teardown_is3`
shifts to the Phase 25 suite alongside the verb itself.

See `halvim_mindsos/confirmation_docs/PHASE_22_DESIGN_LOG.md` §1
round 1 PB-1 for the dependency-analysis rationale.


### amendment-2 (Phase 25 ship — 2026-05-23) — First consumer ships; refcount-bump branch is test-only at v1 production

**Trigger:** Phase 25 ships the cross-user-read substrate per §amendment-1's "first consumer at Phase 25" lock. The §Decision shape lands verbatim — `InstallRecord` dataclass, `_installed_locals: dict[str, InstallRecord]` registry, `read_other_local(admin_session, target_user_id)` context manager, refcount-install + transient + never-flush-on-teardown invariant I-S3.

Module placement diverges from §Decision's literal `MindsOSServer._installed_locals` — the orchestrator ships as **free functions in `mindsos_server/orchestrator.py`** with module-level `_installed_locals`, `_install_lock`, and `_mutex_registry` per Phase 25 PB-38. `MindsOSServer` class first-construction defers to the first user-Local-write phase (alongside the SQLite + Falkor persisters that would justify the class lifecycle). Module-level state is reset per-test via the autouse `reset_state_for_tests()` helper (PB-R6-03 lock from Round 6 pre-impl re-analysis).

**Refcount-bump branch is unreachable in v1 production.** The CLI per-command-process model means each `mindsos server admin read-local` invocation lives in its own short-lived process; no two `read_other_local` callers can share a `_installed_locals` registry. The refcount-bump branch ships at v1 per §Decision verbatim (no scope cut), exercised only via in-process nested `with` invocations in `tests/phase_25/test_read_other_local_refcount_bump_in_process.py`. The branch becomes production-reachable at the future v2 HTTP-daemon phase where multiple concurrent admin readers share one process.

**Status flip:** Proposed → Accepted with Phase 25 first-consumer ship.

**Coordinated changes at this amendment:**

* `mindsos_server/orchestrator.py` (NEW) — `InstallRecord` dataclass + `read_other_local` ctx mgr + `_install_for` / `_release` / `_node_counts` private helpers + `reset_state_for_tests`.
* `mindsos_server/admin.py::read_other_local_summary` + `ReadOtherLocalSummary` + `RoleGraphSummary` — the v1 admin-diagnostic consumer (PB-26 summary-only output).
* `mindsos_cli/commands/server.py::admin_read_local_cmd` — CLI verb `mindsos server admin read-local` with `--json` flag and `_admin_exit_for` mapping.
* `tests/phase_25/test_read_other_local_*.py` — 4 tests covering I-S3 invariant, refcount-bump in-process, audit payload shape, self-target degenerate case.

**Out-of-scope:** Source-user-Local propose path + lazy migration + sticky (non-transient) installs all defer to the first user-Local-write phase. v1 only emits `transient=True` installs through this code path; the sticky branch in `_install_for` + flush path in `_release` is forward-shape dead code at v1.

**Phase 25 design log:** `halvim_mindsos/confirmation_docs/PHASE_25_DESIGN_LOG.md` §1 Rounds 0-4 (PB-29 bump branch, PB-31 audit payload, PB-37 caller-Local collapse, PB-38 free functions, PB-41/43 saturation locks) + §4 ADR delta + §5 implementation references.
