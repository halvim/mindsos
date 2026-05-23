"""CLI ``mindsos server release {propose-for-promotion,ship}`` subgroup.

Per PB-14(b) — semantic separation from `admin` subgroup; exit codes
7-8 extension per Z14.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mindsos_admin import propose_for_promotion
from mindsos_cli.app import app
from mindsos_server._argon2 import _TEST_FAST_PARAMS
from mindsos_server._db import open_db
from mindsos_server._schema import init_or_migrate
from mindsos_server.users import _insert_first_admin


@pytest.fixture()
def cli_runner():
    return CliRunner(mix_stderr=False)


@pytest.fixture()
def cli_db_path(tmp_path: Path, monkeypatch) -> Path:
    """Setup a seeded server.db + point CLI env var at it."""
    db_path = tmp_path / "server.db"
    monkeypatch.setenv("MINDSOS_SERVER_DB", str(db_path))
    with open_db(db_path) as conn:
        init_or_migrate(conn)
        _insert_first_admin(
            conn, "admin", "adminpw",
            params=_TEST_FAST_PARAMS, os_user="test-host",
        )
    return db_path


def _login_admin(cli_runner, monkeypatch, tmp_path) -> None:
    """Log in as 'admin' and store the token at the default path."""
    token_dir = tmp_path / "mindsos"
    token_dir.mkdir(exist_ok=True)
    monkeypatch.setenv("MINDSOS_TOKEN_FILE", str(token_dir / "token"))
    result = cli_runner.invoke(
        app, ["server", "login", "admin"], input="adminpw\n",
    )
    assert result.exit_code == 0, result.stdout + result.stderr


def test_release_subgroup_shows_help(cli_runner, cli_db_path):
    """`mindsos server release --help` lists the two verbs."""
    result = cli_runner.invoke(app, ["server", "release", "--help"])
    assert result.exit_code == 0
    assert "propose-for-promotion" in result.stdout
    assert "ship" in result.stdout


def test_release_ship_empty_exits_7(
    cli_runner, cli_db_path, monkeypatch, tmp_path,
):
    """`release ship` with no pending → exit 7 (EmptyReleaseError)."""
    _login_admin(cli_runner, monkeypatch, tmp_path)
    result = cli_runner.invoke(app, ["server", "release", "ship"])
    assert result.exit_code == 7
    assert "No unshipped pending mutations" in result.stderr


def test_release_propose_and_ship_happy_path(
    cli_runner, cli_db_path, monkeypatch, tmp_path,
):
    """`release propose-for-promotion` then `release ship` round-trip."""
    _login_admin(cli_runner, monkeypatch, tmp_path)
    proposal = {
        "reason": "test",
        "items": [
            {
                "kind": "ATOM",
                "node": {
                    "node_type": "Class",
                    "value": "Animal",
                    "properties": {},
                    "target_role": "ontology",
                },
            }
        ],
    }
    propose_result = cli_runner.invoke(
        app, ["server", "release", "propose-for-promotion",
              "--input-json", "-", "--json"],
        input=json.dumps(proposal),
    )
    assert propose_result.exit_code == 0, (
        propose_result.stdout + propose_result.stderr
    )
    out = json.loads(propose_result.stdout)
    assert out["verb"] == "release_propose_for_promotion"
    assert len(out["mutation_ids"]) == 1

    ship_result = cli_runner.invoke(
        app, ["server", "release", "ship", "--json"],
    )
    assert ship_result.exit_code == 0, ship_result.stdout + ship_result.stderr
    ship_out = json.loads(ship_result.stdout)
    assert ship_out["status"] == "SHIPPED"
    assert ship_out["mutations_shipped_count"] == 1
    assert ship_out["roles_affected"] == ["ontology"]
