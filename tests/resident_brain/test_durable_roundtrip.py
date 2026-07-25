"""Live durable round-trip for the resident brain (``@pytest.mark.integration``).

This is the FIRST end-to-end consumer of Episode save→load against a live
FalkorDB: boot a durable brain, run a task (consolidation writes an Episode
into the user's Local), persist on ``save``, then boot a SECOND brain for
the same user and assert the Episode survived the Falkor round-trip.

If this passes it closes the paper-open carry-forwards L0-25 (live
FalkorDBLocalPersister round-trip coverage) and L0-26 (durable Episode
persistence) by exercising them; if the ADR-0182 dict-value codec has a
latent gap on a full Local-with-episodes, it surfaces here.
"""

from __future__ import annotations

import pytest

from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
from mindsos_knowledge.metagraph_view import MetagraphView


def _episode_count(kl, user: str) -> int:
    graphs = MetagraphView(kl.local_metagraph(user)).graphs_by_role(ROLE_EPISODIC_MEMORIES)
    if not graphs:
        return 0
    return len(graphs[0].nodes)


@pytest.mark.integration
def test_durable_episode_roundtrip(falkordb_clean):
    from mindsos_core.config import FalkorConfig
    from mindsos_core.persistence.client import FalkorClient
    from mindsos_server.boot import boot_brain

    user = "durable_user"

    # ── First brain: task + persist ────────────────────────────────────
    client = FalkorClient(FalkorConfig.from_env())
    try:
        stack = boot_brain(client, user=user)
        outcome = stack.orch.run_lifecycle({"text": "the cat sat"}, request_id="D1")
        assert outcome.status == "succeeded"
        written = _episode_count(stack.kl, user)
        assert written > 0, "task did not write an Episode into the Local"
        stack.save()  # persist Local (incl. episodic_memories) to Falkor
    finally:
        client.close()

    # ── Second brain: reload + assert the Episode survived ─────────────
    client2 = FalkorClient(FalkorConfig.from_env())
    try:
        stack2 = boot_brain(client2, user=user)
        reloaded = _episode_count(stack2.kl, user)
        assert reloaded >= written, (
            f"Episode did not survive the Falkor round-trip: "
            f"wrote {written}, reloaded {reloaded}"
        )
    finally:
        client2.close()
