"""
Token storage resolution for the CLI per Phase 19 PB-5.

Hybrid file + env-var resolution chain (mirrors Phase 18 PB-17
manifest-fallback pattern for ``server.db``): env > file > absent.
Industry convention from ``gh`` / ``kubectl`` / ``docker login`` —
env-var first lets scripts and CI work statelessly, file-default lets
interactive shells avoid re-exporting after login.

* **Resolution order on read:** ``MINDSOS_TOKEN`` env var if set and
  non-empty → ``~/.mindsos/token`` file contents if exists and readable
  → ``None``.
* **Write target:** ``~/.mindsos/token`` mode ``0600`` (owner-only
  read/write). The env-var is read-only from this module's perspective
  — operators set it via their shell profile or CI config; the CLI
  never writes it. The file path can be overridden via
  ``MINDSOS_TOKEN_FILE`` env (parallel escape hatch to
  ``MINDSOS_SERVER_DB`` from Phase 18 PB-17).
* **Delete on logout:** the file (if it exists) is unlinked. The env
  var is NOT cleared (the CLI can't unset env vars in the parent
  shell); the user is informed via CLI output that they should
  ``unset MINDSOS_TOKEN`` if they were using env-var auth.

Per Phase 19 PB-5 §minor-locks: no ``--token`` CLI flag. The auth
material must come from one of the two configured sources; passing on
argv would leak into shell history.

Per Phase 19 sessions.py §security: this module does NOT hash tokens —
it stores/reads/deletes the plaintext token string. Hashing happens at
the sessions.py boundary (``hashlib.sha256``) when the token enters
SQLite lookup. The on-disk file IS plaintext at mode 0600 — the
filesystem permission IS the protection, not at-rest encryption.
A hostile root user on the same machine can read the token regardless
of any in-process protection; this is the accepted threat model for
local-first.
"""

from __future__ import annotations

import os
from pathlib import Path


#: Env-var carrying the token (read-only from CLI perspective).
TOKEN_ENV_VAR = "MINDSOS_TOKEN"

#: Env-var overriding the file location. Defaults to
#: ``~/.mindsos/token`` per Phase 19 PB-5 (parallels Phase 18 PB-17's
#: ``MINDSOS_SERVER_DB`` env override of ``~/.mindsos/server.db``).
TOKEN_FILE_ENV_VAR = "MINDSOS_TOKEN_FILE"

#: Default token file path (resolved relative to ``$HOME``).
_DEFAULT_TOKEN_FILE_REL = ".mindsos/token"


def _resolve_file_path() -> Path:
    """
    Return the token file path. Honors ``MINDSOS_TOKEN_FILE`` env
    override; falls back to ``~/.mindsos/token``.

    Returns a :class:`Path` — the file may not exist yet. Callers that
    need existence use :meth:`Path.exists`.
    """
    override = os.environ.get(TOKEN_FILE_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path.home() / _DEFAULT_TOKEN_FILE_REL


def read_token() -> str | None:
    """
    Resolve the current token per the env > file > absent chain.

    Returns:
        The plaintext token string if found via env or file; ``None``
        otherwise. Trailing whitespace is stripped (file writes from
        ``echo`` often add a newline).
    """
    env_token = os.environ.get(TOKEN_ENV_VAR)
    if env_token:
        # Non-empty env value wins.
        return env_token.strip() or None

    file_path = _resolve_file_path()
    if not file_path.exists():
        return None

    try:
        contents = file_path.read_text(encoding="utf-8").strip()
    except OSError:
        # Permission error / device error / etc. — treat as absent.
        return None

    return contents or None


def write_token(token: str) -> Path:
    """
    Write the plaintext token to ``~/.mindsos/token`` (or env override)
    with mode ``0600``.

    Creates the parent directory if missing (also mode ``0700``).
    Atomic-replace pattern: write to a sibling temp file with mode
    ``0600`` then rename — guarantees the final file is never visible
    with a more-permissive mode on the path between create and
    final-mode-set.

    Returns:
        The :class:`Path` of the written file (for CLI confirmation
        messages — Phase 19 PB-5 minor lock: confirmation goes to
        stderr by default).
    """
    file_path = _resolve_file_path()
    file_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    # Atomic-replace pattern: tempfile in the same directory + rename.
    # opener forces 0600 from the moment the file exists on disk.
    tmp_path = file_path.parent / (file_path.name + ".tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(str(tmp_path), flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            fp.write(token)
            # No trailing newline — read_token's strip() handles either
            # case but we keep the on-disk shape minimal.
    except Exception:
        # Clean up the temp on any error before re-raising.
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise

    os.replace(str(tmp_path), str(file_path))
    return file_path


def delete_token() -> bool:
    """
    Delete the token file if it exists.

    Returns:
        True if a file was actually deleted; False if no file existed.
        The env-var (if set) is NOT cleared — the CLI can't unset env
        vars in the parent shell; logout output instructs the user to
        ``unset MINDSOS_TOKEN`` if they had been using env-var auth.
    """
    file_path = _resolve_file_path()
    if not file_path.exists():
        return False
    try:
        file_path.unlink()
        return True
    except OSError:
        # Permission error during unlink is rare on a 0600 file the
        # user owns; surface as False rather than raising — the
        # session-server-side deletion already succeeded by the time
        # this is called.
        return False


def token_source_description() -> str:
    """
    Diagnostic helper for CLI ``whoami`` output. Returns a short string
    describing where the token came from: ``"env"``, ``"file:<path>"``,
    or ``"none"``. Used for the ``--json`` payload and the human-readable
    plain output.
    """
    if os.environ.get(TOKEN_ENV_VAR):
        return "env"
    file_path = _resolve_file_path()
    if file_path.exists():
        return f"file:{file_path}"
    return "none"
