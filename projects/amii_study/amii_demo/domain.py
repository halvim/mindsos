"""The demo domain — DataStates, Capacities, and the layer builder, defined ONCE.

Built against the shipped core API (verified in this session):

* ``CapacityLayer(categories=...)`` — keyword-only ctor; builds an in-memory
  metagraph, no FalkorDB.
* ``register_datastate(ds, allow_new_realm=True)`` — DataState names are
  ``<realm>.<name>`` (single dot); ``demo`` is a non-reserved realm, hence
  ``allow_new_realm=True``.
* ``register_capacity`` — emits the PRODUCES/CONSUMES edges the finder walks.
* ``find_pipeline(cl, start_datastate=, target_datastate=)`` — keyword-only.
* ``runtime.invoke(decl, inputs, task_id=, step_id=)`` -> InvocationResult.

Categories use the public functional set (perception / comprehension /
derivation). The retired ``CATEGORY_DECISION`` is deliberately not used.
The finder ignores category for composition (it walks typed dataflow), so
the labels are organisational only.
"""
from __future__ import annotations

from mindsos_capacity import (
    Capacity,
    CapacityLayer,
    DataState,
    ShapeDescriptor,
    INPUT_GROUP_ALL_REQUIRED,
    CATEGORY_PERCEPTION,
    CATEGORY_COMPREHENSION,
    CATEGORY_DERIVATION,
)
from mindsos_capacity.needs_input import NeedsInput
from mindsos_capacity.runtime import invoke


# ── DataState IRIs (the "vocabulary" a person teaches) ─────────────────
def IRI(short: str) -> str:
    return f"datastate:demo.{short}"


RAW = IRI("raw_signal")
PARSED = IRI("parsed_signal")
NORMAL = IRI("normal_signal")
CONDITION = IRI("condition")
ACTION = IRI("action")
DIAGNOSIS = IRI("diagnosis")  # registered but no producer -> the no-route refusal

# The taught operating conditions (the knowledge a person supplies).
CONDITIONS = {"pressure_high": "vent", "pressure_low": "seal", "nominal": "hold"}


def _ds(short: str) -> DataState:
    name = f"demo.{short}"
    return DataState(name=name, shape=ShapeDescriptor.scalar("str", opaque_tag=name))


def _cap(name, category, inputs, outputs, impl) -> Capacity:
    return Capacity(
        name=name,
        category=category,
        inputs=tuple(inputs),
        outputs=tuple(outputs),
        input_group=INPUT_GROUP_ALL_REQUIRED,
        implementation=impl,
    )


# ── Capacity bodies. Inputs arrive keyed by DataState IRI. ─────────────
def _parse(**kw):
    return {PARSED: str(kw[RAW]).strip().lower()}


def _normalize(**kw):
    return {NORMAL: kw[PARSED].replace(" ", "_")}


def _classify(**kw):
    v = kw[NORMAL]
    if v not in CONDITIONS:  # honest refusal at the unit (returns a typed ask)
        return NeedsInput(
            question=f"Unrecognized reading {v!r}; which condition is this?",
            missing=CONDITION,
            choices={c: c for c in CONDITIONS},
        )
    return {CONDITION: v}


def _recommend(**kw):
    return {ACTION: CONDITIONS[kw[CONDITION]]}


def build_layer() -> CapacityLayer:
    """Register the demo DataStates + four single-purpose Capacities.

    No pipeline is wired — composing ``raw_signal -> action`` is the
    finder's job, from the typed PRODUCES/CONSUMES edges alone.
    """
    cl = CapacityLayer(
        categories=(CATEGORY_PERCEPTION, CATEGORY_COMPREHENSION, CATEGORY_DERIVATION)
    )
    for short in (
        "raw_signal",
        "parsed_signal",
        "normal_signal",
        "condition",
        "action",
        "diagnosis",
    ):
        cl.register_datastate(_ds(short), allow_new_realm=True)
    cl.register_capacity(_cap("parse", CATEGORY_PERCEPTION, [RAW], [PARSED], _parse))
    cl.register_capacity(_cap("normalize", CATEGORY_COMPREHENSION, [PARSED], [NORMAL], _normalize))
    cl.register_capacity(_cap("classify", CATEGORY_DERIVATION, [NORMAL], [CONDITION], _classify))
    cl.register_capacity(_cap("recommend", CATEGORY_DERIVATION, [CONDITION], [ACTION], _recommend))
    return cl


class Dispatcher:
    """Adapts the shipped ``runtime.invoke`` to ``execute_pipeline``'s
    dispatcher contract (``.dispatch(capacity_iri, inputs, *, ...)``)."""

    def __init__(self, cl: CapacityLayer) -> None:
        self.cl = cl

    def dispatch(self, capacity_iri, inputs, *, cancel_token=None, task_id=None, step_id=None):
        return invoke(
            self.cl.get_declaration(capacity_iri),
            inputs,
            task_id=task_id,
            step_id=step_id,
        )
