"""ADR-0200 (C3) — reads_mm gates the body-facing MM read handle.

``L4Dispatcher.build_context`` injects ``mm_handle`` only when the
declaration sets ``reads_mm=True``; a ``reads_mm=False`` body (the default)
receives ``mm_handle=None``. Enforced on the dispatch path (the single
context-construction site every L4 invocation funnels through). ``kl`` and
``writeable`` are untouched.
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer, CATEGORY_PERCEPTION
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.identifiers import capacity_iri

from mindsos_intelligence.dispatch import L4Dispatcher


class _FakeSession:
    session_id = "s-1"
    user_id = "u-1"
    actor_role = "user"
    capabilities: set = set()

    def has(self, capability: str) -> bool:
        return False


_SENTINEL_MM = object()

DS_IN = "datastate:test.in"
DS_OUT = "datastate:test.out"


def _mm_probe_body(**kwargs):
    ctx = kwargs["context"]
    # Report whether the body actually received an MM handle.
    return {DS_OUT: ctx.mm_handle is _SENTINEL_MM}


def _layer_with(reads_mm: bool, name: str):
    layer = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    from mindsos_capacity import DataState, ShapeDescriptor

    layer.register_datastate(
        DataState(name="test.in", shape=ShapeDescriptor.scalar("str")),
        allow_new_realm=True,
    )
    layer.register_datastate(
        DataState(name="test.out", shape=ShapeDescriptor.scalar("bool")),
        allow_new_realm=True,
    )
    layer.register_capacity(
        Capacity(
            name=name,
            category=CATEGORY_PERCEPTION,
            inputs=(DS_IN,),
            outputs=(DS_OUT,),
            reads_mm=reads_mm,
            implementation=_mm_probe_body,
        )
    )
    return layer, capacity_iri(CATEGORY_PERCEPTION, name)


# ── build_context gating ──────────────────────────────────────────────


def test_build_context_default_withholds_mm_handle():
    layer, _ = _layer_with(False, "probe_default")
    dispatcher = L4Dispatcher(layer, session=_FakeSession(), mm_handle=_SENTINEL_MM)
    ctx = dispatcher.build_context()
    assert ctx.mm_handle is None


def test_build_context_reads_mm_true_injects_handle():
    layer, _ = _layer_with(True, "probe_true_ctx")
    dispatcher = L4Dispatcher(layer, session=_FakeSession(), mm_handle=_SENTINEL_MM)
    ctx = dispatcher.build_context(reads_mm=True)
    assert ctx.mm_handle is _SENTINEL_MM


# ── dispatch threads the declaration's reads_mm to the body ───────────


def test_dispatch_withholds_mm_from_reads_mm_false_body():
    layer, iri = _layer_with(False, "probe_false")
    dispatcher = L4Dispatcher(layer, session=_FakeSession(), mm_handle=_SENTINEL_MM)
    result = dispatcher.dispatch(iri, {DS_IN: "x"})
    assert result.success
    assert result.outputs[DS_OUT] is False  # body saw mm_handle=None


def test_dispatch_gives_mm_to_reads_mm_true_body():
    layer, iri = _layer_with(True, "probe_true")
    dispatcher = L4Dispatcher(layer, session=_FakeSession(), mm_handle=_SENTINEL_MM)
    result = dispatcher.dispatch(iri, {DS_IN: "x"})
    assert result.success
    assert result.outputs[DS_OUT] is True  # body saw the sentinel handle


# ── L3/CLI invoke path structurally carries no MM (ADR-0200) ──────────


def test_capacity_layer_write_path_has_no_mm_handle():
    """The capacity_layer.invoke write path builds a context with no
    mm_handle (L3 has no MM), so it is trivially compliant regardless of
    reads_mm — the gate only has to live on the L4 dispatch path."""
    seen = {}

    def _write_probe(**kwargs):
        seen["mm"] = kwargs["context"].mm_handle
        return None

    layer = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    from mindsos_capacity import DataState, ShapeDescriptor

    layer.register_datastate(
        DataState(name="test.win", shape=ShapeDescriptor.scalar("str")),
        allow_new_realm=True,
    )
    layer.register_capacity(
        Capacity(
            name="write_probe",
            category=CATEGORY_PERCEPTION,
            inputs=("datastate:test.win",),
            outputs=(),  # write-body → CapacityContext path
            reads_mm=True,  # even when declared, L3 path has no MM to give
            implementation=_write_probe,
        )
    )
    layer.invoke(
        capacity_iri(CATEGORY_PERCEPTION, "write_probe"),
        {"datastate:test.win": "x"},
    )
    assert seen["mm"] is None
