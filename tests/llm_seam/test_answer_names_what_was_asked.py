"""An answer names what was asked, BY CONTENT — plan item I-17, gate 2.

Plan rulings R20, R22, R30-R34; ADR-0210 amendment 7. Until this gate an
answer named its prompt by ``prompt_iri`` + ``prompt_version`` and its key
hashed that NAME, so a prompt edited in place, a changed schema or a changed
tool sentence replayed the old reading as if nothing had changed, and a shown
prompt could not be proved to be the one that ran. Each test pins one claim:

* the stamps are the digests of what was SENT, and the key is recomputable
  from them (R22, R24's premise);
* the prompt's NAME is not in the key — the same words under two names are
  one question (R30);
* a deployment replaying its own set MISSES once the words change (R31);
* a third party replays an export from ``replay_config`` alone, without the
  words (R31);
* an undecodable answer still says what was asked (R33);
* a set's key version is read off its payloads, not off this build (R34).

No network, no credential, no FalkorDB.
"""

from __future__ import annotations

import json

import pytest

from mindsos_llm.exceptions import MalformedResponse, RecordedResponseMiss
from mindsos_llm.live import CapturingLLM, LiveLLM
from mindsos_llm.recorded_sets import (
    RecordedSetRefused,
    describe_set,
    export_set,
    import_set,
)
from mindsos_llm.recording import (
    KEY_SCHEMA_VERSION,
    RecordingStore,
    schema_digest,
    text_digest,
    what_was_asked,
)
from mindsos_llm.replay import RecordedLLM

WORDS = "read how many days the customer waited"
SCHEMA = {"type": "object", "properties": {"fields": {"type": "array"}}}
FRAMING = dict(tool_name="extract", tool_description="pull the fields out", max_tokens=512)
ANSWER = {"fields": [{"name": "days", "value": 7, "quote": "seven days"}]}
CALL = dict(prompt_iri="prompt:days", prompt_version=3,
            source_text="it took seven days", extraction_schema=SCHEMA)


def _live(words=WORDS, transport=None, **over):
    kw = dict(model_id="m-1", model_version="v-1", credential_level=1,
              resolve_prompt=lambda **_: words, temperature=0.2, **FRAMING)
    kw.update(over)
    return LiveLLM(transport or (lambda **_: dict(ANSWER)), **kw)


def _captured(words=WORDS):
    store = RecordingStore()
    CapturingLLM(_live(words), store).read(**CALL)
    return store


# ── 1 ── the stamps are what was SENT ──────────────────────────────────

def test_the_answer_stamps_the_digests_of_what_was_sent_and_the_key_recomputes():
    """MUTATION: in ``LiveLLM.read`` stamp ``text_digest(prompt_iri)`` instead
    of ``text_digest(prompt_text)`` — red here, and only here in this file.
    """
    sent = {}

    def transport(**call):
        sent.update(call)
        return dict(ANSWER)

    answer = _live(transport=transport).read(**CALL)
    assert answer["prompt_digest"] == text_digest(sent["prompt_text"]) == text_digest(WORDS)
    assert answer["schema_digest"] == schema_digest(sent["extraction_schema"])
    for field in ("tool_name", "tool_description", "max_tokens", "model_id", "temperature"):
        assert answer[field] == sent[field], field
    assert answer["key_schema_version"] == KEY_SCHEMA_VERSION == "2"
    recomputed = what_was_asked(
        prompt_iri=answer["prompt_iri"], prompt_version=answer["prompt_version"],
        prompt_digest=text_digest(WORDS), extraction_schema=SCHEMA,
        tool_name=answer["tool_name"], tool_description=answer["tool_description"],
        max_tokens=answer["max_tokens"], model_id=answer["model_id"],
        model_version=answer["model_version"], temperature=answer["temperature"],
        source_text=CALL["source_text"],
    )
    assert recomputed["request_key"] == answer["request_key"]


def test_the_prompt_NAME_is_not_in_the_key():
    """R30. Same words, two names: one question."""
    a = _live().read(**CALL)
    b = _live().read(**{**CALL, "prompt_iri": "prompt:renamed", "prompt_version": 9})
    assert a["request_key"] == b["request_key"]
    assert (a["prompt_iri"], b["prompt_iri"]) == ("prompt:days", "prompt:renamed")


# ── 2 ── replay poses the question by digest ──────────────────────────

