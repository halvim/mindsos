"""
CLI ``read-local`` — admin caller targeting nonexistent user exits 2
(UserNotFoundError reuse per PB-32).
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


def test_admin_targeting_nonexistent_user_exits_2(cli_env) -> None:
    runner = CliRunner()
    runner.invoke(
        server_app, ["bootstrap", "admin-caller"], input="adminpw\n",
    )
    runner.invoke(server_app, ["login", "admin-caller"], input="adminpw\n")
    result = runner.invoke(
        server_app, ["admin", "read-local", "ghost-user-id"],
    )
    assert result.exit_code == 2, (result.stdout, result.stderr)
    assert "ghost-user-id" in result.stderr
