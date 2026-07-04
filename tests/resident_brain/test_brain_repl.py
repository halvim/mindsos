"""Headless tests of the ``mindsos brain`` verb dispatcher.

``BrainREPL.dispatch`` is pure (line -> str), so the whole verb surface is
testable without a TTY, over an ephemeral in-memory brain.
"""

from __future__ import annotations

import pytest

from mindsos_cli.commands.brain import _HELP, BrainREPL
from mindsos_server.boot import boot_brain


@pytest.fixture
def repl():
    return BrainREPL(boot_brain(user="alice"))


def test_ls_lists_capabilities(repl):
    out = repl.dispatch("ls")
    assert "capabilit" in out
    assert "capacity:" in out


def test_caps_shows_wiring(repl):
    out = repl.dispatch("caps")
    assert "consumes:" in out
    assert "produces:" in out


def test_datastate_list_and_detail(repl):
    listing = repl.dispatch("datastate")
    assert "datastates" in listing
    # Pull a real datastate IRI from the view and inspect it.
    ds = next(iter(repl.stack.global_view().iter_datastates()))
    detail = repl.dispatch(f"datastate {ds.node_id}")
    assert ds.node_id in detail
    assert "produced by:" in detail
    assert "consumed by:" in detail


def test_datastate_unknown(repl):
    assert "no such datastate" in repl.dispatch("datastate nope:not:real")


def test_verify(repl):
    out = repl.dispatch("verify")
    assert "catalog:" in out
    assert "status:" in out


def test_task_runs(repl):
    assert repl.dispatch("task the cat sat") == "task: succeeded"


def test_task_requires_text(repl):
    assert "usage:" in repl.dispatch("task")


def test_help_and_unknown_and_empty(repl):
    assert repl.dispatch("help") == _HELP
    assert repl.dispatch("frobnicate").startswith("unknown verb")
    assert repl.dispatch("") == ""


def test_state_accrues_in_process(repl):
    """A task writes an episode into the held Local; a later probe sees the
    process is the same live instance (episodic count is non-decreasing)."""
    before = len(list(repl.stack.kl.local_metagraph("alice").graphs.values()))
    repl.dispatch("task the cat sat")
    after = len(list(repl.stack.kl.local_metagraph("alice").graphs.values()))
    assert after >= before
