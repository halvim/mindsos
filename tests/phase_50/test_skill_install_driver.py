"""Phase 50 (SA-1) — skill-bundle install lifecycle (ADR-0183).

Pass criterion per the phase-map §2 row (R0-SA-2, verbatim): validates
**install / de-install / provenance / idempotency ONLY** — NOT
"installed skill runs" (the v0 lifecycle dispatches no real L3 capacity;
Phase 49 PB-1a is WSD's). Exercises the trivial reference bundle
(``tests/fixtures/skill_bundle_ref``) end-to-end:
install → verify → de-install → re-install.
"""

from __future__ import annotations

import sqlite3

import pytest

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins.text import install_text_capacities
from mindsos_knowledge import KnowledgeLayer, ROLE_INSTALLED_SKILLS
from mindsos_server._schema import init_or_migrate
from mindsos_server.audit import (
    EVT_SKILL_INSTALL_REJECTED,
    EVT_SKILL_INSTALLED,
    EVT_SKILL_UNINSTALLED,
)
from mindsos_server.capabilities import (
    ADMIN_CAPS,
    CAN_INSTALL_SKILL,
    CAN_WRITE_GLOBAL,
)
from mindsos_server.skills import (
    ManifestError,
    SkillInstallError,
    SkillInstallRejectedError,
    SkillUninstallRefusedError,
    apply_installed_skills,
    install_skill,
    iter_skill_records,
    latest_records_by_bundle,
    parse_manifest,
    run_preflight,
    uninstall_skill,
)
from tests.fixtures.skill_bundle_ref import MANIFEST_PATH
from tests.fixtures.skill_bundle_ref.installer import (
    CAP_REF_SHOUT,
    DS_REF_SHOUTED,
)


class _FakeSession:
    """Minimal SessionProtocol shape: ``user_id`` + ``has``."""

    def __init__(self, user_id: str, capabilities: frozenset[str]) -> None:
        self.user_id = user_id
        self.session_id = f"sess-{user_id}"
        self._caps = capabilities

    def has(self, capability: str) -> bool:
        return capability in self._caps


@pytest.fixture()
def kl() -> KnowledgeLayer:
    return KnowledgeLayer.bootstrap()


@pytest.fixture()
def cl() -> CapacityLayer:
    layer = CapacityLayer()
    install_text_capacities(layer)
    return layer


@pytest.fixture()
def audit_conn():
    conn = sqlite3.connect(":memory:")
    init_or_migrate(conn)
    yield conn
    conn.close()


def _audit_events(conn) -> list[str]:
    return [
        row[0] for row in conn.execute("SELECT event FROM audit ORDER BY id")
    ]


# CORE-C2R1 (ADR-0150 §am-11 / ADR-0183 §am-6): install/uninstall now
# default to ``scope="local"``. These suites exercise the ADMIN /
# Global path, so every call is explicit about it. The Local path
# has its own suite: tests/phase_50/test_skill_install_local_scope.py


def _install(kl, cl, **kwargs):
    manifest = parse_manifest(MANIFEST_PATH)
    kwargs.setdefault("scope", "global")
    return install_skill(
        manifest, kl=kl, cl=cl, current_phase=50, **kwargs
    )


# ── manifest parsing ───────────────────────────────────────────────────


class TestManifest:
    def test_reference_manifest_parses(self) -> None:
        m = parse_manifest(MANIFEST_PATH)
        assert m.name == "ref-skill"
        assert m.version == "0.1.0"
        assert m.requires_mindsos_phase == 50
        assert len(m.l2_content) == 3
        assert m.l3_capacities == (CAP_REF_SHOUT,)
        assert m.l3_datastates == (DS_REF_SHOUTED,)
        assert m.l4_slots["demo_slot"] == "ref-skill-opaque-l4-fill"
        assert len(m.digest) == 64
        assert m.provenance_tag == "ref-skill@0.1.0"

    def test_missing_file_raises(self, tmp_path) -> None:
        with pytest.raises(ManifestError):
            parse_manifest(tmp_path / "absent.toml")

    def test_bad_toml_raises(self, tmp_path) -> None:
        p = tmp_path / "bad.toml"
        p.write_text("[bundle\nname=")
        with pytest.raises(ManifestError):
            parse_manifest(p)

    def test_missing_bundle_table_raises(self, tmp_path) -> None:
        p = tmp_path / "m.toml"
        p.write_text('[l3]\ninstallers = []\n')
        with pytest.raises(ManifestError):
            parse_manifest(p)

    def test_malformed_entry_point_raises(self, tmp_path) -> None:
        p = tmp_path / "m.toml"
        p.write_text(
            '[bundle]\nname = "x"\nversion = "1"\n'
            '[l3]\ninstallers = ["no-colon-here"]\n'
        )
        with pytest.raises(ManifestError):
            parse_manifest(p)


