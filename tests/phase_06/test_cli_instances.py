"""Phase 06 CLI subprocess tests — 4 verbs × pass / override /
materialise / error paths. Container-only (sandbox skips when
``tomllib`` is missing — sandbox-Python 3.10 doesn't have it; container-
Python 3.12 does).

Round-7 P53 A exit codes:
  0  success
  1  invariant violation
  2  resource-not-found
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Callable

import pytest

# Sandbox skip — confirm_phase.py imports tomllib (Python 3.11+). When
# the sandbox runs on 3.10, every subprocess CLI invocation fails on
# import. Skip in that case so the test pass count remains green; in-
# container tester run picks these up.
SANDBOX_SKIP = sys.version_info < (3, 11)
pytestmark = pytest.mark.skipif(
    SANDBOX_SKIP,
    reason="CLI subprocess tests require Python 3.11+ (tomllib); "
    "tester runs in-container per Phase 06 row §Tests.",
)

# Import subprocess helper at module level once the skipif gate passes.
if not SANDBOX_SKIP:
    from tests._shared.cli import _run_cli  # noqa: E402


@pytest.fixture
def cli() -> Callable:
    return _run_cli


@pytest.fixture(autouse=True)
def _isolated_state_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    monkeypatch.setenv("MINDSOS_STATE_DIR", str(state_dir))
    return state_dir


@pytest.fixture
def populated_mg(cli) -> dict:
    """Create a metagraph with one graph and two nodes via CLI; return
    the names/ids."""
    # Create metagraph.
    r = cli("metagraph", "create", "--name", "MG_T")
    assert r.returncode == 0, r.stderr
    # Create a graph attached to the metagraph.
    r = cli(
        "graph",
        "create",
        "--name",
        "G_T",
        "--metagraph",
        "MG_T",
        "--role",
        "ontology",
    )
    assert r.returncode == 0, r.stderr
    # Add two nodes.
    r1 = cli(
        "graph",
        "add-node",
        "--name",
        "G_T",
        "--value",
        "alice",
        "--type-name",
        "Person",
        "--json",
    )
    assert r1.returncode == 0, r1.stderr
    node1 = json.loads(r1.stdout)
    r2 = cli(
        "graph",
        "add-node",
        "--name",
        "G_T",
        "--value",
        "bob",
        "--type-name",
        "Person",
        "--json",
    )
    assert r2.returncode == 0, r2.stderr
    node2 = json.loads(r2.stdout)
    # Add an edge.
    re = cli(
        "graph",
        "add-edge",
        "--name",
        "G_T",
        "--source-id",
        node1["node_id"],
        "--target-id",
        node2["node_id"],
        "--type-name",
        "KNOWS",
        "--json",
    )
    assert re.returncode == 0, re.stderr
    edge = json.loads(re.stdout)
    return {"node1": node1, "node2": node2, "edge": edge}


# ── instantiate-node ────────────────────────────────────────────────────────


def test_instantiate_node_pass(cli, populated_mg):
    r = cli(
        "instances",
        "instantiate-node",
        "--metagraph",
        "MG_T",
        "--template-id",
        populated_mg["node1"]["node_id"],
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["kind"] == "node"
    assert payload["template_id"] == populated_mg["node1"]["node_id"]


def test_instantiate_node_with_override_materialise(cli, populated_mg):
    r = cli(
        "instances",
        "instantiate-node",
        "--metagraph",
        "MG_T",
        "--template-id",
        populated_mg["node1"]["node_id"],
        "--override",
        "age=31",
        "--materialise",
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["value"] == "alice"
    assert payload["properties"]["age"] == 31


def test_instantiate_node_unknown_template_exits_2(cli, populated_mg):
    r = cli(
        "instances",
        "instantiate-node",
        "--metagraph",
        "MG_T",
        "--template-id",
        "nonexistent",
    )
    assert r.returncode == 2
    assert "IdentityError" in r.stderr


def test_instantiate_node_unknown_metagraph_exits_2(cli):
    r = cli(
        "instances",
        "instantiate-node",
        "--metagraph",
        "NO_SUCH_MG",
        "--template-id",
        "anything",
    )
    assert r.returncode == 2


def test_instantiate_node_invalid_override_exits_1(cli, populated_mg):
    r = cli(
        "instances",
        "instantiate-node",
        "--metagraph",
        "MG_T",
        "--template-id",
        populated_mg["node1"]["node_id"],
        "--override",
        "id=\"spoofed\"",
    )
    assert r.returncode == 1
    assert "OverrideScopeError" in r.stderr


# ── instantiate-edge ────────────────────────────────────────────────────────


def test_instantiate_edge_pass(cli, populated_mg):
    r = cli(
        "instances",
        "instantiate-edge",
        "--metagraph",
        "MG_T",
        "--template-id",
        populated_mg["edge"]["edge_id"],
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["kind"] == "edge"


def test_instantiate_edge_with_label_override_materialise(cli, populated_mg):
    r = cli(
        "instances",
        "instantiate-edge",
        "--metagraph",
        "MG_T",
        "--template-id",
        populated_mg["edge"]["edge_id"],
        "--override",
        'label="custom"',
        "--materialise",
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["label"] == "custom"


def test_instantiate_edge_type_name_override_rejected(cli, populated_mg):
    r = cli(
        "instances",
        "instantiate-edge",
        "--metagraph",
        "MG_T",
        "--template-id",
        populated_mg["edge"]["edge_id"],
        "--override",
        'type_name="HATES"',
    )
    assert r.returncode == 1
    assert "OverrideScopeError" in r.stderr


# ── compose ─────────────────────────────────────────────────────────────────


def test_compose_with_member_specs(cli, populated_mg):
    spec_a = json.dumps(
        {
            "kind": "node",
            "template_id": populated_mg["node1"]["node_id"],
            "overrides": {"age": 99},
        }
    )
    spec_b = json.dumps(
        {
            "kind": "edge",
            "template_id": populated_mg["edge"]["edge_id"],
        }
    )
    r = cli(
        "instances",
        "compose",
        "--metagraph",
        "MG_T",
        "--member-spec",
        spec_a,
        "--member-spec",
        spec_b,
        "--bundle-override",
        'tag="demo"',
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["kind"] == "composite"
    assert payload["bundle_overrides"]["tag"] == "demo"
    assert len(payload["member_ids"]) == 2


def test_compose_materialise(cli, populated_mg):
    spec = json.dumps(
        {
            "kind": "node",
            "template_id": populated_mg["node1"]["node_id"],
        }
    )
    r = cli(
        "instances",
        "compose",
        "--metagraph",
        "MG_T",
        "--member-spec",
        spec,
        "--materialise",
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["kind"] == "composite"
    assert len(payload["members"]) == 1


def test_compose_invalid_member_spec_exits_1(cli, populated_mg):
    r = cli(
        "instances",
        "compose",
        "--metagraph",
        "MG_T",
        "--member-spec",
        "{not_json}",
    )
    assert r.returncode == 1


def test_compose_unknown_kind_exits_1(cli, populated_mg):
    spec = json.dumps(
        {
            "kind": "subgraph",  # not allowed in compose verb
            "template_id": "any",
        }
    )
    r = cli(
        "instances",
        "compose",
        "--metagraph",
        "MG_T",
        "--member-spec",
        spec,
    )
    assert r.returncode == 1
