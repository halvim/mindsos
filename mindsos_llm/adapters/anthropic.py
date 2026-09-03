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
authenticates with a long-lived key and offers no token-exchange or expiring
credential flow, so level 3 cannot be honestly offered here. It arrives with a
hosted adapter (Bedrock, Vertex, Azure), which is a different wire shape and
therefore a different module. :data:`SUPPORTED_LEVELS` is what a first-run
picker reads; it must never be widened to advertise something the wire cannot
do.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Mapping, Optional

from ..credentials import LEVEL_NEVER_STORED, Resolver
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
#: cannot keep.
SUPPORTED_LEVELS = (LEVEL_NEVER_STORED,)


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
    """Build the callable ``LiveLLM`` will hold.

    Args:
        resolve_credential: A :class:`~mindsos_llm.credentials.Resolver`. ⚠ Not
            a credential — see that module for why the indirection is the
            mechanism rather than a style choice.
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
    if not tool_name or not tool_description:
        raise ValueError("the forced tool needs a name and a description")
    endpoint = require_https(endpoint)
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
        request = urllib.request.Request(
            endpoint,
            data=body,
            method="POST",
            headers=build_headers(
                resolver,
                CREDENTIAL_HEADER,
                {
                    "content-type": "application/json",
                    "anthropic-version": API_VERSION,
                },
            ),
        )
        response = send(
            open_url, request, timeout_s=timeout_s, header_name=CREDENTIAL_HEADER
        )
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


__all__ = [
    "API_VERSION",
    "CREDENTIAL_HEADER",
    "ENDPOINT",
    "SUPPORTED_LEVELS",
    "VENDOR_ID",
    "build_transport",
]
