"""Phase 50 — skill-activation resilience (ADR-0183 §am-2).

Boot must not die because one installed bundle's L3 installer is absent
(cross-venv/lane) or broken. Activation is best-effort at boot
(``strict=False``) and strict on explicit invocation (``strict=True``,
the default). These tests pin both sides plus the additive-inert
``ActivationReport`` return shape.

They construct install records directly (via ``append_record`` on a
bootstrapped, Falkor-free ``KnowledgeLayer``) so a *malformed* or
*unimportable* installer spec — which the install-time manifest parser
would reject — can still be planted, mimicking a durable Global record
authored by another checkout.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins.text import install_text_capacities
from mindsos_capacity.context import make_writeable
from mindsos_knowledge import KnowledgeLayer
from mindsos_server.skills import (
    ActivationReport,
    EntryPointError,
    apply_installed_skills,
    install_skill,
    parse_manifest,
)
from mindsos_server.skills.records import append_record
from tests.fixtures.skill_bundle_ref import MANIFEST_PATH
from tests.fixtures.skill_bundle_ref.installer import CAP_REF_SHOUT

_RAISING_INSTALLER = (
    "tests.phase_50.test_skill_activation_resilience:_raising_installer"
)


def _raising_installer(cl) -> None:
    """An importable installer that fails mid-apply (partial-state case)."""
    raise RuntimeError("boom — installer failed after import")


@pytest.fixture()
def kl() -> KnowledgeLayer:
    return KnowledgeLayer.bootstrap()


def _fresh_cl() -> CapacityLayer:
    cl = CapacityLayer()
    install_text_capacities(cl)
    return cl


def _install_ref(kl) -> None:
    """Install the good reference bundle onto ``kl`` (record + L2)."""
    manifest = parse_manifest(MANIFEST_PATH)
    install_skill(manifest, kl=kl, cl=_fresh_cl(), current_phase=50)


def _plant_record(kl, name: str, installers, *, capacities=(), requires=()) -> None:
    """Append an ``installed`` record directly (Global, session-less)."""
    append_record(
        writeable=make_writeable(kl, None),
        kl=kl,
        bundle_name=name,
        bundle_version="0.1.0",
        bundle_digest="0" * 64,
        status="installed",
        action="install",
        value={
            "l3_installers": list(installers),
            "l3_capacities": list(capacities),
            "requires_bundles": list(requires),
        },
    )


# ── absent / unimportable module (the reported mindsos_arc case) ───────


class TestUnresolvedModule:
    def test_skipped_when_not_strict(self, kl) -> None:
        _install_ref(kl)
        _plant_record(kl, "ghost", ["nonexistent.module:install"])
        cl = _fresh_cl()

        report = apply_installed_skills(cl, kl, strict=False)

        # Good bundle still activates; the absent one is skipped, reported.
        assert "ref-skill" in report.activated
        assert "ghost" not in report.activated
        assert "ghost" in [name for name, _ in report.skipped]
        # Layer is usable — the good bundle's capacity is registered.
        mg = cl.global_metagraph()
        assert CAP_REF_SHOUT in cl._capacity_index[mg.metagraph_id]

    def test_raises_when_strict(self, kl) -> None:
        _plant_record(kl, "ghost", ["nonexistent.module:install"])
        with pytest.raises(EntryPointError):
            apply_installed_skills(_fresh_cl(), kl, strict=True)

    def test_strict_is_the_default(self, kl) -> None:
        _plant_record(kl, "ghost", ["nonexistent.module:install"])
        with pytest.raises(EntryPointError):
            apply_installed_skills(_fresh_cl(), kl)


# ── malformed spec (corrupt durable record; parser would have rejected) ─


class TestMalformedSpec:
    def test_skipped_when_not_strict(self, kl) -> None:
        _plant_record(kl, "corrupt", ["no-colon-here"])
        report = apply_installed_skills(_fresh_cl(), kl, strict=False)
        assert "corrupt" in [name for name, _ in report.skipped]

    def test_raises_when_strict(self, kl) -> None:
        _plant_record(kl, "corrupt", ["no-colon-here"])
        with pytest.raises(EntryPointError):
            apply_installed_skills(_fresh_cl(), kl, strict=True)


# ── missing attribute on an importable module ──────────────────────────


class TestMissingAttribute:
    def test_skipped_when_not_strict(self, kl) -> None:
        _plant_record(
            kl,
            "noattr",
            ["tests.fixtures.skill_bundle_ref.installer:does_not_exist"],
        )
        report = apply_installed_skills(_fresh_cl(), kl, strict=False)
        assert "noattr" in [name for name, _ in report.skipped]

    def test_raises_when_strict(self, kl) -> None:
        _plant_record(
            kl,
            "noattr",
            ["tests.fixtures.skill_bundle_ref.installer:does_not_exist"],
        )
        with pytest.raises(EntryPointError):
            apply_installed_skills(_fresh_cl(), kl, strict=True)


# ── installer imports fine but raises mid-apply (partial state) ────────


class TestApplyFailure:
    def test_skipped_when_not_strict(self, kl) -> None:
        _install_ref(kl)
        _plant_record(kl, "breaks", [_RAISING_INSTALLER])
        report = apply_installed_skills(_fresh_cl(), kl, strict=False)
        # The raising bundle is skipped (not a resolve error — an apply
        # error), and the good bundle still activates.
        assert "ref-skill" in report.activated
        assert "breaks" not in report.activated
        reasons = dict(report.skipped)
        assert "breaks" in reasons
        assert "apply-failed" in reasons["breaks"]

    def test_raises_when_strict(self, kl) -> None:
        _plant_record(kl, "breaks", [_RAISING_INSTALLER])
        # A mid-apply failure is NOT masked under strict — the original
        # RuntimeError propagates (not wrapped as EntryPointError).
        with pytest.raises(RuntimeError):
            apply_installed_skills(_fresh_cl(), kl, strict=True)


# ── happy path + backward-compatible return shape ──────────────────────


class TestHappyPathAndReturnShape:
    def test_happy_path_no_skips(self, kl) -> None:
        _install_ref(kl)
        report = apply_installed_skills(_fresh_cl(), kl, strict=False)
        assert report.activated == ("ref-skill",)
        assert report.skipped == ()

    def test_report_is_a_tuple_of_activated_names(self, kl) -> None:
        _install_ref(kl)
        report = apply_installed_skills(_fresh_cl(), kl)
        # Additive-inert: the historical Tuple[str, ...] contract holds.
        assert isinstance(report, ActivationReport)
        assert isinstance(report, tuple)
        assert report == ("ref-skill",)
        assert list(report) == ["ref-skill"]
        assert ", ".join(report) == "ref-skill"

    def test_empty_when_nothing_installed(self, kl) -> None:
        report = apply_installed_skills(_fresh_cl(), kl, strict=False)
        assert report == ()
        assert report.skipped == ()


# -- advisory capacity verification (log-only) --------------------------


def _noop_installer(cl) -> None:
    return None


class TestAdvisoryVerify:
    def test_missing_declared_capacity_warns_but_activates(self, kl, caplog) -> None:
        import logging

        _plant_record(
            kl,
            "hollow",
            ["tests.phase_50.test_skill_activation_resilience:_noop_installer"],
            capacities=["capacity:test:ghost.absent"],
        )
        with caplog.at_level(logging.WARNING):
            report = apply_installed_skills(_fresh_cl(), kl, strict=False)
        assert "hollow" in report.activated
        assert "hollow" not in [n for n, _ in report.skipped]
        assert any(
            "declared capacities are not registered" in r.getMessage()
            for r in caplog.records
        )

    def test_declared_capacity_present_no_warning(self, kl, caplog) -> None:
        import logging

        _install_ref(kl)
        with caplog.at_level(logging.WARNING):
            report = apply_installed_skills(_fresh_cl(), kl, strict=False)
        assert "ref-skill" in report.activated
        assert not any(
            "declared capacities are not registered" in r.getMessage()
            for r in caplog.records
        )
