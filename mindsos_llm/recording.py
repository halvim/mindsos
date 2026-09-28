"""Recorded model responses + the deterministic request key.

A recorded response set is a JSON object mapping a :func:`request_key` to
one response payload. The key is a hash of everything that materially
determines a reading, **BY CONTENT** (plan R22, R30; ADR-0210 am-7): the
digest of the prompt WORDS sent, the digest of the extraction schema, the
forced tool's name and sentence, the token ceiling, the model and its
version, the sampling temperature, and the exact source text. Two runs
that agree on all of those are the same question, so they replay to the
same answer; a change to any of them is a different question and misses,
which is the intended behaviour (a re-worded prompt must not silently
reuse the previous run's reading).

⚠ **v1 did not meet its own sentence.** It hashed the prompt's NAME and
version, not its words, and omitted the schema, the tool framing and the
token ceiling — so a prompt edited in place under the same version, or a
changed schema, replayed the old answer as if nothing had changed. v2
hashes content, and the prompt's name leaves the key (R30): the same words
under two names are one question. The answer still stamps the name.

Nothing here interprets a response. Shape validation and admissibility
are the capacity body's job.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from .exceptions import RecordedResponseMiss

#: Bumped when the key's input tuple changes, so an old recording set
#: misses loudly instead of matching a key that now means something else.
#: ⚠ Every answer STAMPS the version its key was computed under (plan R34),
#: so a set's version is read off its payloads rather than off this constant.
KEY_SCHEMA_VERSION = "2"

#: The version a payload with no ``key_schema_version`` stamp was keyed under.
#: Not an inference from absence: the stamp was introduced WITH v2, so every
#: unstamped payload predates it, and v1 is the only key that existed then.
UNSTAMPED_KEY_SCHEMA_VERSION = "1"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def text_digest(text: str) -> str:
    """``sha256:<hex>`` of ``text``'s UTF-8 bytes — the digest of prompt words.

    Public because the check it feeds lives elsewhere: whoever verifies that a
    shown prompt edition is the one that ran (plan R24) re-hashes the edition's
    text with THIS function and compares it with the answer's stamp.
    """
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def schema_digest(schema: Optional[Mapping[str, Any]]) -> str:
    """``sha256:<hex>`` of the schema's CANONICAL JSON (sorted keys).

    Key order is wire syntax (plan R21: the transport owns serialisation), so
    two schemas that differ only in key order are one schema here.
    """
    return "sha256:" + hashlib.sha256(_canonical(schema).encode("utf-8")).hexdigest()


def request_key(
    *,
    prompt_digest: str,
    schema_digest: str,
    tool_name: str,
    tool_description: str,
    max_tokens: int,
    model_id: str,
    model_version: str,
    temperature: float,
    source_text: str,
) -> str:
    """Deterministic key over everything that determines a reading, by content."""
    payload = json.dumps(
        {
            "schema": KEY_SCHEMA_VERSION,
            "prompt_digest": prompt_digest,
            "schema_digest": schema_digest,
            "tool_name": tool_name,
            "tool_description": tool_description,
            "max_tokens": int(max_tokens),
            "model_id": model_id,
            "model_version": model_version,
            "temperature": float(temperature),
            "source_text": source_text,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def what_was_asked(
    *,
    prompt_iri: str,
    prompt_version: int,
    prompt_digest: str,
    extraction_schema: Optional[Mapping[str, Any]],
    tool_name: str,
    tool_description: str,
    max_tokens: int,
    model_id: str,
    model_version: str,
    temperature: float,
    source_text: str,
) -> Dict[str, Any]:
    """The stamps that name a question BY CONTENT (plan R20–R22, R32, R34).

    ONE function for every client, so a live answer and a replayed one cannot
    describe the same question differently. The source text is hashed into
    ``request_key`` and never stamped (it is the customer's document; R27
    finds it in the grounding graph). The schema is stamped as a digest; its
    text reaches a record from the reader, which holds it (R23).
    """
    sdigest = schema_digest(extraction_schema)
    return {
        "model_id": model_id,
        "model_version": model_version,
        "prompt_iri": prompt_iri,
        "prompt_version": int(prompt_version),
        "prompt_digest": prompt_digest,
        "schema_digest": sdigest,
        "tool_name": tool_name,
        "tool_description": tool_description,
        "max_tokens": int(max_tokens),
        "temperature": float(temperature),
        "request_key": request_key(
            prompt_digest=prompt_digest,
            schema_digest=sdigest,
            tool_name=tool_name,
            tool_description=tool_description,
            max_tokens=max_tokens,
            model_id=model_id,
            model_version=model_version,
            temperature=temperature,
            source_text=source_text,
        ),
        "key_schema_version": KEY_SCHEMA_VERSION,
    }


class RecordingStore:
    """An in-memory, file-backed set of recorded model responses.

    ``responses`` maps ``request_key`` -> response payload (a plain
    mapping; see ``comprehension_v0`` for the shape a reader expects).
    """

    def __init__(self, responses: Optional[Mapping[str, Any]] = None) -> None:
        self._responses: Dict[str, Any] = dict(responses or {})

    @classmethod
    def from_path(cls, path: Any) -> "RecordingStore":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(
                f"recording set at {path!r} must be a JSON object mapping "
                f"request_key -> response, got {type(data).__name__}"
            )
        return cls(data)

    def to_json(self) -> str:
        return json.dumps(self._responses, sort_keys=True, indent=2, ensure_ascii=False)

    def put(self, key: str, response: Mapping[str, Any]) -> None:
        self._responses[key] = dict(response)

    def get(self, key: str) -> Mapping[str, Any]:
        try:
            return self._responses[key]
        except KeyError:
            # Fixed prose + structured attributes: the key is a hash and
            # the set size is ours, and both reach a customer page through
            # ``stopped_detail`` if they are put in the message (see
            # ``exceptions``' module docstring).
            raise RecordedResponseMiss(
                request_key=key, set_size=len(self._responses)
            ) from None

    def __len__(self) -> int:
        return len(self._responses)

    def __contains__(self, key: object) -> bool:
        return key in self._responses


__all__ = [
    "KEY_SCHEMA_VERSION",
    "UNSTAMPED_KEY_SCHEMA_VERSION",
    "RecordingStore",
    "request_key",
    "schema_digest",
    "text_digest",
    "what_was_asked",
]
