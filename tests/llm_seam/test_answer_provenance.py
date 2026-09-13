"""An answer states the terms it was obtained under — ADR-0210 decisions 5
and 6.

**What was wrong.** The ADR has said since 2026-09-02 that *"mode and
credential level are stamped on every answer"*, and slice 4 measured that
neither was: ``LiveLLM.read`` stamped seven fields and ``credential_level``
existed in this package only as an *optional supplied* manifest key on
``recorded_sets.export_set`` — in the module whose own rule is that a manifest
is derived. So ``credential_kinds``' argument for its level/kind pairing check
(*"the level is stamped on answers, so an unchecked pairing corrupts
provenance"*) rested on a property the payload did not have. Filed as
``core-llm-answer-carries-no-mode-or-level``; this file is the guard half of
closing it.

**The two fields are stamped by different mechanisms, deliberately.**

* ``mode`` comes from the CLASS. ``recorded`` has always worked this way —
  hardcoded ``False`` in :mod:`~mindsos_llm.live` and ``True`` in
  :mod:`~mindsos_llm.replay`, never an argument — because a mode a caller can
  pass is a mode a caller can forge, and no later check can catch an answer
  stamped ``replay`` by a client that just called a provider.
* ``credential_level`` is PUSHED IN, because no class can know it: L0 owns it
  and hands it down at construction. It has no default, so that a caller who
  has not thought about it cannot silently get ``None`` — the "optional
  supplied" shape this package refuses everywhere else.

⚠ **``mode`` and ``recorded`` are not redundant and must not disagree.**
``recorded`` answers *"was this replayed?"*; ``mode`` answers *"which of the
three modes produced it?"*. They coincide on two of three values and differ on
``capture``, which is exactly why both exist — and why the invariant between
them is guarded rather than assumed.

**What this file does NOT cover.** Whether a layer above declares these fields
as outputs of its own records is that layer's decision;
:mod:`mindsos_llm` may not import ``mindsos_capacity`` (pinned by
``test_import_isolation_mindsos_llm.py``), so it is structurally unable to make
that change. Filed as ``core-llm-l3-may-declare-answer-mode-and-level``.
"""

from __future__ import annotations

import inspect
import json
from typing import Any, Dict, Iterator

import pytest

from mindsos_llm import adapters, client as C, contract, recording
from mindsos_llm.credentials import Resolver
from mindsos_llm.live import CapturingLLM, LiveLLM
from mindsos_llm.recorded_sets import (
    RecordedSetRefused,
    export_set,
    import_set,
)
from mindsos_llm.recording import RecordingStore
from mindsos_llm.replay import RecordedLLM

PROMPT = "prompt:probe"
CALL = dict(prompt_iri=PROMPT, prompt_version=1, source_text="the source text")


def _transport(**_: Any) -> Dict[str, Any]:
    return {"answer": "42"}


def _live(level, **over: Any) -> LiveLLM:
    kw: Dict[str, Any] = dict(
        model_id="a-model", model_version="1", credential_level=level
    )
    kw.update(over)
    return LiveLLM(_transport, **kw)


# ── 1 ── a live answer ─────────────────────────────────────────────────


@pytest.mark.parametrize("level", [1, 2, 3, None], ids=["l1", "l2", "l3", "none"])
def test_a_live_answer_carries_its_mode_and_the_level_it_was_built_with(level):
    """MUTATION: delete either stamp in ``LiveLLM.read``.

    Parametrized over every level INCLUDING ``None``, because the claim is that
    the class re-publishes what it was handed — a stamp hardcoded to any one
    value would pass a single-level check. ``None`` is in the domain on
    purpose: it is what a contract probe legitimately carries, and a guard that
    omitted it would leave the only value with a second meaning untested.
    """
    payload = _live(level).read(**CALL)
    assert payload["mode"] == "live"
    assert payload["credential_level"] == level


def test_a_live_client_must_decide_a_level_and_cannot_default_into_one():
    """MUTATION: give ``credential_level`` a default of ``None``.

    ⚠ **This is the guard that survives the mutation nothing else notices.**
    A default would leave every other test in this file green while making the
    level a value nobody chose — the exact failure the ADR names about
    ``export_set``'s supplied manifest field. So the absence of a default is
    asked of the SIGNATURE, not inferred from a call that happens to pass one.
    """
    parameter = inspect.signature(LiveLLM).parameters["credential_level"]
    assert parameter.default is inspect.Parameter.empty, (
        "credential_level must have no default: a level nobody chose is the "
        "optional-supplied shape this package refuses"
    )
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    with pytest.raises(TypeError, match="credential_level"):
        LiveLLM(_transport, model_id="m", model_version="1")  # type: ignore[call-arg]


