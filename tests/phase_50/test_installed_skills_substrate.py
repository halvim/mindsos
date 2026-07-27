"""Phase 50 (SA-1) — `installed-skills` role-graph substrate.

ADR-0150 §am-6 (closed role-set 12 → 13) + ADR-0183 §5: role constant +
IRI builder/minter/parser + schema (Global-only, ``append_only``) +
bootstrap presence + capability/audit constants (Phase-44 S8 additive
pattern).
"""

from __future__ import annotations

import pytest

from mindsos_knowledge import (
    ALL_ROLES,
    KnowledgeLayer,
    ROLE_INSTALLED_SKILLS,
    UPPER_LAYER_ROLES,
    build_installed_skills_schema,
    parse_iri,
    schema_for_role,
    skill_install_record_iri,
)
from mindsos_knowledge.bootstrap import (
    _APPLIES_AFTER_BY_ROLE,
    _GLOBAL_NAMED_ROLES,
    _LOCAL_NAMED_ROLES,
    ensure_global_role_graph,
    ensure_local_role_graph,
)
from mindsos_knowledge.exceptions import KnowledgeError
from mindsos_knowledge.schemas import _ROLE_SCHEMA_BUILDERS, Discipline
from mindsos_knowledge.schemas.installed_skills import (
    INSTALLED_SKILLS_EDGE_TYPES,
    INSTALLED_SKILLS_NODE_TYPES,
    NODE_SKILL_INSTALL_RECORD,
    SKILL_INSTALL_ACTIONS,
    SKILL_INSTALL_STATUSES,
    STORAGE_MODE_FIELDS,
)


# ── role constant + closed-set membership (ADR-0150 §am-6) ────────────


class TestRoleConstant:
    def test_role_value(self) -> None:
        assert ROLE_INSTALLED_SKILLS == "installed-skills"

    def test_in_upper_layer_and_all_roles(self) -> None:
        assert ROLE_INSTALLED_SKILLS in UPPER_LAYER_ROLES
        assert ROLE_INSTALLED_SKILLS in ALL_ROLES

    def test_closed_set_is_13(self) -> None:
        # feat/subminds grew the closed role-set 13 → 14 per ADR-0150
        # §amendment-7 (subminds). The Phase-50 closure sentinel updates
        # forward, mirroring how Phase 50 updated the Phase-43 12 → 13.
        assert len(ALL_ROLES) == 16

    def test_global_only_scope(self) -> None:
        assert ROLE_INSTALLED_SKILLS in _GLOBAL_NAMED_ROLES
        assert ROLE_INSTALLED_SKILLS not in _LOCAL_NAMED_ROLES

    def test_applies_after_declared_empty(self) -> None:
        assert _APPLIES_AFTER_BY_ROLE[ROLE_INSTALLED_SKILLS] == frozenset()


# ── IRI builder + minter + parser ──────────────────────────────────────


class TestSkillInstallRecordIri:
    def test_shape(self) -> None:
        iri = skill_install_record_iri("1", "wsd-bundle", "0.1.0:1")
        assert iri == "installed-skills-1:record:wsd-bundle:0.1.0:1"

    def test_parse_round_trip(self) -> None:
        iri = skill_install_record_iri("1", "wsd-bundle", "0.1.0:2")
        parsed = parse_iri(iri)
        assert parsed.full == iri
        assert parsed.role == ROLE_INSTALLED_SKILLS
        assert parsed.kind == "record"
        assert parsed.body == "wsd-bundle:0.1.0:2"

    def test_minter_dispatch(self) -> None:
        from mindsos_knowledge.identifiers import _IRI_BUILDERS

        minter = _IRI_BUILDERS[
            (ROLE_INSTALLED_SKILLS, NODE_SKILL_INSTALL_RECORD)
        ]
        iri = minter("1", bundle_name="b", record_id="0.1.0:1")
        assert iri == skill_install_record_iri("1", "b", "0.1.0:1")

    def test_minter_missing_kwarg_raises_key_error(self) -> None:
        from mindsos_knowledge.identifiers import _IRI_BUILDERS

        minter = _IRI_BUILDERS[
            (ROLE_INSTALLED_SKILLS, NODE_SKILL_INSTALL_RECORD)
        ]
        with pytest.raises(KeyError):
            minter("1", bundle_name="b")


# ── schema (ADR-0183 §5 + ADR-0153 append_only) ───────────────────────


