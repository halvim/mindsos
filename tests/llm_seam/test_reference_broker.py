"""The reference broker itself (ADR-0210 slice 4, decision 9).

``mindsos_broker`` is the one program in this tree that deliberately holds a
credential, so that ``mindsos_llm`` never has to. That inverts what is worth
guarding: the client-side file next to this one proves a credential cannot
arrive; this one proves that the credential which legitimately IS here goes
exactly one place and comes back out nowhere.

**Why core ships it at all.** *An option in a picker that nothing implements is
dead* — a contract with no implementer is a shape nobody has proved fits. It is
also what lets the level-2 path be exercised over a real socket rather than
against a mock of itself.

⚠ **The upstream opener is injected and the inbound hop is not**, which is the
same asymmetry the client-side file states: a guard must not need a vendor
account, and the property this program exists for is on the hop a test actually
makes.
"""

from __future__ import annotations

import io
import json
import threading
import urllib.error
import urllib.request
from typing import Any, Dict

import pytest

from mindsos_llm.adapters import anthropic
from mindsos_llm.broker import (
    BROKER_PROTOCOL_VERSION,
    HEADER_PROTOCOL,
    HEADER_VENDOR,
)
from mindsos_broker import reference
from mindsos_broker.reference import BrokerConfig, serve

CREDENTIAL = "sk-the-broker-alone-knows-this"
BODY = {"model": "a-model", "messages": [{"role": "user", "content": "a document"}]}


class _Upstream:
    status = 200

    def __init__(self, body: bytes, status: int = 200) -> None:
        self._b = body
        self.status = status

    def read(self) -> bytes:
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _config(**over) -> BrokerConfig:
    seen: Dict[str, Any] = over.pop("seen", {})

    def opener(request, timeout=None):
        seen["headers"] = {k.lower(): v for k, v in request.headers.items()}
        seen["body"] = request.data
        seen["url"] = request.full_url
        return _Upstream(json.dumps({"ok": True}).encode("utf-8"))

    kwargs = dict(
        upstream_endpoint=anthropic.ENDPOINT,
        credential_header=anthropic.CREDENTIAL_HEADER,
        fetch_credential=lambda: CREDENTIAL,
        vendor_id="anthropic",
        opener=opener,
    )
    kwargs.update(over)
    return BrokerConfig(**kwargs)


@pytest.fixture
def broker():
    """A running broker plus the dict of what its upstream saw."""
    seen: Dict[str, Any] = {}
    server, url = serve(_config(seen=seen))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield url, seen
    finally:
        server.shutdown()
        server.server_close()


def _post(url, *, body=None, protocol=str(BROKER_PROTOCOL_VERSION), vendor="anthropic",
          method="POST", extra=None):
    payload = json.dumps(body if body is not None else BODY).encode("utf-8")
    headers = {"content-type": "application/json"}
    if protocol is not None:
        headers[HEADER_PROTOCOL] = protocol
    if vendor is not None:
        headers[HEADER_VENDOR] = vendor
    headers.update(extra or {})
    request = urllib.request.Request(url, data=payload, method=method, headers=headers)
    return urllib.request.urlopen(request, timeout=10)


# ---------------------------------------------------------------------------
# The configuration refuses what it cannot hold safely
# ---------------------------------------------------------------------------


def test_a_plaintext_upstream_is_refused_because_THAT_hop_carries_the_credential():
    """MUTATION: drop the ``require_https`` call in ``__post_init__``.

    ⚠ The two hops have different rules and this is the reason. The inbound hop
    may be plaintext on loopback because it carries no credential; the upstream
    hop always carries one, so it is exactly the condition ``require_https``
    states for itself. A broker that relaxed this would put the credential on
    the wire in clear.
    """
    with pytest.raises(ValueError, match="https"):
        _config(upstream_endpoint="http://api.example.com/v1/messages")


def test_a_credential_passed_as_a_VALUE_is_refused():
    """MUTATION: accept a string for ``fetch_credential``.

    The argument does not stop being true because this process is allowed to
    know the secret: a credential held as a value is live in the frame locals
    of every raised link on a traceback. ``mindsos_llm.credentials`` makes this
    case for the client; the program that actually holds one has less excuse.
    """
    with pytest.raises(TypeError, match="not a credential"):
        _config(fetch_credential=CREDENTIAL)


@pytest.mark.parametrize("field", ["credential_header", "vendor_id"], ids=["header", "vendor"])
def test_a_broker_missing_what_it_needs_to_route_is_refused(field):
    with pytest.raises(ValueError, match="credential header and a vendor id"):
        _config(**{field: ""})


# ---------------------------------------------------------------------------
# The one thing it exists to do
# ---------------------------------------------------------------------------


def test_the_credential_is_added_and_the_body_is_forwarded_BYTE_FOR_BYTE(broker):
    """⚠ A broker that "helpfully" adjusted a body would be a silent repair
    layer one process further out — invisible to core, which would still be
    composing a correct request and receiving a plausible answer."""
    url, seen = broker
    sent = json.dumps(BODY).encode("utf-8")
    with _post(url) as response:
        assert response.status == 200
    assert seen["headers"][anthropic.CREDENTIAL_HEADER] == CREDENTIAL
    assert seen["body"] == sent
    assert seen["url"] == anthropic.ENDPOINT


