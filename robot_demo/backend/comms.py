"""DM-4 Seam B — the four ``comms.*`` capacities + the v0-IRI override seam
(plan §2.1, design-log PB-WW / PB-EEE / PB-FFF / PB-GGG).

Two consumer-side mechanisms live here, both proven by the step-1 probe:

* **``install_override``** — replace a *shipped v0 capacity's* implementation
  in place. ``register_capacity(if_exists="upsert")`` does **not** swap the
  bound callable (it only back-fills PRODUCES/CONSUMES edges; capacity_layer
  never re-assigns ``_declarations`` on the upsert branch — design-log §1
  refuted). The dispatcher resolves the impl through ``get_declaration ->
  _declarations``, so the working override is to assign that entry directly,
  cloning the shipped DataState contract so the bipartite edges stay correct.

* **``register_comms_capacities``** — register the four Seam-B verbs under
  *new* IRIs (``if_exists="upsert"`` is correct here: a new IRI takes the
  first-registration branch and stores the declaration; a re-run idempotently
  no-ops). They declare the DM-2 ``robot.*`` DataStates so registration v2
  emits the PRODUCES/CONSUMES edges — what makes ``find_pipeline`` + the
  graph tab honest.

**PB-GGG — DataState reconciliation.** The plan's ``comms.report`` output
``DS_REPORT_SENT`` is not in the DM-2-registered set (§4.0). ``report`` here
consumes ``DS_TASK_OUTCOME`` and produces ``DS_DISPATCH_ACK`` — the report IS
the ack the Manager's ``dispatch`` awaits, so two producers share that
DataState (a many-to-many the bipartite topology allows). No new DataState,
no ``mindsos_*`` edit.

The capacity bodies close over the :class:`~robot_demo.backend.bus.BrainBus`
(injected at registration) — the bus is the wire, the capacity is the
MindsOS-visible surface. ``share_to_peer`` is the F1-min mechanism stub; the
beat-4 transfer itself is DM-7.

MuJoCo-free: the arm's atomic action is injected as ``run_atomic`` (the real
``move_to`` invoke on the Linux gate; a stub in the sandbox), so this whole
module is sandbox-testable.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from mindsos_capacity import Capacity
from mindsos_capacity.identifiers import capacity_iri, datastate_iri

from .bus import DEFER, BrainBus, BusError, BusTimeout, Message

# ── §4.0 DataState IRIs (DM-2 registered) ─────────────────────────────
DS_DISPATCH_CMD = datastate_iri("robot.dispatch_cmd")
DS_DISPATCH_ACK = datastate_iri("robot.dispatch_ack")
DS_TASK_OUTCOME = datastate_iri("robot.task_outcome")
DS_CAP_QUERY = datastate_iri("robot.cap_query")
DS_CAP_REPORT = datastate_iri("robot.cap_report")
DS_SHARE_ARTIFACT = datastate_iri("robot.share_artifact")
DS_SHARE_ACK = datastate_iri("robot.share_ack")

#: comms.* family/category. Plan §2.1 wants ``interaction``-style names;
#: ``interaction`` is an unkeyed FAMILY_RULES category (Phase-42 deferred
#: set), but ``ensure_category_graph`` accepts any category (the
#: ``mechanism``/``validate`` precedent, DM-3) and ``family_rule_for`` falls
#: back. Confirmed registrable at build (PB-BBB); fall to ``signalling`` if a
#: future MindsOS tightens this.
CAT_COMMS = "interaction"

#: pub/sub topic for the query_capabilities push-cache (PB-C).
TOPIC_CAP_REPORT = "capability-report"

#: bus message kind for a Manager→brain dispatch.
KIND_DISPATCH = "dispatch"

# IRIs
DISPATCH_IRI = capacity_iri(CAT_COMMS, "dispatch")
REPORT_IRI = capacity_iri(CAT_COMMS, "report")
QUERY_CAPS_IRI = capacity_iri(CAT_COMMS, "query_capabilities")
SHARE_IRI = capacity_iri(CAT_COMMS, "share_to_peer")


# ── the v0-IRI override seam (PB-WW, validated by dm4_probe) ───────────
def install_override(cl: Any, iri: str, new_impl: Callable[..., dict]) -> None:
    """Swap the implementation bound to an already-registered v0 ``iri``.

    Clones the shipped declaration's contract (same inputs/outputs → the
    PRODUCES/CONSUMES edges already emitted stay correct) and assigns the
    registry entry ``get_declaration`` reads. This is the ONLY working
    same-name override (``if_exists="upsert"`` is a behavioural no-op)."""
    decl = cl.get_declaration(iri)
    cl._declarations[iri] = Capacity(
        name=decl.name,
        category=decl.category,
        inputs=decl.inputs,
        outputs=decl.outputs,
        implementation=new_impl,
        description=f"DM-4 demo override of {iri}",
    )


# ── task_pattern_iri target channel (PB-EEE) ──────────────────────────
_TPI_PREFIX = "task-pattern:demo:move:"


def encode_target(dst: str, target: str) -> str:
    """Encode the dispatch (arm, pose) into the task_pattern_iri string —
    the only task datum that survives into phase 2 (PB-EEE)."""
    return f"{_TPI_PREFIX}{dst}:{target}"


def decode_target(tpi: str) -> Tuple[Optional[str], Optional[str]]:
    if not tpi.startswith(_TPI_PREFIX):
        return None, None
    rest = tpi[len(_TPI_PREFIX):]
    dst, _, target = rest.partition(":")
    return dst or None, target or None


# ── the four comms.* capacities ───────────────────────────────────────
def register_comms_capacities(
    cl: Any,
    bus: BrainBus,
    brain_id: str,
    *,
    cap_snapshot: Optional[Callable[[], List[str]]] = None,
    timeout: float = 30.0,
) -> Tuple[str, ...]:
    """Register dispatch / report / query_capabilities / share_to_peer into
    a brain's CL Global (``session=None``, like the DM-3 atomics — that's
    where the ``robot.*`` DataStates live). Bodies close over ``bus``."""

    def dispatch_impl(context=None, **inputs):
        cmd = inputs.get(DS_DISPATCH_CMD) or {}
        dst = cmd.get("dst")
        try:
            ack = bus.request(brain_id, dst, KIND_DISPATCH, cmd, timeout=timeout)
        except (BusTimeout, BusError) as exc:
            ack = {"status": "dont_know", "reason": str(exc)}
        return {DS_DISPATCH_ACK: ack}

    def report_impl(context=None, **inputs):
        outcome = inputs.get(DS_TASK_OUTCOME) or {}
        # format-only: the bus handler does the actual reply via bus.reply.
        report = {
            "from": brain_id,
            "status": outcome.get("status", "succeeded"),
            "detail": outcome,
        }
        return {DS_DISPATCH_ACK: report}

    def query_caps_impl(context=None, **inputs):
        caps = cap_snapshot() if cap_snapshot else []
        report = {"brain": brain_id, "caps": caps}
        # push-cache (PB-C): fan the report to subscribers; no round-trip.
        bus.publish(brain_id, TOPIC_CAP_REPORT, report)
        return {DS_CAP_REPORT: report}

    def share_impl(context=None, **inputs):
        # F1-min mechanism stub; the beat-4 transfer is DM-7.
        artifact = inputs.get(DS_SHARE_ARTIFACT) or {}
        peer = artifact.get("peer")
        if peer:
            bus.send(brain_id, peer, "share", artifact)
        return {DS_SHARE_ACK: {"status": "deferred", "note": "DM-7"}}

    specs = [
        ("dispatch", (DS_DISPATCH_CMD,), (DS_DISPATCH_ACK,), dispatch_impl),
        ("report", (DS_TASK_OUTCOME,), (DS_DISPATCH_ACK,), report_impl),
        ("query_capabilities", (DS_CAP_QUERY,), (DS_CAP_REPORT,), query_caps_impl),
        ("share_to_peer", (DS_SHARE_ARTIFACT,), (DS_SHARE_ACK,), share_impl),
    ]
    registered: List[str] = []
    for name, ins, outs, impl in specs:
        decl = Capacity(
            name=name,  # IRI = capacity:interaction:<verb> (matches *_IRI consts)
            category=CAT_COMMS,
            inputs=ins,
            outputs=outs,
            implementation=impl,
            description=f"DM-4 Seam-B comms.{name} ({brain_id}).",
        )
        node = cl.register_capacity(decl, session=None, if_exists="upsert")
        registered.append(node.node_id)
    return tuple(registered)


# ── bus wiring: the arm's dispatch handler (deferred reply) ────────────
def make_dispatch_handler(
    bus: BrainBus,
    brain: Any,
    *,
    build_task_input: Callable[[dict], dict],
) -> Callable[[Message], Any]:
    """Return a bus handler that runs the dispatched work *inside the arm's
    own lifecycle* (gate: "arm lifecycle runs the dispatched capacity") and
    replies the outcome to the Manager (PB-FFF deferred-reply: the handler
    enqueues on the IL pool and returns DEFER, keeping the arm's consumer
    thread responsive)."""

    from .brain import run_task

    def handler(msg: Message):
        cmd = msg.payload or {}
        task_input = build_task_input(cmd)

        def on_done(fut):
            try:
                outcome = fut.result()
                # comms.report (capacity) formats the outcome → graph-honest
                res = brain.cl.invoke(
                    REPORT_IRI,
                    {DS_TASK_OUTCOME: {"status": getattr(outcome, "status", "succeeded"),
                                       "task_pattern": getattr(outcome, "outcome", None)}},
                    session=None,
                )
                report = res.outputs.get(DS_DISPATCH_ACK, {"status": "succeeded"})
            except Exception as exc:  # noqa
                report = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
            bus.reply(msg, report)

        # PB-HHH: fresh per-task Orchestrator scope (a 2nd dispatch to the same
        # arm would otherwise collide chain-artifact IRIs).
        fut = run_task(brain, task_input, task_id=cmd.get("task_id") or "dispatch")
        fut.add_done_callback(on_done)
        return DEFER

    return handler


__all__ = [
    "install_override",
    "encode_target",
    "decode_target",
    "register_comms_capacities",
    "make_dispatch_handler",
    "DISPATCH_IRI", "REPORT_IRI", "QUERY_CAPS_IRI", "SHARE_IRI",
    "DS_DISPATCH_CMD", "DS_DISPATCH_ACK", "DS_TASK_OUTCOME",
    "DS_CAP_QUERY", "DS_CAP_REPORT", "DS_SHARE_ARTIFACT", "DS_SHARE_ACK",
    "CAT_COMMS", "TOPIC_CAP_REPORT", "KIND_DISPATCH",
]
