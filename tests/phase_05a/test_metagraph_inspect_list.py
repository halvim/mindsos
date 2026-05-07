"""Phase 05a — `mindsos metagraph inspect` and `list` (P10 shape locks)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli import state as state_mod
from mindsos_cli.app import app


runner = CliRunner()


def test_inspect_json_shape_locked(_isolated_state_dir):
    """P10 — JSON shape: name / metagraph_id / properties / contained_graphs /
    counts{graphs,metaedges,metahyperedges,intergraph_edges} / _state_version / state_file.

    Phase 05b extension: ``schema_name`` (top-level) and
    ``counts.intergraph_edges`` added (Pushback 18-A v=2 bump).
    Phase 05c extension: ``counts.intergraph_hyperedges`` added
    (P14-A smaller-items fold v=3 bump).
    """
    runner.invoke(
        app,
        [
            "metagraph", "create", "--name", "mg",
            "--prop", "kl:active=foo",
        ],
    )
    res = runner.invoke(app, ["metagraph", "inspect", "--name", "mg", "--json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert set(data.keys()) == {
        "name", "metagraph_id", "properties", "schema_name",
        "contained_graphs", "counts", "_state_version", "state_file",
    }
    assert set(data["counts"].keys()) == {
        "graphs", "metaedges", "metahyperedges",
        "intergraph_edges", "intergraph_hyperedges",
    }
    assert data["properties"] == {"kl:active": "foo"}
    assert data["contained_graphs"] == []
    assert data["counts"] == {
        "graphs": 0, "metaedges": 0, "metahyperedges": 0,
        "intergraph_edges": 0, "intergraph_hyperedges": 0,
    }
    assert data["schema_name"] is None
    assert data["_state_version"] == state_mod.METAGRAPH_STATE_VERSION


def test_list_json_shape_locked(_isolated_state_dir):
    """P10 — list JSON shape: state_dir + array of {name, metagraph_id,
    schema_name, contained_graphs_count, metaedges_count,
    metahyperedges_count, intergraph_edges_count, _state_version, path}.

    Phase 05b extension: ``schema_name`` and ``intergraph_edges_count``
    added per Pushback 18-A.
    Phase 05c extension: ``intergraph_hyperedges_count`` added per
    P14-A smaller-items fold v=3 bump.
    """
    runner.invoke(app, ["metagraph", "create", "--name", "mg-a"])
    runner.invoke(app, ["metagraph", "create", "--name", "mg-z"])
    res = runner.invoke(app, ["metagraph", "list", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert "state_dir" in data
    assert "metagraphs" in data
    assert len(data["metagraphs"]) == 2
    # Sorted by name (mg-a before mg-z).
    assert [m["name"] for m in data["metagraphs"]] == ["mg-a", "mg-z"]
    sample = data["metagraphs"][0]
    assert set(sample.keys()) == {
        "name", "metagraph_id", "schema_name",
        "contained_graphs_count", "metaedges_count",
        "metahyperedges_count", "intergraph_edges_count",
        "intergraph_hyperedges_count",
        "_state_version", "path",
    }
