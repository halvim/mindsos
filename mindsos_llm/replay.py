"""``RecordedLLM`` — the recorded-response implementation of the handle.

Satisfies ``mindsos_capacity.context.LLMHandle`` structurally (the
Protocol is ``runtime_checkable``); no import crosses between the two
packages in either direction.

The returned payload is a plain ``Mapping`` carrying, alongside whatever
the model produced, the facts a Decision Record has to be able to state:
which model answered, which prompt and version asked, at what
temperature, under which request key, and **whether the reading was
replayed or live**. Those travel to the capacity body, which emits them
as a reading-record DataState so they land in the run's grounding graph.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from .recording import RecordingStore, request_key


class RecordedLLM:
    """Answer readings from a recorded response set.

    ``model_id`` / ``model_version`` are the identity of the model whose
    answers were recorded — they are reported, not consulted, so a Record
    names the model that actually produced the reading.
    """

    def __init__(
        self,
        store: RecordingStore,
        *,
        model_id: str,
        model_version: str,
        temperature: float = 0.0,
    ) -> None:
        self._store = store
        self._model_id = model_id
        self._model_version = model_version
        self._temperature = float(temperature)

    def read(
        self,
        *,
        prompt_iri: str,
        prompt_version: int,
        source_text: str,
        extraction_schema: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        key = request_key(
            prompt_iri=prompt_iri,
            prompt_version=prompt_version,
            model_id=self._model_id,
            model_version=self._model_version,
            temperature=self._temperature,
            source_text=source_text,
        )
        recorded = self._store.get(key)
        payload = dict(recorded)
        # Provenance is stamped here, never taken from the recorded blob —
        # a recording file cannot claim to be a live reading, and cannot
        # claim a different model than the one configured.
        payload["model_id"] = self._model_id
        payload["model_version"] = self._model_version
        payload["prompt_iri"] = prompt_iri
        payload["prompt_version"] = int(prompt_version)
        payload["temperature"] = self._temperature
        payload["request_key"] = key
        payload["recorded"] = True
        return payload


__all__ = ["RecordedLLM"]
