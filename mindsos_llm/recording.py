"""Recorded model responses + the deterministic request key.

A recorded response set is a JSON object mapping a :func:`request_key` to
one response payload. The key is a hash of everything that materially
determines a reading — the prompt and its version, the model and its
version, the sampling temperature, and the exact source text. Two runs
that agree on all of those are the same question, so they replay to the
same answer; a change to any of them is a different question and misses,
which is the intended behaviour (a re-worded prompt must not silently
reuse the previous run's reading).

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
KEY_SCHEMA_VERSION = "1"


def request_key(
    *,
    prompt_iri: str,
    prompt_version: int,
    model_id: str,
    model_version: str,
    temperature: float,
    source_text: str,
) -> str:
    """Deterministic key over everything that determines a reading."""
    payload = json.dumps(
        {
            "schema": KEY_SCHEMA_VERSION,
            "prompt_iri": prompt_iri,
            "prompt_version": int(prompt_version),
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
            raise RecordedResponseMiss(
                f"no recorded response for {key}. The recording set holds "
                f"{len(self._responses)} response(s). A miss means the prompt, "
                f"its version, the model, the temperature or the source text "
                f"changed since the set was recorded — re-record rather than "
                f"loosening the key."
            ) from None

    def __len__(self) -> int:
        return len(self._responses)

    def __contains__(self, key: object) -> bool:
        return key in self._responses


__all__ = ["KEY_SCHEMA_VERSION", "RecordingStore", "request_key"]
