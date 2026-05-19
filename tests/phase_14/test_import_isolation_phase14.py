"""Phase 14 — extends Phase 12 PB-18 / Phase 13 import-isolation invariant.

``mindsos_knowledge`` (including the Phase 14 additions: knowledge_layer,
metagraph_view, bootstrap) imports nothing from ``mindsos_cli`` or
``mindsos_server`` (latter doesn't exist yet — parametrised over a
forbidden-roots list).

``mindsos_core`` is NOT forbidden — downward import from L2 → L1 is
permitted per ADR-0010.
"""

from __future__ import annotations

import ast
import os

import pytest

import mindsos_knowledge


_FORBIDDEN_ROOTS = ("mindsos_cli", "mindsos_server")


def _iter_kl_py_files() -> list[str]:
    pkg_dir = os.path.dirname(mindsos_knowledge.__file__)
    out: list[str] = []
    for root, _, files in os.walk(pkg_dir):
        for f in files:
            if f.endswith(".py"):
                out.append(os.path.join(root, f))
    return out


@pytest.mark.parametrize("py_file", _iter_kl_py_files())
def test_no_forbidden_imports(py_file: str) -> None:
    with open(py_file, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=py_file)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                assert root not in _FORBIDDEN_ROOTS, (
                    f"{py_file} imports forbidden root {root!r} (ADR-0010)."
                )
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            root = mod.split(".", 1)[0]
            assert root not in _FORBIDDEN_ROOTS, (
                f"{py_file} from-imports forbidden root {root!r} (ADR-0010)."
            )


def test_phase_14_modules_covered() -> None:
    """Smoke: confirm Phase 14's 3 new module files are in the iteration."""
    files = _iter_kl_py_files()
    basenames = {os.path.basename(f) for f in files}
    assert "knowledge_layer.py" in basenames
    assert "metagraph_view.py" in basenames
    assert "bootstrap.py" in basenames
