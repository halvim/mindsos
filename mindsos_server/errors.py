"""
Exception types for the Server Layer.

Phase 18 ships :class:`AuthFailedError` + :class:`UserAlreadyExistsError`.
Phase 19 adds :class:`InvalidSessionError` (PB-14 — unified
expired/missing per ADR-0003 §amendment-1) + :class:`AlreadyLoggedInError`
(PB-3 — 2-field payload per ADR-0005 §amendment-1). Phase 20 adds
:class:`UserNotFoundError` (PB-O) + :class:`NotAnAdminError` (PB-N) for
reset-admin's target-validation gate per ADR-0012 §amendment-2.

* :class:`AuthFailedError` — single opaque error covering all three
  authentication failure causes (unknown_user / bad_password / disabled)
  per Phase 18 PB-23. The public message is uniform ("auth failed") to
  prevent user-enumeration via differential error messages. The private
  ``cause`` attribute carries the actual reason for internal audit-write
  use; tests assert on ``.cause`` while CLI / future HTTP callers see
  only the opaque message.
* :class:`UserAlreadyExistsError` — distinct from :class:`AuthFailedError`
  per Phase 18 PB-30. Create-path UNIQUE-conflict errors are not auth
  errors; the security-leak concerns from PB-23 do not apply (the caller
  by definition already has CAN_MANAGE_USERS capability to be hitting
  create-user, so the existence of the user_id is not a secret to them).
* :class:`InvalidSessionError` — single opaque error covering all three
  session-lookup failure causes (expired-sliding / expired-absolute /
  not-found) per Phase 19 PB-14 + ADR-0003 §amendment-1. Mirrors
  AuthFailedError's PB-23 pattern: uniform public message, private
  ``.cause`` for internal use. The three causes have the same threat-
  model property — a 256-bit-random guesser learns nothing useful from
  the differential — so unifying them simplifies callers without
  security loss. Replaces ADR-0003 §Decision's earlier ``SessionExpiredError``.
* :class:`AlreadyLoggedInError` — raised by
  :func:`mindsos_server.sessions.login` when an active (non-expired)
  session already exists for the user_id per ADR-0005. 2-field payload
  ``{existing_session_id, created_at}`` per ADR-0005 §amendment-1 (the
  original 3-field shape's ``source`` field has no meaning in CLI-only
  context per Phase 19 PB-3 and is deferred to the future HTTP-daemon
  phase).

See ``confirmation_docs/PHASE_18_DESIGN_LOG.md`` §1 round 3 (PB-22 /
PB-23 / PB-30), ``confirmation_docs/PHASE_19_DESIGN_LOG.md`` §1 round 1
PB-3 + round 3 PB-14, and ``confirmation_docs/PHASE_20_DESIGN_LOG.md``
§1 round 3 PB-N + PB-O for the rationale chain.
"""

from __future__ import annotations

from enum import Enum


class AuthFailureCause(str, Enum):
    """
    Private cause enum for :class:`AuthFailedError`.

    Internal to the server's audit-write path — never exposed via the
    exception's ``__str__`` / ``__repr__`` (per Phase 18 PB-23). Tests
    assert on the ``.cause`` attribute; callers who want to inspect cause
    are doing so deliberately and accept the responsibility of not
    logging it.

    Values are stable strings (used as audit-row ``extra_json`` payload
    keys) — renaming is a breaking change.
    """

    #: User row with that ``user_id`` does not exist in ``users``.
    UNKNOWN_USER = "UNKNOWN_USER"

    #: User row exists but argon2id ``verify_password`` returned False.
    BAD_PASSWORD = "BAD_PASSWORD"

    #: User row exists with correct password but ``disabled = 1``
    #: (Phase 22 ships the disable/enable CLI verbs; Phase 18 verify
    #: honors the column from day one per PB-15).
    DISABLED = "DISABLED"


class AuthFailedError(Exception):
    """
    Raised when :func:`mindsos_server.users.verify` cannot authenticate.

    The public message is uniform ("auth failed") regardless of cause to
    prevent user-enumeration attacks (per Phase 18 PB-22 / PB-23). The
    private ``cause`` attribute carries the actual reason and is consumed
    by the server's audit-write path (``EVT_LOGIN_FAILED`` ``extra_json``).

    Callers MUST NOT log ``repr(exc)`` or surface the cause to end users
    via response bodies / CLI stderr. The cause is internal-only.

    Tests assert on ``exc.cause`` (typed) while CLI / future HTTP layers
    assert on the opaque public message.
    """

    #: Uniform public message — same across all causes per PB-23.
    PUBLIC_MESSAGE = "auth failed"

    def __init__(self, cause: AuthFailureCause) -> None:
        super().__init__(self.PUBLIC_MESSAGE)
        self.cause: AuthFailureCause = cause

    def __str__(self) -> str:  # pragma: no cover — Exception.__str__ trivially uses args
        return self.PUBLIC_MESSAGE