# ── install (S7) + provenance ─────────────────────────────────────────


class TestInstall:
    def test_install_writes_content_runs_installers_appends_record(
        self, kl, cl, audit_conn
    ) -> None:
        result = _install(kl, cl, audit_conn=audit_conn)
        assert result.no_op is False
        assert len(result.l2_written) == 3
        assert result.installers_run == (
            "tests.fixtures.skill_bundle_ref.installer:install_ref_skill",
        )
        # L3 registered on the live layer.
        mg = cl.global_metagraph()
        assert CAP_REF_SHOUT in cl._capacity_index[mg.metagraph_id]
        # Record state + ADR-0182 rule-5 flat lift.
        view = latest_records_by_bundle(kl)["ref-skill"]
        assert view.status == "installed"
        assert view.action == "install"
        assert view.seq == 1
        assert view.value["l3_capacities"] == [CAP_REF_SHOUT]
        assert view.value["l4_slots"] == {
            "demo_slot": "ref-skill-opaque-l4-fill"
        }
        # Audit row (S6 provenance split).
        assert _audit_events(audit_conn) == [EVT_SKILL_INSTALLED]

    def test_l2_nodes_carry_provenance_tag(self, kl, cl) -> None:
        _install(kl, cl)
        g = next(
            g
            for g in kl.global_metagraph().graphs.values()
            if g.role == "concepts"
        )
        node = g.nodes["ref-skill-0.1.0:concept:shouting"]
        assert node.properties["installed_by"] == "ref-skill@0.1.0"

    def test_record_lives_in_installed_skills_role_graph(self, kl, cl) -> None:
        result = _install(kl, cl)
        g = next(
            g
            for g in kl.global_metagraph().graphs.values()
            if g.role == ROLE_INSTALLED_SKILLS
        )
        assert result.record.iri in g.nodes
        assert isinstance(g.nodes[result.record.iri].value, dict)

    def test_capability_gate(self, kl, cl) -> None:
        no_caps = _FakeSession("mallory", frozenset())
        with pytest.raises(PermissionError):
            _install(kl, cl, session=no_caps)
        # CAN_INSTALL_SKILL alone is not enough — the ADR-0180 gate
        # denies the Global write without CAN_WRITE_GLOBAL.
        install_only = _FakeSession("eve", frozenset({CAN_INSTALL_SKILL}))
        from mindsos_capacity.exceptions import CapabilityDeniedError

        with pytest.raises(CapabilityDeniedError):
            _install(kl, cl, session=install_only)

    def test_admin_session_passes_both_gates(self, kl, cl) -> None:
        admin = _FakeSession("alice", ADMIN_CAPS)
        result = _install(kl, cl, session=admin)
        assert result.no_op is False
        assert CAN_WRITE_GLOBAL in ADMIN_CAPS  # the co-requirement


# ── idempotency (S8) ──────────────────────────────────────────────────


class TestIdempotency:
    def test_same_digest_reinstall_is_no_op(self, kl, cl, audit_conn) -> None:
        _install(kl, cl)
        result = _install(kl, cl, audit_conn=audit_conn)
        assert result.no_op is True
        assert len(iter_skill_records(kl)) == 1  # no second record
        events = _audit_events(audit_conn)
        assert events == [EVT_SKILL_INSTALLED]  # audited no-op

    def test_same_version_different_digest_rejected(
        self, kl, cl, tmp_path, audit_conn
    ) -> None:
        _install(kl, cl)
        tampered = tmp_path / "manifest.toml"
        tampered.write_bytes(
            MANIFEST_PATH.read_bytes() + b"\n# tampered\n"
        )
        with pytest.raises(SkillInstallRejectedError) as excinfo:
            install_skill(
                parse_manifest(tampered),
                kl=kl,
                cl=cl,
                current_phase=50,
                scope="global",
                audit_conn=audit_conn,
            )
        assert "digest-mismatch" in str(excinfo.value)
        assert _audit_events(audit_conn) == [EVT_SKILL_INSTALL_REJECTED]

    def test_version_change_rejected_upgrade_is_v2(
        self, kl, cl, tmp_path
    ) -> None:
        _install(kl, cl)
        bumped = tmp_path / "manifest.toml"
        bumped.write_text(
            MANIFEST_PATH.read_text().replace(
                'version = "0.1.0"', 'version = "0.2.0"'
            )
        )
        with pytest.raises(SkillInstallRejectedError) as excinfo:
            install_skill(
                parse_manifest(bumped),
                kl=kl,
                cl=cl,
                current_phase=50,
                scope="global",
            )
        assert "version-change" in str(excinfo.value)

    def test_failed_install_appends_failed_record_then_repairs(
        self, kl, cl, tmp_path
    ) -> None:
        broken = tmp_path / "manifest.toml"
        broken.write_text(
            MANIFEST_PATH.read_text().replace(
                "installer:install_ref_skill", "installer:does_not_exist"
            )
        )
        with pytest.raises(SkillInstallError):
            install_skill(
                parse_manifest(broken),
                kl=kl,
                cl=cl,
                current_phase=50,
                scope="global",
            )
        view = latest_records_by_bundle(kl)["ref-skill"]
        assert view.status == "failed"
        assert view.action == "install-failed"
        assert any(
            step.startswith("l2:") for step in view.value["completed_steps"]
        )
        # Repair: re-run with the GOOD manifest of the same version.
        # Digest differs from the broken one, but the L2 ownership tag
        # waives the partials and the run completes.
        result = _install(kl, cl)
        assert result.no_op is False
        assert latest_records_by_bundle(kl)["ref-skill"].status == "installed"


