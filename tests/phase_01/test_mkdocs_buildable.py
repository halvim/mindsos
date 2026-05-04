"""mkdocs builds against the current docs/ tree without errors.

mkdocs is NOT installed in the test image (see manifest.toml [ci] mkdocs_version
+ phase-ci.yml ad-hoc install). This test is therefore skipped when mkdocs
isn't importable. CI installs mkdocs ad-hoc and runs `mkdocs build` directly,
so the cumulative `pytest tests/` step will skip this test in-container, and
the dedicated mkdocs build step covers the actual build verification.

A developer running pytest on the host with `pip install mkdocs==1.6.1` does
exercise this test. Both paths cover the contract.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


def test_mkdocs_build_quiet_succeeds(repo_root: Path, tmp_path: Path):
    if shutil.which("mkdocs") is None:
        pytest.skip("mkdocs not installed (see file docstring)")

    mkdocs_yml = repo_root / "mkdocs.yml"
    assert mkdocs_yml.exists(), "mkdocs.yml not found at repo root"

    site_dir = tmp_path / "site"
    proc = subprocess.run(
        [
            "mkdocs",
            "build",
            "--quiet",
            "--config-file",
            str(mkdocs_yml),
            "--site-dir",
            str(site_dir),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, (
        f"mkdocs build failed (exit {proc.returncode})\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert (site_dir / "index.html").exists(), "site/index.html not produced"
