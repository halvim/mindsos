"""
CLI ``read-local`` — admin caller targeting nonexistent user exits 2
(UserNotFoundError reuse per PB-32).
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


def test_admin_targeting_nonexistent_user_exits_2(runner, env_setup) -> None:
    r = runner.invoke(
        app, ["server", "bootstrap", "admin"], input="adminpw\n",
    )
    assert r.exit_code == 0, r.output
    r = runner.invoke(
        app, ["server", "login", "admin"], input="adminpw\n",
    )
    assert r.exit_code == 0, r.output

    r = runner.invoke(
        app, ["server", "admin", "read-local", "ghost-user-id"],
    )
    assert r.exit_code == 2, r.output
    assert "ghost-user-id" in r.output
