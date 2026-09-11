"""``RecordedLLM`` — the recorded-response implementation of the handle.

Satisfies ``mindsos_capacity.context.LLMHandle`` structurally (the
Protocol is ``runtime_checkable``); no import crosses between the two
packages in either direction.

The returned payload is a plain ``Mapping`` carrying, alongside whatever
the model produced, the facts a reader of the answer has to be able to
state without being told how the client was built: which model answered,
which prompt and version asked, at what temperature, under which request
key, **whether the reading was replayed or live**, **which mode produced
it**, and **at which credential level**. A layer above may declare any of
them as an output so they reach that layer's own records; this package
neither knows nor cares which does.

**Replay's credential level is ``None``, and that is the true value.**
A replay reaches no provider and needs no credential (:mod:`.client`
refuses one on this path), so there is no level to report. Reporting the
level the answers were *captured* under would be this class making a
claim about a run that is not the one it is serving — the same reason the
model identity below is configured rather than read out of the file. The
capture-time level is a property of the recorded SET and lives in its
export manifest, not on a replayed answer.
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

    #: Stamped on every answer this class produces. A class attribute
    #: rather than an argument — see :mod:`.live`'s module docstring.
    MODE = "replay"

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
        payload["mode"] = self.MODE
        # None, not the capture-time level: this run used no credential.
        payload["credential_level"] = None
        return payload


__all__ = ["RecordedLLM"]
