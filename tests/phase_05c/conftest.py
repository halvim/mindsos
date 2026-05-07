"""Phase 05c test fixtures (mirror Phase 05b conftest + n-ary fixture)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tests._shared import tomli_shim  # noqa: F401 — Python 3.10/3.11 tomllib alias
from tests._shared.cli import _run_cli


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


@pytest.fixture
def repo_root() -> Path:
    return _repo_root()


@pytest.fixture
def cli() -> Callable[..., Any]:
    return _run_cli


@pytest.fixture(autouse=True)
def _isolated_state_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Autouse: every Phase 05c test gets a fresh ``MINDSOS_STATE_DIR``."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    monkeypatch.setenv("MINDSOS_STATE_DIR", str(state_dir))
    return state_dir


@pytest.fixture
def mg_for_hyperedge():
    """Build a Metagraph + 3 graphs (word + letter1 + letter2 roles) for n-ary tests.

    Provides a 1-anchor / 3-member fixture — the cat=c+a+t case shape.
    """
    from mindsos_core import Graph, Metagraph

    mg = Metagraph(name="mh")
    g_word = Graph(name="word", role="word")
    g_letter = Graph(name="letter", role="letter")
    mg.add_graph(g_word)
    mg.add_graph(g_letter)
    n_cat = g_word.add_node("cat", type_name="Word", node_id="cat")
    n_c = g_letter.add_node("c", type_name="Letter", node_id="c")
    n_a = g_letter.add_node("a", type_name="Letter", node_id="a")
    n_t = g_letter.add_node("t", type_name="Letter", node_id="t")
    return {
        "mg": mg,
        "g_word": g_word,
        "g_letter": g_letter,
        "n_cat": n_cat,
        "n_c": n_c,
        "n_a": n_a,
        "n_t": n_t,
    }
