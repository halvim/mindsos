"""Tests for ``mindsos schema add-node-type``."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app


runner = CliRunner()


def _create(schema_name: str, *extra: str) -> None:
    res = runner.invoke(app, ["schema", "create", "--name", schema_name, *extra])
    assert res.exit_code == 0, res.output


def test_add_node_type_happy_path(_isolated_state_dir):
    _create("s1")
    res = runner.invoke(
        app,
        [
            "schema",
            "add-node-type",
            "--schema",
            "s1",
            "--type-name",
            "Person",
            "--json",
        ],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["name"] == "Person"
    assert data["property_types"] == {}


def test_add_node_type_with_prop_types(_isolated_state_dir):
    _create("s1")
    res = runner.invoke(
        app,
        [
            "schema",
            "add-node-type",
            "--schema",
            "s1",
            "--type-name",
            "Person",
            "--prop-type",
            "age=int",
            "--prop-type",
            "name=string",
            "--prop-type",
            "tags=list[string]",
            "--json",
        ],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["property_types"] == {
        "age": "int",
        "name": "string",
        "tags": "list[string]",
    }


def test_add_node_type_with_description(_isolated_state_dir):
    _create("s1")
    res = runner.invoke(
        app,
        [
            "schema",
            "add-node-type",
            "--schema",
            "s1",
            "--type-name",
            "Person",
            "--description",
            "A natural person.",
            "--json",
        ],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["description"] == "A natural person."


def test_add_node_type_duplicate_exits_1(_isolated_state_dir):
    _create("s1")
    runner.invoke(app, ["schema", "add-node-type", "--schema", "s1", "--type-name", "Person"])
    res = runner.invoke(
        app, ["schema", "add-node-type", "--schema", "s1", "--type-name", "Person"]
    )
    assert res.exit_code == 1
    assert "UnknownTypeError" in res.output or "UnknownTypeError" in (res.stderr or "")


def test_add_node_type_unrecognised_vocab_exits_2(_isolated_state_dir):
    _create("s1")
    res = runner.invoke(
        app,
        [
            "schema",
            "add-node-type",
            "--schema",
            "s1",
            "--type-name",
            "Person",
            "--prop-type",
            "age=integer",  # not in vocab; should be 'int'
        ],
    )
    assert res.exit_code == 2


def test_add_node_type_empty_prop_type_key_exits_2(_isolated_state_dir):
    _create("s1")
    res = runner.invoke(
        app,
        [
            "schema",
            "add-node-type",
            "--schema",
            "s1",
            "--type-name",
            "Person",
            "--prop-type",
            "=int",
        ],
    )
    assert res.exit_code == 2


def test_add_node_type_missing_schema_exits_1(_isolated_state_dir):
    res = runner.invoke(
        app,
        [
            "schema",
            "add-node-type",
            "--schema",
            "ghost",
            "--type-name",
            "Person",
        ],
    )
    assert res.exit_code == 1
    assert "not found" in res.output or "not found" in (res.stderr or "")
