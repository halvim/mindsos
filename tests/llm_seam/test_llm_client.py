"""The model client: what it decodes, what it raises, and what it never says.

**The load-bearing test here is**
:func:`test_a_provider_failure_never_reaches_the_customers_page`. The
archived seam built its outage message as ``f"the model call for
{prompt_iri!r} ... {type(exc).__name__}: {exc}"``. That string becomes
``stopped_detail`` on L-2's ``RunStopped`` node and the Decision Records
renderer prints it, so a provider's own error text — a URL, an
authorization message, whatever the vendor's library happened to write —
rendered on a customer's page. The critic reproduced it from its own
fixtures before this was fixed: a URL, a key-shaped string, an exception
class name and a prompt IRI, all four on the page (coordination §87 T-F1,
§88 re-run (a)).

The rule the fix follows is not new; ``policy_lookup_v0`` states it for the
store outage and pins it from the other side. What was new is that nobody
had applied it here, and that the RULE COVERS EVERY EXCEPTION IN THE
MODULE — ``runtime.invoke`` envelopes them all, so the budget message's
ceiling number and the replay miss's request-key hash reach the same node
by the same path.
"""

from __future__ import annotations

import pytest

from mindsos_capacity.builtins import origin_v0
from mindsos_capacity.llm import (
    LiveLLM,
    RecordedLLM,
    RecordingStore,
    decode_response,
)
from mindsos_capacity.llm.exceptions import (
    LLMCallBudgetExceeded,
    LLMCallFailed,
    LLMError,
    MalformedResponse,
    RecordedResponseMiss,
    TransportContractError,
    TransportSignatureError,
)

#: The critic's four markers, from the §88 re-run that reproduced the leak.
#: They are the fixture rather than an invention, so this guard tests the
#: thing that actually happened.
MARKERS = ("prompt:read_income", "https://", "sk-abc123", "ConnectError")

ANSWER = {"fields": [{"name": "days", "value": 7, "quote": "seven days"}]}


def _client(transport, **over):
    kwargs = dict(model_id="m", model_version="2026-01-01")
    kwargs.update(over)
    return LiveLLM(transport, **kwargs)


def _read(client):
    return client.read(prompt_iri="prompt:p", prompt_version=1, source_text="doc")


# ── S-2: who decodes, and what a failure to decode means ───────────────


def test_a_mapping_passes_through():
    assert decode_response({"a": 1}) == {"a": 1}


def test_text_is_decoded_inside_the_package():
    """S-2, ruled 2026-08-14: decoding is substrate work and must not sit
    in the deployment's unwritten, untested transport."""
    assert decode_response('{"a": 1}') == {"a": 1}


def test_text_that_will_not_decode_is_a_malformed_ANSWER():
    with pytest.raises(MalformedResponse) as exc:
        decode_response("here you go: about seven weeks")
    assert exc.value.raw == "here you go: about seven weeks", (
        "the raw words must survive - a refusal that cannot show what came "
        "back asks the reader to take our word for it"
    )


def test_text_decoding_to_something_that_is_not_an_object_is_also_malformed():
    with pytest.raises(MalformedResponse):
        decode_response("[1, 2, 3]")


def test_a_return_that_is_neither_is_a_DEPLOYMENT_bug_and_says_so():
    """Three failures, three meanings. Calling this ``model_unreachable``
    would blame the network for our code; calling it
    ``malformed_response`` would blame the model for our code. The
    archived seam collapsed it into the first."""
    with pytest.raises(TransportContractError) as exc:
        decode_response(7)
    assert "returned int" in exc.value.violation


# ── the leak, and the rule that closes it ──────────────────────────────


def test_a_provider_failure_never_reaches_the_customers_page():
    def _transport(**_):
        raise RuntimeError(
            "ConnectError: POST https://api.provider.example/v1/messages "
            "failed (key sk-abc123)"
        )

    with pytest.raises(LLMCallFailed) as exc:
        _read(_client(_transport))

    message = str(exc.value)
    for marker in MARKERS:
        assert marker not in message, (
            f"{marker!r} reached the customer-visible message; that string is "
            f"written onto RunStopped.stopped_detail and printed by a Record"
        )
    assert message == LLMCallFailed.MESSAGE
    assert isinstance(exc.value.__cause__, RuntimeError), (
        "the provider's own exception must survive for a traceback - the "
        "rule is about where it goes, not that it is discarded"
    )


