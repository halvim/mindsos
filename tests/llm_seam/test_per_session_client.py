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


def _brokered(**over):
    """A level-2 client: no resolver, a broker endpoint, an explicit level."""
    kw = dict(vendor_id="anthropic", mode=C.MODE_LIVE, credential_level=2,
              broker_url="http://127.0.0.1:8787", **MODEL, **WIRE)
    kw.update(over)
    return C.build_client(**kw)


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
    """MUTATION: drop the ``resolver is None`` arm reached with no stored level.

    ⚠ The ``match`` is a correction rather than thoroughness: a bare
    ``pytest.raises(ValueError)`` here could not tell this refusal from any
    other ``ValueError`` raised further down — and slice 2 recorded two
    designated mutations that came back green for exactly that reason.
    """
    with pytest.raises(ValueError, match="either a resolver or an explicit"):
        C.build_client(vendor_id="anthropic", mode=C.MODE_LIVE, **MODEL, **WIRE)


def test_a_STORED_level_without_a_resolver_is_refused_too():
    """The second door of the same requirement, and a different input.

    With no stored level the refusal comes from the level-derivation arm above;
    with one, that arm is satisfied and it is the provider arm that must
    refuse. A configuration reaching the wire with neither a credential nor a
    broker would compose an unsigned request to the provider.
    """
    with pytest.raises(ValueError, match="needs a resolver"):
        C.build_client(vendor_id="anthropic", mode=C.MODE_LIVE, credential_level=1,
                       **MODEL, **WIRE)


# ---------------------------------------------------------------------------
# The level, against the WIRE
# ---------------------------------------------------------------------------


def test_a_level_the_vendors_wire_cannot_honour_is_refused():
    """MUTATION: delete the ``level not in serves`` branch.

    The twin of ``credential_kinds``' check. That one asks whether the SOURCE
    can produce such a credential; this asks whether the vendor can be
    CONFIGURED at the level at all — ``offerable_levels``, the union of the
    levels its wire can present a credential at and the levels it serves with a
    broker in front of it. A configuration can satisfy either alone: the
    Anthropic direct API has no expiring-credential flow, so level 3 is a
    promise neither half keeps.
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


# ---------------------------------------------------------------------------
# Level 2 — the one level with no resolver at all (ADR-0210 slice 4)
# ---------------------------------------------------------------------------


def test_level_2_REFUSES_a_resolver():
    """MUTATION: drop the ``resolver is not None`` arm of the level-2 branch.

    ⚠ Not a tidiness rule, and not the same refusal as replay's. Level 2 means
    the broker holds the credential and MindsOS never sees it. A resolver here
    is a credential this process was not meant to be ABLE to obtain — so the
    configuration is claiming a guarantee it is simultaneously breaking, and
    every answer recorded under it would carry a level that was not true.
    """
    with pytest.raises(C.LevelTwoIsBrokered, match="never sees it"):
        _brokered(resolver=_CountingResolver())


def test_level_2_without_a_broker_endpoint_is_refused():
    """MUTATION: drop the ``broker_url is None`` arm.

    Without one there is nowhere for the credential to be added, and the
    request would reach the provider unsigned — a failure at the vendor, about
    authentication, from a client that believed it was brokered.
    """
    with pytest.raises(C.LevelTwoIsBrokered, match="needs the broker endpoint"):
        _brokered(broker_url=None)


@pytest.mark.parametrize("level", [1, 3], ids=["level-1", "level-3"])
def test_a_broker_at_any_OTHER_level_is_refused(level):
    """The third door of the same class, and the one a two-case guard misses.

    At any level but 2 the credential is presented on the wire; a broker in
    front of that would add a second one. Parametrized over both remaining
    levels so the check cannot be satisfied by the level-1 case alone.
    """
    with pytest.raises(C.LevelTwoIsBrokered, match="is level 2"):
        _live(credential_level=level, broker_url="http://127.0.0.1:8787")


def test_level_2_builds_a_live_client_and_asks_for_no_credential():
    """The permitting door. ⚠ It is also the whole point of the level: the
    client is built, it will call a provider, and nothing in this process ever
    had a way to obtain the key."""
    client = _brokered(resolver=None)
    assert isinstance(client, LiveLLM)


def test_replay_REFUSES_a_broker_too():
    """MUTATION: drop the ``broker_url is not None`` arm of the replay branch.

    The twin of ``test_replay_REFUSES_a_resolver`` one level out: a replay
    client answers from a file and contacts nothing, so naming a broker records
    a service this run will never reach.
    """
    with pytest.raises(C.ReplayNeedsNoCredential, match="contacts no broker"):
        C.build_client(
            vendor_id="anthropic",
            mode=C.MODE_REPLAY,
            broker_url="http://127.0.0.1:8787",
            store=RecordingStore(),
            **MODEL,
        )
