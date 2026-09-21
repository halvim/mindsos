"""The lane scripts are safe to paste.

`tools/slice_start.sh`, `slice_commit.sh`, `gate.sh` and `slice_land.sh` are the
pair-execution workflow as scripts: the owner pastes one box instead of four,
and each script ends in one `ANSWER` line. That only helps if the scripts fail
loudly, so this pins the properties that make them trustworthy rather than
convenient:

* they parse (`bash -n`) -- a syntax error would be discovered mid-ship;
* `set -euo pipefail` -- a failed step must stop the script, not roll on;
* every script prints an `ANSWER` line, the interface the owner reads;
* none of them uses `git add -A` / `git add .` (RULES 5: stage explicit paths);
* `slice_land.sh` does not merge unless asked AND every check is SUCCESS.

WHAT THIS CANNOT DO: prove a script does what its name says. That is what
running it does -- these scripts shipped by gating their own PR with
`gate.sh`. This guards the properties a run would not reveal until too late.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ("slice_start.sh", "slice_commit.sh", "gate.sh", "slice_land.sh")


def _path(name: str) -> Path:
    return _ROOT / "tools" / name


@pytest.mark.parametrize("name", SCRIPTS)
def test_the_script_exists_and_is_executable(name):
    p = _path(name)
    assert p.is_file(), f"{name} missing - the lane scripts are tracked (tools/)"
    assert p.stat().st_mode & 0o100, f"{name} is not executable"


@pytest.mark.parametrize("name", SCRIPTS)
def test_the_script_parses(name):
    r = subprocess.run(["bash", "-n", str(_path(name))], capture_output=True, text=True)
    assert r.returncode == 0, f"{name} does not parse: {r.stderr.strip()}"


@pytest.mark.parametrize("name", SCRIPTS)
def test_the_script_aborts_on_the_first_failure(name):
    text = _path(name).read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash"), f"{name} has no bash shebang"
    assert re.search(r"^set -euo pipefail$", text, re.MULTILINE), (
        f"{name} lacks `set -euo pipefail` - a failed step would roll on and the "
        "ANSWER line would describe a state that never happened"
    )


@pytest.mark.parametrize("name", SCRIPTS)
def test_the_script_answers(name):
    assert "ANSWER " in _path(name).read_text(encoding="utf-8"), (
        f"{name} prints no ANSWER line - prose telling the owner what to paste "
        "back is not the same thing"
    )


@pytest.mark.parametrize("name", SCRIPTS)
def test_no_script_stages_everything(name):
    text = _path(name).read_text(encoding="utf-8")
    assert not re.search(r"git add\s+(-A|--all|\.)(\s|$)", text), (
        f"{name} stages everything - RULES 5 says stage explicit paths"
    )


def test_gate_always_answers_and_never_hides_a_stale_worktree():
    """Found by running it: an early abort printed nothing, a second run at the
    same sha overwrote the first one's log, and a failed cleanup was swallowed."""
    text = _path("gate.sh").read_text(encoding="utf-8")
    assert "trap answer EXIT" in text, (
        "gate.sh has no EXIT trap - an aborted run would print no ANSWER line"
    )
    assert "stale_gate_wts=" in text, (
        "gate.sh does not report leftover gate worktrees - a swallowed cleanup "
        "failure is how two of them accumulated"
    )
    assert re.search(r'out="\$\{HOME\}/gate-\$\{sha\}-\$\{stamp\}', text), (
        "gate.sh's log name does not carry the run - a re-run at the same sha "
        "would overwrite the earlier run's evidence"
    )


def test_land_refuses_to_merge_without_a_green_rollup():
    text = _path("slice_land.sh").read_text(encoding="utf-8")
    assert "--merge" in text, "slice_land.sh has no explicit merge opt-in"
    assert re.search(r'rollup.*SUCCESS', text), (
        "slice_land.sh does not gate the merge on the check rollup"
    )
    assert re.search(r"diff .*tip.*sq|git diff \"\$\{tip\}\" \"\$\{sq\}\"", text), (
        "slice_land.sh does not measure the branch-tip vs squash diff - RULES 12.2(a) "
        "is discharged by a measurement, not by a claim"
    )
