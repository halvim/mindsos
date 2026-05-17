"""Tier 7 — Import isolation regression (PB-18).

`mindsos_knowledge.*` must NOT import from `mindsos_cli` or
`mindsos_server`. ADR-0010 forbids L2 importing from L0; ADR-0014
keeps L1 Core-only-imports. Phase 25 (SessionProtocol seam) ships
an explicit parity test for `mindsos_knowledge ⇏ mindsos_server` —
Phase 12 establishes the discipline from day one via this AST walk.

`mindsos_core` is NOT forbidden (downward import L2 → L1 is allowed).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


_FORBIDDEN_ROOTS = ("mindsos_cli", "mindsos_server")
_MINDSOS_KNOWLEDGE_DIR = (
    Path(__file__).resolve().parents[2] / "mindsos_knowledge"
)


def _imports_in(path: Path) -> set[str]:
    """Return the set of top-level module names imported by `path`."""
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
    return names


_PY_FILES = sorted(_MINDSOS_KNOWLEDGE_DIR.glob("*.py"))


@pytest.mark.parametrize(
    "py_file", _PY_FILES, ids=[p.name for p in _PY_FILES]
)
def test_no_forbidden_imports(py_file: Path) -> None:
    """`mindsos_knowledge` modules import nothing from forbidden roots."""
    imports = _imports_in(py_file)
    for forbidden in _FORBIDDEN_ROOTS:
        assert forbidden not in imports, (
            f"{py_file.name} imports forbidden root {forbidden!r}; "
            f"L2 must not depend on {forbidden}."
        )