class UserAlreadyExistsError(Exception):
    """
    Raised when :func:`mindsos_server.users.insert_user` hits a
    ``UNIQUE`` constraint violation on ``users.user_id``.

    Distinct from :class:`AuthFailedError` per Phase 18 PB-30: create-path
    errors are not auth errors. The user_id is included in the message —
    the caller is by definition authenticated and authorized to be
    creating users (``CAN_MANAGE_USERS``), so revealing that the chosen
    id is taken is not a secrecy concern.
    """

    def __init__(self, user_id: str) -> None:
        super().__init__(f"user_id already exists: {user_id!r}")
        self.user_id = user_id


# ---------------------------------------------------------------------------
# Phase 19 additions — session-layer exceptions (PB-3 + PB-14)
# ---------------------------------------------------------------------------


class InvalidSessionCause(str, Enum):
    """
    Private cause enum for :class:`InvalidSessionError`.

    Phase 19 PB-14 + ADR-0003 §amendment-1 unifies expired-sliding /
    expired-absolute / not-found into one opaque exception. The cause
    enum carries the differential for internal audit-write + test
    assertions; callers see only the uniform public message.

    Values are stable strings (used as audit-row ``extra_json`` payload
    keys at Phase 21 audit reader) — renaming is a breaking change.
    """

    #: Session row exists; ``last_seen_at + ttl.sliding_seconds`` is in
    #: the past. Lazy expiry deletes the row before raising.
    EXPIRED_SLIDING = "EXPIRED_SLIDING"

    #: Session row exists; ``created_at + ttl.absolute_seconds`` is in
    #: the past. Lazy expiry deletes the row before raising. Takes
    #: precedence over EXPIRED_SLIDING when both apply (the absolute cap
    #: is the harder limit per ADR-0003 §Rationale).
    EXPIRED_ABSOLUTE = "EXPIRED_ABSOLUTE"

    #: No session row matches the token hash. Either never issued, or
    #: already-deleted via logout / kill_my_own_sessions / lazy expiry
    #: from a prior lookup.
    NOT_FOUND = "NOT_FOUND"


class InvalidSessionError(Exception):
    """
    Raised when :func:`mindsos_server.sessions.session_from_token` cannot
    return a valid session.

    Replaces ADR-0003 §Decision's earlier ``SessionExpiredError`` per
    Phase 19 PB-14 — the three failure modes (expired-sliding,
    expired-absolute, not-found) all surface as this single exception
    with uniform public message and private ``.cause`` for internal use.
    Mirrors the Phase 18 PB-23 :class:`AuthFailedError` pattern.

    Threat-model rationale (ADR-0003 §amendment-1): a 256-bit-random
    token guesser learns nothing useful from the differential between
    "your token was once valid but expired" and "your token was never
    valid." HTTP layer (future) maps all three to 401.

    Callers MUST NOT log ``repr(exc)`` or surface the cause to end users
    via response bodies / CLI stderr. The cause is internal-only and
    consumed by the server's audit-write path + tests.
    """

    #: Uniform public message — same across all causes per PB-14 +
    #: ADR-0003 §amendment-1 mirror of Phase 18 PB-23.
    PUBLIC_MESSAGE = "invalid session"

    def __init__(self, cause: InvalidSessionCause) -> None:
        super().__init__(self.PUBLIC_MESSAGE)
        self.cause: InvalidSessionCause = cause

    def __str__(self) -> str:  # pragma: no cover — Exception.__str__ trivial
        return self.PUBLIC_MESSAGE


class AlreadyLoggedInError(Exception):
    """
    Raised by :func:`mindsos_server.sessions.login` when an active
    (non-expired) session already exists for the ``user_id`` per
    ADR-0005.

    Per ADR-0005 §amendment-1 (Phase 19 PB-3), payload is 2-field:
    ``{existing_session_id, created_at}``. The original ADR-0005
    §Decision 3-field shape included a ``source`` field — it is
    deferred to the future HTTP-daemon phase where remote-IP /
    client-app distinctions become meaningful. In CLI-only context
    "source" doesn't distinguish anything informative.

    Per ADR-0005 §amendment-1 §Consequences (PB-8): the
    lazy-expire-then-concurrent-check ordering means that by the time
    this is raised, any expired session for the user has already been
    deleted. The existing_session_id this carries is guaranteed to be
    an active (non-stale) session at raise time.

    Public message includes the existing_session_id and created_at so
    the CLI / future HTTP body has actionable information for the
    user-facing 409 response. This is fine: the existing session is
    held by the same authenticated user (they just passed verify());
    revealing details about their own session is not a secrecy concern.
    """

    def __init__(self, *, existing_session_id: str, created_at: str) -> None:
        super().__init__(
            f"already logged in (session_id={existing_session_id!r}, "
            f"created_at={created_at!r}); use logout or kill_my_own_sessions"
        )
        self.existing_session_id = existing_session_id
        self.created_at = created_at


