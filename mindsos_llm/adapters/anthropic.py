"""Anthropic Messages — the wire, and nothing but the wire.

Everything that is a RULE rather than a wire detail lives in
:mod:`mindsos_llm.seam`: no repair layer, no free-text fallback, unasked keys
refused rather than stripped, no prompt words in the module, and the three
credential mechanisms. **Read that module's docstring before changing this
one** — a second adapter obeys the same rules, which is why they are not here.

What IS here, and it is the whole of what makes this file Anthropic-specific:

* the endpoint and the API version header;
* the credential header name;
* the request body shape, including how a schema is turned into a forced
  structured output;
* how an answer is found in the reply envelope.

**Structured output is FORCED.** The schema is sent as a tool and the tool is
required, so the provider guarantees a structured object. See the seam for why
this replaced asking for JSON in prose — a live provider returned a fenced code
block despite two explicit instructions not to, and repairing that here was
rejected as a silent repair layer.

⚠ **TWO BLOCKS CARRYING THE FORCED TOOL'S NAME RAISE.** The first winning
silently is the same defect as picking one of two unconsumed carriers: the
reply supports no tie-break, so there is nothing to pick *by*.

⚠ **THIS ADAPTER SUPPORTS CREDENTIAL LEVEL 1 ONLY, and that is a fact about
the provider rather than a limitation of MindsOS.** The Messages API
authenticates with a long-lived `x-api-key` header and offers no token-exchange
or expiring credential flow, so level 3 cannot be honestly offered here. It
arrives with a hosted adapter (Bedrock, Vertex, Azure), which is a different
wire shape and therefore a different module. :data:`SUPPORTED_LEVELS` is what a
first-run picker reads; it must never be widened to advertise something the
wire cannot do.

⚠ **LEVEL 2 IS DECLARED SEPARATELY, IN :data:`BROKERED_LEVELS`, AND THAT SPLIT
IS DELIBERATE** (ADR-0210 slice 4). Level 2 is not a fact about the Messages
API — the provider knows nothing about brokers. It is a fact about *this
module*: the request can be composed without a credential and sent somewhere
else, so a broker can add the credential downstream. Folding that into
:data:`SUPPORTED_LEVELS` would give one tuple two meanings and make the
paragraph above half-wrong, and it would make the resolver optional in
:func:`build_transport` — the one function that must never take a credential
optionally.

⟹ **Two entry points, one closure.** :func:`build_transport` always requires a
resolver; :func:`build_brokered_transport` cannot accept one. The body, the
forced tool and the envelope walk are shared, because level 2 is *a wrapper
around this adapter* rather than a second adapter, and a copy of the wire would
be a second thing to keep correct.

⚠ **MindsOS does not tell the broker where to forward.** There is no upstream
``endpoint`` argument on the brokered path. The broker holds the vendor
relationship — its endpoint and its credential — and a client that could name
the upstream could point a credential-adding proxy at a host of its choosing.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Mapping, Optional

from ..broker import broker_headers, require_broker_endpoint, verify_broker_response
from ..credentials import LEVEL_NEVER_KNOWN, LEVEL_NEVER_STORED, Resolver
from ..seam import (
    NO_ANSWER,
    TransportCallFailed,
    build_headers,
    declared_properties,
    default_opener,
    refuse_unasked_keys,
    require_https,
    require_prompt,
    require_resolver,
    send,
)

#: The stable id a user's stored vendor choice resolves through.
VENDOR_ID = "anthropic"

#: Never printed, never rendered, never in an exception raised here.
ENDPOINT = "https://api.anthropic.com/v1/messages"

#: The wire version header the Messages API requires.
API_VERSION = "2023-06-01"

#: The credential header. Named here because the seam has to know what to
#: scrub, and scrubbing the wrong name is a silent failure of the one property
#: this package guards hardest.
CREDENTIAL_HEADER = "x-api-key"

#: ⚠ Level 1 only. See the module docstring — this is the provider's shape,
#: not a MindsOS choice, and widening it would advertise a guarantee the wire
#: cannot keep. **Level 2 is NOT here**: it is a property of this module rather
#: than of the provider, and it is declared in :data:`BROKERED_LEVELS`.
SUPPORTED_LEVELS = (LEVEL_NEVER_STORED,)

#: The levels this adapter serves with a broker in front of it. Declared
#: because :func:`build_brokered_transport` exists — the registry refuses one
#: without the other, so an adapter cannot advertise a brokered level it has no
#: way to build, nor ship a brokered builder no picker will ever offer.
BROKERED_LEVELS = (LEVEL_NEVER_KNOWN,)


def _build(
    *,
    resolver: Optional[Resolver],
    broker_url: Optional[str],
    model_id: str,
    resolve_prompt: Callable[..., str],
    tool_name: str,
    tool_description: str,
    max_tokens: int,
    temperature: float,
    endpoint: str,
    opener: Optional[Callable[..., Any]],
) -> Callable[..., Mapping[str, Any]]:
    """The shared closure. ⚠ **Exactly one of a resolver or a broker.**

    Not "a resolver, optionally": the two are mutually exclusive and the check
    is written as an exclusive-or on purpose. Neither one would compose an
    unauthenticated request straight to the provider — a call that fails at the
    vendor with a sentence about authentication, from a client that believed it
    was brokered. Both would put a credential on a request aimed at a machine
    that was never meant to receive one.
    """
    if (resolver is None) == (broker_url is None):
        raise ValueError(
            "exactly one of resolve_credential or broker_url: a credentialled "
            "call needs a resolver, and a brokered call must not have one"
        )
    if not tool_name or not tool_description:
        raise ValueError("the forced tool needs a name and a description")
    url = endpoint if resolver is not None else broker_url
    open_url = opener or default_opener()

    def transport(
        *,
        prompt_iri: str,
        prompt_version: int,
        source_text: str,
        extraction_schema: Optional[Mapping[str, Any]],
        timeout_s: float,
    ) -> Mapping[str, Any]:
        # ⚠ No defaults on any of the five. ``LiveLLM`` passes all five on
        # every call, and a default here would let a caller that forgot the
        # document get an answer about nothing instead of a TypeError.
        import urllib.request  # local: the seam owns the network policy

        system = require_prompt(
            resolve_prompt, prompt_iri=prompt_iri, prompt_version=prompt_version
        )
        declared = declared_properties(extraction_schema)
        body = json.dumps(
            {
                "model": model_id,
                "max_tokens": int(max_tokens),
                "temperature": float(temperature),
                "system": system,
                "messages": [{"role": "user", "content": source_text}],
                "tools": [
                    {
                        "name": tool_name,
                        "description": tool_description,
                        "input_schema": dict(extraction_schema or {}),
                    }
                ],
                # THE forcing. Without it the model may answer in prose, and
                # prose is where the fence came back.
                "tool_choice": {"type": "tool", "name": tool_name},
            }
        ).encode("utf-8")
        base = {
            "content-type": "application/json",
            "anthropic-version": API_VERSION,
        }
        # ⚠ The credential branch, and it is the only one in this module. The
        # brokered side has no parameter through which a credential could
        # arrive, so there is nothing on that path to forget to scrub.
        headers = (
            build_headers(resolver, CREDENTIAL_HEADER, base)
            if resolver is not None
            else broker_headers(base, vendor_id=VENDOR_ID)
        )
        request = urllib.request.Request(
            url, data=body, method="POST", headers=headers
        )
        # ⚠ ``header_name`` is passed on BOTH paths. On the brokered one the
        # scrub finds nothing, and that is the point: if a later edit ever put
        # a credential on this request, it would still be removed in the
        # ``finally`` rather than depending on someone noticing the branch.
        response = send(
            open_url, request, timeout_s=timeout_s, header_name=CREDENTIAL_HEADER
        )
        if resolver is None:
            # After the status check, before the body is read. A 200 from
            # something that is not a broker decodes into an answer-shaped
            # nothing and fails far away from here.
            verify_broker_response(response)
        try:
            envelope = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise TransportCallFailed(NO_ANSWER) from exc
        blocks = [
            block
            for block in envelope.get("content") or []
            # A model may emit commentary beside the tool call. It is not the
            # answer and is never returned as one.
            if isinstance(block, Mapping)
            and block.get("type") == "tool_use"
            and block.get("name") == tool_name
        ]
        if len(blocks) != 1:
            # Two carriers and no tie-break the reply supports; or none at all.
            raise TransportCallFailed(NO_ANSWER)
        answer = blocks[0].get("input")
        if not isinstance(answer, Mapping):
            raise TransportCallFailed(NO_ANSWER)
        # Unaltered: no key renamed, no field added, no value coerced.
        return refuse_unasked_keys(answer, declared)

    return transport


def build_transport(
    *,
    resolve_credential: Resolver,
    model_id: str,
    resolve_prompt: Callable[..., str],
    tool_name: str,
    tool_description: str,
    max_tokens: int = 1024,
    temperature: float = 0.0,
    endpoint: str = ENDPOINT,
    opener: Optional[Callable[..., Any]] = None,
) -> Callable[..., Mapping[str, Any]]:
    """Build the callable ``LiveLLM`` will hold. **A resolver is required.**

    Args:
        resolve_credential: A :class:`~mindsos_llm.credentials.Resolver`. ⚠ Not
            a credential — see that module for why the indirection is the
            mechanism rather than a style choice. ⚠ Not optional either: level
            2 has its own entry point rather than a ``None`` accepted here.
        model_id: Passed to the provider. ``LiveLLM`` stamps its own copy onto
            the payload for provenance; this one only reaches the wire.
        resolve_prompt: ``(prompt_iri, prompt_version) -> str``. **The only
            source of prompt words**, injected so a prompt can be shown in full
            without that meaning *read our source*.
        tool_name, tool_description: The forced tool's identity and its
            sentence, injected for the same reason.
        opener: Defaults to ``urllib.request.urlopen``. Injected so every guard
            runs with no network and no credential — and ⚠ so that the DEFAULT
            path is the one no guard exercises, which is where the fourth
            credential defect was found.
    """
    resolver = require_resolver(resolve_credential)
    if resolver.level not in SUPPORTED_LEVELS:
        raise ValueError(
            f"this adapter serves credential levels {SUPPORTED_LEVELS!r}; the "
            f"resolver declares {resolver.level!r}. A level the wire cannot "
            "honour must not be offered for it."
        )
    return _build(
        resolver=resolver,
        broker_url=None,
        model_id=model_id,
        resolve_prompt=resolve_prompt,
        tool_name=tool_name,
        tool_description=tool_description,
        max_tokens=max_tokens,
        temperature=temperature,
        endpoint=require_https(endpoint),
        opener=opener,
    )


def build_brokered_transport(
    *,
    broker_url: str,
    model_id: str,
    resolve_prompt: Callable[..., str],
    tool_name: str,
    tool_description: str,
    max_tokens: int = 1024,
    temperature: float = 0.0,
    opener: Optional[Callable[..., Any]] = None,
) -> Callable[..., Mapping[str, Any]]:
    """Build the level-2 transport: the same request, sent unsigned to a broker.

    ⚠ **There is no ``resolve_credential`` parameter and there must never be
    one.** That absence is the level-2 guarantee expressed as a signature: this
    process has no way to obtain the credential, so it cannot leak one and no
    guard has to prove that it did not. It is the same kind of argument as the
    always-returning header helper — a property of the shape rather than of a
    check over it.

    ⚠ **There is no upstream ``endpoint`` parameter either.** Where the request
    goes after the broker is the broker's configuration, not this client's.

    Args:
        broker_url: ``https://`` anywhere, or ``http://`` on a loopback
            literal. See :func:`mindsos_llm.broker.require_broker_endpoint` for
            why that is not the rule the credentialled path uses.
    """
    return _build(
        resolver=None,
        broker_url=require_broker_endpoint(broker_url),
        model_id=model_id,
        resolve_prompt=resolve_prompt,
        tool_name=tool_name,
        tool_description=tool_description,
        max_tokens=max_tokens,
        temperature=temperature,
        endpoint=ENDPOINT,
        opener=opener,
    )


__all__ = [
    "API_VERSION",
    "BROKERED_LEVELS",
    "CREDENTIAL_HEADER",
    "ENDPOINT",
    "SUPPORTED_LEVELS",
    "VENDOR_ID",
    "build_brokered_transport",
    "build_transport",
]
