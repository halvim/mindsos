"""Phase 46 — L3 must not import the new L4 package (ADR-0169 / PB-8).

The ``TierEnum`` lives in ``mindsos_capacity`` precisely so the L4
Executor + signal-triage thread import it downward; the reverse (L3
importing ``mindsos_intelligence``) is a layering violation. This
sentinel pins that invariant the moment the L4 package exists.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import mindsos_capacity

_PKG_DIR = Path(mindsos_capacity.__file__).resolve().parent
_SOURCE_FILES = sorted(p for p in _PKG_DIR.glob("*.py") if not p.name.startswith("_"))


def _module_names_imported_by(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
    return names


@pytest.mark.parametrize("source_file", _SOURCE_FILES, ids=lambda p: p.name)
def test_capacity_does_not_import_intelligence(source_file):
    imported = _module_names_imported_by(source_file)
    assert "mindsos_intelligence" not in imported, (
        f"{source_file.name} imports mindsos_intelligence; L3 must not import "
        f"L4 (ADR-0169). Imports found: {sorted(imported)!r}."
    )
