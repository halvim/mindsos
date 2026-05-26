"""Phase 31 — text.space_split end-to-end via CapacityLayer.invoke."""

from __future__ import annotations

from mindsos_capacity.builtins import DS_RAW_TEXT, DS_TOKENS

from ._fixtures import make_layer_with_text


def test_space_split_basic():
    layer = make_layer_with_text()
    result = layer.invoke(
        "capacity:perception:text.space_split",
        {DS_RAW_TEXT: "hello world foo"},
    )
    assert result.success is True
    assert result.outputs[DS_TOKENS] == ["hello", "world", "foo"]


def test_space_split_empty_string():
    layer = make_layer_with_text()
    result = layer.invoke(
        "capacity:perception:text.space_split",
        {DS_RAW_TEXT: ""},
    )
    assert result.success is True
    assert result.outputs[DS_TOKENS] == []


def test_space_split_collapses_multiple_spaces():
    layer = make_layer_with_text()
    result = layer.invoke(
        "capacity:perception:text.space_split",
        {DS_RAW_TEXT: "  a   b\tc\n"},
    )
    assert result.success is True
    assert result.outputs[DS_TOKENS] == ["a", "b", "c"]
