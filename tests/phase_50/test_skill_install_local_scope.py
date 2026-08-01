"""CORE-C2R1 — a user installs a Skill into their own Local realm.

ADR-0150 §amendment-11 (``installed-skills`` becomes dual-scope),
ADR-0002 §amendment-3 (``USER_CAPS`` gains the two skill-lifecycle
capabilities), ADR-0183 §amendment-6 (the driver takes a ``scope``).

**What this suite exists to prove.** Phase 50 shipped install
Global-only, which made it admin-only in practice — not through
``CAN_INSTALL_SKILL`` but because every write went to
``scope="global"``, and the ADR-0180 gate guards Global writes with
``CAN_WRITE_GLOBAL``. ADR-0205 §8 says a **user** installs a Skill.

Two halves have to hold together, and the second is the one that is easy
to get wrong:

1. the record **lands Local** and a non-admin can put it there;
2. **every roster reader sees it**. Threading the write half alone would
   ship a Skill a user can install and that nothing ever observes — not
   activated at boot, not counted as a satisfied dependency, absent from
   the CLI. The reader assertions below are the real subject of this
   suite.

The Global/admin path keeps its own coverage in
``test_skill_install_driver.py``.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins.text import install_text_capacities
from mindsos_capacity.exceptions import CapabilityDeniedError
from mindsos_knowledge import KnowledgeLayer, ROLE_INSTALLED_SKILLS
from mindsos_knowledge.bootstrap import (
    _GLOBAL_NAMED_ROLES,
    _LOCAL_NAMED_ROLES,
)
from mindsos_server.capabilities import (
    ADMIN_CAPS,
    CAN_INSTALL_SKILL,
    CAN_UNINSTALL_SKILL,
    CAN_WRITE_GLOBAL,
    USER_CAPS,
)
from mindsos_server.skills import (
    apply_installed_skills,
    install_skill,
    latest_records_by_bundle,
    parse_manifest,
    uninstall_skill,
)
from mindsos_server.skills.records import iter_skill_records
from tests.fixtures.skill_bundle_ref import MANIFEST_PATH

USER = "alice"


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
def user_session() -> _FakeSession:
    """A plain user — exactly ``USER_CAPS``, no admin capability."""
    return _FakeSession(USER, USER_CAPS)


@pytest.fixture()
def admin_session() -> _FakeSession:
    return _FakeSession("root", ADMIN_CAPS)


def _install_local(kl, cl, session):
    return install_skill(
        parse_manifest(MANIFEST_PATH),
        kl=kl,
        cl=cl,
        current_phase=50,
        session=session,
        scope="local",
    )


def _role_graph(metagraph):
    for g in metagraph.graphs.values():
        if g.role == ROLE_INSTALLED_SKILLS:
            return g
    return None


# ── the role is dual-scope ─────────────────────────────────────────────


class TestRoleIsDualScope:
    def test_installed_skills_in_both_named_role_sets(self) -> None:
        """ADR-0150 §am-11. §am-6's Global form is untouched."""
        assert ROLE_INSTALLED_SKILLS in _GLOBAL_NAMED_ROLES
        assert ROLE_INSTALLED_SKILLS in _LOCAL_NAMED_ROLES

    def test_closed_role_set_count_unchanged(self) -> None:
        """An existing role gained a scope — the §am-8 precedent.

        16 named entries. ``alignment:`` and ``dataset:`` are prefixes,
        not members of either named set.
        """
        assert len(_GLOBAL_NAMED_ROLES | _LOCAL_NAMED_ROLES) == 16


# ── a user installs Local ──────────────────────────────────────────────


