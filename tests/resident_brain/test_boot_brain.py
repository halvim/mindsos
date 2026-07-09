"""Ephemeral :func:`mindsos_server.boot.boot_brain` smoke.

The durable (Falkor) path is exercised by the live gate; here the
in-memory path proves the Stack boots, tasks, probes, and persists safely.
"""

from __future__ import annotations

from mindsos_server.boot import boot_brain


def test_ephemeral_boot_shape():
    stack = boot_brain(user="alice")
    assert stack.user == "alice"
    view = stack.global_view()
    assert len(list(view.iter_capacities())) > 0
    assert len(list(view.iter_datastates())) > 0


def test_ephemeral_task_runs():
    stack = boot_brain(user="alice")
    outcome = stack.orch.run_lifecycle({"text": "the cat sat"}, task_id="T1")
    assert outcome.status == "succeeded"


def test_ephemeral_save_is_safe():
    stack = boot_brain(user="alice")
    # In-memory persister — save must not raise.
    stack.save()


def test_install_builtins_false_yields_empty_catalog():
    stack = boot_brain(user="alice", install_builtins=False)
    assert len(list(stack.global_view().iter_capacities())) == 0
