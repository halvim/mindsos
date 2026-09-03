"""The provider-agnostic half of a transport, and the record of what was tried.

**Read this before proposing a change to it.** Nearly every paragraph below is
a design that was proposed, built, and rejected for a reason that only showed
up by running the thing. A shortened version of this docstring invites the
rejected designs straight back, which is why it travels with the code.

**Where this came from.** The rules here were earned in a consumer project
against a live provider, in a module that shipped outside core because core
had ruled that no vendor may enter it. ADR-0210 reversed that ruling and
restated the invariant: *no provider is baked in — the adapter is selected at
runtime, and the gate acquires no network, no credential and no vendor
dependency.* The wire moved into :mod:`mindsos_llm.adapters`; **this module is
the half a SECOND adapter must also obey**, which is exactly why the record
lives here rather than with the first adapter.

⚠ **THE ANSWER IS FORCED INTO A SHAPE, NOT REPAIRED INTO ONE.** The first
version of this work asked for JSON in prose and returned the model's text
verbatim. Run against a live provider it came back fenced in a markdown code
block **even with two explicit instructions not to**, and the conformance
harness reported *"returned text that does not decode to a JSON object"*.
Found by running it. A code fence is not the model malforming its answer, so
refusing on it would have made every reading a refusal for the wrong reason.

**The rejected fix, recorded because it was the first answer.** Stripping a
whole-string fence in the transport. It is a silent repair layer between the
model and every check that follows; it edits the model's output before
anything verifies it; and it does not generalise — trailing prose, *"Here is
the JSON:"* and smart quotes are each another quiet patch. **The argument this
whole seam exists to support is that nothing is fixed up on our side.**

**What replaces it:** the extraction schema is sent as a structured-output
request the provider must satisfy, so no fence can occur, nothing is stripped
and nothing is guessed. What reaches verification is what the model produced.
⟹ All remaining risk sits where it actually lives — the binding between a
value and its quote — instead of being mixed with format noise.

**Consequences, stated rather than discovered later.**

* An adapter returns a ``Mapping``, not text. That is explicitly allowed:
  :data:`~mindsos_llm.live.Transport` is typed
  ``Union[Mapping[str, Any], str]``.
* **There is no free-text fallback.** A call with no ``extraction_schema`` has
  nothing to force, and falling back would silently reintroduce the fence on
  exactly the path nobody is watching. It raises, and a guard pins it.
* ⚠ **A schema must DECLARE its top-level ``properties``, and one that does not
  is refused LOUDLY rather than accepted weakly.** ``{"type": "object"}`` and a
  ``$ref``-only schema are both legal and both declare nothing, so the
  only-what-was-asked-for check below would have computed *every* key as
  unasked and **refused every reply** — a would-refuse-every-time shape, in a
  REFUSAL path where it fails closed and looks principled. The offered
  alternative — engage the check only when ``properties`` exist — is a
  guarantee that silently disappears on exactly the schemas that need it.
* **Only what was asked for.** A reply whose TOP-LEVEL keys are not among the
  schema's declared ``properties`` is **refused, never stripped**: stripping is
  the repair layer above, and it would hide the one event worth seeing. A
  reader searches the fields for its name and ignores the rest, so an unasked
  key — ``confidence``, which the comprehension family's own docstring names as
  a value that must never be stored as evidence — would otherwise ride into
  the payload and live as long as the payload does. ⚠ **Stated limit:** the
  check is on TOP-LEVEL keys. A key nested inside an item is not caught, and a
  caller wanting ``additionalProperties: false`` puts it in its own schema —
  this module does not edit an injected schema.

**NO WORDS LIVE IN THIS MODULE.** Not a prompt, not a tool description. Words
are injected, so a prompt can be shown to a room in full without that meaning
*read our source*.

**FAILURE IS FIXED PROSE, AND THE CREDENTIAL IS THE HARD HALF.** Every failure
raises :class:`TransportCallFailed` with a sentence naming no key, no endpoint
and no model. ``LiveLLM`` wraps whatever raises into ``LLMCallFailed`` with the
provider exception on ``__cause__``, which makes the cause chain a developer
surface. Two obligations, guarded differently on purpose:

* **the credential appears in nothing MindsOS composes or retains** — not in a
  return value, not in any message written here, and not on any object built
  here once the call is over. ⚠ **NOT the same as "nowhere on the exception
  chain".** ``urllib``'s ``do_open`` builds a *copy* of the header dict and
  hands it down through ``request`` → ``_send_request`` → ``_send_output``,
  where it becomes bytes. **Several provider frames hold the credential while
  the request is in flight and no scrub can reach them** — a header that is
  sent must be serialised. The claim is corrected rather than the mechanism,
  because the mechanism is not wrong;
* **the model id and the endpoint appear nowhere in the exception raised
  here**, and the guard for it says in its own body that it does not follow the
  cause chain, because ``HTTPError`` names the URL it failed on and suppressing
  that would destroy the only debugging surface there is. A traceback is not a
  rendered page.

⚠ **THE CREDENTIAL SENTENCE WAS TWICE WIDER THAN ITS CHECK, and the second
time was inside the fix for the first.**

* **Round one** — the credential was a bare closure free variable, live in the
  transport frame's locals on every raised link. The guard walked ``str()`` of
  each link and found nothing, so it passed while the credential sat one road
  over.
* **Round two** — the proposed fix read the credential through a callable, and
  the new guard was to be *"the reviewer's own probe, promoted"*, which walks
  ``str(local)``. ``repr(Request)`` is ``<urllib.request.Request object at
  0x…>``. **The credential would have been on ``request.headers``, one
  attribute hop off the road the promoted probe takes, and the new guard would
  have gone GREEN over it.**
* **Round three** — caught by the widened guard on its first run.
* **Round four** — caught only by running the DEFAULT opener, which no guard
  uses: every credential guard injects a fake one, so the property had been
  asserted in exactly the one configuration where it holds. **Not a road the
  guard missed, a CONFIGURATION it missed.**

**Three mechanisms, and none of them is the guard:**

1. the credential is reached through a **callable**
   (:class:`~mindsos_llm.credentials.Resolver`), so no frame binds it as a free
   variable;
2. headers are built by a helper that **always returns**, so the frame that
   does hold it is off every traceback before anything can raise;
3. ⚠ the composed request's credential header is **scrubbed in a ``finally``**,
   before any exception leaves the call. The plan for (3) was once *"never bind
   the request, so this frame's locals hold no object carrying it."* That is
   worthless: **the opener binds it as a PARAMETER**, and the opener's frame is
   on the traceback when the opener raises. Hiding the object was never the
   property; **removing the credential from it is** — and because every frame
   holds the SAME object, scrubbing once clears all of them.

⚠ **Core enforces these three and does NOT claim to verify them.**
``mindsos_llm.contract`` names the property ``unverifiable`` instead, because a
harness that only CALLS a transport cannot reach the object that transport
composed, and any check that injects an opener to gain visibility recreates
round four exactly.
"""

