"""``describe_set`` — what a recorded-set FILE is, derived from its bytes.

Plan rulings **R12** and **R13** (``docs/plans/MINDSOS_LLM_PLAN.md`` §2), recorded
as ADR-0210 amendment 6. The recorder (plan item I-10) stores a pointer to a file
and must never make a claim about that file it cannot check. Every field this
function returns is therefore read out of the file, and each test below pins one
reason a naive version would be wrong:

* **The identity and the description come from ONE read** — or a file that
  changes between two reads gets a hash of one version and keys of another.
* **An export goes through ``import_set``** — or a hand-edited envelope, whose
  manifest no longer describes its responses, would be described as if it were
  honest.
* **A credential level no single value describes is refused** — ``export_set``
  refuses only a SUPPLIED level that disagrees, and exports a multi-level set
  silently; a pointer cannot carry a level half-true of its file.
* **Nothing unverifiable is returned** (R9) — no vendor, no capture time.
"""

from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

from mindsos_llm.live import CapturingLLM, LiveLLM
from mindsos_llm.recorded_sets import RecordedSetRefused, describe_set, export_set
from mindsos_llm.recording import RecordingStore

ANSWER = {"fields": [{"name": "days", "value": 7, "quote": "seven days"}]}

#: Exactly what R13 names. A key added here is a claim the pointer may store.
EXPECTED_KEYS = frozenset({
    "sha256", "responses", "key_schema_version", "identities", "prompts",
    "request_keys", "credential_level",
})


def _store(*readings):
    """Capture ``(source_text, credential_level)`` readings into ONE store, the
    honest way — a client ran and what came back was kept."""
    store = RecordingStore()
    for text, level in readings:
        CapturingLLM(
            LiveLLM(
                lambda **_: dict(ANSWER),
                model_id="m-1",
                model_version="v-1",
                credential_level=level,
                temperature=0.0,
            ),
            store,
        ).read(prompt_iri="prompt:p", prompt_version=1, source_text=text)
    return store


def _write(tmp_path, name, text):
    f = tmp_path / name
    f.write_text(text, encoding="utf-8")
    return f


def _unstamp(store, keys=None):
    """The same payloads as if recorded before ADR-0210 decisions 5 and 6."""
    raw = json.loads(store.to_json())
    for key in (keys if keys is not None else list(raw)):
        raw[key].pop("credential_level")
    return json.dumps(raw)


def test_a_bare_set_is_described_from_its_own_bytes(tmp_path):
    store = _store(("a", 1), ("b", 1))
    f = _write(tmp_path, "bare.json", store.to_json())
    d = describe_set(f)
    assert d["sha256"] == hashlib.sha256(f.read_bytes()).hexdigest()
    assert d["request_keys"] == sorted(json.loads(store.to_json()))
    assert len(d["request_keys"]) == 2 and d["responses"] == 2
    assert d["credential_level"] == 1


def test_an_export_is_described_through_its_responses_and_is_a_different_file(tmp_path):
    """The same answers held two ways are two files, so two identities (R8)."""
    store = _store(("a", 1))
    bare = describe_set(_write(tmp_path, "bare.json", store.to_json()))
    exported = describe_set(_write(tmp_path, "set.json", export_set(store)))
    assert exported["request_keys"] == bare["request_keys"]
    assert exported["sha256"] != bare["sha256"]


def test_an_edited_export_is_refused_because_describe_set_does_not_bypass_import_set(tmp_path):
    env = json.loads(export_set(_store(("a", 1))))
    key = next(iter(env["responses"]))
    env["responses"][key]["model_id"] = "a-different-model"
    with pytest.raises(RecordedSetRefused, match="edited"):
        describe_set(_write(tmp_path, "edited.json", json.dumps(env)))


def test_the_file_is_read_exactly_once(tmp_path, monkeypatch):
    f = _write(tmp_path, "set.json", export_set(_store(("a", 1))))
    reads = []
    original = pathlib.Path.read_bytes

    def counting(self):
        reads.append(self)
        return original(self)

    monkeypatch.setattr(pathlib.Path, "read_bytes", counting)
    monkeypatch.setattr(
        pathlib.Path, "read_text",
        lambda *a, **k: pytest.fail("a second read of the file"),
    )
    describe_set(f)
    assert len(reads) == 1


def test_two_credential_levels_are_refused(tmp_path):
    f = _write(tmp_path, "mixed.json", _store(("a", 1), ("b", 2)).to_json())
    with pytest.raises(RecordedSetRefused, match="credential levels"):
        describe_set(f)


def test_a_partly_stamped_set_is_refused(tmp_path):
    store = _store(("a", 1), ("b", 1))
    first = sorted(json.loads(store.to_json()))[0]
    f = _write(tmp_path, "partial.json", _unstamp(store, [first]))
    with pytest.raises(RecordedSetRefused, match="credential levels"):
        describe_set(f)


def test_an_unstamped_set_describes_no_level(tmp_path):
    f = _write(tmp_path, "old.json", _unstamp(_store(("a", 1), ("b", 1))))
    assert describe_set(f)["credential_level"] is None


def test_an_empty_set_is_refused(tmp_path):
    with pytest.raises(RecordedSetRefused, match="no responses"):
        describe_set(_write(tmp_path, "empty.json", "{}"))


def test_a_file_that_is_not_a_json_object_is_refused(tmp_path):
    with pytest.raises(RecordedSetRefused, match="UTF-8 JSON"):
        describe_set(_write(tmp_path, "junk.json", "not json"))
    with pytest.raises(RecordedSetRefused, match="JSON object"):
        describe_set(_write(tmp_path, "list.json", "[]"))


def test_the_description_carries_nothing_unverifiable(tmp_path):
    d = describe_set(_write(tmp_path, "set.json", export_set(_store(("a", 1)), vendor_id="anthropic")))
    assert frozenset(d) == EXPECTED_KEYS, (
        "R9/R13: the description is what the FILE proves. A vendor is stamped "
        "on no payload and no payload carries a capture time."
    )
