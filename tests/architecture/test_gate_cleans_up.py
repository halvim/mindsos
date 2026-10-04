"""`tools/gate.sh` cleans up after itself on EVERY path -- proven by running it.

`test_lane_scripts.py` reads the script's text. That cannot see the defect this
file exists for: under `set -euo pipefail` a `grep '^FAILED'` that matches
nothing exits 1, so a GREEN run aborted before cleanup and left its clone
behind, while a RED run cleaned up (STATE pending_designs
`gate-sh-leaves-a-clone-and-a-log-per-run`). A cause like that is only
provable by a run.

So this runs the REAL script. `git`, `python3` and `hostname` are stand-ins on
PATH (the test image has no git, and a real pytest run is not the subject):
the stand-in `git` makes and removes a directory for `worktree add/remove`,
the stand-in `python3` prints a canned pytest tail and exits with a canned
code. Everything the script does around them -- its control flow, its trap,
its cleanup, its log handling -- is the script's own.

WHAT IS HELD
* the clone is gone after a green run, a red run, and an abort that happens
  after the clone exists; the run reaches `step=done` when nothing aborted;
* an abort BEFORE the clone exists still answers;
* logs live in ONE folder, `~/gate-logs/`, each ends with its run's ANSWER
  line (so a lost paste is answered by `tail -1`, never by a re-run), and the
  folder is capped at the newest LOG_CAP (owner ruling 2026-10-03);
* `--mutate <file> <sed-expr>` applies a designated mutation to the clone,
  refuses unless EXACTLY one line changed, runs the mutated tree, and cleans
  up -- so no clone ever has to survive a run to be mutated by hand.

WHAT THIS CANNOT DO: prove the real `git worktree remove` succeeds on the
box, where root-owned files can outlive it. The script reports that case as
`wt_gone=n rm_me=<path>`; this file holds that the script always GETS to the
cleanup, not that the filesystem always lets it finish.
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_GATE = _ROOT / "tools" / "gate.sh"

#: The cap the owner ruled. The script carries its own copy; the cap test
#: seeds more than this many and counts what is left.
LOG_CAP = 20

_GIT = r"""#!/usr/bin/env bash
set -u
if [[ "${1:-}" == "-C" ]]; then shift 2; fi
reg="${STUB_STATE}/registered"
case "${1:-} ${2:-}" in
  "fetch "*)
    [[ "${STUB_FETCH_FAILS:-0}" == "1" ]] && exit 1
    exit 0 ;;
  "worktree add")
    wt="${5}"
    mkdir -p "${wt}/tools"
    printf 'one\ntwo\nthree\n' > "${wt}/target.txt"
    echo "${wt}" >> "${reg}"
    exit 0 ;;
  "worktree list")
    [[ -f "${reg}" ]] && cat "${reg}"
    exit 0 ;;
  "worktree remove")
    rm -rf "${4}"
    exit 0 ;;
  "worktree prune")
    if [[ -f "${reg}" ]]; then
      while read -r p; do [[ -d "${p}" ]] && echo "${p}"; done < "${reg}" > "${reg}.new" || true
      mv "${reg}.new" "${reg}"
    fi
    exit 0 ;;
  "rev-parse "*)
    [[ "${STUB_REVPARSE_FAILS:-0}" == "1" ]] && exit 1
    echo "abc1234"
    exit 0 ;;
esac
echo "stand-in git: unexpected call: $*" >&2
exit 97
"""

_PYTHON3 = r"""#!/usr/bin/env bash
set -u
if [[ "${1:-}" == "-m" && "${2:-}" == "pytest" ]]; then
  if grep -q MUTATED target.txt 2>/dev/null; then
    echo "FAILED tests/x.py::test_the_mutation_is_seen - assert 0"
    echo "1 failed in 0.01s"
    exit 1
  fi
  if [[ "${STUB_PYTEST:-green}" == "red" ]]; then
    echo "FAILED tests/x.py::test_alpha - assert 0"
    echo "FAILED tests/x.py::test_beta - assert 0"
    echo "2 failed, 1 passed in 0.01s"
    exit 1
  fi
  echo "3 passed in 0.01s"
  exit 0
