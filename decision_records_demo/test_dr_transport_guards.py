"""Step 1's guards — nine narrow claims about the piece that touches the network.

⚠ **What these guards DO NOT prove, said first (RULES §11).** They do not prove
this transport satisfies the ``Transport`` contract.
``mindsos_capacity.llm.contract.verify_transport`` is the harness written for
exactly that, and `mindsos_capacity/llm/` is ABSENT from the core this branch
pins — so the conformance check is run by the OWNER from the ``main`` checkout
and reported as evidence, never as a green guard here (plan §0.5 item 9). They
also prove nothing about a live provider: every guard runs against an injected
fake opener, because the build gate has neither network nor key.

**The one branching predicate is fixtured on BOTH sides at birth** (RULES §12):
``test_a_forced_tool_reply_is_returned_unaltered`` is the 2xx door and
``test_a_non_2xx_raises_as_an_OUTAGE_and_returns_nothing`` is the other.

⚠ **Two of these guards exist because an earlier version was WRONG, and both
were caught by running rather than by reading.** The non-2xx guard passed its
own mutation — its fixture raised through the envelope door, so the status check
could be deleted with nothing going red. And the whole free-text design was
falsified by a live provider that fenced its answer despite two instructions not
to; the tool is forced now, and two guards pin the forcing.

Plain python or pytest; no FalkorDB, no network.
"""

from __future__ import annotations

import inspect
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decision_records_demo.dr_transport import (  # noqa: E402
    ENDPOINT,
    NO_SCHEMA,
    UNREACHABLE,
    TransportCallFailed,
    TransportSchemaRequired,
    build_transport,
)

KEY = "sk-ant-TESTKEY-do-not-ship-0000"
MODEL = "claude-haiku-4-5-20251001"
TOOL = "record_stated_facts"
TOOL_WORDS = "TOOL DESCRIPTION SUPPLIED BY THE CALLER, and nothing else may produce it"
PROMPT_SENTINEL = "RESOLVER-SUPPLIED PROMPT, and nothing else may produce these words"

SCHEMA = {
    "type": "object",
    "properties": {
        "fields": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": ["name", "value", "quote"],
            },
        }
    },
    "required": ["fields"],
}

#: What the model produced. Guard 2 asserts this comes back byte-identical.
TOOL_INPUT = {
    "fields": [
        {"name": "off_work_period", "value": "at least six weeks",
         "quote": "off work for at least six weeks"}
    ]
}


def _resolver(*, prompt_iri, prompt_version):
    return PROMPT_SENTINEL


class _Response:
    def __init__(self, payload, status=200):
        self.status = status
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body


def _envelope(tool_input=None, name=TOOL):
    """A realistic reply: commentary BESIDE the tool call.

    The text block is here on purpose. A transport that returned the first
    text block it found would pass a guard whose fixture had only the tool
    call, and would hand the model's commentary to a reader as the answer."""
    return {
        "content": [
            {"type": "text", "text": "I'll record what the message states."},
            {"type": "tool_use", "name": name,
             "input": TOOL_INPUT if tool_input is None else tool_input},
        ]
    }


class _Opener:
    """Records what it was called with. No network anywhere in this file."""

    def __init__(self, payload=None, status=200, raises=None):
        self.payload = _envelope() if payload is None else payload
        self.status = status
        self.raises = raises
        self.calls = []

    def __call__(self, request, **kwargs):
        self.calls.append((request, kwargs))
        if self.raises is not None:
            raise self.raises
        return _Response(self.payload, status=self.status)


def _build(opener=None):
    return build_transport(
        api_key=KEY, model_id=MODEL, resolve_prompt=_resolver,
        tool_name=TOOL, tool_description=TOOL_WORDS, opener=opener,
    )


def _call(transport, **over):
    kwargs = dict(
        prompt_iri="prompt:drdemo/read_exposure",
        prompt_version=1,
        source_text="The operator was off work for at least six weeks.",
        extraction_schema=SCHEMA,
        timeout_s=12.5,
    )
    kwargs.update(over)
    return transport(**kwargs)


