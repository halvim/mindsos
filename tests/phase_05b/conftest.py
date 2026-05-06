"""Phase 05b test fixtures (mirror Phase 05a conftest)."""

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
    """Autouse: every Phase 05b test gets a fresh ``MINDSOS_STATE_DIR``."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    monkeypatch.setenv("MINDSOS_STATE_DIR", str(state_dir))
    return state_dir


@pytest.fixture
def mg_with_two_graphs():
    """Build a Metagraph + 2 graphs (lexicon + concepts roles) ready for IntergraphEdge tests."""
    from mindsos_core import Graph, Metagraph

    mg = Metagraph(name="m1")
    g_lex = Graph(name="lex", role="lexicon")
    g_cpt = Graph(name="cpt", role="concepts")
    mg.add_graph(g_lex)
    mg.add_graph(g_cpt)
    n_lex = g_lex.add_node("cat", type_name="Word")
    n_cpt = g_cpt.add_node("Cat#1", type_name="Concept")
    return {
        "mg": mg,
        "g_lex": g_lex,
        "g_cpt": g_cpt,
        "n_lex": n_lex,
        "n_cpt": n_cpt,
    }
