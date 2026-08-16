"""Guards on the Gate-7 cold-run driver.

Five ways the driver could report a green gate that means nothing. Each
test names one and is shown RED by a named mutation of
:mod:`decision_records_demo.dr_demo_run` (listed in the ship note); a
guard that cannot go red is worse than none (RULES §9).

No FalkorDB, no docker, no network: the backend is a fake, which is the
point — the driver's judgement is separable from the environment it
judges, and that separation is what makes these guards runnable on the
same bare interpreter as the other demo guards.

    PYTHONPATH=. python3 decision_records_demo/test_dr_run_guards.py
"""

from __future__ import annotations

from decision_records_demo import dr_demo_run
from decision_records_demo.dr_demo_run import (
    EXIT_OK,
    EXIT_RUN_FAILED,
    cold_run,
    plan_child_commands,
    run_gate,
    verify_pages_output,
)

#: What a good pages run prints. Built from the driver's own markers so a
#: marker rename cannot leave this fixture silently agreeing with itself.
GOOD_OUTPUT = (
    "== case: claim — Episode 'drdemo-page-claim' ==\n"
    f"{dr_demo_run.REVERIFY_MARKER} ... ==\n"
    "end-state 'claim': store-alone page matches except the date line\n"
    f"{dr_demo_run.TALLY_PREFIX}0\n"
)


class FakeBackend:
    """Records what the driver did to it; answers what the test dictates."""

    def __init__(self, node_count=0, pages=(0, GOOD_OUTPUT), raise_on_pages=None):
        self.node_count = node_count
        self.pages = pages
        self.raise_on_pages = raise_on_pages
        self.up_calls = []
        self.down_calls = []
        self.pages_calls = 0

    def store_up(self, index):
        self.up_calls.append(index)

    def store_down(self, index):
        self.down_calls.append(index)

    def store_node_count(self):
        return self.node_count

    def run_pages(self, screens_dir):
        self.pages_calls += 1
        if self.raise_on_pages:
            raise self.raise_on_pages
        return self.pages


def test_a_render_gap_fails_the_run():
    """A page that raised is a failed run, whatever the tally line says.

    MUTATION: drop the exit-code and RENDER RAISED clauses from
    verify_pages_output (the "it printed a tally, ship it" reading)."""
    raised = GOOD_OUTPUT + f"{dr_demo_run.RAISED_MARKER}: RendererGapError: no manifest\n"
    outcome = cold_run(FakeBackend(pages=(1, raised)), 1)
    assert not outcome.ok, "a run whose page raised was reported green"
    assert "exited 1" in outcome.reason, outcome.reason
    # And the same output with a ZERO exit — the shape a swallowed
    # RendererGapError would produce — must still be refused.
    assert verify_pages_output(raised, 0) is not None, \
        "a raised page was accepted because the script exited 0"


def test_run_two_starts_from_an_empty_store():
    """A store with anything in it is run 1's leftovers — refuse BEFORE
    any case runs, so the failure names the dirty store rather than
    whatever node theft it would have caused (§55, one level up).

    MUTATION: run the cases first and check emptiness after."""
    backend = FakeBackend(node_count=7)
    outcome = cold_run(backend, 2)
    assert not outcome.ok, "a run against a dirty store was reported green"
    assert "not empty" in outcome.reason, outcome.reason
    assert backend.pages_calls == 0, "cases ran against a store known to be dirty"


def test_each_run_is_a_new_process():
    """Three runs, three subprocesses — not one interpreter looping.

    MUTATION: replace the spawn call in run_gate with an in-process
    cold_run loop; this test reddens on the sentinel below."""
    def _no_in_process(*args, **kwargs):
        raise AssertionError("the parent ran a case in its own process")

    saved = dr_demo_run.cold_run
    dr_demo_run.cold_run = _no_in_process
    seen = []
    try:
        code = run_gate(cold_runs=3, port=6382,
                        spawn=lambda argv: (seen.append(list(argv)), (EXIT_OK, ""))[1])
    finally:
        dr_demo_run.cold_run = saved
    assert code == EXIT_OK, code
    assert len(seen) == 3, seen
    indices = [argv[argv.index("--single-run") + 1] for argv in seen]
    assert indices == ["1", "2", "3"], indices
    planned = plan_child_commands(3, 6382)
    assert len({tuple(argv) for argv in planned}) == 3, planned


def test_teardown_runs_even_when_a_run_fails():
    """A failed run must not hand its container to the next one.

    MUTATION: move store_down out of the finally block."""
    backend = FakeBackend(raise_on_pages=OSError("docker vanished"))
    outcome = cold_run(backend, 1)
    assert not outcome.ok, "a driver fault was reported as a green run"
    assert backend.down_calls == [1], backend.down_calls


def test_end_state_reverify_is_enforced_by_the_driver():
    """Exit 0 and a zero tally are not enough: without the re-verify, no
    page was ever re-rendered from the store alone, and the reconstructibility
    claim — the closer's whole content — went unchecked.

    MUTATION: drop the REVERIFY_MARKER clause from verify_pages_output."""
    without = GOOD_OUTPUT.replace(dr_demo_run.REVERIFY_MARKER, "== something else")
    assert verify_pages_output(without, 0) is not None, \
        "a run with no end-state re-verify was accepted"
    outcome = cold_run(FakeBackend(pages=(0, without)), 1)
    assert not outcome.ok, outcome
    assert outcome.index == 1 and cold_run(FakeBackend(), 1).ok, \
        "the good-output fixture no longer passes — the fixture drifted, not the guard"


if __name__ == "__main__":
    for fn in sorted(
        (v for k, v in list(globals().items()) if k.startswith("test_")),
        key=lambda f: f.__name__,
    ):
        fn()
        print(f"PASS {fn.__name__}")
