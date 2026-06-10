"""Phase 49 — Integration C: end-to-end L0→L5 trivial-task scenario.

Two entry points (PHASE_49_DESIGN_LOG PB-2a):

* ``test_chain_inmemory`` — deterministic companion (no live sidecar):
  L3 read-side tokenize + L4→L5 lifecycle + Episode/Memory/edge + dream
  directives. Runs everywhere the L3/L4/L5 packages import.
* ``test_integration_c_scenario`` — ``@pytest.mark.integration`` headline:
  the companion chain PLUS the L0 CLI login and the live
  ``FalkorDBLocalPersister`` save→load round-trip. Skips without a sidecar.

The cookbook ``docs/usage/cookbook/end-to-end.md`` transcribes this test;
if the prose drifts from the test, the test wins.
"""

from __future__ import annotations

import pytest

from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES, memory_composite_iri
from mindsos_knowledge.metagraph_view import MetagraphView
from mindsos_knowledge.schemas.episodic_memories import EDGE_MEMORY_CONTAINS_EPISODE

from tests.phase_49 import integration_c as ic

_V0_TASK_PATTERN = "task-pattern:v0:trivial"


def _assert_chain(stack) -> list:
    """Shared assertions for the L3→L5 chain. Returns the Episode IRIs."""
    tokens = ic.step_read_side_tokenize(stack)
    assert tokens == ic.EXPECTED_TOKENS

    outcome = ic.step_run_trivial_task(stack)
    assert outcome.outcome == _V0_TASK_PATTERN

    episodes = ic.step_collect_episodes(stack)
    assert len(episodes) == 1
    assert episodes[0].value["outcome_classification"] == "succeeded"
    assert ic.step_memory_count(stack) == 1

    # MEMORY_CONTAINS_EPISODE edge on the materialised Memory.
    from mindsos_capacity.builtins.consolidate import _memory_id_for

    memory_iri = memory_composite_iri("v1", stack.user, _memory_id_for(_V0_TASK_PATTERN))
    edges = MetagraphView(stack.kl.local_metagraph(stack.user)).get_edges(
        ROLE_EPISODIC_MEMORIES, memory_iri, edge_type=EDGE_MEMORY_CONTAINS_EPISODE
    )
    iris = ic.step_episode_iris(stack)
    assert any(e.target.node_id == iris[0] for e in edges)

    # Dream step (PB-3a): synchronous driver over the episode corpus.
    non_failed = ic.step_dream(stack, iris, failed=False)
    assert sorted(d.execution_policy for d in non_failed) == [
        "re_execute_capacities",
        "replay_recorded",
    ]
    failed = ic.step_dream(stack, iris, failed=True)
    assert len(failed) == 3
    assert len([d for d in failed if d.replan_injection is not None]) == 1

    return iris


def test_chain_inmemory():
    """Deterministic L3→L5 chain over an in-memory KL (no sidecar)."""
    stack = ic.build_stack()
    _assert_chain(stack)


@pytest.mark.integration
def test_integration_c_scenario(scenario_falkordb_clean, scenario_home):
    """Headline L0→L5 scenario against a live FalkorDB sidecar.

    Live operations are restricted to ones proven by Integration A/B
    (CLI auth + Global-pair bootstrap/persist round-trip); the L3→L5 chain
    is the deterministic companion. The consolidated Episode is asserted in
    the in-memory Local — flushing it to FalkorDB is a known node-value
    serialization gap (PB-RT; see ``integration_c.step_live_persistence_
    machinery`` + the cookbook "Persisting episodes" note).
    """
    from typer.testing import CliRunner

    from mindsos_cli.app import app
    from mindsos_core.config import FalkorConfig
    from mindsos_core.persistence.client import FalkorClient

    # L0 — bootstrap admin + login (Phase 19/20/21: auth + session + audit).
    runner = CliRunner()
    r = runner.invoke(app, ["server", "bootstrap", "admin"], input="adminpw\n")
    assert r.exit_code == 0, r.output
    r = runner.invoke(app, ["server", "login", "admin"], input="adminpw\n")
    assert r.exit_code == 0, r.output

    # L0/L2 — live Falkor persistence machinery (the Phase-44 native round-trip
    # FalkorDBLocalPersister wraps), exercised on the Global pair.
    client = FalkorClient(FalkorConfig.from_env())
    try:
        canonical_kl = ic.step_live_persistence_machinery(client)
    finally:
        client.close()
    assert canonical_kl is not None

    # L3/L4/L5 — the chain (same assertions as the companion).
    stack = ic.build_stack()
    _assert_chain(stack)
