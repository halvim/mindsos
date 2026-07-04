"""Authoritative e2e: ARC installs through the real Phase-50 skill path.

Requires Python 3.11+ (mindsos_server uses datetime.UTC) — runs on the Linux
gate, not the 3.10 build sandbox. Mirrors `mindsos skill install`:
bootstrapped KL + text-only CapacityLayer, session-less (ADR-0080 carve-out).
"""
from __future__ import annotations

from importlib import resources

from mindsos_capacity import CapacityLayer
from mindsos_capacity.bootstrap import ensure_datastate_graph
from mindsos_capacity.builtins.text import install_text_capacities
from mindsos_knowledge import KnowledgeLayer
from mindsos_server.skills import (
    apply_installed_skills,
    install_skill,
    latest_records_by_bundle,
)


def _manifest_path() -> str:
    return str(resources.files("mindsos_arc").joinpath("bundle/manifest.toml"))


def _cl() -> CapacityLayer:
    cl = CapacityLayer()
    install_text_capacities(cl)
    return cl


def test_install_records_and_registers_catalog():
    kl = KnowledgeLayer.bootstrap()
    cl = _cl()
    res = install_skill(_manifest_path(), kl=kl, cl=cl)  # session=None carve-out
    assert res.no_op is False
    assert res.bundle_name == "arc"
    assert latest_records_by_bundle(kl)["arc"].status == "installed"
    dsg = ensure_datastate_graph(cl.global_metagraph(), strict=cl._strict)
    assert any(str(n).startswith("datastate:arc.") for n in dsg.nodes)


def test_reinstall_same_digest_is_no_op():
    kl = KnowledgeLayer.bootstrap()
    install_skill(_manifest_path(), kl=kl, cl=_cl())
    res2 = install_skill(_manifest_path(), kl=kl, cl=_cl())
    assert res2.no_op is True


def test_activation_replays_installer_idempotently():
    kl = KnowledgeLayer.bootstrap()
    install_skill(_manifest_path(), kl=kl, cl=_cl())
    # activate on a fresh layer → re-runs install_arc (cold) → returns ('arc',)
    activated = apply_installed_skills(_cl(), kl)
    assert "arc" in activated
    # activate twice on the SAME warm layer → install_arc must no-op, not raise
    warm = _cl()
    apply_installed_skills(warm, kl)
    apply_installed_skills(warm, kl)
