"""dr_transport — the piece that touches the network, and it lives HERE by design.

`mindsos_capacity.llm.live.LiveLLM` takes a **deployment-supplied callable**
and the callable was never written. This module is that callable, for this
demo, and it is in `decision_records_demo/` for two reasons that are the same
reason: no vendor SDK ships inside MindsOS (`live.py`'s own docstring), and a
demo may never edit `mindsos_*` (RULES §3).

**Gate 4, checked in writing before anything is written (the restated form):**
this module **registers nothing**. No `Capacity`, no `DataState`, no new
capacity CATEGORY beyond `origin_v0.DECISION_SHAPED_CATEGORIES`, and no new
`FAMILY_RULES` entry. It is a module-level factory returning a closure. Gate 4
is not engaged. **PASS.** Imports are stdlib only, so the lane's gate condition
— `git diff --stat <pinned core tag>..HEAD -- 'mindsos_*'` printing nothing —
is unaffected.

⚠ **THIS BRANCH CANNOT IMPORT `mindsos_capacity.llm`.** The package is on
`main` and ABSENT from `dr-partial-record-confirmed`, the core this demo pins
(`git ls-tree`, off the tree). So nothing here imports it, and the conformance
harness that exists for exactly this purpose —
`mindsos_capacity.llm.contract.verify_transport` — is run by the OWNER from the
`main` checkout as evidence (plan §0.5 item 9). **Stated plainly: at step 1 this
transport has no committed guard proving it satisfies the `Transport`
contract.** The seven guards below prove seven narrower things.

**THE S-2 LINE, and it is easy to put in the wrong place.** S-2 (ruled
2026-08-14) says decoding lives in `mindsos_capacity.llm`, not in the transport
— *"Text is decoded in this package, where the failure is typed and tested,
rather than in somebody's unwritten, unowned function."* That rule is about the
MODEL'S ANSWER. It is not about the PROVIDER'S ENVELOPE, which is vendor shape
and belongs nowhere else. So:

* the envelope IS unwrapped here — one provider's JSON, one provider's content
  blocks — because `LiveLLM` must not learn a vendor's wire format;
* the model's answer is returned **verbatim, as text, undecoded**, so that a
  reply the model malformed becomes `MalformedResponse` in the package that
  types it, and never a `ValueError` from here.

**NO PROMPT TEXT LIVES IN THIS MODULE.** `prompt_iri` is carried for provenance
only — `grep -rn 'prompt_iri' mindsos_capacity/` finds recording, replay, live,
contract and comprehension, and **not one of them resolves it to words**. The
prompt is therefore deployment-owned, and plan §0.4 item 3 says it is SHOWN ON
SCREEN IN FULL and the room is invited to improve it. A prompt inlined here
would make "shown in full" mean "read our source code". So the prompt arrives
through an injected `resolve_prompt`, and the stored, dated, printable prompt
file lands with step 3 beside the tier policy. A guard pins this.

**FAILURE IS FIXED PROSE, and the credential is the hard half.** Every failure
raises :class:`TransportCallFailed` with a fixed sentence naming no key, no
endpoint and no model. ``LiveLLM`` wraps whatever raises into ``LLMCallFailed``
with the provider exception on ``__cause__`` — that is the seam's design, and
it means the CAUSE chain is a developer surface. Two different obligations,
and they are guarded differently on purpose:

* **the API key appears NOWHERE** — not in a return value, not in this
  module's exception, not anywhere in its ``__cause__`` chain;
* **the model id and the endpoint appear nowhere in the exception this module
  raises**, and the guard says in its own body that it does not follow the
  cause chain, because `urllib`'s own `HTTPError` names the URL it failed on
  and suppressing that would destroy the only debugging surface there is.
  Plan §0.5 item 8 is about a RENDERED PAGE; a traceback is not one.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Callable, Mapping, Optional

#: Anthropic's Messages endpoint. Never printed, never rendered, never in an
#: exception this module raises.
ENDPOINT = "https://api.anthropic.com/v1/messages"

#: The wire version header the Messages API requires.
API_VERSION = "2023-06-01"

#: Fixed prose. This sentence can reach a page through ``LLMCallFailed``, so it
#: names no vendor, no model, no URL and no internal token — the rule
#: ``mindsos_capacity.llm.exceptions`` states for the client's errors.
UNREACHABLE = (
    "the reading service could not be reached. This is a fault on our side "
    "and is never a finding about the case."
)

#: Same discipline, different cause: the provider answered with something this
#: transport cannot find an answer inside. Not the model malforming its reply —
#: that is the package's ``MalformedResponse`` and it must reach it as text.
NO_ANSWER = (
    "the reading service replied without an answer in it. This is a fault on "
    "our side and is never a finding about the case."
)


class TransportCallFailed(RuntimeError):
    """The call did not produce text. ``LiveLLM`` turns this into an outage."""


def build_transport(
    *,
    api_key: str,
    model_id: str,
    resolve_prompt: Callable[..., str],
    max_tokens: int = 1024,
    temperature: float = 0.0,
    endpoint: str = ENDPOINT,
    opener: Optional[Callable[..., Any]] = None,
) -> Callable[..., str]:
    """Build the callable ``LiveLLM`` will hold.

    Args:
        api_key: The credential. Kept in the closure and never returned,
            printed, or placed on an exception — the whole reason the seam
            takes a callable rather than a config block (§6.4).
        model_id: Passed to the provider. ``LiveLLM`` stamps its own copy onto
            the payload for provenance; this one only reaches the wire.
        resolve_prompt: ``(prompt_iri, prompt_version) -> str``. **The only
            source of prompt words in this module.** Step 1 supplies a
            one-entry resolver from the smoke; step 3 replaces it with the
            stored, dated, printable file the room is shown.
        opener: Defaults to :func:`urllib.request.urlopen`. Injected so every
            guard below runs with no network — the build gate has neither
            network nor key.
    """
    if not api_key:
        raise ValueError("no credential was supplied to the transport")
    open_url = opener or urllib.request.urlopen

    def transport(
        *,
        prompt_iri: str,
        prompt_version: int,
        source_text: str,
        extraction_schema: Optional[Mapping[str, Any]],
        timeout_s: float,
    ) -> str:
        # ⚠ **No defaults on any of the five.** ``LiveLLM`` passes all five on
        # every call, and a default here would let a caller that forgot the
        # document get an answer about nothing instead of a TypeError. A guard
        # binds the call with each key removed in turn and requires failure.
        system = resolve_prompt(prompt_iri=prompt_iri, prompt_version=prompt_version)
        if not isinstance(system, str) or not system.strip():
            raise TransportCallFailed(NO_ANSWER)
        if extraction_schema:
            system = (
                system
                + "\n\nReturn one JSON object in this shape and nothing else:\n"
                + json.dumps(extraction_schema, sort_keys=True)
            )
        body = json.dumps(
            {
                "model": model_id,
                "max_tokens": int(max_tokens),
                "temperature": float(temperature),
                "system": system,
                "messages": [{"role": "user", "content": source_text}],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=body,
            method="POST",
            headers={
                "content-type": "application/json",
                "anthropic-version": API_VERSION,
                "x-api-key": api_key,
            },
        )
        try:
            response = open_url(request, timeout=timeout_s)
        except Exception as exc:
            # Fixed prose out; the provider exception stays on __cause__ for a
            # developer. The credential is not in either, and a guard walks the
            # whole chain to say so.
            raise TransportCallFailed(UNREACHABLE) from exc
        status = getattr(response, "status", None)
        if status is None:
            status = getattr(response, "code", 200)
        if not 200 <= int(status) < 300:
            # The OTHER door out of this predicate. A transport that returned
            # the error body here would hand a provider's error page to a
            # reader as if it were the model's answer.
            raise TransportCallFailed(UNREACHABLE)
        try:
            envelope = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise TransportCallFailed(NO_ANSWER) from exc
        parts = [
            block.get("text")
            for block in (envelope.get("content") or [])
            if isinstance(block, Mapping) and block.get("type") == "text"
        ]
        parts = [p for p in parts if isinstance(p, str)]
        if not parts:
            raise TransportCallFailed(NO_ANSWER)
        # Verbatim, undecoded. S-2: the ANSWER is decoded in
        # ``mindsos_capacity.llm``, where the failure is typed and tested.
        return "".join(parts)

    return transport


__all__ = [
    "API_VERSION",
    "ENDPOINT",
    "NO_ANSWER",
    "UNREACHABLE",
    "TransportCallFailed",
    "build_transport",
]
