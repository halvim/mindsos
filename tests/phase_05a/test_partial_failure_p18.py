"""Phase 05a — P18 partial-failure recovery via DM-A."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def test_metagraph_save_failure_leaves_dangling_back_pointer_recoverable_via_DM_A(
    _isolated_state_dir,
):
    """P18 — graph back-pointer write FIRST, then metagraph; on metagraph save
    failure, graph has a dangling back-pointer; DM-A recovers."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    runner.invoke(app, ["graph", "create", "--name", "g1"])

    # Patch the metagraph save to fail mid-add-graph (after graph save).
    from mindsos_cli import state as state_mod

    real_save_metagraph = state_mod.save_metagraph_state

    def failing_save_metagraph(name, state):
        if name == "mg":
            raise RuntimeError("simulated metagraph save failure")
        return real_save_metagraph(name, state)

    with patch.object(state_mod, "save_metagraph_state", failing_save_metagraph):
        res = runner.invoke(
            app,
            ["metagraph", "add-graph", "--name", "mg", "--graph", "g1"],
        )
        # Add should fail due to metagraph-save failure.
        assert res.exit_code != 0

    # Per P18 — graph state file written FIRST, so back-pointer is set
    # even though metagraph save failed.
    raw = json.loads(
        (_isolated_state_dir / "graph-g1.json").read_text(encoding="utf-8")
    )
    assert raw["metagraph_name"] == "mg"

    # DM-A — recover the dangling back-pointer.
    res = runner.invoke(
        app,
        ["graph", "detach-metagraph", "--name", "g1", "--json"],
    )
    assert res.exit_code == 0
    raw = json.loads(
        (_isolated_state_dir / "graph-g1.json").read_text(encoding="utf-8")
    )
    assert raw["metagraph_name"] is None
