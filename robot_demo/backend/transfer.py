"""DM-7 — teach + peer-transfer (F1/F2), the Local-override framing.

Design picks (design-log §27, probe-validated 2026-06-15):

* **PB-1 Local-override.** A taught skill is NOT a Global ``promoted-pipelines``
  node (that role is Global-only). It is: (a) a **Local ``learned-parameters``
  node** holding the capability descriptor (steps + required-affordances +
  optional motion cache key) — the graph-visible learned artifact; (b) a
  **composite capacity registered on the brain's own CL** that replays the
  descriptor's steps; (c) optionally a **``TrajectoryCache`` clip** (the motion
  blob stays in the motion store, never in L2).

* **PB-2 receiver-side transfer.** No cross-Local **write** capability is
  shipped, so the sender never writes the peer's Local. Instead the sender
  ``bus.send``s the descriptor and the **receiver's own** ``share`` handler
  writes it into the **receiver's own** Local under the **receiver's own**
  session via the shipped ``make_writeable``/ADR-0180 gate. No new cap, no
  ``mindsos_*`` edit.

* **PB-3 receiver performs it (no fabrication).** ``receive_taught`` reconstitutes
  a working composite on the receiver (Local node + CL registration + cache
  pre-fill). The §5.2 embodiment gate still fires receiver-side (it reads the
  receiver's own embodiment bag), so a transferred capability is still
  body-gated — e.g. the jaw arm is still refused a suction-only target.

MuJoCo-free + sandbox-testable, mirroring the DM-5 ``assembled`` split: this
module handles the *descriptor + graph writes + CL declaration*; the live body
execution is injected as ``run_step`` (a stub in the sandbox, the real atomic
on the Linux gate). Only **data** travels peer-to-peer — never code or a body.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from mindsos_capacity import Capacity
from mindsos_capacity.context import make_writeable
from mindsos_capacity.identifiers import capacity_iri
from mindsos_knowledge.identifiers import ROLE_LEARNED_PARAMETERS, learned_parameter_iri
from mindsos_knowledge.schemas.learned_parameters import NODE_LEARNED_PARAMETER

from .capacities import CAT_MECHANISM, DS_MOTION_DONE, DS_POSE_TARGET, _as_payload

#: bus message kind for a peer skill-transfer (the receiver-side handler kind).
KIND_SHARE = "share"

#: ``run_step(op, args) -> outcome`` — the injected live executor (body-driven
#: on the gate; ``None`` in the sandbox → a declarative replay).
RunStep = Callable[[str, dict], Any]


def build_share_artifact(
    capability_name: str,
    steps: List[Dict[str, Any]],
    requires_affordances: List[str],
    *,
    peer: Optional[str] = None,
    cache_key: Optional[Tuple[Any, ...]] = None,
    clip: Optional[Any] = None,
    param_id: Optional[str] = None,
    confidence: float = 1.0,
) -> Dict[str, Any]:
    """Package a taught composite for ``teach_local`` / peer-transfer.

    ``steps`` = ``[{"op": "move_to"|"set_grip"|"run_belt", "args": {...}}, …]``
    (a linear Pipeline descriptor — concurrency lives in the Orchestrator Plan,
    not here, per Scenario §5.1). ``peer`` is the transfer target device id.
    """
    return {
        "capability_name": capability_name,
        "steps": list(steps),
        "requires_affordances": list(requires_affordances),
        "peer": peer,
        "cache_key": list(cache_key) if cache_key is not None else None,
        "clip": clip,
        "param_id": param_id or capability_name,
        "confidence": confidence,
    }


def make_taught_impl(steps: List[Dict[str, Any]], run_step: Optional[RunStep] = None):
    """Build the composite impl that replays ``steps`` over the brain's body.

    ``run_step`` is the live executor (injected with the brain's body on the
    gate). ``None`` (sandbox/declaration) → each step records ``status:declared``
    without touching a body; the graph composite is still honest + gate-able.
    """

    def impl(context=None, **inputs):
        spec = inputs.get(DS_POSE_TARGET) or {}
        executed: List[dict] = []
        ok = True
        for st in steps:
            op = st.get("op", "")
            args = {**(st.get("args") or {}), **(spec if isinstance(spec, dict) else {})}
            if run_step is not None:
                out = run_step(op, args)
                payload = out if isinstance(out, dict) else _as_payload(out)
                if payload.get("status") == "dont_know" or payload.get("ok") is False:
                    ok = False
                executed.append({"op": op, **payload})
                if not ok:
                    break
            else:
                executed.append({"op": op, "status": "declared"})
        return {DS_MOTION_DONE: {
            "status": "done" if ok else "dont_know",
            "taught": True,
            "composite": True,
            "steps": executed,
        }}

    return impl


def _learned_params_graph(brain: Any):
    """The brain's OWN Local ``learned-parameters`` graph, via the ADR-0180 gate."""
    writeable = make_writeable(brain.kl, brain.session)
    if writeable is None:
        raise RuntimeError("no KL bound; make_writeable returned None")
    return writeable(role=ROLE_LEARNED_PARAMETERS, scope="local").graph()


