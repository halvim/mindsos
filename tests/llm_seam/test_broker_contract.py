"""Credential level 2 — the broker contract, from the client's side (ADR-0210 slice 4).

**What level 2 claims, and therefore what is worth guarding.** A broker the
user runs holds the credential; MindsOS composes the vendor's request, sends it
**unsigned** to the broker, and the broker adds the credential. So the claim is
not *"we scrub carefully"* — it is *"this process has no way to obtain the
credential at all"*.

⚠ **That claim is asserted STRUCTURALLY here, from the signature, not from a
call.** ``build_brokered_transport`` has no ``resolve_credential`` parameter
and ``broker_headers`` has no credential parameter, so there is no argument a
caller could pass and no branch a maintainer could forget. A test that merely
observed "no credential header was sent this time" would be asserting the
property in the one configuration it happened to run — which is round four of
the credential review, restated.

⚠ **The round trip below runs over a REAL loopback socket with the DEFAULT
opener.** ``test_adapter_and_seam_guards.py`` opens with *"Every guard injects
an opener, so none of them exercises the DEFAULT opener"*; this file is the
first in the package that does. The opener that IS injected is the **broker's
upstream** one — the hop after the credential is added, on the far side of the
property being claimed.

**What is still not covered, said plainly:** nothing here watches a real
provider fail (``dr-transport-never-watched-a-real-provider-failure``). The
upstream is a stub. What is real is the hop MindsOS makes.
"""

from __future__ import annotations

import inspect
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict

import pytest

from mindsos_llm import adapters, contract
from mindsos_llm.adapters import VendorHasNoBroker, anthropic
from mindsos_llm.broker import (
    BROKER_CONTRACT,
    BROKER_PROTOCOL_VERSION,
    HEADER_PROTOCOL,
    HEADER_VENDOR,
    BrokerContractViolated,
    broker_headers,
    require_broker_endpoint,
    verify_broker_response,
)
from mindsos_llm.credentials import LEVEL_NEVER_KNOWN, LEVEL_NEVER_STORED
from mindsos_llm.seam import UNREACHABLE, TransportCallFailed
from mindsos_broker.reference import BrokerConfig, serve

SCHEMA = {"type": "object", "properties": {"amount": {"type": "number"}}}
ANSWER = {"amount": 7}
BROKER_ONLY_CREDENTIAL = "sk-only-the-broker-ever-holds-this"

WIRE = dict(
    resolve_prompt=lambda **_: "a prompt",
    tool_name="extract",
    tool_description="extract the fields",
)


def _envelope(payload=ANSWER, tool="extract"):
    return {"content": [{"type": "tool_use", "name": tool, "input": payload}]}


# ---------------------------------------------------------------------------
# Two servers, and the difference matters
# ---------------------------------------------------------------------------


class _Recorded:
    """What a server actually received. The client's claim, seen from outside."""

    def __init__(self) -> None:
        self.headers: Dict[str, str] = {}
        self.body: Any = None
        self.path: str = ""


def _recording_server(recorded: _Recorded, *, status=200, echo_version=str(BROKER_PROTOCOL_VERSION), payload=None):
    """A server that is NOT the reference broker.

    It exists to answer *"what did MindsOS put on the wire"* — the reference
    broker forwards upstream and would answer a different question. It is also
    how the not-a-broker cases are built: a 200 with no echoed version is
    exactly the captive proxy the contract refuses.
    """
    body = json.dumps(payload if payload is not None else _envelope()).encode("utf-8")

    class _H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a, **k):  # noqa: D401
            """Silent under pytest."""

        def do_POST(self):  # noqa: N802
            recorded.path = self.path
            recorded.headers = {k.lower(): v for k, v in self.headers.items()}
            length = int(self.headers.get("content-length") or 0)
            recorded.body = json.loads(self.rfile.read(length).decode("utf-8"))
            self.send_response(status)
            if echo_version is not None:
                self.send_header(HEADER_PROTOCOL, echo_version)
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


@pytest.fixture
def recorded():
    return _Recorded()


@pytest.fixture
def restore_registry():
    """Snapshot and restore the adapter registry.

    The registry is module state; a test that leaves a fake vendor in it makes
    the NEXT test's failure someone else's problem to diagnose.
    """
    saved = dict(adapters._REGISTRY)
    try:
        yield
    finally:
        adapters._REGISTRY.clear()
        adapters._REGISTRY.update(saved)


def _call(transport, **over):
    kw = dict(
        prompt_iri="p", prompt_version=1, source_text="a document",
        extraction_schema=SCHEMA, timeout_s=10,
    )
    kw.update(over)
    return transport(**kw)


