"""Phase 15a — extends Phase 12 PB-18 / Phase 14 import-isolation invariant.

``mindsos_admin`` (NEW top-level Phase 15a package) imports nothing
from ``mindsos_cli`` or ``mindsos_server`` (latter doesn't exist yet
— parametrised over a forbidden-roots list per ADR-0010).

``mindsos_core`` and ``mindsos_knowledge`` are NOT forbidden —
downward imports from admin → L2 → L1 are permitted per ADR-0010 and
expected per Phase 15a PB-14 (importers auto-ensure their target
role-graph via `mindsos_knowledge.bootstrap.ensure_global_role_graph`).
"""

from __future__ import annotations

import ast
import os

import pytest

import mindsos_admin


_FORBIDDEN_ROOTS = ("mindsos_cli", "mindsos_server")


def _iter_admin_py_files() -> list[str]:
    pkg_dir = os.path.dirname(mindsos_admin.__file__)
    out: list[str] = []
    for root, _, files in os.walk(pkg_dir):
        for f in files:
            if f.endswith(".py"):
                out.append(os.path.join(root, f))
    return out


@pytest.mark.parametrize("py_file", _iter_admin_py_files())
def test_no_forbidden_imports(py_file: str) -> None:
    """ADR-0010 — mindsos_admin no mindsos_cli / mindsos_server imports."""
    with open(py_file, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=py_file)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".", 1)[0]
                assert top not in _FORBIDDEN_ROOTS, (
                    f"{py_file}: forbidden `import {alias.name}`"
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            top = module.split(".", 1)[0]
            assert top not in _FORBIDDEN_ROOTS, (
                f"{py_file}: forbidden `from {module} import ...`"
            )


def test_admin_package_imports_resolve() -> None:
    """Smoke: top-level mindsos_admin imports work."""
    from mindsos_admin import (
        DolceImporter,
        FrameNetImporter,
        ImporterProtocol,
        ImportResult,
        OewnImporter,
        bootstrap_global,
    )

    assert callable(bootstrap_global)
    for cls in (DolceImporter, OewnImporter, FrameNetImporter):
        assert hasattr(cls, "target_roles")
    assert ImportResult.__name__ == "ImportResult"
    assert ImporterProtocol.__name__ == "ImporterProtocol"
