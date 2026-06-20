"""Phase 51 — ADR-0175 §amendment-3 sentinels (L3-59(b) closure).

Pins: (1) the read path builds a typed ``CapacityContext``; (2) the
public ``context`` kwarg is gone from ``CapacityLayer.invoke``; (3) the
transitional dict-or-CapacityContext union is retired from the
invocation chain; (4) scoped grep-zero — no dict-form context access
anywhere in ``mindsos_capacity/**`` (the phase-map §2 WSD-1 pass
criterion; Phase 41 retirement-sentinel precedent: scoped to the
shipped package, source-level).
"""

from __future__ import annotations

import inspect
import pathlib
import re

import pytest

import mindsos_capacity
from mindsos_capacity import (
    CATEGORY_PERCEPTION,
    Capacity,
    CapacityLayer,
    DataState,
    ShapeDescriptor,
)
from mindsos_capacity.context import CapacityContext
from mindsos_capacity.identifiers import datastate_iri

DS_IN = datastate_iri("p51.in")
DS_OUT = datastate_iri("p51.out")


def _layer_with_probe():
    captured = {}

    def _impl(**kw):
        captured["context"] = kw.get("context")
        return {DS_OUT: "ok"}

    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    cl.register_datastate(
        DataState(name="p51.in", shape=ShapeDescriptor.scalar("str", opaque_tag="p51.in")),
        allow_new_realm=True,
    )
    cl.register_datastate(
        DataState(name="p51.out", shape=ShapeDescriptor.scalar("str", opaque_tag="p51.out")),
        allow_new_realm=True,
    )
    cl.register_capacity(
        Capacity(
            name="p51.probe",
            category=CATEGORY_PERCEPTION,
            inputs=(DS_IN,),
            outputs=(DS_OUT,),
            implementation=_impl,
        )
    )
    return cl, captured


def test_read_body_receives_typed_capacity_context():
    cl, captured = _layer_with_probe()
    result = cl.invoke("capacity:perception:p51.probe", {DS_IN: "x"})
    assert result.success, result.error
    ctx = captured["context"]
    assert isinstance(ctx, CapacityContext)
    assert ctx.writeable is None  # read body: no write capability
    assert dict(ctx.learned_parameters_snapshot) == {}  # §am-3 clause 5
    assert ctx.cl is cl


def test_invoke_context_kwarg_removed():
    """§am-3 clause 2: the caller-supplied context mapping is gone."""
    params = inspect.signature(CapacityLayer.invoke).parameters
    assert "context" not in params


def test_runtime_chain_annotations_union_retired():
    """§am-3 clause 4: no transitional Union on the invocation chain."""
    from mindsos_capacity import capacity as capacity_mod
    from mindsos_capacity import runtime as runtime_mod

    for fn in (runtime_mod.invoke, capacity_mod.call_capacity):
        ann = inspect.signature(fn).parameters["context"].annotation
        assert "Union" not in str(ann) and "Mapping" not in str(ann), (
            f"{fn.__qualname__}: transitional context annotation survives: {ann!r}"
        )
        assert "CapacityContext" in str(ann)


_DICT_CONTEXT = re.compile(r"context\[\"|context\['|context\.get\(")


def test_no_dict_form_context_access_in_package():
    """Scoped grep-zero over mindsos_capacity/** source (incl. docstrings
    and comments — documentation must not teach the retired form)."""
    pkg_root = pathlib.Path(mindsos_capacity.__file__).parent
    offenders = []
    for py in sorted(pkg_root.rglob("*.py")):
        for lineno, line in enumerate(py.read_text().splitlines(), 1):
            if _DICT_CONTEXT.search(line):
                offenders.append(f"{py.relative_to(pkg_root)}:{lineno}: {line.strip()}")
    assert not offenders, "dict-form context access in mindsos_capacity/**:\n" + "\n".join(offenders)


def test_frozen_context_rejects_mutation():
    cl, captured = _layer_with_probe()
    cl.invoke("capacity:perception:p51.probe", {DS_IN: "x"})
    with pytest.raises(Exception):
        captured["context"].user_id = "mallory"
