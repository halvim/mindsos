"""dr_transport — the piece that touches the network, and it lives HERE by design.

`mindsos_capacity.llm.live.LiveLLM` takes a **deployment-supplied callable** and
the callable was never written. This module is that callable, for this demo, and
it is in `decision_records_demo/` for two reasons that are the same reason: no
vendor SDK ships inside MindsOS (`live.py`'s own docstring), and a demo may never
edit `mindsos_*` (RULES §3).

**Gate 4, checked in writing before anything was written (the restated form):**
this module **registers nothing**. No `Capacity`, no `DataState`, no new capacity
CATEGORY beyond `origin_v0.DECISION_SHAPED_CATEGORIES`, and no new `FAMILY_RULES`
entry. It is a module-level factory returning a closure. Gate 4 is not engaged.
**PASS.** Imports are stdlib only, so the lane's gate condition —
`git diff --stat <pinned core tag>..HEAD -- 'mindsos_*'` printing nothing — is
unaffected.

⚠ **THIS BRANCH CANNOT IMPORT `mindsos_capacity.llm`.** The package is on `main`
and ABSENT from `dr-partial-record-confirmed`, the core this demo pins. Nothing
here imports it — not even inside a function, not even guarded by
`try/ImportError`, because `test_no_demo_module_imports_the_model_seam` is an AST
scan and it is right to be. The conformance harness
(`mindsos_capacity.llm.contract.verify_transport`) is run by the OWNER from the
`main` checkout; `README.md` carries the procedure. **Stated plainly: at step 1
this transport has no committed guard proving it satisfies the `Transport`
contract.** The nine guards below prove nine narrower things.

⚠ **THE ANSWER IS FORCED INTO A SHAPE, NOT REPAIRED INTO ONE.** The first
version of this module asked for JSON in prose and returned the model's text
verbatim. Run against a live provider it came back fenced in ```` ```json ````
**even with two explicit instructions not to** — one in the prompt, one appended
here — and `verify_transport` reported `answer_is_text_or_a_mapping — returned
text that does not decode to a JSON object`. Found by running it; a code fence
is not the model malforming its answer, so refusing on it would have made every
reading a refusal for the wrong reason.

**The rejected fix, recorded because it was this lane's first answer.** Stripping
a whole-string fence in the transport. It is a silent repair layer between the
model and every check that follows, it edits the model's output before anything
verifies it, and it does not generalise — trailing prose, *"Here is the JSON:"*
and smart quotes are each another quiet patch. **The demo's argument is that
nothing is fixed up on our side.**

**What replaces it:** the extraction schema is sent as a TOOL and the tool is
FORCED (`tool_choice`). The provider guarantees a structured object, so no fence
can occur, nothing is stripped and nothing is guessed. What reaches verification
is what the model produced. ⟹ All remaining risk sits where it actually lives —
the value↔quote binding (`dr-value-span-binding`) — instead of being mixed with
format noise.

**Consequences, stated rather than discovered later.**

* This returns a `Mapping`, not text. That is explicitly allowed — `Transport` is
  typed `Union[Mapping[str, Any], str]` and `live.py` says the transport may
  return *"a mapping it decoded itself"*. **S-2 is not violated:** S-2 puts the
  decoding of an ambiguous TEXT reply in the package where the failure is typed,
  and a forced tool reply is not an ambiguous text reply.
* `MalformedResponse` can therefore no longer fire from decoding. That case is
  **eliminated at source, not hidden**: a tool reply missing a field reaches
  `comprehension_v0` and becomes `REFUSAL_FIELD_ABSENT`, which is where a finding
  about the answer belongs.
* **There is no free-text fallback.** A call with no `extraction_schema` has
  nothing to force, and falling back would silently reintroduce the fence on
  exactly the path nobody is watching. It raises, and a guard pins it.

**NO WORDS LIVE IN THIS MODULE.** Not the prompt, not the tool's description.
`prompt_iri` is carried for provenance only — `grep -rn 'prompt_iri'
mindsos_capacity/` finds recording, replay, live, contract and comprehension, and
not one of them resolves it to words. Plan §0.4 item 3 shows the prompt ON SCREEN
IN FULL and invites the room to improve it; anything inlined here would make that
mean *read our source*. The prompt arrives through `resolve_prompt` and the tool
description through `tool_description`, both injected. A guard pins the first.

**FAILURE IS FIXED PROSE, and the credential is the hard half.** Every failure
raises :class:`TransportCallFailed` with a sentence naming no key, no endpoint and
no model. ``LiveLLM`` wraps whatever raises into ``LLMCallFailed`` with the
provider exception on ``__cause__`` — the seam's design, and it makes the CAUSE
chain a developer surface. Two obligations, guarded differently on purpose:

* **the API key appears NOWHERE** — not in a return value, not in this module's
  exception, not anywhere in its ``__cause__`` chain;
* **the model id and the endpoint appear nowhere in the exception this module
  raises**, and that guard says in its own body that it does not follow the cause
  chain, because `urllib`'s `HTTPError` names the URL it failed on and
  suppressing it would destroy the only debugging surface there is. Plan §0.5
  item 8 is about a RENDERED PAGE; a traceback is not one.
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
#: names no vendor, no model, no URL and no internal token.
UNREACHABLE = (
    "the reading service could not be reached. This is a fault on our side "
    "and is never a finding about the case."
)

#: Same discipline, different cause: the provider answered with nothing this
#: transport can find an answer inside. NOT the model malforming a reply — a
#: forced tool cannot produce one.
NO_ANSWER = (
    "the reading service replied without an answer in it. This is a fault on "
    "our side and is never a finding about the case."
)

#: A deployment bug, and it is deliberately not survivable. See the module
#: docstring: a free-text fallback reintroduces the fence on the one path
#: nobody watches.
NO_SCHEMA = (
    "a reading was requested with no shape to return it in. This is a fault "
    "on our side and is never a finding about the case."
)


class TransportCallFailed(RuntimeError):
    """The call did not produce an answer. ``LiveLLM`` turns this into an outage."""


class TransportSchemaRequired(TransportCallFailed):
    """No ``extraction_schema``, so no shape could be forced.

    ⚠ **``LiveLLM`` will classify this as an outage, and that is a
    misclassification** — it is a deployment bug, and the seam's own
    ``TransportContractError`` is the right class for it. That class lives in
    `mindsos_capacity.llm`, which this branch cannot import. Recorded here
    rather than papered over; it becomes reachable at step 3's pin bump. It is
    deterministic, so a guard prevents it from ever shipping.
    """


def build_transport(
    *,
    api_key: str,
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
        api_key: The credential. Kept in the closure and never returned,
            printed, or placed on an exception — the reason the seam takes a
            callable rather than a config block (§6.4).
        model_id: Passed to the provider. ``LiveLLM`` stamps its own copy onto
            the payload for provenance; this one only reaches the wire.
        resolve_prompt: ``(prompt_iri, prompt_version) -> str``. **The only
            source of prompt words in this module.** Step 1 supplies a
            one-entry resolver from the smoke; step 3 replaces it with the
            stored, dated, printable file the room is shown.
        tool_name, tool_description: The forced tool's identity and its
            sentence. Injected for the same reason as the prompt: no words
            live in this module.
        opener: Defaults to :func:`urllib.request.urlopen`. Injected so every
            guard runs with no network — the build gate has neither network
            nor key.
    """
    if not api_key:
        raise ValueError("no credential was supplied to the transport")
    if not tool_name or not tool_description:
        raise ValueError("the forced tool needs a name and a description")
    open_url = opener or urllib.request.urlopen

    def transport(
        *,
        prompt_iri: str,
        prompt_version: int,
        source_text: str,
        extraction_schema: Optional[Mapping[str, Any]],
        timeout_s: float,
    ) -> Mapping[str, Any]:
        # ⚠ **No defaults on any of the five.** ``LiveLLM`` passes all five on
        # every call, and a default here would let a caller that forgot the
        # document get an answer about nothing instead of a TypeError. A guard
        # binds the call with each key removed in turn and requires failure.
        system = resolve_prompt(prompt_iri=prompt_iri, prompt_version=prompt_version)
        if not isinstance(system, str) or not system.strip():
            raise TransportCallFailed(NO_ANSWER)
        if not extraction_schema:
            # No fallback. See the module docstring.
            raise TransportSchemaRequired(NO_SCHEMA)
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
                        "input_schema": dict(extraction_schema),
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
            # developer. The credential is in neither, and a guard walks the
            # whole chain to say so.
            raise TransportCallFailed(UNREACHABLE) from exc
        status = getattr(response, "status", None)
        if status is None:
            status = getattr(response, "code", 200)
        if not 200 <= int(status) < 300:
            # The OTHER door out of this predicate. A transport that read the
            # body here would hand a provider's error page to a reader.
            raise TransportCallFailed(UNREACHABLE)
        try:
            envelope = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise TransportCallFailed(NO_ANSWER) from exc
        for block in envelope.get("content") or []:
            if not isinstance(block, Mapping):
                continue
            if block.get("type") != "tool_use" or block.get("name") != tool_name:
                # A model may emit commentary beside the tool call. It is not
                # the answer and it is never returned as one.
                continue
            answer = block.get("input")
            if not isinstance(answer, Mapping):
                raise TransportCallFailed(NO_ANSWER)
            # Unaltered: no key renamed, no field added, no value coerced.
            return answer
        raise TransportCallFailed(NO_ANSWER)

    return transport


__all__ = [
    "API_VERSION",
    "ENDPOINT",
    "NO_ANSWER",
    "NO_SCHEMA",
    "UNREACHABLE",
    "TransportCallFailed",
    "TransportSchemaRequired",
    "build_transport",
]
