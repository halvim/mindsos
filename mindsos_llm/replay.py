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

**A replay poses its question BY DIGEST** (plan R31, ADR-0210 am-7). The v2
key hashes the digest of the prompt words, not the words, so a replay needs
only the digest — from one of two sources, and exactly one:

* ``resolve_prompt`` — the deployment replaying its OWN set hashes its
  CURRENT words, so a prompt reworded since the capture misses. That is the
  key's purpose (``recording.py``), and a replay that took the digest from
  the file would silently reuse the old reading.
* ``prompt_digests`` — a THIRD PARTY replaying an export gets the digests
  from :meth:`~.recorded_sets.ImportedSet.replay_config`, derived from the
  set's payloads. It reproduces what was recorded without being handed the
  prompt words — portability is the export's job (ADR-0210 am-6) — and it
  stands where ``model_id`` always has: reported as configured, not checked.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Optional, Tuple

from .exceptions import RecordedResponseMiss
from .recording import RecordingStore, text_digest, what_was_asked
from .seam import require_prompt_text


class RecordedLLM:
    """Answer readings from a recorded response set.

    ``model_id`` / ``model_version`` are the identity of the model whose
    answers were recorded — they are reported, not consulted, so a Record
    names the model that actually produced the reading. The tool framing is
    configured the same way and is part of the key (plan R22).
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
        tool_name: str,
        tool_description: str,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        resolve_prompt: Optional[Callable[..., str]] = None,
        prompt_digests: Optional[Mapping[Tuple[str, int], str]] = None,
    ) -> None:
        if (resolve_prompt is None) == (prompt_digests is None):
            raise ValueError(
                "exactly one of resolve_prompt (a deployment replaying its own "
                "set, hashing its current words) or prompt_digests (a third "
                "party replaying an export, from ImportedSet.replay_config)"
            )
        if not tool_name or not tool_description:
            raise ValueError("the forced tool needs a name and a description")
        self._store = store
        self._model_id = model_id
        self._model_version = model_version
        self._tool_name = str(tool_name)
        self._tool_description = str(tool_description)
        self._max_tokens = int(max_tokens)
        self._temperature = float(temperature)
        self._resolve_prompt = resolve_prompt
        self._prompt_digests = (
            None
            if prompt_digests is None
            else {(str(i), int(v)): str(d) for (i, v), d in prompt_digests.items()}
        )

    def _prompt_digest(self, prompt_iri: str, prompt_version: int) -> Optional[str]:
        if self._resolve_prompt is not None:
            return text_digest(
                require_prompt_text(
                    self._resolve_prompt(
                        prompt_iri=prompt_iri, prompt_version=prompt_version
                    )
                )
            )
        return self._prompt_digests.get((str(prompt_iri), int(prompt_version)))

    def read(
        self,
        *,
        prompt_iri: str,
        prompt_version: int,
        source_text: str,
        extraction_schema: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        digest = self._prompt_digest(prompt_iri, prompt_version)
        if digest is None:
            # The set holds no answer to any question under this prompt: a
            # miss, said the way every other miss is said.
            raise RecordedResponseMiss(request_key="", set_size=len(self._store))
        stamps = what_was_asked(
            prompt_iri=prompt_iri,
            prompt_version=prompt_version,
            prompt_digest=digest,
            extraction_schema=extraction_schema,
            tool_name=self._tool_name,
            tool_description=self._tool_description,
            max_tokens=self._max_tokens,
            model_id=self._model_id,
            model_version=self._model_version,
            temperature=self._temperature,
            source_text=source_text,
        )
        payload = dict(self._store.get(stamps["request_key"]))
        # Provenance is stamped here, never taken from the recorded blob —
        # a recording file cannot claim to be a live reading, and cannot
        # claim a different model, prompt or framing than the one configured.
        payload.update(stamps)
        payload["recorded"] = True
        payload["mode"] = self.MODE
        # None, not the capture-time level: this run used no credential.
        payload["credential_level"] = None
        return payload


__all__ = ["RecordedLLM"]
