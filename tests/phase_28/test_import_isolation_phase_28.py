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


#: The guard's DOMAIN, stated rather than implied (RULES §12.3 — a
#: quantified claim states its domain). It was a flat ``glob("*.py")``,
#: which silently exempted every subpackage; found 2026-08-16 when
#: ``llm/`` landed (coordination §87 T-F11) and would otherwise have been
#: the only architecture guard that could not see it.
#:
#: ``builtins/`` is EXCLUDED, and that is a decision, not an oversight:
#: L3 builtin bodies reach L2 through **function-local** imports by
#: design (``policy_lookup_v0`` says so at its import site — "local: L3
#: declares no L2 dep"), and this walker is an AST walk that sees nested
#: imports too, so including them would redden six shipped files. The
#: rule this guard enforces is about MODULE-level layering.
_ISOLATED_SUBPACKAGES = ("llm",)

_SOURCE_FILES = sorted(
    [p for p in _PKG_DIR.glob("*.py") if not p.name.startswith("_")]
    + [
        p
        for sub in _ISOLATED_SUBPACKAGES
        for p in (_PKG_DIR / sub).glob("*.py")
        if not p.name.startswith("_")
    ]
)


@pytest.mark.parametrize("source_file", _SOURCE_FILES, ids=lambda p: str(p.relative_to(_PKG_DIR)))
@pytest.mark.parametrize("forbidden", ["mindsos_server", "mindsos_knowledge"])
def test_no_upward_import(source_file, forbidden):
    imported = _module_names_imported_by(source_file)
    assert forbidden not in imported, (
        f"{source_file.name} imports forbidden module {forbidden!r}; "
        f"this violates layer isolation. Imports found: {sorted(imported)!r}."
    )
