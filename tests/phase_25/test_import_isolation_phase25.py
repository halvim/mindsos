"""
ADR-0010 §I-S1 — :mod:`mindsos_knowledge` MUST NOT import
:mod:`mindsos_server` at module load.

Static scan of the KL package — any ``from mindsos_server`` /
``import mindsos_server`` in any KL submodule fails this test.

Phase 25 adds :mod:`mindsos_knowledge.types` (SessionProtocol first
ship); the scan must keep returning clean.
"""

from __future__ import annotations

from pathlib import Path

import mindsos_knowledge


def _kl_package_root() -> Path:
    return Path(mindsos_knowledge.__file__).parent


def test_no_mindsos_server_imports_in_mindsos_knowledge() -> None:
    root = _kl_package_root()
    py_files = list(root.rglob("*.py"))
    assert py_files, "mindsos_knowledge package has no .py files"

    offenders: list[tuple[Path, int, str]] = []
    for py in py_files:
        for n, line in enumerate(py.read_text().splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if (
                "from mindsos_server" in stripped
                or stripped.startswith("import mindsos_server")
            ):
                offenders.append((py, n, line))
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
        for n, line in enumerate(py.read_text().splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if (
                "from mindsos_admin" in stripped
                or stripped.startswith("import mindsos_admin")
            ):
                offenders.append((py, n, line))
    assert not offenders, (
        f"mindsos_knowledge imports mindsos_admin (ADR-0010 §am1 "
        f"violation): {offenders}"
    )


def test_mindsos_knowledge_types_module_loads() -> None:
    """Sanity — the new module is importable."""
    from mindsos_knowledge.types import SessionProtocol
    assert SessionProtocol is not None
