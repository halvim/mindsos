"""`mindsos confirm-phase --phase NN --notes-file ...` writes a confirmation doc."""

from __future__ import annotations

import json
from pathlib import Path


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


def _write_notes(tmp_path: Path) -> Path:
    notes = tmp_path / "notes-phase-01.md"
    notes.write_text(_NOTES_FIXTURE)
    return notes


def test_confirm_phase_writes_doc_with_all_schema_fields(cli, tmp_path: Path):
    notes = _write_notes(tmp_path)
    out = tmp_path / "PHASE_01_CONFIRMED.md"
    proc = cli(
        "confirm-phase",
        "--phase",
        "01",
        "--notes-file",
        str(notes),
        "--out",
        str(out),
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


def test_confirm_phase_json_mode(cli, tmp_path: Path):
    notes = _write_notes(tmp_path)
    out = tmp_path / "PHASE_01_CONFIRMED.md"
    proc = cli(
        "confirm-phase",
        "--phase",
        "01",
        "--notes-file",
        str(notes),
        "--out",
        str(out),
        "--skip-tests",
        "--json",
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["mode"] == "confirm-phase"
    assert payload["phase"] == "01"
    assert payload["out"] == str(out)
    assert payload["tests_run"] is False
    assert payload["tests_failed"] is False


def test_confirm_phase_rejects_phase_mismatched_to_manifest(cli, tmp_path: Path):
    """Manifest's [mindsos] phase is '01' on phase-01 branch; --phase 02 must fail."""
    notes = _write_notes(tmp_path)
    out = tmp_path / "PHASE_02_CONFIRMED.md"
    proc = cli(
        "confirm-phase",
        "--phase",
        "02",
        "--notes-file",
        str(notes),
        "--out",
        str(out),
        "--skip-tests",
    )
    assert proc.returncode != 0
    assert "manifest" in proc.stderr.lower()
    assert not out.exists(), "doc was written despite phase mismatch"


def test_confirm_phase_requires_notes_file(cli, tmp_path: Path):
    out = tmp_path / "PHASE_01_CONFIRMED.md"
    proc = cli(
        "confirm-phase",
        "--phase",
        "01",
        "--notes-file",
        str(tmp_path / "does-not-exist.md"),
        "--out",
        str(out),
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

    notes = _write_notes(tmp_path)
    out = tmp_path / "PHASE_01_CONFIRMED.md"
    proc = cli(
        "confirm-phase",
        "--phase",
        "01",
        "--notes-file",
        str(notes),
        "--out",
        str(out),
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
        f"Phase 01 wrapper produced {actual_fields}"
    )
