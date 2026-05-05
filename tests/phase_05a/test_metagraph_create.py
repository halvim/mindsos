"""Phase 05a — `mindsos metagraph create` (CR-A locked)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli import state as state_mod
from mindsos_cli.app import app


runner = CliRunner()


def test_create_fresh_metagraph(_isolated_state_dir):
    """Happy path — fresh metagraph state file written."""
    res = runner.invoke(app, ["metagraph", "create", "--name", "mg1", "--json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["name"] == "mg1"
    assert data["properties"] == {}
    # State file exists.
    path = _isolated_state_dir / "metagraph-mg1.json"
    assert path.exists()
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["_state_version"] == state_mod.METAGRAPH_STATE_VERSION
    assert raw["name"] == "mg1"
    assert raw["contained_graphs"] == []


def test_create_with_properties_via_CR_A(_isolated_state_dir):
    """CR-A — `--prop k=v` accepted at create time."""
    res = runner.invoke(
        app,
        [
            "metagraph", "create", "--name", "mg",
            "--prop", "kl:active_graph_ids=foo",
            "--prop", "server:user_id=user-1",
            "--json",
        ],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["properties"] == {
        "kl:active_graph_ids": "foo",
        "server:user_id": "user-1",
    }


def test_create_with_explicit_metagraph_id(_isolated_state_dir):
    """`--metagraph-id` accepted (parity with `mindsos graph create --graph-id`)."""
    res = runner.invoke(
        app,
        [
            "metagraph", "create", "--name", "mg",
            "--metagraph-id", "test-mg-id",
            "--json",
        ],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["metagraph_id"] == "test-mg-id"


def test_create_duplicate_name_refused(_isolated_state_dir):
    """Re-create of existing name refused with exit 1."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    res = runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    assert res.exit_code == 1
    output = res.output + (res.stderr or "")
    assert "already exists" in output


def test_create_reserved_property_key_rejected(_isolated_state_dir):
    """P13 — reserved-key validation extends to metagraph property scope."""
    res = runner.invoke(
        app,
        [
            "metagraph", "create", "--name", "mg",
            "--prop", "metaedges=lol",  # reserved per P13
        ],
    )
    assert res.exit_code == 1
    output = res.output + (res.stderr or "")
    assert "PropertyShapeError" in output or "reserved" in output
