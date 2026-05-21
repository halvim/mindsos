"""
Tests for ``mindsos server bootstrap`` CLI verb — Phase 18 PB-27 + PB-29.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mindsos_cli.app import app
from mindsos_server._db import open_db


@pytest.fixture()
def runner() -> CliRunner:
    # B-18-T2 — click 8.2 removed `mix_stderr` kwarg. See test_cli_server_user.py.
    return CliRunner()


@pytest.fixture()
def tmp_db_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "server.db"
    monkeypatch.setenv("MINDSOS_SERVER_DB", str(db_path))
    return db_path


class TestBootstrapHappyPath:
    """Fresh install: inserts admin + writes EVT_BOOTSTRAP."""

    def test_bootstrap_creates_admin(
        self, runner: CliRunner, tmp_db_env: Path
    ) -> None:
        result = runner.invoke(
            app, ["server", "bootstrap", "admin"], input="rootpw\n"
        )
        assert result.exit_code == 0, result.output
        assert "admin bootstrapped" in result.stdout

    def test_bootstrap_writes_evt_bootstrap_audit(
        self, runner: CliRunner, tmp_db_env: Path
    ) -> None:
        runner.invoke(
            app, ["server", "bootstrap", "admin"], input="rootpw\n"
        )
        # Inspect the DB directly.
        with open_db(tmp_db_env) as conn:
            rows = conn.execute(
                "SELECT event, target_user FROM audit WHERE event=?",
                ("EVT_BOOTSTRAP",),
            ).fetchall()
        assert len(rows) == 1
        assert rows[0] == ("EVT_BOOTSTRAP", "admin")


class TestBootstrapIdempotentPerPB29:
    """PB-29 — second bootstrap call is a no-op when an admin already exists."""

    def test_second_call_skips(
        self, runner: CliRunner, tmp_db_env: Path
    ) -> None:
        # First call creates admin.
        result = runner.invoke(
            app, ["server", "bootstrap", "admin"], input="rootpw\n"
        )
        assert result.exit_code == 0

        # Second call should skip — exit 0 with "admin already exists" message.
        result = runner.invoke(
            app, ["server", "bootstrap", "alice"], input="anotherpw\n"
        )
        assert result.exit_code == 0
        assert "already exists" in result.stdout

    def test_second_call_does_not_create_alice(
        self, runner: CliRunner, tmp_db_env: Path
    ) -> None:
        """Second call must NOT create the alice user."""
        runner.invoke(
            app, ["server", "bootstrap", "admin"], input="rootpw\n"
        )
        runner.invoke(
            app, ["server", "bootstrap", "alice"], input="anotherpw\n"
        )
        with open_db(tmp_db_env) as conn:
            rows = conn.execute(
                "SELECT user_id FROM users ORDER BY user_id"
            ).fetchall()
        assert [r[0] for r in rows] == ["admin"]

    def test_second_call_json_output(
        self, runner: CliRunner, tmp_db_env: Path
    ) -> None:
        runner.invoke(
            app, ["server", "bootstrap", "admin"], input="rootpw\n"
        )
        result = runner.invoke(
            app, ["server", "bootstrap", "alice", "--json"], input="anotherpw\n"
        )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["status"] == "skipped"
        assert payload["admin_count"] == 1
