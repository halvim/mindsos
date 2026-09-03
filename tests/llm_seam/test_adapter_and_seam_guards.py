"""The transport guards — four adversarial review rounds, in executable form.

Every test here pins something that was found by RUNNING a transport against a
live provider, not by reading one. The prose reasons live in
``mindsos_llm/seam.py``; this file is the part that fails.

⚠ **Every guard injects an opener, so none of them exercises the DEFAULT
path** — and the fourth credential defect was found only in that path. That is
stated here rather than left implicit, because a reader who believes these
guards cover the credential property completely will believe the thing round
four disproved. ``mindsos_llm.contract`` names the gap ``unverifiable``.

No test in this file touches the network or needs a credential.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List, Mapping

import pytest

from mindsos_llm import adapters
from mindsos_llm.adapters import anthropic
from mindsos_llm.credentials import (
    LEVEL_NEVER_KNOWN,
    LEVEL_SHORT_LIVED,
    CredentialUnavailable,
    Resolver,
    static_resolver,
)
from mindsos_llm.seam import (
    NO_ANSWER,
    NO_PROPERTIES,
    NO_SCHEMA,
    UNASKED_KEYS,
    UNREACHABLE,
    TransportCallFailed,
    TransportSchemaRequired,
    TransportUnaskedKeys,
    scrub,
)

FAKE_KEY = "sk-ant-THIS-IS-THE-CREDENTIAL-DO-NOT-LEAK-IT"
SCHEMA = {
    "type": "object",
    "properties": {"fields": {"type": "array"}},
}
ANSWER = {"fields": [{"name": "days", "value": 7, "quote": "seven days"}]}


class _Response:
    """Minimal stand-in for what ``urlopen`` returns."""

    def __init__(self, payload: Mapping[str, Any], status: int = 200) -> None:
        self._payload = payload
        self.status = status

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def _envelope(*blocks: Mapping[str, Any]) -> Dict[str, Any]:
    return {"content": list(blocks)}


def _tool_block(name: str = "extract", payload: Mapping[str, Any] = None) -> Dict[str, Any]:
    return {"type": "tool_use", "name": name, "input": dict(payload or ANSWER)}


def _prompt(**_: Any) -> str:
    return "read the document"


def _build(**over: Any):
    seen: List[Any] = []

    def opener(request, timeout=None):
        seen.append((request, timeout))
        return _Response(_envelope(_tool_block()))

    kwargs: Dict[str, Any] = dict(
        resolve_credential=static_resolver(lambda: FAKE_KEY),
        model_id="a-model",
        resolve_prompt=_prompt,
        tool_name="extract",
        tool_description="pull the fields out",
        opener=opener,
    )
    kwargs.update(over)
    return anthropic.build_transport(**kwargs), seen


def _call(transport, **over: Any):
    kwargs = dict(
        prompt_iri="prompt:p",
        prompt_version=1,
        source_text="the document says seven days",
        extraction_schema=SCHEMA,
        timeout_s=9.5,
    )
    kwargs.update(over)
    return transport(**kwargs)


# ── 1 ── the call shape ────────────────────────────────────────────────

def test_the_transport_requires_all_five_keywords_with_no_defaults():
    """``LiveLLM`` passes all five every time. A default would let a caller
    that forgot the document get an answer about nothing."""
    transport, _ = _build()
    for missing in (
        "prompt_iri", "prompt_version", "source_text",
        "extraction_schema", "timeout_s",
    ):
        kwargs = dict(
            prompt_iri="prompt:p", prompt_version=1, source_text="doc",
            extraction_schema=SCHEMA, timeout_s=1.0,
        )
        del kwargs[missing]
        with pytest.raises(TypeError):
            transport(**kwargs)


def test_a_forced_tool_reply_is_returned_unaltered():
    transport, _ = _build()
    assert _call(transport) == ANSWER


# ── 2 ── the credential is a callable, not a value ─────────────────────

def test_a_bare_credential_is_refused_at_BUILD_time():
    """Round one: a credential passed as a value is a free variable of the
    transport closure, live in the frame locals of every raised link."""
    with pytest.raises(ValueError):
        anthropic.build_transport(
            resolve_credential=FAKE_KEY,  # type: ignore[arg-type]
            model_id="a-model",
            resolve_prompt=_prompt,
            tool_name="extract",
            tool_description="d",
        )


def test_a_resolver_refuses_a_non_callable_fetch():
    with pytest.raises(TypeError):
        Resolver(fetch=FAKE_KEY, level=1)  # type: ignore[arg-type]


# ── 3 ── the credential leaves nothing behind ──────────────────────────

def test_the_composed_request_retains_no_credential_after_a_SUCCESSFUL_call():
    """The scrub runs in a ``finally``, so it runs on the success path too —
    everything after the call can also raise, and this frame's request is on
    those tracebacks as well."""
    transport, seen = _build()
    _call(transport)
    request, _timeout = seen[0]
    blob = repr(sorted(request.headers.items())) + repr(
        sorted(request.unredirected_hdrs.items())
    )
    assert FAKE_KEY not in blob


def test_the_composed_request_retains_no_credential_after_a_FAILED_call():
    """The other door. Round three widened the guard to walk attributes rather
    than ``str(local)``, because ``repr(Request)`` is an address and the
    credential sat one attribute hop off that road."""
    captured: List[Any] = []

    def exploding(request, timeout=None):
        captured.append(request)
        raise OSError("connection reset")

    transport, _ = _build(opener=exploding)
    with pytest.raises(TransportCallFailed):
        _call(transport)
    request = captured[0]
    blob = repr(sorted(request.headers.items())) + repr(
        sorted(request.unredirected_hdrs.items())
    )
    assert FAKE_KEY not in blob


def test_scrub_is_case_insensitive_on_both_header_stores():
    """``Request`` title-cases header names and keeps a second dict for
    unredirected headers. Scrubbing one, or matching case-sensitively, leaves
    the credential exactly where it was."""

    class _Req:
        def __init__(self) -> None:
            self.headers = {"X-Api-Key": FAKE_KEY, "Content-Type": "application/json"}
            self.unredirected_hdrs = {"x-api-key": FAKE_KEY}

    request = _Req()
    scrub(request, "x-api-key")
    assert FAKE_KEY not in repr(request.headers)
    assert FAKE_KEY not in repr(request.unredirected_hdrs)
    assert request.headers["Content-Type"] == "application/json"


def test_the_credential_reaches_no_exception_this_module_raises():
    """Walks the whole cause chain. It does NOT assert the credential is absent
    from provider frames in flight: ``urllib`` copies the header dict down
    several frames and a header that is sent must be serialised. The claim was
    corrected to what survives — nothing MindsOS composes or retains carries
    it."""

    def exploding(request, timeout=None):
        raise OSError("connection reset")

    transport, _ = _build(opener=exploding)
    with pytest.raises(TransportCallFailed) as caught:
        _call(transport)
    exc = caught.value
    while exc is not None:
        assert FAKE_KEY not in str(exc)
        exc = exc.__cause__


def test_the_model_id_and_endpoint_reach_no_exception_this_module_raises():
    """⚠ This guard does NOT follow the cause chain, and says so in its own
    body: ``HTTPError`` names the URL it failed on, and suppressing that would
    destroy the only debugging surface there is. A traceback is not a rendered
    page."""

    def exploding(request, timeout=None):
        raise OSError("connection reset")

    transport, _ = _build(opener=exploding)
    with pytest.raises(TransportCallFailed) as caught:
        _call(transport)
    text = str(caught.value)
    assert "a-model" not in text
    assert "anthropic" not in text.lower()
    assert text == UNREACHABLE


def test_a_credential_that_cannot_be_fetched_says_so_and_not_that_we_are_down():
    """Two different faults, two different sentences. "We could not sign in" is
    not "they could not be reached", and collapsing them sends an operator to
    the wrong system."""
    transport, _ = _build(
        resolve_credential=static_resolver(lambda: (_ for _ in ()).throw(KeyError("nope")))
    )
    with pytest.raises(CredentialUnavailable) as caught:
        _call(transport)
    assert "nope" not in str(caught.value)
    assert str(caught.value) != UNREACHABLE


# ── 4 ── nothing is repaired ───────────────────────────────────────────

def test_a_call_with_no_schema_raises_instead_of_falling_back_to_free_text():
    transport, _ = _build()
    with pytest.raises(TransportSchemaRequired) as caught:
        _call(transport, extraction_schema=None)
    assert str(caught.value) == NO_SCHEMA


@pytest.mark.parametrize(
    "schema",
    [{"type": "object"}, {"$ref": "#/defs/x"}, {"type": "object", "properties": {}}],
    ids=["bare-object", "ref-only", "empty-properties"],
)
def test_a_schema_declaring_no_properties_RAISES_rather_than_refusing_every_reply(schema):
    """The would-refuse-every-time shape, in a REFUSAL path where it fails
    closed and looks principled. Engaging the only-what-was-asked-for check on
    a schema that declares nothing computes every key as unasked."""
    transport, _ = _build()
    with pytest.raises(TransportSchemaRequired) as caught:
        _call(transport, extraction_schema=schema)
    assert str(caught.value) == NO_PROPERTIES


def test_an_unasked_TOP_LEVEL_key_is_REFUSED_and_never_stripped():
    """``confidence`` is the worked example: a model self-report the reader's
    own docstring forbids storing as evidence. Stripped, it would ride into the
    payload and live as long as the payload does."""

    def opener(request, timeout=None):
        return _Response(
            _envelope(_tool_block(payload={**ANSWER, "confidence": 0.91}))
        )

    transport, _ = _build(opener=opener)
    with pytest.raises(TransportUnaskedKeys) as caught:
        _call(transport)
    assert str(caught.value) == UNASKED_KEYS


def test_a_nested_unasked_key_is_NOT_caught_and_the_limit_is_pinned():
    """The stated limit, pinned so it cannot quietly become a promise. A caller
    wanting this puts ``additionalProperties: false`` in its own schema."""

    def opener(request, timeout=None):
        return _Response(
            _envelope(_tool_block(payload={"fields": [{"name": "d", "confidence": 0.9}]}))
        )

    transport, _ = _build(opener=opener)
    assert "confidence" in _call(transport)["fields"][0]


# ── 5 ── the reply envelope ────────────────────────────────────────────

def test_two_blocks_with_the_forced_tools_name_RAISE_rather_than_the_first_winning():
    def opener(request, timeout=None):
        return _Response(_envelope(_tool_block(), _tool_block()))

    transport, _ = _build(opener=opener)
    with pytest.raises(TransportCallFailed) as caught:
        _call(transport)
    assert str(caught.value) == NO_ANSWER


def test_commentary_beside_the_tool_call_is_not_returned_as_the_answer():
    def opener(request, timeout=None):
        return _Response(
            _envelope({"type": "text", "text": "Here is the JSON:"}, _tool_block())
        )

    transport, _ = _build(opener=opener)
    assert _call(transport) == ANSWER


def test_a_non_2xx_raises_as_an_OUTAGE_without_reading_the_body():
    """A transport that read the body here would hand a provider's error page
    to a reader."""

    class _Exploding(_Response):
        def read(self):  # pragma: no cover - must never be called
            raise AssertionError("the error body was read")

    def opener(request, timeout=None):
        return _Exploding(_envelope(), status=503)

    transport, _ = _build(opener=opener)
    with pytest.raises(TransportCallFailed) as caught:
        _call(transport)
    assert str(caught.value) == UNREACHABLE


# ── 6 ── the request that is actually sent ─────────────────────────────

def test_the_request_FORCES_the_tool_and_sends_the_injected_schema():
    transport, seen = _build()
    _call(transport)
    body = json.loads(seen[0][0].data.decode("utf-8"))
    assert body["tool_choice"] == {"type": "tool", "name": "extract"}
    assert body["tools"][0]["input_schema"] == SCHEMA
    assert body["messages"][0]["content"] == "the document says seven days"


def test_the_prompt_comes_from_the_injected_resolver_and_no_words_live_here():
    transport, seen = _build(resolve_prompt=lambda **_: "INJECTED-PROMPT-TEXT")
    _call(transport)
    body = json.loads(seen[0][0].data.decode("utf-8"))
    assert body["system"] == "INJECTED-PROMPT-TEXT"
    source = open(anthropic.__file__, encoding="utf-8").read()
    assert "INJECTED-PROMPT-TEXT" not in source


def test_an_empty_prompt_is_a_fault_not_an_empty_system_message():
    transport, _ = _build(resolve_prompt=lambda **_: "   ")
    with pytest.raises(TransportCallFailed) as caught:
        _call(transport)
    assert str(caught.value) == NO_ANSWER


def test_the_timeout_reaches_the_opener():
    """One of the four properties the conformance harness calls unverifiable
    from outside — checkable here only because we are inside the transport."""
    transport, seen = _build()
    _call(transport, timeout_s=3.25)
    assert seen[0][1] == 3.25


def test_a_non_https_endpoint_is_refused_at_BUILD_time():
    """``https`` rather than "has a scheme": this request carries a credential.
    A schemeless endpoint once escaped as a bare ValueError NAMING the
    endpoint, through the one path that composes no fixed prose at all."""
    with pytest.raises(ValueError):
        anthropic.build_transport(
            resolve_credential=static_resolver(lambda: FAKE_KEY),
            model_id="a-model",
            resolve_prompt=_prompt,
            tool_name="extract",
            tool_description="d",
            endpoint="http://api.example.com/v1/messages",
        )


# ── 7 ── credential levels are the ADAPTER's promise ───────────────────

def test_the_anthropic_adapter_serves_level_1_ONLY():
    """A fact about the provider, not a limitation of MindsOS: the Messages API
    has no token-exchange flow, so level 3 cannot be honestly offered here."""
    assert anthropic.SUPPORTED_LEVELS == (1,)


@pytest.mark.parametrize("level", [LEVEL_NEVER_KNOWN, LEVEL_SHORT_LIVED])
def test_a_resolver_declaring_an_unsupported_level_is_refused_at_BUILD_time(level):
    with pytest.raises(ValueError):
        anthropic.build_transport(
            resolve_credential=Resolver(fetch=lambda: FAKE_KEY, level=level),
            model_id="a-model",
            resolve_prompt=_prompt,
            tool_name="extract",
            tool_description="d",
        )


def test_a_picker_reads_levels_off_the_ADAPTER_not_off_the_level_list():
    assert adapters.supported_levels("anthropic") == (1,)


# ── 8 ── refresh is not a retry ────────────────────────────────────────

def test_a_non_expiring_credential_never_reports_needing_refresh():
    assert static_resolver(lambda: FAKE_KEY).needs_refresh() is False


def test_refresh_is_decided_BEFORE_the_call_from_expiry_not_from_a_rejection():
    """⚠ The whole point. A resolver that re-mints in reaction to a 401 turns
    one call into two and makes the census of what was sent unknowable — the
    property ``no_silent_retry`` exists to protect."""
    resolver = Resolver(fetch=lambda: FAKE_KEY, level=3, expires_at=lambda: 1_000.0)
    assert resolver.needs_refresh(now=900.0) is False
    assert resolver.needs_refresh(now=960.0) is True
    assert resolver.needs_refresh(now=1_200.0) is True


# ── 9 ── the registry ──────────────────────────────────────────────────

def test_the_vendor_id_resolves_at_runtime_and_an_unknown_one_is_LOUD():
    """A silent default would run a reading against a provider the user did not
    choose, and the answer would carry the wrong provenance while looking
    correct."""
    assert adapters.get("anthropic") is anthropic
    with pytest.raises(adapters.UnknownVendor):
        adapters.get("not-a-vendor")


def test_registering_a_duplicate_id_is_refused_rather_than_overwriting():
    """Last-write-wins would make the resolved vendor depend on import order."""

    class _Impostor:
        VENDOR_ID = "anthropic"
        SUPPORTED_LEVELS = (1,)

        @staticmethod
        def build_transport(**_):  # pragma: no cover
            raise AssertionError

    with pytest.raises(ValueError):
        adapters.register(_Impostor)  # type: ignore[arg-type]


def test_an_incomplete_adapter_is_refused():
    class _Partial:
        VENDOR_ID = "partial"

    with pytest.raises(ValueError):
        adapters.register(_Partial)  # type: ignore[arg-type]


# ── 10 ── the domain this file does NOT cover ──────────────────────────

def test_every_guard_here_injects_an_opener_and_that_is_the_known_gap():
    """⚠ Round four was found in the DEFAULT opener path, which no guard in
    this file exercises. Asserted as a fact about the file rather than left
    implicit, so nobody reads this suite as complete coverage of the credential
    property. ``mindsos_llm.contract`` names the gap ``unverifiable``.

    ⚠ **This assertion is an AST walk, and the first version was a TEXT scan
    that matched its own assertion string and failed on its first run.** Same
    class as the relative import a path sweep could not see during the package
    move: *ask the structure, not the characters.* A text scan of source cannot
    tell a call from a mention of a call — and a test that scans its own file
    is guaranteed to contain the mention.
    """
    import ast as _ast

    tree = _ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"))
    called = {
        node.func.attr if isinstance(node.func, _ast.Attribute) else
        getattr(node.func, "id", None)
        for node in _ast.walk(tree)
        if isinstance(node, _ast.Call)
    }
    assert "default_opener" not in called, (
        "a guard here started using the real opener - that is a design event, "
        "not a tidy-up: state what it now proves and what it needs"
    )
    assert "urlopen" not in called
    imported = {
        alias.name.split(".")[0]
        for node in _ast.walk(tree)
        if isinstance(node, _ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in _ast.walk(tree)
        if isinstance(node, _ast.ImportFrom)
    }
    assert "urllib" not in imported, "this suite must not be able to reach the network"
