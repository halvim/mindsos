"""
CLI verbs for the Server Layer (Phase 18 + Phase 19 + Phase 20).

Per Phase 18 PB-32 — verbs live here at ``mindsos_cli/commands/server.py``
following the existing convention (admin.py, graph.py, etc.). Adds
``mindsos_cli → mindsos_server`` dep edge in pyproject per PB-25.

Verb groups (Phase 18):

* ``mindsos server user create <user_id>`` — create a new user; reads
  password from stdin (PB-8 — no ``--password`` flag declared).
* ``mindsos server user list [--json]`` — list all users; never includes
  ``password_hash`` (PB-24 — the User dataclass has no such field).
* ``mindsos server user verify <user_id>`` — diagnostic credential check
  per PB-36; reads password from stdin; exits 0 on success, non-zero on
  ``AuthFailedError`` with opaque "auth failed" stderr message.
* ``mindsos server bootstrap [<user_id>]`` — idempotent first-admin
  bootstrap per PB-27 (lifted from Phase 20); reads password from
  stdin; exits 0 with message if admin already exists per PB-29.

Verb additions (Phase 19):

* ``mindsos server login <user_id> [--print-token] [--json]`` — verify
  credentials + mint session; writes token to ``~/.mindsos/token`` mode
  0600 per PB-5; ``--print-token`` emits to stdout for shell capture.
* ``mindsos server whoami [--json]`` — read token (env > file resolution
  chain per PB-5), call session_from_token, print identity + capabilities
  + computed expires_at. Exit 1 + stderr "not logged in" when no token /
  invalid session in plain mode; exit 0 + ``{"logged_in": false}`` in
  --json mode (pipe-friendly).
* ``mindsos server logout [--json]`` — call logout(token) + delete the
  on-disk token file. Silent no-op on invalid / missing token per
  Phase 19 minor lock.

Verb additions (Phase 20):

* ``mindsos server reset-admin <user_id> [--json]`` — lock-out recovery
  per ADR-0012 §amendment-2. Positional user_id REQUIRED (no prompt
  fallback per PB-G — destructive ops are deliberate). Reads password
  from stdin (PB-G — no ``--password`` flag, mirroring PB-8). Existing
  admin only (UserNotFoundError on missing per PB-A; NotAnAdminError
  on non-admin target per PB-E). Rotates password + re-enables + kills
  all sessions in a single transaction per PB-R.

Verb additions (Phase 21):

* ``mindsos server query-audit [--actor X] [--event Y] [--target Z]
  [--since ISO] [--until ISO] [--after-id N] [--limit N]
  [--count-only] [--json]`` — read rows from the audit log per
  ADR-0013 §amendment-2. Gated on ``CAN_VIEW_AUDIT_LOG`` via
  ``_require_or_audit`` (PB-6); session-backed verb (reads token via
  ``read_token()`` then ``session_from_token``). Inclusive
  ``since``/``until`` bounds (PB-11); ``id`` ASC default order (PB-12);
  cursor pagination via ``--after-id`` (PB-10). ``--count-only`` flips
  to ``SELECT COUNT(*)`` form (PB-4 reframe of "audit stats"). Emits
  ``EVT_AUDIT_QUERY`` happy-path audit row per call (PB-16); ``EVT_PERMISSION_DENIED``
  + raise on non-admin caller (PB-13). Exit 3 on PermissionDeniedError;
  exit 2 on ValueError (bad ISO-8601 / invalid arg).

Per PB-29 — bootstrap idempotency lives at THIS CLI verb (not in the
helper). The helper :func:`mindsos_server.users._insert_first_admin`
is a pure insert; this CLI does the ``count_admins() ≥ 1`` skip check.

Per PB-17 — DB path resolution chain: env > manifest > default. The CLI
uses :func:`mindsos_server._db.resolve_db_path` (env + default only;
manifest fallback is wired here if/when ``mindsos_cli/manifest.toml``
grows a ``[server] db_path`` field).

Per Phase 19 PB-5 — token storage uses
:mod:`mindsos_server._token_storage` (file 0600 default + env override;
no ``--token`` flag declared, mirroring PB-8's no-``--password`` rule).
"""

from __future__ import annotations

import getpass
import json
import os
import pwd
import sys
from typing import Optional

import typer

