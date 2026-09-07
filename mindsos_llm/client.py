"""Build the per-session client from what L0 resolved (ADR-0210 decision 7).

**Why per session.** Different users have different vendors, different
credential levels and different modes, so one client built at startup cannot
serve them. L0 resolves *that user's* vendor id, level, mode and a credential
resolver, and pushes all four in here. This module resolves the vendor id to an
adapter, builds the wire, and wraps it in whichever client the mode names.

⚠ **The push direction is the security property, and it is why this function
takes plain arguments rather than an L0 object.** ``mindsos_llm`` is a domain
package (ADR-0010 §I-S1) and never imports ``mindsos_server``, so the module
that makes the network call is structurally unable to read the store the
credential came from. Naming an L0 type in this signature would end that,
which is why the signature is scalars and a callable.

⚠ **This function never CALLS the resolver.** It hands the callable to the
transport, which asks for a credential inside one request and lets the frame
return. A credential fetched here would be a free variable of everything built
below — round one of the credential review, argued in
:mod:`mindsos_llm.credentials`.

**Replay resolves nothing, and that is enforced rather than assumed.** A
replay client answers from a file: it needs no vendor wire and no credential,
so passing a resolver is refused. The refusal is the point — a resolver
reaching this path means somebody released a credential through L0's
capability gate and wrote an audit row for a run that never went near a
provider. That is not harmless; it is a false entry in the record of when
credentials were used. A broker endpoint on that path is refused for the same
reason, one step further out: it names a service the run will never contact.

**Level 2 is the one level with no resolver at all** (ADR-0210 slice 4), and
:data:`~mindsos_llm.credentials.LEVEL_NEVER_KNOWN` is what selects the path
here — not the presence of a broker URL. The level is what L0 stores and what
is stamped on the answer, so it is the thing that decides; a URL is
deployment configuration that the chosen level then requires.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from . import adapters
from .credentials import LEVEL_NEVER_KNOWN, Resolver
from .live import CapturingLLM, LiveLLM
from .recording import RecordingStore
from .replay import RecordedLLM

#: Answer from the provider.
MODE_LIVE = "live"

#: Answer from the provider and save every answer into the store, so a set can
#: be recorded from a real run rather than hand-written.
MODE_CAPTURE = "capture"

#: Answer from a recorded set. No vendor, no credential, no network.
MODE_REPLAY = "replay"

#: The closed set, stamped on every answer (ADR-0210 decision 5). ⚠ It is
#: duplicated as a SQL ``CHECK`` on ``mindsos_server``'s ``llm_config`` table,
#: because a constraint cannot import Python; a parity guard pins the two
#: together so the pair cannot drift the way a hand-copied roster does.
MODES = (MODE_LIVE, MODE_CAPTURE, MODE_REPLAY)


class UnknownMode(ValueError):
    """A stored mode is not one this package can serve.

    Loud rather than defaulting to live: a mode silently promoted to live
    would make a real provider call for a user who asked for replay, and the
    answer would be stamped with a mode that did not produce it.
    """


class ModeRequiresStore(ValueError):
    """``capture`` and ``replay`` name a recorded set; ``live`` must not."""


class ReplayNeedsNoCredential(ValueError):
    """A resolver, or a broker, reached the one path that answers from a file.

    See the module docstring: this is a false entry in the record of when
    credentials were released, not a harmless extra argument.
    """


class CredentialLevelUnsupportedByVendor(ValueError):
    """The stored level is one this vendor can neither present nor broker.

    Checked against ``adapters.offerable_levels`` — the union of the wire's
    levels and the brokered ones — because a picker offers that union and a
    stored level is only ever one of the two halves.
    """


class LevelTwoIsBrokered(ValueError):
    """Level 2 means a broker holds the credential, and three things deny it.

    A resolver passed at level 2 (there is nothing for MindsOS to resolve); a
    missing broker endpoint at level 2 (the credential has nowhere to be added);
    and a broker endpoint at any other level (the credential is already being
    presented on the wire, so a broker in front of it would add a second one).
    One class, three sentences: the fixes differ, and the message names which.
    """


def build_client(
    *,
    vendor_id: str,
    mode: str,
    resolver: Optional[Resolver] = None,
    credential_level: Optional[int] = None,
    broker_url: Optional[str] = None,
    model_id: str,
    model_version: str,
    store: Optional[RecordingStore] = None,
    temperature: float = 0.0,
    timeout_s: float = 30.0,
    max_calls: int = 200,
    **transport_kwargs: Any,
) -> Any:
    """Resolve a stored configuration into the client that serves it.

    Args:
        vendor_id: L0's stored choice, resolved through :mod:`.adapters`.
        mode: one of :data:`MODES`.
        resolver: the callable L0 released. Required for ``live`` and
            ``capture`` at levels 1 and 3; **refused** at level 2 and for
            ``replay``.
        credential_level: L0's stored level, checked against the vendor's
            ``offerable_levels``. Defaults to the resolver's own level, and is
            therefore **required** at level 2, where there is no resolver to
            take it from.
        broker_url: the level-2 broker this deployment runs. Required at level
            2, refused at every other level.
        store: the recorded set. Required for ``capture`` and ``replay``;
            refused for ``live``, because a store passed to a live client is
            silently unused and the caller meant ``capture``.
        **transport_kwargs: passed to the adapter's builder
            (``resolve_prompt``, ``tool_name``, ``tool_description``, …).
    """
    if mode not in MODES:
        raise UnknownMode(f"mode must be one of {MODES!r}, got {mode!r}")

    if mode == MODE_REPLAY:
        if resolver is not None:
            raise ReplayNeedsNoCredential(
                "a replay client answers from a file and reaches no provider; "
                "releasing a credential for it writes an audit row for a "
                "credential that was never used"
            )
        if broker_url is not None:
            raise ReplayNeedsNoCredential(
                "a replay client answers from a file and contacts no broker; "
                "naming one records a service this run will never reach"
            )
        if store is None:
            raise ModeRequiresStore("replay needs the recorded set to replay")
        return RecordedLLM(
            store,
            model_id=model_id,
            model_version=model_version,
            temperature=temperature,
        )

    level = credential_level
    if level is None:
        if resolver is None:
            raise ValueError(
                f"mode {mode!r} calls a provider and needs either a resolver "
                "or an explicit credential_level"
            )
        level = resolver.level

    if level == LEVEL_NEVER_KNOWN:
        if resolver is not None:
            raise LevelTwoIsBrokered(
                "level 2 means the broker holds the credential and MindsOS "
                "never sees it; a resolver here is a credential this process "
                "was not meant to be able to obtain"
            )
        if broker_url is None:
            raise LevelTwoIsBrokered(
                "level 2 needs the broker endpoint that adds the credential; "
                "without one the request would reach the provider unsigned"
            )
    else:
        if resolver is None:
            raise ValueError(f"mode {mode!r} calls a provider and needs a resolver")
        if broker_url is not None:
            raise LevelTwoIsBrokered(
                f"a broker endpoint is level {LEVEL_NEVER_KNOWN}; at level "
                f"{level!r} the credential is presented on the wire, and a "
                "broker in front of that would add a second one"
            )

    if mode == MODE_CAPTURE and store is None:
        raise ModeRequiresStore("capture needs the store it captures into")
    if mode == MODE_LIVE and store is not None:
        raise ModeRequiresStore(
            "a live client writes to no store; a store here means the caller "
            "meant capture, and silently ignoring it would lose the recording"
        )

    serves = adapters.offerable_levels(vendor_id)
    if level not in serves:
        raise CredentialLevelUnsupportedByVendor(
            f"vendor {vendor_id!r} can be configured at credential levels "
            f"{serves!r}, not {level!r}"
        )

    transport: Callable[..., Any]
    if level == LEVEL_NEVER_KNOWN:
        transport = adapters.build_brokered_transport(
            vendor_id,
            broker_url=broker_url,
            model_id=model_id,
            **transport_kwargs,
        )
    else:
        transport = adapters.build_transport(
            vendor_id,
            resolve_credential=resolver,
            model_id=model_id,
            **transport_kwargs,
        )
    live = LiveLLM(
        transport,
        model_id=model_id,
        model_version=model_version,
        temperature=temperature,
        timeout_s=timeout_s,
        max_calls=max_calls,
    )
    if mode == MODE_CAPTURE:
        return CapturingLLM(live, store)
    return live


__all__ = [
    "MODES",
    "MODE_CAPTURE",
    "MODE_LIVE",
    "MODE_REPLAY",
    "CredentialLevelUnsupportedByVendor",
    "LevelTwoIsBrokered",
    "ModeRequiresStore",
    "ReplayNeedsNoCredential",
    "UnknownMode",
    "build_client",
]