# ── preflight (S4) ────────────────────────────────────────────────────


class TestPreflight:
    def test_clean_preflight_ok(self, kl, cl) -> None:
        report = run_preflight(
            parse_manifest(MANIFEST_PATH), kl=kl, cl=cl, current_phase=50
        )
        assert report.ok

    def test_phase_requirement_rejects(self, kl, cl) -> None:
        report = run_preflight(
            parse_manifest(MANIFEST_PATH), kl=kl, cl=cl, current_phase=49
        )
        assert not report.ok
        assert any(f.code == "phase-unsatisfied" for f in report.findings)

    def test_missing_required_bundle_rejects(self, kl, cl, tmp_path) -> None:
        p = tmp_path / "manifest.toml"
        p.write_text(
            MANIFEST_PATH.read_text().replace(
                "requires_bundles = []",
                'requires_bundles = ["not-installed-bundle"]',
            )
        )
        report = run_preflight(
            parse_manifest(p), kl=kl, cl=cl, current_phase=50
        )
        assert any(
            f.code == "missing-required-bundle" for f in report.findings
        )

    def test_non_global_tier_rejects(self, kl, cl, tmp_path) -> None:
        p = tmp_path / "manifest.toml"
        p.write_text(
            MANIFEST_PATH.read_text().replace(
                'tier = "global"', 'tier = "local"', 1
            )
        )
        report = run_preflight(
            parse_manifest(p), kl=kl, cl=cl, current_phase=50
        )
        assert any(f.code == "tier-not-global" for f in report.findings)

    def test_unknown_role_rejects(self, kl, cl, tmp_path) -> None:
        p = tmp_path / "manifest.toml"
        p.write_text(
            MANIFEST_PATH.read_text().replace(
                'role = "concepts"', 'role = "world-axioms"', 1
            )
        )
        report = run_preflight(
            parse_manifest(p), kl=kl, cl=cl, current_phase=50
        )
        assert any(
            f.code == "unknown-or-non-global-role" for f in report.findings
        )

    def test_local_only_role_rejects(self, kl, cl, tmp_path) -> None:
        p = tmp_path / "manifest.toml"
        p.write_text(
            MANIFEST_PATH.read_text().replace(
                'role = "concepts"', 'role = "episodic_memories"', 1
            )
        )
        report = run_preflight(
            parse_manifest(p), kl=kl, cl=cl, current_phase=50
        )
        assert any(
            f.code == "unknown-or-non-global-role" for f in report.findings
        )

    def test_foreign_capacity_collision_rejects(self, kl, cl, tmp_path) -> None:
        p = tmp_path / "manifest.toml"
        p.write_text(
            MANIFEST_PATH.read_text().replace(
                'capacities = ["capacity:perception:text.ref_shout"]',
                'capacities = ["capacity:perception:text.space_split"]',
            )
        )
        report = run_preflight(
            parse_manifest(p), kl=kl, cl=cl, current_phase=50
        )
        assert any(
            f.code == "capacity-iri-collision" for f in report.findings
        )

    def test_undeclared_new_realm_rejects(self, kl, cl, tmp_path) -> None:
        p = tmp_path / "manifest.toml"
        p.write_text(
            MANIFEST_PATH.read_text().replace(
                'datastates = ["datastate:text.ref_shouted"]',
                'datastates = ["datastate:exotic.thing"]',
            )
        )
        report = run_preflight(
            parse_manifest(p), kl=kl, cl=cl, current_phase=50
        )
        assert any(f.code == "realm-conflict" for f in report.findings)

    def test_declared_new_realm_passes(self, kl, cl, tmp_path) -> None:
        p = tmp_path / "manifest.toml"
        p.write_text(
            MANIFEST_PATH.read_text()
            .replace(
                'datastates = ["datastate:text.ref_shouted"]',
                'datastates = ["datastate:exotic.thing"]',
            )
            .replace(
                "allow_new_realm = []", 'allow_new_realm = ["exotic"]'
            )
        )
        report = run_preflight(
            parse_manifest(p), kl=kl, cl=cl, current_phase=50
        )
        assert not any(f.code == "realm-conflict" for f in report.findings)

    def test_install_rejects_on_preflight_findings(
        self, kl, cl, tmp_path, audit_conn
    ) -> None:
        p = tmp_path / "manifest.toml"
        p.write_text(
            MANIFEST_PATH.read_text().replace(
                "requires_bundles = []",
                'requires_bundles = ["ghost"]',
            )
        )
        with pytest.raises(SkillInstallRejectedError):
            install_skill(
                parse_manifest(p),
                kl=kl,
                cl=cl,
                current_phase=50,
                scope="global",
                audit_conn=audit_conn,
            )
        assert _audit_events(audit_conn) == [EVT_SKILL_INSTALL_REJECTED]
        assert latest_records_by_bundle(kl) == {}  # atomic abort: no record


