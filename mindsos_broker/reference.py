"""The reference broker: hold the credential, add it, forward, return.

**The whole program in one sentence.** It accepts the body MindsOS composed,
puts the credential header on it, sends it to the vendor, and hands back the
status and the bytes that came back.

⚠ **It rewrites NOTHING about the request except its destination and its
credential.** Not the model, not the tool, not the schema, not the prompt.
A broker that "helpfully" adjusted a body would be a silent repair layer one
process further out — the thing ``mindsos_llm.seam``'s docstring records four
review rounds of refusing — and it would be invisible to every guard core has,
because core would still be composing a correct request and receiving a
plausible answer.

**The credential is a CALLABLE here too.** :class:`BrokerConfig` holds
``fetch_credential``, not a key, for exactly the reason
:mod:`mindsos_llm.credentials` gives: a credential passed as a value is a free
variable of every closure that can see it and is live in the frame locals of
every raised link on a traceback. That argument does not stop being true
because this process is allowed to know the secret. **This is the one program
in the tree that holds one, so it is the one that can least afford to be
careless with it.**

**Three refusals, and each one is a different person's bug.**

* A request that does not carry this contract's version, or carries another
  one, is **400** — the caller is not speaking this protocol.
* A request for a different vendor is **400** — this broker holds one vendor's
  credential and the body is shaped for another vendor's wire; forwarding it
  would spend a real credential on a request that cannot succeed.
* An upstream that fails is **502 with an EMPTY body.** ⚠ The vendor's error
  page is never passed through. ``seam.send`` refuses a non-2xx *without
  reading the body* so that a provider's error page cannot reach a reader;
  a broker that forwarded it would defeat that from outside, and error pages
  are exactly where providers put account identifiers.

**Nothing is logged.** ``log_message`` is silenced rather than left to
``http.server``'s default, which writes the request line to stderr. There is no
prompt or source text in a request line, but the habit of a broker writing
anything about a request it did not compose is the wrong one to start.
"""

from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Optional, Tuple

from mindsos_llm.broker import (
    BROKER_PROTOCOL_VERSION,
    HEADER_PROTOCOL,
    HEADER_VENDOR,
)
from mindsos_llm.seam import require_https

#: Headers this broker never forwards upstream. The two protocol headers are
#: ours and mean nothing to a vendor; the rest are per-connection facts that
#: belong to the hop being made, not the hop being relayed.
_NOT_FORWARDED = frozenset(
    {
        HEADER_PROTOCOL,
        HEADER_VENDOR,
        "host",
        "content-length",
        "connection",
        "accept-encoding",
    }
)

#: Bodies larger than this are refused rather than buffered. A reading request
#: is a prompt and a document; anything at this scale is a misdirected upload,
#: and an unbounded ``read`` on a socket is how a local service becomes a way
#: to exhaust a laptop's memory.
MAX_BODY_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class BrokerConfig:
    """What this broker needs to know. ⚠ Not a credential — a way to get one.

    Args:
        upstream_endpoint: where the forwarded request goes. **https only**,
            checked at construction: this is the hop that carries the
            credential, which is precisely the condition
            :func:`mindsos_llm.seam.require_https` states for itself.
        credential_header: the header name the vendor authenticates with.
        fetch_credential: ``() -> str``, evaluated per request. A rotated
            credential is picked up without restarting the broker, and the
            value is a local of a frame that returns rather than a field on a
            long-lived object.
        vendor_id: the vendor this broker serves. A request naming another one
            is refused.
        opener: the UPSTREAM opener, defaulting to ``urllib.request.urlopen``.
            ⚠ Injected for the same reason the adapter injects one — a guard
            must not need a vendor account — and the asymmetry is deliberate:
            the hop a guard stubs here is the one **after** the credential is
            added, so the MindsOS-to-broker hop that carries the level-2
            guarantee is still made over a real socket with the default
            opener. Round four's lesson is that a property asserted only
            through an injected opener is asserted in the one configuration
            where it holds; the property this program exists for is on the
            hop that is NOT injected.
    """

    upstream_endpoint: str
    credential_header: str
    fetch_credential: Callable[[], str]
    vendor_id: str
    opener: Optional[Callable[..., Any]] = None

    def __post_init__(self) -> None:
        require_https(self.upstream_endpoint)
        if not callable(self.fetch_credential):
            raise TypeError(
                "fetch_credential must be a callable, not a credential - a "
                "credential held as a value is live in the frame locals of "
                "every raised link on a traceback"
            )
        if not self.credential_header or not self.vendor_id:
            raise ValueError("a broker needs a credential header and a vendor id")


