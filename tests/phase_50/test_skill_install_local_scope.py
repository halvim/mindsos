"""CORE-C2R1 — a user installs a Skill into their own Local realm.

ADR-0150 §amendment-11 (``installed-skills`` becomes dual-scope),
ADR-0002 §amendment-3 (``USER_CAPS`` gains the skill-lifecycle
capabilities), ADR-0183 §amendment-6 (the driver takes a ``scope``).

**What this suite exists to prove.** Phase 50 shipped install Global-only,
which made it admin-only in practice — not through ``CAN_INSTALL_SKILL``
but because every write went to ``scope="global"``, and the ADR-0180 gate
guards Global writes with ``CAN_WRITE_GLOBAL``. ADR-0205 §8 says a
**user** installs a Skill.

Three things have to hold together, and the first gate run proved the
last two are where it goes wrong:

1. the install **record** lands Local and a plain user can put it there;
2. the bundle's **content** goes where the *manifest* says
   (``[[l2.content]].tier``) — the record's realm decides nothing about
   it, and conflating the two silently redirects a bundle's content;
3. **every roster reader sees it** — otherwise the write half ships a
   Skill nothing observes: not activated at boot, not counted as a
   satisfied dependency, absent from the CLI.

The Global/admin path keeps its coverage in
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
    install_skill,
    latest_records_by_bundle,
    parse_manifest,
    uninstall_skill,
)
from mindsos_server.skills.records import iter_skill_records
from tests.fixtures.skill_bundle_local import (
    MANIFEST_PATH as LOCAL_MANIFEST_PATH,
)
from tests.fixtures.skill_bundle_ref import MANIFEST_PATH as REF_MANIFEST_PATH

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


def _install_local(kl, cl, session, **kwargs):
    """Install the Local-tier bundle; ``scope`` left to follow the principal."""
    return install_skill(
        parse_manifest(LOCAL_MANIFEST_PATH),
        kl=kl,
        cl=cl,
        current_phase=50,
        session=session,
        **kwargs,
    )


def _role_graph(metagraph, role=ROLE_INSTALLED_SKILLS):
    for g in metagraph.graphs.values():
        if g.role == role:
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

        ``alignment:`` and ``dataset:`` are prefixes, not members.
        """
        assert len(_GLOBAL_NAMED_ROLES | _LOCAL_NAMED_ROLES) == 16


# ── a user installs Local ──────────────────────────────────────────────


class TestUserInstallsLocal:
    def test_user_caps_alone_suffice(self, kl, cl, user_session) -> None:
        """The capability gate passes for a plain user.

        Before §am-3 this was unreachable: ``USER_CAPS`` was empty.
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

    def test_global_tier_content_is_refused_for_a_user(
        self, kl, cl, user_session
    ) -> None:
        """The manifest decides the content's realm, not the caller.

        The reference bundle declares every entry at ``tier = "global"``,
        so it needs ``CAN_WRITE_GLOBAL`` whoever installs it. A user
        installing it must be refused at the ADR-0180 gate — **not**
        silently redirected into their own realm, which is what
        overriding the manifest's tier would do.
        """
        with pytest.raises((CapabilityDeniedError, Exception)) as excinfo:
            install_skill(
                parse_manifest(REF_MANIFEST_PATH),
                kl=kl,
                cl=cl,
                current_phase=50,
                session=user_session,
            )
        assert "ref-skill" not in latest_records_by_bundle(kl)
        assert excinfo.value is not None

    def test_admin_can_still_install_global(
        self, kl, cl, admin_session
    ) -> None:
        install_skill(
            parse_manifest(REF_MANIFEST_PATH),
            kl=kl,
            cl=cl,
            current_phase=50,
            session=admin_session,
            scope="global",
        )
        assert _role_graph(kl.global_metagraph()).nodes


# ── scope follows the principal ────────────────────────────────────────


class TestScopeFollowsThePrincipal:
    def test_no_session_records_global(self, kl, cl) -> None:
        """A session-less system caller must not attempt a Local write.

        ``KnowledgeLayer.writeable`` scopes Local writes by user, so
        there is no coherent Local destination without a session. A fixed
        ``scope="local"`` default raised for every bootstrap caller — the
        first gate run caught it across nine activation tests and the CLI.
        """
        install_skill(
            parse_manifest(REF_MANIFEST_PATH),
            kl=kl,
            cl=cl,
            current_phase=50,
            session=None,
        )
        assert "ref-skill" in latest_records_by_bundle(kl)

    def test_explicit_scope_wins_over_the_principal(
        self, kl, cl, admin_session
    ) -> None:
        install_skill(
            parse_manifest(REF_MANIFEST_PATH),
            kl=kl,
            cl=cl,
            current_phase=50,
            session=admin_session,
            scope="global",
        )
        assert "ref-skill" in latest_records_by_bundle(kl)


# ── every reader sees it — the point of the item ───────────────────────


class TestReadersAreScopeAware:
    def test_roster_readers_need_the_user(self, kl, cl, user_session) -> None:
        """Without ``user_id`` the Local install is invisible.

        Deliberate: omitting ``user_id`` is the pre-§am-11 Global-only
        read, still correct for admin and system callers.
        """
        _install_local(kl, cl, user_session)

        assert latest_records_by_bundle(kl) == {}
        assert iter_skill_records(kl) == []

        assert "local-skill" in latest_records_by_bundle(kl, USER)
        assert [v.bundle_name for v in iter_skill_records(kl, USER)] == [
            "local-skill"
        ]

    def test_reading_a_roster_never_mints_a_local(self, kl) -> None:
        """A read must not lazily create the user's Local metagraph.

        ``local_metagraph`` lazy-creates. Materialising an empty Local
        while merely reading a roster would run ahead of the durable boot
        that restores one.
        """
        assert not kl.has_local("nobody")
        assert iter_skill_records(kl, "nobody") == []
        assert not kl.has_local("nobody")

    def test_local_shadows_global_for_that_user(
        self, kl, cl, user_session, admin_session
    ) -> None:
        """Global first, Local second — the user's own state governs.

        ``seq`` is minted over the unioned set, so the Local record is
        strictly later and wins on the highest-``seq`` rule.
        """
        install_skill(
            parse_manifest(REF_MANIFEST_PATH),
            kl=kl,
            cl=cl,
            current_phase=50,
            session=admin_session,
            scope="global",
        )
        assert latest_records_by_bundle(kl)["ref-skill"].status == "installed"

        _install_local(kl, cl, user_session)
        by_user = latest_records_by_bundle(kl, USER)
        assert set(by_user) == {"ref-skill", "local-skill"}
        assert by_user["local-skill"].seq > by_user["ref-skill"].seq


# ── uninstall ──────────────────────────────────────────────────────────


class TestUserUninstallsLocal:
    def test_user_removes_their_own(self, kl, cl, user_session) -> None:
        assert CAN_UNINSTALL_SKILL in USER_CAPS
        _install_local(kl, cl, user_session)
        uninstall_skill("local-skill", kl=kl, session=user_session)
        latest = latest_records_by_bundle(kl, USER)
        assert latest["local-skill"].status == "uninstalled"

    def test_user_cannot_uninstall_global(
        self, kl, cl, admin_session, user_session
    ) -> None:
        install_skill(
            parse_manifest(REF_MANIFEST_PATH),
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
