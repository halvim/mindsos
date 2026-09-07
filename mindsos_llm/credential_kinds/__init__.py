"""The credential-kind registry — where a credential comes FROM, chosen at runtime.

**The symmetry is the design** (owner ruling 2026-09-05). ``adapters`` answers
*which vendors can this deployment speak to*; this registry answers *which
credential sources can this deployment use*. Both are explicit registration, no
entry-point scanning and no import-time discovery, so in both cases ``git grep``
answers the question rather than a running process.

**What L0 stores, and what it does not read.** L0 keeps ``credential_kind`` —
the id below — and a JSON object of that kind's OWN fields, which it never
interprets. It hands the pair here. That split is why core gains **set-time
validation without ever learning what a credential looks like**: a wrong
environment-variable name is refused when the configuration is written, not
discovered at the moment a reading was supposed to happen.

⚠ **The stored value is a POINTER, never a secret**, and the distinction the
levels draw is not the one the phrase "MindsOS never knows your key" suggests.
Level 1 is never **stored**: MindsOS sees the credential for one request and
writes it nowhere. Level 2 is never **known**: a broker the user runs adds it
and MindsOS never sees the value at all. Only level 2 is "never sees it", and a
kind registered here always serves level 1 or 3 — a broker is a wrapper around
an ADAPTER, not a kind, and modelling it as one would be a lie with a return
type (:mod:`mindsos_llm.credentials` argues this at length).

**A kind is a MODULE**, exposing:

* ``KIND_ID`` — the stable id L0 stores.
* ``SUPPORTED_LEVELS`` — the levels this SOURCE can honour, which is a
  different question from the levels the WIRE can honour. Both are checked:
  the adapter's tuple says an expiring credential can be sent, this one says
  an expiring credential can be obtained, and a configuration that satisfies
  one but not the other is a real and otherwise-silent mismatch.
* ``validate(spec)`` — raise on anything unusable. Called when the
  configuration is SET.
* ``build(spec) -> Resolver`` — called when a credential is RELEASED.

Core ships exactly one, :mod:`.env`, per decision 9: an option in a picker that
nothing implements is dead, and a registry with no reference implementation is
a shape nobody has proved fits.
"""

from __future__ import annotations

from types import ModuleType
from typing import Any, Dict, Mapping, Tuple

from ..credentials import Resolver
from . import env as _env


class UnknownCredentialKind(KeyError):
    """A stored ``credential_kind`` resolves to no registered kind.

    Loud rather than falling back to a default, on ``adapters.UnknownVendor``'s
    reasoning: a silent default would fetch a credential from a source the user
    did not choose, and the call would succeed while the provenance lied.
    """


class CredentialLevelUnsupported(ValueError):
    """The stored kind cannot serve the stored credential level.

    ⚠ **This pairing is unchecked anywhere else.** A configuration naming
    ``kind="env"`` with ``level=3`` would otherwise store a claim that the
    credential expires, from a source that mints nothing, and every answer
    recorded under it would carry a level that was never true. The level is
    stamped on answers (ADR-0210 decision 6), so an unchecked pairing corrupts
    provenance rather than merely failing.
    """


_REGISTRY: Dict[str, ModuleType] = {}


def register(kind: ModuleType) -> ModuleType:
    """Add a kind. Refuses a duplicate id rather than overwriting.

    Last-write-wins would make the resolved credential source depend on import
    order — ``adapters.register``'s argument, and it is worse here, because the
    thing whose source became order-dependent is a secret.
    """
    for attr in ("KIND_ID", "SUPPORTED_LEVELS", "validate", "build"):
        if not hasattr(kind, attr):
            raise ValueError(
                f"a credential kind must expose {attr!r}; {kind!r} does not"
            )
    kind_id = kind.KIND_ID
    if kind_id in _REGISTRY and _REGISTRY[kind_id] is not kind:
        raise ValueError(
            f"credential kind {kind_id!r} is already registered to "
            f"{_REGISTRY[kind_id]!r}; ids are unique so a stored choice "
            "resolves to exactly one source"
        )
    _REGISTRY[kind_id] = kind
    return kind


def get(kind_id: str) -> ModuleType:
    """Resolve a stored kind id to its module, or raise."""
    try:
        return _REGISTRY[kind_id]
    except KeyError:
        raise UnknownCredentialKind(kind_id) from None


def kinds() -> Tuple[str, ...]:
    """Every registered kind id, sorted. What a first-run picker lists."""
    return tuple(sorted(_REGISTRY))


def supported_levels(kind_id: str) -> Tuple[int, ...]:
    """The credential levels this SOURCE can honour."""
    return tuple(get(kind_id).SUPPORTED_LEVELS)


def validate(kind_id: str, spec: Mapping[str, Any], *, level: int) -> None:
    """Refuse an unusable configuration at the moment it is SET.

    Two separate refusals, on purpose. An unknown kind is a deployment that
    never registered the source it is naming; a level the kind cannot serve is
    a deployment claiming a property of a credential it has not got. Collapsing
    them would report the second as the first, and the second is the one a
    reader of the audit trail would otherwise never learn about.
    """
    kind = get(kind_id)
    if level not in tuple(kind.SUPPORTED_LEVELS):
        raise CredentialLevelUnsupported(
            f"credential kind {kind_id!r} serves levels "
            f"{tuple(kind.SUPPORTED_LEVELS)!r}, not {level!r}"
        )
    kind.validate(spec)


def build(kind_id: str, spec: Mapping[str, Any], *, level: int) -> Resolver:
    """Build the resolver a stored configuration names.

    Re-validates rather than trusting that storage only ever holds validated
    rows. A spec can reach the table by a migration, a restore or a hand-edit,
    and the failure that costs least is the one at construction.
    """
    validate(kind_id, spec, level=level)
    return get(kind_id).build(spec)


register(_env)

__all__ = [
    "CredentialLevelUnsupported",
    "UnknownCredentialKind",
    "build",
    "get",
    "kinds",
    "register",
    "supported_levels",
    "validate",
]
