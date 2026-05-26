"""Phase 31 — DataState IRI literals are stable (downstream phases depend on them)."""

from __future__ import annotations

from mindsos_capacity.builtins import (
    DS_RAW_TEXT,
    DS_SENTENCES,
    DS_TOKENS,
)


def test_ds_raw_text_literal():
    assert DS_RAW_TEXT == "datastate:text.raw"


def test_ds_tokens_literal():
    assert DS_TOKENS == "datastate:text.tokens"


def test_ds_sentences_literal():
    assert DS_SENTENCES == "datastate:text.sentences"
