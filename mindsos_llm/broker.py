"""Credential level 2 — the broker contract, from the side that never holds a key.

**What level 2 is, and what it is not.** A broker the user runs holds the
credential. MindsOS composes the vendor's request exactly as it always does,
sends it to the broker **with no credential on it**, and the broker adds the
credential and forwards it upstream. The credential never reaches this process.

⚠ **This is NOT a resolver, and the shape of this module is the argument.**
:mod:`mindsos_llm.credentials` states it: *"a resolver that returns nothing
would be a lie with a return type"*. So there is no resolver here, no optional
credential parameter, and no sentinel standing in for one. :func:`broker_headers`
is the twin of :func:`mindsos_llm.seam.build_headers` and its **signature cannot
accept a credential** — that is enforcement, not a guard, in the same sense as
the always-returning header helper it mirrors.

**The wire is a TRANSPARENT PROXY of the vendor's own request**, and that choice
is load-bearing. The alternative — a MindsOS-native protocol in which the broker
composes the vendor call itself — would put the forced tool, the response walk
and the only-what-was-asked-for refusal inside an artifact core cannot guard.
Every rule in :mod:`mindsos_llm.seam` would have to be re-asserted in somebody
else's program. As a transparent proxy the broker changes exactly two things
about a request — the URL it is sent to, and the credential header it does not
carry — and every other property of the call is the adapter's, unchanged.

**What the broker sees, said plainly rather than discovered later.** The
request body carries the prompt and the source text. A broker therefore sees
the customer's material. That is acceptable because it is the *user's own*
broker on the user's own machine, and it is stated here so that nobody deploys
a shared one under the impression that level 2 hides anything but the key.

**Versioned, and refused rather than negotiated.** MindsOS stamps
:data:`BROKER_PROTOCOL_VERSION` on every request and the broker must echo it.
A missing or different echo is :class:`BrokerContractViolated` — loud, in the
class of :data:`~mindsos_llm.seam.NO_SCHEMA`, because it is a deployment bug
and not a provider outage. There is deliberately no negotiation and no
fallback: a broker one version behind would otherwise silently do something
adjacent to what was asked, and the failure would surface as a wrong answer
rather than as a refusal.
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping
from urllib.parse import urlsplit

from .seam import TransportCallFailed

#: The version of the request/response contract below. An integer, bumped when
#: the contract changes in a way an existing broker would get wrong. It is sent
#: on every request and must be echoed on every response.
BROKER_PROTOCOL_VERSION = 1

#: Sent by MindsOS, echoed by the broker. A response without it did not come
#: from something implementing this contract.
HEADER_PROTOCOL = "x-mindsos-broker-protocol"

#: The vendor whose wire this body speaks. A broker configured for a different
#: vendor refuses rather than forwarding a body its upstream cannot read.
HEADER_VENDOR = "x-mindsos-broker-vendor"

#: Loopback LITERALS. ⚠ Deliberately not ``localhost``: a name is resolved, and
#: what it resolves to is not this module's to promise. The literals are the
#: only hosts that cannot be pointed somewhere else between configuration and
#: call.
LOOPBACK_HOSTS = ("127.0.0.1", "::1")

#: A deployment bug, in the class of :data:`~mindsos_llm.seam.NO_SCHEMA`: fixed
#: prose, safe on a customer's page, and deliberately not survivable.
BROKER_CONTRACT = (
    "the reading service is not correctly connected to its credential broker. "
    "This is a fault on our side and is never a finding about the case."
)


class BrokerContractViolated(TransportCallFailed):
    """The thing answering the broker endpoint does not implement this contract.

    A subclass of :class:`~mindsos_llm.seam.TransportCallFailed` so a caller
    that classifies transport failures does not need to learn a new family;
    a distinct class so a deployment can tell "my broker is wrong" from "the
    provider could not be reached", which are fixed by different people.
    """

    def __init__(self) -> None:
        super().__init__(BROKER_CONTRACT)


def require_broker_endpoint(url: str) -> str:
    """Refuse an unusable broker endpoint at BUILD time.

    ⚠ **This is deliberately NOT :func:`~mindsos_llm.seam.require_https`, and
    the difference is the reason that function gives for itself:** *"``https``
    rather than 'has a scheme': this request carries a credential."* A brokered
    request carries none. What it does carry is the customer's source text, so
    plaintext is refused everywhere it could leave the machine — and permitted
    on the loopback literals, where it cannot.

    Requiring TLS on loopback would mean a certificate for every user who runs
    the reference broker, which is how a level nobody can configure becomes a
    level nobody uses (decision 9's argument, one step further along).
    """
    parts = urlsplit(str(url))
    if parts.scheme == "https":
        return url
    if parts.scheme == "http" and parts.hostname in LOOPBACK_HOSTS:
        return url
    raise ValueError(
        "a broker endpoint must be https://, or http:// on a loopback literal "
        f"({', '.join(LOOPBACK_HOSTS)}); plaintext off this machine would put "
        "the source text on the wire"
    )


def broker_headers(
    base: Mapping[str, str], *, vendor_id: str
) -> MutableMapping[str, str]:
    """Build the headers of a brokered request. **Takes no credential.**

    ⚠ The twin of :func:`~mindsos_llm.seam.build_headers`, and the asymmetry is
    the point: that one exists to hold a credential in a frame that always
    returns, and this one exists so that no frame holds one at all. There is no
    parameter here through which a credential could arrive, which is why level 2
    needs no scrub, no ``finally`` and no traceback argument.
    """
    headers = dict(base)
    headers[HEADER_PROTOCOL] = str(BROKER_PROTOCOL_VERSION)
    headers[HEADER_VENDOR] = str(vendor_id)
    return headers


def verify_broker_response(response: Any) -> None:
    """Refuse a response that did not come from a broker speaking this version.

    Called after :func:`~mindsos_llm.seam.send` has already refused a non-2xx,
    so a broker's own failure is an outage and reaches here as one. What is
    left is the quieter case: something returned 200 and is not implementing
    this contract — a proxy, a captive portal, a broker a version behind. Its
    body would decode into an answer-shaped nothing, and the reading would fail
    somewhere further away with a sentence about the model.
    """
    headers = getattr(response, "headers", None)
    echoed = None
    if headers is not None:
        getter = getattr(headers, "get", None)
        if callable(getter):
            echoed = getter(HEADER_PROTOCOL)
    if echoed is None or str(echoed).strip() != str(BROKER_PROTOCOL_VERSION):
        raise BrokerContractViolated()


__all__ = [
    "BROKER_CONTRACT",
    "BROKER_PROTOCOL_VERSION",
    "HEADER_PROTOCOL",
    "HEADER_VENDOR",
    "LOOPBACK_HOSTS",
    "BrokerContractViolated",
    "broker_headers",
    "require_broker_endpoint",
    "verify_broker_response",
]
