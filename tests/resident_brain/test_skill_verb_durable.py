"""Live durable proof of skill-declared brain verbs (``@integration``).

Installs a bundle whose ``[l4.slots]`` declares verb ``arc`` bound to the
shipped ``phase1_text`` modality, persists to Falkor, boots a FRESH durable
brain, and asserts the ``arc`` verb drives ``run_lifecycle`` with a
modality-stamped ``InputEnvelope``. Reuses ``install_phase1_text`` — no
bespoke capacities.

Requires a live FalkorDB sidecar (auto-skips via the package conftest
probe). The crash-guard and collision branches are unit-tested in
``test_skill_verbs.py``; this file proves only the end-to-end seam.
"""
from __future__ import annotations

import pytest


def _write_manifest(tmp_path):
    from mindsos_capacity.builtins.phase1_text import (
        TEXT_DERIVE_GOAL_IRI,
        TEXT_HINT_IRI,
        TEXT_MAP_IRI,
        TEXT_MODALITY_DS,
        TEXT_PROCESS_IRI,
        TEXT_TASK_PATTERN_IRI,
    )

    p = tmp_path / "manifest.toml"
    p.write_text(
        f"""
[bundle]
name = "brain-verb-skill"
version = "0.1.0"
requires_mindsos_phase = 50
requires_bundles = []

[[l2.content]]
role = "task-patterns"
tier = "global"
node_type = "TaskPattern"
iri = "{TEXT_TASK_PATTERN_IRI}"
value = "{TEXT_TASK_PATTERN_IRI}"

[l2.content.properties]
description = "text task pattern for the brain-verb integration skill."

[l3]
installers = ["mindsos_capacity.builtins.phase1_text:install_phase1_text"]
capacities = []
datastates = []
allow_new_realm = []

[l4.slots]
verb = "arc"
modality = "{TEXT_MODALITY_DS}"
process = "{TEXT_PROCESS_IRI}"
hint = "{TEXT_HINT_IRI}"
derive_goal = "{TEXT_DERIVE_GOAL_IRI}"
map = "{TEXT_MAP_IRI}"
"""
    )
    return p


@pytest.mark.integration
def test_skill_verb_runs_through_durable_brain(falkordb_clean, tmp_path):
    from mindsos_capacity import CapacityLayer
    from mindsos_capacity.builtins.phase1_text import TEXT_MODALITY_DS
    from mindsos_core.config import FalkorConfig
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_core.persistence.client import FalkorClient
    from mindsos_core.reconstruction import MetagraphLoader
    from mindsos_intelligence.ingress import InputEnvelope
    from mindsos_knowledge import KnowledgeLayer
    from mindsos_cli.commands.brain import BrainREPL
    from mindsos_server.boot import boot_brain
    from mindsos_server.skills import install_skill, parse_manifest

    manifest = _write_manifest(tmp_path)

    # ── install into the Falkor-backed Global + persist ────────────────
    client = FalkorClient(FalkorConfig.from_env())
    try:
        loader = MetagraphLoader(client)
        mid = loader.find_by_name("global_knowledge")
        kl = (
            KnowledgeLayer(global_metagraph=loader.load(mid))
            if mid is not None
            else KnowledgeLayer.bootstrap()
        )
        install_skill(
            parse_manifest(manifest), kl=kl, cl=CapacityLayer(), current_phase=50
        )
        MetagraphRepository(client).persist(kl.global_metagraph())
    finally:
        client.close()

    # ── fresh durable brain: the verb + modality profile must appear ───
    client2 = FalkorClient(FalkorConfig.from_env())
    try:
        stack = boot_brain(client2, user="arc_user")
        assert "arc" in stack.skill_verbs, stack.skill_verbs
        assert stack.dispatcher.modality_profiles.get(TEXT_MODALITY_DS) is not None

        seen = []
        real = stack.orch.run_lifecycle

        def _spy(task_input, **kw):
            seen.append(task_input)
            return real(task_input, **kw)

        stack.orch.run_lifecycle = _spy

        out = BrainREPL(stack).dispatch("arc hello world foo")

        assert len(seen) == 1
        env = seen[0]
        assert isinstance(env, InputEnvelope)
        assert env.modality == TEXT_MODALITY_DS
        assert env.value == "hello world foo"
        # Expected happy path on the v0 downstream (same as the durable
        # round-trip smoke). A dont_know here is a real downstream signal,
        # not a test bug — the seam assertions above still hold.
        assert out == "succeeded", out
    finally:
        client2.close()