fi
exit 1
"""

_HOSTNAME = "#!/usr/bin/env bash\necho gatebox\n"


class Run:
    def __init__(self, proc, home: Path, main: Path):
        self.rc = proc.returncode
        self.stdout = proc.stdout
        self.stderr = proc.stderr
        self.home = home
        self.main = main
        answers = [ln for ln in proc.stdout.splitlines() if ln.startswith("ANSWER gate ")]
        self.answer = answers[-1] if answers else ""

    def field(self, key: str) -> str:
        m = re.search(rf"(?:^| ){re.escape(key)}=(\[[^\]]*\]|\S*)", self.answer)
        assert m, f"no `{key}=` in the ANSWER line: {self.answer!r}\nstderr: {self.stderr}"
        return m.group(1)

    def clones(self) -> list[str]:
        return sorted(p.name for p in self.main.parent.glob(self.main.name + "-gate-*"))

    def logs(self) -> list[Path]:
        return sorted((self.home / "gate-logs").glob("gate-*.txt"))

    def stray_logs(self) -> list[str]:
        return sorted(p.name for p in self.home.glob("gate-*.txt"))


@pytest.fixture
def gate(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("git", _GIT), ("python3", _PYTHON3), ("hostname", _HOSTNAME)):
        p = bin_dir / name
        p.write_text(body, encoding="utf-8")
        p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    home = tmp_path / "home"
    main = tmp_path / "mindsos"
    state = tmp_path / "state"
    for d in (home, main, state):
        d.mkdir()

    def run(*args: str, **stub: str) -> Run:
        env = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '/usr/bin:/bin')}",
            "HOME": str(home),
            "MINDSOS_MAIN": str(main),
            "STUB_STATE": str(state),
        }
        env.update(stub)
        proc = subprocess.run(
            ["bash", str(_GATE), "abc1234", *args],
            capture_output=True, text=True, env=env, cwd=str(tmp_path), timeout=60,
        )
        return Run(proc, home, main)

    return run


# -- the clone ---------------------------------------------------------------

def test_a_green_run_reaches_the_end_and_removes_its_clone(gate):
    r = gate("tests/x.py")
    assert r.field("step") == "done", (
        "a GREEN run did not reach the end - nothing failed, so a search for "
        f"failures matched nothing and the script aborted there: {r.answer}"
    )
    assert r.field("rc") == "0" and r.field("fails") == "[]"
    assert r.field("wt_gone") == "y" and r.clones() == [], (
        f"a green run left its clone behind: {r.clones()}"
    )
    assert r.field("registered") == "0"


def test_a_red_run_reaches_the_end_names_the_failures_and_removes_its_clone(gate):
    r = gate("tests/x.py", STUB_PYTEST="red")
    assert r.field("step") == "done"
    assert r.field("rc") == "1"
    assert r.field("fails") == "[test_alpha,test_beta]"
    assert r.field("wt_gone") == "y" and r.clones() == []


def test_an_abort_after_the_clone_exists_still_removes_it(gate):
    r = gate("tests/x.py", STUB_REVPARSE_FAILS="1")
    assert r.answer, f"an aborted run printed no ANSWER line: {r.stdout!r}"
    assert r.field("step") != "done", "the stand-in abort did not abort - the corner is dead"
    assert r.field("wt_gone") == "y" and r.clones() == [], (
        f"an abort after the clone was made left it behind: {r.clones()} - "
        "cleanup belongs on the exit path, not at the end of the happy path"
    )


def test_an_abort_before_the_clone_exists_still_answers(gate):
    r = gate("tests/x.py", STUB_FETCH_FAILS="1")
    assert r.field("step") == "fetch"
    assert r.field("wt_gone") == "y" and r.clones() == []


# -- the log -----------------------------------------------------------------

def test_the_log_lives_in_one_folder_and_ends_with_the_answer(gate):
    r = gate("tests/x.py", STUB_PYTEST="red")
    assert r.stray_logs() == [], (
        f"a log was written straight into the home folder: {r.stray_logs()} - "
        "logs go in ~/gate-logs/, one folder that is capped"
    )
    logs = r.logs()
    assert len(logs) == 1, f"expected exactly this run's log in gate-logs/, found {logs}"
    assert r.field("log") == str(logs[0])
    lines = logs[0].read_text(encoding="utf-8").splitlines()
    assert "2 failed, 1 passed in 0.01s" in lines, "the log lost the run's own output"
    assert lines[-1] == r.answer, (
        "the log's last line is not the run's ANSWER line - a lost paste must "
        "be answerable by `tail -1` on the log, never by a re-run"
    )


def test_the_log_folder_is_capped_at_the_newest(gate):
    seeded = LOG_CAP + 5
    probe = gate("tests/x.py", STUB_FETCH_FAILS="1")
    logdir = probe.home / "gate-logs"
    logdir.mkdir(exist_ok=True)
    for p in logdir.glob("gate-*.txt"):
        p.unlink()
    for i in range(seeded):
        old = logdir / f"gate-old-{i:02d}.txt"
        old.write_text("old\n", encoding="utf-8")
        os.utime(old, (1_000_000 + i, 1_000_000 + i))
    r = gate("tests/x.py", STUB_PYTEST="red")
    names = [p.name for p in r.logs()]
    assert len(names) == LOG_CAP, (
        f"{len(names)} logs after a run over {seeded} seeded - the folder is "
        f"capped at the newest {LOG_CAP}"
    )
    assert Path(r.field("log")).name in names, "the cap deleted the run's own log"
    survivors = sorted(n for n in names if n.startswith("gate-old-"))
    expected = [f"gate-old-{i:02d}.txt" for i in range(seeded - (LOG_CAP - 1), seeded)]
    assert survivors == expected, "the cap did not keep the NEWEST logs"


# -- the mutation mode -------------------------------------------------------

def test_mutate_changes_exactly_one_line_and_runs_the_mutated_tree(gate):
    r = gate("--mutate", "target.txt", "s/two/MUTATED/", "tests/x.py")
    assert r.field("step") == "done"
    assert r.field("mutated") == "target.txt:1"
    assert r.field("rc") == "1" and r.field("fails") == "[test_the_mutation_is_seen]", (
        f"the run did not see the mutated tree: {r.answer}"
    )
    assert r.field("wt_gone") == "y" and r.clones() == [], "a mutated clone outlived its run"


def test_mutate_refuses_an_expression_that_changes_nothing(gate):
    r = gate("--mutate", "target.txt", "s/absent/MUTATED/", "tests/x.py")
    assert r.field("step") == "mutate", (
        f"a mutation that changed nothing was run as if it had: {r.answer}"
    )
    assert r.field("mutated") == "target.txt:0"
    assert r.field("wt_gone") == "y" and r.clones() == []


def test_mutate_refuses_an_expression_that_changes_more_than_one_line(gate):
    r = gate("--mutate", "target.txt", "s/^/MUTATED /", "tests/x.py")
    assert r.field("step") == "mutate", (
        f"a mutation that changed several lines was run as a one-line mutation: {r.answer}"
    )
    assert r.field("mutated") == "target.txt:3"
    assert r.field("wt_gone") == "y" and r.clones() == []