class TestUserInstallsLocal:
    def test_user_caps_alone_suffice(self, kl, cl, user_session) -> None:
        """The capability gate passes for a plain user.

        Before §am-3 this raised: ``USER_CAPS`` was empty, so
        ``CAN_INSTALL_SKILL`` was unreachable for a non-admin.
        """
        assert CAN_INSTALL_SKILL in USER_CAPS
        assert CAN_WRITE_GLOBAL not in USER_CAPS
        result = _install_local(kl, cl, user_session)
        assert result.record.status == "installed"

    def test_record_lands_local_not_global(
        self, kl, cl, user_session
    ) -> None:
        _install_local(kl, cl, user_session)

        local_graph = _role_graph(kl.local_metagraph(USER))
        assert local_graph is not None
        assert len(local_graph.nodes) == 1

        global_graph = _role_graph(kl.global_metagraph())
        assert global_graph is None or not global_graph.nodes

    def test_user_cannot_install_global(self, kl, cl, user_session) -> None:
        """The ADR-0180 gate, not the capability, keeps Global admin-only."""
        with pytest.raises(CapabilityDeniedError):
            install_skill(
                parse_manifest(MANIFEST_PATH),
                kl=kl,
                cl=cl,
                current_phase=50,
                session=user_session,
                scope="global",
            )

    def test_admin_can_still_install_global(
        self, kl, cl, admin_session
    ) -> None:
        install_skill(
            parse_manifest(MANIFEST_PATH),
            kl=kl,
            cl=cl,
            current_phase=50,
            session=admin_session,
            scope="global",
        )
        assert _role_graph(kl.global_metagraph()).nodes


# ── every reader sees it — the point of the item ───────────────────────


class TestReadersAreScopeAware:
    def test_roster_readers_need_the_user(self, kl, cl, user_session) -> None:
        """Without ``user_id`` the Local install is invisible.

        This asymmetry is deliberate: omitting ``user_id`` is the
        pre-§am-11 Global-only read, still correct for admin and system
        callers. Passing it unions the user's realm in.
        """
        _install_local(kl, cl, user_session)

        assert latest_records_by_bundle(kl) == {}
        assert iter_skill_records(kl) == []

        assert "ref-skill" in latest_records_by_bundle(kl, USER)
        assert [v.bundle_name for v in iter_skill_records(kl, USER)] == [
            "ref-skill"
        ]

    def test_activation_sees_a_local_install(
        self, kl, cl, user_session
    ) -> None:
        """Boot must activate what the user installed for themselves."""
        _install_local(kl, cl, user_session)

        fresh = CapacityLayer()
        install_text_capacities(fresh)
        report = apply_installed_skills(fresh, kl, user_id=USER)
        assert report.activated == ("ref-skill",)

    def test_activation_without_user_activates_nothing(
        self, kl, cl, user_session
    ) -> None:
        _install_local(kl, cl, user_session)

        fresh = CapacityLayer()
        install_text_capacities(fresh)
        assert apply_installed_skills(fresh, kl).activated == ()

    def test_local_shadows_global_for_that_user(
        self, kl, cl, user_session, admin_session
    ) -> None:
        """Global first, Local second — the user's own state governs.

        ``seq`` is minted over the unioned set, so the Local record is
        strictly later and wins on the highest-``seq`` rule.
        """
        install_skill(
            parse_manifest(MANIFEST_PATH),
            kl=kl,
            cl=cl,
            current_phase=50,
            session=admin_session,
            scope="global",
        )
        uninstall_skill(
            "ref-skill", kl=kl, session=user_session, scope="local"
        )

        assert latest_records_by_bundle(kl)["ref-skill"].status == "installed"
        assert (
            latest_records_by_bundle(kl, USER)["ref-skill"].status
            == "uninstalled"
        )


# ── uninstall ──────────────────────────────────────────────────────────


class TestUserUninstallsLocal:
    def test_user_removes_their_own(self, kl, cl, user_session) -> None:
        assert CAN_UNINSTALL_SKILL in USER_CAPS
        _install_local(kl, cl, user_session)
        uninstall_skill(
            "ref-skill", kl=kl, session=user_session, scope="local"
        )
        latest = latest_records_by_bundle(kl, USER)
        assert latest["ref-skill"].status == "uninstalled"

    def test_user_cannot_uninstall_global(
        self, kl, cl, admin_session, user_session
    ) -> None:
        install_skill(
            parse_manifest(MANIFEST_PATH),
            kl=kl,
            cl=cl,
            current_phase=50,
            session=admin_session,
            scope="global",
        )
        with pytest.raises(CapabilityDeniedError):
            uninstall_skill(
                "ref-skill", kl=kl, session=user_session, scope="global"
            )
