"""
Exception types for the Server Layer.

Two exception classes ship at Phase 18:

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

See ``confirmation_docs/PHASE_18_DESIGN_LOG.md`` §1 round 3 (PB-22 / PB-23
/ PB-30) for the security rationale and decision ledger.
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
