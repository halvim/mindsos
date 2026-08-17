"""Step 1's guards — seven narrow claims about the piece that touches the network.

⚠ **What these guards DO NOT prove, said first (RULES §11).** They do not prove
this transport satisfies the ``Transport`` contract.
``mindsos_capacity.llm.contract.verify_transport`` is the harness written for
exactly that, and `mindsos_capacity/llm/` is ABSENT from the core this branch
pins — so the conformance check is run by the OWNER from the ``main`` checkout
and reported as evidence, never as a green guard here (plan §0.5 item 9). They
also do not prove anything about a live provider: every guard below runs
against an injected fake opener, because the build gate has neither network nor
key.

**Both doors of the one branching predicate are fixtured at birth** (RULES §12):
``test_a_successful_call_returns_the_models_text_undecoded`` is the 2xx door and
``test_a_non_2xx_raises_and_returns_nothing`` is the other. A transport guarded
only on success returns a provider's error page to a reader as an answer.

Plain python or pytest; no FalkorDB, no network.
"""

from __future__ import annotations

import inspect
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decision_records_demo.dr_transport import (  # noqa: E402
    ENDPOINT,
    UNREACHABLE,
    TransportCallFailed,
    build_transport,
)

KEY = "sk-ant-TESTKEY-do-not-ship-0000"
MODEL = "claude-haiku-4-5-20251001"
PROMPT_SENTINEL = "RESOLVER-SUPPLIED PROMPT, and nothing else may produce these words"
ANSWER = '{"fields": [{"name": "off_work_period", "value": "at least six weeks"}]}'


def _resolver(*, prompt_iri, prompt_version):
    return PROMPT_SENTINEL


class _Response:
    def __init__(self, payload, status=200):
        self.status = status
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body


class _Opener:
    """Records what it was called with. No network anywhere in this file."""

    def __init__(self, payload=None, status=200, raises=None):
        self.payload = payload if payload is not None else {
            "content": [{"type": "text", "text": ANSWER}]
        }
        self.status = status
        self.raises = raises
        self.calls = []

    def __call__(self, request, **kwargs):
        self.calls.append((request, kwargs))
        if self.raises is not None:
            raise self.raises
        return _Response(self.payload, status=self.status)


def _call(transport, **over):
    kwargs = dict(
        prompt_iri="prompt:drdemo/read_exposure",
        prompt_version=1,
        source_text="The operator was off work for at least six weeks.",
        extraction_schema={"off_work_period": "str"},
        timeout_s=12.5,
    )
    kwargs.update(over)
    return transport(**kwargs)


def _chain(exc):
    seen = []
    while exc is not None and exc not in seen:
        seen.append(exc)
        exc = exc.__cause__ or exc.__context__
    return seen


# ── 1 ──────────────────────────────────────────────────────────────────

def test_the_callable_binds_the_call_LiveLLM_makes_and_requires_all_five():
    """``LiveLLM.read`` builds one dict and binds it before calling (`live.py`'s
    ``_assert_binds``). The five keys are copied here VERBATIM from that call
    site.

    **Two halves, and the second is the one with teeth.** Binding the full call
    proves the names line up. Binding a call with any ONE key removed must
    FAIL — otherwise a parameter has a default, and a caller that forgets to
    pass the document reads an empty string and the model answers about
    nothing. A guard that only checked the happy call would pass on exactly
    that transport."""
    transport = build_transport(api_key=KEY, model_id=MODEL, resolve_prompt=_resolver)
    signature = inspect.signature(transport)
    call = dict(
        prompt_iri="prompt:x",
        prompt_version=1,
        source_text="text",
        extraction_schema=None,
        timeout_s=30.0,
    )
    signature.bind(**call)
    for dropped in sorted(call):
        partial = {k: v for k, v in call.items() if k != dropped}
        try:
            signature.bind(**partial)
        except TypeError:
            continue
        raise AssertionError(
            f"the transport binds a call with {dropped!r} missing — that "
            "parameter carries a default, and a caller that omits it gets "
            "silence instead of an error"
        )


# ── 2 ── the 2xx door ──────────────────────────────────────────────────

def test_a_successful_call_returns_the_models_text_undecoded():
    """S-2: the ENVELOPE is unwrapped here, the ANSWER is not decoded here.
    The fixture's answer is itself valid JSON precisely so that a transport
    which decoded it would return a mapping and be caught."""
    opener = _Opener()
    transport = build_transport(
        api_key=KEY, model_id=MODEL, resolve_prompt=_resolver, opener=opener
    )
    out = _call(transport)
    assert isinstance(out, str), (
        f"the transport returned {type(out).__name__}; decoding the model's "
        "answer belongs to mindsos_capacity.llm, where the failure is typed"
    )
    assert out == ANSWER, out


# ── 3 ── the other door ────────────────────────────────────────────────

