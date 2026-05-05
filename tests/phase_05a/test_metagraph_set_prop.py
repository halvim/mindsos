"""Phase 05a — `mindsos metagraph set-prop` (Q1-B + P17 3-way mutex)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def _setup_with_metaedge():
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    for n in ["g1", "g2"]:
        runner.invoke(app, ["graph", "create", "--name", n])
        runner.invoke(app, ["metagraph", "add-graph", "--name", "mg", "--graph", n])
    res = runner.invoke(
        app,
        [
            "metagraph", "add-metaedge", "--name", "mg",
            "--source-graph", "g1", "--target-graph", "g2",
            "--type", "REL", "--prop", "a=1", "--json",
        ],
    )
    return json.loads(res.output)["edge_id"]


def test_set_prop_metaedge_merge(_isolated_state_dir):
    """Default merge on metaedge property bag."""
    eid = _setup_with_metaedge()
    res = runner.invoke(
        app,
        [
            "metagraph", "set-prop", "--name", "mg",
            "--metaedge-id", eid, "--prop", "b=2", "--json",
        ],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["properties"] == {"a": 1, "b": 2}


def test_set_prop_metaedge_replace_preserves_refs(_isolated_state_dir):
    """--replace swaps non-ref portion; ref:* keys preserved (Pick D + N5)."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    for n in ["g1", "g2"]:
        runner.invoke(app, ["graph", "create", "--name", n])
        runner.invoke(app, ["metagraph", "add-graph", "--name", "mg", "--graph", n])
    res = runner.invoke(
        app,
        [
            "metagraph", "add-metaedge", "--name", "mg",
            "--source-graph", "g1", "--target-graph", "g2",
            "--type", "REL", "--prop", "a=1",
            "--prop", "ref:anchor=anchor-id-1", "--json",
        ],
    )
    eid = json.loads(res.output)["edge_id"]
    res = runner.invoke(
        app,
        [
            "metagraph", "set-prop", "--name", "mg",
            "--metaedge-id", eid, "--prop", "b=2", "--replace", "--json",
        ],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    # 'a' dropped (replace), 'b' set, ref:anchor preserved.
    assert data["properties"] == {"b": 2, "ref:anchor": "anchor-id-1"}


def test_set_prop_three_way_mutex_violation(_isolated_state_dir):
    """P17 — exactly ONE of --on-metagraph / --metaedge-id / --metahyperedge-id."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    res = runner.invoke(
        app,
        [
            "metagraph", "set-prop", "--name", "mg",
            "--on-metagraph", "--metaedge-id", "x",
            "--prop", "a=1",
        ],
    )
    assert res.exit_code == 2


def test_set_prop_on_metagraph_merges(_isolated_state_dir):
    """P17 — --on-metagraph operates on metagraph property bag."""
    runner.invoke(
        app,
        ["metagraph", "create", "--name", "mg",
         "--prop", "kl:active=foo"],
    )
    res = runner.invoke(
        app,
        [
            "metagraph", "set-prop", "--name", "mg",
            "--on-metagraph", "--prop", "server:user_id=u1", "--json",
        ],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["kind"] == "metagraph"
    assert data["properties"] == {
        "kl:active": "foo",
        "server:user_id": "u1",
    }


def test_set_prop_on_metagraph_round_trip_via_inspect(_isolated_state_dir):
    """P17 — properties survive load via `metagraph inspect`."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    runner.invoke(
        app,
        [
            "metagraph", "set-prop", "--name", "mg",
            "--on-metagraph", "--prop", "kl:k=v",
        ],
    )
    res = runner.invoke(app, ["metagraph", "inspect", "--name", "mg", "--json"])
    data = json.loads(res.output)
    assert data["properties"] == {"kl:k": "v"}


def test_set_prop_metahyperedge_merge(_isolated_state_dir):
    """Mutex case: --metahyperedge-id."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    for n in ["g1", "g2"]:
        runner.invoke(app, ["graph", "create", "--name", n])
        runner.invoke(app, ["metagraph", "add-graph", "--name", "mg", "--graph", n])
    res = runner.invoke(
        app,
        [
            "metagraph", "add-metahyperedge", "--name", "mg",
            "--type", "T", "--member", "g1", "--member", "g2",
            "--prop", "a=1", "--json",
        ],
    )
    eid = json.loads(res.output)["edge_id"]
    res = runner.invoke(
        app,
        [
            "metagraph", "set-prop", "--name", "mg",
            "--metahyperedge-id", eid, "--prop", "b=2", "--json",
        ],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["properties"] == {"a": 1, "b": 2}


def test_set_prop_reserved_key_rejected(_isolated_state_dir):
    """P13 — reserved key on metagraph property bag rejected."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    res = runner.invoke(
        app,
        [
            "metagraph", "set-prop", "--name", "mg",
            "--on-metagraph", "--prop", "metaedges=lol",  # reserved per P13
        ],
    )
    assert res.exit_code == 1
