"""Direct unit tests for confirm-phase internals.

`test_confirm_phase.py` exercises the CLI end-to-end via subprocess. This file
exercises the parser internals directly — they're load-bearing for the
confirmation doc's correctness, and the CLI's --skip-tests path doesn't cover
the test-summary parser at all.
"""

from __future__ import annotations

from pathlib import Path

from mindsos_cli.commands.confirm_phase import (
    _parse_notes,
    _parse_pytest_summary,
)


# --- pytest summary parser (fix A — error/errors no longer double-counts) ---


def test_pytest_summary_simple_pass_line():
    counts = _parse_pytest_summary("4 passed in 0.5s")
    assert counts == {"count": 4, "passed": 4, "skipped": 0, "failed": 0}


def test_pytest_summary_mixed_outcomes():
    counts = _parse_pytest_summary("4 passed, 1 skipped, 2 failed in 1.2s")
    assert counts == {"count": 7, "passed": 4, "skipped": 1, "failed": 2}


def test_pytest_summary_errors_singular_not_double_counted():
    counts = _parse_pytest_summary("3 errors in 0.5s")
    assert counts == {"count": 3, "passed": 0, "skipped": 0, "failed": 3}


def test_pytest_summary_error_singular_not_double_counted():
    counts = _parse_pytest_summary("1 error in 0.1s")
    assert counts == {"count": 1, "passed": 0, "skipped": 0, "failed": 1}


def test_pytest_summary_errors_alongside_failures():
    """Both `failed` and `errors` should be counted exactly once each."""
    counts = _parse_pytest_summary(
        "10 passed, 2 failed, 3 errors in 2.0s"
    )
    assert counts == {"count": 15, "passed": 10, "skipped": 0, "failed": 5}


def test_pytest_summary_no_match_returns_zeros():
    counts = _parse_pytest_summary("no pytest output recognised")
    assert counts == {"count": 0, "passed": 0, "skipped": 0, "failed": 0}


# --- notes parser (fix B — inner H2 inside tester_notes stays in body) ---


def test_parse_notes_inner_h2_stays_in_tester_notes(tmp_path: Path):
    notes = tmp_path / "n.md"
    notes.write_text(
        "## phase_title\n\n"
        "Tooling infrastructure\n\n"
        "## tester_notes\n\n"
        "Smoke run was clean.\n\n"
        "## Background\n\n"
        "We hit a rare race in the FalkorDB healthcheck the first run.\n\n"
        "## Open questions\n\n"
        "Should mkdocs ship in the test image?\n"
    )
    parsed = _parse_notes(notes)
    assert parsed["phase_title"] == "Tooling infrastructure"
    # The body must include both the leading paragraph AND the inner H2 sections.
    body = parsed["tester_notes"]
    assert "Smoke run was clean." in body
    assert "## Background" in body
    assert "rare race" in body
    assert "## Open questions" in body
    assert "mkdocs" in body


def test_parse_notes_handles_template_blockquote_instructions(tmp_path: Path):
    notes = tmp_path / "n.md"
    notes.write_text(
        "## phase_title\n\n"
        "> instructional comment\n"
        "Tooling infrastructure\n\n"
        "## tester_notes\n\n"
        "> another instruction\n"
        "Real tester notes here.\n"
    )
    parsed = _parse_notes(notes)
    assert parsed["phase_title"] == "Tooling infrastructure"
    assert parsed["tester_notes"] == "Real tester notes here."


def test_parse_notes_empty_field_becomes_empty_string(tmp_path: Path):
    notes = tmp_path / "n.md"
    notes.write_text("## phase_title\n\n…\n\n## tester_notes\n\n\n")
    parsed = _parse_notes(notes)
    assert parsed == {"phase_title": "", "tester_notes": ""}


def test_parse_notes_unknown_top_h2_does_not_become_a_field(tmp_path: Path):
    """An unrelated H2 above the sentinel sections is benign."""
    notes = tmp_path / "n.md"
    notes.write_text(
        "## random_unknown_section\n\n"
        "this should be ignored entirely\n\n"
        "## phase_title\n\n"
        "Tooling infrastructure\n\n"
        "## tester_notes\n\n"
        "Notes.\n"
    )
    parsed = _parse_notes(notes)
    assert parsed["phase_title"] == "Tooling infrastructure"
    assert parsed["tester_notes"] == "Notes."
    # No leak from random section.
    assert "this should be ignored" not in parsed["phase_title"]
    assert "this should be ignored" not in parsed["tester_notes"]
