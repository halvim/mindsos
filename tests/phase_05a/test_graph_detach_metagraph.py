"""Phase 05a — `mindsos graph detach-metagraph` (DM-A recovery path)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def test_detach_metagraph_happy_path(_isolated_state_dir):
    """DM-A — clears metagraph_name back-pointer."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    runner.invoke(app, ["metagraph", "add-graph", "--name", "mg", "--graph", "g1"])
    res = runner.invoke(
        app,
        ["graph", "detach-metagraph", "--name", "g1", "--json"],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["previous_metagraph"] == "mg"
    # File now has metagraph_name == None.
    raw = json.loads(
        (_isolated_state_dir / "graph-g1.json").read_text(encoding="utf-8")
    )
    assert raw["metagraph_name"] is None


def test_detach_metagraph_on_dangling_back_pointer(_isolated_state_dir):
    """DM-A primary purpose: recover from missing metagraph state file."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    runner.invoke(app, ["metagraph", "add-graph", "--name", "mg", "--graph", "g1"])
    # Manually delete the metagraph state file (simulating corruption).
    (_isolated_state_dir / "metagraph-mg.json").unlink()
    # detach-metagraph still recovers (raw JSON path bypass).
    res = runner.invoke(
        app,
        ["graph", "detach-metagraph", "--name", "g1"],
    )
    assert res.exit_code == 0


def test_detach_metagraph_no_back_pointer_exits_1(_isolated_state_dir):
    """Idempotent-no-op refused: nothing to detach → exit 1."""
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    res = runner.invoke(
        app,
        ["graph", "detach-metagraph", "--name", "g1"],
    )
    assert res.exit_code == 1
    output = res.output + (res.stderr or "")
    assert "no metagraph back-pointer" in output or "nothing to detach" in output
