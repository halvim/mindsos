"""Guards for per-session client construction (ADR-0210 decision 7).

The client is built after L0 resolves a user's vendor, level and mode. Four
things can go wrong quietly here, and each has a test below: a mode silently
promoted to live; a credential released for a run that never reaches a
provider; a level that one half of the configuration can serve and the other
cannot; and a credential fetched at construction, where it would become a free
variable of everything built underneath it.
"""

from __future__ import annotations

import pytest

from mindsos_llm import client as C
from mindsos_llm.credentials import Resolver
from mindsos_llm.live import CapturingLLM, LiveLLM
from mindsos_llm.recording import RecordingStore
from mindsos_llm.replay import RecordedLLM

WIRE = dict(
    resolve_prompt=lambda **_: "a prompt",
    tool_name="extract",
    tool_description="extract the fields",
)
MODEL = dict(model_id="a-model", model_version="1")


class _CountingResolver(Resolver):
    """A resolver that records whether anyone asked it for a credential."""

    def __init__(self, level: int = 1) -> None:
        self.calls = 0
        super().__init__(fetch=self._fetch, level=level)

    def _fetch(self) -> str:
        self.calls += 1
        return "sk-not-a-real-key"


def _live(**over):
    kw = dict(vendor_id="anthropic", mode=C.MODE_LIVE, resolver=_CountingResolver(),
              **MODEL, **WIRE)
    kw.update(over)
    return C.build_client(**kw)


# ---------------------------------------------------------------------------
# The mode
# ---------------------------------------------------------------------------


def test_an_unknown_mode_is_refused_never_promoted_to_live():
    """MUTATION: default an unrecognised mode to ``MODE_LIVE``.

    A silent promotion makes a real provider call for a user who asked for
    replay, and stamps the answer with a mode that did not produce it.
    """
    with pytest.raises(C.UnknownMode):
        _live(mode="lve")


def test_live_builds_a_live_client():
    assert isinstance(_live(), LiveLLM)


def test_capture_wraps_the_live_client_in_the_recorder():
    c = _live(mode=C.MODE_CAPTURE, store=RecordingStore())
    assert isinstance(c, CapturingLLM)
    assert isinstance(c._inner, LiveLLM)


def test_replay_answers_from_the_file_and_builds_no_wire():
    c = C.build_client(
        vendor_id="anthropic", mode=C.MODE_REPLAY, store=RecordingStore(), **MODEL
    )
    assert isinstance(c, RecordedLLM)


# ---------------------------------------------------------------------------
# ⚠ Replay resolves nothing — the property that keeps the audit trail honest
# ---------------------------------------------------------------------------


def test_replay_REFUSES_a_resolver():
    """MUTATION: drop the ``resolver is not None`` branch from the replay arm.

    Not a tidiness rule. A resolver arriving here means somebody released a
    credential through L0's capability gate and wrote an audit row saying a
    credential was used — for a run that answered from a file and reached no
    provider. That is a FALSE entry in the record of when credentials were
    released, and the record is the reason the gate exists.
    """
    with pytest.raises(C.ReplayNeedsNoCredential):
        C.build_client(
            vendor_id="anthropic",
            mode=C.MODE_REPLAY,
            resolver=_CountingResolver(),
            store=RecordingStore(),
            **MODEL,
        )


def test_replay_still_needs_the_set_it_replays():
    """The other door of the replay arm's two checks."""
    with pytest.raises(C.ModeRequiresStore):
        C.build_client(vendor_id="anthropic", mode=C.MODE_REPLAY, **MODEL)


# ---------------------------------------------------------------------------
# The store, on both sides
# ---------------------------------------------------------------------------


def test_capture_without_a_store_is_refused():
    with pytest.raises(C.ModeRequiresStore):
        _live(mode=C.MODE_CAPTURE)


def test_live_WITH_a_store_is_refused_rather_than_ignored():
    """MUTATION: ignore ``store`` in the live arm.

    Silently dropping it loses the recording the caller asked for, and the
    run looks successful. A caller who passes a store meant capture.
    """
    with pytest.raises(C.ModeRequiresStore):
        _live(store=RecordingStore())


def test_a_provider_mode_without_a_resolver_is_refused():
    with pytest.raises(ValueError):
        C.build_client(vendor_id="anthropic", mode=C.MODE_LIVE, **MODEL, **WIRE)


# ---------------------------------------------------------------------------
# The level, against the WIRE
# ---------------------------------------------------------------------------


def test_a_level_the_vendors_wire_cannot_honour_is_refused():
    """MUTATION: delete the ``level not in serves`` branch.

    The twin of ``credential_kinds``' check. That one asks whether the SOURCE
    can produce such a credential; this asks whether the WIRE can present one.
    A configuration can satisfy either alone — the Anthropic direct API has no
    expiring-credential flow at all, so level 3 here is a promise nothing on
    the wire keeps.
    """
    with pytest.raises(C.CredentialLevelUnsupportedByVendor):
        _live(credential_level=3)


def test_the_level_falls_back_to_the_resolvers_own():
    """The other door: with no stored level, the resolver's level is used and
    a level-1 resolver against a level-1 wire builds."""
    assert isinstance(_live(credential_level=None), LiveLLM)


def test_an_unregistered_vendor_is_refused_by_the_registry():
    from mindsos_llm.adapters import UnknownVendor

    with pytest.raises(UnknownVendor):
        _live(vendor_id="a-vendor-nobody-registered")


# ---------------------------------------------------------------------------
# ⚠ Construction asks for nothing
# ---------------------------------------------------------------------------


def test_building_a_client_NEVER_asks_the_resolver_for_a_credential():
    """MUTATION: call ``resolver()`` anywhere in ``build_client``.

    The credential is fetched inside one request, by a frame that always
    returns. A value fetched at construction becomes a free variable of the
    transport, the client and every closure built under them — live in the
    frame locals of every raised link on a traceback. That exposure was found
    by review; this is the guard that keeps it closed at the one place a
    convenience fetch would be tempting.
    """
    for mode, store in ((C.MODE_LIVE, None), (C.MODE_CAPTURE, RecordingStore())):
        r = _CountingResolver()
        C.build_client(
            vendor_id="anthropic", mode=mode, resolver=r, store=store, **MODEL, **WIRE
        )
        assert r.calls == 0, f"{mode} fetched the credential at construction"
