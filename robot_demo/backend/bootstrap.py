"""DM-1 bootstrap — idempotent, run on container start.

Sequence (plan §1.3, with Round-5 step 0):
  0. init server.db schema (``init_or_migrate``) — REQUIRED before any
     ``insert_user`` on a fresh volume (PB-S).
  1. get-or-create admin (``_insert_first_admin``).
  2. get-or-create 4 brain users (``insert_user``).
  3. real ``login()`` per user → real Session (P9 — not ``for_testing``).
  4. per-device stack (``build_brain_stack``) — own KL/CL/IL/Orchestrator,
     IL started (``dream_interval_s=None``).
  5. smoke: one trivial ``run_lifecycle`` per brain on its IL worker pool;
     assert ``consolidation_enabled`` + 4 Episodes consolidate.

DM-1 do-nots (stubbed, not run): skill bundles (§3.4), Local seeds (§3.3),
demo L3 capacities (§4), bus/sim/UI. Marked `# DM-2`/`# DM-3` below.

Idempotency (P6): get-or-create via an existence query (not catch-and-
swallow). ``init_or_migrate`` is ``CREATE TABLE IF NOT EXISTS``. Per-device
KLs are in-memory at DM-1 (PB-J) → re-boot idempotency exercises server.db
user state only (PB-R; full KL load-or-mint idempotency is DM-2).

Requires Python 3.12 (mindsos_server uses ``datetime.UTC``); validated on
the Mac/Linux gate host, not the 3.10 Cowork sandbox (design log §6).
"""

from __future__ import annotations

import getpass
import os
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from mindsos_intelligence.consolidation import consolidation_enabled
from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
from mindsos_knowledge.metagraph_view import MetagraphView

from .brain import Brain, build_brain_stack, run_task
from .bundles import manifest_path
from .capacities import register_embodied_capacities
from .persistence import (
    load_or_mint_global,
    persist_global,
    probe_episode_roundtrip,
)
from .profiles import DEVICE_ORDER, DEVICE_PROFILES
from .seeds import seed_local_embodiment

ADMIN_ID = "admin"

# Demo-fixed credentials (P9). Local demo only — overridable via env; never
# a production secret. Not persisted to memory.
_DEFAULT_PW = "demo-pass"  # noqa: S105 — demo fixture, not a real secret


#: The phase the demo runs against (preflight gate: phase >= bundle's
#: requires_mindsos_phase=50). Overridable for a newer base image.
_CURRENT_PHASE = int(os.environ.get("DEMO_MINDSOS_PHASE", "50"))


def _password_for(user_id: str) -> str:
    return os.environ.get(f"DEMO_PW_{user_id.upper()}", _DEFAULT_PW)


def _falkor_enabled() -> bool:
    """DM-2: persist per-device Globals to Falkor unless explicitly off.
    Off ⇒ DM-1 in-memory path (sandbox / unit tests have no FalkorDB)."""
    return os.environ.get("DEMO_FALKOR", "1") != "0"


