"""Phase 16 — extends Phase 15a import-isolation invariant.

The Phase 16 NEW modules (`mindsos_admin/similarity.py` +
`_content_hash.py` + `exceptions.py`) must NOT import
``mindsos_cli`` or ``mindsos_server`` (latter doesn't exist yet —
parametrised over a forbidden-roots list per ADR-0010).

``mindsos_core`` and ``mindsos_knowledge`` imports remain permitted
(downward; ADR-0010). ``mindsos_admin``'s own internal imports
are permitted (intra-package).
"""

from __future__ import annotations

import ast
import os

import pytest


_FORBIDDEN_ROOTS = ("mindsos_cli", "mindsos_server")

# Phase 16 NEW modules to audit (sentinel paths from sentinel_paths.py).
_PHASE_16_NEW_MODULES = (
    "mindsos_admin/similarity.py",
    "mindsos_admin/_content_hash.py",
    "mindsos_admin/exceptions.py",
)


def _module_path(rel: str) -> str:
    repo_root = os.environ.get("MINDSOS_REPO_ROOT", os.getcwd())
    return os.path.join(repo_root, rel)


def _top_level_imports(module_file: str) -> set[str]:
    """Parse the AST and return the set of top-level imported module-roots."""
    with open(module_file, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=module_file)
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".", 1)[0])
    return roots


@pytest.mark.parametrize("rel_path", _PHASE_16_NEW_MODULES)
def test_phase_16_module_does_not_import_forbidden_roots(rel_path: str) -> None:
    """Each Phase 16 NEW module's AST is free of forbidden top-level imports."""
    full = _module_path(rel_path)
    assert os.path.exists(full), f"sentinel path missing: {rel_path}"
    imported = _top_level_imports(full)
    for forbidden in _FORBIDDEN_ROOTS:
        assert forbidden not in imported, (
            f"{rel_path} imports forbidden root {forbidden!r}; "
            f"ADR-0010 layer-isolation violated."
        )


def test_similarity_imports_admin_internal_helpers() -> None:
    """Sanity-check: similarity.py imports its `_content_hash` + `exceptions` siblings."""
    full = _module_path("mindsos_admin/similarity.py")
    imported = _top_level_imports(full)
    # The relative imports show up under the package root.
    # ast picks up `from ._content_hash import ...` with module="_content_hash".
    assert "_content_hash" in imported or "mindsos_admin" in imported
    assert "exceptions" in imported or "mindsos_admin" in imported
