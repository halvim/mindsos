"""ADR-0198 (Part 5 / 5a) — same-type operand arity on invoke validation.

A capacity declaring ``operand_arity={DS: N>1}`` must receive a length-N
list under that key. Length only — core never inspects operand *value*
types. Default (absent / arity 1) preserves the single-operand behaviour,
so every pre-ADR-0198 capacity is unchanged.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import CATEGORY_PERCEPTION, Capacity
from mindsos_capacity.capacity import _validate_inputs
from mindsos_capacity.exceptions import CapacityRegistrationError, InputContractError

from tests.phase_30._fixtures import (
    DS_INPUT_IRI,
    DS_OUTPUT_IRI,
    build_echo_capacity,
    build_min_layer,
)


def _binary_comparator() -> Capacity:
    """A same-type binary comparator: two DS_INPUT operands → DS_OUTPUT."""
    return Capacity(
        name="test.same",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_INPUT_IRI,),
        outputs=(DS_OUTPUT_IRI,),
        operand_arity={DS_INPUT_IRI: 2},
        implementation=lambda **kw: {DS_OUTPUT_IRI: kw[DS_INPUT_IRI][0] == kw[DS_INPUT_IRI][1]},
    )


# ── happy path ────────────────────────────────────────────────────────


def test_length_n_list_succeeds():
    cl = build_min_layer()
    cap = _binary_comparator()
    cl.register_capacity(cap)
    result = cl.invoke(cap.iri, inputs={DS_INPUT_IRI: ["a", "a"]})
    assert result.success is True
    assert result.outputs == {DS_OUTPUT_IRI: True}


def test_body_reads_operands_by_position():
    cl = build_min_layer()
    cap = _binary_comparator()
    cl.register_capacity(cap)
    result = cl.invoke(cap.iri, inputs={DS_INPUT_IRI: ["a", "b"]})
    assert result.success is True
    assert result.outputs == {DS_OUTPUT_IRI: False}


# ── arity violations ──────────────────────────────────────────────────


def test_non_list_operand_rejected():
    cl = build_min_layer()
    cap = _binary_comparator()
    cl.register_capacity(cap)
    result = cl.invoke(cap.iri, inputs={DS_INPUT_IRI: "a"})
    assert result.success is False
    assert isinstance(result.error, InputContractError)
    assert result.error.kind == "operand_arity"


def test_wrong_length_operand_rejected():
    cl = build_min_layer()
    cap = _binary_comparator()
    cl.register_capacity(cap)
    result = cl.invoke(cap.iri, inputs={DS_INPUT_IRI: ["a", "b", "c"]})
    assert result.success is False
    assert isinstance(result.error, InputContractError)
    assert result.error.kind == "operand_arity"


def test_direct_validate_raises_on_arity():
    cap = _binary_comparator()
    try:
        _validate_inputs(cap, {DS_INPUT_IRI: ["only-one"]})
    except InputContractError as exc:
        assert exc.kind == "operand_arity"
    else:
        raise AssertionError("expected InputContractError")


# ── default arity is unchanged ────────────────────────────────────────


def test_default_arity_accepts_scalar():
    """A capacity with no operand_arity accepts a plain (non-list) value."""
    cl = build_min_layer()
    echo = build_echo_capacity()
    cl.register_capacity(echo)
    result = cl.invoke(echo.iri, inputs={DS_INPUT_IRI: "hi"})
    assert result.success is True
    assert result.outputs == {DS_OUTPUT_IRI: "hi"}


def test_arity_one_is_not_a_list_check():
    """Explicit arity 1 is a no-op (the branch only fires for N>1)."""
    cap = Capacity(
        name="test.arity1",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_INPUT_IRI,),
        outputs=(DS_OUTPUT_IRI,),
        operand_arity={DS_INPUT_IRI: 1},
        implementation=lambda **kw: {DS_OUTPUT_IRI: kw[DS_INPUT_IRI]},
    )
    # a plain scalar must pass (arity 1 does not require a list)
    _validate_inputs(cap, {DS_INPUT_IRI: "scalar"})


# ── registration guard (ADR-0198): arity keys must be declared inputs ─


def test_operand_arity_stray_key_rejected_at_registration():
    cl = build_min_layer()
    cap = Capacity(
        name="test.stray",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_INPUT_IRI,),
        outputs=(DS_OUTPUT_IRI,),
        operand_arity={"datastate:test.NOT_AN_INPUT": 2},
        implementation=lambda **kw: {DS_OUTPUT_IRI: None},
    )
    with pytest.raises(CapacityRegistrationError):
        cl.register_capacity(cap)
