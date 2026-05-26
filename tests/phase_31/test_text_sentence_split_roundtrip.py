"""Phase 31 — text.sentence_split end-to-end via CapacityLayer.invoke."""

from __future__ import annotations

from mindsos_capacity.builtins import DS_RAW_TEXT, DS_SENTENCES

from ._fixtures import make_layer_with_text


def test_sentence_split_basic():
    layer = make_layer_with_text()
    result = layer.invoke(
        "capacity:perception:text.sentence_split",
        {DS_RAW_TEXT: "First sentence. Second sentence! Third?"},
    )
    assert result.success is True
    # Last sentence has no trailing whitespace boundary so it's part
    # of the last split chunk.
    assert result.outputs[DS_SENTENCES] == [
        "First sentence.",
        "Second sentence!",
        "Third?",
    ]


def test_sentence_split_empty_string():
    layer = make_layer_with_text()
    result = layer.invoke(
        "capacity:perception:text.sentence_split",
        {DS_RAW_TEXT: ""},
    )
    assert result.success is True
    assert result.outputs[DS_SENTENCES] == []


def test_sentence_split_single_sentence_no_terminator():
    layer = make_layer_with_text()
    result = layer.invoke(
        "capacity:perception:text.sentence_split",
        {DS_RAW_TEXT: "no terminator here"},
    )
    assert result.success is True
    assert result.outputs[DS_SENTENCES] == ["no terminator here"]
