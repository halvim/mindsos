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
over **what was asked, by content** (v2, plan R22): the prompt words' digest,
the schema's digest, the tool framing, **the model id and version**, the
temperature and the exact source text. So a third party handed a bare
``{key: response}`` file cannot replay it: they must construct
``RecordedLLM`` with the *same* values, and **nothing in that file tells them
what those were**. Every
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
row are therefore owned by a layer above this one** — settled by plan ruling R1
(L3 writes it) and built as plan item I-10. :func:`describe_set` is the one thing
that layer asks of this one. A file is the interchange format; a pointer to a
file is somebody else's record.

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

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from .recording import (
    KEY_SCHEMA_VERSION,
    UNSTAMPED_KEY_SCHEMA_VERSION,
    RecordingStore,
)

#: The framing a v2 answer stamps and a v2 key hashes (plan R22, R32). Part of
#: a set's IDENTITY from v2 on: one replay client carries one framing, so a set
#: holding two cannot be replayed by one client, exactly as with two models.
FRAMING = ("tool_name", "tool_description", "max_tokens")

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


#: Returned by :func:`_declared_levels` for a payload that has no
#: ``credential_level`` key at all. ⚠ **Not ``None``** — a replayed answer
#: carries the key WITH the value ``None``, which is a client stating that no
#: credential was in force, while an absent key is a payload recorded before
#: ADR-0210 decisions 5 and 6 that states nothing. Collapsing the two with
#: ``.get()`` would make every pre-decision set unexportable with the supplied
#: ``credential_level`` its operator has always passed — a compatibility break
#: bought for no verification, since a set that says nothing cannot contradict
#: anything.
_UNSTAMPED = "<unstamped>"


def _declared_levels(store: RecordingStore) -> set:
    """The credential levels the responses themselves carry.

    ⚠ **Read from the payloads, never supplied** — that is the whole point of
    the check it feeds. ``credential_level`` is deliberately NOT added to
    :data:`REQUIRED_PROVENANCE` (as ``recorded`` never was), so a set recorded
    before decisions 5 and 6 still imports; it reports :data:`_UNSTAMPED`
    instead.
    """
    return {
        payload["credential_level"] if "credential_level" in payload
        else _UNSTAMPED
        for _, payload in _payloads(store)
    }


