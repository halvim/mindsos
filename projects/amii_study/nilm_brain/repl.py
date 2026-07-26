"""``python -m nilm_brain.repl`` — boot nilm as a RESIDENT mindsos brain.

A thin per-brain shim over the shipped resident runtime (``boot_brain`` +
``BrainREPL``/``loop``): boot the stack, install nilm's L3, persist its two
finder-composed segments as learned pipelines (ADR-0203), then hand to the
generic REPL. The engine — boot, persister, REPL, ``save`` — is core; the only
nilm-specific lines are the ``Solver`` install and the two ``learn_pipeline``
calls. (The brain-agnostic goal is to skill-package nilm so even this shim goes
away and ``mindsos brain`` runs it; that is a separate slice.)

Ephemeral by default (no Falkor); ``--durable`` boots on the Falkor sidecar and
the REPL's ``save``/``quit`` persists the taught pipelines across reboots.

    PYTHONPATH=.:projects/amii_study python -m nilm_brain.repl
    PYTHONPATH=.:projects/amii_study python -m nilm_brain.repl --durable
"""
from __future__ import annotations

import sys

from mindsos_server.boot import boot_brain
from mindsos_server.pipelines import iter_local_pipelines, learn_pipeline
from mindsos_cli.commands.brain import BrainREPL, loop

from nilm_brain.control import Solver

USER = "nilm"
SEGMENTS = ("cycle_recognition", "appliance_signature")


def _persist_segments(stack, solver) -> None:
    """Persist the finder-composed segments as learned pipelines, ONCE each:
    the ADR-0203 discipline is append-only (``immutable_successor``), so skip any
    name already present or re-boot would churn versions under ``--durable``.
    Non-fatal — a persist/round-trip failure logs and never bricks the brain."""
    segs = {"cycle_recognition": solver.segment,
            "appliance_signature": solver.appliance_segment}
    try:
        have = {str((n.properties or {}).get("pipeline_name"))
                for n in iter_local_pipelines(stack.kl, stack.user)}
    except Exception:
        have = set()
    for name in SEGMENTS:
        if name in have:
            continue
        try:
            learn_pipeline(stack.kl, stack.user, name, segs[name])
        except Exception as e:  # codec/validation guard — persistence is best-effort
            print(f"  (skip persist {name}: {type(e).__name__}: {e})")


def main() -> None:
    durable = "--durable" in sys.argv
    client = None
    if durable:
        from mindsos_core.config import FalkorConfig
        from mindsos_core.persistence.client import FalkorClient
        client = FalkorClient(FalkorConfig.from_env())
    try:
        stack = boot_brain(client, user=USER)
        solver = Solver(USER, cl=stack.cl, session=stack.session)   # install nilm L3
        _persist_segments(stack, solver)
        print(f"nilm resident brain booted "
              f"({'durable/Falkor' if durable else 'ephemeral'}). "
              "Try: pl · ls · caps nilm:* · quit")
        loop(BrainREPL(stack))
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    main()
