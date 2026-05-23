"""
Universal audit logging for the Server Layer.

Phase 18 ships the full ADR-0013 event-constant enum upfront per Phase
18 PB-34 — constants for events that won't fire until Phase 19+ are
declared here so the roster is grep-able from a single file.

Phase 18 actually FIRES (writes audit rows for) only a subset:

* :data:`EVT_BOOTSTRAP` — first-admin bootstrap CLI verb per ADR-0012 +
  Phase 18 PB-27.
* :data:`EVT_ADMIN_CREATE_USER` — user-create CLI verb when called by an
  admin session (Phase 18 path: from bootstrap helper or future admin
  CLI).
* :data:`EVT_LOGIN_FAILED` — :func:`mindsos_server.users.verify` writes
  on auth failure with private cause in ``extra_json``.
* :data:`EVT_PERMISSION_DENIED` — future ``_require_or_audit`` wrapper
  (Phase 21+); declared here for completeness.

All other constants are declared but unused at Phase 18 ship — Phase
19/20/21/22/24 consumers wire them.

Timestamps per Phase 18 PB-35 — TEXT ISO-8601 UTC with millisecond
precision via :func:`_now_utc_iso`. Lex-sortable; timezone explicit.

Per ADR-0013 §Decision — "Audits are written in the same SQLite
transaction as the state change where feasible." Phase 18
:func:`write_audit` takes the connection from the caller; the caller
controls commit boundaries. For user-create the audit row + users row
are inserted in the same explicit transaction.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any, Mapping


# ---------------------------------------------------------------------------
# Audit event constants — FULL ADR-0013 enum per Phase 18 PB-34
# ---------------------------------------------------------------------------

# Authentication & session events.
#: Successful login (Phase 19 consumer).
EVT_LOGIN = "EVT_LOGIN"
#: Failed login attempt (Phase 18 :func:`users.verify`; Phase 19 login()).
EVT_LOGIN_FAILED = "EVT_LOGIN_FAILED"
#: Login rejected because user is already logged in (Phase 19, ADR-0005).
EVT_LOGIN_REJECTED_CONCURRENT = "EVT_LOGIN_REJECTED_CONCURRENT"
#: User self-logout (Phase 19).
EVT_LOGOUT = "EVT_LOGOUT"

# Authorization events.
#: Capability check denied; emitted by ``_require_or_audit`` (Phase 21+).
EVT_PERMISSION_DENIED = "EVT_PERMISSION_DENIED"

# User-management events.
#: Admin created a new user (Phase 18 consumer).
EVT_ADMIN_CREATE_USER = "EVT_ADMIN_CREATE_USER"
#: Admin promoted a user to admin role (Phase 22).
EVT_ADMIN_PROMOTE_USER = "EVT_ADMIN_PROMOTE_USER"
#: Admin demoted a user from admin role (Phase 22).
EVT_ADMIN_DEMOTE_USER = "EVT_ADMIN_DEMOTE_USER"
#: Admin disabled a user (Phase 22).
EVT_ADMIN_DISABLE_USER = "EVT_ADMIN_DISABLE_USER"
#: Admin enabled a user (Phase 22).
EVT_ADMIN_ENABLE_USER = "EVT_ADMIN_ENABLE_USER"
#: Hard delete of a user + their Local (Phase 22).
EVT_HARD_DELETE_USER = "EVT_HARD_DELETE_USER"
#: Password change (Phase 22 admin reset; later self-service if added).
EVT_PASSWORD_CHANGED = "EVT_PASSWORD_CHANGED"

# Bootstrap / recovery events.
#: First-admin bootstrap via CLI (Phase 18 consumer per PB-27).
#: ``actor_user`` is the OS user (``pwd.getpwuid(os.getuid())``) per
#: ADR-0012 — there is no Session at bootstrap time.
EVT_BOOTSTRAP = "EVT_BOOTSTRAP"
#: Reset-admin lock-out recovery (Phase 20).
EVT_RESET_ADMIN = "EVT_RESET_ADMIN"

# Session admin events.
#: Admin killed a user's session (Phase 22).
EVT_KILL_SESSION = "EVT_KILL_SESSION"

# Cross-user read events (Phase 18 PB-34 declaration; Phase 25 first
# consumer per ADR-0008 §amendment-1).
#: Admin opened an admin-cross-user-read transient install of another
#: user's Local.
#:
#: Declared at Phase 18 PB-34; first fires at Phase 25's
#: :func:`mindsos_server.orchestrator.read_other_local` ctx mgr.
#:
#: ``extra_json`` payload shape (Phase 25 PB-31 lock):
#:
#: .. code-block:: python
#:
#:     {
#:         "admin_user_id":                str,             # caller (== actor_user)
#:         "target_user_id":               str,             # whose Local was installed
#:         "transient":                    bool,            # always True at v1
#:         "install_was_existing":         bool,            # always False at v1 production
#:                                                          # (true only in nested in-process
#:                                                          # test exercises of bump branch)
#:         "refcount_after_acquire":       int,             # always 1 at v1 production
#:         "target_role_graph_node_counts": dict[str, int], # role → node count
#:     }
#:
#: Per ADR-0008 §Consequences "audit MUST outlive subjects" — the row
#: persists after the install record itself is torn down on
#: refcount→0. No EVT_CROSS_USER_READ_RELEASE counterpart at v1
#: (release symmetry is bookkeeping, not audit-worthy; the install
#: row carries enough state for forensic reconstruction).
EVT_CROSS_USER_READ_INSTALL = "EVT_CROSS_USER_READ_INSTALL"

# Promotion + release events (Phase 24 — ADR-0118 + ADR-0114 + ADR-0115).
#
# Phase 24 design log PB-11(a) shrank PIVOT §7.6's 8-event slate to 4
# v1 events: 4 deferred to Phase 25 alongside source-user-Local path +
# lazy migration (EVT_DRAFT_FROZEN, EVT_DRAFT_UNFROZEN,
# EVT_MIGRATION_APPLIED, EVT_MIGRATION_FAILED — declared at P25).
#
# Phase 24 design log PB-27(a) locked the ``extra_json`` payload
# shapes (documented under each constant below). Schema-level
# enforcement is in code (write callsites), not at the audit table
# (per ADR-0013 §Rationale "JSON extras, not columns").
#
# Phase 18 PB-34 ship had placeholder constants (``EVT_PROMOTION_
# COMMITTED``, ``EVT_PROMOTION_REJECTED_STALE_REPORT``, ``EVT_
# PROMOTION_FAILED``) reflecting the pre-pivot ADR-0007 / ADR-0049
# semantic. At Phase 24, those constants are replaced with the
# release-model slate per Phase 24 design log §"Audit event naming"
# (Round 1 PB-6 + PB-11). The placeholders were declared-but-never-
# fired through Phase 18-22, so no shipped consumer breaks.

#: Promotion proposed by admin via
#: :func:`mindsos_admin.propose_for_promotion` (Phase 24 first-fire).
#:
#: ``extra_json`` shape (PB-27(a)):
#: ``{ proposer_admin_user_id: str, mutation_ids: list[int],
#:     items_count: int, kinds: list[str], roles_affected: list[str] }``
EVT_PROMOTION_PROPOSED = "EVT_PROMOTION_PROPOSED"

#: Promotion rejected by admin (Phase 24 first-declared; reserved
#: for v2 reject verb — v1 has no separate reject step per Phase 24
#: design log PB-10(a) SHIPPED+FAILED-only release lifecycle).
#:
#: ``extra_json`` shape (PB-27(a)):
#: ``{ proposer_admin_user_id: str, mutation_ids: list[int],
#:     reason: str }``
EVT_PROMOTION_REJECTED = "EVT_PROMOTION_REJECTED"

#: Release shipped successfully via
#: :func:`mindsos_server.release.release_update` (Phase 24 first-fire).
#:
#: ``extra_json`` shape (PB-27(a)):
#: ``{ release_id: int, mutations_shipped_count: int,
#:     roles_affected: list[str], parent_release_id: int | None }``
EVT_RELEASE_SHIPPED = "EVT_RELEASE_SHIPPED"

#: Release failed (audit gate blocked or FalkorDB write raised) via
#: :func:`mindsos_server.release.release_update` (Phase 24 first-fire).
#:
#: ``extra_json`` shape (PB-27(a)):
#: ``{ release_id: int | None, failed_at_role: str | None,
#:     error_class: str, mutations_attempted_count: int,
#:     roles_shipped_before_failure: list[str] }``
#:
#: ``error_class`` is one of ``"blocking_similarity_findings"`` |
#: ``"empty_comparison"`` (ADR-0114 §am3 + PB-Z16) | ``"FalkorDBWriteError"``.
EVT_RELEASE_FAILED = "EVT_RELEASE_FAILED"

# Audit-query events (Phase 21, ADR-0013 §am2 PB-16).
#: Happy-path audit emission for :func:`mindsos_server.admin.admin_query_audit`.
#: ADR-0013 §Decision: "Every privileged endpoint audits both its happy path
#: and its denial path." Phase 21 first-fires; included in default reader
#: output per PB-16i (transparency — an attacker running admin_query_audit
#: shows up in the log).
EVT_AUDIT_QUERY = "EVT_AUDIT_QUERY"


#: All audit event constants in stable declaration order. Convenience
#: tuple for tests + future enumeration. Renaming any constant is a
#: breaking change; new events append.
ALL_AUDIT_EVENTS: tuple[str, ...] = (
    EVT_LOGIN,
    EVT_LOGIN_FAILED,
    EVT_LOGIN_REJECTED_CONCURRENT,
    EVT_LOGOUT,
    EVT_PERMISSION_DENIED,
    EVT_ADMIN_CREATE_USER,
    EVT_ADMIN_PROMOTE_USER,
    EVT_ADMIN_DEMOTE_USER,
    EVT_ADMIN_DISABLE_USER,
    EVT_ADMIN_ENABLE_USER,
    EVT_HARD_DELETE_USER,
    EVT_PASSWORD_CHANGED,
    EVT_BOOTSTRAP,
    EVT_RESET_ADMIN,
    EVT_KILL_SESSION,
    EVT_CROSS_USER_READ_INSTALL,
    EVT_PROMOTION_PROPOSED,
    EVT_PROMOTION_REJECTED,
    EVT_RELEASE_SHIPPED,
    EVT_RELEASE_FAILED,
    EVT_AUDIT_QUERY,
)


# ---------------------------------------------------------------------------
# Timestamp + writer
# ---------------------------------------------------------------------------


def _now_utc_iso() -> str:
    """
    Canonical TEXT ISO-8601 UTC millisecond timestamp per Phase 18 PB-35.

    Format: ``YYYY-MM-DDTHH:MM:SS.mmmZ`` (always Z-suffixed; always
    millisecond-precision). Lex-sortable == chronologically sortable;
    timezone is explicit.

    Tests assert exact format invariance via regex.
    """
    now = datetime.now(UTC)
    # Format with milliseconds (3 digits) + Z suffix; manually trim
    # microseconds to milliseconds since strftime has no native ms.
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def write_audit(
    conn: sqlite3.Connection,
    *,
    actor: str | None,
    event: str,
    target: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> None:
    """
    Write a row to the ``audit`` table.

    Does NOT commit — caller controls the transaction boundary per
    ADR-0013 §Decision ("Audits are written in the same SQLite
    transaction as the state change where feasible").

    Per Phase 18 PB-34 — ``event`` SHOULD be one of the constants in
    :data:`ALL_AUDIT_EVENTS`, but the writer does not enforce this
    (callers occasionally need custom events; the constant convention
    is for greppability, not for runtime validation).

    Args:
        conn: SQLite connection (typically from
            :func:`mindsos_server._db.open_db`).
        actor: ``user_id`` of the actor, or OS-user string for
            session-less events (``EVT_BOOTSTRAP``, ``EVT_RESET_ADMIN``).
            None for future system-actor events.
        event: One of :data:`ALL_AUDIT_EVENTS`.
        target: ``user_id`` the event is about (e.g., target of
            ``EVT_ADMIN_CREATE_USER``). None when N/A.
        extra: Event-specific fields stored as JSON in ``extra_json``.
            Defaults to empty object. Caller responsibility: values
            must be JSON-serializable.
    """
    conn.execute(
        "INSERT INTO audit (ts, actor_user, event, target_user, extra_json) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            _now_utc_iso(),
            actor,
            event,
            target,
            json.dumps(extra) if extra is not None else "{}",
        ),
    )