def _derive_manifest(store: RecordingStore) -> Dict[str, Any]:
    """Read the manifest OUT of the payloads. Nothing here is supplied.

    ⚠ ``key_schema_version`` is DERIVED (plan R34). It used to be this
    module's constant, so every set was described as keyed under the version
    the READER was built with — a false claim the day the key changed, while
    ``mindsos_knowledge.recorded_sets`` said it was "derived from the file's
    bytes". Each payload states its version; an unstamped one predates the
    stamp and is v1; a set mixing versions refuses.
    """
    identities = set()
    prompts = set()
    versions = set()
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
        version = str(payload.get("key_schema_version", UNSTAMPED_KEY_SCHEMA_VERSION))
        versions.add(version)
        identity = {
            "model_id": str(payload["model_id"]),
            "model_version": str(payload["model_version"]),
            "temperature": float(payload["temperature"]),
        }
        prompt = {
            "prompt_iri": str(payload["prompt_iri"]),
            "prompt_version": int(payload["prompt_version"]),
        }
        if version != UNSTAMPED_KEY_SCHEMA_VERSION:
            missing = [f for f in FRAMING + ("prompt_digest",) if f not in payload]
            if missing:
                raise RecordedSetRefused(
                    f"response {key!r} states key_schema_version {version!r} "
                    f"but is missing {missing!r}, which every v2 answer carries."
                )
            identity.update(
                tool_name=str(payload["tool_name"]),
                tool_description=str(payload["tool_description"]),
                max_tokens=int(payload["max_tokens"]),
            )
            prompt["prompt_digest"] = str(payload["prompt_digest"])
        identities.add(json.dumps(identity, sort_keys=True))
        prompts.add(json.dumps(prompt, sort_keys=True))
    if len(versions) > 1:
        raise RecordedSetRefused(
            f"this set mixes key schema versions {sorted(versions)!r}. One "
            "client computes one key, so part of the set would always miss - "
            "split it by version."
        )
    return {
        "responses": len(store),
        "key_schema_version": (
            next(iter(versions)) if versions else KEY_SCHEMA_VERSION
        ),
        # Sorted by the SAME keys as before v2, extended — an export written by
        # an earlier build must still derive to the manifest it carries.
        "identities": sorted(
            (json.loads(i) for i in identities),
            key=lambda d: (
                d["model_id"], d["model_version"], d["temperature"],
                d.get("tool_name", ""), d.get("tool_description", ""),
                d.get("max_tokens", 0),
            ),
        ),
        "prompts": sorted(
            (json.loads(p) for p in prompts),
            key=lambda d: (
                d["prompt_iri"], d["prompt_version"], d.get("prompt_digest", ""),
            ),
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

    ``vendor_id`` and ``credential_level`` are the only supplied fields. They
    are recorded as context, never as something replay depends on: a replay
    reaches no vendor and needs no credential, which is the entire point of
    handing someone a set.

    ⚠ **CORRECTED with ADR-0210 decisions 5 and 6.** This docstring used to say
    they were supplied *because the payloads do not carry them*. The payloads
    now carry ``credential_level``, so that reason has expired for one of the
    two — and a supplied value is no longer merely redundant, it is
    **falsifiable**: an export could declare a level its own responses
    contradict, which is a file that disproves itself. So the field stays
    supplied (a caller may still want to record which of several levels a
    mixed set was gathered under) and is **checked against the payloads**
    rather than trusted. ``vendor_id`` has no such check because nothing
    stamps it; that asymmetry is real and is why the check is per-field rather
    than over ``captured_over`` as a whole.

    Raises :class:`RecordedSetRefused` when a supplied ``credential_level``
    is not what the responses say, on either of two doors: the responses agree
    on one level and it is a different one, or they hold more than one and a
    single value cannot describe them. The second mirrors
    :meth:`ImportedSet.replay_config`'s refusal on multiple model identities,
    for the same reason — a manifest half-true of its file reads as a broken
    recording rather than as a wrong declaration.

    A set whose responses were all recorded before decisions 5 and 6 stamps
    nothing, contradicts nothing, and is exported unchecked — see
    :data:`_UNSTAMPED`.
    """
    manifest = _derive_manifest(store)
    levels = _declared_levels(store)
    if (
        credential_level is not None
        and levels != {_UNSTAMPED}
        and levels != {credential_level}
    ):
        raise RecordedSetRefused(
            f"credential_level={credential_level!r} was supplied, but the "
            f"responses in this set carry {sorted(levels, key=repr)!r}. The "
            "client stamps the level it called at onto every answer, so a "
            "supplied value that disagrees would export a file that "
            "contradicts itself - and a set carrying more than one level "
            "cannot be described by a single value at all. Export the "
            "level the responses actually carry, split the set, or omit "
            "credential_level and let the responses speak."
        )
    envelope = {
        "format": EXPORT_FORMAT,
        "manifest": manifest,
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

        ⚠ Returns ``prompt_digests`` rather than prompt words (plan R31): the
        v2 key hashes the digest, so a third party replays an export without
        being handed the prompts. ⚠ Refuses a set keyed under another
        ``key_schema_version``, and a set in which one prompt edition was
        asked with two wordings.

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
                f"{identities!r}. request_key hashes the model id, version, "
                "temperature and tool framing, so ONE RecordedLLM can replay "
                "exactly one of them - split the set, or build one client per "
                "identity."
            )
        version = self.manifest.get("key_schema_version")
        if version != KEY_SCHEMA_VERSION:
            raise RecordedSetRefused(
                f"this set was keyed under key_schema_version {version!r}; this "
                f"build computes {KEY_SCHEMA_VERSION!r}, so every read would "
                "miss. Re-capture it (plan R22: an old set misses loudly, and "
                "this is the loud part)."
            )
        digests: Dict[Tuple[str, int], str] = {}
        for entry in self.manifest.get("prompts") or []:
            at = (entry["prompt_iri"], int(entry["prompt_version"]))
            if at in digests and digests[at] != entry["prompt_digest"]:
                raise RecordedSetRefused(
                    f"prompt {at!r} was asked with two different wordings in "
                    "this set - the edition was changed in place between "
                    "captures. One client resolves one wording per edition; "
                    "split the set."
                )
            digests[at] = entry["prompt_digest"]
        only = identities[0]
        return {
            "model_id": only["model_id"],
            "model_version": only["model_version"],
            "temperature": only["temperature"],
            "tool_name": only["tool_name"],
            "tool_description": only["tool_description"],
            "max_tokens": only["max_tokens"],
            "prompt_digests": digests,
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


def describe_set(path: Any) -> Dict[str, Any]:
    """What a recorded-set FILE is, derived from its bytes — plan rulings R12, R13.

    Reads the file **once**, hashes exactly those bytes, and derives every other
    field from the same bytes, so the identity and the description cannot come
    from two different reads of a file that changed in between. ``format``
    decides the door (R12): an exported envelope goes through :func:`import_set`,
    which refuses a manifest that no longer describes its responses; a bare
    ``{request_key: response}`` map goes through :class:`RecordingStore`.

    Returns exactly: ``path`` (the resolved absolute path that was opened —
    so the caller cannot name one file and hash another), ``sha256`` (bare
    hex, so ``sha256sum`` output compares directly), ``responses``, ``key_schema_version``, ``identities``,
    ``prompts``, the sorted ``request_keys``, and ``credential_level``.

    ⚠ **Named for what it describes, never for the L2 record it feeds** (R13).
    This package may not import ``mindsos_knowledge``; a function here that
    spoke the pointer's vocabulary would be the same layering error pointing
    the other way. What is stored, and as what, is the caller's decision.

    ⚠ **Nothing unverifiable is returned** (R9): no vendor, and no capture time
    — no payload carries one. ``credential_level`` is the one level every
    payload states, or ``None`` when none states one. A set whose payloads state
    ``None`` (no credential in force) describes the same as an unstamped one;
    the FILE still tells them apart, and the hash makes the file verifiable.

    Raises:
        RecordedSetRefused: the file is not a recorded set (R10 — the recorder
            has no don't-know): not JSON, not an object, an export this
            package would not import, a payload no client produced, NO
            responses, or credential levels that no single value describes
            — more than one level, or some payloads stamped and some not. That
            last rule is new here: :func:`export_set` refuses only a SUPPLIED
            level that disagrees, and exports a multi-level set silently.
    """
    opened = Path(path).resolve()
    data = opened.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    try:
        raw = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise RecordedSetRefused(
            f"{str(path)!r} is not a recorded set: it does not parse as UTF-8 "
            f"JSON ({exc})."
        ) from exc
    if not isinstance(raw, Mapping):
        raise RecordedSetRefused(
            f"{str(path)!r} is not a recorded set: a set is a JSON object, got "
            f"{type(raw).__name__}."
        )
    store = import_set(raw).store if "format" in raw else RecordingStore(raw)
    if len(store) == 0:
        raise RecordedSetRefused(
            f"{str(path)!r} holds no responses. A pointer to it would name no "
            "request_key, so no conclusion could ever be traced to it."
        )
    manifest = _derive_manifest(store)
    levels = _declared_levels(store)
    stamped = levels - {_UNSTAMPED}
    if len(stamped) > 1 or (stamped and _UNSTAMPED in levels):
        raise RecordedSetRefused(
            f"{str(path)!r} carries credential levels "
            f"{sorted(levels, key=repr)!r}. One value cannot describe them, "
            "and a description half-true of its file reads as a broken "
            "recording rather than as a mixed one - split the set."
        )
    return {
        "path": str(opened),
        "sha256": digest,
        "responses": manifest["responses"],
        "key_schema_version": manifest["key_schema_version"],
        "identities": manifest["identities"],
        "prompts": manifest["prompts"],
        "request_keys": sorted(json.loads(store.to_json())),
        "credential_level": next(iter(stamped)) if stamped else None,
    }


__all__ = [
    "EXPORT_FORMAT",
    "REQUIRED_PROVENANCE",
    "ImportedSet",
    "RecordedSetRefused",
    "describe_set",
    "export_set",
    "import_set",
]
