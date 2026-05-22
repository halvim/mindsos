"""
Capability-check wrapper with audit-on-denial.

Phase 21 PB-6 lock. ADR-0013 §Decision: "Capability checks go through
``_require_or_audit(session, CAP)`` which writes ``PERMISSION_DENIED``
before raising ``PermissionDeniedError``." Phase 21 first-construction;
Phase 22 second+ consumers (5+ admin verbs all routing through this
wrapper).

ADR-0013 §amendment-2 documents the conn-first signature divergence
from the ADR's original wording — the codebase's conn-first convention
wins (all Phase 19/20 verbs take conn positionally). The additive
``verb`` kwarg per PB-13 lets the audit row carry the calling
function's name; operator audit-review pattern "which verbs got denied
for user X" is answerable from a single column-equality query on
``extra_json.verb`` once Phase 21's reader lands.

The wrapper writes the denial-path audit + commits + raises. Happy
path returns silently — the caller's verb-specific happy-path audit
emission is the caller's responsibility (e.g.
:func:`mindsos_server.admin.admin_query_audit` writes
:data:`EVT_AUDIT_QUERY` at the end of its body per PB-16 + ADR-0013
§Decision "Every privileged endpoint audits both its happy path and
its denial path").
"""

from __future__ import annotations

import sqlite3

from mindsos_server.audit import EVT_PERMISSION_DENIED, write_audit
from mindsos_server.errors import PermissionDeniedError
from mindsos_server.session import Session


def _require_or_audit(
    conn: sqlite3.Connection,
    session: Session,
    capability: str,
    *,
    verb: str,
) -> None:
    """
    Assert ``session`` has ``capability``. On denial, write one
    :data:`EVT_PERMISSION_DENIED` audit row (committed) and raise
    :class:`PermissionDeniedError`.

    Happy path returns silently. The caller is responsible for any
    verb-specific happy-path audit emission.

    Args:
        conn: SQLite connection. The denial-path audit row INSERT +
            commit happen on this connection.
        session: Caller's session (typically constructed by
            :func:`mindsos_server.sessions.session_from_token` or
            :meth:`mindsos_server.session.Session.for_testing`).
        capability: Capability constant from
            :mod:`mindsos_server.capabilities` (e.g.
            ``CAN_VIEW_AUDIT_LOG``).
        verb: Calling function name (e.g. ``"admin_query_audit"``).
            Recorded in ``EVT_PERMISSION_DENIED.extra_json.verb`` per
            Phase 21 PB-13.

    Raises:
        PermissionDeniedError: If ``session.has(capability)`` is
            ``False``. The audit row is written + committed BEFORE
            the raise.

    Note:
        The denial-path commit is a deliberate transaction-boundary
        choice: the audit row must survive even if the caller's outer
        transaction (if any) rolls back. ADR-0013 §Consequences:
        "Permission denials are audit events" — they cannot be lost
        to rollback.
    """
    if session.has(capability):
        return
    # Denial path: write audit + commit + raise.
    write_audit(
        conn,
        actor=session.user_id,
        event=EVT_PERMISSION_DENIED,
        target=None,
        extra={"capability": capability, "verb": verb},
    )
    conn.commit()
    raise PermissionDeniedError(session.user_id, capability)
