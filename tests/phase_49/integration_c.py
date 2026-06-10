"""Phase 49 — Integration C shared scenario harness.

Composes the shipped L0–L5 pieces into one trivial-task exercise. The
harness builds the L2/L3/L4/L5 stack and exposes step helpers that BOTH
the in-memory companion (deterministic, no live sidecar) and the
``@pytest.mark.integration`` live-Falkor scenario drive.

Design note (PHASE_49_DESIGN_LOG PB-1a): the substrate is exercised as
two stitched slices sharing one session + KL — (i) a read-side L3 invoke
of ``text.space_split`` (the text-realm slice), and (ii) a write-side
L4→L5 lifecycle over the ``planning.*``/``orchestration.*`` v0 catalogs
whose leaf Pipeline executes a *notional* step (``execution.py``), then
consolidates an Episode. The v0 lifecycle does NOT consume the tokenize
output — that single chain is WSD-gated. The harness keeps the two
slices co-resident on one KL so the full L0–L5 surface is shown wired
and co-functional.

``mindsos_server`` / CLI imports are deliberately kept out of module
scope (and inside the integration-only helpers) so this module + the
in-memory companion collect and run wherever the L3/L4/L5 packages
import — the live-Falkor round-trip is the only server-coupled step.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from mindsos_capacity import CapacityLayer, DS_MM_COMPOSITE_INSTANCE  # noqa: F401
from mindsos_capacity.builtins import (
    install_orchestration_v0,
    install_phase1_v0,
    install_planning_v0,
    install_text_capacities,
    reset_v0_verdicts,
)
from mindsos_capacity.builtins.consolidate import install_consolidate_capacities
from mindsos_capacity.builtins.dream import install_dream_capacities
from mindsos_capacity.builtins.text import DS_RAW_TEXT, DS_TOKENS
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.dream_cycle import run_dream_cycle
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.orchestrator import Orchestrator
from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
from mindsos_knowledge.metagraph_view import MetagraphView

from mindsos_capacity.pipeline import find_pipeline

SEED_TEXT = "the cat sat"
EXPECTED_TOKENS = ["the", "cat", "sat"]
TASK_USER = "alice"


class _Session:
    """SessionProtocol-conforming session for one Local user.

    ``has()`` returns ``True`` for any capability — the trivial-task
    consolidate writes the user's OWN Local (no ``CAN_WRITE_GLOBAL``
    needed; the scope-aware ADR-0180 gate only fires for Global writes).
    """

    def __init__(self, user_id: str = TASK_USER) -> None:
        self.user_id = user_id
        self.session_id = f"scenario-{user_id}"
        self.actor_role = "user"

    def has(self, capability: str) -> bool:  # noqa: D401 — protocol stub
        return True


@dataclass
class Stack:
    orch: Orchestrator
    mm: MentalModel
    kl: Any
    layer: Any
    dispatcher: L4Dispatcher
    session: _Session
    user: str


def build_stack(kl: Any = None, *, user: str = TASK_USER) -> Stack:
    """Build the full L2/L3/L4/L5 stack on one KL, all catalogs installed.

    ``kl=None`` → in-memory ``KnowledgeLayer.bootstrap()`` (deterministic).
    Pass a live (Falkor-bootstrapped) KL for the integration scenario.
    """
    kl = kl if kl is not None else KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    install_planning_v0(layer)
    install_phase1_v0(layer)
    install_orchestration_v0(layer)
    install_consolidate_capacities(layer)
    install_text_capacities(layer)
    install_dream_capacities(layer)
    reset_v0_verdicts()
    session = _Session(user)
    mm = MentalModel(session_id=session.session_id, user_id=user)
    dispatcher = L4Dispatcher(layer, session=session, kl=kl)
    orch = Orchestrator(dispatcher, mm, task_scope="integration-c")
    return Stack(orch, mm, kl, layer, dispatcher, session, user)


# ── Step helpers ───────────────────────────────────────────────────────


def step_read_side_tokenize(stack: Stack, text: str = SEED_TEXT) -> List[str]:
    """L3 read-side: find the raw-text→tokens pipeline and invoke it.

    Mirrors the text-realm cookbook: ``find_pipeline`` over the Global
    view, then dispatch the single ``text.space_split`` step.
    """
    pipeline = find_pipeline(
        stack.layer, start_datastate=DS_RAW_TEXT, target_datastate=DS_TOKENS
    )
    assert pipeline.steps, "no pipeline raw-text -> tokens"
    cap_iri = pipeline.steps[0].capacity_iri
    assert cap_iri == "capacity:perception:text.space_split"
    result = stack.dispatcher.dispatch(cap_iri, {DS_RAW_TEXT: text})
    assert result.success is True
    return list(result.outputs[DS_TOKENS])


def step_run_trivial_task(stack: Stack, text: str = SEED_TEXT, *, task_id: str = "T1"):
    """L4 enqueue-equivalent: run the six-phase lifecycle over the v0
    catalogs. Consolidation (L5) fires on the terminal path."""
    outcome = stack.orch.run_lifecycle({"text": text}, task_id=task_id)
    assert outcome.status == "succeeded"
    return outcome


def _episodic_graph(stack: Stack):
    return MetagraphView(stack.kl.local_metagraph(stack.user)).graphs_by_role(
        ROLE_EPISODIC_MEMORIES
    )[0]


def step_collect_episodes(stack: Stack) -> List[Any]:
    """Return the Episode nodes written into the user's Local
    ``episodic_memories`` by consolidation."""
    g = _episodic_graph(stack)
    return [n for n in g.nodes.values() if getattr(n, "type_name", None) == "Episode"]


def step_episode_iris(stack: Stack) -> List[str]:
    g = _episodic_graph(stack)
    return [
        iri
        for iri, n in g.nodes.items()
        if getattr(n, "type_name", None) == "Episode"
    ]


def step_memory_count(stack: Stack) -> int:
    g = _episodic_graph(stack)
    return len([n for n in g.nodes.values() if getattr(n, "type_name", None) == "Memory"])


def step_dream(stack: Stack, episode_iris: List[str], *, failed: bool = False) -> List[Any]:
    """L4 dream step (PB-3a): drive the dream driver synchronously over the
    episode corpus; an identity re-executor stands in for the WSD-gated
    faithful re-execution. Returns the emitted ``DreamDirective``s."""
    episodes: List[Dict[str, Any]] = [
        {"source_episode_iri": iri, "task_run_iri": "", "failed": failed}
        for iri in episode_iris
    ]
    return run_dream_cycle(stack.dispatcher, episodes, re_executor=lambda _d: None)


def step_live_persistence_machinery(client: Any) -> Any:
    """L0/L2 live round-trip (Phase 44 machinery): bootstrap the Global pair
    from FalkorDB and persist it back — the same native ``MetagraphRepository``
    round-trip that ``FalkorDBLocalPersister`` wraps. Proven-live operation
    (Integration A/B precedent).

    NB (PB-RT): we deliberately do NOT flush the consolidated *Episode* here.
    The Episode node's ``value`` is a structured 6-field dict, and the L0 node
    persister stores node values as **primitives** (``build_unwind_create_nodes``
    sets ``n.value = row.value``; ADR-0130 ``_props_json`` JSON-encodes
    *metagraph* properties only, not node values). Flushing a structured
    Episode to FalkorDB needs node-value serialization that has not shipped —
    a known L0↔L5 gap routed downstream. v1 Episodes live in the in-memory
    Local; see the cookbook "Persisting episodes" note and
    ``_workbench/L0_FUTURE_WORK.md``.
    """
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_server.persistence import bootstrap_global_pair_from_falkordb

    canonical_kl, _ = bootstrap_global_pair_from_falkordb(client)
    MetagraphRepository(client).persist(canonical_kl.global_metagraph())
    return canonical_kl


__all__ = [
    "SEED_TEXT",
    "EXPECTED_TOKENS",
    "TASK_USER",
    "Stack",
    "build_stack",
    "step_read_side_tokenize",
    "step_run_trivial_task",
    "step_collect_episodes",
    "step_episode_iris",
    "step_memory_count",
    "step_dream",
    "step_live_persistence_machinery",
]