@pytest.mark.parametrize("exc", [
    LLMCallFailed(),
    LLMCallBudgetExceeded(max_calls=200),
    RecordedResponseMiss(request_key="sha256:deadbeef", set_size=17),
    MalformedResponse(raw='{"days": 7'),
    TransportContractError(violation="returned int"),
])
def test_every_exception_here_says_only_what_we_wrote(exc):
    """The rule covers the whole module, not just the outage. Extended
    while building T1: ``runtime.invoke`` envelopes every exception, so a
    ceiling number and a request-key hash reach a customer's page by the
    same path a provider's stack trace would."""
    message = str(exc)
    assert message == type(exc).MESSAGE
    for leaked in ("200", "sha256:", "deadbeef", "17", "days", "int"):
        assert leaked not in message, f"{leaked!r} is operator detail, not prose"


def test_operator_detail_survives_on_attributes():
    """Fixed prose is not amnesia: everything the message no longer says is
    still reachable by whoever is debugging."""
    assert LLMCallBudgetExceeded(max_calls=200).max_calls == 200
    miss = RecordedResponseMiss(request_key="sha256:x", set_size=17)
    assert (miss.request_key, miss.set_size) == ("sha256:x", 17)
    assert MalformedResponse(raw="junk").raw == "junk"
    assert TransportContractError(violation="returned int").violation == "returned int"


def test_a_transport_that_will_not_ACCEPT_the_call_is_a_deployment_bug_too():
    """**Found by the contract harness on its first run** (2026-08-16).

    ``LiveLLM`` wrapped the call in a blanket ``except Exception``, so a
    transport declared with the wrong parameters raised ``TypeError`` at
    binding and came back as ``LLMCallFailed`` — ``model_unreachable``. A
    deployment that mis-wrote its function would have watched every member
    stop with "the reading service could not be reached" and gone looking
    at the network. The line had been drawn for what a transport RETURNS
    and not for how it is CALLED.
    """
    with pytest.raises(TransportSignatureError) as exc:
        _read(_client(lambda prompt_iri: ANSWER))
    assert "does not accept" in exc.value.violation
    assert not isinstance(exc.value, LLMCallFailed)


def test_a_TypeError_from_INSIDE_a_correct_transport_is_still_a_real_failure():
    """The other side of the split, and the reason binding is checked
    before the call rather than by catching ``TypeError`` around it: those
    two are the same exception at the same catch."""
    def _internally_broken(**_):
        return None + 1  # noqa: E711 — deliberate TypeError inside the body

    with pytest.raises(LLMCallFailed):
        _read(_client(_internally_broken))


def test_the_outage_token_agrees_with_the_origin_vocabulary():
    """The literal on ``LLMCallFailed`` is deliberate — this package does
    not import the origin vocabulary, so the two stay decoupled. This is
    the price of that: agreement is a test, and drift is a red gate."""
    assert LLMCallFailed.refusal_reason == origin_v0.REFUSAL_MODEL_UNREACHABLE
    assert MalformedResponse.refusal_reason == origin_v0.REFUSAL_MALFORMED_RESPONSE


# ── which failures a member may retry (ADR-0201 am-7) ──────────────────


def test_only_the_outage_is_transient():
    """The fatal-set exemption (critic §88 Q3). Retrying past a ceiling
    defeats the ceiling; retrying a replay miss cannot conjure a
    recording; retrying a contract violation returns the same wrong type.
    """
    assert LLMCallFailed.retryable is True
    assert LLMCallBudgetExceeded.retryable is False
    assert RecordedResponseMiss.retryable is False
    assert TransportContractError.retryable is False
    assert TransportSignatureError.retryable is False
    assert LLMError.retryable is False


# ── the ceiling, and identity the model cannot forge ───────────────────


def test_the_ceiling_is_enforced_BEFORE_the_transport_is_called():
    calls = []
    client = _client(lambda **k: calls.append(k) or ANSWER, max_calls=1)
    _read(client)
    with pytest.raises(LLMCallBudgetExceeded):
        _read(client)
    assert len(calls) == 1, "a refused call must not reach the provider"


def test_identity_is_stamped_above_the_transport_and_overrides_it():
    """A transport cannot misreport which model answered: the client
    stamps identity AFTER the call, over whatever came back."""
    lying = lambda **_: dict(ANSWER, model_id="something-else", recorded=True)
    payload = _read(_client(lying))
    assert payload["model_id"] == "m"
    assert payload["recorded"] is False


def test_a_replayed_reading_cannot_present_as_live():
    store = RecordingStore()
    live = _client(lambda **_: ANSWER)
    payload = _read(live)
    store.put(payload["request_key"], payload)
    replayed = RecordedLLM(
        store, model_id="m", model_version="2026-01-01"
    ).read(prompt_iri="prompt:p", prompt_version=1, source_text="doc")
    assert payload["recorded"] is False and replayed["recorded"] is True
    assert replayed["request_key"] == payload["request_key"]
