"""How a credential reaches the wire, and how far it gets.

**MindsOS never stores a credential and never asks for one.** It asks for a
*way to get one*, at the moment of the call, and forgets it immediately after.
That is the whole of the design; everything below is the shape of "a way to
get one" and the honest limits of each shape.

**Three levels, offered as each adapter supports them** (ADR-0210). The user
picks on first run and can change later, so the level is stored data, not a
code path chosen at import:

* :data:`LEVEL_NEVER_STORED` — the credential lives in the user's keychain or
  environment. MindsOS calls :class:`CredentialResolver` at call time, builds
  the header, and scrubs it after. It holds the value for the duration of one
  request and writes it nowhere.
* :data:`LEVEL_NEVER_KNOWN` — a broker the user runs holds the credential and
  adds it. ⚠ **This is NOT a resolver and must never be modelled as one.**
  The credential does not reach MindsOS at all, so there is nothing to
  resolve: it is a different request path, and it belongs in a wrapper AROUND
  an adapter rather than in a plug INTO one. A "resolver that returns nothing"
  would be a lie with a return type.
* :data:`LEVEL_SHORT_LIVED` — the resolver returns a scoped token that
  expires, so a leak expires with it.

⚠ **LEVEL IS A PROPERTY OF THE ADAPTER, NOT OF MindsOS.** An adapter declares
which levels it can serve and the picker offers only those. Anthropic's direct
Messages API authenticates with a long-lived key and has no token-exchange
flow, so its adapter declares level 1 alone; expiring credentials arrive with
the hosted routes (Bedrock, Vertex, Azure), which are different adapters with
different wire shapes. Promising level 3 generically would promise something
no adapter could deliver.

**The interface is deliberately identical across levels.** A resolver
returning a static key and one returning a rotating token are the same
callable to everything above them, which is why level 3 costs nothing to
prepare for now: the adapter does not know or care which it got.

⚠ **REFRESH IS NOT A RETRY.** ``mindsos_llm.contract`` requires a transport
not to retry silently, and a token that expires mid-call would otherwise force
exactly that. So :meth:`CredentialResolver.expires_at` exists and refresh
happens **before** a call when the credential is near expiry — never as a
reaction to a rejection. **A 401 is a failure.** A resolver that quietly
re-mints on rejection turns one call into two and makes the census of what
was actually sent unknowable, which is the property the no-silent-retry rule
exists to protect.

**What this module does NOT do.** It does not read the keychain, the
environment, or L0's store. It defines the shape of the thing that does, and
that thing is supplied from outside — L0 owns the user's vendor id, level,
mode and credential custody, and **pushes a resolver in** at client
construction. ``mindsos_llm`` never imports ``mindsos_server``
(ADR-0010 §I-S1, pinned by
``tests/llm_seam/test_import_isolation_mindsos_llm.py``), so the module that
makes the network call is structurally unable to read the store the
credential came from. That is the point, not a side effect.
"""

from __future__ import annotations

import time
from typing import Callable, Optional, Protocol, runtime_checkable

#: The credential never leaves the user's keychain or environment except for
#: the duration of one request, and is scrubbed from the composed request
#: afterwards.
LEVEL_NEVER_STORED = 1

#: A broker the user runs holds the credential; MindsOS never sees its value.
#: ⚠ Not a resolver — see the module docstring.
LEVEL_NEVER_KNOWN = 2

#: The resolver returns a short-lived scoped token, so a leak expires.
LEVEL_SHORT_LIVED = 3

#: Every level, in the order a picker should offer them. Membership here is
#: not a promise that any given adapter serves the level — ask the adapter.
LEVELS = (LEVEL_NEVER_STORED, LEVEL_NEVER_KNOWN, LEVEL_SHORT_LIVED)

#: Human-facing, and deliberately phrased as what the user gets rather than
#: as a mechanism. Rendered by a picker; never composed into an error.
LEVEL_PHRASES = {
    LEVEL_NEVER_STORED: "kept on this machine and never stored by MindsOS",
    LEVEL_NEVER_KNOWN: "held by a service you run, so MindsOS never sees it",
    LEVEL_SHORT_LIVED: "a short-lived token that expires on its own",
}

