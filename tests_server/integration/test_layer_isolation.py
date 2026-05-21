"""
Layer-isolation test per ADR-0010 §I-S1.

Phase 18 PB-26 — this test ships at Phase 18 (the moment ``mindsos_server``
exists) NOT deferred to Phase 25. Closes the window in which a
contributor could add ``from mindsos_server`` to a domain layer module
without CI noticing.

Greps every ``.py`` file in ``mindsos_knowledge/``, ``mindsos_admin/``,
``mindsos_instances/``, and ``mindsos_core/`` (the four domain layer
packages as of Phase 18) for top-level imports of ``mindsos_server`` and
asserts none exist.

The reverse direction (``mindsos_server → mindsos_knowledge``) IS
permitted per ADR-0010 + Phase 18 PB-7 — Phase 18 specifically imports
``_USER_ID_RE`` from KL identifiers. This test does NOT check that
direction.
"""

from __future__ import annotations

import re
from pathlib import Path


def _repo_root() -> Path:
    """Find repo root by walking up to find pyproject.toml."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not find repo root")


# Domain layer packages that must NOT import mindsos_server per ADR-0010.
# Append future domain packages here (mindsos_capacity / L3 will join when
# Phase 27+ ships).
_DOMAIN_PACKAGES = (
    "mindsos_core",
    "mindsos_knowledge",
    "mindsos_admin",
    "mindsos_instances",
)

# Patterns that violate I-S1: any top-level import of mindsos_server.
# Match `from mindsos_server` or `import mindsos_server` at line start
# (allowing leading whitespace for guarded imports — but those are still
# violations per ADR-0010 §I-S1 "no top-level `from mindsos_server`").
_VIOLATION_PATTERNS = (
    re.compile(r"^\s*from\s+mindsos_server\b", re.MULTILINE),
    re.compile(r"^\s*import\s+mindsos_server\b", re.MULTILINE),
)


def _scan_package(pkg_root: Path) -> list[tuple[Path, str]]:
    """
    Return list of (path, matched_line) for every violation in the package.
    """
    violations: list[tuple[Path, str]] = []
    for py_file in pkg_root.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for pattern in _VIOLATION_PATTERNS:
            for match in pattern.finditer(text):
                # Capture the matched line for the error message.
                line_start = text.rfind("\n", 0, match.start()) + 1
                line_end = text.find("\n", match.end())
                if line_end == -1:
                    line_end = len(text)
                violations.append((py_file, text[line_start:line_end].strip()))
    return violations


def test_no_domain_layer_imports_mindsos_server() -> None:
    """ADR-0010 §I-S1 — domain layers MUST NOT import mindsos_server."""
    root = _repo_root()
    all_violations: list[tuple[Path, str]] = []

    for pkg_name in _DOMAIN_PACKAGES:
        pkg_root = root / pkg_name
        if not pkg_root.exists():
            # Domain pkg not shipped yet (e.g., mindsos_capacity at Phase 27+).
            # Skip without failing — Phase 18 only enforces against shipped pkgs.
            continue
        all_violations.extend(_scan_package(pkg_root))

    if all_violations:
        msg_lines = ["ADR-0010 §I-S1 violation: domain layer imports mindsos_server"]
        for path, line in all_violations:
            msg_lines.append(f"  {path.relative_to(_repo_root())}: {line}")
        raise AssertionError("\n".join(msg_lines))
