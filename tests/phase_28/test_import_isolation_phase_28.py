"""Phase 28 — import-isolation discipline for mindsos_capacity."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import mindsos_capacity

_PKG_DIR = Path(mindsos_capacity.__file__).resolve().parent


def _module_names_imported_by(path: Path):
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
    return names


_SOURCE_FILES = sorted(p for p in _PKG_DIR.glob("*.py") if not p.name.startswith("_"))


@pytest.mark.parametrize("source_file", _SOURCE_FILES, ids=lambda p: p.name)
@pytest.mark.parametrize("forbidden", ["mindsos_server", "mindsos_knowledge"])
def test_no_upward_import(source_file, forbidden):
    imported = _module_names_imported_by(source_file)
    assert forbidden not in imported, (
        f"{source_file.name} imports forbidden module {forbidden!r}; "
        f"this violates layer isolation. Imports found: {sorted(imported)!r}."
    )
