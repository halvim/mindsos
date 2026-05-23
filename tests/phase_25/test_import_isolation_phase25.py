"""
ADR-0010 §I-S1 — :mod:`mindsos_knowledge` MUST NOT import
:mod:`mindsos_server` at module load.

AST-based scan of the KL package — any real ``ImportFrom`` or
``Import`` node referencing :mod:`mindsos_server` fails this test.
Docstring mentions of the forbidden import statement (used for
documentation) are correctly ignored because they're not real imports
in the AST.

Phase 25 B-25-T1 hotfix: the original Phase 25 implementation used a
literal substring scan ("from mindsos_server" in stripped) which
matched the documentation docstring of
``mindsos_knowledge/types.py`` (false positive). AST-based scanning
is the load-bearing fix.
"""

from __future__ import annotations

import ast
from pathlib import Path

import mindsos_knowledge


def _kl_package_root() -> Path:
    return Path(mindsos_knowledge.__file__).parent


def _scan_for_imports(
    py: Path, forbidden_prefix: str,
) -> list[tuple[Path, int, str]]:
    """Return real (ImportFrom + Import) AST nodes matching the prefix."""
    tree = ast.parse(py.read_text(), filename=str(py))
    offenders: list[tuple[Path, int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith(forbidden_prefix):
                offenders.append((py, node.lineno, node.module))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(forbidden_prefix):
                    offenders.append((py, node.lineno, alias.name))
    return offenders


def test_no_mindsos_server_imports_in_mindsos_knowledge() -> None:
    root = _kl_package_root()
    py_files = list(root.rglob("*.py"))
    assert py_files, "mindsos_knowledge package has no .py files"

    offenders: list[tuple[Path, int, str]] = []
    for py in py_files:
        offenders.extend(_scan_for_imports(py, "mindsos_server"))
    assert not offenders, (
        f"mindsos_knowledge imports mindsos_server (ADR-0010 §I-S1 "
        f"violation): {offenders}"
    )


def test_no_mindsos_admin_imports_in_mindsos_knowledge() -> None:
    """ADR-0010 §am1 — knowledge → admin: FORBIDDEN."""
    root = _kl_package_root()
    py_files = list(root.rglob("*.py"))

    offenders: list[tuple[Path, int, str]] = []
    for py in py_files:
        offenders.extend(_scan_for_imports(py, "mindsos_admin"))
    assert not offenders, (
        f"mindsos_knowledge imports mindsos_admin (ADR-0010 §am1 "
        f"violation): {offenders}"
    )


def test_mindsos_knowledge_types_module_loads() -> None:
    """Sanity — the new module is importable."""
    from mindsos_knowledge.types import SessionProtocol
    assert SessionProtocol is not None
