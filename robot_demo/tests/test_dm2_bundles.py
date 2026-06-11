"""DM-2 — bundles + DataStates + Local seeds + per-device persistence.

Two layers (mirrors test_dm1_bootstrap):
  * **Core** tests run on any host (incl. the 3.10 Cowork sandbox): they
    exercise the demo-authored pieces that need only mindsos_capacity /
    mindsos_knowledge — manifest→schema validity (PB-X regression),
    the §4.0 DataState installer (idempotent triple), Local embodiment
    seeds (PB-W), and the P-8 bundle-selection map.
  * **Integration** tests exercise the real Phase-50 ``install_skill``
    gate + per-device Falkor persistence; they import mindsos_server
    lazily and skip where the host can't run it (Python < 3.11 / argon2).

DM-2 gate (plan §8): bundles install idempotently; seeds visible when
querying the per-device KL; an episode round-trips Falkor (or fallback
documented); the DM-1 smoke stays green (4 brains, 4 Episodes).
"""

from __future__ import annotations

import hashlib

import pytest

from mindsos_capacity import CapacityLayer
from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.schemas import schema_for_role
from mindsos_core.models.graph import Graph

from robot_demo.backend.bundles import BUNDLES_ROOT, manifest_path
from robot_demo.backend.installers import (
    install_core_datastates,
    installed_robot_datastates,
    robot_datastate_iris,
    ROBOT_DATASTATE_NAMES,
)
from robot_demo.backend.profiles import DEVICE_ORDER, DEVICE_PROFILES
from robot_demo.backend.seeds import (
    EMBODIMENT,
    read_local_embodiment,
    seed_local_embodiment,
)

try:  # tomllib is 3.11+; the sandbox is 3.10 → tomli
    import tomllib as _toml
except ModuleNotFoundError:  # pragma: no cover
    import tomli as _toml


