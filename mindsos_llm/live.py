"""Live and capture modes.

``RecordedLLM`` (``replay.py``) answers from a saved file. These two are
the other half:

* :class:`LiveLLM` — calls a real model through a **deployment-supplied
  transport**. No provider SDK ships in this repo: the deployment passes
  a callable, so the vendor choice is not baked into core and swapping
  providers changes one line at boot.
* :class:`CapturingLLM` — wraps any LLM and saves what came back, keyed
  the same way :class:`RecordedLLM` looks it up. This is how a recorded
  set is produced: run live once and keep the answers. Hand-writing that
  file would mean hand-writing the model's answers, which is the failure
  mode the whole seam exists to prevent.

**Failure is loud.** A transport failure raises :class:`LLMCallFailed`;
there is no retry and no fallback to a saved answer. A silent fallback
would let a run present a stale reading as a fresh one. A batch caller
decides what a failed case means; this layer will not decide it quietly.

**A call ceiling is mandatory.** ``max_calls`` bounds one dispatcher's
lifetime. Without it a batch over a few hundred historical decisions can
spend without limit before anyone notices.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Optional

from .exceptions import LLMCallBudgetExceeded, LLMCallFailed
from .recording import RecordingStore, request_key

#: ``(prompt_iri, prompt_version, source_text, extraction_schema, timeout_s)``
#: -> the model's parsed response mapping. Supplied by the deployment.
Transport = Callable[..., Mapping[str, Any]]


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
            raise LLMCallBudgetExceeded(
                f"call ceiling of {self._max_calls} reached. Raise max_calls "
                f"deliberately rather than by default — this bound is what "
                f"stops a batch run spending without anyone noticing."
            )
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
            raise LLMCallFailed(
                f"the model call for {prompt_iri!r} v{prompt_version} failed: "
                f"{type(exc).__name__}: {exc}. Not retried and not answered "
                f"from a saved response — a silent fallback would present a "
                f"stale reading as a fresh one."
            ) from exc
        if not isinstance(response, Mapping):
            raise LLMCallFailed(
                f"transport returned {type(response).__name__}, expected a mapping"
            )
        payload = dict(response)
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
    """Wrap an LLM and save every answer into a :class:`RecordingStore`.

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


__all__ = ["CapturingLLM", "LiveLLM", "Transport"]
