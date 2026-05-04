"""`mindsos confirm-phase --phase NN --notes-file ...` writes a confirmation doc.

Tests are written **phase-agnostic**: they read the current `[mindsos]
phase` from `manifest.toml` so the manifest can bump phase-by-phase
without breaking these. The mismatch test deliberately picks a far-away
phase ('99') that no real branch will ever match.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Production code targets Python 3.12 (test image), where tomllib is stdlib.
# Host-side runs on 3.10/3.11 fall back to tomli.
if sys.version_info < (3, 11):
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore
else:
    import tomllib


_NOTES_FIXTURE = """\
## phase_title

Tooling infrastructure

## tester_notes

Smoke test fixture.
Phase 01 wired up CI workflows + confirm-phase wrapper.
"""


_REQUIRED_SCHEMA_FIELDS = (
    "phase_number",
    "phase_title",
    "git_sha",
    "image_build_hash",
    "falkordb_version",
    "automated_test_summary",
    "tester_notes",
    "timestamp_utc",
    "mkdocs_pages_updated",
)


def _current_phase(repo_root: Path) -> str:
    """Read the current `[mindsos] phase` from manifest.toml.

    These tests are phase-agnostic — they exercise the wrapper against
    whatever phase the manifest currently advertises. Hardcoding '01'
    (or any specific phase) breaks the moment a later phase bumps the
    manifest, so we read the source of truth instead.
    """
    if tomllib is None:
        # Best-effort regex fallback for Python <3.11 without tomli.
        import re
        body = (repo_root / "mindsos_cli" / "manifest.toml").read_text()
        m = re.search(r'^\s*phase\s*=\s*"([^"]+)"', body, re.MULTILINE)
        assert m, "couldn't parse [mindsos] phase from manifest.toml"
        return m.group(1)
    with (repo_root / "mindsos_cli" / "manifest.toml").open("rb") as f:
        data = tomllib.load(f)
    return data["mindsos"]["phase"]


def _write_notes(tmp_path: Path, phase: str) -> Path:
    notes = tmp_path / f"notes-phase-{phase}.md"
    notes.write_text(_NOTES_FIXTURE)
    return notes


def test_confirm_phase_writes_doc_with_all_schema_fields(cli, tmp_path: Path, repo_root):
    phase = _current_phase(repo_root)
    notes = _write_notes(tmp_path, phase)
    out = tmp_path / f"PHASE_{phase}_CONFIRMED.md"
    proc = cli(
        "confirm-phase",
        "--phase", phase,
        "--notes-file", str(notes),
        "--out", str(out),
        "--skip-tests",
    )
    # --skip-tests means tests aren't run, so wrapper should exit 0 even if
    # the docker compose stack isn't up.
    assert proc.returncode == 0, proc.stderr

    body = out.read_text()
    assert body.strip()
    for field in _REQUIRED_SCHEMA_FIELDS:
        assert f"## {field}" in body, f"missing schema field: {field}"

    assert "Tooling infrastructure" in body
    assert "Smoke test fixture." in body
    assert "tests skipped (--skip-tests)" in body


def test_confirm_phase_json_mode(cli, tmp_path: Path, repo_root):
    phase = _current_phase(repo_root)
    notes = _write_notes(tmp_path, phase)
    out = tmp_path / f"PHASE_{phase}_CONFIRMED.md"
    proc = cli(
        "confirm-phase",
        "--phase", phase,
        "--notes-file", str(notes),
        "--out", str(out),
        "--skip-tests",
        "--json",
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["mode"] == "confirm-phase"
    assert payload["phase"] == phase
    assert payload["out"] == str(out)
    assert payload["tests_run"] is False
    assert payload["tests_failed"] is False


def test_confirm_phase_rejects_phase_mismatched_to_manifest(cli, tmp_path: Path, repo_root):
    """`--phase 99` must fail — no real branch will ever match phase 99."""
    current = _current_phase(repo_root)
    assert current != "99", "test fixture clash: bump _MISMATCH_PHASE"
    notes = _write_notes(tmp_path, current)
    out = tmp_path / "PHASE_99_CONFIRMED.md"
    proc = cli(
        "confirm-phase",
        "--phase", "99",
        "--notes-file", str(notes),
        "--out", str(out),
        "--skip-tests",
    )
    assert proc.returncode != 0
    assert "manifest" in proc.stderr.lower()
    assert not out.exists(), "doc was written despite phase mismatch"


def test_confirm_phase_requires_notes_file(cli, tmp_path: Path, repo_root):
    phase = _current_phase(repo_root)
    out = tmp_path / f"PHASE_{phase}_CONFIRMED.md"
    proc = cli(
        "confirm-phase",
        "--phase", phase,
        "--notes-file", str(tmp_path / "does-not-exist.md"),
        "--out", str(out),
        "--skip-tests",
    )
    assert proc.returncode != 0


def test_confirm_phase_doc_structurally_matches_phase00(cli, tmp_path: Path, repo_root):
    """The wrapper's output must use the same field names + order as the
    hand-filled Phase 00 confirmation doc."""
    phase00_doc = repo_root / "confirmation_docs" / "PHASE_00_CONFIRMED.md"
    if not phase00_doc.exists():
        return  # tolerated — Phase 00 confirmation may not be in this checkout
    expected_fields = [
        line[3:].strip()
        for line in phase00_doc.read_text().splitlines()
        if line.startswith("## ")
    ]

    phase = _current_phase(repo_root)
    notes = _write_notes(tmp_path, phase)
    out = tmp_path / f"PHASE_{phase}_CONFIRMED.md"
    proc = cli(
        "confirm-phase",
        "--phase", phase,
        "--notes-file", str(notes),
        "--out", str(out),
        "--skip-tests",
    )
    assert proc.returncode == 0, proc.stderr

    actual_fields = [
        line[3:].strip()
        for line in out.read_text().splitlines()
        if line.startswith("## ")
    ]
    assert actual_fields == expected_fields, (
        f"field mismatch — Phase 00 had {expected_fields}, "
        f"Phase {phase} wrapper produced {actual_fields}"
    )