class _DuckSession:
    """Local-write session (Local writes don't hit the ADR-0180 Global gate)."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.session_id = f"sess-{user_id}"
        self.actor_role = "user"
        self.capabilities = frozenset()

    def has(self, capability: str) -> bool:
        return True


# ── Core: every backend module imports (guards latent top-level NameErrors
# in modules the rest of the sandbox suite only imports lazily). ──────────

def test_all_backend_modules_import():
    import importlib
    for mod in ("bootstrap", "brain", "bundles", "installers", "main",
                "measure", "persistence", "profiles", "reset", "seeds"):
        importlib.import_module(f"robot_demo.backend.{mod}")
    # the PB-JJ dedicated graph constant resolves
    from robot_demo.backend.persistence import _DEMO_GRAPH
    assert _DEMO_GRAPH


# ── Core: every bundle manifest parses + L2 node_types are schema-valid ──
# (PB-X regression — type registration is enforced even at strict=False.)

def test_all_manifests_parse_and_l2_is_schema_valid():
    graphs = {}

    def role_graph(role):
        if role not in graphs:
            graphs[role] = Graph(
                name=role, role=role, schema=schema_for_role(role, strict=False)
            )
        return graphs[role]

    manifests = sorted(BUNDLES_ROOT.glob("*/manifest.toml"))
    assert len(manifests) == 5, [m.parent.name for m in manifests]
    total = 0
    for mf in manifests:
        raw = mf.read_bytes()
        data = _toml.loads(raw.decode())
        bundle = data["bundle"]
        assert bundle["requires_mindsos_phase"] == 50
        # stable, content-derived digest (PB-CC)
        assert hashlib.sha256(raw).hexdigest()
        for entry in data.get("l2", {}).get("content", []) or []:
            assert entry["tier"] == "global"  # bundles are Global-only (S3)
            g = role_graph(entry["role"])
            g.add_node(  # raises UnknownTypeError if the type is unregistered
                entry.get("value"),
                entry["node_type"],
                properties={**(entry.get("properties") or {}),
                            "installed_by": f"{bundle['name']}@{bundle['version']}"},
                node_id=entry["iri"],
            )
            total += 1
    assert total == 26  # 8 core + 15 manager + 1*3 type bundles


def test_core_bundle_declares_robot_realm():
    with open(manifest_path("core"), "rb") as fh:
        data = _toml.loads(fh.read().decode())
    l3 = data["l3"]
    assert l3["installers"] == ["robot_demo.backend.installers:install_core_datastates"]
    assert "robot" in l3["allow_new_realm"]


# ── Core: §4.0 DataState installer (idempotent triple) ──────────────────

def test_install_core_datastates_idempotent():
    kl = KnowledgeLayer.bootstrap()
    cl = CapacityLayer(kl=kl)
    assert len(robot_datastate_iris()) == 32
    install_core_datastates(cl)
    assert len(installed_robot_datastates(cl)) == 32
    install_core_datastates(cl)  # re-activation no-op
    assert len(installed_robot_datastates(cl)) == 32


def test_install_core_datastates_partial_detected():
    from robot_demo.backend.installers import _robot_datastate
    from mindsos_capacity.exceptions import CapacityRegistrationError

    kl = KnowledgeLayer.bootstrap()
    cl = CapacityLayer(kl=kl)
    cl.register_datastate(_robot_datastate(ROBOT_DATASTATE_NAMES[0]),
                          allow_new_realm=True)
    with pytest.raises(CapacityRegistrationError):
        install_core_datastates(cl)


# ── Core: Local embodiment seeds (PB-W) ─────────────────────────────────

def test_local_embodiment_seeds_idempotent_and_visible():
    for device_id in DEVICE_ORDER:
        kl = KnowledgeLayer.bootstrap()
        kl.local_metagraph(device_id)
        session = _DuckSession(device_id)
        assert seed_local_embodiment(kl, session, device_id) is True
        assert seed_local_embodiment(kl, session, device_id) is False  # idempotent
        bag = read_local_embodiment(kl, device_id)
        assert bag is not None
        assert bag["provides"] == EMBODIMENT[device_id]["provides"]
        assert bag["reach"] == EMBODIMENT[device_id]["reach"]


def test_arm_affordances_distinct():
    assert read_or_spec("arm1")["provides"] == ["grasp:suction"]
    assert read_or_spec("arm2")["provides"] == ["grasp:jaw"]
    assert read_or_spec("mgr")["provides"] == []  # manager has no body


def read_or_spec(device_id):
    return EMBODIMENT[device_id]


# ── Core: P-8 device-type-exclusive bundle selection ────────────────────

def test_bundle_selection_is_device_type_exclusive():
    selection = {d: DEVICE_PROFILES[d].bundle_names for d in DEVICE_ORDER}
    # core installs everywhere
    assert all("core" in names for names in selection.values())
    # each type bundle appears on exactly one device
    for type_bundle, owner in [
        ("manager", "mgr"), ("arm-suction", "arm1"),
        ("arm-jaw", "arm2"), ("conveyor", "conv"),
    ]:
        owners = [d for d, names in selection.items() if type_bundle in names]
        assert owners == [owner], (type_bundle, owners)
    # all selected bundles resolve to a real manifest on disk
    for names in selection.values():
        for b in names:
            assert manifest_path(b)


# ── Core: reset wipes run-state, keeps the embodiment seed (G-11) ───────

def test_wipe_local_run_state_keeps_seed():
    from robot_demo.backend.brain import build_brain_stack
    from robot_demo.backend.reset import wipe_local_run_state
    from robot_demo.backend.seeds import read_local_embodiment

    profile = DEVICE_PROFILES["arm1"]
    session = _DuckSession("arm1")
    brain = build_brain_stack(profile, session)
    try:
        seed_local_embodiment(brain.kl, session, "arm1")
        brain.il.enqueue(
            lambda: brain.orch.run_lifecycle({"text": "x"}, task_id="reset-ep")
        ).result(timeout=30)
        # an Episode now exists in the Local
        from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
        from mindsos_knowledge.metagraph_view import MetagraphView
        ep_g = MetagraphView(
            brain.kl.local_metagraph("arm1")
        ).graphs_by_role(ROLE_EPISODIC_MEMORIES)[0]
        n_ep = sum(1 for n in ep_g.nodes.values()
                   if getattr(n, "type_name", None) == "Episode")
        assert n_ep >= 1

        removed = wipe_local_run_state(brain)
        assert removed >= n_ep
        # embodiment seed survives; episodes gone
        assert read_local_embodiment(brain.kl, "arm1") is not None
        assert all(getattr(n, "type_name", None) != "Episode"
                   for n in ep_g.nodes.values())
    finally:
        brain.il.stop()


# ── Integration: real install_skill gate + per-device persistence ───────

@pytest.mark.integration
def test_install_skill_idempotent_same_kl(tmp_path):
    """Real Phase-50 install_skill: install core twice on one device's KL;
    second call is a digest-match no-op (S8). No Falkor needed."""
    pytest.importorskip("argon2")
    try:
        import mindsos_server  # noqa: F401
        from mindsos_server.skills.driver import install_skill
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"mindsos_server unavailable: {exc}")

    from robot_demo.backend.bootstrap import _ensure_users, _login_admin
    from mindsos_server._db import open_db

    with open_db(str(tmp_path / "server.db")) as conn:
        _ensure_users(conn)
        admin = _login_admin(conn)

    kl = KnowledgeLayer.bootstrap()
    cl = CapacityLayer(kl=kl)
    r1 = install_skill(manifest_path("core"), kl=kl, cl=cl,
                       session=admin, current_phase=50)
    assert r1.no_op is False and r1.l2_written
    r2 = install_skill(manifest_path("core"), kl=kl, cl=cl,
                       session=admin, current_phase=50)
    assert r2.no_op is True  # same name+version+digest → no-op
    assert len(installed_robot_datastates(cl)) == 32  # installer ran once


@pytest.mark.integration
def test_full_bootstrap_dm2(tmp_path):
    """Full DM-2 bootstrap: bundles install per device-type, seeds visible,
    4 Episodes, idempotent re-boot. Falkor parts asserted only when a live
    FalkorDB is present (else graceful in-memory fallback, PB-Z/G-5)."""
    pytest.importorskip("argon2")
    try:
        import mindsos_server  # noqa: F401
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"mindsos_server unavailable: {exc}")

    from robot_demo.backend.bootstrap import bootstrap

    r1 = bootstrap(db_path=str(tmp_path / "server.db"))
    try:
        assert r1.ok and r1.total_episodes == 4
        # P-8 selective install reflected in the result
        assert r1.bundles["mgr"][0].startswith("core")
        assert any("manager@1.0" in b for b in r1.bundles["mgr"])
        assert any("arm-suction@1.0" in b for b in r1.bundles["arm1"])
        assert all(r1.seeded_local[d] for d in DEVICE_ORDER)
        # seeds visible by querying the per-device KL
        assert read_local_embodiment(r1.brains["arm1"].kl, "arm1")["provides"] \
            == ["grasp:suction"]
        from robot_demo.backend.installers import installed_robot_datastates
        assert len(installed_robot_datastates(r1.brains["mgr"].cl)) == 32

        if r1.persisted_global:
            # G-5: episode round-trip via the ADR-0182 codec (or documented)
            assert r1.episode_roundtrip is not None
            # idempotent re-boot: bundles no-op on the reloaded Global
            r2 = bootstrap(db_path=str(tmp_path / "server.db"))
            try:
                assert r2.ok and r2.total_episodes == 4
                assert any("(no-op)" in b for b in r2.bundles["mgr"])
            finally:
                for b in r2.brains.values():
                    b.il.stop()
    finally:
        for b in r1.brains.values():
            b.il.stop()