def test_a_non_2xx_raises_as_an_OUTAGE_and_returns_nothing():
    """A provider error body is not an answer. Returning it would hand a reader
    a vendor's error page to quote-verify against a claim email.

    ⚠ **Two things in this guard are deliberately adversarial, and the first
    version of it had neither — it PASSED ITS OWN MUTATION and the harness
    caught it.**

    * **The 529 fixture carries a well-formed `content` block.** A realistic
      error body has none, so with the status check deleted the transport still
      raised — through the ENVELOPE door — and the guard was green while
      proving nothing about the status. The fixture is shaped to isolate the
      one predicate this guard is about.
    * **The message is asserted, not just the exception type.** A non-2xx is
      OUR OUTAGE (``UNREACHABLE``); a reply with no answer inside it is a
      different failure (``NO_ANSWER``). ``live.py`` classifies three failure
      kinds on purpose and collapsing them is how a page ends up blaming a
      customer's document for our configuration."""
    opener = _Opener(
        payload={"content": [{"type": "text", "text": "overloaded, try later"}]},
        status=529,
    )
    transport = build_transport(
        api_key=KEY, model_id=MODEL, resolve_prompt=_resolver, opener=opener
    )
    try:
        out = _call(transport)
    except TransportCallFailed as exc:
        assert str(exc) == UNREACHABLE, (
            f"a 529 raised {str(exc)!r} — a non-2xx is our outage, not a "
            "reply we could not find an answer in"
        )
        return
    raise AssertionError(f"a 529 returned {out!r} instead of raising")


# ── 4 ── the credential ────────────────────────────────────────────────

def test_the_api_key_reaches_no_return_value_and_no_exception_in_the_chain():
    """The hard half. Walks the WHOLE ``__cause__``/``__context__`` chain,
    because a credential one traceback away is a credential that leaks."""
    ok = _Opener()
    transport = build_transport(
        api_key=KEY, model_id=MODEL, resolve_prompt=_resolver, opener=ok
    )
    assert KEY not in _call(transport)

    boom = _Opener(raises=RuntimeError("connection reset by peer"))
    transport = build_transport(
        api_key=KEY, model_id=MODEL, resolve_prompt=_resolver, opener=boom
    )
    try:
        _call(transport)
    except TransportCallFailed as exc:
        for link in _chain(exc):
            assert KEY not in str(link), (
                f"the credential appears on {type(link).__name__} in the "
                "exception chain"
            )
        return
    raise AssertionError("the failing opener did not raise")


# ── 5 ── the identifiers ───────────────────────────────────────────────

def test_the_model_id_and_endpoint_reach_no_exception_this_module_raises():
    """⚠ **This guard does NOT follow the cause chain, and that is deliberate.**
    ``LiveLLM`` attaches the provider exception with ``from exc`` by design, and
    `urllib`'s ``HTTPError`` names the URL it failed on — suppressing it would
    destroy the only debugging surface there is. Plan §0.5 item 8 is about a
    RENDERED PAGE; a traceback is not one. What this pins is the sentence THIS
    module composes, which is the sentence that can reach a page through
    ``LLMCallFailed``."""
    boom = _Opener(raises=RuntimeError("connection reset by peer"))
    transport = build_transport(
        api_key=KEY, model_id=MODEL, resolve_prompt=_resolver, opener=boom
    )
    try:
        _call(transport)
    except TransportCallFailed as exc:
        assert MODEL not in str(exc), str(exc)
        assert ENDPOINT not in str(exc), str(exc)
        assert "anthropic" not in str(exc).lower(), str(exc)
        return
    raise AssertionError("the failing opener did not raise")


# ── 6 ── the timeout ───────────────────────────────────────────────────

def test_the_timeout_reaches_the_opener():
    """``LiveLLM`` owns the timeout and passes it per call. A transport that
    drops it honours a default nobody chose, and ``contract.py`` lists
    ``timeout_honoured`` as UNVERIFIABLE from outside — so the one thing
    checkable from in here is checked in here."""
    opener = _Opener()
    transport = build_transport(
        api_key=KEY, model_id=MODEL, resolve_prompt=_resolver, opener=opener
    )
    _call(transport, timeout_s=7.5)
    assert opener.calls, "the opener was never called"
    _request, kwargs = opener.calls[0]
    assert kwargs.get("timeout") == 7.5, kwargs


# ── 7 ── the prompt ────────────────────────────────────────────────────

def test_the_prompt_comes_from_the_injected_resolver():
    """No prompt words live in ``dr_transport``. Plan §0.4 item 3 shows the
    prompt IN FULL and invites the room to improve it; a prompt inlined in a
    module makes that mean *read our source*. Checked on the wire body rather
    than by scanning source text, so it stays true however the module is
    reformatted."""
    opener = _Opener()
    transport = build_transport(
        api_key=KEY, model_id=MODEL, resolve_prompt=_resolver, opener=opener
    )
    _call(transport)
    request, _kwargs = opener.calls[0]
    sent = json.loads(request.data.decode("utf-8"))
    assert PROMPT_SENTINEL in sent["system"], sent["system"][:200]


if __name__ == "__main__":
    for fn in sorted(
        (v for k, v in list(globals().items()) if k.startswith("test_")),
        key=lambda f: f.__name__,
    ):
        fn()
        print(f"PASS {fn.__name__}")
