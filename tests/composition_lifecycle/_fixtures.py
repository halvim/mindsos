"""composition-lifecycle — shared fixture builders (pure L3, no live DB).

Hand-rolled DataState + Capacity shapes (Phase-28 fixture style), used by
the finder-seam / conjunction-finder / input-group tests.
"""

from __future__ import annotations

from mindsos_capacity import (
    CATEGORY_PERCEPTION,
    Capacity,
    CapacityLayer,
    DataState,
    INPUT_GROUP_ALL_REQUIRED,
    ShapeDescriptor,
)


def IRI(short: str) -> str:
    """``datastate:t.<short>`` IRI for a test DataState."""
    return f"datastate:t.{short}"


def ds(short: str) -> DataState:
    full = f"t.{short}"
    return DataState(name=full, shape=ShapeDescriptor.scalar("str", opaque_tag=full))


def cap(
    name: str,
    inputs,
    outputs,
    input_group: str = INPUT_GROUP_ALL_REQUIRED,
) -> Capacity:
    return Capacity(
        name=name,
        category=CATEGORY_PERCEPTION,
        inputs=tuple(IRI(i) for i in inputs),
        outputs=tuple(IRI(o) for o in outputs),
        input_group=input_group,
        implementation=lambda **kw: {},
    )


def layer(*datastate_shorts: str) -> CapacityLayer:
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    for short in datastate_shorts:
        cl.register_datastate(ds(short), allow_new_realm=True)
    return cl


def step_index(dag, name_suffix: str) -> int:
    """Index of the step whose capacity IRI ends with ``name_suffix``."""
    for i, s in enumerate(dag.steps):
        if s.capacity_iri.endswith(name_suffix):
            return i
    raise AssertionError(f"no step ending {name_suffix!r} in {[s.capacity_iri for s in dag.steps]}")


def incoming_datastates(dag, consumer_idx: int):
    """The ``datastate`` short-names wired *into* ``consumer_idx``."""
    return sorted(
        e.datastate.split(".")[-1] for e in dag.edges if e.consumer == consumer_idx
    )
