"""F9 — capacity re-activation factory registry (ADR-0185).

Descriptor-driven re-activation of learned (and, in principle, bundle)
capacities after a process restart, **without serializing Python
callables**. The durable artifact is the L2 ``learned-parameters``
descriptor (a plain ``dict``); the L3 capacity node and its
``implementation`` are per-process and re-minted here via a registered
factory.

Layer boundary (test-enforced — ``tests/phase_28`` "no upward import"):
this module is pure ``mindsos_capacity``. It never imports
``mindsos_knowledge`` (the descriptor's storage role) or
``mindsos_server`` (the lifecycle). It therefore operates on plain
descriptor dicts. The KL-walking glue that reads the
``learned-parameters`` role-graph nodes out of a user's Local and feeds
their value-dicts to :func:`reactivate_from_descriptors` lives in
``mindsos_server`` (which may import both layers).

Descriptor contract (PB-F — the descriptor must self-describe). A
re-activatable ``learned-parameters`` value dict carries, in addition to
the shipped taught-composite fields (``capability``, ``steps``,
``requires_affordances``, ``cache_key``, ``source``):

* ``reactivation_key`` — names the factory that rebuilds the capacity.
  Absence, or the reserved value :data:`INSTALLER_SENTINEL`, marks the
  descriptor as **not** Local-re-activatable (it re-activates by
  re-running its installer per ADR-0183 — the negative path).

The factory owns *all* reconstruction (name, category, inputs, outputs,
node_kind, and the bound ``implementation``), so this module stays
generic and never edge-walks or touches ``to_properties``. A factory is
typically registered by the consumer at process boot, closing over any
live runtime handles its implementation needs (e.g. a demo's
``run_step``) — those handles are exactly what cannot be serialized, so
they are re-supplied each process rather than reloaded.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping

from .capacity import _CapacityBase
from .exceptions import CapacityRegistrationError

#: Descriptor key (in the ``learned-parameters`` value dict) naming the
#: factory that rebuilds the capacity. See module docstring.
REACTIVATION_KEY = "reactivation_key"

#: Reserved ``reactivation_key`` value: the capacity is NOT
#: Local-re-activatable from its descriptor; it re-activates by re-running
#: its installer (ADR-0183), not by this Local walk.
INSTALLER_SENTINEL = "installer"

#: A factory rebuilds a fully-bound declaration from a descriptor dict.
ReactivationFactory = Callable[[Mapping[str, Any]], _CapacityBase]

_FACTORIES: Dict[str, ReactivationFactory] = {}


class ReactivationError(CapacityRegistrationError):
    """A descriptor could not be re-activated (unknown/invalid key, or a
    factory returned a non-declaration)."""


def register_reactivation_factory(
    key: str,
    fn: ReactivationFactory,
    *,
    if_exists: str = "raise",
) -> None:
    """Register the factory that rebuilds capacities of kind ``key``.

    ``if_exists="upsert"`` re-binds the factory (process-local
    last-registration-wins; mirrors the capacity-declaration rebind).
    ``key`` must be a non-empty string and may not be the reserved
    :data:`INSTALLER_SENTINEL`.
    """
    if not isinstance(key, str) or not key:
        raise ReactivationError(
            f"reactivation key must be a non-empty str, got {key!r}"
        )
    if key == INSTALLER_SENTINEL:
        raise ReactivationError(
            f"{INSTALLER_SENTINEL!r} is reserved (marks non-re-activatable "
            "descriptors); it may not name a factory"
        )
    if key in _FACTORIES and if_exists == "raise":
        raise ReactivationError(
            f"reactivation factory {key!r} already registered "
            "(pass if_exists='upsert' to re-bind)"
        )
    _FACTORIES[key] = fn


def unregister_reactivation_factory(key: str) -> bool:
    """Remove a factory. Returns ``True`` if one was present."""
    return _FACTORIES.pop(key, None) is not None


def reactivation_factories() -> Dict[str, ReactivationFactory]:
    """Return a copy of the current factory registry (introspection)."""
    return dict(_FACTORIES)


def is_reactivatable(descriptor: Mapping[str, Any]) -> bool:
    """True iff ``descriptor`` carries a re-activatable ``reactivation_key``."""
    key = descriptor.get(REACTIVATION_KEY)
    return bool(key) and key != INSTALLER_SENTINEL


def build_declaration(key: str, descriptor: Mapping[str, Any]) -> _CapacityBase:
    """Rebuild a fully-bound declaration via the registered ``key`` factory."""
    fn = _FACTORIES.get(key)
    if fn is None:
        raise ReactivationError(
            f"no reactivation factory registered for key {key!r}; "
            f"known={sorted(_FACTORIES)}"
        )
    decl = fn(descriptor)
    if not isinstance(decl, _CapacityBase):
        raise ReactivationError(
            f"reactivation factory {key!r} returned "
            f"{type(decl).__name__}, expected a Capacity/Monitor/Adapter"
        )
    return decl


def reactivate_from_descriptors(
    cl: Any,
    descriptors: Any,
    *,
    session: Any,
) -> List[str]:
    """Re-activate Local capacities from ``learned-parameters`` descriptors.

    For each descriptor carrying a re-activatable ``reactivation_key``,
    build the declaration via its factory and (re-)register it on the
    Local (``session``-scoped, so it targets the user's Local capacity
    metagraph and skips the Global-write gate) with
    ``if_exists="upsert"`` — so a re-run is idempotent and the ADR-0156
    §amendment-1 rebind binds the freshly minted ``implementation`` that
    ``invoke`` resolves through ``_declarations``. Referenced Global
    DataStates are mirrored Local-side by ``register_capacity`` itself
    (ADR-0185 §A2′), so no DataState step is needed here.

    Descriptors without a re-activatable key are skipped (they
    re-activate via their installer, ADR-0183 — not from this walk).

    Args:
        cl: the :class:`~mindsos_capacity.CapacityLayer`.
        descriptors: an iterable of descriptor dicts (the
            ``learned-parameters`` node value dicts).
        session: a Local-scoped session-like object (needs ``user_id``);
            supplied by the caller — this module never constructs a
            ``Session`` (layer boundary).

    Returns:
        The list of re-activated capacity IRIs, in walk order.
    """
    reactivated: List[str] = []
    for descriptor in descriptors:
        key = descriptor.get(REACTIVATION_KEY)
        if not key or key == INSTALLER_SENTINEL:
            continue
        decl = build_declaration(key, descriptor)
        cl.register_capacity(decl, session=session, if_exists="upsert")
        reactivated.append(decl.iri)
    return reactivated