def build_handler_class(config: BrokerConfig) -> type:
    """The request handler, closed over one configuration.

    A factory rather than a class attribute so two brokers can run in one
    process — which is what the guards do, and what a user with two vendors
    would do.
    """

    class _Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args, **kwargs) -> None:  # noqa: D401,ANN002
            """Silenced. See the module docstring."""

        def _respond(self, status: int, body: bytes = b"") -> None:
            if status >= 400:
                # ⚠ A refusal happens BEFORE the body is read, so the socket
                # still holds bytes this handler will never consume. Reusing
                # that connection would parse a JSON body as the next request
                # line. Refuse, answer, close.
                self.close_connection = True
            self.send_response(status)
            # ⚠ Echoed on EVERY response, including the refusals. A client
            # that cannot tell "your broker refused you" from "something else
            # is listening on that port" would report the wrong fault.
            self.send_header(HEADER_PROTOCOL, str(BROKER_PROTOCOL_VERSION))
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802 — http.server's spelling
            if self.headers.get(HEADER_PROTOCOL) != str(BROKER_PROTOCOL_VERSION):
                self._respond(400)
                return
            if self.headers.get(HEADER_VENDOR) != config.vendor_id:
                self._respond(400)
                return
            try:
                length = int(self.headers.get("content-length") or 0)
            except ValueError:
                self._respond(400)
                return
            if length <= 0 or length > MAX_BODY_BYTES:
                self._respond(400)
                return
            body = self.rfile.read(length)

            forwarded = {
                name: value
                for name, value in self.headers.items()
                if name.lower() not in _NOT_FORWARDED
            }
            # THE ONE THING THIS PROGRAM EXISTS TO DO.
            forwarded[config.credential_header] = config.fetch_credential()

            request = urllib.request.Request(
                config.upstream_endpoint,
                data=body,
                method="POST",
                headers=forwarded,
            )
            open_url = config.opener or urllib.request.urlopen
            try:
                with open_url(request, timeout=60) as response:
                    status = int(getattr(response, "status", 200) or 200)
                    payload = response.read()
            except Exception:  # noqa: BLE001
                # ⚠ Empty body, always. The vendor's error page is not ours to
                # relay, and it is where account identifiers live.
                self._respond(502)
                return
            finally:
                # Every frame here holds the same dict; one removal clears them
                # all. ``seam.scrub``'s argument, applied to the one process
                # that legitimately had the value in the first place.
                forwarded.pop(config.credential_header, None)
            self._respond(status, payload)

        def do_GET(self) -> None:  # noqa: N802
            """No readable surface. A broker answers one question."""
            self._respond(405)

    return _Handler


def serve(
    config: BrokerConfig, *, host: str = "127.0.0.1", port: int = 0
) -> Tuple[ThreadingHTTPServer, str]:
    """Bind and return ``(server, url)`` WITHOUT serving. The caller decides how.

    Defaults to the loopback literal and to port 0. The literal because a
    broker bound to every interface is a credential-adding proxy on the
    network, which is the opposite of what level 2 is for; port 0 because a
    fixed port in a test is a flake waiting for a second run.
    """
    server = ThreadingHTTPServer((host, port), build_handler_class(config))
    bound_host, bound_port = server.server_address[0], server.server_address[1]
    # An IPv6 literal is bracketed in a URL. ``require_broker_endpoint`` parses
    # the host back out, so an unbracketed one would be refused by the very
    # client this URL is for.
    shown = f"[{bound_host}]" if ":" in str(bound_host) else bound_host
    return server, f"http://{shown}:{bound_port}"


__all__ = [
    "MAX_BODY_BYTES",
    "BrokerConfig",
    "build_handler_class",
    "serve",
]
