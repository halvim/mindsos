"""Live durable proof of ADR-0183 §am-5 — installed-skill Local capabilities.

Installs a bundle declaring a ``[[l3.local_capacity]]``, persists to Falkor,
boots a FRESH durable brain, and asserts the capability is registered
metadata-only in the booting user's Local (no skill code ran), then builds its
live function on first use — both via a direct ``invoke`` and through the
``invoke`` brain verb (reachability). ``@integration`` — auto-skips without a
live FalkorDB sidecar.
"""

from __future__ import annotations

import pytest


def _write_manifest(tmp_path):
    p = tmp_path / "manifest.toml"
    p.write_text(
        """
[bundle]
name = "local-cap-skill"
version = "0.1.0"
requires_mindsos_phase = 50
requires_bundles = []

[l3]
installers = ["tests.fixtures.skill_bundle_ref.local_cap:install_local_cap_skill"]
capacities = []
datastates = []
allow_new_realm = []

[[l3.local_capacity]]
name = "text.lc_shout"
category = "perception"
reactivation_key = "ref-local-shout"
inputs = ["datastate:text.lc_in"]
outputs = ["datastate:text.lc_out"]
"""
    )
    return p


@pytest.mark.integration
def test_local_cap_installs_boots_builds_and_is_verb_reachable(
    falkordb_clean, tmp_path
):
    from mindsos_capacity import CapacityLayer
    from mindsos_core.config import FalkorConfig
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_core.persistence.client import FalkorClient
    from mindsos_core.reconstruction import MetagraphLoader
    from mindsos_knowledge import KnowledgeLayer
    from mindsos_cli.commands.brain import BrainREPL
    from mindsos_server.boot import boot_brain
    from mindsos_server.skills import install_skill, parse_manifest
    from tests.fixtures.skill_bundle_ref.local_cap import (
        CAP_LC,
        DS_LC_IN,
        DS_LC_OUT,
    )

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
        # CORE-C2R1: this suite persists the GLOBAL metagraph, so the
        # install must land Global (the driver now defaults to "local").
        install_skill(
            parse_manifest(manifest),
            kl=kl,
            cl=CapacityLayer(),
            current_phase=50,
            scope="global",
        )
        MetagraphRepository(client).persist(kl.global_metagraph())
    finally:
        client.close()

    # ── fresh durable brain: registered metadata-only, builds on first use ─
    client2 = FalkorClient(FalkorConfig.from_env())
    try:
        stack = boot_brain(client2, user="lc_user")

        # registered + planner-selectable in the user's Local; function NOT
        # built (boot ran no skill code) — metadata only.
        assert CAP_LC in stack.cl._declarations, CAP_LC
        assert stack.cl._declarations[CAP_LC].implementation is None
        assert not stack.local_caps_failed, stack.local_caps_failed

        # first use builds the live function + runs it
        res = stack.cl.invoke(CAP_LC, {DS_LC_IN: "hello"}, session=stack.session)
        assert res.success, res.error
        assert res.outputs[DS_LC_OUT] == "HELLO"
        assert stack.cl._declarations[CAP_LC].implementation is not None

        # reachable through the `invoke` brain verb (a person can run it)
        out = BrainREPL(stack).dispatch("invoke text.lc_shout world")
        assert "WORLD" in out, out
    finally:
        client2.close()
