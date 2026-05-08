"""Phase 05d test fixtures (mirror Phase 05c conftest)."""

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
    """Autouse: every Phase 05d test gets a fresh ``MINDSOS_STATE_DIR``."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    monkeypatch.setenv("MINDSOS_STATE_DIR", str(state_dir))
    return state_dir


@pytest.fixture
def mg_for_metaedge():
    """Build a Metagraph + 2 graphs (ontology + lexicon roles).

    Suitable for binary metaedge tests; metaedge type is supplied
    per-test.
    """
    from mindsos_core import Graph, Metagraph

    mg = Metagraph(name="mg")
    g_a = Graph(name="ont", role="ontology")
    g_b = Graph(name="lex", role="lexicon")
    mg.add_graph(g_a)
    mg.add_graph(g_b)
    return {"mg": mg, "g_a": g_a, "g_b": g_b}
