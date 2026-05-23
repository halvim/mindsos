"""
CLI ``mindsos server admin read-local`` happy path.

Uses the CliRunner pattern (Phase 22 precedent). Login → run verb →
exit 0 + expected summary output.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from mindsos_cli.commands.server import server_app


@pytest.fixture()
def cli_env(tmp_path: Path, monkeypatch) -> Path:
    """Isolate ~/.mindsos to tmp_path so CLI state doesn't bleed."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("MINDSOS_STATE_DIR", str(tmp_path / "state"))
    return tmp_path


def _bootstrap_and_login(runner: CliRunner) -> None:
    """Bootstrap admin + login; idempotent across reruns."""
    runner.invoke(
        server_app,
        ["bootstrap", "admin-caller"],
        input="adminpw\n",
    )
    runner.invoke(
        server_app,
        ["login", "admin-caller"],
        input="adminpw\n",
    )


def test_read_local_happy_path_text_output(cli_env) -> None:
    runner = CliRunner()
    _bootstrap_and_login(runner)
    # Create the target user via admin verb.
    runner.invoke(
        server_app,
        ["admin", "promote-user", "admin-caller"],  # no-op admin already
    )
    # Seed a regular target user.
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

    result = runner.invoke(server_app, ["admin", "read-local", "alice"])
    assert result.exit_code == 0, result.stderr
    assert "Local for user_id=alice" in result.stdout
    assert "memories" in result.stdout
    assert "capacity-state" in result.stdout
    assert "xrefs: 0" in result.stdout
    assert "intergraph_edges: 0" in result.stdout


def test_read_local_happy_path_json_output(cli_env) -> None:
    runner = CliRunner()
    _bootstrap_and_login(runner)
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

    result = runner.invoke(
        server_app, ["admin", "read-local", "--json", "alice"],
    )
    assert result.exit_code == 0, result.stderr
    import json
    payload = json.loads(result.stdout)
    assert payload["target_user_id"] == "alice"
    assert payload["xref_count"] == 0
    assert payload["intergraph_edge_count"] == 0
    roles = {rg["role"] for rg in payload["role_graphs"]}
    assert roles == {"memories", "capacity-state"}
