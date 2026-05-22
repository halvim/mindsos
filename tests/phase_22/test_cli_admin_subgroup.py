"""
Phase 22 — CLI ``mindsos server admin <verb>`` subgroup.

Asserts:

* Subgroup is wired under ``server`` (R1 PB-2).
* All six verbs (promote-user, demote-user, disable-user, enable-user,
  kill-session, hard-delete-user) appear in ``server admin --help``.
* Each verb is REQUIRED-positional, no prompt (R4 PB-26).
* Exit-code mapping per R5 PB-27:
  - 0 success
  - 1 not logged in
  - 2 UserNotFoundError / NotAnAdminError / ValueError
  - 3 PermissionDeniedError
  - 4 LastAdminError
  - 5 AlreadyAnAdminError
  - 6 SessionNotFoundError
* Each verb supports --json (R3 PB-20).
"""

from __future__ import annotations

import json
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
    db_path = tmp_path / "server.db"
    monkeypatch.setenv("MINDSOS_SERVER_DB", str(db_path))
    monkeypatch.delenv("MINDSOS_TOKEN", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    return {"db": db_path, "home": tmp_path}


def _bootstrap_and_login(
    runner: CliRunner, user_id: str = "admin", password: str = "adminpw"
) -> None:
    r = runner.invoke(
        app, ["server", "bootstrap", user_id], input=f"{password}\n"
    )
    assert r.exit_code == 0, r.output
    r = runner.invoke(
        app, ["server", "login", user_id], input=f"{password}\n"
    )
    assert r.exit_code == 0, r.output


def _create_user(
    runner: CliRunner, user_id: str = "alice", password: str = "alicepw",
    role: str = "user",
) -> None:
    r = runner.invoke(
        app, ["server", "user", "create", user_id, "--role", role],
        input=f"{password}\n",
    )
    assert r.exit_code == 0, r.output


class TestSubgroupWiring:
    def test_admin_subgroup_in_server_help(self, runner: CliRunner) -> None:
        r = runner.invoke(app, ["server", "--help"])
        assert r.exit_code == 0
        assert "admin" in r.output

    def test_all_six_verbs_listed(self, runner: CliRunner) -> None:
        r = runner.invoke(app, ["server", "admin", "--help"])
        assert r.exit_code == 0
        for verb in (
            "promote-user",
            "demote-user",
            "disable-user",
            "enable-user",
            "kill-session",
            "hard-delete-user",
        ):
            assert verb in r.output, f"missing verb in --help: {verb!r}"

    def test_each_verb_declares_json_flag(self, runner: CliRunner) -> None:
        for verb in (
            "promote-user",
            "demote-user",
            "disable-user",
            "enable-user",
            "kill-session",
            "hard-delete-user",
        ):
            r = runner.invoke(app, ["server", "admin", verb, "--help"])
            assert r.exit_code == 0, f"{verb}: {r.output}"
            assert "--json" in r.output


class TestNoTokenExit1:
    def test_promote_user_no_token(
        self, runner: CliRunner, env_setup
    ) -> None:
        r = runner.invoke(app, ["server", "admin", "promote-user", "alice"])
        assert r.exit_code == 1
        assert "not logged in" in r.output


class TestPromoteUserHappy:
    def test_happy_json(self, runner: CliRunner, env_setup) -> None:
        _bootstrap_and_login(runner)
        _create_user(runner, "alice", "alicepw", role="user")
        r = runner.invoke(
            app, ["server", "admin", "promote-user", "alice", "--json"]
        )
        assert r.exit_code == 0, r.output
        payload = json.loads(r.output.splitlines()[-1])
        assert payload["verb"] == "admin_promote_user"
        assert payload["target"] == "alice"
        assert payload["prior_role"] == "user"


class TestPromoteUserExit5AlreadyAdmin:
    def test_already_admin_exit_5(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap_and_login(runner)
        r = runner.invoke(
            app, ["server", "admin", "promote-user", "admin"]
        )
        # admin is already an admin → AlreadyAnAdminError → exit 5
        assert r.exit_code == 5, r.output


class TestPromoteUserExit2UserNotFound:
    def test_user_not_found_exit_2(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap_and_login(runner)
        r = runner.invoke(
            app, ["server", "admin", "promote-user", "nobody"]
        )
        assert r.exit_code == 2, r.output


class TestDemoteUserExit4LastAdmin:
    def test_sole_admin_exit_4(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap_and_login(runner)
        r = runner.invoke(
            app, ["server", "admin", "demote-user", "admin"]
        )
        # admin is the sole admin → LastAdminError → exit 4
        assert r.exit_code == 4, r.output


class TestDemoteUserExit2NotAnAdmin:
    def test_non_admin_target_exit_2(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap_and_login(runner)
        _create_user(runner, "alice", "alicepw", role="user")
        r = runner.invoke(
            app, ["server", "admin", "demote-user", "alice"]
        )
        # alice is a user, not admin → NotAnAdminError → exit 2
        assert r.exit_code == 2, r.output


class TestEnableUserHappy:
    def test_happy_json(self, runner: CliRunner, env_setup) -> None:
        _bootstrap_and_login(runner)
        _create_user(runner, "alice", "alicepw", role="user")
        r = runner.invoke(
            app, ["server", "admin", "enable-user", "alice", "--json"]
        )
        assert r.exit_code == 0, r.output
        payload = json.loads(r.output.splitlines()[-1])
        assert payload["verb"] == "admin_enable_user"
        assert payload["target"] == "alice"


class TestKillSessionExit6:
    def test_session_not_found_exit_6(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap_and_login(runner)
        r = runner.invoke(
            app, ["server", "admin", "kill-session", "nope"]
        )
        # SessionNotFoundError → exit 6
        assert r.exit_code == 6, r.output


class TestHardDeleteHappy:
    def test_happy_json(self, runner: CliRunner, env_setup) -> None:
        _bootstrap_and_login(runner)
        _create_user(runner, "alice", "alicepw", role="user")
        r = runner.invoke(
            app, ["server", "admin", "hard-delete-user", "alice", "--json"]
        )
        assert r.exit_code == 0, r.output
        payload = json.loads(r.output.splitlines()[-1])
        assert payload["verb"] == "hard_delete_user"
        assert payload["target"] == "alice"
        assert payload["prior_role"] == "user"
        assert payload["was_disabled"] is False


class TestHardDeleteExit4SoleAdmin:
    def test_sole_admin_exit_4(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap_and_login(runner)
        r = runner.invoke(
            app, ["server", "admin", "hard-delete-user", "admin"]
        )
        # admin is sole admin → LastAdminError → exit 4
        assert r.exit_code == 4, r.output


class TestDisableUserHappy:
    def test_happy_json(self, runner: CliRunner, env_setup) -> None:
        _bootstrap_and_login(runner)
        _create_user(runner, "alice", "alicepw", role="user")
        r = runner.invoke(
            app, ["server", "admin", "disable-user", "alice", "--json"]
        )
        assert r.exit_code == 0, r.output
        payload = json.loads(r.output.splitlines()[-1])
        assert payload["verb"] == "admin_disable_user"
        assert payload["target"] == "alice"
        assert payload["was_already_disabled"] is False
