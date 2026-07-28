"""Reference LOCAL capability fixture (ADR-0183 §am-5 durable e2e).

A bundle module referenced as an ``l3.installers`` entry point AND declaring a
``[[l3.local_capacity]]`` (in the test's inline manifest). At boot,
``apply_installed_skills`` imports this module — registering the reactivation
factory that builds the live function on first use — and runs
``install_local_cap_skill`` to register the capability's input/output DataStates
Global. The capability itself is registered **metadata-only per user** by the
boot step (ADR-0183 §am-5), and its function is built on first ``invoke``.
"""

from __future__ import annotations

from typing import Any

from mindsos_capacity import (
    Capacity,
    DataState,
    ShapeDescriptor,
    register_reactivation_factory,
)
from mindsos_capacity.bootstrap import ensure_datastate_graph
from mindsos_capacity.identifiers import (
    CATEGORY_PERCEPTION,
    capacity_iri,
    datastate_iri,
)

DS_LC_IN = datastate_iri("text.lc_in")
DS_LC_OUT = datastate_iri("text.lc_out")
CAP_LC = capacity_iri(CATEGORY_PERCEPTION, "text.lc_shout")
REACT_KEY = "ref-local-shout"


def _lc_in_ds() -> DataState:
    return DataState(
        name="text.lc_in",
        shape=ShapeDescriptor.scalar("str", opaque_tag="text.lc_in"),
    )


def _lc_out_ds() -> DataState:
    return DataState(
        name="text.lc_out",
        shape=ShapeDescriptor.scalar("str", opaque_tag="text.lc_out"),
    )


def _lc_factory(desc: dict) -> Capacity:
    """The skill's builder — produces ONLY the live function (called on first
    use). Uppercases the input."""
    out = desc["outputs"][0]
    inp = desc["inputs"][0]
    return Capacity(
        name=desc["name"],
        category=desc["category"],
        inputs=tuple(desc["inputs"]),
        outputs=tuple(desc["outputs"]),
        implementation=lambda **kw: {out: str(kw[inp]).upper()},
    )


# Registered at import — apply_installed_skills imports this module at boot, so
# the builder is available when the capability is first invoked.
register_reactivation_factory(REACT_KEY, _lc_factory, if_exists="upsert")


def install_local_cap_skill(capacity_layer: Any) -> None:
    """Idempotent installer: register the Local capability's input/output
    DataStates Global (mirrored Local-side at registration). The capability
    itself is registered per user at boot, not here."""
    mg = capacity_layer.global_metagraph()
    ds_graph = ensure_datastate_graph(mg, strict=capacity_layer._strict)
    if DS_LC_IN not in ds_graph.nodes:
        capacity_layer.register_datastate(_lc_in_ds())
    if DS_LC_OUT not in ds_graph.nodes:
        capacity_layer.register_datastate(_lc_out_ds())


__all__ = [
    "DS_LC_IN",
    "DS_LC_OUT",
    "CAP_LC",
    "REACT_KEY",
    "install_local_cap_skill",
]
