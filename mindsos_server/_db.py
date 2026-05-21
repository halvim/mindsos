"""
SQLite connection helpers for ``server.db``.

Phase 18 PB-19 — every connection sets:

* ``PRAGMA journal_mode=WAL`` — concurrent reads + single writer; fits
  the dev workflow where docker test container + host CLI may both
  touch the DB.
* ``PRAGMA foreign_keys=ON`` — SQLite default is OFF; we want FK
  enforcement even though Phase 18 has no FKs yet (forward-looking;
  Phase 19 ``sessions.user_id`` referencing ``users.user_id`` will rely
  on this).
* ``PRAGMA busy_timeout=5000`` — 5-second wait on writer contention
  before raising; avoids spurious ``SQLITE_BUSY`` errors in the dev
  test cycle.

Per PB-19 — no connection pool; per-call short-lived connections via
the :func:`open_db` context manager. v1 scale (single-user local
install) doesn't justify pooling complexity.

Phase 18 PB-17 — DB path resolution:

1. ``MINDSOS_SERVER_DB`` env var (override).
2. ``[server] db_path`` field in CLI manifest (fallback).
3. ``~/.mindsos/server.db`` (hard-coded last resort).

Matches Phase 07 B-07-T2 env-driven config + manifest fallback pattern
per ``feedback_cli_config_manifest_fallback.md``.
"""

from __future__ import annotations

import contextlib
import os
import sqlite3
from pathlib import Path
from typing import Iterator

#: Hard-coded default DB path. Last-resort per PB-17.
_DEFAULT_DB_PATH = Path.home() / ".mindsos" / "server.db"

#: Env var name for path override per PB-17.
_DB_PATH_ENV_VAR = "MINDSOS_SERVER_DB"


def resolve_db_path(manifest_path: str | None = None) -> Path:
    """
    Resolve the path to ``server.db`` per the PB-17 precedence chain:

    1. ``MINDSOS_SERVER_DB`` env var (highest).
    2. ``manifest_path`` argument (CLI manifest ``[server] db_path``
       value, if set).
    3. ``~/.mindsos/server.db`` (last resort).

    Returns the resolved :class:`Path`. Does NOT create parent dirs;
    :func:`open_db` handles that.
    """
    env_value = os.environ.get(_DB_PATH_ENV_VAR)
    if env_value:
        return Path(env_value).expanduser()

    if manifest_path:
        return Path(manifest_path).expanduser()

    return _DEFAULT_DB_PATH


@contextlib.contextmanager
def open_db(db_path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    """
    Open a SQLite connection to ``server.db`` with Phase 18 PB-19 pragmas.

    Yields the connection; closes on exit. Caller commits/rollbacks
    inside the ``with`` block as needed (the helper does NOT
    auto-commit on exit — that would mask test failures).

    If ``db_path`` is None, resolves via :func:`resolve_db_path` with
    no manifest fallback (env or default only). CLI callers SHOULD
    pre-resolve via :func:`resolve_db_path` themselves so manifest
    fallback applies; this helper is also used in tests where
    ``db_path`` is typically a tmpdir path passed explicitly.

    Parent directory is created if missing (e.g. fresh install with
    no ``~/.mindsos/`` yet).

    Pragmas applied per Phase 18 PB-19:

    * ``journal_mode = WAL``
    * ``foreign_keys = ON``
    * ``busy_timeout = 5000``
    """
    resolved = Path(db_path) if db_path is not None else resolve_db_path()
    resolved.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        str(resolved),
        # isolation_level=None would put us in autocommit; we want
        # explicit commit() boundaries (see write_audit / insert_user).
        isolation_level="DEFERRED",
    )
    try:
        # Pragma order per PB-19. WAL mode setter returns a row; the
        # other two are statement-only.
        conn.execute("PRAGMA journal_mode = WAL").fetchone()
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        yield conn
    finally:
        conn.close()
