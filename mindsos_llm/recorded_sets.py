"""Exporting and importing a recorded set, so a third party can re-run a result.

**Why this exists, and why it is not optional.** ADR-0210 rules that recorded
response sets are per-user **L2 Local, never Global**. That is the right call
for a store — one user's readings are not another's knowledge — but taken alone
it removes the one thing recording was for: **somebody else re-running a result
with no credential and no vendor account.** A set scoped to one user cannot be
replayed by anyone else. Export is what keeps "never Global" from quietly
meaning "never reproducible".

⚠ **THE BUG THIS MODULE ACTUALLY FIXES IS NOT THE SCOPE, IT IS THE KEY.**
``RecordedLLM`` looks an answer up by :func:`~.recording.request_key`, a hash
over the prompt IRI and version, **the model id and version**, the temperature
and the exact source text. So a third party handed a bare
``{key: response}`` file cannot replay it: they must construct
``RecordedLLM(store, model_id=…, model_version=…, temperature=…)`` with the
*same* values, and **nothing in that file tells them what those were**. Every
read would miss, loudly and for the wrong reason — a replay miss reads as "the
set is wrong", not as "you configured the client differently". An exported set
therefore carries a manifest, and :meth:`ImportedSet.replay_config` hands back
the exact keyword arguments.

**The manifest is DERIVED, never asserted.** Every field in it is read out of
the payloads themselves, which were stamped by the client at capture time and
not by whoever ran the export. A manifest a caller could fill in by hand is a
claim about a recording rather than a property of it, and this package's whole
argument is that nothing is fixed up on our side.

⚠ **A SET WITH MORE THAN ONE MODEL IDENTITY CANNOT BE REPLAYED BY ONE CLIENT,
and saying so at export is the point.** The keys were computed with different
model ids, so a single ``RecordedLLM`` would hit for some and miss for others —
a half-replaying set that looks like a broken recording. The manifest records
every identity it finds; :meth:`ImportedSet.replay_config` refuses when there
is more than one and names what to do about it.

**What this module does NOT do.** It does not touch L2. ``mindsos_llm`` may not
import ``mindsos_knowledge`` (pinned by
``tests/llm_seam/test_import_isolation_mindsos_llm.py``): substrate does not
depend on the layers that consume it. **The L2 Local pointer and its provenance
row are therefore owned by a layer above this one, and that is an open design
question, not an oversight** — see the CR. A file is the interchange format; a
pointer to a file is somebody else's record.

**Hand-written sets.** ``RecordingStore.from_path`` accepts any JSON object,
which means a set can be typed by hand — and hand-writing a recording file is
hand-writing the model's answers, which ``live.py``'s docstring names as the
failure mode the whole seam exists to prevent. This module cannot make that
impossible; a determined author can synthesise payloads. What it does is make
it **inconvenient and visible**: an exported set is structurally checked on
import, a payload missing the provenance a client stamps is refused, and the
format version is explicit. Recording something you did not run remains
possible and remains dishonest.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from .recording import KEY_SCHEMA_VERSION, RecordingStore

#: Bumped when the envelope's shape changes. An unknown version is refused
#: rather than best-guessed: a set read under the wrong assumptions replays
#: answers that look right.
EXPORT_FORMAT = 1

#: The provenance a client stamps onto every payload. A payload missing any of
#: these did not come from ``LiveLLM``/``RecordedLLM``, and the manifest cannot
#: be derived from it.
REQUIRED_PROVENANCE = (
    "model_id",
    "model_version",
    "prompt_iri",
    "prompt_version",
    "temperature",
    "request_key",
)


class RecordedSetRefused(ValueError):
    """The set could not be read as a recording this package produced.

    Operator-facing and deliberately detailed — unlike the transport's fixed
    prose, this never reaches a customer page. It is read by someone holding a
    file and wondering why it will not load.
    """


def _payloads(store: RecordingStore) -> Tuple[Tuple[str, Mapping[str, Any]], ...]:
    return tuple(
        (key, store.get(key)) for key in sorted(json.loads(store.to_json()))
    )


def _derive_manifest(store: RecordingStore) -> Dict[str, Any]:
    """Read the manifest OUT of the payloads. Nothing here is supplied."""
    identities = set()
    prompts = set()
    for key, payload in _payloads(store):
        missing = [f for f in REQUIRED_PROVENANCE if f not in payload]
        if missing:
            raise RecordedSetRefused(
                f"response {key!r} is missing {missing!r}. Every payload a "
                "client produces carries these; a payload without them was not "
                "recorded by one, and a manifest cannot be derived from it."
            )
        if payload["request_key"] != key:
            raise RecordedSetRefused(
                f"response filed under {key!r} carries request_key "
                f"{payload['request_key']!r}. The key is the question; a "
                "payload filed under a different one answers something else."
            )
        identities.add(
            (
                str(payload["model_id"]),
                str(payload["model_version"]),
                float(payload["temperature"]),
            )
        )
        prompts.add((str(payload["prompt_iri"]), int(payload["prompt_version"])))
    return {
        "responses": len(store),
        "key_schema_version": KEY_SCHEMA_VERSION,
        "identities": sorted(
            [
                {"model_id": m, "model_version": v, "temperature": t}
                for m, v, t in identities
            ],
            key=lambda d: (d["model_id"], d["model_version"], d["temperature"]),
        ),
        "prompts": sorted(
            [{"prompt_iri": i, "prompt_version": v} for i, v in prompts],
            key=lambda d: (d["prompt_iri"], d["prompt_version"]),
        ),
    }


def export_set(
    store: RecordingStore,
    *,
    vendor_id: Optional[str] = None,
    credential_level: Optional[int] = None,
    note: str = "",
) -> str:
    """Serialise a set with a derived manifest. Returns JSON text.

    ``vendor_id`` and ``credential_level`` are the only supplied fields, and
    they are supplied because **the payloads do not carry them** — the client
    stamps the model, not the wire it came over. They are recorded as context,
    never as something replay depends on: a replay reaches no vendor and needs
    no credential, which is the entire point of handing someone a set.
    """
    envelope = {
        "format": EXPORT_FORMAT,
        "manifest": _derive_manifest(store),
        "captured_over": {"vendor_id": vendor_id, "credential_level": credential_level},
        "note": note,
        "responses": json.loads(store.to_json()),
    }
    return json.dumps(envelope, sort_keys=True, indent=2, ensure_ascii=False)


class ImportedSet:
    """A loaded set, its manifest, and the client configuration that replays it."""

    __slots__ = ("store", "manifest", "captured_over", "note")

    def __init__(
        self,
        *,
        store: RecordingStore,
        manifest: Mapping[str, Any],
        captured_over: Mapping[str, Any],
        note: str,
    ) -> None:
        self.store = store
        self.manifest = dict(manifest)
        self.captured_over = dict(captured_over)
        self.note = note

    def replay_config(self) -> Dict[str, Any]:
        """The exact keyword arguments ``RecordedLLM`` needs for this set.

        ⚠ Raises when the set holds more than one model identity. A single
        client cannot replay it: the keys were computed with different model
        ids, so some reads would hit and others would miss, and a partial
        replay looks like a corrupt recording rather than a misconfiguration.
        Split the set by identity, or build one client per identity.
        """
        identities = self.manifest.get("identities") or []
        if len(identities) != 1:
            raise RecordedSetRefused(
                f"this set holds {len(identities)} model identities "
                f"{identities!r}. request_key hashes the model id, version and "
                "temperature, so ONE RecordedLLM can replay exactly one of "
                "them - split the set, or build one client per identity."
            )
        only = identities[0]
        return {
            "model_id": only["model_id"],
            "model_version": only["model_version"],
            "temperature": only["temperature"],
        }


def import_set(source: Any) -> ImportedSet:
    """Load an exported set from JSON text, a mapping, or a path.

    ⚠ **A bare ``{key: response}`` file is refused, and that is deliberate.**
    ``RecordingStore.from_path`` still accepts one, because that is the format
    ``to_json`` has always written and existing sets are not invalidated by
    this module. But a set handed to a *third party* must carry the manifest
    that tells them how to configure the client — a bare map is exactly the
    artifact that misses every key and reads as a broken recording. Re-export
    it through :func:`export_set` instead.
    """
    if isinstance(source, (str, Path)) and not str(source).lstrip().startswith("{"):
        raw: Any = json.loads(Path(source).read_text(encoding="utf-8"))
    elif isinstance(source, (str, bytes)):
        raw = json.loads(source)
    else:
        raw = source
    if not isinstance(raw, Mapping):
        raise RecordedSetRefused(
            f"an exported set is a JSON object, got {type(raw).__name__}"
        )
    if "format" not in raw:
        raise RecordedSetRefused(
            "this looks like a bare response map, not an exported set. It has "
            "no manifest, so a reader cannot know which model id, version and "
            "temperature to configure - and every lookup would miss. Load it "
            "with RecordingStore.from_path and re-export it."
        )
    if raw["format"] != EXPORT_FORMAT:
        raise RecordedSetRefused(
            f"unknown export format {raw['format']!r}; this build writes and "
            f"reads {EXPORT_FORMAT!r}. Refused rather than guessed: a set read "
            "under the wrong assumptions replays answers that look right."
        )
    responses = raw.get("responses")
    if not isinstance(responses, Mapping):
        raise RecordedSetRefused("the exported set carries no responses object")
    store = RecordingStore(responses)
    derived = _derive_manifest(store)
    declared = raw.get("manifest")
    if declared != derived:
        raise RecordedSetRefused(
            "the manifest does not describe the responses in this file. The "
            "manifest is DERIVED at export, so a mismatch means the file was "
            "edited after it was written - which is hand-writing the model's "
            "answers, the one thing this package exists to prevent.\n"
            f"declared: {declared!r}\nderived:  {derived!r}"
        )
    return ImportedSet(
        store=store,
        manifest=derived,
        captured_over=dict(raw.get("captured_over") or {}),
        note=str(raw.get("note") or ""),
    )


__all__ = [
    "EXPORT_FORMAT",
    "REQUIRED_PROVENANCE",
    "ImportedSet",
    "RecordedSetRefused",
    "export_set",
    "import_set",
]