from __future__ import annotations

import urllib.request
from typing import Any, Callable, Mapping, MutableMapping, Optional

from .credentials import CredentialUnavailable, Resolver

#: A fault on our side, said in a way that is safe on a customer's page.
UNREACHABLE = (
    "the reading service could not be reached. This is a fault on our side "
    "and is never a finding about the case."
)

#: Same discipline, different cause: the provider answered with nothing this
#: transport can find an answer inside. NOT the model malforming a reply — a
#: forced structured output cannot produce one.
NO_ANSWER = (
    "the reading service replied without an answer in it. This is a fault on "
    "our side and is never a finding about the case."
)

#: A deployment bug, and deliberately not survivable. See the module
#: docstring: a free-text fallback reintroduces the fence on the one path
#: nobody watches.
NO_SCHEMA = (
    "a reading was requested with no shape to return it in. This is a fault "
    "on our side and is never a finding about the case."
)

#: Also a deployment bug. A schema declaring no top-level ``properties``
#: cannot support the only-what-was-asked-for check, and engaging that check
#: anyway refuses every reply.
NO_PROPERTIES = (
    "a reading was requested against a shape that names no fields. This is a "
    "fault on our side and is never a finding about the case."
)

#: A finding about the ANSWER, not about us.
UNASKED_KEYS = (
    "the reading came back carrying something that was not asked for, so it "
    "was not accepted."
)


class TransportCallFailed(RuntimeError):
    """The call did not produce an answer. ``LiveLLM`` turns this into an outage."""


class TransportUnaskedKeys(TransportCallFailed):
    """The reply carried top-level keys outside the declared schema.

    **Refused, not stripped.** Dropping them is a repair layer, and it hides
    the one event worth seeing.
    """


class TransportSchemaRequired(TransportCallFailed):
    """No usable ``extraction_schema``, so no shape could be forced.

    A deployment bug rather than an outage. It is deterministic, so a guard
    prevents it from ever shipping.
    """


def require_https(endpoint: str) -> str:
    """Refuse a non-``https`` endpoint at BUILD time.

    ⚠ Same class as :data:`NO_SCHEMA` and :data:`NO_PROPERTIES`: a deployment
    bug made loud and deterministic. A schemeless endpoint once reached
    ``Request()`` constructed one line above the ``try``, so the scrub never
    ran, and it escaped as a bare ``ValueError`` **naming the endpoint** —
    through the one path that composes no fixed prose at all. ``https`` rather
    than "has a scheme": this request carries a credential.
    """
    if not str(endpoint).startswith("https://"):
        raise ValueError("the endpoint must be an https:// URL")
    return endpoint


