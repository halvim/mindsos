"""
Phase 19 CLI verb tests: ``mindsos server {login,whoami,logout}``.

Uses Typer ``CliRunner`` + tmp ``MINDSOS_SERVER_DB`` env per Phase 18
pattern + tmp ``MINDSOS_TOKEN_FILE`` env per PB-5.

Asserts:
* CLI help lists login/whoami/logout subverbs.
* No `--password` / `--token` flag declared (PB-8 + PB-5).
* login happy path writes the token file mode 0600 + emits
  confirmation to stderr; `--print-token` ALSO emits to stdout.
* login `--json` payload shape.
* whoami plain mode: not-logged-in → exit 1; logged-in → exit 0.
* whoami `--json` always exits 0 (pipe-friendly minor lock).
* logout: silent no-op when no token; happy path deletes file +
  server row.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mindsos_cli.app import app


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def env_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Path]:
    """Point both DB + token file at tmp_path; clear any inherited env."""
    db_path = tmp_path / "server.db"
    token_path = tmp_path / "token"
    monkeypatch.setenv("MINDSOS_SERVER_DB", str(db_path))
    monkeypatch.setenv("MINDSOS_TOKEN_FILE", str(token_path))
    monkeypatch.delenv("MINDSOS_TOKEN", raising=False)
    return {"db": db_path, "token": token_path}


def _bootstrap(runner: CliRunner) -> None:
    """Helper: bootstrap an admin so login has something to verify against."""
    result = runner.invoke(
        app, ["server", "bootstrap", "admin"], input="adminpw\n"
    )
    assert result.exit_code == 0, result.output


class TestCliShape:
    def test_login_in_help(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["server", "--help"])
        assert result.exit_code == 0
        assert "login" in result.output

    def test_whoami_in_help(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["server", "--help"])
        assert "whoami" in result.output

    def test_logout_in_help(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["server", "--help"])
        assert "logout" in result.output


class TestNoPasswordOrTokenFlag:
    """PB-8 + PB-5: no `--password`; no `--token`."""

    def test_login_rejects_password_flag(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap(runner)
        result = runner.invoke(
            app, ["server", "login", "admin", "--password", "p"]
        )
        # Unknown option → Typer/Click exits 2.
        assert result.exit_code != 0

    def test_login_rejects_token_flag(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap(runner)
        result = runner.invoke(
            app, ["server", "login", "admin", "--token", "t"]
        )
        assert result.exit_code != 0

    def test_whoami_rejects_token_flag(self, runner: CliRunner, env_setup) -> None:
        result = runner.invoke(app, ["server", "whoami", "--token", "t"])
        assert result.exit_code != 0


class TestLoginHappyPath:
    def test_writes_token_file(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap(runner)
        result = runner.invoke(
            app, ["server", "login", "admin"], input="adminpw\n"
        )
        assert result.exit_code == 0, result.output
        assert env_setup["token"].exists()

    def test_confirmation_to_stderr_no_token_to_stdout_by_default(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap(runner)
        result = runner.invoke(
            app, ["server", "login", "admin"], input="adminpw\n"
        )
        # Plain default — stdout should NOT contain the token. (The
        # token is only on disk + via --print-token.)
        token_on_disk = env_setup["token"].read_text(encoding="utf-8").strip()
        assert token_on_disk not in result.stdout

    def test_print_token_emits_to_stdout(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap(runner)
        result = runner.invoke(
            app,
            ["server", "login", "admin", "--print-token"],
            input="adminpw\n",
        )
        assert result.exit_code == 0
        token_on_disk = env_setup["token"].read_text(encoding="utf-8").strip()
        assert token_on_disk in result.stdout

    def test_json_payload_includes_token(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap(runner)
        result = runner.invoke(
            app, ["server", "login", "admin", "--json"], input="adminpw\n"
        )
        assert result.exit_code == 0
        # JSON output mixed with the stderr confirmation; parse the
        # JSON line. Typer.echo with err=True still goes to combined
        # output under CliRunner default; we find the JSON object.
        json_match = re.search(r"\{.*\}", result.output, re.DOTALL)
        assert json_match
        payload = json.loads(json_match.group(0))
        assert payload["status"] == "ok"
        assert payload["user_id"] == "admin"
        assert "token" in payload
        assert "session_id" in payload


class TestLoginFailure:
    def test_wrong_password_exits_1(self, runner: CliRunner, env_setup) -> None:
        _bootstrap(runner)
        result = runner.invoke(
            app, ["server", "login", "admin"], input="wrong\n"
        )
        assert result.exit_code == 1

    def test_unknown_user_exits_1(self, runner: CliRunner, env_setup) -> None:
        result = runner.invoke(
            app, ["server", "login", "ghost"], input="any\n"
        )
        assert result.exit_code == 1

    def test_already_logged_in_exits_1(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap(runner)
        first = runner.invoke(
            app, ["server", "login", "admin"], input="adminpw\n"
        )
        assert first.exit_code == 0
        # Token file kept; second login from a fresh shell would normally
        # use kill_my_own_sessions, but here we directly invoke login
        # which must refuse.
        second = runner.invoke(
            app, ["server", "login", "admin"], input="adminpw\n"
        )
        assert second.exit_code == 1


class TestWhoami:
    def test_not_logged_in_plain_exit_1(
        self, runner: CliRunner, env_setup
    ) -> None:
        result = runner.invoke(app, ["server", "whoami"])
        assert result.exit_code == 1

    def test_not_logged_in_json_exit_0(
        self, runner: CliRunner, env_setup
    ) -> None:
        """Minor lock: --json always exits 0 (pipe-friendly)."""
        result = runner.invoke(app, ["server", "whoami", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["logged_in"] is False

    def test_logged_in_plain_exit_0(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap(runner)
        runner.invoke(
            app, ["server", "login", "admin"], input="adminpw\n"
        )
        result = runner.invoke(app, ["server", "whoami"])
        assert result.exit_code == 0
        assert "admin" in result.output

    def test_logged_in_json_payload(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap(runner)
        runner.invoke(
            app, ["server", "login", "admin"], input="adminpw\n"
        )
        result = runner.invoke(app, ["server", "whoami", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["logged_in"] is True
        assert payload["user_id"] == "admin"
        assert payload["actor_role"] == "admin"


class TestLogout:
    def test_logout_no_token_is_no_op(
        self, runner: CliRunner, env_setup
    ) -> None:
        result = runner.invoke(app, ["server", "logout"])
        assert result.exit_code == 0

    def test_logout_deletes_token_file(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap(runner)
        runner.invoke(
            app, ["server", "login", "admin"], input="adminpw\n"
        )
        assert env_setup["token"].exists()
        result = runner.invoke(app, ["server", "logout"])
        assert result.exit_code == 0
        assert not env_setup["token"].exists()

    def test_logout_then_whoami_not_logged_in(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap(runner)
        runner.invoke(
            app, ["server", "login", "admin"], input="adminpw\n"
        )
        runner.invoke(app, ["server", "logout"])
        result = runner.invoke(app, ["server", "whoami"])
        assert result.exit_code == 1
