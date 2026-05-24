"""
Tests for doctor pkg-parity loop — Phase 18 PB-21 origin; Phase 27
PB-25/33 generalized to a manifest-driven N-pkg parity.

Verifies that ``mindsos doctor --self-test`` checks every package
listed in ``manifest.toml [mindsos] packages`` has a matching
``__init__.py:__version__``. File kept at ``tests/phase_18/`` for
cumulative-artifact location; semantic ownership now spans Phase 18
(introduction) + Phase 27 (manifest-driven generalization that closed
the 6-pkg literal-decay class).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover — runtime image is 3.11+
    import tomli as tomllib  # type: ignore[no-redef]


def _repo_root() -> Path:
    """Find repo root by walking up to find pyproject.toml."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not find repo root")


def _load_manifest_packages() -> list[str]:
    """Return the manifest's authoritative [mindsos] packages list."""
    manifest_path = _repo_root() / "mindsos_cli" / "manifest.toml"
    with manifest_path.open("rb") as f:
        manifest = tomllib.load(f)
    pkgs = manifest["mindsos"].get("packages")
    assert isinstance(pkgs, list) and pkgs, (
        "manifest.toml [mindsos] packages must be a non-empty list "
        "(Phase 27 PB-25 generalization)"
    )
    return list(pkgs)


def _manifest_version() -> str:
    manifest_path = _repo_root() / "mindsos_cli" / "manifest.toml"
    with manifest_path.open("rb") as f:
        manifest = tomllib.load(f)
    version = manifest["mindsos"]["version"]
    assert isinstance(version, str)
    return version


class TestDoctorChecksMindosServer:
    """PB-21 — doctor.py references the manifest-driven parity loop
    (Phase 27 retains the substantive assertion: doctor reads + asserts
    every manifest-listed package matches the manifest version)."""

    def test_doctor_module_references_manifest_packages(self) -> None:
        doctor_path = _repo_root() / "mindsos_cli" / "commands" / "doctor.py"
        text = doctor_path.read_text()
        # Phase 27 — the manifest-driven loop reads `[mindsos] packages`.
        assert 'manifest["mindsos"].get("packages"' in text, (
            "doctor.py must iterate manifest [mindsos] packages "
            "per Phase 27 PB-25 generalization"
        )

    def test_doctor_includes_version_drift_block(self) -> None:
        doctor_path = _repo_root() / "mindsos_cli" / "commands" / "doctor.py"
        text = doctor_path.read_text()
        # Pattern matches the generalized parity drift message.
        assert re.search(
            r"__version__ drift", text
        ), "doctor.py must emit version drift failure per parity loop"


class TestServerVersionMatchesManifest:
    """Phase 18 version bump — server pkg matches manifest."""

    def test_server_version_matches_manifest(self) -> None:
        root = _repo_root()

        # Read mindsos_server/__init__.py version.
        server_init = (root / "mindsos_server" / "__init__.py").read_text()
        match = re.search(r'__version__\s*=\s*"([^"]+)"', server_init)
        assert match is not None, "mindsos_server/__init__.py must declare __version__"
        server_version = match.group(1)

        assert server_version == _manifest_version(), (
            f"version drift: mindsos_server={server_version!r} "
            f"manifest={_manifest_version()!r}"
        )


class TestAllPackagesMatchManifest:
    """Phase 27 PB-25/33: All packages listed in
    ``manifest.toml [mindsos] packages`` must have ``__init__.py``
    ``__version__`` equal to ``manifest [mindsos] version``. Replaces
    the hard-coded 6-pkg tuple (was: ``TestAll6PkgsAtCurrentPhase``)
    so future new-pkg phases only add a single manifest line — no
    test or doctor edits.
    """

    def test_all_manifest_packages_match_manifest_version(self) -> None:
        root = _repo_root()
        expected = _manifest_version()
        packages = _load_manifest_packages()
        assert len(packages) >= 6, (
            "Phase 18+ baseline expects ≥6 packages; got "
            f"{packages!r}"
        )
        for pkg in packages:
            init_text = (root / pkg / "__init__.py").read_text()
            match = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
            assert match is not None, f"{pkg}/__init__.py has no __version__"
            assert match.group(1) == expected, (
                f"{pkg}/__init__.py version drift: "
                f"got {match.group(1)!r}, expected {expected!r} (from manifest)"
            )
