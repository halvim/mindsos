"""A recording never replaces an answer it already holds.

``docs/plans/MINDSOS_LLM_PLAN.md`` item I-23, ruling R65. Measured on
``e935cf8``: ``RecordingStore.put`` assigned with no check, so a second,
different answer under one ``request_key`` silently replaced the first, and a
conclusion minted from the first then replayed to the second. A different
answer under a held key now refuses; the same answer again changes nothing.
"""

from __future__ import annotations

import pytest

from mindsos_llm import CapturingLLM, LiveLLM, RecordingStore
from mindsos_llm.exceptions import RecordedAnswerConflict

FIRST = {"fields": [{"name": "days", "value": 7, "quote": "seven days"}]}
SECOND = {"fields": [{"name": "days", "value": 8, "quote": "seven days"}]}


def _capture(store, answer):
    live = LiveLLM(
        lambda **_: dict(answer), model_id="m", model_version="v", credential_level=1,
        resolve_prompt=lambda **_: "read the document",
        tool_name="extract", tool_description="pull the fields out",
    )
    return CapturingLLM(live, store).read(
        prompt_iri="prompt:p", prompt_version=1, source_text="seven days")


def test_a_different_answer_under_a_held_key_refuses_and_the_first_stays():
    store = RecordingStore()
    store.put("sha256:k", FIRST)
    with pytest.raises(RecordedAnswerConflict) as exc:
        store.put("sha256:k", SECOND)
    assert exc.value.request_key == "sha256:k"
    assert dict(store.get("sha256:k")) == FIRST


def test_the_same_answer_again_changes_nothing():
    store = RecordingStore()
    store.put("sha256:k", FIRST)
    store.put("sha256:k", dict(FIRST))
    assert len(store) == 1
    assert dict(store.get("sha256:k")) == FIRST


def test_a_capture_that_would_replace_an_answer_refuses_and_keeps_the_first():
    store = RecordingStore()
    first = _capture(store, FIRST)
    with pytest.raises(RecordedAnswerConflict):
        _capture(store, SECOND)
    assert len(store) == 1
    assert dict(store.get(first["request_key"]))["fields"] == FIRST["fields"]


def test_the_refusal_is_fixed_prose_and_not_retried():
    exc = RecordedAnswerConflict(request_key="sha256:deadbeef")
    assert str(exc) == RecordedAnswerConflict.MESSAGE
    assert "sha256" not in str(exc)
    assert RecordedAnswerConflict.retryable is False
