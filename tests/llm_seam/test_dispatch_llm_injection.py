"""L4 injects the LLM only into LLM-consulting categories.

Capacities already live in per-category graphs, so membership of a
category in ``LLM_CATEGORIES`` IS the declaration — no per-capacity
field. A capacity outside those categories is handed nothing and cannot
reach a model, and the set that may is one registry query.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import CapacityLayer
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_COMPREHENSION,
    CATEGORY_REDUCTION,
    datastate_iri,
)
from mindsos_intelligence.dispatch import (
    LLM_CATEGORIES,
    L4Dispatcher,
    LLMUnavailableError,
)

DS_IN = datastate_iri("seam.text")
DS_OUT = datastate_iri("seam.seen_llm")


class _LLM:
    def read(self, **kwargs):  # pragma: no cover — never called here
        return {}


def _layer(category: str) -> CapacityLayer:
    layer = CapacityLayer()
    for name, desc in ((DS_IN, "Input text."), (DS_OUT, "Whether an LLM arrived.")):
        layer.register_datastate(
            DataState(
                name=name.split(":", 1)[-1],
                shape=ShapeDescriptor.opaque(name),
                description=desc,
                provenance_category=CATEGORY_COMPREHENSION,
            ),
            allow_new_realm=True,
        )
    layer.register_capacity(
        Capacity(
            name="probe",
            category=category,
            inputs=(DS_IN,),
            outputs=(DS_OUT,),
            implementation=lambda **kw: {
                DS_OUT: getattr(kw.get("context"), "llm", None) is not None
            },
            description="Report whether an LLM capability was injected.",
        )
    )
    return layer


def _dispatch(category: str, llm):
    layer = _layer(category)
    dispatcher = L4Dispatcher(layer, llm=llm)
    iri = [i for i in layer._capacity_index[layer.global_metagraph().metagraph_id]][0]
    return dispatcher.dispatch(iri, {DS_IN: "some text"}, request_id="r1")


def test_a_capacity_in_an_llm_category_receives_the_llm():
    result = _dispatch(CATEGORY_COMPREHENSION, _LLM())
    assert result.success is True
    assert result.outputs[DS_OUT] is True


def test_a_capacity_outside_those_categories_never_sees_it():
    result = _dispatch(CATEGORY_REDUCTION, _LLM())
    assert result.success is True
    assert result.outputs[DS_OUT] is False


def test_an_llm_category_with_no_llm_bound_is_a_deployment_error():
    # Not a don't-know: a body that silently declined here would put an
    # unexplained refusal into a Decision Record.
    with pytest.raises(LLMUnavailableError):
        _dispatch(CATEGORY_COMPREHENSION, None)


def test_build_context_defaults_to_no_llm():
    dispatcher = L4Dispatcher(_layer(CATEGORY_REDUCTION), llm=_LLM())
    assert dispatcher.build_context().llm is None
    assert dispatcher.build_context(consults_llm=True).llm is not None