# ── de-install (S11 + G1) ─────────────────────────────────────────────


class TestUninstall:
    def test_uninstall_deprecates_and_records(self, kl, cl, audit_conn) -> None:
        _install(kl, cl)
        result = uninstall_skill("ref-skill", scope="global", kl=kl, audit_conn=audit_conn)
        assert len(result.deprecated_node_ids) == 3
        # G1 marker-only: nodes still present, visible-but-marked.
        g = next(
            g
            for g in kl.global_metagraph().graphs.values()
            if g.role == "concepts"
        )
        node = g.nodes["ref-skill-0.1.0:concept:shouting"]
        assert "deprecated_at" in node.properties
        view = latest_records_by_bundle(kl)["ref-skill"]
        assert view.status == "uninstalled"
        assert view.action == "uninstall"
        assert _audit_events(audit_conn) == [EVT_SKILL_UNINSTALLED]

    def test_uninstall_absent_bundle_refused(self, kl) -> None:
        with pytest.raises(SkillUninstallRefusedError):
            uninstall_skill("ghost", scope="global", kl=kl)

    def test_double_uninstall_refused(self, kl, cl) -> None:
        _install(kl, cl)
        uninstall_skill("ref-skill", scope="global", kl=kl)
        with pytest.raises(SkillUninstallRefusedError):
            uninstall_skill("ref-skill", scope="global", kl=kl)

    def test_reverse_dependency_refuses(self, kl, cl, tmp_path) -> None:
        _install(kl, cl)
        dependant = tmp_path / "manifest.toml"
        dependant.write_text(
            '[bundle]\nname = "dep-skill"\nversion = "0.1.0"\n'
            'requires_bundles = ["ref-skill"]\n'
        )
        install_skill(
            parse_manifest(dependant),
            kl=kl,
            cl=cl,
            current_phase=50,
            scope="global",
        )
        with pytest.raises(SkillUninstallRefusedError) as excinfo:
            uninstall_skill("ref-skill", scope="global", kl=kl)
        assert "reverse-dependency" in str(excinfo.value)

    def test_reinstall_after_uninstall_reclaims(self, kl, cl) -> None:
        _install(kl, cl)
        uninstall_skill("ref-skill", scope="global", kl=kl)
        result = _install(kl, cl)
        assert result.no_op is False
        g = next(
            g
            for g in kl.global_metagraph().graphs.values()
            if g.role == "concepts"
        )
        node = g.nodes["ref-skill-0.1.0:concept:shouting"]
        assert "deprecated_at" not in node.properties  # re-claimed
        assert latest_records_by_bundle(kl)["ref-skill"].status == "installed"
        # Append-only history: install, uninstall, install.
        actions = [
            v.action
            for v in iter_skill_records(kl)
            if v.bundle_name == "ref-skill"
        ]
        assert actions == ["install", "uninstall", "install"]


# ── activation (S7 stage 2) ───────────────────────────────────────────


class TestActivation:
    def test_fresh_process_activation_re_registers(self, kl, cl) -> None:
        _install(kl, cl)
        fresh = CapacityLayer()
        install_text_capacities(fresh)
        activated = apply_installed_skills(fresh, kl)
        assert activated == ("ref-skill",)
        mg = fresh.global_metagraph()
        assert CAP_REF_SHOUT in fresh._capacity_index[mg.metagraph_id]

    def test_activation_skips_uninstalled(self, kl, cl) -> None:
        _install(kl, cl)
        uninstall_skill("ref-skill", scope="global", kl=kl)
        fresh = CapacityLayer()
        install_text_capacities(fresh)
        assert apply_installed_skills(fresh, kl) == ()

    def test_activation_idempotent_on_warm_layer(self, kl, cl) -> None:
        _install(kl, cl)
        # cl already carries the registrations; activation no-ops via
        # the installer triple.
        assert apply_installed_skills(cl, kl) == ("ref-skill",)