# ── 2 ── a replayed answer ─────────────────────────────────────────────


def test_a_replayed_answer_says_replay_and_reports_NO_credential_level():
    """MUTATION: delete ``payload["credential_level"] = None`` in ``replay``.

    ``None`` is the true value, not a missing one: a replay reaches no provider
    and ``client.build_client`` refuses a resolver on this path, so no level
    was in force. Reporting the level the answers were CAPTURED under would be
    this class making a claim about a run it is not serving — the same reason
    the model identity is configured rather than read out of the file.
    """
    store = RecordingStore({})
    captured = CapturingLLM(_live(1), store).read(**CALL)
    replayed = RecordedLLM(store, model_id="a-model", model_version="1").read(**CALL)

    assert replayed["mode"] == "replay"
    assert "credential_level" in replayed, "absent is not the same as None"
    assert replayed["credential_level"] is None
    assert captured["credential_level"] == 1, (
        "the premise of this guard is that the CAPTURED answer carried a real "
        "level, so reporting None on replay is a decision and not an accident"
    )


# ── 3 ── a captured answer, on BOTH copies ─────────────────────────────


def test_a_captured_answer_says_capture_on_the_returned_AND_the_stored_copy():
    """MUTATION: move ``CapturingLLM``'s override AFTER ``store.put``.

    ⚠ **The two-door row.** ``CapturingLLM`` wraps a ``LiveLLM``, which stamps
    ``live``; the override to ``capture`` happens on the way through, and the
    ordering against the store write is a claim in its own right. Checking only
    the returned copy would leave a file on disk saying a capture run never
    happened while the caller's copy said otherwise — two copies of one answer
    disagreeing about how it was obtained, which is the provenance defect this
    module exists to prevent. The mutation reddens this door and only this
    door, which is why the doors are separate assertions and not one.
    """
    store = RecordingStore({})
    returned = CapturingLLM(_live(1), store).read(**CALL)

    assert returned["mode"] == "capture", "the returned copy"
    stored = store.get(returned["request_key"])
    assert stored["mode"] == "capture", "the STORED copy — the one replayed later"


def test_capture_overrides_the_mode_and_ONLY_the_mode():
    """``recorded`` stays ``False`` through a capture, and that is not an
    oversight: the answer came off a provider a moment ago, so *"was this
    replayed?"* is still no. Asserted here so the asymmetry is a checked
    decision rather than a reading of the source."""
    store = RecordingStore({})
    live_payload = _live(2).read(**CALL)
    captured = CapturingLLM(_live(2), store).read(**CALL)

    assert captured["recorded"] is False
    differ = {k for k in live_payload if live_payload[k] != captured.get(k)}
    assert differ == {"mode"}, f"capture changed more than the mode: {differ}"


# ── 4 ── the two fields cannot disagree ────────────────────────────────


def test_mode_and_recorded_can_never_contradict_each_other():
    """MUTATION: flip ``recorded`` to ``False`` in ``replay``.

    ⚠ **Predicted to redden TWO rows** (RULES §12, fifth practice): this one
    and ``test_replayed_reading_is_stamped_recorded_and_cannot_lie_about_the_model``,
    which already claims half of it from a different angle. Written down before
    the run so the older row's prediction being short is a finding about the
    prediction and not a surprise.

    Every client is exercised, so a fourth one added later without an entry
    here is caught by the companion test below rather than silently unchecked.
    """
    store = RecordingStore({})
    payloads = [
        _live(1).read(**CALL),
        CapturingLLM(_live(1), store).read(**CALL),
        RecordedLLM(store, model_id="a-model", model_version="1").read(**CALL),
    ]
    assert {p["mode"] for p in payloads} == set(C.MODES), (
        "the three payloads must cover all three modes, or this guard checks "
        "the invariant on a subset of the clients that can violate it"
    )
    for payload in payloads:
        assert (payload["mode"] == C.MODE_REPLAY) == payload["recorded"], payload["mode"]


