"""Import-isolation contract per ADR-0010 §am1 (revised at Round 0 PB-Z22).

Same-commit discipline per Z10: this test ships in the same commit
as ADR-0010 §am1.

DAG rules enforced:

| From → To | Status |
|---|---|
| `mindsos_knowledge` → `mindsos_server` | FORBIDDEN (ADR-0010 §I-S1) |
| `mindsos_knowledge` → `mindsos_admin` | FORBIDDEN |
| `mindsos_admin` → `mindsos_knowledge` | ALLOWED |
| `mindsos_admin` → `mindsos_server` | ALLOWED (Round 0 PB-Z22 revised) |
| `mindsos_server` → `mindsos_admin` | ALLOWED (Phase 24 release.py) |
| `mindsos_server` → `mindsos_knowledge` | ALLOWED |
"""

from __future__ import annotations

import ast
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[2]


def _scan_imports(pkg_name: str) -> set[str]:
    """Return the set of top-level module names imported anywhere in
    ``mindsos_<pkg>/`` (excluding __pycache__ and tests).
    """
    pkg_dir = PKG_ROOT / pkg_name
    imports: set[str] = set()
    for py in pkg_dir.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.level == 0:
                    imports.add(node.module.split(".")[0])
    return imports


def test_knowledge_does_not_import_server():
    """ADR-0010 §I-S1 original — KL stays library-installable."""
    imports = _scan_imports("mindsos_knowledge")
    assert "mindsos_server" not in imports, (
        f"FORBIDDEN: mindsos_knowledge imports mindsos_server "
        f"(seen in imports). ADR-0010 §I-S1 violated."
    )


def test_knowledge_does_not_import_admin():
    """ADR-0010 §am1 — KL stays self-contained from curation machinery."""
    imports = _scan_imports("mindsos_knowledge")
    assert "mindsos_admin" not in imports, (
        f"FORBIDDEN: mindsos_knowledge imports mindsos_admin. "
        f"ADR-0010 §am1 violated."
    )


def test_admin_imports_knowledge_allowed():
    """ADR-0010 §am1 — admin composes KL surfaces (Phase 15a + 16)."""
    imports = _scan_imports("mindsos_admin")
    # Existence is allowed; this asserts the import is present per design.
    assert "mindsos_knowledge" in imports, (
        f"EXPECTED: mindsos_admin should import mindsos_knowledge "
        f"(Phase 15a importers + Phase 16 similarity); not seen."
    )


def test_admin_imports_server_allowed():
    """ADR-0010 §am1 Round 0 Z22 revision — admin uses server infrastructure."""
    imports = _scan_imports("mindsos_admin")
    assert "mindsos_server" in imports, (
        f"EXPECTED: mindsos_admin imports mindsos_server "
        f"(Phase 24 promotion + audit_gate need admin_tx + authz + "
        f"audit + Session); not seen — Round 0 Z22 was wrong-direction."
    )


def test_server_imports_admin_allowed():
    """ADR-0010 §am1 — server composes admin machinery (release.py)."""
    imports = _scan_imports("mindsos_server")
    assert "mindsos_admin" in imports, (
        f"EXPECTED: mindsos_server imports mindsos_admin "
        f"(Phase 24 release.py calls audit_gate.run); not seen."
    )
