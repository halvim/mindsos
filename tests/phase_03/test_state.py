"""Direct unit tests for ``mindsos_cli/state.py``."""

from __future__ import annotations

import json
import os

import pytest

from mindsos_cli import state as state_mod


def test_state_dir_uses_env_var_when_set(_isolated_state_dir):
    """state_dir() returns $MINDSOS_STATE_DIR when set."""
    assert state_mod.state_dir() == _isolated_state_dir


def test_state_file_path_validates_name():
    """Bad names raise ValueError; good names produce a Path under state_dir."""
    p = state_mod.state_file_path("foo")
    assert p.name == "graph-foo.json"

    with pytest.raises(ValueError):
        state_mod.state_file_path("foo/bar")  # path traversal
    with pytest.raises(ValueError):
        state_mod.state_file_path("")  # empty
    with pytest.raises(ValueError):
        state_mod.state_file_path("-leading-dash")  # leading non-alnum


def test_save_and_load_round_trip(_isolated_state_dir):
    state = {
        "_state_version": 1,
        "graph_id": "abc",
        "name": "g",
        "role": None,
        "nodes": [],
        "edges": [],
        "hyperedges": [],
    }
    state_mod.save_graph_state("g", state)
    loaded = state_mod.load_graph_state("g")
    assert loaded == state


def test_save_is_atomic(_isolated_state_dir):
    """The .tmp suffix is the staging path; replaced atomically onto canonical."""
    state = {"_state_version": 1, "graph_id": "x", "name": "g",
             "role": None, "nodes": [], "edges": [], "hyperedges": []}
    state_mod.save_graph_state("g", state)
    path = state_mod.state_file_path("g")
    tmp = path.with_suffix(path.suffix + ".tmp")
    assert path.exists()
    assert not tmp.exists()  # tmp was replaced; no leftover


def test_load_missing_file_raises_filenotfound(_isolated_state_dir):
    with pytest.raises(FileNotFoundError):
        state_mod.load_graph_state("does-not-exist")


def test_load_corrupt_json_raises_runtime(_isolated_state_dir):
    path = state_mod.state_file_path("g")
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(RuntimeError, match="not valid JSON"):
        state_mod.load_graph_state("g")


def test_load_missing_state_version_field_raises(_isolated_state_dir):
    path = state_mod.state_file_path("g")
    path.write_text(json.dumps({"name": "g"}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="missing required field"):
        state_mod.load_graph_state("g")


def test_load_future_state_version_rejected(_isolated_state_dir):
    path = state_mod.state_file_path("g")
    path.write_text(
        json.dumps({"_state_version": 99, "name": "g"}), encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="this CLI supports v1"):
        state_mod.load_graph_state("g")


def test_iter_state_files_sorted(_isolated_state_dir):
    state_mod.save_graph_state("zebra", {"_state_version": 1, "graph_id": "z",
                                          "name": "zebra", "role": None,
                                          "nodes": [], "edges": [], "hyperedges": []})
    state_mod.save_graph_state("apple", {"_state_version": 1, "graph_id": "a",
                                          "name": "apple", "role": None,
                                          "nodes": [], "edges": [], "hyperedges": []})
    paths = list(state_mod.iter_state_files())
    names = [p.stem for p in paths]
    assert names == sorted(names)
    assert names == ["graph-apple", "graph-zebra"]


def test_delete_state_file(_isolated_state_dir):
    state_mod.save_graph_state("g", {"_state_version": 1, "graph_id": "x",
                                      "name": "g", "role": None,
                                      "nodes": [], "edges": [], "hyperedges": []})
    assert state_mod.state_file_path("g").exists()
    state_mod.delete_state_file("g")
    assert not state_mod.state_file_path("g").exists()
    with pytest.raises(FileNotFoundError):
        state_mod.delete_state_file("g")  # second delete
