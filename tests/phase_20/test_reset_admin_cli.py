"""
Phase 20 CLI verb: ``mindsos server reset-admin <user_id>``.

Asserts:
* Verb appears in help.
* No `--password` flag declared (PB-G — mirrors PB-8).
* user_id is POSITIONAL + REQUIRED (PB-G — no interactive prompt
  fallback; missing arg → exit 2 from Typer).
* Happy path: rotates password + commits; plain + --json output shapes.
* UserNotFoundError + NotAnAdminError → exit 2 + stderr.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mindsos_cli.app import app


@pytest.fixture()
def runner() -> CliRunner:
    # B-18-T2 — Click 8.2 removed the `mix_stderr` kwarg; CliRunner
    # now mixes stderr into stdout/output. Tests against stderr-only
    # content assert against result.output (which contains both).
    return CliRunner()


@pytest.fixture()
def env_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Path]:
    """
    Point the CLI at a tmp ``server.db``; clear any inherited token env.
    Per Phase 18 _argon2 module convention there is no env-driven fast
    mode (PRODUCTION_PARAMS is what the CLI uses); Phase 19 CLI tests
    pay the same ~100ms-per-hash cost. Phase 20 mirrors.
    """
    db_path = tmp_path / "server.db"
    monkeypatch.setenv("MINDSOS_SERVER_DB", str(db_path))
    monkeypatch.delenv("MINDSOS_TOKEN", raising=False)
    return {"db": db_path}


def _bootstrap(runner: CliRunner) -> None:
    """Helper: bootstrap an admin so reset-admin has a target."""
    result = runner.invoke(
        app, ["server", "bootstrap", "admin"], input="adminpw\n"
    )
    assert result.exit_code == 0, result.output


def _create_user(runner: CliRunner, user_id: str, password: str) -> None:
    """Helper: create a non-admin user via user-create CLI."""
    result = runner.invoke(
        app, ["server", "user", "create", user_id], input=f"{password}\n"
    )
    assert result.exit_code == 0, result.output


class TestCliShape:
    def test_reset_admin_in_help(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["server", "--help"])
        assert result.exit_code == 0
        assert "reset-admin" in result.output

    def test_user_id_is_positional_required(self, runner: CliRunner) -> None:
        # No user_id argument → Typer exits 2 (missing required argument).
        # PB-G — destructive verb has no interactive prompt fallback.
        result = runner.invoke(app, ["server", "reset-admin"])
        assert result.exit_code != 0


class TestNoPasswordFlag:
    """PB-G — mirrors PB-8's no-`--password` rule for bootstrap/user-create."""

    def test_rejects_password_flag(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap(runner)
        result = runner.invoke(
            app, ["server", "reset-admin", "admin", "--password", "p"]
        )
        assert result.exit_code != 0


class TestHappyPath:
    def test_plain_output_shape(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap(runner)
        result = runner.invoke(
            app, ["server", "reset-admin", "admin"], input="newpw\n"
        )
        assert result.exit_code == 0, result.output
        assert "admin reset" in result.output
        assert "'admin'" in result.output
        assert "sessions_killed=0" in result.output

    def test_json_output_shape(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap(runner)
        result = runner.invoke(
            app,
            ["server", "reset-admin", "admin", "--json"],
            input="newpw\n",
        )
        assert result.exit_code == 0, result.output
        # PB-BB JSON shape.
        decoded = json.loads(result.output)
        assert decoded == {
            "status": "reset",
            "user_id": "admin",
            "sessions_killed": 0,
            "was_disabled": False,
        }


class TestFailurePaths:
    def test_user_not_found_exits_2(
        self, runner: CliRunner, env_setup
    ) -> None:
        result = runner.invoke(
            app, ["server", "reset-admin", "ghost"], input="newpw\n"
        )
        assert result.exit_code == 2
        assert "ghost" in result.output
        assert "error:" in result.output

    def test_not_an_admin_exits_2(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap(runner)
        _create_user(runner, "alice", "alicepw")
        result = runner.invoke(
            app, ["server", "reset-admin", "alice"], input="newpw\n"
        )
        assert result.exit_code == 2
        assert "alice" in result.output
        # NotAnAdminError message surfaces the actual_role per PB-N.
        assert "user" in result.output or "not an admin" in result.output
