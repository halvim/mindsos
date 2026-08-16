"""dr_demo_run — the Gate-7 cold-run driver: three cold runs, no operator intervention.

Gate 7's operative clause is *"run cold on a laptop three times with no
operator intervention"* (demo plan §5 Phase 7). Before this module a run
was four operator commands — start a FalkorDB container on a port the
README warns is contended, build a venv, export ``PYTHONPATH`` and
``FALKORDB_PORT``, run the pages script, tear the container down — and a
person deciding, per run, whether the output looked right. **Four
commands and a human judgement is not "no operator intervention".**

**What "cold" is taken to mean here, stated rather than assumed:** a new
process against a new store. Both halves matter and each has its own
guard. Repeating the cases inside one process would reuse an interpreter
that has already imported, registered and cached; repeating them against
one store would run case ``claim`` of run 2 into the graph run 1 left
behind, which is the §55 scope defect one level up (MERGE by node id
steals nodes across writers sharing a scope). So each run gets its own
container AND its own subprocess, and the store is asserted EMPTY before
any case executes — an assertion that fails loudly rather than a comment
that hopes.

**This module decides nothing about a Record.** It starts a store, runs
:mod:`decision_records_demo.dr_render_pages` unchanged, reads that run's
own stdout for its own verdicts, and tears the store down. Every fact on
every page is the renderer's; the exit code, the tally line and the
narration below are this module's (RULES §11).

**Gate 4, checked in writing before anything was written (the restated
form):** no new capacity CATEGORY beyond ``origin_v0.DECISION_SHAPED_CATEGORIES``
and no new ``FAMILY_RULES`` entry. This module registers **no capacity and
no DataState at all** — it composes cases that already exist. PASS,
vacuously and checkably: ``git diff --stat <pinned_core>..HEAD -- 'mindsos_*'``
is empty for this ship.

**The verdict is read from the pages run's output, not re-derived.**
:func:`verify_pages_output` is pure and is the only place a run is judged
acceptable. A pages run is acceptable when it exited 0, printed its
end-state re-verify header, tallied zero raising cases, and reported no
unexpected store-alone difference. Any one of those absent is a failed
run — including a zero exit code with no re-verify, which is the shape a
future refactor of the pages script would silently produce.

Run it (Linux gate box, the demo's own venv):

    PYTHONPATH=. /tmp/drdemo-venv/bin/python decision_records_demo/dr_demo_run.py

Exit codes: 0 every run green; 1 at least one run failed; 2 usage;
3 the store could not be started or reached.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence, Tuple

EXIT_OK = 0
EXIT_RUN_FAILED = 1
EXIT_USAGE = 2
EXIT_STORE = 3

DEFAULT_COLD_RUNS = 3
DEFAULT_PORT = 6382
DEFAULT_IMAGE = "falkordb/falkordb"

#: Markers this driver reads out of the pages run's own stdout. They are
#: that script's strings, not this one's — a rename there must redden
#: :func:`verify_pages_output`'s guards rather than pass quietly.
REVERIFY_MARKER = "== END-STATE re-verify"
TALLY_PREFIX = "cases that raised: "
UNEXPECTED_MARKER = "UNEXPECTED differences"
RAISED_MARKER = "RENDER RAISED"

PAGES_MODULE = "decision_records_demo/dr_render_pages.py"


class StoreUnavailable(RuntimeError):
    """The store could not be started or reached — not a demo failure."""


@dataclass
class RunOutcome:
    """One cold run's verdict. ``reason`` is empty exactly when ``ok``."""

    index: int
    ok: bool
    reason: str = ""
    stdout: str = ""


def verify_pages_output(stdout: str, exit_code: int) -> Optional[str]:
    """Judge one pages run. ``None`` means acceptable; a string is the reason.

    Pure — no store, no clock, no filesystem. Every clause here is a way a
    run can be green-looking and worthless, and each is pinned by a guard.
    """
    if exit_code != 0:
        return f"the pages run exited {exit_code}"
    if RAISED_MARKER in stdout:
        return "a page raised during the run"
    if REVERIFY_MARKER not in stdout:
        return "the run printed no end-state re-verify"
    if UNEXPECTED_MARKER in stdout:
        return "a store-alone page differed by more than the date line"
    if f"{TALLY_PREFIX}0" not in stdout:
        return "the run did not tally zero raising cases"
    return None


