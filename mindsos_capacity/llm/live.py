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
"""

from __future__ import annotations

import json
from typing import Any, Callable, Mapping, Optional, Union

from .exceptions import (
    LLMCallBudgetExceeded,
    LLMCallFailed,
    MalformedResponse,
    TransportContractError,
)
from .recording import RecordingStore, request_key

#: ``(prompt_iri, prompt_version, source_text, extraction_schema,
#: timeout_s)`` -> the model's answer, EITHER already decoded into a
#: mapping OR the raw text the model produced (S-2). Supplied by the
#: deployment; see :mod:`mindsos_capacity.llm.contract` for the checks a
#: transport has to pass.
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
    raise TransportContractError(returned_type=type(response).__name__)


class LiveLLM:
    """Consult a real model through a deployment-supplied transport."""

    def __init__(
        self,
        transport: Transport,
        *,
        model_id: str,
        model_version: str,
        temperature: float = 0.0,
        timeout_s: float = 30.0,
        max_calls: int = 200,
    ) -> None:
        self._transport = transport
        self._model_id = model_id
        self._model_version = model_version
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
            response = self._transport(
                prompt_iri=prompt_iri,
                prompt_version=prompt_version,
                source_text=source_text,
                extraction_schema=extraction_schema,
                timeout_s=self._timeout_s,
            )
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
        return payload


class CapturingLLM:
    """Wrap a client and save every answer into a :class:`RecordingStore`.

    Used to build a recorded set from a real run. Answers pass through
    unchanged — including ``recorded: False``, because *this* run was
    live. The saved copy is what a later ``RecordedLLM`` replays.
    """

    def __init__(self, inner: Any, store: RecordingStore) -> None:
        self._inner = inner
        self._store = store

    @property
    def store(self) -> RecordingStore:
        return self._store

    def read(self, **kwargs: Any) -> Mapping[str, Any]:
        response = self._inner.read(**kwargs)
        key = response.get("request_key")
        if key:
            self._store.put(key, response)
        return response


__all__ = ["CapturingLLM", "LiveLLM", "Transport", "decode_response"]