from mindsos_server._argon2 import PRODUCTION_PARAMS
from mindsos_server._db import open_db, resolve_db_path
from mindsos_server._schema import init_or_migrate
from mindsos_server._token_storage import (
    TOKEN_ENV_VAR,
    delete_token,
    read_token,
    token_source_description,
    write_token,
)
from mindsos_server.admin import AuditRow, admin_query_audit, reset_admin
from mindsos_server.errors import (
    AlreadyLoggedInError,
    AuthFailedError,
    InvalidSessionError,
    NotAnAdminError,
    PermissionDeniedError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from mindsos_server.sessions import (
    PRODUCTION_TTL,
    login,
    logout,
    session_from_token,
)
from mindsos_server.users import (
    _insert_first_admin,
    count_admins,
    insert_user,
    list_users,
    verify,
)


# ---------------------------------------------------------------------------
# Typer apps
# ---------------------------------------------------------------------------

server_app = typer.Typer(
    name="server",
    help="Server-layer admin: user store, auth, bootstrap.",
    no_args_is_help=True,
    add_completion=False,
)

user_app = typer.Typer(
    name="user",
    help="User store CRUD.",
    no_args_is_help=True,
    add_completion=False,
)


# ---------------------------------------------------------------------------
# Helpers — password reading + DB resolution
# ---------------------------------------------------------------------------


def _read_password_stdin(prompt: str = "Password: ") -> str:
    """
    Read a password per Phase 18 PB-8 — ``--password-stdin`` only;
    NEVER from CLI arguments.

    If stdin is a TTY: prompt interactively via :func:`getpass.getpass`
    (no echo, terminal-disciplined).

    If stdin is a pipe (script context): read one line, strip trailing
    newline.

    The flag itself (``--password-stdin``) is NOT declared as a CLI
    option per PB-8 — declaring it would suggest a sibling
    ``--password`` flag exists, which is precisely what we forbid.
    Stdin is the implicit + only password source.
    """
    if sys.stdin.isatty():
        return getpass.getpass(prompt)
    # Pipe mode — read one line.
    line = sys.stdin.readline()
    if not line:
        typer.echo("error: no password provided on stdin", err=True)
        raise typer.Exit(code=2)
    # Strip trailing newline only; preserve other whitespace.
    return line.rstrip("\n").rstrip("\r")


def _resolve_and_open():
    """Resolve DB path per PB-17 + open via PB-19 pragma helper."""
    return open_db(resolve_db_path())


def _ensure_migrated(conn) -> None:
    """Run idempotent v1 migration; safe to call on every CLI invocation."""
    init_or_migrate(conn)


# ---------------------------------------------------------------------------
# `mindsos server bootstrap`
# ---------------------------------------------------------------------------


@server_app.command(name="bootstrap")
def bootstrap(
    user_id: Optional[str] = typer.Argument(
        None,
        help="Admin user_id. If omitted, prompts interactively.",
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Emit JSON output to stdout."
    ),
) -> None:
    """
    Idempotent first-admin bootstrap per ADR-0012 + Phase 18 PB-27.

    If admins already exist, exits 0 with a message — NEVER modifies
    state per ADR-0012 §Decision ("Makes the command safe to run in
    deployment scripts").

    On fresh install:
    * Prompts for ``user_id`` if not given.
    * Reads password from stdin (TTY: ``getpass`` prompt; pipe: one
      line) per PB-8.
    * argon2id-hashes (PRODUCTION_PARAMS).
    * Inserts with ``actor_role='admin'``; audits ``EVT_BOOTSTRAP`` with
      the OS user as ``actor_user`` per ADR-0012.
    """
    with _resolve_and_open() as conn:
        _ensure_migrated(conn)

        # PB-29 — idempotency check at CLI level (not in helper).
        existing = count_admins(conn)
        if existing >= 1:
            message = (
                f"admin already exists (count={existing}); bootstrap is a "
                f"no-op. Use `mindsos server reset-admin` (Phase 20) for "
                f"lock-out recovery."
            )
            if json_out:
                typer.echo(json.dumps({"status": "skipped", "admin_count": existing}))
            else:
                typer.echo(message)
            raise typer.Exit(code=0)

        resolved_user_id = user_id if user_id is not None else typer.prompt(
            "Admin user_id", type=str
        )
        password = _read_password_stdin()

        # OS user as actor per ADR-0012.
        os_user = pwd.getpwuid(os.getuid()).pw_name

        try:
            user = _insert_first_admin(
                conn,
                resolved_user_id,
                password,
                params=PRODUCTION_PARAMS,
                os_user=os_user,
            )
        except (ValueError, UserAlreadyExistsError) as exc:
            typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(code=2) from exc

        if json_out:
            typer.echo(
                json.dumps(
                    {
                        "status": "created",
                        "user_id": user.user_id,
                        "actor_role": user.actor_role,
                        "created_at": user.created_at.isoformat(),
                    }
                )
            )
        else:
            typer.echo(f"admin bootstrapped: user_id={user.user_id!r}")


# ---------------------------------------------------------------------------
# `mindsos server user create`
# ---------------------------------------------------------------------------


@user_app.command(name="create")
def user_create(
    user_id: str = typer.Argument(..., help="New user's user_id."),
    actor_role: str = typer.Option(
        "user",
        "--role",
        help="Role for the new user: 'user' or 'admin'.",
        show_default=True,
    ),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """
    Create a new user. Reads password from stdin per PB-8.

    NOTE: at Phase 18 ship this CLI is not capability-gated (Phase 19+
    ships login + Session → Phase 21+ ships ``_require_or_audit``
    wrapper). The first admin must be created via
    ``mindsos server bootstrap`` (Phase 18); subsequent users via this
    verb. Phase 22 admin ops re-wires this verb behind ``CAN_MANAGE_USERS``.
    """
    if actor_role not in ("user", "admin"):
        typer.echo(
            f"error: --role must be 'user' or 'admin'; got {actor_role!r}",
            err=True,
        )
        raise typer.Exit(code=2)

    password = _read_password_stdin()

    with _resolve_and_open() as conn:
        _ensure_migrated(conn)

        # Phase 18: no Session caller yet (Phase 19+ wires login). Audit
        # actor is the OS user as a stop-gap; Phase 22 admin ops will
        # thread session.user_id once login lands.
        os_user = pwd.getpwuid(os.getuid()).pw_name

        try:
            user = insert_user(
                conn,
                user_id,
                password,
                actor_role=actor_role,  # type: ignore[arg-type]
                params=PRODUCTION_PARAMS,
                audit_actor=os_user,
            )
        except (ValueError, UserAlreadyExistsError) as exc:
            typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(code=2) from exc

        if json_out:
            typer.echo(
                json.dumps(
                    {
                        "user_id": user.user_id,
                        "actor_role": user.actor_role,
                        "disabled": user.disabled,
                        "created_at": user.created_at.isoformat(),
                    }
                )
            )
        else:
            typer.echo(f"user created: user_id={user.user_id!r} role={user.actor_role}")


# ---------------------------------------------------------------------------
# `mindsos server user list`
# ---------------------------------------------------------------------------


@user_app.command(name="list")
def user_list(
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """
    List all users. NEVER emits ``password_hash`` per PB-24.

    Sorted by ``user_id`` ascending.
    """
    with _resolve_and_open() as conn:
        _ensure_migrated(conn)
        users = list_users(conn)

    if json_out:
        typer.echo(
            json.dumps(
                {
                    "count": len(users),
                    "users": [
                        {
                            "user_id": u.user_id,
                            "actor_role": u.actor_role,
                            "disabled": u.disabled,
                            "created_at": u.created_at.isoformat(),
                        }
                        for u in users
                    ],
                },
                indent=2,
            )
        )
        return

    typer.echo(f"count={len(users)}")
    for u in users:
        disabled_marker = " [DISABLED]" if u.disabled else ""
        typer.echo(
            f"  {u.user_id}  role={u.actor_role}  "
            f"created_at={u.created_at.isoformat()}{disabled_marker}"
        )


# ---------------------------------------------------------------------------
# `mindsos server user verify`  (PB-36 diagnostic)
# ---------------------------------------------------------------------------


@user_app.command(name="verify")
def user_verify(
    user_id: str = typer.Argument(..., help="User to verify."),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """
    Diagnostic credential check per PB-36.

    Reads password from stdin (PB-8). Exits 0 on success; exits 1 with
    opaque "auth failed" stderr message on any failure (PB-23 — public
    message uniform across UNKNOWN_USER / BAD_PASSWORD / DISABLED).

    Use case: smoke test post-bootstrap that the admin password
    roundtrips. NOT the primary login path — that ships at Phase 19 as
    ``mindsos server login`` returning a token.
    """
    password = _read_password_stdin()

    with _resolve_and_open() as conn:
        _ensure_migrated(conn)
        try:
            user = verify(conn, user_id, password, params=PRODUCTION_PARAMS)
        except AuthFailedError as exc:
            # PB-23: opaque public message; cause stays internal.
            if json_out:
                typer.echo(json.dumps({"status": "failed", "message": str(exc)}))
            else:
                typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(code=1) from exc
        except ValueError as exc:
            # Charset violation — caller programming error per users.py.
            typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(code=2) from exc

        if json_out:
            typer.echo(
                json.dumps(
                    {
                        "status": "ok",
                        "user_id": user.user_id,
                        "actor_role": user.actor_role,
                    }
                )
            )
        else:
            typer.echo(f"ok: user_id={user.user_id!r} role={user.actor_role}")


# ---------------------------------------------------------------------------
# `mindsos server login`  (Phase 19 PB-5 + PB-6)
# ---------------------------------------------------------------------------


@server_app.command(name="login")
def login_cmd(
    user_id: str = typer.Argument(..., help="User to authenticate."),
    print_token: bool = typer.Option(
        False,
        "--print-token",
        help="Emit the plaintext token to stdout (for shell capture).",
    ),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """
    Authenticate and issue a session per Phase 19 + ADR-0003.

    Reads password from stdin per PB-8 (no ``--password`` flag). Writes
    the plaintext token to ``~/.mindsos/token`` mode 0600 by default
    per Phase 19 PB-5; ``--print-token`` ALSO emits to stdout for
    ``TOKEN=$(mindsos server login ...)`` shell pipelines.

    Exit codes:
    * 0 — login succeeded; token file written.
    * 1 — login refused (AuthFailedError opaque public message,
      or AlreadyLoggedInError 2-field payload per PB-3).
    * 2 — caller error (charset violation on user_id, etc.).
    """
    password = _read_password_stdin()

    with _resolve_and_open() as conn:
        _ensure_migrated(conn)
        try:
            result = login(
                conn,
                user_id,
                password,
                ttl=PRODUCTION_TTL,
                params=PRODUCTION_PARAMS,
            )
        except AuthFailedError as exc:
            if json_out:
                typer.echo(
                    json.dumps({"status": "failed", "message": str(exc)})
                )
            else:
                typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(code=1) from exc
        except AlreadyLoggedInError as exc:
            if json_out:
                typer.echo(
                    json.dumps(
                        {
                            "status": "already_logged_in",
                            "existing_session_id": exc.existing_session_id,
                            "created_at": exc.created_at,
                        }
                    )
                )
            else:
                typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(code=1) from exc
        except ValueError as exc:
            typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(code=2) from exc

    # Persist the token to disk per PB-5 (file 0600 default).
    token_path = write_token(result.token)

    if json_out:
        # --json: include the token in the payload so the caller can pipe.
        typer.echo(
            json.dumps(
                {
                    "status": "ok",
                    "user_id": result.session.user_id,
                    "actor_role": result.session.actor_role,
                    "session_id": result.session.session_id,
                    "capabilities": sorted(result.session.capabilities),
                    "created_at": result.created_at.isoformat(),
                    "expires_at": result.expires_at.isoformat(),
                    "token_file": str(token_path),
                    "token": result.token,
                }
            )
        )
        return

    # Plain mode: confirmation to stderr; token to stdout only if
    # --print-token requested (PB-5 minor lock).
    typer.echo(
        f"logged in as {result.session.user_id!r} (role={result.session.actor_role}); "
        f"token written to {token_path}",
        err=True,
    )
    if print_token:
        typer.echo(result.token)


# ---------------------------------------------------------------------------
# `mindsos server whoami`  (Phase 19 PB-5 + minor lock --json shape)
# ---------------------------------------------------------------------------


@server_app.command(name="whoami")
def whoami_cmd(
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """
    Print the currently-logged-in identity.

    Resolves the token per the env > file > absent chain
    (:mod:`mindsos_server._token_storage`); calls
    :func:`mindsos_server.sessions.session_from_token`; emits identity
    + capabilities + computed expires_at.

    Exit shape per Phase 19 PB-5 minor lock:
    * Plain mode: logged-in → exit 0 + identity; not-logged-in → exit 1
      + stderr "not logged in".
    * ``--json`` mode: always exit 0 + structured payload
      (``{"logged_in": false}`` or full object). Pipe-friendly.
    """
    token = read_token()

    if token is None:
        if json_out:
            typer.echo(
                json.dumps(
                    {
                        "logged_in": False,
                        "token_source": token_source_description(),
                    }
                )
            )
            return
        typer.echo("not logged in", err=True)
        raise typer.Exit(code=1)

    with _resolve_and_open() as conn:
        _ensure_migrated(conn)
        try:
            session = session_from_token(conn, token, ttl=PRODUCTION_TTL)
        except InvalidSessionError as exc:
            # Token resolved from env/file but server rejected it.
            # In plain mode this is also "not logged in"; in --json
            # mode the cause goes into the payload for diagnostic use
            # (cause is NOT secret per Phase 18 PB-23 / Phase 19 PB-14
            # threat-model rationale — it's not exposed to remote
            # callers, only to the local CLI invocation that holds
            # the token).
            if json_out:
                typer.echo(
                    json.dumps(
                        {
                            "logged_in": False,
                            "token_source": token_source_description(),
                            "cause": exc.cause.value,
                        }
                    )
                )
                return
            typer.echo("not logged in", err=True)
            raise typer.Exit(code=1) from exc

    if json_out:
        typer.echo(
            json.dumps(
                {
                    "logged_in": True,
                    "user_id": session.user_id,
                    "actor_role": session.actor_role,
                    "session_id": session.session_id,
                    "capabilities": sorted(session.capabilities),
                    "token_source": token_source_description(),
                }
            )
        )
        return

    typer.echo(
        f"user_id={session.user_id!r} role={session.actor_role} "
        f"session_id={session.session_id!r}"
    )


# ---------------------------------------------------------------------------
# `mindsos server logout`  (Phase 19 PB-11)
# ---------------------------------------------------------------------------


@server_app.command(name="logout")
def logout_cmd(
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """
    Delete the current session (server-side) + the on-disk token file.

    Per Phase 19 PB-11 — self-logout is by-token. Per Phase 19 minor
    lock — invalid / expired / missing token is a silent no-op
    (exit 0; logout is idempotent by nature).

    The env-var ``MINDSOS_TOKEN`` (if set in the parent shell) is NOT
    cleared — a child process cannot unset env in its parent. Plain
    output instructs the user to ``unset MINDSOS_TOKEN`` if they had
    been using env-var auth.
    """
    token = read_token()
    server_deleted = False

    if token is not None:
        with _resolve_and_open() as conn:
            _ensure_migrated(conn)
            server_deleted = logout(conn, token)

    file_deleted = delete_token()

    if json_out:
        typer.echo(
            json.dumps(
                {
                    "status": "ok",
                    "server_session_deleted": server_deleted,
                    "token_file_deleted": file_deleted,
                    "had_env_var": bool(__import__("os").environ.get(TOKEN_ENV_VAR)),
                }
            )
        )
        return

    if server_deleted:
        typer.echo("logged out")
    else:
        typer.echo("not logged in (no-op)")

    if __import__("os").environ.get(TOKEN_ENV_VAR):
        typer.echo(
            f"note: {TOKEN_ENV_VAR} is still set in your shell; "
            f"run `unset {TOKEN_ENV_VAR}` to clear it.",
            err=True,
        )


# ---------------------------------------------------------------------------
# `mindsos server reset-admin` (Phase 20 PB-Z verb)
# ---------------------------------------------------------------------------


@server_app.command(name="reset-admin")
def reset_admin_cmd(
    user_id: str = typer.Argument(
        ...,
        help=(
            "Existing admin user_id to reset. REQUIRED — reset-admin "
            "is destructive; no interactive prompt fallback per PB-G."
        ),
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Emit JSON output to stdout."
    ),
) -> None:
    """
    Lock-out recovery for an existing admin per ADR-0012 §amendment-2.

    Rotates the target admin's password (fresh argon2id salt),
    re-enables the row if disabled, and kills every active session
    for that user in a single SQLite transaction (DELETE → UPDATE →
    audit → commit per PB-R).

    Pre-conditions:

    * Target user_id MUST exist (UserNotFoundError on missing per
      PB-A). To mint a new admin, use ``bootstrap`` (first admin) or
      ``admin promote-user`` (Phase 22, for subsequent admins).
    * Target MUST already be ``actor_role='admin'`` (NotAnAdminError
      otherwise per PB-E). Reset-admin will NEVER escalate a
      non-admin to admin — use ``admin promote-user`` (Phase 22).

    Authority model: reset-admin runs without a Session by definition
    (the operator is recovering from lock-out). Per ADR-0012
    §Rationale, filesystem access to ``server.db`` IS the authority
    floor — the operator's proof-of-authority is being able to run
    this CLI against the production DB file. The OS user (from
    ``pwd.getpwuid(os.getuid()).pw_name``) is recorded as the audit
    actor on the EVT_RESET_ADMIN row + every EVT_KILL_SESSION row.

    Password reading: stdin only (PB-G — no ``--password`` flag, same
    rule as Phase 18 PB-8). TTY: ``getpass`` prompt. Pipe: one line.

    Audit emitted (per PB-D + PB-U + PB-AA + PB-BB):

    * 1× ``EVT_RESET_ADMIN`` with
      ``extra = {"was_disabled": bool, "sessions_killed": N}``.
    * N× ``EVT_KILL_SESSION`` (one per killed session) with
      ``extra = {"session_id": sid, "context": "reset_admin"}``.
    * 1× ``EVT_ADMIN_ENABLE_USER`` IFF target was disabled, with
      ``extra = {"context": "reset_admin"}``.

    Exit codes:

    * 0 — reset succeeded.
    * 2 — UserNotFoundError / NotAnAdminError / ValueError on bad
      user_id; stderr carries the error message.
    """
    password = _read_password_stdin()

    # OS user as actor per ADR-0012 §Rationale (no Session in this path).
    os_user = pwd.getpwuid(os.getuid()).pw_name

    with _resolve_and_open() as conn:
        _ensure_migrated(conn)

        try:
            result = reset_admin(
                conn,
                user_id,
                password,
                os_user=os_user,
                params=PRODUCTION_PARAMS,
            )
        except (UserNotFoundError, NotAnAdminError, ValueError) as exc:
            typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(code=2) from exc

    if json_out:
        typer.echo(
            json.dumps(
                {
                    "status": "reset",
                    "user_id": result.user_id,
                    "sessions_killed": result.sessions_killed,
                    "was_disabled": result.was_disabled,
                }
            )
        )
    else:
        suffix = "; re-enabled=true" if result.was_disabled else ""
        typer.echo(
            f"admin reset: user_id={result.user_id!r}; "
            f"sessions_killed={result.sessions_killed}{suffix}"
        )


# ---------------------------------------------------------------------------
# `mindsos server query-audit`  (Phase 21 PB-23 verb)
# ---------------------------------------------------------------------------


def _format_audit_row_tsv(r: AuditRow) -> str:
    """
    PB-25 plain output: one row per line, tab-separated.

    Columns: ``id<TAB>ts<TAB>actor<TAB>event<TAB>target<TAB>extra_json_oneline``.
    Null ``actor`` / ``target`` rendered as ``-`` (single dash).
    ``extra`` is re-serialized to compact JSON via ``separators=(',', ':')``.
    """
    actor_str = r.actor if r.actor is not None else "-"
    target_str = r.target if r.target is not None else "-"
    extra_oneline = json.dumps(dict(r.extra), separators=(",", ":"))
    return f"{r.id}\t{r.ts}\t{actor_str}\t{r.event}\t{target_str}\t{extra_oneline}"


@server_app.command(name="query-audit")
def query_audit_cmd(
    actor: Optional[str] = typer.Option(
        None, "--actor", help="Filter audit_row.actor_user = X."
    ),
    event: Optional[str] = typer.Option(
        None,
        "--event",
        help=(
            "Filter audit_row.event = X (e.g. EVT_LOGIN, "
            "EVT_PERMISSION_DENIED, EVT_AUDIT_QUERY)."
        ),
    ),
    target: Optional[str] = typer.Option(
        None, "--target", help="Filter audit_row.target_user = X."
    ),
    since: Optional[str] = typer.Option(
        None,
        "--since",
        help=(
            "Inclusive lower bound (ts >= since); ISO-8601 with or "
            "without ms / Z (e.g. 2026-05-21T00:00:00Z)."
        ),
    ),
    until: Optional[str] = typer.Option(
        None,
        "--until",
        help=(
            "Inclusive upper bound (ts <= until); ISO-8601 same format "
            "as --since."
        ),
    ),
    after_id: Optional[int] = typer.Option(
        None,
        "--after-id",
        help=(
            "Cursor for stable pagination (id > after_id). Pair with "
            "--since / --until / --limit; combine AND-together (PB-20)."
        ),
    ),
    limit: int = typer.Option(
        100,
        "--limit",
        min=1,
        help=(
            "Max rows returned. Default 100; silently clamped to 10000."
        ),
    ),
    count_only: bool = typer.Option(
        False,
        "--count-only",
        help=(
            "Emit only the matching-row count (SELECT COUNT(*) form). "
            "Reframed 'audit stats' feature per PB-4."
        ),
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Emit JSON output to stdout."
    ),
) -> None:
    """
    Read rows from the audit log per ADR-0013 §amendment-2.

    Gated on ``CAN_VIEW_AUDIT_LOG`` (in ``ADMIN_CAPS`` only). Token is
    resolved from env > file via :func:`mindsos_server._token_storage.read_token`;
    session via :func:`mindsos_server.sessions.session_from_token`.
    Non-admin caller emits ``EVT_PERMISSION_DENIED`` audit row + exits
    3 (per PB-13). Bad ISO-8601 / invalid arg exits 2.

    Happy path always writes one ``EVT_AUDIT_QUERY`` audit row before
    returning (PB-16) — including ``--count-only`` invocations (PB-18).
    The ``EVT_AUDIT_QUERY.extra_json`` carries the sparse filters
    snapshot + result count + count_only flag per PB-17, letting
    operator-side audit-review reconstruct exactly what was queried.

    Output (default mode — list mode):

    * Plain: TSV one row per line; null actor/target → ``-``.
    * ``--json``: ``{"rows": [...], "count": N, "next_after_id": int | null}``
      where ``next_after_id`` is the last row's id IFF ``len(rows) >= limit``
      (page-end sentinel), else ``null``.

    Output (``--count-only`` mode):

    * Plain: ``count=N``.
    * ``--json``: ``{"count": N}``.

    Exit codes:

    * 0 — success.
    * 1 — not logged in (no token / invalid token).
    * 2 — ValueError on ISO-8601 parse / invalid arg.
    * 3 — PermissionDeniedError (caller lacks CAN_VIEW_AUDIT_LOG).
    """
    token = read_token()
    if token is None:
        typer.echo("not logged in", err=True)
        raise typer.Exit(code=1)

    with _resolve_and_open() as conn:
        _ensure_migrated(conn)
        try:
            session = session_from_token(conn, token, ttl=PRODUCTION_TTL)
        except InvalidSessionError as exc:
            typer.echo("not logged in", err=True)
            raise typer.Exit(code=1) from exc

        try:
            result = admin_query_audit(
                conn,
                session,
                actor=actor,
                event=event,
                target=target,
                since=since,
                until=until,
                after_id=after_id,
                limit=limit,
                count_only=count_only,
            )
        except PermissionDeniedError as exc:
            typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(code=3) from exc
        except ValueError as exc:
            typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(code=2) from exc

    # --count-only mode → int result.
    if count_only:
        assert isinstance(result, int)
        if json_out:
            typer.echo(json.dumps({"count": result}))
        else:
            typer.echo(f"count={result}")
        return

    # Default mode → list[AuditRow].
    assert isinstance(result, list)
    if json_out:
        # next_after_id sentinel per PB-24: null when fewer rows than limit
        # (last page); else the last row's id (cursor for the next page).
        next_after_id = result[-1].id if len(result) >= limit and result else None
        typer.echo(
            json.dumps(
                {
                    "rows": [
                        {
                            "id": r.id,
                            "ts": r.ts,
                            "actor": r.actor,
                            "event": r.event,
                            "target": r.target,
                            "extra": dict(r.extra),
                        }
                        for r in result
                    ],
                    "count": len(result),
                    "next_after_id": next_after_id,
                }
            )
        )
        return

    # Plain TSV per PB-25.
    for r in result:
        typer.echo(_format_audit_row_tsv(r))


# ---------------------------------------------------------------------------
# Wire user_app onto server_app + register_server_app for app.py
# ---------------------------------------------------------------------------

server_app.add_typer(user_app, name="user")


def register_server_app(parent: typer.Typer) -> None:
    """Wire the server sub-app onto a parent Typer app."""
    parent.add_typer(server_app, name="server")