def _sent(opener):
    request, _kwargs = opener.calls[0]
    return json.loads(request.data.decode("utf-8"))


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
    nothing."""
    signature = inspect.signature(_build())
    call = dict(
        prompt_iri="prompt:x", prompt_version=1, source_text="text",
        extraction_schema=None, timeout_s=30.0,
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

def test_a_forced_tool_reply_is_returned_unaltered():
    """No key renamed, no field added, no value coerced — and the model's
    COMMENTARY is not the answer. The fixture carries a text block beside the
    tool call precisely so a transport that returned the first text block would
    redden here."""
    opener = _Opener()
    out = _call(_build(opener))
    assert isinstance(out, dict), f"returned {type(out).__name__}"
    assert out == TOOL_INPUT, out


# ── 3 ── the other door ────────────────────────────────────────────────

def test_a_non_2xx_raises_as_an_OUTAGE_and_returns_nothing():
    """⚠ **Two things here are deliberately adversarial, and the first version
    of this guard had neither — it PASSED ITS OWN MUTATION.**

    * **The 529 fixture carries a well-formed tool_use block.** A realistic
      error body has none, so with the status check deleted the transport still
      raised — through the ENVELOPE door — and the guard was green while
      proving nothing about the status.
    * **The message is asserted, not just the exception type.** A non-2xx is
      OUR OUTAGE (``UNREACHABLE``); a reply with no answer inside it is a
      different failure (``NO_ANSWER``). ``live.py`` classifies three failure
      kinds on purpose."""
    opener = _Opener(payload=_envelope(), status=529)
    try:
        out = _call(_build(opener))
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
    assert KEY not in json.dumps(_call(_build(_Opener())))

    boom = _Opener(raises=RuntimeError("connection reset by peer"))
    try:
        _call(_build(boom))
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
    module composes, which is the one that can reach a page through
    ``LLMCallFailed``."""
    boom = _Opener(raises=RuntimeError("connection reset by peer"))
    try:
        _call(_build(boom))
    except TransportCallFailed as exc:
        assert MODEL not in str(exc), str(exc)
        assert ENDPOINT not in str(exc), str(exc)
        assert "anthropic" not in str(exc).lower(), str(exc)
        return
    raise AssertionError("the failing opener did not raise")


# ── 6 ── the timeout ───────────────────────────────────────────────────

def test_the_timeout_reaches_the_opener():
    """``LiveLLM`` owns the timeout and passes it per call. A transport that
    drops it honours a default nobody chose, and ``contract.py`` reports
    ``timeout_honoured`` as UNVERIFIABLE from outside — so the one thing
    checkable from in here is checked in here."""
    opener = _Opener()
    _call(_build(opener), timeout_s=7.5)
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
    _call(_build(opener))
    assert PROMPT_SENTINEL in _sent(opener)["system"], _sent(opener)["system"][:200]


# ── 8 ── the forcing ───────────────────────────────────────────────────

def test_the_request_FORCES_the_tool_and_sends_the_injected_schema():
    """⚠ **This guard exists because a live provider falsified the design it
    replaced.** Asked for JSON in prose — twice, once in the prompt and once
    appended by the transport — the model returned it fenced in a markdown code
    block, and `verify_transport` reported *answer_is_text_or_a_mapping —
    returned text that does not decode to a JSON object*. Repairing the fence
    in the transport was rejected: it edits the model's output before anything
    checks it. **Forcing the tool removes the failure instead of repairing
    it**, so this pins the forcing and the schema that was forced."""
    opener = _Opener()
    _call(_build(opener))
    sent = _sent(opener)
    assert sent.get("tool_choice") == {"type": "tool", "name": TOOL}, sent.get("tool_choice")
    tools = sent.get("tools") or []
    assert len(tools) == 1, tools
    assert tools[0]["name"] == TOOL, tools[0]
    assert tools[0]["input_schema"] == SCHEMA, tools[0]["input_schema"]
    assert tools[0]["description"] == TOOL_WORDS, tools[0]["description"]


# ── 9 ── no fallback ───────────────────────────────────────────────────

def test_a_call_with_no_schema_raises_instead_of_falling_back_to_free_text():
    """The other half of guard 8, and the one that matters when nobody is
    watching. A transport that quietly dropped the tool when no schema arrived
    would reintroduce the fence on exactly the path with no fixture — and it
    would do it silently, months later, on whichever reader forgot to declare
    a schema."""
    opener = _Opener()
    try:
        _call(_build(opener), extraction_schema=None)
    except TransportSchemaRequired as exc:
        assert str(exc) == NO_SCHEMA, str(exc)
        assert not opener.calls, "it reached the network with nothing to force"
        return
    raise AssertionError("a call with no schema did not raise")


if __name__ == "__main__":
    for fn in sorted(
        (v for k, v in list(globals().items()) if k.startswith("test_")),
        key=lambda f: f.__name__,
    ):
        fn()
        print(f"PASS {fn.__name__}")