def teach_local(
    brain: Any,
    artifact: Dict[str, Any],
    *,
    run_step: Optional[RunStep] = None,
    cache: Optional[Any] = None,
) -> str:
    """Install a taught composite into ``brain``'s OWN Local + CL (idempotent).

    Writes the ``learned-parameters`` descriptor node, registers the composite
    capacity on the brain's CL, and (if a clip + cache are supplied) pre-fills
    the motion store. Returns the ``learned-parameters`` node iri. Used both for
    the original teach (on the teaching arm) and on the receiver (``receive_taught``).
    """
    name = artifact["capability_name"]
    node_iri = learned_parameter_iri("v1", artifact.get("param_id") or name)

    g = _learned_params_graph(brain)
    if node_iri not in g.nodes:
        g.add_node(
            {
                "capability": name,
                "steps": artifact["steps"],
                "requires_affordances": artifact.get("requires_affordances", []),
                "cache_key": artifact.get("cache_key"),
                "source": artifact.get("source", brain.device_id),
                "reactivation_key": "taught",
                "category": CAT_MECHANISM,
                "inputs": [DS_POSE_TARGET],
                "outputs": [DS_MOTION_DONE],
                "node_kind": "reactive",
            },
            NODE_LEARNED_PARAMETER,
            properties={
                "parameter_set_iri": f"taught:{name}",
                "confidence": float(artifact.get("confidence", 1.0)),
                "peer_from": artifact.get("source"),
            },
            node_id=node_iri,
        )

    decl = Capacity(
        name=name,
        category=CAT_MECHANISM,
        inputs=(DS_POSE_TARGET,),
        outputs=(DS_MOTION_DONE,),
        implementation=make_taught_impl(artifact["steps"], run_step),
        description=f"DM-7 taught composite {name} ({brain.device_id}).",
    )
    brain.cl.register_capacity(decl, session=brain.session, if_exists="upsert")

    clip, cache_key = artifact.get("clip"), artifact.get("cache_key")
    if clip is not None and cache is not None and cache_key is not None:
        cache.put(tuple(cache_key), clip)

    return node_iri


def receive_taught(
    brain: Any,
    artifact: Dict[str, Any],
    src: str,
    *,
    run_step: Optional[RunStep] = None,
    cache: Optional[Any] = None,
) -> str:
    """Receiver-side teach: stamp the origin, then ``teach_local`` into the
    receiver's OWN Local (the embodiment gate still applies at dispatch)."""
    stamped = {**artifact, "source": src}
    return teach_local(brain, stamped, run_step=run_step, cache=cache)


def make_share_handler(
    brain: Any,
    *,
    run_step: Optional[RunStep] = None,
    cache: Optional[Any] = None,
    on_receive: Optional[Callable[[str, str, Dict[str, Any]], None]] = None,
):
    """Bus ``share`` handler for a receiver brain (PB-2): write the transferred
    descriptor into the receiver's OWN Local + register the composite. Never
    touches the sender's Local. ``on_receive(src, capability_name, artifact)``
    is an optional narration hook (behavior-level, policy B)."""

    def handler(msg: Any) -> None:
        artifact = msg.payload or {}
        if not artifact.get("capability_name"):
            return
        receive_taught(brain, artifact, msg.src, run_step=run_step, cache=cache)
        if on_receive is not None:
            on_receive(msg.src, artifact["capability_name"], artifact)

    return handler


def has_taught(brain: Any, capability_name: str, *, param_id: Optional[str] = None) -> bool:
    """True if ``brain`` holds the taught descriptor in its Local (read side)."""
    from mindsos_knowledge.metagraph_view import MetagraphView

    node_iri = learned_parameter_iri("v1", param_id or capability_name)
    try:
        local_mg = brain.kl.local_metagraph(brain.device_id)
        for gr in MetagraphView(local_mg).graphs_by_role(ROLE_LEARNED_PARAMETERS):
            if node_iri in gr.nodes:
                return True
    except Exception:
        return False
    return False


__all__ = [
    "KIND_SHARE",
    "build_share_artifact",
    "make_taught_impl",
    "teach_local",
    "receive_taught",
    "make_share_handler",
    "has_taught",
]
