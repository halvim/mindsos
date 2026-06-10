"""Reference-bundle L3 installer (Phase 50 — ADR-0183 §1/R2-3).

Release-side code referenced by the bundle manifest's installer entry
point (``tests.fixtures.skill_bundle_ref.installer:install_ref_skill``)
and resolved via ``importlib`` over modules already on the path — no
bundle-path code loading.

The capacity body is **CapacityContext-native** per design log S9
(L3-59(a)): typed ``CapacityContext`` annotation, attribute access only
— never the dict form. Idempotency follows the builtins triple
(all-present → no-op; partial → error; none → install), DataStates
first.
"""

from __future__ import annotations

from typing import Any, Optional

from mindsos_capacity import Capacity, DataState, ShapeDescriptor
from mindsos_capacity.bootstrap import ensure_datastate_graph
from mindsos_capacity.builtins.text import DS_RAW_TEXT
from mindsos_capacity.context import CapacityContext
from mindsos_capacity.exceptions import CapacityRegistrationError
from mindsos_capacity.identifiers import (
    CATEGORY_PERCEPTION,
    capacity_iri,
    datastate_iri,
)

DS_REF_SHOUTED = datastate_iri("text.ref_shouted")
CAP_REF_SHOUT = capacity_iri(CATEGORY_PERCEPTION, "text.ref_shout")

_FAMILY_IRIS = (DS_REF_SHOUTED, CAP_REF_SHOUT)


def ref_shouted_datastate() -> DataState:
    return DataState(
        name="text.ref_shouted",
        shape=ShapeDescriptor.scalar("str", opaque_tag="text.ref_shouted"),
        description="An upper-cased string (reference-bundle demo).",
        provenance_category=CATEGORY_PERCEPTION,
    )


def _ref_shout(
    *, text: str, context: Optional[CapacityContext] = None
) -> str:
    """Upper-case ``text``. CapacityContext-native (S9): the typed
    ``context`` is accepted and accessed by attribute only (unused
    here — the reference body needs no KL access)."""
    if text is None:
        return ""
    if not isinstance(text, str):
        raise TypeError(f"ref_shout expects str, got {type(text).__name__}")
    return text.upper()


def _ref_shout_callable(**kwargs: Any) -> dict:
    return {
        DS_REF_SHOUTED: _ref_shout(
            text=kwargs.get(DS_RAW_TEXT), context=kwargs.get("context")
        )
    }


def build_ref_shout() -> Capacity:
    """Capacity: ``text.raw`` → ``text.ref_shouted``."""
    return Capacity(
        name="text.ref_shout",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_RAW_TEXT,),
        outputs=(DS_REF_SHOUTED,),
        implementation=_ref_shout_callable,
        description="Reference-bundle upper-caser. text.raw → text.ref_shouted.",
        cost_prior=1.0,
        latency_ms_prior=1.0,
    )


def install_ref_skill(capacity_layer: Any) -> None:
    """Idempotent installer (builtins triple; DataStates first).

    Requires the ``text`` builtins to be installed first
    (``DS_RAW_TEXT`` is this capacity's input) — the bundle's driver-
    level guarantee is the activation order, not this function.

    Raises:
        CapacityRegistrationError: partial install state detected.
    """
    mg = capacity_layer.global_metagraph()
    cap_index = capacity_layer._capacity_index[mg.metagraph_id]
    ds_graph = ensure_datastate_graph(mg, strict=capacity_layer._strict)

    ds_present = DS_REF_SHOUTED in ds_graph.nodes
    cap_present = CAP_REF_SHOUT in cap_index
    if ds_present and cap_present:
        return  # all present — no-op
    if ds_present or cap_present:
        raise CapacityRegistrationError(
            "install_ref_skill: partial install state detected — "
            f"datastate_present={ds_present}, capacity_present={cap_present}"
        )
    capacity_layer.register_datastate(ref_shouted_datastate())
    capacity_layer.register_capacity(build_ref_shout())


__all__ = [
    "DS_REF_SHOUTED",
    "CAP_REF_SHOUT",
    "ref_shouted_datastate",
    "build_ref_shout",
    "install_ref_skill",
]
