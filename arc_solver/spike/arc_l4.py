"""L4 wiring — the ARC solver's control flow composed from the SHIPPED
mindsos_intelligence primitives, honoring the layer boundary:

  * L4 (this module) ORCHESTRATES — it decides which capacity to call and
    dispatches it through the real L4 choke point (``L4Dispatcher`` ->
    ``runtime.invoke``). We do NOT use ``Orchestrator.run_lifecycle`` — it is
    hardwired to the v0 catalogs (real catalogs ship in WSD); the demo composes
    the primitives directly.
  * L3 (arc_capacities) COMPUTES — the fixed perceive caps produce the result.
  * L5 (``MentalModel`` + ``ChainArtifactWriter``) STORES — the per-task result
    and the TaskRun chain artifact land here.

Intake slice (step 2 of the wiring): dispatch the perceive extractors through
L4->L3 for every grid and prove they match the inline perception; emit a real
L5 TaskRun for one task. Reasoning/rule phases (8/9/10) wire consumer-driven
on top of this driver.
"""

from __future__ import annotations

from types import SimpleNamespace

from mindsos_capacity.capacity_layer import CapacityLayer
from mindsos_capacity.identifiers import capacity_iri
from mindsos_capacity.builtins import (
    install_orchestration_v0,
    install_phase1_v0,
    install_planning_v0,
    install_text_capacities,
    reset_v0_verdicts,
)
from mindsos_capacity.builtins.consolidate import install_consolidate_capacities
from mindsos_capacity.builtins.dream import install_dream_capacities

from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.orchestrator import Orchestrator

from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
from mindsos_knowledge.metagraph_view import MetagraphView

from . import arc_capacities as ac

_CAP_OBJECTS = capacity_iri(ac.CATEGORY_PERCEIVER, "extract_objects")
_CAP_POINTS = capacity_iri(ac.CATEGORY_PERCEIVER, "extract_points")


def dispatcher(cl) -> L4Dispatcher:
    """The L4 dispatch choke point over the ARC CapacityLayer (read path — no
    session/KL/MM needed for the perceive caps)."""
    return L4Dispatcher(cl)


def perceive_grid(disp: L4Dispatcher, grid) -> dict:
    """Dispatch the perceive extractors for one grid through L4 -> L3 and return
    the results (the L5-bound per-grid perception)."""
    ro = disp.dispatch(_CAP_OBJECTS, {ac.DS_GRID: grid})
    rp = disp.dispatch(_CAP_POINTS, {ac.DS_GRID: grid})
    assert ro.success and rp.success, "perceive dispatch through L4 failed"
    return {"objects": ro.outputs[ac.DS_OBJECT], "points": rp.outputs[ac.DS_POINT]}


_CAP_EMIT = capacity_iri(ac.CATEGORY_REASONING, "emit_candidates")
_CAP_SELECT = capacity_iri(ac.CATEGORY_REASONING, "select_rules")
_CAP_APPLY = capacity_iri(ac.CATEGORY_REASONING, "apply_solution")


def solve_through_layer(disp, task_id: str, dataset: dict):
    """L4 DRIVER — sequence the arc solve's phases 8→9→10, dispatching each as a
    REAL L3 decision cap through the layer (not inline). Phases 1-7 (perceive +
    hypothesis working state) are run inline to build the profile the decisions
    consume. Returns (dispatched_solve, inline_solve) for conformance."""
    from arc_solver.solve import pipeline
    ctx = pipeline.run_all(task_id, dataset)          # inline profile + inline answer (oracle)
    base = {ac.DS_PROFILE: ctx["profile"], ac.DS_ENCLOSED: ctx.get("enclosed")}
    rules = disp.dispatch(_CAP_EMIT, {**base,
                                      ac.DS_BG_CAND: ctx.get("bg_cand"),
                                      ac.DS_RECOMPARISON: ctx.get("recomparison")}
                          ).outputs[ac.DS_RULES]
    sel = disp.dispatch(_CAP_SELECT, {**base, ac.DS_RULES: rules}).outputs[ac.DS_SELECTION]
    solve = disp.dispatch(_CAP_APPLY, {**base, ac.DS_RULES: rules,
                                       ac.DS_SELECTION: sel,
                                       ac.DS_RAW_TASK: ctx.get("raw")}).outputs[ac.DS_SOLVE]
    return solve, ctx.get("solve")


def emit_task_run(task_id: str):
    """Stand up an in-memory L5 MentalModel + writer and emit the TaskRun chain
    artifact for the task (the L4 intake's L5 product)."""
    mm = MentalModel(session_id="arc", user_id="arc")
    writer = ChainArtifactWriter(mm, task_scope=task_id)
    return writer.emit_task_run()


# ── the real MindsOS instance (a): bootstrapped stack + arc caps ─────────
class _ArcSession:
    """Minimal SessionProtocol session for one Local user (mirrors the Phase-49
    scenario session). ``has()`` is permissive — the trivial consolidate writes
    the user's OWN Local, which needs no CAN_WRITE_GLOBAL (ADR-0180 gate only
    fires for Global writes)."""

    def __init__(self, user_id: str = "arc") -> None:
        self.user_id = user_id
        self.session_id = f"arc-{user_id}"
        self.actor_role = "user"

    def has(self, capability: str) -> bool:
        return True


def build_instance(user: str = "arc", *, arc_local: bool = False):
    """Stand up a REAL in-process MindsOS instance (option (a)) — the shipped
    Phase-49 `build_stack` recipe (bootstrapped KL + CapacityLayer with every v0
    catalog + consolidate/text/dream builtins) with the ARC capacities registered
    ON TOP. This is an actual instance of the stack, not an isolated
    CapacityLayer.

    Seam for option (b): swap the in-memory `KnowledgeLayer.bootstrap()` for a
    live Falkor-bootstrapped KL + a FalkorDBLocalPersister (the Phase-49
    `build_stack(kl=...)` comment) — nothing else here changes."""
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    install_planning_v0(layer)
    install_phase1_v0(layer)
    install_orchestration_v0(layer)
    install_consolidate_capacities(layer)
    install_text_capacities(layer)
    install_dream_capacities(layer)
    reset_v0_verdicts()
    session = _ArcSession(user)
    # arc caps + DataStates: Global by default (gate); the user's LOCAL L3 when
    # arc_local (durable instance) — arc-solve content Local, per "No Global L5".
    ac.install_arc(layer, session=session if arc_local else None)
    mm = MentalModel(session_id=session.session_id, user_id=user)
    dispatcher = L4Dispatcher(layer, session=session, kl=kl)
    orch = Orchestrator(dispatcher, mm, task_scope="arc")
    return SimpleNamespace(kl=kl, layer=layer, session=session, mm=mm,
                           dispatcher=dispatcher, orch=orch, user=user)


def episodes(inst) -> list:
    """L5 read-back: the Episode nodes consolidation wrote into the user's Local
    episodic_memories role graph."""
    g = MetagraphView(inst.kl.local_metagraph(inst.user)).graphs_by_role(
        ROLE_EPISODIC_MEMORIES
    )[0]
    return [n for n in g.nodes.values()
            if getattr(n, "type_name", None) == "Episode"]
