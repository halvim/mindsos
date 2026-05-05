"""Phase 05a — Metagraph state-file v=1 round-trip + byte-stable + atomic write."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli import state as state_mod
from mindsos_cli.app import app


runner = CliRunner()


def test_v1_round_trip(_isolated_state_dir):
    """Save → load → save produces identical content."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    raw = json.loads(
        (_isolated_state_dir / "metagraph-mg.json").read_text(encoding="utf-8")
    )
    assert raw["_state_version"] == state_mod.METAGRAPH_STATE_VERSION
    assert raw["name"] == "mg"
    assert raw["properties"] == {}
    assert raw["contained_graphs"] == []
    assert raw["metaedges"] == []
    assert raw["metahyperedges"] == []


def test_v1_byte_stable_sort_on_contained_graphs(_isolated_state_dir):
    """contained_graphs sorted by name (insertion order ignored)."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    for n in ["zebra", "apple", "mango"]:
        runner.invoke(app, ["graph", "create", "--name", n])
        runner.invoke(app, ["metagraph", "add-graph", "--name", "mg", "--graph", n])
    raw = json.loads(
        (_isolated_state_dir / "metagraph-mg.json").read_text(encoding="utf-8")
    )
    assert raw["contained_graphs"] == ["apple", "mango", "zebra"]


def test_v1_atomic_write_no_tmp_leftover(_isolated_state_dir):
    """Atomic .tmp + os.replace; no leftover tmp file."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    files = list(_isolated_state_dir.iterdir())
    tmp_files = [f for f in files if f.name.endswith(".tmp")]
    assert tmp_files == []
