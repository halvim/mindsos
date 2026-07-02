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

from mindsos_capacity.identifiers import capacity_iri

from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel

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


def emit_task_run(task_id: str):
    """Stand up an in-memory L5 MentalModel + writer and emit the TaskRun chain
    artifact for the task (the L4 intake's L5 product)."""
    mm = MentalModel(session_id="arc", user_id="arc")
    writer = ChainArtifactWriter(mm, task_scope=task_id)
    return writer.emit_task_run()
