"""DM-2 — release-side L3 bundle installers (referenced by manifest TOML).

A skill bundle's ``[l3].installers`` names import paths resolved by the
Phase-50 driver over release-shipped modules only (``importlib``; no
bundle-path code loading). The demo's only DM-2 installer registers the
``robot`` realm + the §4.0 DataStates into a device's CapacityLayer.

Embodied L3 capacities (§4.1-§4.3) are **not** here — they need a
per-brain ``BodyHandle`` closure and land in DM-3 (registered directly,
not via a bundle installer). At DM-2 the bundle's L3 footprint is the
DataState/realm registration only (plan §3.4 item 3, scoped to DataStates
per the DM-2 do-not "no L3 demo capacities").

Idempotency: the builtins triple (all-present → no-op; partial → error;
none → install) so ``apply_installed_skills`` can re-run the installer on
every boot. ``register_datastate(session=None)`` targets the CL's Global
DataState graph via the ADR-0080 bootstrap carve-out; ``robot`` is not a
reserved realm, so ``allow_new_realm=True`` is required (plan §4.0).
"""

from __future__ import annotations

from typing import Any, List, Tuple

from mindsos_capacity import DataState, ShapeDescriptor
from mindsos_capacity.bootstrap import ensure_datastate_graph
from mindsos_capacity.exceptions import CapacityRegistrationError
from mindsos_capacity.identifiers import datastate_iri

#: Realm for every demo DataState (plan §4.0). Not in RESERVED_REALMS →
#: register_datastate needs allow_new_realm=True.
REALM_ROBOT = "robot"

#: The §4.0 DataState suffixes (realm-stripped). Order is stable for the
#: idempotency roster + tests.
ROBOT_DATASTATE_NAMES: Tuple[str, ...] = (
    "order",
    "order_lines",
    "allocation",
    "plan",
    "dispatch_cmd",
    "dispatch_ack",
    "task_outcome",
    "cap_query",
    "cap_report",
    "share_artifact",
    "share_ack",
    "world_fact",
    "pose_target",
    "motion_done",
    "grip_cmd",
    "grip_state",
    "pick_goal",
    "holding",
    "place_goal",
    "placed",
    "on_belt",
    "in_box",
    "belt_cmd",
    "belt_done",
    "stage_goal",
    "staged",
    "diag_request",
    "diag_report",
    "teach_blocks",
    "pipeline_artifact",
    "feasibility_verdict",
    "demo_event",
)


def _robot_datastate(suffix: str) -> DataState:
    """Build one ``robot.<suffix>`` DataState.

    Opaque shape at DM-2 — the demo capacities (DM-3+) carry their real
    payloads in node values; the DataState is the typed handle the
    PRODUCES/CONSUMES edges reference. ``provenance_category`` is left
    unset (no family is the canonical producer at registration time).
    """
    name = f"{REALM_ROBOT}.{suffix}"
    return DataState(
        name=name,
        shape=ShapeDescriptor.opaque(name),
        description=f"Robot-demo DataState {name} (DM-2 §4.0).",
    )


def robot_datastate_iris() -> Tuple[str, ...]:
    """The 32 ``datastate:robot.*`` IRIs, for tests + roster checks."""
    return tuple(
        datastate_iri(f"{REALM_ROBOT}.{s}") for s in ROBOT_DATASTATE_NAMES
    )


def install_core_datastates(capacity_layer: Any) -> None:
    """Register the ``robot`` realm + §4.0 DataStates (idempotent triple).

    Raises:
        CapacityRegistrationError: partial install state detected
            (some robot DataStates present, some absent).
    """
    mg = capacity_layer.global_metagraph()
    ds_graph = ensure_datastate_graph(mg, strict=capacity_layer._strict)

    iris = robot_datastate_iris()
    present = [iri for iri in iris if iri in ds_graph.nodes]
    if len(present) == len(iris):
        return  # all present — no-op (re-activation path)
    if present:
        raise CapacityRegistrationError(
            "install_core_datastates: partial robot-realm state — "
            f"{len(present)}/{len(iris)} DataStates already registered."
        )
    for suffix in ROBOT_DATASTATE_NAMES:
        capacity_layer.register_datastate(
            _robot_datastate(suffix), allow_new_realm=True
        )


def installed_robot_datastates(capacity_layer: Any) -> List[str]:
    """Helper for tests/visibility: which robot DataStates are registered."""
    mg = capacity_layer.global_metagraph()
    ds_graph = ensure_datastate_graph(mg, strict=capacity_layer._strict)
    return [iri for iri in robot_datastate_iris() if iri in ds_graph.nodes]


__all__ = [
    "REALM_ROBOT",
    "ROBOT_DATASTATE_NAMES",
    "robot_datastate_iris",
    "install_core_datastates",
    "installed_robot_datastates",
]
