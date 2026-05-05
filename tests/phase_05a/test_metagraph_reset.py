"""Phase 05a — `mindsos metagraph reset` (Q6-A orphan check + P5 --yes guard)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


# ── Q6-A orphan check ───────────────────────────────────────────────────────


def test_reset_refuses_with_referencing_graphs_no_force(_isolated_state_dir):
    """Q6-A — refuse exit 1 if any graph references this metagraph."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    runner.invoke(app, ["metagraph", "add-graph", "--name", "mg", "--graph", "g1"])
    res = runner.invoke(app, ["metagraph", "reset", "--name", "mg"])
    assert res.exit_code == 1
    output = res.output + (res.stderr or "")
    assert "referenced by" in output


def test_reset_force_strips_back_pointers_with_yes(_isolated_state_dir):
    """Q6-A + P5 — --force --yes strips back-pointers + deletes."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    runner.invoke(app, ["graph", "create", "--name", "g1"])
    runner.invoke(app, ["metagraph", "add-graph", "--name", "mg", "--graph", "g1"])
    res = runner.invoke(
        app,
        ["metagraph", "reset", "--name", "mg",
         "--force", "--yes", "--json"],
    )
    assert res.exit_code == 0, res.output
    # Stderr warning may be mixed in (Q6-A force-strip warning).
    idx = res.output.find("{")
    data = json.loads(res.output[idx:])
    assert "g1" in data["stripped_back_pointers"]
    # Graph state file's back-pointer is now None.
    raw = json.loads(
        (_isolated_state_dir / "graph-g1.json").read_text(encoding="utf-8")
    )
    assert raw["metagraph_name"] is None


# ── P5 --yes guard ──────────────────────────────────────────────────────────


def test_reset_force_without_yes_refuses(_isolated_state_dir):
    """P5 — --force requires --yes."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    res = runner.invoke(
        app,
        ["metagraph", "reset", "--name", "mg", "--force"],
    )
    assert res.exit_code == 2
    output = res.output + (res.stderr or "")
    assert "--yes" in output


def test_reset_all_without_yes_refuses(_isolated_state_dir):
    """P5 — --all requires --yes."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg-a"])
    res = runner.invoke(app, ["metagraph", "reset", "--all"])
    assert res.exit_code == 2
    output = res.output + (res.stderr or "")
    assert "--yes" in output


def test_reset_all_with_yes_succeeds(_isolated_state_dir):
    """P5 — --all --yes deletes every metagraph."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg-a"])
    runner.invoke(app, ["metagraph", "create", "--name", "mg-b"])
    res = runner.invoke(
        app,
        ["metagraph", "reset", "--all", "--yes", "--json"],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert sorted(data["deleted"]) == ["mg-a", "mg-b"]


def test_reset_name_only_no_references_succeeds(_isolated_state_dir):
    """Reset by name with no referencing graphs needs no flags."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    res = runner.invoke(
        app,
        ["metagraph", "reset", "--name", "mg", "--json"],
    )
    assert res.exit_code == 0
    assert not (_isolated_state_dir / "metagraph-mg.json").exists()
