"""Phase 39 ``tools/check_rename_state.py`` detector contract.

Per Phase 39 design log §2 PB-8 + PB-3:

* Standalone Falkor probe (~20 LOC).
* Exit 0 on clean state (no pre-rename ``memories-`` IRI nodes found
  in any data graph).
* Exit 1 + stderr wipe-and-rebootstrap instructions on pre-rename
  rows present.
* Idempotent (same input → same exit code).

Contract assertions only — actual Falkor side-effect testing happens
at integration tier per ``[[feedback-tester-two-machine-workflow]]``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "tools" / "check_rename_state.py"


def test_check_rename_state_script_present() -> None:
    """File ships per design log §6 outputs list."""
    assert _SCRIPT.exists(), (
        f"Phase 39 detector script missing: {_SCRIPT.relative_to(_REPO_ROOT)}"
    )


def test_check_rename_state_script_is_executable_python() -> None:
    """The shebang + Python source parse cleanly."""
    body = _SCRIPT.read_text(encoding="utf-8")
    assert body.startswith("#!"), "Detector script needs shebang"
    assert "python" in body.splitlines()[0].lower()
    compile(body, str(_SCRIPT), "exec")


def test_check_rename_state_script_help_runs_without_falkor() -> None:
    """``--help`` exits 0 without requiring Falkor at runtime."""
    result = subprocess.run(
        [sys.executable, str(_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"check_rename_state --help failed: stdout={result.stdout!r}, "
        f"stderr={result.stderr!r}"
    )


def test_check_rename_state_script_documents_exit_codes() -> None:
    """Docstring or argparse description enumerates exit-code contract."""
    body = _SCRIPT.read_text(encoding="utf-8")
    # Per design log: exit 0 = clean; exit 1 = found pre-rename rows.
    assert "exit 0" in body.lower() or "exit code 0" in body.lower()
    assert "exit 1" in body.lower() or "exit code 1" in body.lower()


def test_check_rename_state_script_mentions_iri_prefix() -> None:
    """Body references the pre-rename ``memories-`` IRI prefix it scans for."""
    body = _SCRIPT.read_text(encoding="utf-8")
    assert "memories-" in body, (
        "Detector body must reference the pre-rename IRI prefix it scans for"
    )
