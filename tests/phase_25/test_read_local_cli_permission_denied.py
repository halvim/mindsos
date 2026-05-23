"""
CLI ``read-local`` denial path — non-admin caller exits 3.

PB-R6-05 info-leak verification — non-admin probing a nonexistent
target_user_id ALSO gets exit 3, NOT exit 2, because the outer cap
check runs first.
"""

from __future__ import annotations

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


def _bootstrap_admin(runner: CliRunner) -> None:
    r = runner.invoke(
        app, ["server", "bootstrap", "admin"], input="adminpw\n",
    )
    assert r.exit_code == 0, r.output


def _login_as(runner: CliRunner, user_id: str, password: str) -> None:
    r = runner.invoke(
        app, ["server", "login", user_id], input=f"{password}\n",
    )
    assert r.exit_code == 0, r.output


def _logout(runner: CliRunner) -> None:
    r = runner.invoke(app, ["server", "logout"])
    # logout is idempotent — exit 0 on success or already-logged-out.
    assert r.exit_code in (0, 1), r.output


def _create_user_via_admin(
    runner: CliRunner, user_id: str, password: str,
) -> None:
    r = runner.invoke(
        app, ["server", "user", "create", user_id, "--role", "user"],
        input=f"{password}\n",
    )
    assert r.exit_code == 0, r.output


def test_non_admin_caller_exits_3(runner, env_setup) -> None:
    _bootstrap_admin(runner)
    _login_as(runner, "admin", "adminpw")
    _create_user_via_admin(runner, "alice", "alicepw")
    _logout(runner)
    _login_as(runner, "alice", "alicepw")

    r = runner.invoke(app, ["server", "admin", "read-local", "alice"])
    assert r.exit_code == 3, r.output


def test_non_admin_probing_nonexistent_target_still_exits_3(
    runner, env_setup,
) -> None:
    """
    PB-R6-05 — outer cap check runs FIRST, so target-not-found is
    not observable to a non-admin caller. Exit 3, not exit 2.
    """
    _bootstrap_admin(runner)
    _login_as(runner, "admin", "adminpw")
    _create_user_via_admin(runner, "alice", "alicepw")
    _logout(runner)
    _login_as(runner, "alice", "alicepw")

    r = runner.invoke(
        app, ["server", "admin", "read-local", "ghost-user-id"],
    )
    assert r.exit_code == 3, r.output