class DockerBackend:
    """The real environment: one container per run, on one port.

    ``falkordb`` and ``mindsos_core`` are imported lazily so the guards
    can import this module in a bare interpreter.
    """

    def __init__(self, port: int = DEFAULT_PORT, image: str = DEFAULT_IMAGE):
        self.port = port
        self.image = image

    def _container(self, index: int) -> str:
        return f"drdemo-gate-run{index}"

    def store_up(self, index: int) -> None:
        name = self._container(index)
        # A leftover container from a killed run is the dirty-store case
        # this driver exists to refuse: remove it, then start clean.
        subprocess.run(["docker", "rm", "-f", name],
                       capture_output=True, check=False)
        started = subprocess.run(
            ["docker", "run", "--rm", "-d", "--name", name,
             "-p", f"{self.port}:6379", self.image],
            capture_output=True, text=True, check=False,
        )
        if started.returncode != 0:
            raise StoreUnavailable(
                f"docker run failed: {started.stderr.strip()}"
            )
        self._wait_ready()

    def _wait_ready(self, attempts: int = 30, pause: float = 0.5) -> None:
        last = ""
        for _ in range(attempts):
            try:
                self._query("RETURN 1 AS ok")
                return
            except Exception as exc:  # noqa: BLE001 — the raw error IS the report
                last = f"{type(exc).__name__}: {exc}"
                time.sleep(pause)
        raise StoreUnavailable(f"store never became reachable — last: {last}")

    def _query(self, cypher: str):
        from mindsos_core.config import FalkorConfig
        from mindsos_core.persistence.client import FalkorClient

        os.environ["FALKORDB_PORT"] = str(self.port)
        client = FalkorClient(FalkorConfig.from_env())
        try:
            return client.run_query(cypher, {})
        finally:
            client.close()

    def store_node_count(self) -> int:
        rows = self._query("MATCH (n) RETURN count(n) AS n").rows
        return int(rows[0]["n"]) if rows else 0

    def run_pages(self, screens_dir: Optional[str]) -> Tuple[int, str]:
        argv = [sys.executable, PAGES_MODULE]
        if screens_dir:
            argv += ["--screens", screens_dir]
        env = dict(os.environ)
        env["FALKORDB_PORT"] = str(self.port)
        env.setdefault("PYTHONPATH", ".")
        done = subprocess.run(argv, capture_output=True, text=True,
                              env=env, check=False)
        return done.returncode, done.stdout + done.stderr

    def store_down(self, index: int) -> None:
        subprocess.run(["docker", "rm", "-f", self._container(index)],
                       capture_output=True, check=False)


def cold_run(backend, index: int, screens_dir: Optional[str] = None) -> RunOutcome:
    """One cold run, start to teardown.

    Teardown is in a ``finally`` on purpose: a run that fails and leaves
    its container up hands run N+1 a dirty store, and run N+1 would then
    fail for a reason that has nothing to do with the code under test.
    """
    backend.store_up(index)
    try:
        occupied = backend.store_node_count()
        if occupied:
            return RunOutcome(
                index, False,
                f"the store was not empty at start: {occupied} nodes",
            )
        code, out = backend.run_pages(screens_dir)
        reason = verify_pages_output(out, code)
        return RunOutcome(index, reason is None, reason or "", out)
    except StoreUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001 — a driver fault is a failed run
        return RunOutcome(index, False, f"{type(exc).__name__}: {exc}")
    finally:
        backend.store_down(index)


def plan_child_commands(
    cold_runs: int,
    port: int,
    screens_dir: Optional[str] = None,
    script: Optional[str] = None,
) -> List[List[str]]:
    """The argv of each child. One command per run, each its own process."""
    here = script or os.path.abspath(__file__)
    commands = []
    for index in range(1, cold_runs + 1):
        argv = [sys.executable, here, "--single-run", str(index),
                "--port", str(port)]
        if screens_dir:
            argv += ["--screens", os.path.join(screens_dir, f"run{index}")]
        commands.append(argv)
    return commands


def _spawn(argv: Sequence[str]) -> Tuple[int, str]:
    done = subprocess.run(list(argv), capture_output=True, text=True,
                          check=False)
    sys.stdout.write(done.stdout)
    sys.stdout.write(done.stderr)
    return done.returncode, done.stdout + done.stderr


def run_gate(
    cold_runs: int = DEFAULT_COLD_RUNS,
    port: int = DEFAULT_PORT,
    screens_dir: Optional[str] = None,
    spawn: Callable[[Sequence[str]], Tuple[int, str]] = _spawn,
) -> int:
    """The parent: N children, N verdicts, one exit code."""
    commands = plan_child_commands(cold_runs, port, screens_dir)
    failed = []
    for index, argv in enumerate(commands, start=1):
        print(f"== cold run {index} of {cold_runs} — {' '.join(argv)} ==")
        code, _ = spawn(argv)
        if code == EXIT_STORE:
            print(f"run {index}: the store was unavailable — not a demo verdict")
            return EXIT_STORE
        if code != EXIT_OK:
            failed.append(index)
        print()
    print(f"== cold runs: {cold_runs}, failed: {len(failed)} {failed or ''} ==")
    return EXIT_OK if not failed else EXIT_RUN_FAILED


def _usage() -> int:
    print("usage: dr_demo_run.py [--cold-runs N] [--port P] [--screens DIR]")
    print("       dr_demo_run.py --single-run I [--port P] [--screens DIR]")
    return EXIT_USAGE


def main(argv: Sequence[str]) -> int:
    args = list(argv[1:])
    single: Optional[int] = None
    cold_runs = DEFAULT_COLD_RUNS
    port = DEFAULT_PORT
    screens_dir: Optional[str] = None
    while args:
        flag = args.pop(0)
        if flag in ("--single-run", "--cold-runs", "--port", "--screens"):
            if not args:
                return _usage()
            value = args.pop(0)
            if flag == "--screens":
                screens_dir = value
                continue
            try:
                number = int(value)
            except ValueError:
                return _usage()
            if flag == "--single-run":
                single = number
            elif flag == "--cold-runs":
                cold_runs = number
            else:
                port = number
        else:
            return _usage()
    if cold_runs < 1:
        return _usage()

    if single is not None:
        try:
            outcome = cold_run(DockerBackend(port=port), single, screens_dir)
        except StoreUnavailable as exc:
            print(f"STORE UNAVAILABLE: {exc}")
            return EXIT_STORE
        if outcome.ok:
            print(f"run {single}: GREEN")
            return EXIT_OK
        print(f"run {single}: FAILED — {outcome.reason}")
        return EXIT_RUN_FAILED

    return run_gate(cold_runs, port, screens_dir)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
