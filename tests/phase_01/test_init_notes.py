"""`mindsos confirm-phase --init-notes` writes a fillable notes file."""

from __future__ import annotations

import json
from pathlib import Path


def test_init_notes_writes_non_empty_with_required_sections(cli, tmp_path: Path):
    out = tmp_path / "notes-phase-99.md"
    proc = cli("confirm-phase", "--init-notes", "phase-99", "--out", str(out))
    assert proc.returncode == 0, proc.stderr

    body = out.read_text()
    assert body.strip(), "notes file is empty"
    assert "## phase_title" in body
    assert "## tester_notes" in body
    assert "Phase 99" in body, "phase token NN was not substituted into the title"


def test_init_notes_json_mode_emits_path(cli, tmp_path: Path):
    out = tmp_path / "notes-phase-02.md"
    proc = cli(
        "confirm-phase",
        "--init-notes",
        "phase-02",
        "--out",
        str(out),
        "--json",
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload == {"mode": "init-notes", "path": str(out)}


def test_init_notes_rejects_malformed_token(cli):
    proc = cli("confirm-phase", "--init-notes", "phase02")  # missing dash
    assert proc.returncode != 0
    assert "phase-NN" in proc.stderr


def test_init_notes_mutually_exclusive_with_phase(cli, tmp_path: Path):
    notes = tmp_path / "notes.md"
    notes.write_text("## phase_title\nFoo\n## tester_notes\nBar\n")
    proc = cli(
        "confirm-phase",
        "--init-notes",
        "phase-02",
        "--phase",
        "01",
        "--notes-file",
        str(notes),
    )
    assert proc.returncode != 0
    assert "mutually exclusive" in proc.stderr