# ── 5 ── the closed set is derived from the classes ────────────────────


def test_MODES_is_exactly_the_union_of_the_classes_that_serve_them():
    """MUTATION: drop ``CapturingLLM.MODE`` from ``MODES``.

    ``MODES`` used to be three literals sitting beside three other literals.
    Deriving it means a mode this module offers that no class serves, and a
    class stamping a mode this module does not offer, are both unwritable —
    rather than a hand-copied roster a guard has to compensate for. The SQL
    ``CHECK`` parity guard lives in ``test_l0_credential_custody.py`` and now
    reaches the classes through this.
    """
    declared = {LiveLLM.MODE, CapturingLLM.MODE, RecordedLLM.MODE}
    assert set(C.MODES) == declared
    assert len(C.MODES) == len(declared), "MODES holds a duplicate"
    assert (C.MODE_LIVE, C.MODE_CAPTURE, C.MODE_REPLAY) == (
        LiveLLM.MODE, CapturingLLM.MODE, RecordedLLM.MODE,
    )


# ── 6 ── neither field may enter the request key ───────────────────────


def test_the_request_key_does_not_depend_on_the_mode_or_the_level():
    """MUTATION: add a seventh parameter to ``request_key``.

    ⚠ **Asked of the SIGNATURE, not of a list of six strings.** The key is
    documented as *"everything that materially determines a reading"*, and
    neither of these fields does: a set captured at level 1 must replay to a
    client configured at level 2, and a captured answer must replay at all —
    both of which break the moment either value enters the hash. Nothing
    pinned the key's input set before this ship.
    """
    assert set(inspect.signature(recording.request_key).parameters) == {
        "prompt_iri", "prompt_version", "model_id", "model_version",
        "temperature", "source_text",
    }

    store = RecordingStore({})
    captured = CapturingLLM(_live(1), store).read(**CALL)
    # A DIFFERENT level, and the same question: it must still hit.
    replayed = RecordedLLM(store, model_id="a-model", model_version="1").read(**CALL)
    assert replayed["request_key"] == captured["request_key"]
    assert _live(3).read(**CALL)["request_key"] == captured["request_key"]


# ── 7 ── the published contract names both ─────────────────────────────


def test_verify_transport_reports_both_fields_as_stamped_above_the_transport():
    """MUTATION: remove ``"credential_level"`` from the identity tuple.

    Both fields belong to this check by its own name: one comes from the class
    that answered and one from what L0 pushed into it, so a transport can
    supply neither — which is the property ``identity_is_stamped_above_the_
    transport`` is named for.

    ⚠ This check asks PRESENCE, not OVERRIDE. That is now a division of
    labour rather than a weakness: OVERRIDE is asked by
    ``identity_overrides_a_transport_that_supplies_its_own``, against a probe
    the harness fabricates, and the two reds are different diagnoses. Named
    here so this file is not read as proof of more than it shows — it shows
    the two fields reach the payload, not that they are core's.
    """
    report = contract.verify_transport(_transport, prompt_iri=PROMPT,
                                       prompt_version=1, source_text="s")
    check = next(c for c in report.checks
                 if c.name == "identity_is_stamped_above_the_transport")
    assert check.status == contract.PASSED, check.detail

    def _strips(**kwargs):
        return {"answer": "42"}

    class _Stripped(LiveLLM):
        def read(self, **kwargs):
            payload = dict(super().read(**kwargs))
            payload.pop("credential_level")
            return payload

    original = contract._client
    contract._client = lambda t: _Stripped(  # type: ignore[assignment]
        t, model_id="probe", model_version="probe", credential_level=None,
        max_calls=8,
    )
    try:
        stripped = contract.verify_transport(_strips, prompt_iri=PROMPT,
                                             prompt_version=1, source_text="s")
    finally:
        contract._client = original  # type: ignore[assignment]
    failed = next(c for c in stripped.checks
                  if c.name == "identity_is_stamped_above_the_transport")
    assert failed.status == contract.FAILED
    assert "credential_level" in failed.detail


# ── 8 ── an exported set cannot contradict its own responses ───────────


def _store_at(*levels: int) -> RecordingStore:
    store = RecordingStore({})
    for index, level in enumerate(levels):
        CapturingLLM(_live(level), store).read(
            prompt_iri=PROMPT, prompt_version=1, source_text=f"source {index}"
        )
    return store


