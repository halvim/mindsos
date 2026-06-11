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
from typing import Any, Dict, Optional

from mindsos_intelligence.consolidation import consolidation_enabled
from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
from mindsos_knowledge.metagraph_view import MetagraphView

from .brain import Brain, build_brain_stack
from .profiles import DEVICE_ORDER, DEVICE_PROFILES

ADMIN_ID = "admin"

# Demo-fixed credentials (P9). Local demo only — overridable via env; never
# a production secret. Not persisted to memory.
_DEFAULT_PW = "demo-pass"  # noqa: S105 — demo fixture, not a real secret


def _password_for(user_id: str) -> str:
    return os.environ.get(f"DEMO_PW_{user_id.upper()}", _DEFAULT_PW)


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


def _login_all(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Step 3: real login() per brain user → real Session objects.

    login() enforces one active session per user (AlreadyLoggedInError),
    and server.db persists across re-boots — so clear any stale session
    first via the shipped self-recovery valve. This is what makes a
    re-boot on an existing server.db idempotent (P6).
    """
    from mindsos_server.sessions import kill_my_own_sessions, login

    sessions: Dict[str, Any] = {}
    for device_id in DEVICE_ORDER:
        pw = _password_for(device_id)
        kill_my_own_sessions(conn, device_id, pw)
        sessions[device_id] = login(conn, device_id, pw).session
    conn.commit()
    return sessions


@dataclass
class BootstrapResult:
    brains: Dict[str, Brain]
    episodes: Dict[str, int]

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
        future = brain.il.enqueue(
            lambda b=brain: b.orch.run_lifecycle(
                {"text": "dm1-smoke"}, task_id=f"dm1-smoke-{b.device_id}"
            )
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


def bootstrap(db_path: Optional[str] = None) -> BootstrapResult:
    """Run the full DM-1 bootstrap + smoke. Returns a BootstrapResult.

    Raises on any failure so a container/gate exits non-zero.
    """
    from mindsos_server._db import open_db

    with open_db(db_path) as conn:
        _ensure_users(conn)        # steps 0–2
        sessions = _login_all(conn)  # step 3

    # step 4 — per-device stacks (KL in-memory at DM-1; build + start IL)
    brains: Dict[str, Brain] = {}
    for device_id in DEVICE_ORDER:
        brains[device_id] = build_brain_stack(
            DEVICE_PROFILES[device_id], sessions[device_id]
        )
        # DM-2: admin installs device-type bundles into brains[device_id].(kl, cl)
        # DM-2: seed brains[device_id]'s Local via make_writeable(kl, session)
        # DM-3: register embodied capacities over the brain's BodyHandle

    episodes = smoke(brains)  # step 5
    return BootstrapResult(brains=brains, episodes=episodes)


__all__ = ["bootstrap", "smoke", "BootstrapResult", "ADMIN_ID"]
