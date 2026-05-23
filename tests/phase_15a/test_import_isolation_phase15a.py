"""Phase 15a — import-isolation invariant for mindsos_admin.

ORIGINAL Phase 15a lock: ``mindsos_admin`` imports nothing from
``mindsos_cli`` or ``mindsos_server`` (latter didn't exist at
Phase 15a — parametrised over a forbidden-roots list per
ADR-0010-pre-Phase-24).

**Revised at Phase 24 (Round 0 PB-Z22 / ADR-0010 §amendment-1):**
admin is a server-side curation toolkit, not a domain layer. It USES
server infrastructure (admin_tx + authz + audit + Session +
capabilities). The Phase 24 ``mindsos_admin/promotion.py`` +
``mindsos_admin/audit_gate.py`` legitimately import from
``mindsos_server.*`` per the revised DAG rule. Phase 24's
``tests/phase_24/test_import_isolation_phase24.py`` is the canonical
enforcer of the post-Z22 contract.

This Phase 15a test is RELAXED at Phase 24 ship: ``mindsos_cli`` is
still forbidden (admin must not reach into CLI presentation); but
``mindsos_server`` is no longer forbidden (post-Z22).
"""

from __future__ import annotations

import ast
import os

import pytest

import mindsos_admin


# Post-Z22 — mindsos_server removed from the forbidden-roots list
# (admin → server is ALLOWED per ADR-0010 §am1 revised).
_FORBIDDEN_ROOTS = ("mindsos_cli",)


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
