"""Composition-lifecycle Slice 2 Part 6 — invoke INPUT contract.

`call_capacity` / `runtime.invoke` validate inputs against the declared
``CONSUMES`` set, respecting ``input_group`` (ADR-0072 §amendment-2):
``all_required`` ⇒ all present, ``any_of`` ⇒ ≥1, ``fold`` ⇒ not enforced
at v1 (Part 5). Non-fold groups also reject undeclared keys. Violations
raise :class:`InputContractError`; the ``invoke`` path envelopes it
(``success=False``) and tags ``error_kind="input_contract:<kind>"``.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from mindsos_capacity import CATEGORY_PERCEPTION, Capacity
from mindsos_capacity.capacity import call_capacity
from mindsos_capacity.exceptions import InputContractError
from mindsos_capacity.identifiers import INPUT_GROUP_ANY_OF, INPUT_GROUP_FOLD
from mindsos_capacity.runtime import invoke as runtime_invoke

from tests.phase_30._fixtures import (
    DS_INPUT_IRI,
    DS_MID_IRI,
    DS_OUTPUT_IRI,
    build_echo_capacity,
    build_min_layer,
)


DS_EXTRA_IRI = "datastate:test.extra"


def _any_of_capacity() -> Capacity:
    return Capacity(
        name="test.anyof",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_INPUT_IRI, DS_MID_IRI),
        outputs=(DS_OUTPUT_IRI,),
        input_group=INPUT_GROUP_ANY_OF,
        implementation=lambda **kw: {
            DS_OUTPUT_IRI: kw.get(DS_INPUT_IRI) or kw.get(DS_MID_IRI)
        },
    )


def _fold_capacity() -> Capacity:
    return Capacity(
        name="test.fold",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_INPUT_IRI,),
        outputs=(DS_OUTPUT_IRI,),
        input_group=INPUT_GROUP_FOLD,
        implementation=lambda **kw: {DS_OUTPUT_IRI: kw.get(DS_INPUT_IRI)},
    )


def _write_capacity() -> Capacity:
    return Capacity(
        name="test.write",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_INPUT_IRI,),
        outputs=(),
        implementation=lambda **kw: None,
    )


# ── all_required ──────────────────────────────────────────────────────


def test_all_required_present_succeeds():
    cl = build_min_layer()
    echo = build_echo_capacity()
    cl.register_capacity(echo)
    result = cl.invoke(echo.iri, inputs={DS_INPUT_IRI: "hi"})
    assert result.success is True
    assert result.outputs == {DS_OUTPUT_IRI: "hi"}


def test_all_required_missing_envelopes_input_contract():
    cl = build_min_layer()
    echo = build_echo_capacity()
    cl.register_capacity(echo)
    result = cl.invoke(echo.iri, inputs={})
    assert result.success is False
    assert isinstance(result.error, InputContractError)
    assert result.error.kind == "missing_required"


def test_unexpected_key_envelopes_input_contract():
    cl = build_min_layer()
    echo = build_echo_capacity()
    cl.register_capacity(echo)
    result = cl.invoke(echo.iri, inputs={DS_INPUT_IRI: "hi", DS_EXTRA_IRI: "x"})
    assert result.success is False
    assert isinstance(result.error, InputContractError)
    assert result.error.kind == "unexpected_input"


def test_error_kind_tagged_in_problem_trace():
    cl = build_min_layer()
    echo = build_echo_capacity()
    cl.register_capacity(echo)
    cl.invoke(echo.iri, inputs={}, task_id="t1")
    records = cl.problem_trace.records()
    assert len(records) == 1
    assert records[0].error_kind == "input_contract:missing_required"


# ── any_of ────────────────────────────────────────────────────────────


def test_any_of_one_present_succeeds():
    cl = build_min_layer()
    cap = _any_of_capacity()
    cl.register_capacity(cap)
    result = cl.invoke(cap.iri, inputs={DS_INPUT_IRI: "hi"})
    assert result.success is True


def test_any_of_none_present_fails():
    cl = build_min_layer()
    cap = _any_of_capacity()
    cl.register_capacity(cap)
    result = cl.invoke(cap.iri, inputs={})
    assert result.success is False
    assert isinstance(result.error, InputContractError)
    assert result.error.kind == "missing_required"


# ── fold (not enforced at v1; Part 5) ─────────────────────────────────


def test_fold_inputs_not_enforced():
    cl = build_min_layer()
    cap = _fold_capacity()
    cl.register_capacity(cap)
    result = cl.invoke(cap.iri, inputs={})
    assert result.success is True
    assert result.outputs == {DS_OUTPUT_IRI: None}


def test_fold_unexpected_key_not_rejected():
    cl = build_min_layer()
    cap = _fold_capacity()
    cl.register_capacity(cap)
    result = cl.invoke(cap.iri, inputs={DS_EXTRA_IRI: "x"})
    assert result.success is True


# ── direct call_capacity raises (no envelope) ─────────────────────────


def test_direct_call_capacity_raises():
    echo = build_echo_capacity()
    try:
        call_capacity(echo, inputs={})
    except InputContractError as exc:
        assert exc.kind == "missing_required"
    else:
        raise AssertionError("expected InputContractError")


# ── write-bypass path validates too ───────────────────────────────────


def test_write_bypass_validates_inputs():
    decl = _write_capacity()
    result = runtime_invoke(decl, inputs={})
    assert result.success is False
    assert isinstance(result.error, InputContractError)
    assert result.error.kind == "missing_required"


# ── CLI invoke surfaces the contract error (live consumer) ────────────


def test_cli_invoke_wrong_input_iri_surfaces_input_contract():
    from mindsos_cli.app import app

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "capacity",
            "invoke",
            "capacity:perception:text.space_split",
            "--input-json",
            '{"datastate:text.WRONG": "hello"}',
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.output)
    assert parsed["success"] is False
    assert parsed["error"]["type"] == "InputContractError"