# ---------------------------------------------------------------------------
# 1 — the endpoint rule, which is NOT require_https
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://broker.example.com/v1",
        "https://127.0.0.1:8787",
        "http://127.0.0.1:8787",
        "http://[::1]:8787",
    ],
    ids=["https-remote", "https-loopback", "http-v4-loopback", "http-v6-loopback"],
)
def test_a_usable_broker_endpoint_is_accepted(url):
    """The permitting door. ``https`` anywhere, plaintext only where it cannot
    leave the machine."""
    assert require_broker_endpoint(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "http://broker.example.com/v1",
        "http://10.0.0.7:8787",
        "http://localhost:8787",
        "ftp://127.0.0.1/x",
        "127.0.0.1:8787",
    ],
    ids=["http-remote", "http-lan", "http-localhost-NAME", "not-http", "no-scheme"],
)
def test_a_broker_endpoint_that_could_leave_this_machine_is_refused(url):
    """MUTATION: relax any one clause of ``require_broker_endpoint``.

    ⚠ The ``localhost`` case is the one a looser rule would wave through and it
    is deliberate: a NAME is resolved, and what it resolves to is not this
    module's to promise. The literals are the only hosts that cannot be pointed
    somewhere else between configuration and call. A brokered request carries
    no credential but it does carry the customer's source text, which is why
    the rule is about leaving the machine rather than about secrecy.
    """
    with pytest.raises(ValueError, match="loopback"):
        require_broker_endpoint(url)


# ---------------------------------------------------------------------------
# 2 — the level-2 guarantee, asked from the SIGNATURE
# ---------------------------------------------------------------------------


def test_the_brokered_builder_has_NO_credential_parameter():
    """⚠ THE LEVEL-2 GUARANTEE, and it is a property of the shape.

    MUTATION: add a ``resolve_credential`` parameter to
    ``build_brokered_transport``.

    Level 2 says MindsOS never sees the credential. A guard that called the
    transport and observed no credential header would prove it for that call
    and that configuration — round four. There being no parameter proves it for
    every call, and it cannot be forgotten in a branch.
    """
    params = inspect.signature(anthropic.build_brokered_transport).parameters
    assert "resolve_credential" not in params
    assert not any("credential" in name for name in params), sorted(params)


def test_the_brokered_builder_cannot_be_told_where_to_forward():
    """MUTATION: add an ``endpoint`` parameter to ``build_brokered_transport``.

    The broker holds the vendor relationship. A client able to name the
    upstream could aim a credential-adding proxy at a host of its choosing,
    and the credential would be added to that request exactly as designed.
    """
    assert "endpoint" not in inspect.signature(anthropic.build_brokered_transport).parameters


def test_broker_headers_has_no_credential_parameter():
    """The twin of ``build_headers``, and the asymmetry is the design.

    MUTATION: give ``broker_headers`` a ``resolver`` parameter.
    """
    params = inspect.signature(broker_headers).parameters
    assert sorted(params) == ["base", "vendor_id"]


def test_broker_headers_stamps_the_version_and_the_vendor_and_keeps_the_base():
    got = broker_headers({"content-type": "application/json"}, vendor_id="anthropic")
    assert got[HEADER_PROTOCOL] == str(BROKER_PROTOCOL_VERSION)
    assert got[HEADER_VENDOR] == "anthropic"
    assert got["content-type"] == "application/json"


# ---------------------------------------------------------------------------
# 3 — the version is refused, never negotiated
# ---------------------------------------------------------------------------


class _Response:
    def __init__(self, headers):
        self.headers = headers
        self.status = 200


@pytest.mark.parametrize(
    "headers",
    [{}, {HEADER_PROTOCOL: "0"}, {HEADER_PROTOCOL: "2"}, {HEADER_PROTOCOL: ""}],
    ids=["absent", "older", "newer", "empty"],
)
def test_a_response_not_speaking_this_version_is_REFUSED_not_accommodated(headers):
    """MUTATION: accept a missing echo, or compare with ``in`` instead of ``==``.

    There is no negotiation and no fallback on purpose. A broker one version
    behind would otherwise do something adjacent to what was asked, and the
    failure would arrive as a wrong answer rather than as a refusal. The
    ``absent`` case is the captive-proxy one: something returned 200 and is not
    implementing this contract at all.
    """
    with pytest.raises(BrokerContractViolated) as caught:
        verify_broker_response(_Response(headers))
    assert str(caught.value) == BROKER_CONTRACT