def _user_exists(conn: sqlite3.Connection, user_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    return row is not None


def _ensure_users(conn: sqlite3.Connection) -> None:
    """Step 0–2: schema + get-or-create admin + 4 brain users."""
    from mindsos_server._argon2 import PRODUCTION_PARAMS
    from mindsos_server._schema import init_or_migrate
    from mindsos_server.users import _insert_first_admin, insert_user

    init_or_migrate(conn)  # PB-S — idempotent (CREATE TABLE IF NOT EXISTS)

    if not _user_exists(conn, ADMIN_ID):
        _insert_first_admin(
            conn,
            ADMIN_ID,
            _password_for(ADMIN_ID),
            params=PRODUCTION_PARAMS,
            os_user=getpass.getuser(),
        )
        conn.commit()

    for device_id in DEVICE_ORDER:
        if not _user_exists(conn, device_id):
            insert_user(
                conn,
                device_id,
                _password_for(device_id),
                actor_role="user",  # USER_CAPS empty in v1; Local writes ride the gate
                params=PRODUCTION_PARAMS,
                audit_actor=ADMIN_ID,
            )
    conn.commit()


def _login(conn: sqlite3.Connection, user_id: str) -> Any:
    """Real login() for one user → real Session. Clears any stale session
    first (PB-V): login() enforces one active session per user and
    server.db persists across re-boots."""
    from mindsos_server.sessions import kill_my_own_sessions, login

    pw = _password_for(user_id)
    kill_my_own_sessions(conn, user_id, pw)
    return login(conn, user_id, pw).session


def _login_all(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Step 3: real login() per brain user → real Session objects."""
    sessions: Dict[str, Any] = {
        device_id: _login(conn, device_id) for device_id in DEVICE_ORDER
    }
    conn.commit()
    return sessions


def _login_admin(conn: sqlite3.Connection) -> Any:
    """DM-2 (PB-BB): log the admin in so bundle installs ride the REAL
    ADR-0180 gate. ADMIN_CAPS carries CAN_INSTALL_SKILL + CAN_WRITE_GLOBAL
    (vs. the ADR-0080 session=None carve-out, which bypasses the gate and
    wouldn't 'eat the Phase-50 dogfood' per §3.4)."""
    session = _login(conn, ADMIN_ID)
    conn.commit()
    return session


def _install_device_bundles(brain: Brain, admin_session: Any) -> Tuple[str, ...]:
    """DM-2 §3.4 / P-8: admin installs the device-type-selected bundles
    into this brain's own (kl, cl) through the real ``install_skill`` gate.
    Idempotent (Phase-50 S8: same name+version+digest → no-op).

    Bundle selection lives here in robot_demo: ``profile.bundle_names``
    (``core`` everywhere; the type bundle only on its device)."""
    from mindsos_server.skills.driver import install_skill

    installed: list[str] = []
    for bundle_name in brain.profile.bundle_names:
        result = install_skill(
            manifest_path(bundle_name),
            kl=brain.kl,
            cl=brain.cl,
            session=admin_session,
            current_phase=_CURRENT_PHASE,
        )
        installed.append(
            f"{result.bundle_name}@{result.bundle_version}"
            f"{'(no-op)' if result.no_op else ''}"
        )
    return tuple(installed)


@dataclass
class BootstrapResult:
    brains: Dict[str, Brain]
    episodes: Dict[str, int]
    bundles: Dict[str, Tuple[str, ...]] = None  # device → installed bundles
    seeded_local: Dict[str, bool] = None        # device → embodiment written
    persisted_global: bool = False              # DM-2 Falkor Global persist
    episode_roundtrip: Optional[str] = None     # G-5 probe detail (or None)
    embodied: Dict[str, Tuple[str, ...]] = None  # DM-3 device → atomic IRIs
    sim_engine: Any = None                       # DM-3 shared SimEngine (or None)

    @property
    def total_episodes(self) -> int:
        return sum(self.episodes.values())

    @property
    def ok(self) -> bool:
        return self.total_episodes == len(self.brains) == len(DEVICE_ORDER)


def _episode_count(brain: Brain) -> int:
    g = MetagraphView(brain.kl.local_metagraph(brain.device_id)).graphs_by_role(
        ROLE_EPISODIC_MEMORIES
    )[0]
    return sum(
        1 for n in g.nodes.values() if getattr(n, "type_name", None) == "Episode"
    )


def smoke(brains: Dict[str, Brain]) -> Dict[str, int]:
    """Step 5: one trivial lifecycle per brain through its IL worker pool;
    assert consolidation is wired (PB-Q — guard against a silent graceful
    skip) and an Episode lands in each brain's own Local."""
    episodes: Dict[str, int] = {}
    for device_id in DEVICE_ORDER:
        brain = brains[device_id]
        if not consolidation_enabled(brain.dispatcher):
            raise RuntimeError(
                f"[{device_id}] consolidation NOT enabled — consolidate:mm "
                "unregistered or KL unbound (PB-Q); smoke would silently "
                "skip the Episode write."
            )
        future = run_task(
            brain, {"text": "dm1-smoke"}, task_id=f"dm1-smoke-{brain.device_id}"
        )
        outcome = future.result(timeout=30)
        if outcome.status != "succeeded":
            raise RuntimeError(
                f"[{device_id}] smoke lifecycle status={outcome.status!r}"
            )
        episodes[device_id] = _episode_count(brain)
        if episodes[device_id] < 1:
            raise RuntimeError(
                f"[{device_id}] lifecycle succeeded but 0 Episodes consolidated"
            )
    return episodes


def _open_falkor_client():
    """DM-2: open a FalkorDB client, or return None (fall back to the DM-1
    in-memory path) if disabled or unreachable. Falling back is documented,
    not fatal — the gate degrades gracefully (G-5 fallback contract)."""
    if not _falkor_enabled():
        return None
    from .persistence import open_client

    try:
        return open_client()
    except Exception as exc:  # PersistenceError / driver missing
        print(f"[DM-2] FalkorDB unavailable ({exc}); in-memory fallback.")
        return None


def _maybe_build_bodies():
    """DM-3: build the single shared SimEngine + per-device BodyHandles, or
    return None when the body runtime is unavailable.

    The body runtime imports ``sim_engine`` → ``mujoco`` (+ the ``sim/`` cell),
    which the 3.10 / no-MuJoCo sandbox can't load — so embodied registration
    is **Linux-gated** and skipped gracefully elsewhere (the DM-1/DM-2 gate
    stays green; PB-TT). ``DEMO_BODY=0`` also forces the skip."""
    if os.environ.get("DEMO_BODY", "1") == "0":
        return None
    if os.environ.get("DEMO_BOOTSTRAP_ONLY") == "1":
        # The DM-1/DM-2 idempotency boots assert L2/L3/persistence, not
        # motion — keep MuJoCo out of that spine (it stays exactly as it
        # gated green). The DM-3 gate builds the body runtime directly
        # (robot_demo.backend.dm3_check); the full runtime (main.py, not
        # bootstrap-only) still builds it.
        return None
    try:
        from .body_adapter import build_body_runtime
        return build_body_runtime()
    except Exception as exc:  # mujoco/sim import OR Cell build failed
        print(f"[DM-3] body runtime unavailable ({exc}); "
              "embodied capacities skipped.")
        return None


def _register_embodied(brains: Dict[str, Brain], handles) -> Dict[str, Tuple[str, ...]]:
    """Register each embodied brain's ⬡ atomic capacities over its BodyHandle
    (PB-UU: session=None into the brain's own CL Global; the brain's own
    kl/session ride along only for diagnose's Local gap-write closure)."""
    out: Dict[str, Tuple[str, ...]] = {}
    for device_id, handle in handles.items():
        brain = brains[device_id]
        iris = register_embodied_capacities(
            brain.cl,
            device_type=brain.profile.device_type,
            body=handle,
            kl=brain.kl,
            session=brain.session,
            device_id=device_id,
        )
        out[device_id] = tuple(iris)
    return out


def bootstrap(db_path: Optional[str] = None) -> BootstrapResult:
    """Run the full DM-1 + DM-2 bootstrap + smoke. Returns a BootstrapResult.

    DM-2 adds, per device (plan §1.3 steps 4–5): per-device named Falkor
    load-or-mint of the Global (PB-J), admin-gated device-type bundle
    install (P-8/§3.4), and Local embodiment seeding (§3.3). Globals are
    persisted; Locals stay in-memory (PB-Z). A single G-5 episode→Falkor
    round-trip probe runs after the smoke.

    Raises on any failure so a container/gate exits non-zero.
    """
    from mindsos_server._db import open_db

    with open_db(db_path) as conn:
        _ensure_users(conn)              # steps 0–2
        sessions = _login_all(conn)      # step 3 (brain users)
        admin_session = _login_admin(conn)  # DM-2 PB-BB (admin)

    client = _open_falkor_client()
    brains: Dict[str, Brain] = {}
    bundles: Dict[str, Tuple[str, ...]] = {}
    seeded_local: Dict[str, bool] = {}
    try:
        # step 4 — per-device stacks (Falkor load-or-mint Global, or
        # in-memory when no client), + bundle install + Local seed.
        for device_id in DEVICE_ORDER:
            profile = DEVICE_PROFILES[device_id]
            kl = None
            if client is not None:
                kl = load_or_mint_global(client, profile).kl
            brain = build_brain_stack(profile, sessions[device_id], kl=kl)
            brains[device_id] = brain

            bundles[device_id] = _install_device_bundles(brain, admin_session)
            # Ensure the robot.* DataStates in this boot's CapacityLayer
            # (idempotent). On a Falkor RELOAD boot install_skill no-ops on
            # digest match, so the bundle's L3 installer does NOT re-register
            # them into the fresh CL — but step-6 atomics AND DM-4 comms.*
            # both need them. F9: re-activating bundle L3 content on reboot.
            from .installers import install_core_datastates
            install_core_datastates(brain.cl)
            seeded_local[device_id] = seed_local_embodiment(
                brain.kl, brain.session, device_id
            )
            if client is not None:
                persist_global(client, brain.kl)  # MERGE-idempotent

        # step 6 (DM-3) — single shared SimEngine + per-brain embodied atomics.
        # Guarded: skipped (no-op) where MuJoCo is absent (sandbox); the
        # DM-1/DM-2 smoke below is unaffected (it dispatches the v0 builtins).
        bodies = _maybe_build_bodies()
        embodied: Dict[str, Tuple[str, ...]] = {}
        if bodies is not None:
            sim_engine, handles = bodies
            embodied = _register_embodied(brains, handles)
        else:
            sim_engine = None

        episodes = smoke(brains)  # step 5

        # G-5 — one episode→Falkor round-trip probe (mgr); fallback = in-memory.
        roundtrip: Optional[str] = None
        if client is not None:
            res = probe_episode_roundtrip(client, brains["mgr"].kl, "mgr")
            roundtrip = res.detail
            if not res.ok:
                print(f"[DM-2][G-5] episode round-trip FAILED: {res.detail} "
                      "— falling back to in-memory episodes (documented).")
    finally:
        if client is not None and hasattr(client, "close"):
            try:
                client.close()
            except Exception:
                pass

    return BootstrapResult(
        brains=brains,
        episodes=episodes,
        bundles=bundles,
        seeded_local=seeded_local,
        persisted_global=client is not None,
        episode_roundtrip=roundtrip,
        embodied=embodied,
        sim_engine=sim_engine,
    )


__all__ = ["bootstrap", "smoke", "BootstrapResult", "ADMIN_ID"]
