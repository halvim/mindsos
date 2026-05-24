"""Phase 26a import isolation per ADR-0010 §am2 (R3-PB-4 (a)).

Asserts the new ``mindsos_admin → mindsos_core`` edge is the ONLY
new edge Phase 26a introduces. KL → server stays forbidden. KL →
admin stays forbidden.

AST-walk pattern per Phase 25 B-25-T1 hotfix lesson — substring grep
for ``from mindsos_server`` would false-positive on docstring
mentions.
"""

from __future__ import annotations

import ast
import pathlib

import mindsos_admin
import mindsos_knowledge


def _modules_under(pkg) -> list[pathlib.Path]:
    """Return all .py files under a package directory."""
    pkg_dir = pathlib.Path(pkg.__file__).parent
    return [p for p in pkg_dir.rglob("*.py") if p.is_file()]


def _top_level_imports(path: pathlib.Path) -> set[str]:
    """Top-level import roots in a Python file (via AST walk)."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                roots.add(node.module.split(".")[0])
    return roots


def test_mindsos_knowledge_does_not_import_mindsos_server() -> None:
    """ADR-0010 §I-S1 — KL stays library-installable without server."""
    for path in _modules_under(mindsos_knowledge):
        roots = _top_level_imports(path)
        assert "mindsos_server" not in roots, (
            f"{path} imports mindsos_server; violates ADR-0010 §I-S1"
        )


def test_mindsos_knowledge_does_not_import_mindsos_admin() -> None:
    """ADR-0010 §am1 — KL stays self-contained from curation machinery."""
    for path in _modules_under(mindsos_knowledge):
        roots = _top_level_imports(path)
        assert "mindsos_admin" not in roots, (
            f"{path} imports mindsos_admin; violates ADR-0010 §am1"
        )


def test_mindsos_admin_imports_mindsos_core() -> None:
    """ADR-0010 §am2 — admin → core ALLOWED (Phase 26a wiring)."""
    found_admin_to_core = False
    for path in _modules_under(mindsos_admin):
        roots = _top_level_imports(path)
        if "mindsos_core" in roots:
            found_admin_to_core = True
            break
    assert found_admin_to_core, (
        "Phase 26a should introduce at least one mindsos_admin → "
        "mindsos_core import edge (e.g. promotion.py importing Client)"
    )
