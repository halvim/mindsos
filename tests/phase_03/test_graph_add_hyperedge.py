"""Tests for ``mindsos graph add-hyperedge``.

Phase 04-v2 — every invocation now passes ``--type <REL_TYPE>`` (per
ADR-0017 / MC-2). Pre-04-v2 invocations that omitted ``--type`` no
longer parse (Typer-default exit 2). Phase 03 tests aligned with the
current contract per Phase 04 §1 ("Breaking changes between phases
allowed; documented in version notes") and B-04-prev precedent.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def _setup_three_nodes(_isolated_state_dir, name="g1"):
    runner.invoke(app, ["graph", "create", "--name", name])
    for nid in ("a", "b", "c"):
        runner.invoke(
            app,
            ["graph", "add-node", nid, "--name", name, "--type", "T",
             "--node-id", nid],
        )


def test_add_hyperedge_happy_path(_isolated_state_dir):
    _setup_three_nodes(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1", "--type", "TRIO",
         "--member", "a", "--member", "b", "--member", "c",
         "--label", "trio", "--json"],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["member_ids"] == ["a", "b", "c"]
    assert data["label"] == "trio"
    assert data["type_name"] == "TRIO"  # Phase 04-v2.


def test_add_hyperedge_empty_members_exits_1(_isolated_state_dir):
    """Phase 04-v2: empty members → SchemaError on Graph.add_hyperedge → exit 1.

    --type is required so the test now passes --type but omits --member
    deliberately to exercise the empty-members rejection path.
    """
    _setup_three_nodes(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1", "--type", "TRIO"],
    )
    # No --member flag → empty list → SchemaError on add_hyperedge → exit 1
    assert res.exit_code == 1
    assert "SchemaError" in (res.output + (res.stderr or ""))


def test_add_hyperedge_canonicalises_member_order(_isolated_state_dir):
    """member_ids in JSON output is sorted regardless of input order."""
    _setup_three_nodes(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1", "--type", "TRIO",
         "--member", "c", "--member", "a", "--member", "b",
         "--json"],
    )
    data = json.loads(res.output)
    assert data["member_ids"] == ["a", "b", "c"]  # sorted, not c-a-b


def test_add_hyperedge_unknown_member_exits_1(_isolated_state_dir):
    _setup_three_nodes(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1", "--type", "TRIO",
         "--member", "a", "--member", "missing"],
    )
    assert res.exit_code == 1
    assert "IdentityError" in (res.output + (res.stderr or ""))


def test_add_hyperedge_explicit_id(_isolated_state_dir):
    _setup_three_nodes(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1", "--type", "TRIO",
         "--member", "a", "--member", "b",
         "--hyperedge-id", "he-1", "--json"],
    )
    data = json.loads(res.output)
    assert data["edge_id"] == "he-1"


def test_add_hyperedge_missing_type_exits_2(_isolated_state_dir):
    """Phase 04-v2 — --type is required; omitting it = Typer exit 2."""
    _setup_three_nodes(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1",
         "--member", "a", "--member", "b"],
    )
    assert res.exit_code == 2  # Typer-default for missing required option.


def test_add_hyperedge_invalid_cypher_type_exits_1(_isolated_state_dir):
    """Phase 04-v2 — cypher rel-type regex enforced on --type."""
    _setup_three_nodes(_isolated_state_dir)
    res = runner.invoke(
        app,
        ["graph", "add-hyperedge", "--name", "g1", "--type", "lower-case",
         "--member", "a", "--member", "b"],
    )
    assert res.exit_code == 1
    assert "CypherError" in (res.output + (res.stderr or ""))