# ---------------------------------------------------------------------------
# Phase 20 additions — admin-verb target-validation exceptions (PB-N + PB-O)
# ---------------------------------------------------------------------------


class UserNotFoundError(Exception):
    """
    Raised when an admin verb targets a ``user_id`` that does not exist
    in the ``users`` table.

    Phase 20 first-fires from :func:`mindsos_server.admin.reset_admin`
    (PB-O + PB-A). Phase 22 admin verbs (``admin_demote_user``,
    ``admin_disable_user``, ``admin_promote_user``, ``hard_delete_user``)
    will reuse this class for the parallel target-validation gate.

    Distinct from :class:`AuthFailedError(cause=UNKNOWN_USER)` per
    Phase 20 PB-O: reset-admin's "user not found" is not an auth
    failure (no password is being checked). Reusing AuthFailedError
    would ship the misleading public message ``"auth failed"`` for an
    operator who attempted no authentication.

    Caller threat-model: admin verbs require either proof-of-authority
    (filesystem access to ``server.db`` for session-less reset-admin)
    or ``CAN_MANAGE_USERS`` capability (for session-backed Phase 22
    verbs) — in both cases the caller is privileged enough that
    revealing whether a user_id exists is not a secrecy concern.
    Public message includes the target user_id verbatim.
    """

    def __init__(self, target_user_id: str) -> None:
        super().__init__(f"user not found: {target_user_id!r}")
        self.target_user_id = target_user_id


class NotAnAdminError(Exception):
    """
    Raised by :func:`mindsos_server.admin.reset_admin` when the target
    ``user_id`` exists but has ``actor_role != 'admin'``.

    Phase 20 PB-E locks reset-admin's contract to admin-only targets.
    Reset-admin will NEVER escalate a non-admin user to admin —
    that path is :func:`admin_promote_user` (Phase 22), gated by
    ``CAN_MANAGE_USERS``. This separation prevents reset-admin from
    becoming a "promote arbitrary user to admin" backdoor for any
    operator with filesystem access to ``server.db``.

    Per Phase 20 PB-N, the target's actual ``actor_role`` is included
    in the public message. Filesystem-access threat model has no
    enumeration concern: the operator already has read access to
    ``users.actor_role`` for every row. Including the actual role
    makes the error actionable ("you tried to reset 'foo', who is
    role='user'; use admin_promote_user to escalate") rather than
    forcing the operator to grep ``server.db`` to figure out what
    went wrong.
    """

    def __init__(self, target_user_id: str, actual_role: str) -> None:
        super().__init__(
            f"target user {target_user_id!r} is not an admin "
            f"(actor_role={actual_role!r}); reset-admin only rotates "
            f"credentials for existing admins. Use "
            f"`mindsos server admin promote-user` (Phase 22) to "
            f"escalate a non-admin to admin."
        )
        self.target_user_id = target_user_id
        self.actual_role = actual_role


# ---------------------------------------------------------------------------
# Phase 21 additions — capability-denial exception (PB-14)
# ---------------------------------------------------------------------------


class PermissionDeniedError(Exception):
    """
    Raised by :func:`mindsos_server.authz._require_or_audit` when a
    :class:`mindsos_server.session.Session` lacks the required
    capability.

    Phase 21 PB-14 lock. ADR-0013 §Decision: "Capability checks go
    through ``_require_or_audit(session, CAP)`` which writes
    ``PERMISSION_DENIED`` before raising ``PermissionDeniedError``."
    The audit row INSERT + commit is the state change on the denial
    path; the exception is raised AFTER the audit write.

    Phase 21 first-fires from :func:`mindsos_server.admin.admin_query_audit`
    (capability ``CAN_VIEW_AUDIT_LOG``). Phase 22 admin verbs are
    second+ consumers (``admin_promote_user``, ``admin_demote_user``,
    ``admin_disable_user``, ``admin_enable_user`` gated by
    ``CAN_MANAGE_USERS``; ``admin_kill_session`` gated by
    ``CAN_KILL_SESSION``; ``hard_delete_user`` gated by
    ``CAN_HARD_DELETE_ARCHIVED``).

    Constructor shape mirrors :class:`NotAnAdminError` density per
    Phase 20 PB-N. The target_user_id is the session's user_id (the
    user who tried to perform the action and was denied — not a
    different "target" of the action). No enumeration concern: caller
    has either filesystem access to ``server.db`` or holds a session
    whose capabilities are documented in :mod:`mindsos_server.capabilities`.

    Future HTTP transport (no roadmap; CLI-only per PHASE_MAP §1)
    would map this to HTTP 403; ADR-0002 §Decision documents the
    intended mapping. CLI verbs wrap this exception to exit code 3.
    """

    def __init__(self, target_user_id: str, capability: str) -> None:
        super().__init__(
            f"user {target_user_id!r} lacks capability {capability!r}"
        )
        self.target_user_id = target_user_id
        self.capability = capability
