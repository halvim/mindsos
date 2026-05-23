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

from mindsos_cli.commands.server import server_app


@pytest.fixture()
def cli_env(tmp_path: Path, monkeypatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("MINDSOS_STATE_DIR", str(tmp_path / "state"))
    return tmp_path


def _bootstrap_admin_then_non_admin_login(runner: CliRunner) -> None:
    """Bootstrap admin, create regular user 'alice', login as alice."""
    runner.invoke(
        server_app, ["bootstrap", "admin-caller"], input="adminpw\n",
    )
    # First login as admin to create alice; then logout + login alice.
    runner.invoke(server_app, ["login", "admin-caller"], input="adminpw\n")
    from mindsos_cli.commands.server import (
        _ensure_migrated,
        _resolve_and_open,
    )
    from mindsos_server._argon2 import _TEST_FAST_PARAMS
    from mindsos_server.users import insert_user
    with _resolve_and_open() as conn:
        _ensure_migrated(conn)
        insert_user(
            conn, "alice", "alicepw",
            actor_role="user", params=_TEST_FAST_PARAMS,
        )
        conn.commit()
    runner.invoke(server_app, ["logout"])
    runner.invoke(server_app, ["login", "alice"], input="alicepw\n")


def test_non_admin_caller_exits_3(cli_env) -> None:
    runner = CliRunner(mix_stderr=False)
    _bootstrap_admin_then_non_admin_login(runner)
    result = runner.invoke(
        server_app, ["admin", "read-local", "alice"],
    )
    assert result.exit_code == 3, (result.stdout, result.stderr)


def test_non_admin_probing_nonexistent_target_still_exits_3(cli_env) -> None:
    """
    PB-R6-05 — outer cap check runs FIRST, so target-not-found is
    not observable to a non-admin caller. Exit 3, not exit 2.
    """
    runner = CliRunner(mix_stderr=False)
    _bootstrap_admin_then_non_admin_login(runner)
    result = runner.invoke(
        server_app, ["admin", "read-local", "ghost-user-id"],
    )
    assert result.exit_code == 3, (result.stdout, result.stderr)
