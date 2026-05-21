"""
Tests for doctor 5→6 pkg parity loop — Phase 18 PB-21.

Verifies that ``mindsos doctor --self-test`` checks
``mindsos_server/__init__.py:__version__`` matches
``manifest.toml [mindsos] version``.
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


class TestDoctorChecksMindosServer:
    """PB-21 — doctor.py reads + asserts mindsos_server version."""

    def test_doctor_module_references_mindsos_server(self) -> None:
        doctor_path = _repo_root() / "mindsos_cli" / "commands" / "doctor.py"
        text = doctor_path.read_text()
        # The 6-pkg parity loop must include mindsos_server.
        assert "mindsos_server" in text, (
            "doctor.py must reference mindsos_server in the version-parity loop "
            "per Phase 18 PB-21"
        )

    def test_doctor_includes_server_version_check_block(self) -> None:
        doctor_path = _repo_root() / "mindsos_cli" / "commands" / "doctor.py"
        text = doctor_path.read_text()
        # Pattern matches the parity-check block (drift message format).
        assert re.search(
            r"mindsos_server/__init__\.py __version__ drift", text
        ), "doctor.py must check mindsos_server version drift per PB-21"


class TestServerVersionMatchesManifest:
    """Phase 18 version bump — server pkg matches manifest."""

    def test_server_version_matches_manifest(self) -> None:
        root = _repo_root()

        # Read mindsos_server/__init__.py version.
        server_init = (root / "mindsos_server" / "__init__.py").read_text()
        match = re.search(r'__version__\s*=\s*"([^"]+)"', server_init)
        assert match is not None, "mindsos_server/__init__.py must declare __version__"
        server_version = match.group(1)

        # Read manifest.toml [mindsos] version.
        manifest = (root / "mindsos_cli" / "manifest.toml").read_text()
        match = re.search(
            r'\[mindsos\][\s\S]*?version\s*=\s*"([^"]+)"', manifest
        )
        assert match is not None
        manifest_version = match.group(1)

        assert server_version == manifest_version, (
            f"version drift: mindsos_server={server_version!r} "
            f"manifest={manifest_version!r}"
        )


class TestAll6PkgsAtCurrentPhase:
    """All 6 packages (5 pre-existing + mindsos_server) must agree with
    ``manifest.toml [mindsos] version`` — that file is the canonical
    drift target per Phase 18 PB-21. Generalized at Phase 19 B-19-T1
    (was: hard-coded ``"0.0.0+phase18"`` literal; decayed on every
    version bump). Per ``feedback_phase_baseline_literal_audit.md`` —
    the parity is what we care about, not the absolute version."""

    def test_all_six_packages_match_manifest(self) -> None:
        root = _repo_root()

        # Source-of-truth: manifest.toml [mindsos] version.
        manifest = (root / "mindsos_cli" / "manifest.toml").read_text()
        manifest_match = re.search(
            r'\[mindsos\][\s\S]*?version\s*=\s*"([^"]+)"', manifest
        )
        assert manifest_match is not None, (
            "manifest.toml [mindsos] version not found"
        )
        expected = manifest_match.group(1)

        for pkg in (
            "mindsos_core",
            "mindsos_knowledge",
            "mindsos_admin",
            "mindsos_instances",
            "mindsos_cli",
            "mindsos_server",
        ):
            init_text = (root / pkg / "__init__.py").read_text()
            match = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
            assert match is not None, f"{pkg}/__init__.py has no __version__"
            assert match.group(1) == expected, (
                f"{pkg}/__init__.py version drift: "
                f"got {match.group(1)!r}, expected {expected!r} (from manifest)"
            )
