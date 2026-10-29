"""A reply the provider cut at the token ceiling is never an answer.

``docs/plans/MINDSOS_LLM_PLAN.md`` item I-22, ruling R64. Measured on
``e935cf8``: no adapter read the provider's stop reason, so a reply cut at
``max_tokens`` that still decoded was taken as complete. The ceiling is our
configuration, so a cut is OUR stop — never a refusal on the case — and it is
not retried: a second attempt at the same ceiling is the same cut, paid twice.
It carries no refusal token, as the call ceiling carries none.
"""

from __future__ import annotations

import io
import json
import urllib.request
from types import SimpleNamespace

import pytest

from mindsos_capacity.builtins.comprehension_v0 import build_reader
from mindsos_capacity.builtins.origin_v0 import BASIS_STATED
from mindsos_capacity.identifiers import datastate_iri
from mindsos_intelligence.execution import _failure_is_retryable
from mindsos_llm import adapters
from mindsos_llm.adapters import anthropic
from mindsos_llm.broker import BROKER_PROTOCOL_VERSION, HEADER_PROTOCOL
from mindsos_llm.contract import UNVERIFIABLE_PROPERTIES
from mindsos_llm.credentials import static_resolver
from mindsos_llm.exceptions import AnswerCutAtCeiling, LLMCallFailed
from mindsos_llm.live import LiveLLM
from mindsos_llm.seam import ANSWER_CUT, TransportAnswerCut

SCHEMA = {"type": "object", "properties": {"fields": {"type": "array"}}}
ANSWER = {"fields": [{"name": "days", "value": 7, "quote": "seven days"}]}
CUT = "max_tokens"


def _envelope(stop_reason):
    return {
        "content": [{"type": "tool_use", "name": "extract", "input": dict(ANSWER)}],
        "stop_reason": stop_reason,
    }


class _Response:
    def __init__(self, payload, headers=None):
        self._payload = payload
        self.status = 200
        self.headers = dict(headers or {})

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def _call(transport):
    return transport(
        prompt_text="read the document",
        source_text="the document says seven days",
        extraction_schema=SCHEMA,
        tool_name="extract",
        tool_description="pull the fields out",
        model_id="a-model",
        temperature=0.0,
        max_tokens=16,
        timeout_s=5.0,
    )


def _credentialled(stop_reason):
    return anthropic.build_transport(
        resolve_credential=static_resolver(lambda: "sk-test"),
        opener=lambda request, timeout=None: _Response(_envelope(stop_reason)),
    )


def _brokered(stop_reason):
    headers = {HEADER_PROTOCOL: str(BROKER_PROTOCOL_VERSION)}
    return anthropic.build_brokered_transport(
        broker_url="http://127.0.0.1:9",
        opener=lambda request, timeout=None: _Response(_envelope(stop_reason), headers),
    )


def _client(transport):
    return LiveLLM(
        transport, model_id="m", model_version="v", credential_level=1,
        resolve_prompt=lambda **_: "read the document",
        tool_name="extract", tool_description="pull the fields out",
    )


def test_the_adapter_refuses_a_reply_cut_at_the_ceiling():
    with pytest.raises(TransportAnswerCut) as exc:
        _call(_credentialled(CUT))
    assert str(exc.value) == ANSWER_CUT


def test_a_complete_reply_still_passes():
    assert dict(_call(_credentialled("tool_use"))) == ANSWER


def test_the_brokered_path_refuses_it_too():
    with pytest.raises(TransportAnswerCut):
        _call(_brokered(CUT))


def test_the_shipped_adapter_refuses_it_on_the_DEFAULT_opener(monkeypatch):
    seen = []

    class _Body(io.BytesIO):
        status = 200

    def urlopen(request, timeout=None):
        seen.append(request)
        return _Body(json.dumps(_envelope(CUT)).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    transport = adapters.build_transport(
        anthropic.VENDOR_ID, resolve_credential=static_resolver(lambda: "sk-test"))
    with pytest.raises(TransportAnswerCut):
        _call(transport)
    assert seen, "the default opener was never reached"


def test_the_client_raises_its_own_class_and_not_an_outage():
    def transport(**_):
        raise TransportAnswerCut(ANSWER_CUT)

    with pytest.raises(AnswerCutAtCeiling) as exc:
        _client(transport).read(prompt_iri="prompt:p", prompt_version=1, source_text="doc")
    assert not isinstance(exc.value, LLMCallFailed)
    assert str(exc.value) == AnswerCutAtCeiling.MESSAGE
    assert isinstance(exc.value.__cause__, TransportAnswerCut)


def test_it_is_not_retried_and_carries_no_refusal_token():
    assert AnswerCutAtCeiling.retryable is False
    assert getattr(AnswerCutAtCeiling, "refusal_reason", None) is None
    result = SimpleNamespace(error=AnswerCutAtCeiling(), failed_step="capacity:x")
    assert _failure_is_retryable(None, result) is False


def test_a_reader_stops_on_it_and_writes_no_refusal():
    source = datastate_iri("cut.document")

    class _Ctx:
        llm = _client(lambda **_: (_ for _ in ()).throw(TransportAnswerCut(ANSWER_CUT)))

    reader = build_reader(
        name="read_days_cut", source_datastate_iri=source,
        value_datastate_iri=datastate_iri("cut.days"),
        prompt_iri="prompt:cut", prompt_version=1, field_name="days",
        question="how many days", description="Read the days.",
        origin_party_phrase="the writer", source_identity_phrase="their document",
        expected_basis=BASIS_STATED,
    )
    with pytest.raises(AnswerCutAtCeiling):
        reader.implementation(**{source: "seven days", "context": _Ctx()})


def test_the_contract_names_it_unverifiable_for_a_transport_core_did_not_write():
    assert "refuses_an_answer_cut_at_the_ceiling" in {n for n, _ in UNVERIFIABLE_PROPERTIES}
