"""Phase 02 — `mindsos identity registry` exercises IdentityRegistry semantics
through a JSON state file persisted across invocations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_register_and_list_round_trip(cli, isolated_state_dir, monkeypatch):
    proc1 = cli(
        "identity", "registry",
        "--scope", "phase02",
        "--register", "id-a",
        "--register", "id-b",
        env={**dict(MINDSOS_STATE_DIR=str(isolated_state_dir))},
    )
    assert proc1.returncode == 0, proc1.stderr

    proc2 = cli(
        "identity", "registry",
        "--scope", "phase02",
        "--list", "--json",
        env={"MINDSOS_STATE_DIR": str(isolated_state_dir)},
    )
    assert proc2.returncode == 0, proc2.stderr
    payload = json.loads(proc2.stdout)
    assert payload["scope"] == "phase02"
    assert payload["count"] == 2
    assert payload["ids"] == ["id-a", "id-b"]


def test_duplicate_register_exits_non_zero_with_structured_error(
    cli, isolated_state_dir
):
    env = {"MINDSOS_STATE_DIR": str(isolated_state_dir)}
    cli(
        "identity", "registry",
        "--scope", "dup",
        "--register", "shared-id",
        env=env,
    )
    proc = cli(
        "identity", "registry",
        "--scope", "dup",
        "--register", "shared-id",
        env=env,
    )
    assert proc.returncode == 1, (proc.returncode, proc.stdout, proc.stderr)
    assert "Duplicate id" in proc.stderr


def test_clear_empties_the_scope(cli, isolated_state_dir):
    env = {"MINDSOS_STATE_DIR": str(isolated_state_dir)}
    cli("identity", "registry", "--scope", "c", "--register", "x", env=env)
    cli("identity", "registry", "--scope", "c", "--register", "y", env=env)
    cli("identity", "registry", "--scope", "c", "--clear", env=env)

    proc = cli(
        "identity", "registry",
        "--scope", "c", "--list", "--json",
        env=env,
    )
    payload = json.loads(proc.stdout)
    assert payload["count"] == 0
    assert payload["ids"] == []


def test_state_file_explicit_override(cli, tmp_path):
    custom = tmp_path / "custom-registry.json"
    proc1 = cli(
        "identity", "registry",
        "--state-file", str(custom),
        "--register", "from-override",
    )
    assert proc1.returncode == 0
    assert custom.exists(), proc1.stderr

    body = json.loads(custom.read_text())
    assert body == {"ids": ["from-override"]}


def test_no_action_exits_two_with_help_message(cli, isolated_state_dir):
    proc = cli(
        "identity", "registry",
        "--scope", "x",
        env={"MINDSOS_STATE_DIR": str(isolated_state_dir)},
    )
    assert proc.returncode == 2, (proc.returncode, proc.stdout, proc.stderr)
    assert "No action requested" in proc.stderr


def test_corrupt_state_file_is_diagnosed(cli, isolated_state_dir, tmp_path):
    custom = tmp_path / "corrupt.json"
    custom.write_text("{this is not json")
    proc = cli(
        "identity", "registry",
        "--state-file", str(custom),
        "--list",
    )
    assert proc.returncode == 1
    assert "state file corrupt" in proc.stderr or "Expecting" in proc.stderr