def require_resolver(resolver: Any) -> Resolver:
    """Refuse anything but a :class:`~mindsos_llm.credentials.Resolver`.

    A bare string would be a free variable of the transport closure and
    therefore live in the frame locals of every raised link — round one above.
    """
    if not isinstance(resolver, Resolver):
        raise ValueError(
            "resolve_credential must be a Resolver, not a credential - see "
            "mindsos_llm.credentials for why the indirection is load-bearing"
        )
    return resolver


def declared_properties(extraction_schema: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
    """The schema's top-level ``properties``, or raise.

    Two separate refusals on purpose. No schema at all is a caller that forgot
    to ask for a shape; a schema declaring nothing is a caller that asked for a
    shape the only-what-was-asked-for check cannot read. Collapsing them would
    hide the second, which is the one that fails closed and looks principled.
    """
    if not extraction_schema:
        raise TransportSchemaRequired(NO_SCHEMA)
    declared = extraction_schema.get("properties")
    if not isinstance(declared, Mapping) or not declared:
        raise TransportSchemaRequired(NO_PROPERTIES)
    return declared


def refuse_unasked_keys(
    answer: Mapping[str, Any], declared: Mapping[str, Any]
) -> Mapping[str, Any]:
    """Return ``answer`` unaltered, or refuse it. **Never strip.**

    ⚠ Stated limit: TOP-LEVEL keys only. A key nested inside an item is not
    caught; a caller wanting that puts ``additionalProperties: false`` in its
    own schema, because this seam does not edit an injected schema.
    """
    unasked = sorted(set(answer) - set(declared))
    if unasked:
        raise TransportUnaskedKeys(UNASKED_KEYS)
    return answer


def require_prompt(resolve_prompt: Callable[..., str], **kwargs: Any) -> str:
    """Resolve the prompt through the injected resolver, or refuse.

    The only source of prompt words. Nothing in this package inlines one.
    """
    system = resolve_prompt(**kwargs)
    if not isinstance(system, str) or not system.strip():
        raise TransportCallFailed(NO_ANSWER)
    return system


def build_headers(
    resolver: Resolver, header_name: str, base: Mapping[str, str]
) -> MutableMapping[str, str]:
    """Build request headers and RETURN.

    ⚠ **This function exists to always return.** The credential is a local of
    THIS frame and of no other, so this frame is off every traceback before
    anything downstream can raise. Inlining it at the call site would put the
    credential in the frame that also makes the call — which is round one.
    """
    headers = dict(base)
    headers[header_name] = resolver()
    return headers


def scrub(request: Any, header_name: str) -> None:
    """Remove the credential from a request that frames still hold.

    Every frame on every traceback holds the SAME object, so one removal
    clears them all — which is why this works where not-binding-it did not.
    ``Request`` title-cases header names and keeps a second dict for
    unredirected headers; both are cleared, case-insensitively.
    """
    wanted = header_name.lower()
    for store in (
        getattr(request, "headers", None),
        getattr(request, "unredirected_hdrs", None),
    ):
        if not store:
            continue
        for name in [k for k in store if k.lower() == wanted]:
            del store[name]


def send(
    open_url: Callable[..., Any],
    request: Any,
    *,
    timeout_s: float,
    header_name: str,
) -> Any:
    """Make the call, scrub in a ``finally``, and refuse a non-2xx.

    ⚠ The scrub runs **before the exception propagates, and on the success path
    too** — everything after the call can also raise, and this frame's request
    is on those tracebacks as well.

    A non-2xx raises without reading the body. A transport that read it would
    hand a provider's error page to a reader.
    """
    try:
        response = open_url(request, timeout=timeout_s)
    except CredentialUnavailable:
        # Already fixed prose, and it says something different from an outage:
        # we could not sign in, rather than they could not be reached.
        raise
    except Exception as exc:
        raise TransportCallFailed(UNREACHABLE) from exc
    finally:
        scrub(request, header_name)
    status = getattr(response, "status", None)
    if status is None:
        status = getattr(response, "code", 200)
    if not 200 <= int(status) < 300:
        raise TransportCallFailed(UNREACHABLE)
    return response


def default_opener() -> Callable[..., Any]:
    """``urllib.request.urlopen``.

    Injected everywhere so guards run with no network and no credential. ⚠ The
    default is nonetheless the configuration round four was found in: a
    property asserted only against an injected opener is asserted in the one
    configuration where it holds.
    """
    return urllib.request.urlopen


__all__ = [
    "NO_ANSWER",
    "NO_PROPERTIES",
    "NO_SCHEMA",
    "UNASKED_KEYS",
    "UNREACHABLE",
    "TransportCallFailed",
    "TransportSchemaRequired",
    "TransportUnaskedKeys",
    "build_headers",
    "declared_properties",
    "default_opener",
    "refuse_unasked_keys",
    "require_https",
    "require_prompt",
    "require_resolver",
    "scrub",
    "send",
]