def test_an_export_declaring_a_level_its_responses_deny_is_refused():
    """MUTATION: refuse only the mixed-level case.

    ⚠ **Door one of two.** Before this ship ``credential_level`` was supplied
    *because the payloads did not carry it*; now they do, so a supplied value
    is no longer merely redundant — it is falsifiable, and an export declaring
    one is a file that disproves itself.
    """
    store = _store_at(1)
    assert import_set(export_set(store, vendor_id="anthropic", credential_level=1))
    with pytest.raises(RecordedSetRefused, match="responses in this set carry"):
        export_set(store, vendor_id="anthropic", credential_level=2)


def test_an_export_of_a_MIXED_set_cannot_be_described_by_one_level():
    """⚠ **Door two.** Mirrors ``replay_config``'s refusal on multiple model
    identities, for the same reason: a manifest half-true of its file reads as
    a broken recording rather than as a wrong declaration. Reachable because
    the level is deliberately NOT part of the request key — see above."""
    store = _store_at(1, 2)
    with pytest.raises(RecordedSetRefused, match="responses in this set carry"):
        export_set(store, vendor_id="anthropic", credential_level=1)
    # …and omitting it is always available.
    assert import_set(export_set(store, vendor_id="anthropic"))


def test_a_set_recorded_BEFORE_this_ship_still_exports_with_a_supplied_level():
    """⚠ **The compatibility door, and it is not a courtesy.**

    ``credential_level`` is deliberately absent from ``REQUIRED_PROVENANCE``
    (as ``recorded`` always has been), so a set recorded before decisions 5 and
    6 still imports. Such a set carries no key at all — which is NOT the same
    as carrying the key with value ``None``, the thing a replayed answer
    legitimately does. Collapsing the two with ``.get()`` would refuse every
    pre-decision set for no verification gain: a set that says nothing cannot
    contradict anything.
    """
    store = _store_at(1)
    legacy = RecordingStore({})
    for key in json.loads(store.to_json()):
        payload = dict(store.get(key))
        payload.pop("credential_level")
        payload.pop("mode")
        legacy.put(key, payload)

    exported = export_set(legacy, vendor_id="anthropic", credential_level=1)
    assert import_set(exported).captured_over["credential_level"] == 1


# ── 9 ── the level that reaches the answer is the RESOLVED one ─────────


class _StubAdapter:
    VENDOR_ID = "stub-provenance"
    SUPPORTED_LEVELS = (1, 3)

    @staticmethod
    def build_transport(**_: Any):
        return _transport


@pytest.fixture()
def stub_vendor() -> Iterator[str]:
    adapters.register(_StubAdapter)  # type: ignore[arg-type]
    try:
        yield _StubAdapter.VENDOR_ID
    finally:
        adapters._REGISTRY.pop(_StubAdapter.VENDOR_ID, None)


def test_the_level_stamped_is_the_one_RESOLVED_not_only_an_explicit_argument(
    stub_vendor,
):
    """MUTATION: in ``build_client``, pass ``credential_level=credential_level``
    instead of the resolved ``level``.

    ⚠ **Two doors, and the mutation is invisible through one of them.** At
    levels 1 and 3 the level may arrive from the RESOLVER rather than from a
    keyword — ``build_client`` falls back to ``resolver.level`` — so a client
    built without an explicit ``credential_level`` would stamp ``None`` while
    every explicit-argument test stayed green. That is the configuration the
    answer most needs to be right about, because it is the one L0 produces.
    """
    resolver = Resolver(fetch=lambda: "sk-not-a-real-key", level=3)

    implicit = C.build_client(
        vendor_id=stub_vendor, mode=C.MODE_LIVE, resolver=resolver,
        model_id="a-model", model_version="1",
    ).read(**CALL)
    assert implicit["credential_level"] == 3, "resolved from the resolver"

    explicit = C.build_client(
        vendor_id=stub_vendor, mode=C.MODE_LIVE, resolver=resolver,
        credential_level=3, model_id="a-model", model_version="1",
    ).read(**CALL)
    assert explicit["credential_level"] == 3, "and from the keyword"
    assert implicit["mode"] == explicit["mode"] == C.MODE_LIVE
