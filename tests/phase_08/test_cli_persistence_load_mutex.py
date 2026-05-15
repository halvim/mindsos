"""R4-6 A — --graph G | --metagraph M mutex on load + verify."""

from __future__ import annotations

import subprocess
import sys


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "mindsos_cli", *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_load_combo_graph_and_metagraph_exits_1() -> None:
    """`mindsos persistence load --graph G --metagraph M` exits 1 (R4-6 A)."""
    result = _run_cli(
        "persistence", "load", "--graph", "g1", "--metagraph", "m1",
    )
    assert result.returncode == 1, (
        f"expected exit 1; got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # Stderr or stdout mentions mutex.
    combined = result.stdout + result.stderr
    assert "mutually exclusive" in combined.lower()


def test_load_neither_graph_nor_metagraph_exits_1() -> None:
    """`mindsos persistence load` with neither flag exits 1."""
    result = _run_cli("persistence", "load")
    assert result.returncode == 1


def test_verify_combo_graph_and_metagraph_db_source_exits_1() -> None:
    """`verify --source=db --graph G --metagraph M` exits 1 (R4-6 A)."""
    result = _run_cli(
        "persistence", "verify",
        "--source", "db",
        "--graph", "g1",
        "--metagraph", "m1",
    )
    assert result.returncode == 1
    combined = result.stdout + result.stderr
    assert "mutually exclusive" in combined.lower()


def test_sync_combo_graph_and_metagraph_exits_1() -> None:
    """`sync --graph G --metagraph M` exits 1 (R4-6 A symmetric)."""
    result = _run_cli(
        "persistence", "sync", "--graph", "g1", "--metagraph", "m1",
    )
    assert result.returncode == 1
