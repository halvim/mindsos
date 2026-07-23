"""``python -m nilm_brain.repl`` — boot nilm as a RESIDENT mindsos brain and open
the mindsos brain REPL over it.

This is the arc1 pattern (`arc1_brain/repl.py`): boot the real resident stack
via ``mindsos_server.boot.boot_brain``, install the nilm L3 (ontology +
capacities + the finder-composed segments) into it, then hand the stack to the
**same** ``BrainREPL``/``loop`` that ``mindsos brain`` drives. So the verbs
(``ls``, ``caps``, ``ds``, ``pl``, ``search``, ``invoke``, ``verify`` …) run
against a live stack that has nilm installed.

Ephemeral by default (no Falkor sidecar needed) — the brain boots, you inspect
and invoke it live, nothing persists. ``--durable`` boots on the Falkor sidecar
(Local metagraph persists across restarts); that is the durable-L2 slice and
needs the container up (see docker-compose), Linux only.

    PYTHONPATH=.:projects/amii_study python -m nilm_brain.repl            # ephemeral
    PYTHONPATH=.:projects/amii_study python -m nilm_brain.repl --durable  # Falkor

Note: the generic REPL exposes probe + single-capacity ``invoke``. The full
appliance recognize loop (L4 window fan-out + k-NN) is driven through the
``Solver`` API (`recognize_appliance`) or `scripts/appliance_recognize_demo.py`;
exposing it as a REPL ``task``/verb is the skill-declared-brain-verb slice.
"""
from __future__ import annotations

import sys

from mindsos_server.boot import boot_brain
from mindsos_cli.commands.brain import BrainREPL, loop

from nilm_brain.control import Solver


def main() -> None:
    durable = "--durable" in sys.argv
    client = None
    if durable:
        from mindsos_core.config import FalkorConfig
        from mindsos_core.persistence.client import FalkorClient
        client = FalkorClient(FalkorConfig.from_env())
    try:
        stack = boot_brain(client, user="nilm")
        # Install the nilm L3 into the resident stack (the arc1 install_arc step):
        # the Solver constructor registers the ontology + all capacities into the
        # given cl/session and composes the segments — here against the real stack.
        Solver("nilm", cl=stack.cl, session=stack.session)
        print("nilm resident brain booted "
              f"({'durable/Falkor' if durable else 'ephemeral'}). "
              "Try: ls · caps nilm:* · pl · verify · help")
        loop(BrainREPL(stack))
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    main()
