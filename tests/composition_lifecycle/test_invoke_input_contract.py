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
    cl.invoke(echo.iri, inputs={}, request_id="t1")
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


# ── CORE-C3R1 signature sweep — the `kind` set is closed and documented ──
#
# `exceptions.py` documented two `kind` values where `_validate_inputs` raises
# three; the omitted one, ``operand_arity``, is precisely the one the shared
# step-admission predicate makes load-bearing, and an L4 consumer branches on
# `kind` to decide whether the finder wired it wrong. A docstring cannot be
# gated, so gate the set instead: the raisers, the docstring and this test move
# together or the gate goes red.

KIND_VALUES = frozenset({"missing_required", "unexpected_input", "operand_arity"})


def test_input_contract_error_is_exported_from_the_package():
    """arc1 and SubMind import it from the package, not from `.exceptions`."""
    import mindsos_capacity

    assert mindsos_capacity.InputContractError is InputContractError
    assert "InputContractError" in mindsos_capacity.__all__


def test_kind_set_matches_what_validate_inputs_actually_raises():
    """AST over the raiser — a different method than reading the docstring."""
    import ast
    import inspect

    from mindsos_capacity import capacity as capacity_mod

    tree = ast.parse(inspect.getsource(capacity_mod))
    raised = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id != "InputContractError":
            continue
        for kw in node.keywords:
            if kw.arg == "kind" and isinstance(kw.value, ast.Constant):
                raised.add(kw.value.value)
    assert raised == set(KIND_VALUES), (
        f"`kind` values raised by capacity.py are {sorted(raised)}; this test "
        f"and InputContractError's docstring say {sorted(KIND_VALUES)}. "
        "Adding or removing a kind is an L4-visible contract change."
    )


def test_kind_set_is_documented_in_the_exception_docstring():
    doc = InputContractError.__doc__ or ""
    missing = sorted(k for k in KIND_VALUES if f'"{k}"' not in doc)
    assert not missing, (
        f"InputContractError's docstring omits {missing}. It is the closed set "
        "an L4 consumer branches on; the two-value version shipped at ae63aa2."
    )
