"""ADR-0156 §amendment-1 — ``if_exists="upsert"`` re-binds the in-memory
declaration, not only the PRODUCES/CONSUMES edges.

Before the amendment, the upsert branch of ``register_capacity`` reused the
existing node and re-emitted missing edges but never re-assigned
``self._declarations[iri]`` — so re-registering an IRI with a new
``implementation`` was a behavioural no-op (the old impl stayed bound, the
live defect the demo's re-teach path hit). The amendment broadens upsert to
also re-bind the declaration (last-registration-wins, mirroring the
fresh-registration branch + the Local-wins ``_declarations`` semantic), so
``invoke`` resolves the swapped implementation.

The edge-idempotency invariant (no duplicate PRODUCES/CONSUMES on re-register)
is retained — guarded here alongside the rebind so the two cannot regress
independently.
"""

from __future__ import annotations

from mindsos_capacity import Capacity
from mindsos_capacity.identifiers import (
    CATEGORY_PERCEPTION,
    EDGE_CONSUMES,
    EDGE_PRODUCES,
)

from tests.phase_30._fixtures import (
    DS_INPUT_IRI,
    DS_MID_IRI,
    build_min_layer,
)


def _edges(mg, type_name):
    return [ie for ie in mg.iter_intergraph_edges() if ie.type_name == type_name]


def _swap_capacity(label: str) -> Capacity:
    """A step1-shaped read capacity (input→mid) whose impl returns ``label``."""
    return Capacity(
        name="test.step1",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_INPUT_IRI,),
        outputs=(DS_MID_IRI,),
        implementation=lambda context=None, **inputs: {DS_MID_IRI: label},
    )


def test_upsert_rebinds_implementation():
    cl = build_min_layer()
    cl.register_capacity(_swap_capacity("A"))
    iri = "capacity:perception:test.step1"

    first = cl.invoke(iri, {DS_INPUT_IRI: "x"})
    assert first.success and first.outputs[DS_MID_IRI] == "A"

    # Re-register the same IRI under upsert with a different implementation.
    cl.register_capacity(_swap_capacity("B"), if_exists="upsert")

    # ADR-0156 §amendment-1: invoke now resolves the swapped implementation.
    second = cl.invoke(iri, {DS_INPUT_IRI: "x"})
    assert second.success and second.outputs[DS_MID_IRI] == "B"

    # get_declaration reflects the most-recent registration.
    assert cl.get_declaration(iri).implementation(context=None) == {DS_MID_IRI: "B"}


def test_upsert_rebind_does_not_duplicate_edges_or_declarations():
    cl = build_min_layer()
    cl.register_capacity(_swap_capacity("A"))
    mg = cl.global_metagraph()
    before_p = len(_edges(mg, EDGE_PRODUCES))
    before_c = len(_edges(mg, EDGE_CONSUMES))
    before_decls = len(cl.iter_declarations())

    cl.register_capacity(_swap_capacity("B"), if_exists="upsert")

    # Edge-idempotency retained; the rebind reuses the single IRI slot.
    assert len(_edges(mg, EDGE_PRODUCES)) == before_p
    assert len(_edges(mg, EDGE_CONSUMES)) == before_c
    assert len(cl.iter_declarations()) == before_decls
