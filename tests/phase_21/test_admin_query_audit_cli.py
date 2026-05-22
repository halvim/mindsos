"""
Phase 21 CLI verb: ``mindsos server query-audit``.

Asserts:

* Verb appears in help; all 9 flags declared (PB-23 + PB-24).
* Token-required path (no token → exit 1 "not logged in").
* PermissionDeniedError → exit 3 + stderr.
* ValueError (bad ISO-8601) → exit 2 + stderr.
* Happy-path TSV output shape (PB-25): one row per line, tab-sep.
* Happy-path ``--json`` shape (PB-24): rows + count + next_after_id.
* ``--count-only`` plain + JSON shapes.
* ``next_after_id`` sentinel: null on last page; populated otherwise.

Per ADR-0013 §am2 + Phase 21 PB-23 + PB-24 + PB-25.
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
    """
    Point the CLI at a tmp ``server.db``; clear any inherited token env.
    """
    db_path = tmp_path / "server.db"
    monkeypatch.setenv("MINDSOS_SERVER_DB", str(db_path))
    monkeypatch.delenv("MINDSOS_TOKEN", raising=False)
    # Force a tmp HOME so token file goes into tmp_path (avoids
    # picking up the host operator's real ~/.mindsos/token).
    monkeypatch.setenv("HOME", str(tmp_path))
    return {"db": db_path, "home": tmp_path}


def _bootstrap_and_login(
    runner: CliRunner, *, user_id: str = "admin", password: str = "adminpw"
) -> None:
    """Helper: bootstrap an admin + login so the CLI has a session token."""
    r = runner.invoke(
        app, ["server", "bootstrap", user_id], input=f"{password}\n"
    )
    assert r.exit_code == 0, r.output
    r = runner.invoke(
        app, ["server", "login", user_id], input=f"{password}\n"
    )
    assert r.exit_code == 0, r.output


class TestCliShape:
    def test_query_audit_in_help(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["server", "--help"])
        assert result.exit_code == 0
        assert "query-audit" in result.output

    def test_flags_declared(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["server", "query-audit", "--help"])
        assert result.exit_code == 0
        for flag in (
            "--actor",
            "--event",
            "--target",
            "--since",
            "--until",
            "--after-id",
            "--limit",
            "--count-only",
            "--json",
        ):
            assert flag in result.output


class TestNoTokenExit1:
    def test_no_token_exits_1(
        self, runner: CliRunner, env_setup
    ) -> None:
        # No bootstrap, no login → no token file.
        result = runner.invoke(app, ["server", "query-audit"])
        assert result.exit_code == 1
        assert "not logged in" in result.output


class TestHappyPath:
    def test_plain_output_is_tsv(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap_and_login(runner)
        result = runner.invoke(app, ["server", "query-audit"])
        assert result.exit_code == 0, result.output
        # At least one row should contain tabs.
        lines = result.output.strip().splitlines()
        assert any("\t" in line for line in lines)

    def test_json_output_shape(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap_and_login(runner)
        result = runner.invoke(app, ["server", "query-audit", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output.strip().splitlines()[-1])
        assert "rows" in payload
        assert "count" in payload
        assert "next_after_id" in payload

    def test_count_only_plain(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap_and_login(runner)
        result = runner.invoke(
            app, ["server", "query-audit", "--count-only"]
        )
        assert result.exit_code == 0, result.output
        assert "count=" in result.output

    def test_count_only_json(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap_and_login(runner)
        result = runner.invoke(
            app, ["server", "query-audit", "--count-only", "--json"]
        )
        assert result.exit_code == 0, result.output
        # The very last line is the JSON payload; earlier lines may be
        # login-print or empty.
        payload = json.loads(result.output.strip().splitlines()[-1])
        assert "count" in payload
        # count_only mode shouldn't have rows / next_after_id.
        assert "rows" not in payload
        assert "next_after_id" not in payload


class TestBadIsoExits2:
    def test_bad_iso_raises_value_error_exit_2(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap_and_login(runner)
        result = runner.invoke(
            app, ["server", "query-audit", "--since", "not a date"]
        )
        assert result.exit_code == 2
        assert "error:" in result.output


class TestNonAdminExit3:
    """
    Non-admin caller → PermissionDeniedError → CLI exit 3.

    Setup: bootstrap an admin, create + login as a non-admin user,
    then run query-audit as that non-admin session.
    """

    def test_non_admin_exits_3(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap_and_login(runner)
        # Create a non-admin user via admin user-create.
        r = runner.invoke(
            app, ["server", "user", "create", "alice"], input="alicepw\n"
        )
        assert r.exit_code == 0, r.output
        # Logout admin, then login as alice.
        r = runner.invoke(app, ["server", "logout"])
        assert r.exit_code == 0, r.output
        r = runner.invoke(
            app, ["server", "login", "alice"], input="alicepw\n"
        )
        assert r.exit_code == 0, r.output

        # Now query-audit as alice → denial → exit 3.
        result = runner.invoke(app, ["server", "query-audit"])
        assert result.exit_code == 3
        assert "error:" in result.output
        assert "CAN_VIEW_AUDIT_LOG" in result.output


class TestNextAfterIdSentinel:
    def test_null_when_fewer_than_limit(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap_and_login(runner)
        # Fresh DB has only a few audit rows; default limit=100 →
        # next_after_id should be null.
        result = runner.invoke(app, ["server", "query-audit", "--json"])
        payload = json.loads(result.output.strip().splitlines()[-1])
        assert payload["next_after_id"] is None

    def test_populated_when_at_limit(
        self, runner: CliRunner, env_setup
    ) -> None:
        _bootstrap_and_login(runner)
        # limit=2 + at least 2 existing rows → next_after_id present.
        result = runner.invoke(
            app, ["server", "query-audit", "--json", "--limit", "2"]
        )
        payload = json.loads(result.output.strip().splitlines()[-1])
        assert payload["count"] == 2
        assert payload["next_after_id"] is not None
        # next_after_id is the last row's id.
        assert payload["next_after_id"] == payload["rows"][-1]["id"]
