"""
argon2id password hashing helpers for the Server Layer.

Private module (underscore-prefixed); the public surface is
:func:`mindsos_server.users.verify` and friends.

Phase 18 ships:

* :data:`PRODUCTION_PARAMS` — ADR-0003 verbatim (time_cost=3,
  memory_cost=65536 KiB, parallelism=4).
* :data:`_TEST_FAST_PARAMS` — low-cost variant for the test suite per
  Phase 18 PB-14. Tests pass explicitly; production never uses these.
* :func:`hash_password` / :func:`verify_password` — thin wrappers over
  ``argon2.PasswordHasher`` that accept a ``Argon2Params`` arg.
* :data:`_SENTINEL_HASH` — precomputed argon2id hash of a fixed
  nonsense string per Phase 18 PB-22 / PB-31. Used by
  :func:`verify_against_sentinel` to close the user-enumeration timing
  leak in :func:`mindsos_server.users.verify`.

Per Phase 18 PB-14, params are passed **explicitly** at every call site;
no env-driven globals. Production callers use ``PRODUCTION_PARAMS``;
test callers pass ``_TEST_FAST_PARAMS``.
"""

from __future__ import annotations

from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


@dataclass(frozen=True, slots=True)
class Argon2Params:
    """
    argon2id parameter bundle.

    Frozen to prevent accidental mutation across call sites.

    Per Phase 18 PB-14: production callers use :data:`PRODUCTION_PARAMS`
    (matching ADR-0003 verbatim); test callers use
    :data:`_TEST_FAST_PARAMS`. There is no env-var override and no
    global default — params are an explicit argument at every hash /
    verify boundary.
    """

    #: Number of iterations. ADR-0003 = 3.
    time_cost: int

    #: Memory cost in KiB. ADR-0003 = 65536 (64 MiB).
    memory_cost: int

    #: Parallel lanes. ADR-0003 = 4.
    parallelism: int

    #: Output hash length in bytes. argon2-cffi default = 32.
    hash_len: int = 32

    #: Salt length in bytes. argon2-cffi default = 16.
    salt_len: int = 16

    def hasher(self) -> PasswordHasher:
        """Return an argon2 ``PasswordHasher`` configured with these params."""
        return PasswordHasher(
            time_cost=self.time_cost,
            memory_cost=self.memory_cost,
            parallelism=self.parallelism,
            hash_len=self.hash_len,
            salt_len=self.salt_len,
        )


#: Production argon2id parameters per ADR-0003 §Decision (verbatim).
#: All real user-create / verify calls use this. Renaming or relaxing is
#: a security-impacting change; see ADR-0003 §Rationale.
PRODUCTION_PARAMS: Argon2Params = Argon2Params(
    time_cost=3,
    memory_cost=65536,  # 64 MiB
    parallelism=4,
)


#: Test-only fast parameters per Phase 18 PB-14.
#:
#: Trades cryptographic strength for test-suite speed: production
#: argon2id at PRODUCTION_PARAMS is ~100ms per hash; the cumulative
#: test suite would pay seconds. _TEST_FAST_PARAMS targets ~5ms per
#: hash while still exercising the same argon2id code path.
#:
#: NEVER use in production. Convention is enforced by code review +
#: the fact that nothing in the production import chain references
#: this constant.
_TEST_FAST_PARAMS: Argon2Params = Argon2Params(
    time_cost=1,
    memory_cost=8,  # 8 KiB — minimum that argon2-cffi accepts
    parallelism=1,
)


def hash_password(password: str, *, params: Argon2Params) -> str:
    """
    Hash a plaintext password with argon2id at the given params.

    Returns the standard ``$argon2id$...`` encoded hash for storage in
    ``users.password_hash``. Caller is responsible for choosing params
    appropriate to the context (production callers pass
    :data:`PRODUCTION_PARAMS`; tests pass :data:`_TEST_FAST_PARAMS`).

    Per Phase 18 PB-14 there is no default — params are explicit at
    every call site.
    """
    return params.hasher().hash(password)


def verify_password(stored_hash: str, password: str, *, params: Argon2Params) -> bool:
    """
    Constant-time verify a plaintext password against a stored argon2id hash.

    Returns True on match, False on mismatch. Does NOT raise on
    mismatch — the caller (typically :func:`mindsos_server.users.verify`)
    decides whether to translate False into an exception (per Phase 18
    PB-23 the translation goes through :class:`AuthFailedError`).

    Other argon2 verify errors (corrupt hash, parameter mismatch) DO
    propagate — they indicate data corruption, not auth failure, and
    deserve to be visible.

    The ``params`` arg is plumbed for future rehash-on-cost-bump logic;
    argon2's verify is parameter-self-describing (cost params live in
    the hash string) so the explicit arg is currently advisory only.
    Carried for symmetry with :func:`hash_password` and as the
    extension point for ADR-0003's "Password changes rehash with a
    fresh salt" requirement (Phase 22 password-change consumer).
    """
    try:
        params.hasher().verify(stored_hash, password)
        return True
    except VerifyMismatchError:
        return False


def _precompute_sentinel_hash() -> str:
    """
    Compute the module-load-time sentinel hash.

    Factored out as a function for clarity + to make the test harness
    able to assert "module constant exists + is parseable as argon2id".
    Called exactly once at import.

    The plaintext is a fixed nonsense string baked into source. Per
    Phase 18 PB-31, argon2's one-wayness makes the bake-in safe: knowing
    the plaintext + the hash reveals nothing about any real user's
    password. The bake avoids paying argon2 cost at every process start.
    """
    return PRODUCTION_PARAMS.hasher().hash(
        # Fixed nonsense string. Not a secret; presence in source is intentional.
        "phase-18-sentinel-not-a-real-password"
    )


#: Precomputed argon2id hash of a fixed nonsense string per Phase 18
#: PB-22 / PB-31.
#:
#: Used by :func:`verify_against_sentinel` to make
#: :func:`mindsos_server.users.verify` constant-time-ish on user-not-
#: found: instead of returning early (revealing absence via timing),
#: the caller verifies the supplied password against this sentinel,
#: then raises :class:`AuthFailedError` with cause UNKNOWN_USER.
#:
#: Computed at import time. Cost is one-shot per process (~100ms).
#: Acceptable because CLI processes are typically short-lived and run
#: a single user-store operation; the alternative ("precompute at
#: build time and bake into source") was rejected for portability
#: (the encoded hash includes a salt, so it's not naturally a
#: source-literal).
_SENTINEL_HASH: str = _precompute_sentinel_hash()


def verify_against_sentinel(password: str, *, params: Argon2Params) -> None:
    """
    Run argon2id verify against the module-level sentinel hash.

    Always returns None; never raises. The point is to consume the
    same wall-clock time argon2 verification would consume against a
    real hash, closing the timing differential that would otherwise
    leak user existence on the user-not-found path.

    Per Phase 18 PB-22 — verify() in users.py calls this on
    ``UNKNOWN_USER`` before raising :class:`AuthFailedError`.
    """
    try:
        params.hasher().verify(_SENTINEL_HASH, password)
    except VerifyMismatchError:
        # Expected — the sentinel hash never matches any real password.
        pass
    except Exception:  # noqa: BLE001 — defensive: don't let argon2 internals leak as auth fail
        # If argon2 raises something else (corrupt hash, parameter mismatch),
        # the leak-closing call already burned the wall-clock time we needed.
        # Swallow; the caller is about to raise AuthFailedError anyway.
        pass