def test_a_response_speaking_this_version_passes():
    """The other door of the same predicate."""
    assert verify_broker_response(
        _Response({HEADER_PROTOCOL: str(BROKER_PROTOCOL_VERSION)})
    ) is None


def test_the_broker_refusal_is_a_transport_failure_a_caller_already_classifies():
    """A deployment can tell 'my broker is wrong' from 'the provider is down',
    without a caller having to learn a new exception family."""
    assert issubclass(BrokerContractViolated, TransportCallFailed)
    assert BROKER_CONTRACT != UNREACHABLE


# ---------------------------------------------------------------------------
# 4 — the two level declarations, which slice 4 makes separate
# ---------------------------------------------------------------------------


def test_the_wire_tuple_did_NOT_absorb_level_2():
    """⚠ The whole reason level 2 is declared separately.

    ``SUPPORTED_LEVELS`` is a promise about the provider's wire — the Messages
    API has no expiring credential, and it has never heard of a broker. Level 2
    is a property of the adapter's code. Folding them together would give one
    tuple two meanings and would make ``build_transport``'s resolver optional.
    """
    assert anthropic.SUPPORTED_LEVELS == (LEVEL_NEVER_STORED,)
    assert anthropic.BROKERED_LEVELS == (LEVEL_NEVER_KNOWN,)


def test_a_picker_reads_the_UNION_and_the_halves_stay_separate():
    assert adapters.supported_levels("anthropic") == (1,)
    assert adapters.brokered_levels("anthropic") == (2,)
    assert adapters.offerable_levels("anthropic") == (1, 2)


@pytest.mark.parametrize("half", ["declaration", "builder"], ids=["declares-only", "builds-only"])
def test_declaring_HALF_of_level_2_is_refused_at_registration(restore_registry, half):
    """MUTATION: drop either arm of the ``declares != builds`` check.

    Both doors, because a registry that checked one would let the other
    through. An adapter advertising a brokered level it cannot build fails at
    client construction, in front of a user who picked level 2; one shipping a
    builder it never advertises is code no picker can reach.
    """
    attrs = {
        "VENDOR_ID": "half-a-broker",
        "SUPPORTED_LEVELS": (1,),
        "build_transport": staticmethod(lambda **_: None),
    }
    if half == "declaration":
        attrs["BROKERED_LEVELS"] = (2,)
    else:
        attrs["build_brokered_transport"] = staticmethod(lambda **_: None)
    with pytest.raises(ValueError, match="together or not at all"):
        adapters.register(type("_Half", (), attrs))


def test_a_vendor_with_no_broker_is_refused_by_NAME_not_by_AttributeError(restore_registry):
    """MUTATION: delete the ``brokered_levels`` check in
    ``adapters.build_brokered_transport``.

    Without it the failure is an ``AttributeError`` about a missing function,
    which names the code rather than the configuration that is wrong.
    """
    class _NoBroker:
        VENDOR_ID = "no-broker"
        SUPPORTED_LEVELS = (1,)
        build_transport = staticmethod(lambda **_: None)

    adapters.register(_NoBroker)
    with pytest.raises(VendorHasNoBroker, match="declares no brokered level"):
        adapters.build_brokered_transport("no-broker", broker_url="https://x/y")


def test_exactly_one_of_a_resolver_or_a_broker():
    """MUTATION: turn the exclusive-or in ``_build`` into ``or``.

    Neither would compose an unauthenticated request straight to the provider;
    both would put a credential on a request aimed at a machine never meant to
    receive one. The public entry points make each case unreachable from
    outside, which is why this is asked of the shared closure directly.
    """
    with pytest.raises(ValueError, match="exactly one of"):
        anthropic._build(
            resolver=None, broker_url=None, model_id="m", max_tokens=1,
            temperature=0.0, endpoint=anthropic.ENDPOINT, opener=lambda *a, **k: None,
            **WIRE,
        )


# ---------------------------------------------------------------------------
# 5 — what MindsOS actually puts on the wire, over a real socket
# ---------------------------------------------------------------------------


