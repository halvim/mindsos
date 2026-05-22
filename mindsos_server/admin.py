"""
mindsos_server.admin — admin verbs that operate on the user store + sessions table.

Phase 20 ships ONE verb: :func:`reset_admin` — the lock-out recovery
escape hatch per ADR-0012 + ADR-0012 §amendment-2.

Pre-positions the ``admin.py`` module per Phase 20 PB-Z. Phase 22 will
add ``admin_promote_user``, ``admin_demote_user``, ``admin_disable_user``,
``admin_enable_user``, ``admin_kill_session``, ``hard_delete_user``
to this module + the ``_assert_not_sole_admin`` helper + ``LastAdminError``
class (deferred from Phase 20 per PB-B — no Phase 20 caller exists for
the helper).

Module conventions (inherited from Phase 18 ``users.py``):

* Functions take a ``conn: sqlite3.Connection`` as the first positional
  arg; callers control the transaction boundary by NOT-passing a
  pre-committed connection. ``reset_admin`` commits internally per
  PB-R single-tx lock.
* Argon2 parameters are injected as ``params=PRODUCTION_PARAMS`` kwarg
  (Phase 18 PB-14 convention); tests pass ``_TEST_FAST_PARAMS``.
* Audit actor for session-less verbs is the OS user from
  ``pwd.getpwuid(os.getuid()).pw_name`` (Phase 18 bootstrap precedent;
  ADR-0012 §amendment-1).

See ``confirmation_docs/PHASE_20_DESIGN_LOG.md`` §1 rounds 1-4 for the
13-pick rationale and §5 for the impl reference; ADR-0012 §amendment-2
for the documentary contract.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from mindsos_server._argon2 import (
    PRODUCTION_PARAMS,
    Argon2Params,
    hash_password,
)
from mindsos_server.audit import (
    EVT_ADMIN_ENABLE_USER,
    EVT_KILL_SESSION,
    EVT_RESET_ADMIN,
    write_audit,
)
from mindsos_server.errors import NotAnAdminError, UserNotFoundError


@dataclass(frozen=True)
class ResetAdminResult:
    """
    Return type of :func:`reset_admin`.

    Tests + CLI ``--json`` payload + future audit reader (Phase 21)
    consume these three fields. ``sessions_killed`` is also denormalized
    into the ``EVT_RESET_ADMIN`` audit row's ``extra_json`` per PB-BB so
    the audit reader can answer "how many sessions were killed in user
    X's last reset" without joining ``EVT_KILL_SESSION`` rows.
    """

    user_id: str
    sessions_killed: int
    was_disabled: bool


def reset_admin(
    conn: sqlite3.Connection,
    user_id: str,
    new_password: str,
    *,
    os_user: str,
    params: Argon2Params = PRODUCTION_PARAMS,
) -> ResetAdminResult:
    """
    Rotate an existing admin's password + re-enable + kill sessions.

    Lock-out recovery per ADR-0012 §Decision + ADR-0012 §amendment-2.

    Pre-conditions (enforced in order):

    1. ``user_id`` must exist in ``users`` (else :class:`UserNotFoundError`
       per PB-A + PB-O).
    2. ``users.actor_role`` for that row must be ``'admin'`` (else
       :class:`NotAnAdminError` per PB-E + PB-N). Reset-admin will NEVER
       escalate a non-admin to admin — that path is :func:`admin_promote_user`
       (Phase 22), gated by ``CAN_MANAGE_USERS``.

    On success (all in a single SQLite transaction per PB-R, in the
    locked order ``DELETE → UPDATE → INSERT audits → commit``):

    * **DELETE** every row from ``sessions`` whose ``user_id`` matches.
      Captured first via SELECT for per-row audit emission. Killed
      tokens are unrecoverable.
    * **UPDATE** ``users``: replace ``password_hash`` with a fresh
      argon2id hash (fresh salt) at the given ``params``; force
      ``disabled = 0`` to re-enable a disabled-admin recovery target.
    * **INSERT** N× :data:`EVT_KILL_SESSION` audit rows (one per killed
      session) with ``extra = {"session_id": sid, "context":
      "reset_admin"}`` per PB-AA. Reuses the Phase 18-declared constant;
      first-fire of EVT_KILL_SESSION lifts from Phase 22 to Phase 20
      (PB-D). Phase 22 ``admin_kill_session`` is the second consumer.
    * **INSERT** 1× :data:`EVT_ADMIN_ENABLE_USER` audit row IFF the
      target was disabled, with ``extra = {"context": "reset_admin"}``
      per PB-U. First-fire also lifts to Phase 20.
    * **INSERT** 1× :data:`EVT_RESET_ADMIN` audit row with
      ``extra = {"was_disabled": bool, "sessions_killed": N}`` per
      PB-BB. The denormalized fields let Phase 21's audit reader
      answer reset-summary queries without joining.
    * **COMMIT**. Single-tx atomicity per PB-R closes the
      "UPDATE committed but DELETE didn't" crash-window where old
      tokens would silently authenticate against the new password.

    Audit ``actor`` is the OS user per ADR-0012 §Rationale ("filesystem
    access is the acceptable authority floor"). Reset-admin runs
    without a Session by definition — the operator's proof-of-authority
    is having shell access to ``server.db``.

    Args:
        conn: SQLite connection (typically from
            :func:`mindsos_server._db.open_db`). Must have schema v2 +
            ``PRAGMA foreign_keys=ON`` (Phase 18 PB-19 default).
        user_id: Target admin's user_id. Existence + admin-role checked.
        new_password: Plaintext; argon2id-hashed before UPDATE. Read
            by the CLI from stdin per PB-G (no ``--password`` flag).
        os_user: OS user invoking reset-admin (the CLI passes
            ``pwd.getpwuid(os.getuid()).pw_name``). Becomes
            ``actor_user`` on every audit row written by this verb.
        params: argon2id parameters. Defaults to
            :data:`PRODUCTION_PARAMS`; tests pass
            :data:`_TEST_FAST_PARAMS`. Mirrors Phase 18 PB-14
            convention for ``insert_user`` + ``_insert_first_admin``.

    Raises:
        UserNotFoundError: target ``user_id`` does not exist in ``users``.
        NotAnAdminError: target exists but ``actor_role != 'admin'``.

    Returns:
        :class:`ResetAdminResult` with ``user_id``, ``sessions_killed``
        (may be 0), and ``was_disabled`` (True iff the row's
        ``disabled`` column was 1 before the UPDATE).
    """
    # ---- Step 1: probe target (existence + role + disabled state). -----
    row = conn.execute(
        "SELECT actor_role, disabled FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        raise UserNotFoundError(user_id)
    actual_role, disabled_int = row[0], int(row[1])
    if actual_role != "admin":
        raise NotAnAdminError(user_id, actual_role)
    was_disabled = bool(disabled_int)

    # ---- Step 2: capture session_ids BEFORE delete (for per-row audit). --
    # SELECT-then-DELETE race in DELETE: same race as Phase 19
    # kill_my_own_sessions; CLI-only product → concurrency is one-shell
    # per invocation. Not opening a new vulnerability surface.
    rows = conn.execute(
        "SELECT session_id FROM sessions WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    session_ids = [r[0] for r in rows]

    # ---- Step 3: single transaction, DELETE-then-UPDATE order (PB-R). ---
    # Order matters: if UPDATE commits and DELETE doesn't, old tokens
    # would auth against the new password until the (now expired) row
    # exits via lazy expiry — strictly worse than the pre-reset state.
    # DELETE first ensures any partial-failure state is "sessions gone +
    # password unchanged" (operator can re-run reset-admin cleanly).
    conn.execute(
        "DELETE FROM sessions WHERE user_id = ?",
        (user_id,),
    )

    new_hash = hash_password(new_password, params=params)
    conn.execute(
        "UPDATE users SET password_hash = ?, disabled = 0 WHERE user_id = ?",
        (new_hash, user_id),
    )

    # ---- Step 4: audit rows (same transaction per ADR-0013 §Decision). --
    # Per PB-D + PB-AA: one EVT_KILL_SESSION per killed session, with
    # context="reset_admin" discriminator matching Phase 19's "context"
    # key naming for kill_my_own_sessions.
    for sid in session_ids:
        write_audit(
            conn,
            actor=os_user,
            event=EVT_KILL_SESSION,
            target=user_id,
            extra={"session_id": sid, "context": "reset_admin"},
        )

    # Per PB-U: conditional EVT_ADMIN_ENABLE_USER iff target was disabled.
    # Phase 22's admin_enable_user will be the second consumer.
    if was_disabled:
        write_audit(
            conn,
            actor=os_user,
            event=EVT_ADMIN_ENABLE_USER,
            target=user_id,
            extra={"context": "reset_admin"},
        )

    # Per PB-D + PB-BB: single summary row; sessions_killed denormalized
    # for the Phase 21 audit reader.
    write_audit(
        conn,
        actor=os_user,
        event=EVT_RESET_ADMIN,
        target=user_id,
        extra={
            "was_disabled": was_disabled,
            "sessions_killed": len(session_ids),
        },
    )

    conn.commit()

    return ResetAdminResult(
        user_id=user_id,
        sessions_killed=len(session_ids),
        was_disabled=was_disabled,
    )
