"""
CLI ``mindsos server admin read-local`` happy path.

Follows the Phase 22 ``test_cli_admin_subgroup.py`` canonical pattern:
``from mindsos_cli.app import app`` (not ``server_app``); env setup
via ``MINDSOS_SERVER_DB`` + ``HOME`` + delenv ``MINDSOS_TOKEN``;
invocation paths use the full subcommand chain.
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
    runner: CliRunner, user_id: str = "admin", password: str = "adminpw",
) -> None:
    r = runner.invoke(
        app, ["server", "bootstrap", user_id], input=f"{password}\n",
    )
    assert r.exit_code == 0, r.output
    r = runner.invoke(
        app, ["server", "login", user_id], input=f"{password}\n",
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


def test_read_local_happy_path_text_output(runner, env_setup) -> None:
    _bootstrap_and_login(runner)
    _create_user(runner, "alice", "alicepw", role="user")

    r = runner.invoke(app, ["server", "admin", "read-local", "alice"])
    assert r.exit_code == 0, r.output
    assert "Local for user_id=alice" in r.output
    assert "memories" in r.output
    assert "capacity-state" in r.output
    assert "xrefs: 0" in r.output
    assert "intergraph_edges: 0" in r.output


def test_read_local_happy_path_json_output(runner, env_setup) -> None:
    _bootstrap_and_login(runner)
    _create_user(runner, "alice", "alicepw", role="user")

    r = runner.invoke(
        app, ["server", "admin", "read-local", "--json", "alice"],
    )
    assert r.exit_code == 0, r.output
    # The JSON payload is the entire stdout (no extra prologue).
    payload = json.loads(r.output)
    assert payload["target_user_id"] == "alice"
    assert payload["xref_count"] == 0
    assert payload["intergraph_edge_count"] == 0
    roles = {rg["role"] for rg in payload["role_graphs"]}
    assert roles == {"memories", "capacity-state"}
