"""A client asks one question once.

``docs/plans/MINDSOS_LLM_PLAN.md`` item I-24, ruling R66. Readers may share a
prompt and schema, each taking its own field from the same answer; measured on
``e935cf8``, ``LiveLLM.read`` called the provider every time, so N readers of
one document made N paid calls under one ``request_key``. A client now keeps
the first outcome of each question — an answer, an undecodable answer, or a
reply cut at the ceiling — and returns it for a repeat. An outage is not kept.
The call ceiling counts provider calls, so a repeat costs nothing.
"""

from __future__ import annotations

import pytest

from mindsos_capacity.builtins.comprehension_v0 import build_reader
from mindsos_capacity.builtins.origin_v0 import BASIS_STATED, origin_record_iri
from mindsos_capacity.identifiers import datastate_iri
from mindsos_llm import CapturingLLM, LiveLLM, RecordingStore
from mindsos_llm.exceptions import (
    AnswerCutAtCeiling,
    LLMCallBudgetExceeded,
    LLMCallFailed,
    MalformedResponse,
)
from mindsos_llm.seam import ANSWER_CUT, TransportAnswerCut

DOCUMENT = "I bought it on 3 March and claimed seven days later."
SOURCE = datastate_iri("once.document")
ANSWER = {"fields": [
    {"name": "bought_on", "value": "3 March", "quote": "3 March", "basis": BASIS_STATED},
    {"name": "days", "value": "seven", "quote": "seven days", "basis": BASIS_STATED},
]}


class _Transport:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def __call__(self, **_):
        self.calls += 1
        outcome = self.outcomes[min(self.calls, len(self.outcomes)) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome() if callable(outcome) else outcome


def _client(transport, **over):
    kwargs = dict(model_id="m", model_version="v", credential_level=1,
                  resolve_prompt=lambda **_: "read the document",
                  tool_name="extract", tool_description="pull the fields out")
    kwargs.update(over)
    return LiveLLM(transport, **kwargs)


def _read(client, text=DOCUMENT):
    return client.read(prompt_iri="prompt:once", prompt_version=1, source_text=text)


def _reader(field):
    return build_reader(
        name=f"read_{field}_once", source_datastate_iri=SOURCE,
        value_datastate_iri=datastate_iri(f"once.{field}"),
        prompt_iri="prompt:once", prompt_version=1, field_name=field,
        question=f"the {field}", description=f"Read the {field}.",
        origin_party_phrase="the writer", source_identity_phrase="their document",
        expected_basis=BASIS_STATED,
    )


class _Ctx:
    def __init__(self, llm):
        self.llm = llm


def test_the_same_question_twice_reaches_the_provider_once():
    transport = _Transport(lambda: dict(ANSWER))
    client = _client(transport)
    first, second = _read(client), _read(client)
    assert transport.calls == 1
    assert client.calls_made == 1
    assert first == second


def test_a_different_question_is_asked():
    transport = _Transport(lambda: dict(ANSWER))
    client = _client(transport)
    _read(client)
    _read(client, text="another document")
    assert transport.calls == 2


def test_two_readers_sharing_a_prompt_cost_one_call_and_each_gets_its_field():
    transport = _Transport(lambda: dict(ANSWER))
    ctx = _Ctx(_client(transport))
    values = {}
    for field in ("bought_on", "days"):
        value_ds = datastate_iri(f"once.{field}")
        out = _reader(field).implementation(**{SOURCE: DOCUMENT, "context": ctx})
        assert out[origin_record_iri(value_ds)]["refusal_reason"] is None
        values[field] = out[value_ds]
    assert transport.calls == 1
    assert values == {"bought_on": "3 March", "days": "seven"}


def test_an_undecodable_answer_is_kept_and_not_asked_again():
    transport = _Transport("not json at all")
    client = _client(transport)
    for _ in range(2):
        with pytest.raises(MalformedResponse) as exc:
            _read(client)
        assert exc.value.raw == "not json at all"
        assert exc.value.asked["request_key"]
    assert transport.calls == 1


def test_a_cut_reply_is_kept_and_not_asked_again():
    transport = _Transport(TransportAnswerCut(ANSWER_CUT))
    client = _client(transport)
    for _ in range(2):
        with pytest.raises(AnswerCutAtCeiling):
            _read(client)
    assert transport.calls == 1


def test_an_outage_is_not_kept_and_is_asked_again():
    transport = _Transport(RuntimeError("down"), lambda: dict(ANSWER))
    client = _client(transport)
    with pytest.raises(LLMCallFailed):
        _read(client)
    assert _read(client)["fields"] == ANSWER["fields"]
    assert transport.calls == 2


def test_a_repeat_does_not_count_toward_the_ceiling():
    transport = _Transport(lambda: dict(ANSWER))
    client = _client(transport, max_calls=1)
    _read(client)
    _read(client)
    with pytest.raises(LLMCallBudgetExceeded):
        _read(client, text="another document")
    assert transport.calls == 1


def test_a_returned_answer_is_a_copy():
    client = _client(_Transport(lambda: dict(ANSWER)))
    first = _read(client)
    first["fields"].clear()
    assert _read(client)["fields"] == ANSWER["fields"]


def test_a_capture_of_two_readers_sharing_a_prompt_records_one_answer():
    store = RecordingStore()
    transport = _Transport(lambda: dict(ANSWER))
    ctx = _Ctx(CapturingLLM(_client(transport), store))
    for field in ("bought_on", "days"):
        _reader(field).implementation(**{SOURCE: DOCUMENT, "context": ctx})
    assert transport.calls == 1
    assert len(store) == 1
