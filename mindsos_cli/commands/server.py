"""
CLI verbs for the Server Layer (Phase 18).

Per Phase 18 PB-32 — verbs live here at ``mindsos_cli/commands/server.py``
following the existing convention (admin.py, graph.py, etc.). Adds
``mindsos_cli → mindsos_server`` dep edge in pyproject per PB-25.

Verb groups:

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

Per PB-29 — bootstrap idempotency lives at THIS CLI verb (not in the
helper). The helper :func:`mindsos_server.users._insert_first_admin`
is a pure insert; this CLI does the ``count_admins() ≥ 1`` skip check.

Per PB-17 — DB path resolution chain: env > manifest > default. The CLI
uses :func:`mindsos_server._db.resolve_db_path` (env + default only;
manifest fallback is wired here if/when ``mindsos_cli/manifest.toml``
grows a ``[server] db_path`` field).
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
from mindsos_server.errors import AuthFailedError, UserAlreadyExistsError
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
# Wire user_app onto server_app + register_server_app for app.py
# ---------------------------------------------------------------------------

server_app.add_typer(user_app, name="user")


def register_server_app(parent: typer.Typer) -> None:
    """Wire the server sub-app onto a parent Typer app."""
    parent.add_typer(server_app, name="server")
