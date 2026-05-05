"""Phase 05a — `mindsos metagraph add/remove-metaedge / -metahyperedge` (P11 + P15 + Q3-A)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def _setup_metagraph_with_three_graphs():
    """Common fixture: mg + g1 + g2 + g3 added."""
    runner.invoke(app, ["metagraph", "create", "--name", "mg"])
    for n in ["g1", "g2", "g3"]:
        runner.invoke(app, ["graph", "create", "--name", n])
        runner.invoke(app, ["metagraph", "add-graph", "--name", "mg", "--graph", n])


# ── add-metaedge ────────────────────────────────────────────────────────────


def test_add_metaedge_happy_path(_isolated_state_dir):
    _setup_metagraph_with_three_graphs()
    res = runner.invoke(
        app,
        [
            "metagraph", "add-metaedge", "--name", "mg",
            "--source-graph", "g1", "--target-graph", "g2",
            "--type", "REFINES", "--json",
        ],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["source_graph"] == "g1"
    assert data["target_graph"] == "g2"
    assert data["type_name"] == "REFINES"


def test_add_metaedge_cypher_regex_enforced(_isolated_state_dir):
    """ADR-0021 — invalid cypher rel-type rejected."""
    _setup_metagraph_with_three_graphs()
    res = runner.invoke(
        app,
        [
            "metagraph", "add-metaedge", "--name", "mg",
            "--source-graph", "g1", "--target-graph", "g2",
            "--type", "lowercase",  # invalid
        ],
    )
    assert res.exit_code == 1
    output = res.output + (res.stderr or "")
    assert "CypherError" in output


def test_add_metaedge_self_loop_refused_P15(_isolated_state_dir):
    """P15 — source == target rejected."""
    _setup_metagraph_with_three_graphs()
    res = runner.invoke(
        app,
        [
            "metagraph", "add-metaedge", "--name", "mg",
            "--source-graph", "g1", "--target-graph", "g1",
            "--type", "SELF",
        ],
    )
    assert res.exit_code == 1
    output = res.output + (res.stderr or "")
    assert "self-loop" in output or "SchemaError" in output


def test_add_metaedge_carries_label_and_properties(_isolated_state_dir):
    """Label round-trip + properties round-trip."""
    _setup_metagraph_with_three_graphs()
    res = runner.invoke(
        app,
        [
            "metagraph", "add-metaedge", "--name", "mg",
            "--source-graph", "g1", "--target-graph", "g2",
            "--type", "REL", "--label", "human-label",
            "--prop", "a=1", "--prop", "b=hello", "--json",
        ],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["label"] == "human-label"
    assert data["properties"] == {"a": 1, "b": "hello"}


def test_add_metaedge_unknown_source_graph(_isolated_state_dir):
    """Source graph not in metagraph rejected."""
    _setup_metagraph_with_three_graphs()
    res = runner.invoke(
        app,
        [
            "metagraph", "add-metaedge", "--name", "mg",
            "--source-graph", "not-in-mg", "--target-graph", "g2",
            "--type", "REL",
        ],
    )
    assert res.exit_code == 1


# ── remove-metaedge ─────────────────────────────────────────────────────────


def test_remove_metaedge_happy_path(_isolated_state_dir):
    _setup_metagraph_with_three_graphs()
    res = runner.invoke(
        app,
        [
            "metagraph", "add-metaedge", "--name", "mg",
            "--source-graph", "g1", "--target-graph", "g2",
            "--type", "REL", "--json",
        ],
    )
    edge_id = json.loads(res.output)["edge_id"]
    res = runner.invoke(
        app,
        [
            "metagraph", "remove-metaedge", "--name", "mg",
            "--metaedge-id", edge_id, "--json",
        ],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["removed"] is True


# ── add-metahyperedge ───────────────────────────────────────────────────────


def test_add_metahyperedge_happy_path(_isolated_state_dir):
    _setup_metagraph_with_three_graphs()
    res = runner.invoke(
        app,
        [
            "metagraph", "add-metahyperedge", "--name", "mg",
            "--type", "TRIO",
            "--member", "g1", "--member", "g2", "--member", "g3",
            "--json",
        ],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    # Q3-A — member_graphs sorted by name.
    assert data["member_graphs"] == ["g1", "g2", "g3"]
    assert data["type_name"] == "TRIO"


def test_add_metahyperedge_cypher_regex_enforced(_isolated_state_dir):
    _setup_metagraph_with_three_graphs()
    res = runner.invoke(
        app,
        [
            "metagraph", "add-metahyperedge", "--name", "mg",
            "--type", "lowercase",
            "--member", "g1", "--member", "g2",
        ],
    )
    assert res.exit_code == 1
    assert "CypherError" in (res.output + (res.stderr or ""))


def test_add_metahyperedge_member_byte_stable_sort_Q3_A(_isolated_state_dir):
    """Q3-A — member_graphs sorted by graph name on serialize."""
    _setup_metagraph_with_three_graphs()
    res = runner.invoke(
        app,
        [
            "metagraph", "add-metahyperedge", "--name", "mg",
            "--type", "TRI",
            # Insertion order reversed; output must be sorted.
            "--member", "g3", "--member", "g1", "--member", "g2",
            "--json",
        ],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["member_graphs"] == ["g1", "g2", "g3"]


def test_add_metahyperedge_single_member_refused_P15(_isolated_state_dir):
    """P15 — < 2 members rejected at CLI boundary."""
    _setup_metagraph_with_three_graphs()
    res = runner.invoke(
        app,
        [
            "metagraph", "add-metahyperedge", "--name", "mg",
            "--type", "X", "--member", "g1",
        ],
    )
    assert res.exit_code == 1
    output = res.output + (res.stderr or "")
    assert "at least 2" in output or "SchemaError" in output


def test_add_metahyperedge_member_not_in_metagraph_refused(_isolated_state_dir):
    _setup_metagraph_with_three_graphs()
    res = runner.invoke(
        app,
        [
            "metagraph", "add-metahyperedge", "--name", "mg",
            "--type", "X", "--member", "g1", "--member", "not-in-mg",
        ],
    )
    assert res.exit_code == 1


# ── remove-metahyperedge ────────────────────────────────────────────────────


def test_remove_metahyperedge_happy_path(_isolated_state_dir):
    _setup_metagraph_with_three_graphs()
    res = runner.invoke(
        app,
        [
            "metagraph", "add-metahyperedge", "--name", "mg",
            "--type", "TRIO",
            "--member", "g1", "--member", "g2", "--member", "g3",
            "--json",
        ],
    )
    edge_id = json.loads(res.output)["edge_id"]
    res = runner.invoke(
        app,
        [
            "metagraph", "remove-metahyperedge", "--name", "mg",
            "--metahyperedge-id", edge_id, "--json",
        ],
    )
    assert res.exit_code == 0


# ── list-metaedges / list-metahyperedges ────────────────────────────────────


def test_list_metaedges_returns_array(_isolated_state_dir):
    _setup_metagraph_with_three_graphs()
    runner.invoke(
        app,
        ["metagraph", "add-metaedge", "--name", "mg",
         "--source-graph", "g1", "--target-graph", "g2", "--type", "R1"],
    )
    runner.invoke(
        app,
        ["metagraph", "add-metaedge", "--name", "mg",
         "--source-graph", "g2", "--target-graph", "g3", "--type", "R2"],
    )
    res = runner.invoke(
        app, ["metagraph", "list-metaedges", "--name", "mg", "--json"],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert len(data) == 2
    types = {me["type_name"] for me in data}
    assert types == {"R1", "R2"}


def test_list_metahyperedges_returns_array(_isolated_state_dir):
    _setup_metagraph_with_three_graphs()
    runner.invoke(
        app,
        ["metagraph", "add-metahyperedge", "--name", "mg",
         "--type", "TRIO", "--member", "g1", "--member", "g2"],
    )
    res = runner.invoke(
        app, ["metagraph", "list-metahyperedges", "--name", "mg", "--json"],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert len(data) == 1
    assert data[0]["type_name"] == "TRIO"