def test_a_brokered_request_carries_the_contract_headers_and_NO_CREDENTIAL(recorded):
    """⚠ The claim, observed from outside the process, over a REAL socket and
    through the DEFAULT opener.

    MUTATION: swap ``broker_headers`` for ``build_headers`` in the adapter's
    header branch.

    The structural guards above prove there is no way to supply a credential;
    this proves the composed request is the vendor's own body all the same — a
    transparent proxy, not a second protocol.
    """
    server, url = _recording_server(recorded)
    try:
        transport = adapters.build_brokered_transport(
            "anthropic", broker_url=url, model_id="a-model", **WIRE
        )
        assert _call(transport) == ANSWER
    finally:
        server.shutdown()
        server.server_close()

    assert recorded.headers[HEADER_PROTOCOL] == str(BROKER_PROTOCOL_VERSION)
    assert recorded.headers[HEADER_VENDOR] == "anthropic"
    assert anthropic.CREDENTIAL_HEADER not in recorded.headers
    assert not any("api-key" in name for name in recorded.headers), recorded.headers
    # The body is the vendor's, unchanged: same model, same forced tool.
    assert recorded.body["model"] == "a-model"
    assert recorded.body["tool_choice"] == {"type": "tool", "name": "extract"}
    assert recorded.body["messages"][0]["content"] == "a document"


def test_something_that_is_not_a_broker_answering_200_is_refused(recorded):
    """A captive proxy, a health-check page, a broker a version behind. Its body
    would decode into an answer-shaped nothing and fail far from here."""
    server, url = _recording_server(recorded, echo_version=None)
    try:
        transport = adapters.build_brokered_transport(
            "anthropic", broker_url=url, model_id="a-model", **WIRE
        )
        with pytest.raises(BrokerContractViolated):
            _call(transport)
    finally:
        server.shutdown()
        server.server_close()


def test_a_broker_that_fails_is_an_outage_in_the_fixed_prose(recorded):
    """A non-2xx is refused by ``seam.send`` before any body is read, so a
    broker's error page cannot reach a reader any more than a provider's can."""
    server, url = _recording_server(recorded, status=500)
    try:
        transport = adapters.build_brokered_transport(
            "anthropic", broker_url=url, model_id="a-model", **WIRE
        )
        with pytest.raises(TransportCallFailed) as caught:
            _call(transport)
        assert str(caught.value) == UNREACHABLE
    finally:
        server.shutdown()
        server.server_close()


# ---------------------------------------------------------------------------
# 6 — end to end, against the reference broker core actually ships
# ---------------------------------------------------------------------------


def test_the_credential_reaches_the_VENDOR_and_never_the_client():
    """⚠ Level 2, whole, over loopback: MindsOS → the shipped reference broker
    → a stubbed vendor.

    The credential is known only to the broker's config. The vendor sees it;
    the request MindsOS composed does not carry it; and the client gets its
    answer through the same ``refuse_unasked_keys`` every other call uses.
    """
    seen: Dict[str, Any] = {}

    class _Upstream:
        status = 200

        def __init__(self, body):
            self._b = body

        def read(self):
            return self._b

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_vendor(request, timeout=None):
        seen["headers"] = {k.lower(): v for k, v in request.headers.items()}
        seen["body"] = json.loads(request.data.decode("utf-8"))
        seen["url"] = request.full_url
        return _Upstream(json.dumps(_envelope()).encode("utf-8"))

    server, url = serve(
        BrokerConfig(
            upstream_endpoint=anthropic.ENDPOINT,
            credential_header=anthropic.CREDENTIAL_HEADER,
            fetch_credential=lambda: BROKER_ONLY_CREDENTIAL,
            vendor_id="anthropic",
            opener=fake_vendor,
        )
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        transport = adapters.build_brokered_transport(
            "anthropic", broker_url=url, model_id="a-model", **WIRE
        )
        assert _call(transport) == ANSWER
    finally:
        server.shutdown()
        server.server_close()

    assert seen["headers"][anthropic.CREDENTIAL_HEADER] == BROKER_ONLY_CREDENTIAL
    assert seen["url"] == anthropic.ENDPOINT
    # ⚠ The broker's own protocol headers are not the vendor's business.
    assert not [k for k in seen["headers"] if k.startswith("x-mindsos-")]


def test_the_shipped_contract_harness_passes_against_the_BROKERED_transport(recorded):
    """Row 7 of the capability contract, aimed at the level-2 path.

    ``verify_transport`` is what core hands a consumer to check a transport.
    A brokered transport is still a transport: same signature, same refusals,
    same no-silent-retry. A level that passed no contract check would be a
    second, unverified way to call a model.
    """
    server, url = _recording_server(recorded)
    try:
        transport = adapters.build_brokered_transport(
            "anthropic", broker_url=url, model_id="a-model", **WIRE
        )
        report = contract.verify_transport(
            transport,
            prompt_iri="prompt:p",
            prompt_version=1,
            source_text="a document",
            extraction_schema=SCHEMA,
        )
    finally:
        server.shutdown()
        server.server_close()
    assert not [c for c in report.checks if c.status == contract.FAILED], str(report)
    assert report.ok
