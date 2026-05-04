"""Phase 02 — `confirm-phase` preflights `doctor --self-test`.

ζ from PHASE_01 §6 deferral. The preflight catches drift (manifest /
compose / lockfile / workflows / version strings) BEFORE writing the
confirmation doc — so a CI run on an inconsistent branch can't silently
record a doc that disagrees with reality.

These tests exercise the preflight helper directly. Subprocess-level
end-to-end coverage of the `--skip-tests` path lives in
`tests/phase_01/test_confirm_phase.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from mindsos_cli.commands import confirm_phase as _cp


def test_preflight_helper_returns_tuple_of_ok_and_text(monkeypatch):
    # Stub _preflight_self_test's subprocess to return a clean success.
    class _StubProc:
        returncode = 0
        stdout = '{"ok": true}'
        stderr = ""

    def _fake_run(*args, **kwargs):
        return _StubProc()

    monkeypatch.setattr(_cp.subprocess, "run", _fake_run)
    ok, text = _cp._preflight_self_test()
    assert ok is True
    assert "ok" in text


def test_preflight_helper_reports_failure_text(monkeypatch):
    class _StubProc:
        returncode = 1
        stdout = '{"ok": false, "failures": ["python version drift"]}'
        stderr = ""

    monkeypatch.setattr(_cp.subprocess, "run", lambda *a, **k: _StubProc())
    ok, text = _cp._preflight_self_test()
    assert ok is False
    assert "drift" in text


def test_preflight_helper_handles_missing_executable(monkeypatch):
    def _raise(*args, **kwargs):
        raise FileNotFoundError("mindsos CLI not on PATH")

    monkeypatch.setattr(_cp.subprocess, "run", _raise)
    ok, text = _cp._preflight_self_test()
    assert ok is False
    assert "preflight invocation failed" in text


def test_init_notes_accepts_bare_phase_number(tmp_path, monkeypatch):
    # Place a notes template in a fake repo root.
    fake_root = tmp_path / "repo"
    (fake_root / "confirmation_docs").mkdir(parents=True)
    (fake_root / "confirmation_docs" / "_template_notes.md").write_text(
        "# Phase NN — notes\n\n## phase_title\n\n…\n\n## tester_notes\n\n…\n"
    )
    monkeypatch.setattr(_cp, "_repo_root", lambda: fake_root)

    # Bare numeric form (Phase 02 canonical).
    out_bare = tmp_path / "out-bare.md"
    _cp._init_notes("02", out_bare)
    assert out_bare.exists()
    assert "Phase 02" in out_bare.read_text()


def test_init_notes_accepts_legacy_phase_prefixed_form(tmp_path, monkeypatch):
    fake_root = tmp_path / "repo"
    (fake_root / "confirmation_docs").mkdir(parents=True)
    (fake_root / "confirmation_docs" / "_template_notes.md").write_text(
        "# Phase NN — notes\n\n## phase_title\n\n…\n"
    )
    monkeypatch.setattr(_cp, "_repo_root", lambda: fake_root)

    out_legacy = tmp_path / "out-legacy.md"
    _cp._init_notes("phase-02", out_legacy)
    assert out_legacy.exists()
    assert "Phase 02" in out_legacy.read_text()


def test_init_notes_rejects_other_shapes(tmp_path, monkeypatch):
    fake_root = tmp_path / "repo"
    (fake_root / "confirmation_docs").mkdir(parents=True)
    (fake_root / "confirmation_docs" / "_template_notes.md").write_text("x")
    monkeypatch.setattr(_cp, "_repo_root", lambda: fake_root)

    import typer
    with pytest.raises(typer.Exit) as exc:
        _cp._init_notes("phase02", tmp_path / "junk.md")
    assert exc.value.exit_code == 2
