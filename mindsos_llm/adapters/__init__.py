"""The adapter registry — vendor choice resolved at RUNTIME, never at import.

**Why a registry and not an import** (ADR-0210 decision 3). The user picks a
vendor on first run and can change it later, so the choice is stored data: L0
holds a vendor **id**, and that id is resolved to an adapter at the moment a
client is constructed. An import-time choice cannot satisfy "change it later"
without restarting the process, and a conditional import scattered through
call sites cannot be enumerated.

**What an adapter is.** A module exposing ``VENDOR_ID``, ``SUPPORTED_LEVELS``
and ``build_transport(**kwargs) -> Transport``. Nothing else. The rules every
adapter obeys — no repair layer, no free-text fallback, unasked keys refused
rather than stripped, no prompt words, the three credential mechanisms — live
in :mod:`mindsos_llm.seam` and are shared, not reimplemented.

⚠ **``SUPPORTED_LEVELS`` is a promise about the WIRE.** A first-run picker
offers a user only the credential levels the chosen vendor can actually
honour. Anthropic-direct serves level 1 alone because its API has no expiring
credential; hosted routes serve level 3 because theirs do.
:func:`supported_levels` is what a picker should call — never a hardcoded
list, which is how a picker ends up offering a guarantee no adapter keeps.

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
    """The credential levels this vendor's wire can honour.

    ⚠ A picker calls this rather than listing
    :data:`~mindsos_llm.credentials.LEVELS`, because membership in that tuple
    is not a promise that any given adapter serves the level.
    """
    return tuple(get(vendor_id).SUPPORTED_LEVELS)


def build_transport(vendor_id: str, **kwargs: Any) -> Callable[..., Mapping[str, Any]]:
    """Resolve and build in one step — the call a client construction makes."""
    return get(vendor_id).build_transport(**kwargs)


register(_anthropic)

__all__ = [
    "UnknownVendor",
    "build_transport",
    "get",
    "register",
    "supported_levels",
    "vendors",
]
