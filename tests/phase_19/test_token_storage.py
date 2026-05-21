"""
Phase 19 token storage tests per PB-5.

Verifies the env > file > absent resolution chain + file 0600 +
atomic-replace write + delete-on-logout.

Uses ``MINDSOS_TOKEN_FILE`` env override to redirect the storage path
into pytest's tmp_path (avoiding tests touching the user's real
``~/.mindsos/token``).
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from mindsos_server._token_storage import (
    TOKEN_ENV_VAR,
    TOKEN_FILE_ENV_VAR,
    delete_token,
    read_token,
    token_source_description,
    write_token,
)


@pytest.fixture()
def token_paths(tmp_path: Path, monkeypatch):
    """Redirect file storage into tmp; clear env var."""
    target = tmp_path / "token"
    monkeypatch.setenv(TOKEN_FILE_ENV_VAR, str(target))
    monkeypatch.delenv(TOKEN_ENV_VAR, raising=False)
    return target


class TestWriteAndRead:
    def test_round_trip(self, token_paths: Path) -> None:
        write_token("secret-256-bit")
        assert read_token() == "secret-256-bit"

    def test_file_mode_0600(self, token_paths: Path) -> None:
        write_token("secret")
        mode = stat.S_IMODE(os.stat(token_paths).st_mode)
        assert mode == 0o600

    def test_creates_parent_dir(self, tmp_path: Path, monkeypatch) -> None:
        nested = tmp_path / "newdir" / "token"
        monkeypatch.setenv(TOKEN_FILE_ENV_VAR, str(nested))
        monkeypatch.delenv(TOKEN_ENV_VAR, raising=False)
        write_token("s")
        assert nested.exists()
        # Parent dir is 0700.
        parent_mode = stat.S_IMODE(os.stat(nested.parent).st_mode)
        assert parent_mode == 0o700

    def test_overwrite(self, token_paths: Path) -> None:
        write_token("first")
        write_token("second")
        assert read_token() == "second"


class TestResolutionChain:
    """env > file > absent."""

    def test_env_wins_over_file(self, token_paths: Path, monkeypatch) -> None:
        write_token("file-token")
        monkeypatch.setenv(TOKEN_ENV_VAR, "env-token")
        assert read_token() == "env-token"

    def test_file_when_env_absent(self, token_paths: Path) -> None:
        write_token("file-token")
        assert read_token() == "file-token"

    def test_none_when_both_absent(self, token_paths: Path) -> None:
        assert read_token() is None

    def test_empty_env_falls_through_to_file(
        self, token_paths: Path, monkeypatch
    ) -> None:
        """Empty env value should NOT shadow the file (treated as absent)."""
        write_token("file-token")
        monkeypatch.setenv(TOKEN_ENV_VAR, "")
        assert read_token() == "file-token"

    def test_strip_trailing_whitespace(self, token_paths: Path) -> None:
        # write_token doesn't add a newline, but if a user echoed it
        # they would. Simulate that scenario directly.
        token_paths.parent.mkdir(parents=True, exist_ok=True)
        token_paths.write_text("token-with-newline\n", encoding="utf-8")
        os.chmod(token_paths, 0o600)
        assert read_token() == "token-with-newline"


class TestDelete:
    def test_delete_returns_true_when_file_existed(
        self, token_paths: Path
    ) -> None:
        write_token("t")
        assert delete_token() is True
        assert not token_paths.exists()

    def test_delete_returns_false_when_no_file(self, token_paths: Path) -> None:
        assert delete_token() is False

    def test_delete_does_not_clear_env(
        self, token_paths: Path, monkeypatch
    ) -> None:
        monkeypatch.setenv(TOKEN_ENV_VAR, "still-here")
        delete_token()
        assert os.environ[TOKEN_ENV_VAR] == "still-here"


class TestTokenSourceDescription:
    def test_env(self, token_paths: Path, monkeypatch) -> None:
        monkeypatch.setenv(TOKEN_ENV_VAR, "x")
        assert token_source_description() == "env"

    def test_file(self, token_paths: Path) -> None:
        write_token("x")
        desc = token_source_description()
        assert desc.startswith("file:")

    def test_none(self, token_paths: Path) -> None:
        assert token_source_description() == "none"