def test_a_deployment_replaying_its_own_set_MISSES_once_the_words_change():
    """R31. The failure v1 permitted: the edition's text changed in place and
    the old reading came back. The replay hashes the CURRENT words."""
    store = _captured()
    own = dict(model_id="m-1", model_version="v-1", temperature=0.2, **FRAMING)
    assert RecordedLLM(store, resolve_prompt=lambda **_: WORDS, **own).read(**CALL)["fields"]
    with pytest.raises(RecordedResponseMiss):
        RecordedLLM(store, resolve_prompt=lambda **_: WORDS + " (edited)", **own).read(**CALL)


def test_a_third_party_replays_an_export_from_replay_config_WITHOUT_the_words():
    """R31. ``replay_config`` hands over digests; nothing in it is the prompt."""
    loaded = import_set(export_set(_captured()))
    config = loaded.replay_config()
    assert WORDS not in json.dumps({k: str(v) for k, v in config.items()})
    replayed = RecordedLLM(loaded.store, **config).read(**CALL)
    assert replayed["fields"] == ANSWER["fields"]
    assert replayed["prompt_digest"] == text_digest(WORDS)


def test_replay_needs_exactly_one_source_for_the_prompt_digest():
    kw = dict(model_id="m", model_version="v", **FRAMING)
    with pytest.raises(ValueError, match="exactly one"):
        RecordedLLM(RecordingStore(), **kw)
    with pytest.raises(ValueError, match="exactly one"):
        RecordedLLM(RecordingStore(), resolve_prompt=lambda **_: WORDS,
                    prompt_digests={}, **kw)


def test_one_edition_asked_with_two_wordings_refuses_to_hand_out_one_config():
    merged = RecordingStore({
        **json.loads(_captured(WORDS).to_json()),
        **json.loads(_captured(WORDS + " v2").to_json()),
    })
    with pytest.raises(RecordedSetRefused, match="two different wordings"):
        import_set(export_set(merged)).replay_config()


# ── 3 ── an undecodable answer still says what was asked ──────────────

@pytest.mark.parametrize("wrap", ["live", "capture"])
def test_an_undecodable_answer_carries_what_was_asked(wrap):
    """R33. MUTATION: delete ``exc.asked = dict(stamps)`` in ``LiveLLM.read``
    — both ids red."""
    client = _live(transport=lambda **_: "not json at all")
    if wrap == "capture":
        client = CapturingLLM(client, RecordingStore())
    with pytest.raises(MalformedResponse) as caught:
        client.read(**CALL)
    asked = caught.value.asked
    assert asked is not None
    assert asked["prompt_digest"] == text_digest(WORDS)
    assert asked["mode"] == wrap
    assert asked["request_key"] == _live().read(**CALL)["request_key"]
    assert str(caught.value) == MalformedResponse.MESSAGE


# ── 4 ── a set's key version is read off its payloads ─────────────────

def _v1_payloads(store):
    old = {}
    for key, payload in json.loads(store.to_json()).items():
        for field in ("key_schema_version", "prompt_digest", "schema_digest",
                      "tool_name", "tool_description", "max_tokens"):
            payload.pop(field)
        old[key] = payload
    return old


def test_a_set_with_no_version_stamp_is_described_as_v1_not_as_this_build(tmp_path):
    """R34. MUTATION: in ``_derive_manifest`` return ``KEY_SCHEMA_VERSION`` —
    red here."""
    f = tmp_path / "v1.json"
    f.write_text(json.dumps(_v1_payloads(_captured())), encoding="utf-8")
    assert describe_set(f)["key_schema_version"] == "1"
    assert describe_set(f)["identities"] == [
        {"model_id": "m-1", "model_version": "v-1", "temperature": 0.2}
    ]


def test_a_v1_set_refuses_a_replay_config_rather_than_missing_every_read():
    loaded = import_set(export_set(RecordingStore(_v1_payloads(_captured()))))
    with pytest.raises(RecordedSetRefused, match="key_schema_version"):
        loaded.replay_config()


def test_a_set_mixing_key_versions_refuses():
    mixed = RecordingStore({
        **_v1_payloads(_captured(WORDS)),
        **json.loads(_captured(WORDS + " v2").to_json()),
    })
    with pytest.raises(RecordedSetRefused, match="mixes key schema versions"):
        export_set(mixed)
