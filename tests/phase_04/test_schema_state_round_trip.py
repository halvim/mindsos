"""Round-trip tests for the ``schema-<name>.json`` state file.

Guarantees that a schema written by ``mindsos schema create`` +
``add-node-type`` + ``add-edge-type`` deserialises into a structurally
identical ``Schema`` (in particular: the 8 PropertyType values survive
the JSON round trip, ``allowed_sources`` / ``allowed_targets`` round-trip
as frozensets via sorted-list serialization, and ``strict`` is preserved).
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_cli.app import app
from mindsos_cli import state as state_mod
from mindsos_cli.commands.schema import _state_to_schema


runner = CliRunner()


def test_schema_round_trip_all_8_property_types(_isolated_state_dir):
    runner.invoke(app, ["schema", "create", "--name", "s1", "--strict"])
    runner.invoke(
        app,
        [
            "schema",
            "add-node-type",
            "--schema",
            "s1",
            "--type-name",
            "Allsorts",
            "--prop-type",
            "s=string",
            "--prop-type",
            "i=int",
            "--prop-type",
            "f=float",
            "--prop-type",
            "b=bool",
            "--prop-type",
            "ls=list[string]",
            "--prop-type",
            "li=list[int]",
            "--prop-type",
            "lf=list[float]",
            "--prop-type",
            "lb=list[bool]",
        ],
    )
    state = state_mod.load_schema_state("s1")
    schema = _state_to_schema(state)
    assert schema.strict is True
    nt = schema.require_node_type("Allsorts")
    expected = {
        "s": "string",
        "i": "int",
        "f": "float",
        "b": "bool",
        "ls": "list[string]",
        "li": "list[int]",
        "lf": "list[float]",
        "lb": "list[bool]",
    }
    assert {k: v.value for k, v in nt.property_types.items()} == expected


def test_schema_state_file_is_byte_stable_for_sorted_inputs(_isolated_state_dir):
    """Two schemas with the same content (added in different order) produce
    identical JSON on disk because the writer sorts node_types / edge_types
    by name and ``allowed_sources`` / ``allowed_targets`` sort on save."""
    runner.invoke(app, ["schema", "create", "--name", "a"])
    runner.invoke(
        app, ["schema", "add-node-type", "--schema", "a", "--type-name", "Org"]
    )
    runner.invoke(
        app, ["schema", "add-node-type", "--schema", "a", "--type-name", "Person"]
    )
    runner.invoke(app, ["schema", "create", "--name", "b"])
    runner.invoke(
        app, ["schema", "add-node-type", "--schema", "b", "--type-name", "Person"]
    )
    runner.invoke(
        app, ["schema", "add-node-type", "--schema", "b", "--type-name", "Org"]
    )
    a_raw = json.loads((_isolated_state_dir / "schema-a.json").read_text(encoding="utf-8"))
    b_raw = json.loads((_isolated_state_dir / "schema-b.json").read_text(encoding="utf-8"))
    a_raw["name"] = "X"
    b_raw["name"] = "X"
    assert a_raw == b_raw


def test_edge_type_allowed_source_target_sorted_on_save(_isolated_state_dir):
    runner.invoke(app, ["schema", "create", "--name", "s1"])
    for nt in ("Z_Type", "A_Type", "M_Type"):
        runner.invoke(
            app,
            ["schema", "add-node-type", "--schema", "s1", "--type-name", nt],
        )
    runner.invoke(
        app,
        [
            "schema",
            "add-edge-type",
            "--schema",
            "s1",
            "--type-name",
            "REL",
            "--allowed-source",
            "Z_Type",
            "--allowed-source",
            "A_Type",
            "--allowed-source",
            "M_Type",
        ],
    )
    raw = json.loads((_isolated_state_dir / "schema-s1.json").read_text(encoding="utf-8"))
    et = raw["edge_types"][0]
    assert et["allowed_sources"] == ["A_Type", "M_Type", "Z_Type"]
