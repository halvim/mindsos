"""L4 injects the model client only into capacities that DECLARED it.

**Rewritten 2026-08-16.** The seam inferred this from the capacity's
CATEGORY (``LLM_CATEGORIES``), endorsed on a premise that turned out to be
backwards: ``reads_mm`` — the pattern it claimed to mirror — is a
per-declaration flag, not a category rule (coordination §87 T-F7, critic
§88 Q1). A category says what a capacity IS; a dependency says what it
DOES, and only the second can be read off the registry per capacity.

So ``Capacity.consults_llm`` is the declaration, and a body that did not
ask is handed ``None``. "Declared == what the body can reach" stays
structurally true for this channel as it does for the MM handle.
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
from mindsos_intelligence.dispatch import L4Dispatcher, LLMUnavailableError

DS_IN = datastate_iri("seam.text")
DS_OUT = datastate_iri("seam.seen_llm")


class _LLM:
    def read(self, **kwargs):  # pragma: no cover — never called here
        return {}


def _layer(category: str, *, consults_llm: bool) -> CapacityLayer:
    layer = CapacityLayer()
    for name, desc in ((DS_IN, "Input text."), (DS_OUT, "Whether a client arrived.")):
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
            description="Report whether a model capability was injected.",
            consults_llm=consults_llm,
        )
    )
    return layer


def _dispatch(category: str, llm, *, consults_llm: bool):
    layer = _layer(category, consults_llm=consults_llm)
    iri = [i for i in layer._capacity_index[layer.global_metagraph().metagraph_id]][0]
    return L4Dispatcher(layer, llm=llm).dispatch(
        iri, {DS_IN: "some text"}, request_id="r1"
    )


def test_a_capacity_that_declared_it_receives_the_client():
    result = _dispatch(CATEGORY_COMPREHENSION, _LLM(), consults_llm=True)
    assert result.success is True
    assert result.outputs[DS_OUT] is True


def test_a_capacity_that_did_not_declare_it_never_sees_it():
    result = _dispatch(CATEGORY_COMPREHENSION, _LLM(), consults_llm=False)
    assert result.success is True
    assert result.outputs[DS_OUT] is False, (
        "being in the comprehension category is not a declaration - that was "
        "the mechanism this test was rewritten to remove"
    )


def test_the_declaration_travels_and_not_the_category():
    """The other half of the same point: a capacity OUTSIDE the
    comprehension category that declares the dependency gets the client.
    Under the category rule this was unreachable, and "the day a
    non-comprehension capacity needs a model" was filed as the condition
    to re-open that rule. There is nothing left to re-open."""
    result = _dispatch(CATEGORY_REDUCTION, _LLM(), consults_llm=True)
    assert result.outputs[DS_OUT] is True


def test_a_declared_capacity_with_no_client_bound_is_a_deployment_error():
    # Not a don't-know: a body that silently declined here would put an
    # unexplained refusal into a Decision Record.
    with pytest.raises(LLMUnavailableError):
        _dispatch(CATEGORY_COMPREHENSION, None, consults_llm=True)


def test_that_error_ESCAPES_the_executor_rather_than_stopping_one_member():
    """**The fatality pin** (coordination §87 T-F9 / ruling 8). The raise
    happens before ``runtime.invoke``'s envelope and ``execute_pipeline``
    does not wrap the dispatch call, so it propagates out of the run
    instead of becoming a stopped member.

    Deliberate: a dispatcher with no client bound fails identically for
    EVERY member, so a partial Record would be a Record of nothing. It is
    pinned because the escape LOOKS like an oversight, and the obvious
    "fix" - catching it into a stop - would produce a page full of stops
    with no cause. Mutation: wrap the dispatch call in
    ``pipeline_execution`` and this test goes red.
    """
    from mindsos_intelligence.pipeline_execution import execute_pipeline

    layer = _layer(CATEGORY_COMPREHENSION, consults_llm=True)
    iri = [i for i in layer._capacity_index[layer.global_metagraph().metagraph_id]][0]
    dispatcher = L4Dispatcher(layer, llm=None)

    class _Step:
        capacity_iri = iri
        input_datastates = (DS_IN,)

    class _Pipeline:
        steps = (_Step(),)
        start_datastates = (DS_IN,)

    with pytest.raises(LLMUnavailableError):
        execute_pipeline(
            dispatcher, _Pipeline(), {DS_IN: "some text"},
            request_id="r1", mm=None, pipeline_run_ref="pipelinerun:r1:0:0",
        )


def test_build_context_defaults_to_no_client():
    layer = _layer(CATEGORY_REDUCTION, consults_llm=False)
    dispatcher = L4Dispatcher(layer, llm=_LLM())
    assert dispatcher.build_context().llm is None
    assert dispatcher.build_context(consults_llm=True).llm is not None
