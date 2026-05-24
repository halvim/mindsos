"""Phase 26b — Integration A end-to-end scripted scenario.

Single ``test_integration_a`` function + 13 step helpers + ScenarioState
thread per Phase 26b design log R3-PB-7 (a). Composes the
Phase 24/25/26a substrate end-to-end:

* CLI invocations (via Typer CliRunner per Phase 25 canonical pattern;
  each invoke gets fresh `_resolve_persister()` mimicking subprocess
  semantics for persister freshness; SQLite + FalkorDB state survives
  across invocations).
* In-process Python helpers for steps that have no CLI verb (test
  importer, MetagraphView walk, _seed_user2_local, admin_read_local
  in-process per R1-PB-2 (a), direct Cypher stable-id assertion).

Audit-events table (R4-PB-4 + R5-F1/F2 corrections):

  | step | event(s) | emits_audit_in_same_call |
  | 1    | EVT_BOOTSTRAP                  | true (session-less)  |
  | 1.5  | EVT_LOGIN                      | true                 |
  | 2    | EVT_ADMIN_CREATE_USER ×2       | true                 |
  | 3    | EVT_LOGIN                      | true                 |
  | 4    | (none)                         | n/a (R7-F4 pin)      |
  | 5    | (none)                         | n/a (read-only)      |
  | 5.5  | (none)                         | n/a (in-process)     |
  | 6    | EVT_CROSS_USER_READ_INSTALL    | true                 |
  | 7    | EVT_PROMOTION_PROPOSED         | true                 |
  | 7b   | EVT_RELEASE_SHIPPED            | true                 |
  | 8    | EVT_LOGOUT                     | true                 |
  | 9    | EVT_AUDIT_QUERY                | true (FILTERED)      |
  | 10   | (none)                         | n/a (substrate read) |
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pytest
from typer.testing import CliRunner

from mindsos_admin import PENDING_GLOBAL_METAGRAPH_NAME
from mindsos_cli.app import app
from mindsos_core import Metagraph
from mindsos_core.config import FalkorConfig
from mindsos_core.persistence.client import FalkorClient
from mindsos_core.persistence.metagraph_repository import MetagraphRepository
from mindsos_knowledge.bootstrap import ensure_global_role_graph
from mindsos_knowledge.identifiers import ROLE_CONCEPTS
from mindsos_knowledge.knowledge_layer import (
    _GLOBAL_METAGRAPH_NAME,
    KnowledgeLayer,
)
from mindsos_server.admin import read_other_local_summary
from mindsos_server.persistence import (
    InMemoryLocalPersister,
    bootstrap_global_pair_from_falkordb,
)
from mindsos_server.sessions import session_from_token

from tests.phase_26b._falkordb_assert import (
    count_canonical_nodes_via_graph_traversal,
    count_canonical_nodes_via_metagraph_id_property,
    resolve_canonical_metagraph_id,
    resolve_pending_metagraph_id,
)
from tests.phase_26b._normalize import normalize
from tests.phase_26b.fixtures._test_importer import FixtureImporter


# ── ScenarioState ──────────────────────────────────────────────────────


@dataclass
class ScenarioState:
    runner: CliRunner
    db_path: Path
    home: Path
    admin_token: Optional[str] = None
    user1_token: Optional[str] = None
    canonical_metagraph_id_pre_propose: Optional[str] = None
    canonical_metagraph_id_post_ship: Optional[str] = None
    pending_metagraph_id: Optional[str] = None
    canonical_node_count_post_import: int = 0
    canonical_node_count_post_ship: int = 0
    audit_event_ids: list[int] = field(default_factory=list)


# ── Pytest fixtures ────────────────────────────────────────────────────


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def scenario_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario_falkordb_clean: None,  # noqa: ARG001 — fixture-side-effect
) -> dict[str, Path]:
    """Per-scenario fresh server.db + HOME; FalkorDB pre-cleaned by conftest."""
    db_path = tmp_path / "server.db"
    monkeypatch.setenv("MINDSOS_SERVER_DB", str(db_path))
    monkeypatch.delenv("MINDSOS_TOKEN", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    return {"db": db_path, "home": tmp_path}


# ── Step helpers (13 substeps per R3-PB-4 (a) + R3-PB-7 (a)) ───────────


def _step_01_bootstrap_admin(state: ScenarioState) -> ScenarioState:
    r = state.runner.invoke(
        app, ["server", "bootstrap", "admin"], input="adminpw\n",
    )
    assert r.exit_code == 0, r.output
    return state


def _step_02_login_admin(state: ScenarioState) -> ScenarioState:
    r = state.runner.invoke(
        app, ["server", "login", "admin"], input="adminpw\n",
    )
    assert r.exit_code == 0, r.output
    # Token is written to ~/.mindsos/token by the login command; the CLI
    # subsequently reads MINDSOS_TOKEN OR ~/.mindsos/token. We don't need
    # to capture it explicitly — subsequent invocations inherit via HOME.
    return state


def _step_03_create_user1_user2(state: ScenarioState) -> ScenarioState:
    r = state.runner.invoke(
        app, ["server", "user", "create", "user1", "--role", "user"],
        input="user1pw\n",
    )
    assert r.exit_code == 0, r.output
    r = state.runner.invoke(
        app, ["server", "user", "create", "user2", "--role", "user"],
        input="user2pw\n",
    )
    assert r.exit_code == 0, r.output
    return state


def _step_04_login_user1(state: ScenarioState) -> ScenarioState:
    # Logout admin first (CLI session is per-process; CliRunner reuses
    # process state via HOME). Phase 19's refuse-concurrent-login means
    # we must logout admin before user1 login from the same HOME.
    r = state.runner.invoke(app, ["server", "logout"])
    assert r.exit_code == 0, r.output
    r = state.runner.invoke(
        app, ["server", "login", "user1"], input="user1pw\n",
    )
    assert r.exit_code == 0, r.output
    return state


def _step_05_import_via_test_importer(state: ScenarioState) -> ScenarioState:
    """Python-API in-process — bypass CLI (no `mindsos admin import
    test-importer` verb; PHASE_MAP §38 deferred)."""
    client = FalkorClient(FalkorConfig.from_env())
    try:
        canonical_kl, _ = bootstrap_global_pair_from_falkordb(client)
        importer = FixtureImporter()
        importer.run(canonical_kl.global_metagraph())
        repo = MetagraphRepository(client)
        repo.persist(canonical_kl.global_metagraph())
    finally:
        client.close()

    state.canonical_node_count_post_import = (
        count_canonical_nodes_via_graph_traversal()
    )
    assert state.canonical_node_count_post_import >= 10, (
        f"expected ≥10 nodes post-import (graph-traversal shape), "
        f"got {state.canonical_node_count_post_import}"
    )
    return state


def _step_06_metagraph_view_walk(state: ScenarioState) -> ScenarioState:
    """Python-API in-process — read-only MetagraphView walk."""
    client = FalkorClient(FalkorConfig.from_env())
    try:
        canonical_kl, _ = bootstrap_global_pair_from_falkordb(client)
    finally:
        client.close()
    view = canonical_kl.global_view()
    concepts_count = 0
    for role in view.roles():
        graph = view.role_graph(role)
        if graph is None:
            continue
        if role == ROLE_CONCEPTS:
            concepts_count = len(graph.nodes)
    assert concepts_count >= 10, f"concepts walk count {concepts_count}"
    return state


def _step_07_seed_user2_local(state: ScenarioState) -> tuple[
    ScenarioState, InMemoryLocalPersister, KnowledgeLayer
]:
    """Python-API in-process — install 1-node Local for user2.

    Per R2-PB-3 (a) + R5-F4 — role `concepts` reuses
    ``ensure_global_role_graph`` (helper isn't Global-specific).
    """
    persister = InMemoryLocalPersister()
    kl = KnowledgeLayer.bootstrap()

    local_mg = Metagraph(name="local:user2")
    ensure_global_role_graph(local_mg, ROLE_CONCEPTS)
    graph = next(
        g for g in local_mg.graphs.values() if g.role == ROLE_CONCEPTS
    )
    graph.add_node(
        "test_concept_user2", "Frame", properties={},
    )

    persister.save("user2", local_mg)
    kl.install_local_metagraph("user2", local_mg)
    return state, persister, kl


def _step_08_admin_read_local_user2(
    state: ScenarioState,
    persister: InMemoryLocalPersister,
    kl: KnowledgeLayer,
) -> ScenarioState:
    """Python-API in-process — admin diagnostic via direct function call.

    Per R1-PB-2 (a) — NOT a CLI subprocess; InMemoryLocalPersister
    doesn't survive process boundaries; in-process preserves the seed.
    """
    # Logout user1 + login admin via CLI to capture an admin session.
    r = state.runner.invoke(app, ["server", "logout"])
    assert r.exit_code == 0, r.output
    r = state.runner.invoke(
        app, ["server", "login", "admin"], input="adminpw\n",
    )
    assert r.exit_code == 0, r.output

    # Resolve the admin session from the CLI-written token.
    token = (state.home / ".mindsos" / "token").read_text().strip()
    conn = sqlite3.connect(str(state.db_path))
    try:
        session = session_from_token(conn, token)
        summary = read_other_local_summary(
            conn,
            session,
            target_user_id="user2",
            persister=persister,
            kl=kl,
        )
    finally:
        conn.close()

    role_counts = {rg.role: rg.node_count for rg in summary.role_graphs}
    assert role_counts.get(ROLE_CONCEPTS, 0) == 1, (
        f"expected user2 Local to have 1 node in concepts; got {role_counts}"
    )

    # Re-login user1 for the next CLI step.
    r = state.runner.invoke(app, ["server", "logout"])
    assert r.exit_code == 0, r.output
    r = state.runner.invoke(
        app, ["server", "login", "user1"], input="user1pw\n",
    )
    assert r.exit_code == 0, r.output
    return state


def _step_09_propose_atom(state: ScenarioState) -> ScenarioState:
    """CLI subprocess (via CliRunner) — propose ATOM Lemma into lexicon.

    R5-F3 payload. Admin session required (CAN_PROPOSE_MUTATION).
    """
    r = state.runner.invoke(app, ["server", "logout"])
    assert r.exit_code == 0, r.output
    r = state.runner.invoke(
        app, ["server", "login", "admin"], input="adminpw\n",
    )
    assert r.exit_code == 0, r.output

    state.canonical_metagraph_id_pre_propose = resolve_canonical_metagraph_id()
    state.pending_metagraph_id = resolve_pending_metagraph_id()

    proposal_path = state.home / "proposal.json"
    proposal_payload = {
        "reason": "Phase 26b scenario propose",
        "items": [{
            "kind": "ATOM",
            "node": {
                "node_type": "Lemma",
                "value": "test_lemma_phase26b",
                "target_role": "lexicon",
                "properties": {},
            },
        }],
    }
    proposal_path.write_text(json.dumps(proposal_payload))

    r = state.runner.invoke(
        app,
        [
            "server", "release", "propose-for-promotion",
            "--input-json", str(proposal_path), "--json",
        ],
    )
    assert r.exit_code == 0, r.output
    payload = json.loads(r.output)
    assert "mutation_ids" in payload
    assert len(payload["mutation_ids"]) == 1
    return state


def _step_10_release_ship(state: ScenarioState) -> ScenarioState:
    r = state.runner.invoke(
        app, ["server", "release", "ship", "--json"],
    )
    assert r.exit_code == 0, r.output
    payload = json.loads(r.output)
    assert payload["status"] == "SHIPPED"
    assert payload["mutations_shipped_count"] == 1
    # Post-ship: importer-shape count unchanged (release writes orphan
    # nodes via §am3 path); release-shape count grew by exactly 1
    # (the propose'd ATOM Lemma).
    state.canonical_node_count_post_ship = (
        count_canonical_nodes_via_metagraph_id_property()
    )
    state.canonical_metagraph_id_post_ship = resolve_canonical_metagraph_id()
    return state


def _step_11_logout_user1(state: ScenarioState) -> ScenarioState:
    # Re-login as user1 first (current session is admin from step 9-10).
    r = state.runner.invoke(app, ["server", "logout"])
    assert r.exit_code == 0, r.output
    r = state.runner.invoke(
        app, ["server", "login", "user1"], input="user1pw\n",
    )
    assert r.exit_code == 0, r.output
    r = state.runner.invoke(app, ["server", "logout"])
    assert r.exit_code == 0, r.output
    return state


def _step_12_query_audit(state: ScenarioState) -> ScenarioState:
    """CLI subprocess — query-audit. EVT_AUDIT_QUERY self-emit filtered
    from result per R0-PB-7 (c) (Phase 21 B-21-T1 lesson)."""
    r = state.runner.invoke(
        app, ["server", "login", "admin"], input="adminpw\n",
    )
    assert r.exit_code == 0, r.output
    r = state.runner.invoke(
        app, ["server", "query-audit", "--json"],
    )
    assert r.exit_code == 0, r.output
    rows = json.loads(r.output)

    # Per R4-PB-4 + R5-F1/F2 — assert presence of expected events.
    event_kinds = [row["kind"] for row in rows]
    expected_events = {
        "EVT_BOOTSTRAP",
        "EVT_LOGIN",
        "EVT_ADMIN_CREATE_USER",
        "EVT_LOGOUT",
        "EVT_CROSS_USER_READ_INSTALL",
        "EVT_PROMOTION_PROPOSED",
        "EVT_RELEASE_SHIPPED",
    }
    for ev in expected_events:
        assert ev in event_kinds, f"expected {ev} in audit; got {event_kinds}"

    # Per R0-PB-7 (c) — EVT_AUDIT_QUERY self-row NOT in the result of
    # this very call's SELECT (Phase 21 SELECT → write → return ordering).
    # Subsequent query-audit calls would see it.
    _normalized = normalize(json.dumps(rows, sort_keys=True))
    # (golden-output snapshot deferred; smoke-assert non-empty + key events)
    return state


def _step_13_fresh_stable_id_assert(state: ScenarioState) -> ScenarioState:
    """Direct Cypher — assert canonical metagraph_id stable across the
    propose/ship calls. Pair helper's load-or-mint with persist-on-mint
    means the same id resolves on every invocation."""
    canonical_id_now = resolve_canonical_metagraph_id()
    assert canonical_id_now is not None
    assert canonical_id_now == state.canonical_metagraph_id_pre_propose, (
        "canonical metagraph_id drift across CLI invocations — "
        "B-26a-T4 regression: "
        f"pre-propose={state.canonical_metagraph_id_pre_propose!r} "
        f"post-ship={canonical_id_now!r}"
    )
    assert canonical_id_now == state.canonical_metagraph_id_post_ship

    # Pending id also stable.
    pending_id_now = resolve_pending_metagraph_id()
    assert pending_id_now is not None
    assert pending_id_now == state.pending_metagraph_id

    # Release-shape canonical node count (§am3 _RELEASE_MERGE_CYPHER path)
    # grew by exactly 1 — the propose'd ATOM Lemma. Importer-shape count
    # (graph-traversal) is unaffected because §am3 writes don't link via
    # :IN_GRAPH (B-26b-T5 finding; documented carry-forward).
    assert state.canonical_node_count_post_ship == 1, (
        f"release-shape canonical node count: expected 1 (post-ship);"
        f" got {state.canonical_node_count_post_ship}"
    )
    return state


# ── The scenario ───────────────────────────────────────────────────────


@pytest.mark.integration
def test_integration_a(runner, scenario_env, scenario_state_dir) -> None:
    """Phase 26b — L0+L1+L2 end-to-end scripted scenario over the
    Phase 26a-wired FalkorDB substrate + the Phase 26b
    bootstrap_global_pair_from_falkordb closure of B-26a-T4."""
    state = ScenarioState(
        runner=runner,
        db_path=scenario_env["db"],
        home=scenario_env["home"],
    )

    state = _step_01_bootstrap_admin(state)
    state = _step_02_login_admin(state)
    state = _step_03_create_user1_user2(state)
    state = _step_04_login_user1(state)
    state = _step_05_import_via_test_importer(state)
    state = _step_06_metagraph_view_walk(state)
    state, persister, kl = _step_07_seed_user2_local(state)
    state = _step_08_admin_read_local_user2(state, persister, kl)
    state = _step_09_propose_atom(state)
    state = _step_10_release_ship(state)
    state = _step_11_logout_user1(state)
    state = _step_12_query_audit(state)
    state = _step_13_fresh_stable_id_assert(state)
