"""Live and capture modes.

``RecordedLLM`` (``replay.py``) answers from a saved file. These two are
the other half:

* :class:`LiveLLM` — calls a real model through a **deployment-supplied
  transport**. No provider SDK ships in this repo: the deployment passes
  a callable, so the vendor choice is not baked into core and swapping
  providers changes one line at boot.
* :class:`CapturingLLM` — wraps any client and saves what came back,
  keyed the way :class:`~.replay.RecordedLLM` looks it up. This is how a
  recorded set is produced: run live once and keep the answers.
  Hand-writing that file would mean hand-writing the model's answers,
  which is the failure mode the whole seam exists to prevent.

**Failure is loud, and it is classified.** A transport that RAISES gives
:class:`~.exceptions.LLMCallFailed` — our outage, a stop, never a finding
about the customer's case. A transport that RETURNS text we cannot decode
gives :class:`~.exceptions.MalformedResponse` — a finding about the
answer, which the reader turns into a refusal. A transport that returns
something its contract forbids gives
:class:`~.exceptions.TransportContractError` — a deployment bug, which is
neither. Three failures, three meanings; collapsing them is how a page
ends up blaming a customer's document for our configuration.

**Decoding lives HERE, not in the transport (S-2, ruled 2026-08-14).**
The transport may return a mapping it decoded itself or the raw text the
model produced. Text is decoded in this package, where the failure is
typed and tested, rather than in somebody's unwritten, unowned function.

**A call ceiling is mandatory.** ``max_calls`` bounds one client's
lifetime. Without it a batch over a few hundred historical decisions can
spend without limit before anyone notices.

**Mode is a property of the CLASS, never an argument** (ADR-0210
decision 5). ``recorded`` has always been stamped this way — hardcoded
``False`` here and ``True`` in :mod:`.replay`, never passed in — and mode
follows the same rule for the same reason: a mode a caller can pass is a
mode a caller can forge, and an answer stamped ``replay`` by a client
that just called a provider is a lie no later check can catch. Each
client declares its own :attr:`MODE` and :data:`~.client.MODES` is the
union of the three, so the closed set cannot drift from the classes that
serve it.

**The credential level is pushed in, and there is no default** (ADR-0210
decision 6). L0 owns the level and hands it down at client construction
(:mod:`.client`); this class re-publishes it onto the answer so the
answer states the terms it was obtained under. It is ``Optional`` because
``None`` is a real value — a probe over somebody's transport
(:mod:`.contract`) genuinely has no level — but it has **no default**,
because a level nobody chose is the "optional supplied" shape this
package refuses everywhere else. A caller must decide; it may decide
``None``.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Mapping, Optional, Tuple, Union

import inspect

from .exceptions import (
    LLMCallBudgetExceeded,
    LLMCallFailed,
    MalformedResponse,
    TransportContractError,
    TransportSignatureError,
)
from .recording import RecordingStore, request_key
from .seam import require_prompt_text

#: The call a transport receives: **everything the model receives**, and
#: nothing that only names it (plan R21, ADR-0210 am-7). The transport adds
#: wire syntax and the credential; it resolves no prompt and holds no model
#: setting of its own. ``prompt_iri`` / ``prompt_version`` are NOT here — they
#: name the words, and a transport that could see the name could fetch its
#: own words, which is the defect R21 closes.
TRANSPORT_CALL_KEYS: Tuple[str, ...] = (
    "prompt_text",
    "source_text",
    "extraction_schema",
    "tool_name",
    "tool_description",
    "model_id",
    "temperature",
    "max_tokens",
    "timeout_s",
)

#: ``**TRANSPORT_CALL_KEYS`` -> the model's answer, EITHER already decoded
#: into a mapping OR the raw text the model produced (S-2). Supplied by the
#: deployment; see :mod:`mindsos_llm.contract` for the checks a transport has
#: to pass.
Transport = Callable[..., Union[Mapping[str, Any], str]]


def decode_response(response: Union[Mapping[str, Any], str, Any]) -> Mapping[str, Any]:
    """Normalise what a transport returned into a mapping (S-2).

    A mapping passes through. Text is JSON-decoded here. Anything else is
    a contract violation, not an answer.

    Raises :class:`~.exceptions.MalformedResponse` when text will not
    decode, or decodes to something that is not an object — both are the
    MODEL failing to answer in the shape it was asked for, and the raw
    words are retained on the exception so the refusal can carry them.
    Raises :class:`~.exceptions.TransportContractError` when the
    transport returned neither text nor a mapping, which is a bug in
    deployment code and must not be reported as either an outage or a bad
    answer.
    """
    if isinstance(response, Mapping):
        return response
    if isinstance(response, str):
        try:
            decoded = json.loads(response)
        except (ValueError, TypeError) as exc:
            raise MalformedResponse(raw=response) from exc
        if not isinstance(decoded, Mapping):
            raise MalformedResponse(raw=response)
        return decoded
    raise TransportContractError(
        violation=f"returned {type(response).__name__}, expected text or a mapping"
    )


def _assert_binds(transport, kwargs) -> None:
    """Refuse a transport that will not accept the specified call.

    Checked BEFORE calling, so that a ``TypeError`` from a mis-declared
    signature is a deployment bug and a ``TypeError`` from inside a
    correct transport is a real failure. Without the split they are the
    same exception at the same catch, and the first was reported as an
    outage — see :class:`TransportSignatureError`.

    A callable whose signature cannot be introspected at all (a C
    builtin) is allowed through: unknown is not the same as wrong, and
    the call itself is the next check.
    """
    try:
        signature = inspect.signature(transport)
    except (TypeError, ValueError):  # pragma: no cover — exotic callables
        return
    try:
        signature.bind(**kwargs)
    except TypeError as exc:
        raise TransportSignatureError(
            violation=f"does not accept the specified call ({exc})"
        ) from exc


class LiveLLM:
    """Consult a real model through a deployment-supplied transport.

    ⚠ **The client resolves and hands over everything the model receives**
    (plan R21, ADR-0210 am-7): the prompt words through ``resolve_prompt``,
    and the tool framing, model id, temperature and token ceiling it was
    built with. They used to be split — the prompt resolver and the framing
    lived in the adapter, and the model id and temperature were held twice,
    here and there, with nothing checking the two agreed. Held once, here,
    every value this class stamps is the value it sent.
    """

    #: Stamped on every answer this class produces. A class attribute
    #: rather than an argument — see the module docstring.
    MODE = "live"

    def __init__(
        self,
        transport: Transport,
        *,
        model_id: str,
        model_version: str,
        credential_level: Optional[int],
        resolve_prompt: Callable[..., str],
        tool_name: str,
        tool_description: str,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        timeout_s: float = 30.0,
        max_calls: int = 200,
    ) -> None:
        if not callable(resolve_prompt):
            raise TypeError("resolve_prompt must be a callable (prompt_iri, prompt_version) -> str")
        if not tool_name or not tool_description:
            raise ValueError("the forced tool needs a name and a description")
        self._transport = transport
        self._resolve_prompt = resolve_prompt
        self._tool_name = str(tool_name)
        self._tool_description = str(tool_description)
        self._max_tokens = int(max_tokens)
        self._model_id = model_id
        self._model_version = model_version
        self._credential_level = credential_level
        self._temperature = float(temperature)
        self._timeout_s = float(timeout_s)
        self._max_calls = int(max_calls)
        self._calls = 0

    @property
    def calls_made(self) -> int:
        return self._calls

    def read(
        self,
        *,
        prompt_iri: str,
        prompt_version: int,
        source_text: str,
        extraction_schema: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        if self._calls >= self._max_calls:
            raise LLMCallBudgetExceeded(max_calls=self._max_calls)
        self._calls += 1
        try:
            # Resolved HERE, inside the classified failure: a resolver that
            # raises is our configuration failing, exactly as it was when the
            # adapter called it, and it reaches the caller as an outage.
            prompt_text = require_prompt_text(
                self._resolve_prompt(
                    prompt_iri=prompt_iri, prompt_version=prompt_version
                )
            )
        except Exception as exc:
            raise LLMCallFailed() from exc
        call = dict(
            prompt_text=prompt_text,
            source_text=source_text,
            extraction_schema=extraction_schema,
            tool_name=self._tool_name,
            tool_description=self._tool_description,
            model_id=self._model_id,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            timeout_s=self._timeout_s,
        )
        _assert_binds(self._transport, call)
        try:
            response = self._transport(**call)
        except Exception as exc:
            # Fixed prose, provider exception on ``__cause__``. See
            # ``exceptions``' module docstring — this message is printed
            # on a customer's page.
            raise LLMCallFailed() from exc
        payload = dict(decode_response(response))
        # Provenance is stamped here, never taken from the response.
        payload["model_id"] = self._model_id
        payload["model_version"] = self._model_version
        payload["prompt_iri"] = prompt_iri
        payload["prompt_version"] = int(prompt_version)
        payload["temperature"] = self._temperature
        payload["request_key"] = request_key(
            prompt_iri=prompt_iri,
            prompt_version=prompt_version,
            model_id=self._model_id,
            model_version=self._model_version,
            temperature=self._temperature,
            source_text=source_text,
        )
        payload["recorded"] = False
        payload["mode"] = self.MODE
        payload["credential_level"] = self._credential_level
        return payload


class CapturingLLM:
    """Wrap a client and save every answer into a :class:`RecordingStore`.

    Used to build a recorded set from a real run. The saved copy is what a
    later ``RecordedLLM`` replays.

    ⚠ **Two provenance fields, deliberately opposite treatment.**
    ``recorded`` passes through unchanged as ``False``, because it answers
    *"was this answer replayed?"* and this one was not — it came off a
    provider a moment ago. ``mode`` answers a different question, *"which
    of the three modes produced this?"*, and the answer is ``capture``:
    the run was a capture run, and no other object in the tree knows that
    (:class:`LiveLLM` cannot — it is the same class whether or not it is
    wrapped). So this class overrides ``mode`` and only ``mode``.

    ⚠ **The override happens BEFORE the store write, and the order is the
    claim.** The saved copy is the artifact a third party replays and
    exports; a copy stamped ``live`` would say a capture run never
    happened, while the caller's returned copy said otherwise. Two copies
    of one answer disagreeing about how it was obtained is exactly the
    provenance defect this module exists to prevent, so the ordering is
    guarded on both doors rather than left to reading order.
    """

    #: Stamped on every answer that passes through — see above.
    MODE = "capture"

    def __init__(self, inner: Any, store: RecordingStore) -> None:
        self._inner = inner
        self._store = store

    @property
    def store(self) -> RecordingStore:
        return self._store

    def read(self, **kwargs: Any) -> Mapping[str, Any]:
        response = dict(self._inner.read(**kwargs))
        response["mode"] = self.MODE
        key = response.get("request_key")
        if key:
            self._store.put(key, response)
        return response


__all__ = [
    "CapturingLLM",
    "LiveLLM",
    "TRANSPORT_CALL_KEYS",
    "Transport",
    "decode_response",
]