#: How close to expiry counts as "refresh before the next call". Generous on
#: purpose: the cost of refreshing early is one extra mint, and the cost of
#: refreshing late is a mid-flight 401 that looks like a silent retry.
REFRESH_MARGIN_S = 60.0


class CredentialUnavailable(RuntimeError):
    """The credential could not be obtained.

    Fixed prose, and it names no vendor, no store, no environment variable and
    no user. It can reach a page through ``LLMCallFailed``; the operator detail
    belongs on ``__cause__``.
    """

    MESSAGE = (
        "the reading service is not configured to sign in. This is a fault on "
        "our side and is never a finding about the case."
    )

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


@runtime_checkable
class CredentialResolver(Protocol):
    """``() -> str``, plus an optional expiry.

    ⚠ **A CALLABLE, NOT A CREDENTIAL, and that is load-bearing rather than
    stylistic.** A credential passed as a value becomes a free variable of
    every closure that can see it, and therefore lives in the frame locals of
    every raised link on a traceback. That exposure was found by review and the
    fix was to make the credential something you *ask for*, so that only the
    frame that asks holds it and that frame always returns.

    :meth:`expires_at` returns a POSIX timestamp, or ``None`` for a credential
    that does not expire. It exists so refresh can be deliberate — see the
    module docstring on why a reactive refresh is indistinguishable from the
    silent retry the transport contract forbids.
    """

    def __call__(self) -> str: ...


def static_resolver(fetch: Callable[[], str]) -> "Resolver":
    """Wrap a plain ``() -> str`` as a level-1 resolver.

    ``static_resolver(lambda: os.environ["SOME_KEY"])`` is the whole of level 1
    from a deployment's side. The lambda is evaluated per call, so a rotated
    environment value is picked up without reconstructing the client.
    """
    return Resolver(fetch=fetch, level=LEVEL_NEVER_STORED, expires_at=None)


class Resolver:
    """The concrete resolver every adapter receives.

    Carries its level so the level can be stamped on an answer (ADR-0210
    decision 6 — the level is not a secret, and it determines how reproducible
    the answer is).
    """

    __slots__ = ("_fetch", "_level", "_expires_at")

    def __init__(
        self,
        *,
        fetch: Callable[[], str],
        level: int,
        expires_at: Optional[Callable[[], Optional[float]]] = None,
    ) -> None:
        if not callable(fetch):
            raise TypeError(
                "fetch must be a callable, not a credential - a credential "
                "passed as a value is live in the frame locals of every raised "
                "link on a traceback"
            )
        if level not in LEVELS:
            raise ValueError(f"level must be one of {LEVELS!r}, got {level!r}")
        self._fetch = fetch
        self._level = int(level)
        self._expires_at = expires_at

    @property
    def level(self) -> int:
        return self._level

    def expires_at(self) -> Optional[float]:
        """POSIX expiry, or ``None`` for a credential that does not expire."""
        return self._expires_at() if self._expires_at is not None else None

    def needs_refresh(self, *, now: Optional[float] = None) -> bool:
        """True when the credential is close enough to expiry to re-mint NOW.

        Callers refresh **before** the call. A resolver that re-mints in
        reaction to a rejection would turn one call into two and make the
        census of what was actually sent unknowable — the exact property
        ``no_silent_retry`` protects.
        """
        expiry = self.expires_at()
        if expiry is None:
            return False
        return (now if now is not None else time.time()) >= expiry - REFRESH_MARGIN_S

    def __call__(self) -> str:
        """Fetch the credential. Raises :class:`CredentialUnavailable`.

        The value is returned to exactly one caller — the header builder — and
        that function always returns, so its frame is off every traceback
        before anything downstream can raise.
        """
        try:
            value = self._fetch()
        except Exception as exc:
            raise CredentialUnavailable() from exc
        if not isinstance(value, str) or not value:
            raise CredentialUnavailable()
        return value


__all__ = [
    "LEVELS",
    "LEVEL_NEVER_KNOWN",
    "LEVEL_NEVER_STORED",
    "LEVEL_PHRASES",
    "LEVEL_SHORT_LIVED",
    "REFRESH_MARGIN_S",
    "CredentialResolver",
    "CredentialUnavailable",
    "Resolver",
    "static_resolver",
]
