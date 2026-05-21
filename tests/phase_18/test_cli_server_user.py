"""
Tests for ``mindsos_cli/commands/server.py`` — Phase 18 PB-8 + PB-10 +
PB-32 + PB-36.

CLI tests use Typer's ``CliRunner`` + a tmp DB path passed via the
``MINDSOS_SERVER_DB`` env var.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mindsos_cli.app import app


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner(mix_stderr=False)


@pytest.fixture()
def tmp_db_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the CLI at a tmp server.db via env var per PB-17."""
    db_path = tmp_path / "server.db"
    monkeypatch.setenv("MINDSOS_SERVER_DB", str(db_path))
    return db_path


class TestCliShape:
    """PB-10 — verb group at `mindsos server user {create,list,verify}`."""

    def test_server_help_lists_subgroups(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["server", "--help"])
        assert result.exit_code == 0
        assert "user" in result.stdout
        assert "bootstrap" in result.stdout

    def test_server_user_help_lists_verbs(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["server", "user", "--help"])
        assert result.exit_code == 0
        assert "create" in result.stdout
        assert "list" in result.stdout
        assert "verify" in result.stdout


class TestNoPasswordFlagPerPB8:
    """PB-8 — `--password` flag NEVER declared; only stdin."""

    def test_user_create_rejects_password_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(
            app, ["server", "user", "create", "alice", "--password", "leak"]
        )
        # Typer surfaces unknown options as exit 2.
        assert result.exit_code == 2

    def test_user_verify_rejects_password_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(
            app, ["server", "user", "verify", "alice", "--password", "leak"]
        )
        assert result.exit_code == 2

    def test_bootstrap_rejects_password_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(
            app, ["server", "bootstrap", "admin", "--password", "leak"]
        )
        assert result.exit_code == 2


class TestUserCreateListRoundtrip:
    """create + list roundtrip via CLI."""

    def test_create_then_list(self, runner: CliRunner, tmp_db_env: Path) -> None:
        # Create
        result = runner.invoke(
            app,
            ["server", "user", "create", "alice"],
            input="hunter2\n",
        )
        assert result.exit_code == 0, result.stderr
        assert "alice" in result.stdout

        # List
        result = runner.invoke(app, ["server", "user", "list"])
        assert result.exit_code == 0
        assert "alice" in result.stdout

    def test_list_json_no_password_hash(
        self, runner: CliRunner, tmp_db_env: Path
    ) -> None:
        """PB-24 — list --json never includes password_hash."""
        runner.invoke(
            app, ["server", "user", "create", "alice"], input="secret-pw\n"
        )
        result = runner.invoke(app, ["server", "user", "list", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["count"] == 1
        user = payload["users"][0]
        assert "password_hash" not in user
        assert "secret-pw" not in result.stdout


class TestUserVerifyDiagnostic:
    """PB-36 — verify CLI exists; PB-23 — opaque error message."""

    def test_verify_ok(self, runner: CliRunner, tmp_db_env: Path) -> None:
        runner.invoke(
            app, ["server", "user", "create", "alice"], input="hunter2\n"
        )
        result = runner.invoke(
            app, ["server", "user", "verify", "alice"], input="hunter2\n"
        )
        assert result.exit_code == 0
        assert "ok" in result.stdout

    def test_verify_bad_password_opaque(
        self, runner: CliRunner, tmp_db_env: Path
    ) -> None:
        """PB-23 — opaque 'auth failed' message; no cause leak to stderr."""
        runner.invoke(
            app, ["server", "user", "create", "alice"], input="correct\n"
        )
        result = runner.invoke(
            app, ["server", "user", "verify", "alice"], input="wrong\n"
        )
        assert result.exit_code == 1
        assert "auth failed" in result.stderr
        # PB-23 — cause MUST NOT leak in stderr.
        assert "BAD_PASSWORD" not in result.stderr
        assert "UNKNOWN_USER" not in result.stderr

    def test_verify_unknown_user_opaque(
        self, runner: CliRunner, tmp_db_env: Path
    ) -> None:
        result = runner.invoke(
            app, ["server", "user", "verify", "nobody"], input="any\n"
        )
        assert result.exit_code == 1
        assert "auth failed" in result.stderr
        assert "UNKNOWN_USER" not in result.stderr
