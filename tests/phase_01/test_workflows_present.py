"""`.github/workflows/{phase-ci,release}.yml` exist and are well-shaped."""

from __future__ import annotations

import re
from pathlib import Path

import pytest


_PHASE_CI = ".github/workflows/phase-ci.yml"
_RELEASE = ".github/workflows/release.yml"


def test_phase_ci_exists_and_non_empty(repo_root: Path):
    p = repo_root / _PHASE_CI
    assert p.exists(), f"missing {_PHASE_CI}"
    assert p.read_text().strip(), f"{_PHASE_CI} is empty"


def test_release_exists_and_non_empty(repo_root: Path):
    p = repo_root / _RELEASE
    assert p.exists(), f"missing {_RELEASE}"
    assert p.read_text().strip(), f"{_RELEASE} is empty"


def test_phase_ci_yaml_parses(repo_root: Path):
    yaml = pytest.importorskip("yaml")
    body = (repo_root / _PHASE_CI).read_text()
    doc = yaml.safe_load(body)
    assert isinstance(doc, dict)
    assert "jobs" in doc
    # PyYAML maps the YAML key `on:` to Python boolean True (special case).
    # Accept either spelling.
    assert "on" in doc or True in doc


def test_release_yaml_parses_and_has_required_steps(repo_root: Path):
    yaml = pytest.importorskip("yaml")
    body = (repo_root / _RELEASE).read_text()
    doc = yaml.safe_load(body)
    assert isinstance(doc, dict)
    assert "jobs" in doc

    # Permissions must be declared at JOB scope (Phase 01 fix I — narrower
    # blast radius than workflow-scope). Explicit assertion guards against
    # accidental promotion back to workflow scope.
    release_job = doc["jobs"]["release"]
    assert "permissions" in release_job, (
        "release job must declare permissions at job scope"
    )
    assert release_job["permissions"].get("contents") == "write"
    # And NOT at workflow scope (top-level dict has no 'permissions' key, or
    # if it does, it's not contents: write).
    workflow_perms = doc.get("permissions", {})
    assert workflow_perms.get("contents") != "write", (
        "release.yml leaks contents: write to workflow scope"
    )

    # Release creation + retention prune must both appear by name.
    assert "gh release create" in body or "gh release edit" in body, (
        "release.yml must call `gh release create` (or edit on rerun)"
    )
    assert "Retention prune" in body or "retention" in body.lower(), (
        "release.yml must include the retention prune step"
    )

    # Tag pattern must restrict to phase-*-confirmed.
    assert "phase-*-confirmed" in body

    # Phase 01 fix α — ALL_TAGS must be exported so the Python heredoc inherits.
    assert re.search(r"^\s*export ALL_TAGS=", body, re.MULTILINE), (
        "release.yml retention step must `export` ALL_TAGS so the Python "
        "heredoc child process can read it via os.environ"
    )


def test_phase_ci_runs_cumulative_tests(repo_root: Path):
    body = (repo_root / _PHASE_CI).read_text()
    assert "pytest tests/" in body, (
        "phase-ci.yml must run pytest tests/ cumulatively, not just one phase dir"
    )


def test_phase_ci_runs_mkdocs_build(repo_root: Path):
    body = (repo_root / _PHASE_CI).read_text()
    assert "mkdocs build" in body