class TestInstalledSkillsSchema:
    def test_dispatch_table_has_role(self) -> None:
        assert ROLE_INSTALLED_SKILLS in _ROLE_SCHEMA_BUILDERS

    def test_schema_for_role_dispatches(self) -> None:
        s = schema_for_role(ROLE_INSTALLED_SKILLS)
        assert NODE_SKILL_INSTALL_RECORD in s.node_types

    def test_discipline_is_append_only(self) -> None:
        s = build_installed_skills_schema()
        assert s.mutation_discipline is Discipline.APPEND_ONLY

    def test_single_node_type_no_edge_types(self) -> None:
        assert INSTALLED_SKILLS_NODE_TYPES == (NODE_SKILL_INSTALL_RECORD,)
        assert INSTALLED_SKILLS_EDGE_TYPES == ()

    def test_strict_kwarg_plumbed(self) -> None:
        assert build_installed_skills_schema(strict=True).strict is True
        assert build_installed_skills_schema().strict is False

    def test_storage_mode_declares_value_only(self) -> None:
        assert STORAGE_MODE_FIELDS == {
            NODE_SKILL_INSTALL_RECORD: frozenset({"value"}),
        }

    def test_status_and_action_vocabularies(self) -> None:
        assert SKILL_INSTALL_STATUSES == {
            "installed", "uninstalled", "failed",
        }
        assert SKILL_INSTALL_ACTIONS == {
            "install", "uninstall", "install-failed",
        }


# ── bootstrap (Global-only scope routing) ─────────────────────────────


class TestBootstrap:
    def test_kl_bootstrap_ensures_installed_skills(self) -> None:
        kl = KnowledgeLayer.bootstrap()
        roles = {g.role for g in kl.global_metagraph().graphs.values()}
        assert ROLE_INSTALLED_SKILLS in roles

    def test_not_in_lazy_local(self) -> None:
        kl = KnowledgeLayer.bootstrap()
        local = kl.local_metagraph("alice")
        roles = {g.role for g in local.graphs.values()}
        assert ROLE_INSTALLED_SKILLS not in roles

    def test_ensure_global_idempotent(self) -> None:
        kl = KnowledgeLayer.bootstrap()
        mg = kl.global_metagraph()
        g1 = ensure_global_role_graph(mg, ROLE_INSTALLED_SKILLS)
        g2 = ensure_global_role_graph(mg, ROLE_INSTALLED_SKILLS)
        assert g1 is g2

    def test_ensure_local_rejects(self) -> None:
        kl = KnowledgeLayer.bootstrap()
        local = kl.local_metagraph("alice")
        with pytest.raises(KnowledgeError):
            ensure_local_role_graph(local, ROLE_INSTALLED_SKILLS)


# ── capabilities + audit constants (Phase-44 S8 additive pattern) ─────


class TestCapabilitiesAndAudit:
    def test_capability_values(self) -> None:
        from mindsos_server.capabilities import (
            CAN_INSTALL_SKILL,
            CAN_UNINSTALL_SKILL,
        )

        assert CAN_INSTALL_SKILL == "CAN_INSTALL_SKILL"
        assert CAN_UNINSTALL_SKILL == "CAN_UNINSTALL_SKILL"

    def test_capabilities_admin_bundled_user_denied(self) -> None:
        from mindsos_server.capabilities import (
            ADMIN_CAPS,
            ALL_CAPABILITIES,
            CAN_INSTALL_SKILL,
            CAN_UNINSTALL_SKILL,
            USER_CAPS,
        )

        for cap in (CAN_INSTALL_SKILL, CAN_UNINSTALL_SKILL):
            assert cap in ALL_CAPABILITIES
            assert cap in ADMIN_CAPS
            assert cap not in USER_CAPS

    def test_audit_event_values_and_roster(self) -> None:
        from mindsos_server.audit import (
            ALL_AUDIT_EVENTS,
            EVT_SKILL_INSTALL_REJECTED,
            EVT_SKILL_INSTALLED,
            EVT_SKILL_UNINSTALLED,
        )

        assert EVT_SKILL_INSTALLED == "EVT_SKILL_INSTALLED"
        assert EVT_SKILL_UNINSTALLED == "EVT_SKILL_UNINSTALLED"
        assert EVT_SKILL_INSTALL_REJECTED == "EVT_SKILL_INSTALL_REJECTED"
        for evt in (
            EVT_SKILL_INSTALLED,
            EVT_SKILL_UNINSTALLED,
            EVT_SKILL_INSTALL_REJECTED,
        ):
            assert evt in ALL_AUDIT_EVENTS

    def test_phase_44_event_drift_fixed(self) -> None:
        """EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY was declared at Phase 44
        but omitted from ALL_AUDIT_EVENTS; Phase 50 appends it per the
        'new events append' contract (latent-drift fix)."""
        from mindsos_server.audit import (
            ALL_AUDIT_EVENTS,
            EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY,
        )

        assert EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY in ALL_AUDIT_EVENTS
