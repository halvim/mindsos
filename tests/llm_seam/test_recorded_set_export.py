"""Export/import guards — what keeps "never Global" from meaning "never reproducible".

The scope ruling (recorded sets are per-user L2 Local) is right for a store and
fatal for reproducibility taken alone. These guards pin the export that fixes
it, and — more importantly — pin the reason it was needed, which is not the
scope at all: **`request_key` hashes the model id, version and temperature, so
a bare response map cannot be replayed by anyone who was not told what those
were.**
"""

from __future__ import annotations

import json

import pytest

from mindsos_llm.live import CapturingLLM, LiveLLM
from mindsos_llm.recorded_sets import (
    EXPORT_FORMAT,
    ImportedSet,
    RecordedSetRefused,
    export_set,
    import_set,
)
from mindsos_llm.recording import RecordingStore
from mindsos_llm.replay import RecordedLLM

ANSWER = {"fields": [{"name": "days", "value": 7, "quote": "seven days"}]}


def _captured(model_id="m-1", model_version="v-1", temperature=0.0, text="the doc"):
    """Produce a set the honest way: run a client and keep what came back."""
    store = RecordingStore()
    client = CapturingLLM(
        LiveLLM(
            lambda **_: dict(ANSWER),
            model_id=model_id,
            model_version=model_version,
            temperature=temperature,
        ),
        store,
    )
    client.read(prompt_iri="prompt:p", prompt_version=1, source_text=text)
    return store


# ── the round trip ─────────────────────────────────────────────────────

def test_an_exported_set_replays_with_NO_client_and_NO_credential():
    """The whole promise: hand someone a file, they get the same answer."""
    exported = export_set(_captured(), vendor_id="anthropic", credential_level=1)
    loaded = import_set(exported)
    replayed = RecordedLLM(loaded.store, **loaded.replay_config()).read(
        prompt_iri="prompt:p", prompt_version=1, source_text="the doc"
    )
    assert replayed["fields"] == ANSWER["fields"]
    assert replayed["recorded"] is True


def test_replay_config_is_what_a_third_party_would_otherwise_have_to_GUESS():
    """⚠ The actual bug. request_key hashes model id, version and temperature;
    a bare map tells a reader none of them, so every lookup misses and reads as
    a broken recording rather than a misconfigured client."""
    loaded = import_set(export_set(_captured(model_id="m-9", model_version="v-3")))
    assert loaded.replay_config() == {
        "model_id": "m-9",
        "model_version": "v-3",
        "temperature": 0.0,
    }


def test_a_wrongly_configured_client_MISSES_which_is_why_the_manifest_exists():
    from mindsos_llm.exceptions import RecordedResponseMiss

    loaded = import_set(export_set(_captured(model_id="m-1")))
    wrong = RecordedLLM(loaded.store, model_id="m-2", model_version="v-1")
    with pytest.raises(RecordedResponseMiss):
        wrong.read(prompt_iri="prompt:p", prompt_version=1, source_text="the doc")


# ── the manifest is derived, never asserted ────────────────────────────

def test_the_manifest_is_read_out_of_the_payloads_not_supplied():
    exported = json.loads(export_set(_captured(model_id="m-1", model_version="v-1")))
    assert exported["manifest"]["identities"] == [
        {"model_id": "m-1", "model_version": "v-1", "temperature": 0.0}
    ]
    assert exported["manifest"]["prompts"] == [
        {"prompt_iri": "prompt:p", "prompt_version": 1}
    ]
    assert exported["manifest"]["responses"] == 1


def test_an_edited_file_is_REFUSED_because_the_manifest_no_longer_describes_it():
    """Editing a recording file is hand-writing the model's answers — the
    failure mode ``live.py`` says the seam exists to prevent. This cannot make
    it impossible; it makes it visible."""
    exported = json.loads(export_set(_captured()))
    key = next(iter(exported["responses"]))
    exported["responses"][key]["model_id"] = "a-different-model"
    with pytest.raises(RecordedSetRefused) as caught:
        import_set(exported)
    assert "edited" in str(caught.value)


def test_a_payload_filed_under_the_wrong_key_is_REFUSED():
    """The key is the question. A payload filed under a different one answers
    something else, and would replay confidently."""
    exported = json.loads(export_set(_captured()))
    key = next(iter(exported["responses"]))
    exported["responses"]["sha256:not-the-real-key"] = exported["responses"].pop(key)
    with pytest.raises(RecordedSetRefused):
        import_set(exported)


def test_a_payload_missing_client_provenance_is_REFUSED():
    store = RecordingStore({"sha256:x": {"fields": []}})
    with pytest.raises(RecordedSetRefused) as caught:
        export_set(store)
    assert "model_id" in str(caught.value)


# ── the trap the manifest exists to name ───────────────────────────────

def test_a_set_with_TWO_model_identities_refuses_to_hand_out_ONE_config():
    """⚠ One client cannot replay it: the keys were computed with different
    model ids, so some reads hit and others miss. A partial replay looks like a
    corrupt recording rather than a misconfiguration, which is why this refuses
    at the point of asking rather than at the point of missing."""
    merged = RecordingStore(
        {
            **json.loads(_captured(model_id="m-1").to_json()),
            **json.loads(_captured(model_id="m-2").to_json()),
        }
    )
    loaded = import_set(export_set(merged))
    assert len(loaded.manifest["identities"]) == 2
    with pytest.raises(RecordedSetRefused) as caught:
        loaded.replay_config()
    assert "split the set" in str(caught.value)


# ── the envelope ───────────────────────────────────────────────────────

def test_a_BARE_response_map_is_refused_with_the_reason_a_reader_needs():
    """The artifact that misses every key. Refused with the fix in the message
    rather than loaded into a client that will fail confusingly later."""
    with pytest.raises(RecordedSetRefused) as caught:
        import_set(json.loads(_captured().to_json()))
    assert "bare response map" in str(caught.value)


def test_an_unknown_format_version_is_REFUSED_not_best_guessed():
    exported = json.loads(export_set(_captured()))
    exported["format"] = EXPORT_FORMAT + 99
    with pytest.raises(RecordedSetRefused) as caught:
        import_set(exported)
    assert "Refused rather than guessed" in str(caught.value)


def test_the_wire_it_came_over_is_CONTEXT_and_replay_never_depends_on_it():
    """A replay reaches no vendor and needs no credential — that is the point
    of handing someone a set. The vendor and level are recorded so a reader
    knows what produced it, not so replay can use them."""
    loaded = import_set(export_set(_captured(), vendor_id="anthropic", credential_level=1))
    assert loaded.captured_over == {"vendor_id": "anthropic", "credential_level": 1}
    stripped = ImportedSet(
        store=loaded.store, manifest=loaded.manifest, captured_over={}, note=""
    )
    assert stripped.replay_config() == loaded.replay_config()