def test_the_protocol_headers_are_NOT_forwarded_upstream(broker):
    """MUTATION: empty ``_NOT_FORWARDED``.

    They are ours and mean nothing to a vendor. Forwarding them tells the
    provider how this deployment is wired, which is a fingerprint for no
    benefit.
    """
    url, seen = broker
    with _post(url):
        pass
    assert not [k for k in seen["headers"] if k.startswith("x-mindsos-")]
    assert "host" not in seen["headers"]


def test_the_response_never_carries_the_credential_back(broker):
    """The direction nobody thinks to check. A proxy that echoed request
    headers onto its response would hand the credential to the one process the
    design keeps it away from."""
    url, _ = broker
    with _post(url) as response:
        headers = {k.lower(): v for k, v in response.headers.items()}
        assert CREDENTIAL not in response.read().decode("utf-8")
    assert anthropic.CREDENTIAL_HEADER not in headers
    assert not [v for v in headers.values() if CREDENTIAL in str(v)]


def test_every_response_echoes_the_protocol_version_INCLUDING_the_refusals(broker):
    """MUTATION: move the echo header into the success path only.

    A client that cannot tell "your broker refused you" from "something else is
    listening on that port" reports the wrong fault, and the two are fixed by
    different people.
    """
    url, _ = broker
    with _post(url) as ok:
        assert ok.headers.get(HEADER_PROTOCOL) == str(BROKER_PROTOCOL_VERSION)
    with pytest.raises(urllib.error.HTTPError) as caught:
        _post(url, protocol="99")
    assert caught.value.headers.get(HEADER_PROTOCOL) == str(BROKER_PROTOCOL_VERSION)


# ---------------------------------------------------------------------------
# The three refusals, each a different person's bug
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "over",
    [
        {"protocol": None},
        {"protocol": "99"},
        {"vendor": None},
        {"vendor": "some-other-vendor"},
    ],
    ids=["no-version", "wrong-version", "no-vendor", "wrong-vendor"],
)
def test_a_request_this_broker_cannot_serve_is_400_and_is_NOT_forwarded(broker, over):
    """MUTATION: drop either the version check or the vendor check.

    ⚠ The vendor case is the one that costs money rather than only correctness:
    this broker holds ONE vendor's credential, and a body shaped for another
    vendor's wire would spend a real credential on a request that cannot
    succeed. Both are refused before anything is forwarded, which is what
    ``seen`` staying empty asserts.
    """
    url, seen = broker
    with pytest.raises(urllib.error.HTTPError) as caught:
        _post(url, **over)
    assert caught.value.code == 400
    assert seen == {}


def test_a_GET_is_refused_because_a_broker_answers_ONE_question(broker):
    url, seen = broker
    with pytest.raises(urllib.error.HTTPError) as caught:
        urllib.request.urlopen(url, timeout=10)
    assert caught.value.code == 405
    assert seen == {}


def test_an_upstream_failure_is_502_with_an_EMPTY_body():
    """⚠ MUTATION: relay the upstream body on failure.

    ``seam.send`` refuses a non-2xx *without reading the body* so a provider's
    error page cannot reach a reader. A broker that forwarded it would defeat
    that from outside — and error pages are where providers put account
    identifiers.
    """
    def exploding(request, timeout=None):
        raise urllib.error.HTTPError(
            request.full_url, 401, "Unauthorized", {},
            io.BytesIO(b'{"error":"account acct_12345 is over quota"}'),
        )

    failing, failing_url = serve(_config(opener=exploding))
    threading.Thread(target=failing.serve_forever, daemon=True).start()
    try:
        with pytest.raises(urllib.error.HTTPError) as caught:
            _post(failing_url)
        assert caught.value.code == 502
        assert caught.value.read() == b""
    finally:
        failing.shutdown()
        failing.server_close()


@pytest.mark.parametrize(
    "length", ["0", str(reference.MAX_BODY_BYTES + 1)], ids=["empty", "oversized"]
)
def test_a_body_this_broker_will_not_buffer_is_refused(broker, length):
    """MUTATION: drop either bound of the length check.

    Both doors of one predicate. An unbounded read on a socket is how a local
    service becomes a way to exhaust a laptop's memory; a zero-length body is a
    request with nothing to forward, and forwarding it would spend a credential
    on an empty call. Refused before any body is read, which is what ``seen``
    staying empty asserts.
    """
    url, seen = broker
    with pytest.raises(urllib.error.HTTPError) as caught:
        _post(url, extra={"content-length": length})
    assert caught.value.code == 400
    assert seen == {}


def test_the_broker_binds_LOOPBACK_by_default():
    """MUTATION: default ``host`` to ``0.0.0.0``.

    A credential-adding proxy reachable from the network is the opposite of
    what level 2 is for: anyone who can reach it can spend the credential.
    """
    server, url = serve(_config())
    try:
        assert server.server_address[0] == "127.0.0.1"
        assert url.startswith("http://127.0.0.1:")
    finally:
        server.server_close()
