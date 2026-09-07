"""The adapter registry — vendor choice resolved at RUNTIME, never at import.

**Why a registry and not an import** (ADR-0210 decision 3). The user picks a
vendor on first run and can change it later, so the choice is stored data: L0
holds a vendor **id**, and that id is resolved to an adapter at the moment a
client is constructed. An import-time choice cannot satisfy "change it later"
without restarting the process, and a conditional import scattered through
call sites cannot be enumerated.

**What an adapter is.** A module exposing ``VENDOR_ID``, ``SUPPORTED_LEVELS``
and ``build_transport(**kwargs) -> Transport``. Nothing else is required. The
rules every adapter obeys — no repair layer, no free-text fallback, unasked
keys refused rather than stripped, no prompt words, the three credential
mechanisms — live in :mod:`mindsos_llm.seam` and are shared, not
reimplemented.

⚠ **``SUPPORTED_LEVELS`` is a promise about the WIRE.** A first-run picker
offers a user only the credential levels the chosen vendor can actually
honour. Anthropic-direct serves level 1 alone because its API has no expiring
credential; hosted routes serve level 3 because theirs do.

⚠ **``BROKERED_LEVELS`` is a promise about the MODULE, and it is separate on
purpose** (ADR-0210 slice 4). Level 2 says nothing about a provider — the
provider never learns a broker exists. It says this adapter can compose its
request *without a credential* and send it elsewhere, which is a fact about
the adapter's code. One tuple carrying both meanings would make
``SUPPORTED_LEVELS`` unreadable and would force the resolver to become optional
in ``build_transport``.

⟹ **:func:`offerable_levels` is what a picker calls** — the union of the two —
never :data:`~mindsos_llm.credentials.LEVELS`, and never a hardcoded list,
which is how a picker ends up offering a guarantee no adapter keeps.

**Declaring one half of level 2 is refused.** :func:`register` requires
``BROKERED_LEVELS`` and ``build_brokered_transport`` to arrive together: an
adapter advertising a brokered level it cannot build would fail at client
construction, and one shipping a brokered builder it never advertises is code
no picker will ever reach. Both doors, because a registry that checked one
would let the other through.

**Registration is explicit.** No entry-point scanning and no import-time
discovery: an adapter is in this registry because someone put it there, and
``git grep`` finds every vendor core can speak to. A plugin registering itself
by side effect would make that question unanswerable.
"""

from __future__ import annotations

from types import ModuleType
from typing import Any, Callable, Dict, Mapping, Tuple

from . import anthropic as _anthropic


class UnknownVendor(KeyError):
    """A stored vendor id resolves to no registered adapter.

    Loud rather than falling back to a default. A silent default would run a
    user's reading against a provider they did not choose, and the answer would
    carry the wrong provenance while looking correct.
    """


class VendorHasNoBroker(ValueError):
    """This vendor's adapter serves no brokered level.

    Distinct from :class:`UnknownVendor` because the fixes differ: one is a
    vendor id nobody registered, the other is a registered vendor asked for a
    level it never advertised. Collapsing them would report a level mismatch as
    a typo.
    """


_REGISTRY: Dict[str, ModuleType] = {}


def register(adapter: ModuleType) -> ModuleType:
    """Add an adapter. Refuses a duplicate id rather than overwriting.

    Last-write-wins would make the resolved vendor depend on import order,
    which is the kind of thing that is discovered in production.
    """
    for attr in ("VENDOR_ID", "SUPPORTED_LEVELS", "build_transport"):
        if not hasattr(adapter, attr):
            raise ValueError(
                f"an adapter must expose {attr!r}; {adapter!r} does not"
            )
    declares = bool(tuple(getattr(adapter, "BROKERED_LEVELS", ())))
    builds = hasattr(adapter, "build_brokered_transport")
    if declares != builds:
        raise ValueError(
            "an adapter declares BROKERED_LEVELS and exposes "
            "build_brokered_transport together or not at all; "
            f"{adapter!r} has one without the other"
        )
    vendor_id = adapter.VENDOR_ID
    if vendor_id in _REGISTRY and _REGISTRY[vendor_id] is not adapter:
        raise ValueError(
            f"vendor id {vendor_id!r} is already registered to "
            f"{_REGISTRY[vendor_id]!r}; ids are unique so a stored choice "
            "resolves to exactly one wire"
        )
    _REGISTRY[vendor_id] = adapter
    return adapter


def get(vendor_id: str) -> ModuleType:
    """Resolve a stored vendor id to its adapter, or raise."""
    try:
        return _REGISTRY[vendor_id]
    except KeyError:
        raise UnknownVendor(vendor_id) from None


def vendors() -> Tuple[str, ...]:
    """Every registered vendor id, sorted. What a picker lists."""
    return tuple(sorted(_REGISTRY))


def supported_levels(vendor_id: str) -> Tuple[int, ...]:
    """The credential levels this vendor's WIRE can present a credential at.

    ⚠ Not what a picker offers — see :func:`offerable_levels`. A brokered level
    is deliberately absent here, because the wire never sees that credential.
    """
    return tuple(get(vendor_id).SUPPORTED_LEVELS)


def brokered_levels(vendor_id: str) -> Tuple[int, ...]:
    """The levels this vendor's adapter serves with a broker in front of it.

    Empty for an adapter that cannot compose its request without a credential.
    """
    return tuple(getattr(get(vendor_id), "BROKERED_LEVELS", ()))


def offerable_levels(vendor_id: str) -> Tuple[int, ...]:
    """Every level this vendor can be configured at, sorted. **What a picker
    calls, and what L0 validates a stored level against.**

    The union of the wire's levels and the brokered ones. Two questions with
    one answer here, because a user choosing a level does not care which half
    of the mechanism serves it — but everything below this function does, which
    is why the halves stay separate everywhere else.
    """
    return tuple(sorted(set(supported_levels(vendor_id)) | set(brokered_levels(vendor_id))))


def build_transport(vendor_id: str, **kwargs: Any) -> Callable[..., Mapping[str, Any]]:
    """Resolve and build in one step — the call a client construction makes."""
    return get(vendor_id).build_transport(**kwargs)


def build_brokered_transport(
    vendor_id: str, **kwargs: Any
) -> Callable[..., Mapping[str, Any]]:
    """The level-2 twin. Refuses a vendor that advertises no brokered level.

    ⚠ Checked here rather than left to an ``AttributeError``: the registration
    rule above keeps the declaration and the builder together, so a vendor
    reaching this function without one has none, and saying so names the
    configuration that is wrong.
    """
    adapter = get(vendor_id)
    if not brokered_levels(vendor_id):
        raise VendorHasNoBroker(
            f"vendor {vendor_id!r} declares no brokered level; a broker cannot "
            "be put in front of a wire that has no way to be composed unsigned"
        )
    return adapter.build_brokered_transport(**kwargs)


register(_anthropic)

__all__ = [
    "UnknownVendor",
    "VendorHasNoBroker",
    "brokered_levels",
    "build_brokered_transport",
    "build_transport",
    "get",
    "offerable_levels",
    "register",
    "supported_levels",
    "vendors",
]
