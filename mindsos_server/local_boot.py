"""F9 — durable per-device Local lifecycle + re-activation glue (ADR-0186).

Cross-layer orchestration. The server sits above the domain stack and
may import both ``mindsos_knowledge`` (the durable descriptor's storage
role) and ``mindsos_capacity`` (the re-activation registry) — the
``mindsos_capacity`` ⇏ ``mindsos_knowledge`` boundary (test-enforced,
``tests/phase_28``) is exactly why the KL-walking half of re-activation
lives here rather than in ``mindsos_capacity.reactivation``.

Provides the free-function primitives (per Phase 44 CR-3 / PB-38 — not a
``MindsOSServer`` method) that a future server lifecycle, or a demo's
boot loop (robot DM-8), calls on first access to a user's Local:

* :func:`load_or_mint_local` — durable load-or-mint of one user's Local
  Metagraph, install-before-mint safe (PB-O).
* :func:`reactivate_local_capacities` — re-mint the user's learned
  capacities from their persisted ``learned-parameters`` descriptors.
* :func:`boot_local` — the two composed: lazy load-on-first-access for
  one ``user_id``. No global boot scan (PB-D) — enumerate-all-Locals is
  a v2 concern.

Wiring these into actual login/logout stays deferred (Phase 44 CR-3);
F9 provides the durable backing store the ADR-0042 install/extract hooks
will use.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from mindsos_capacity import (
    REACTIVATION_KEY,
    build_declaration,
    composite_dependencies,
    is_reactivatable,
    reactivate_from_descriptors,
)
from mindsos_core import Metagraph
from mindsos_knowledge import ROLE_LEARNED_PARAMETERS
from mindsos_knowledge.bootstrap import kahn_sort
from mindsos_knowledge.exceptions import AlreadyInstalledError

__all__ = [
    "load_or_mint_local",
    "reactivate_local_capacities",
    "boot_local",
]


def load_or_mint_local(
    kl: Any,
    persister: Any,
    user_id: str,
) -> Tuple[Metagraph, bool]:
    """Load a user's durable Local from ``persister``, else lazily mint one.

    Mirrors the demo's ``load_or_mint_global`` and the orchestrator's
    cold-start branch. Returns ``(metagraph, minted)`` where ``minted``
    is ``True`` only when no dump existed and a fresh Local was created.

    Install-before-mint (PB-O): :meth:`KnowledgeLayer.install_local_metagraph`
    refuses with :class:`AlreadyInstalledError` if a Local is already
    present for ``user_id``, and any lazy ``kl.local_metagraph`` access
    would mint+store one first — so a dump must be installed *before* any
    lazy access. Re-entrant: if a Local is already installed this process
    (e.g. a prior access lazily minted it), the existing reference is
    returned rather than raising.

    The ``FalkorDBLocalPersister`` keys by ``user_id`` →
    ``local_knowledge:<user_id>``; a per-device caller pins
    ``device_id == user_id`` so the names collide-match.
    """
    dump = persister.load(user_id)
    if dump is None:
        # Cold start: KL's lazy-create gives the canonically-named
        # Metagraph with the 5 auto-ensured Local role-graphs.
        return kl.local_metagraph(user_id), True
    try:
        kl.install_local_metagraph(user_id, dump)
    except AlreadyInstalledError:
        # Already installed this process — honour the existing reference.
        return kl.local_metagraph(user_id), False
    return dump, False


def _learned_parameter_descriptors(local_mg: Metagraph) -> List[dict]:
    """Read the ``learned-parameters`` descriptor dicts out of a Local.

    The role-graph is auto-ensured on mint/install (all 5 Local roles),
    so its absence is treated as "no taught capacities" rather than an
    error. Only dict-valued nodes are descriptors (ADR-0182 round-trips
    the dict value intact).
    """
    for g in local_mg.graphs.values():
        if getattr(g, "role", None) == ROLE_LEARNED_PARAMETERS:
            return [
                n.value
                for n in g.nodes.values()
                if isinstance(n.value, dict)
            ]
    return []


def _dep_order_descriptors(descriptors: List[dict]) -> List[dict]:
    """Topologically order re-activatable composite descriptors.

    A composite whose serialized DAG references another in-batch
    composite's capacity IRI must re-activate **after** that dependency
    (so a factory closure that resolves a live downstream declaration
    finds it already registered). Within-batch dependencies are derived
    from :func:`mindsos_capacity.composite_dependencies`; the order is
    produced by ``mindsos_knowledge.kahn_sort`` — placed here because
    ``mindsos_capacity`` may not import ``mindsos_knowledge`` (boundary,
    test-enforced), but the server may import both (PB-C).

    Non-re-activatable descriptors (installer-backed; no
    :data:`REACTIVATION_KEY`) are returned unchanged after the ordered
    composites — they re-activate via their installer, not this walk, and
    carry no in-batch dependency.

    A descriptor's IRI is read from its freshly-built declaration (pure
    construction; no registration), so no extra descriptor field is
    needed. Raises ``BootstrapCycleError`` if the composites form a
    dependency cycle.
    """
    reactivatable = [d for d in descriptors if is_reactivatable(d)]
    if len(reactivatable) <= 1:
        return list(descriptors)

    by_iri: Dict[str, dict] = {}
    for d in reactivatable:
        decl = build_declaration(d[REACTIVATION_KEY], d)  # pure build, no register
        by_iri[decl.iri] = d
    iris = set(by_iri)

    applies_after = {
        iri: frozenset(composite_dependencies(d) & iris - {iri})
        for iri, d in by_iri.items()
    }
    ordered_iris = kahn_sort(iris, applies_after)

    ordered = [by_iri[i] for i in ordered_iris]
    others = [d for d in descriptors if not is_reactivatable(d)]
    return ordered + others


def reactivate_local_capacities(
    cl: Any,
    kl: Any,
    user_id: str,
    *,
    session: Any,
) -> List[str]:
    """Re-activate a user's Local capacities from persisted descriptors.

    Reads the ``learned-parameters`` descriptors out of the KL Local
    (``local_knowledge:<user_id>``) — the upward-importing step the
    capacity layer cannot perform — dep-orders any composites
    (:func:`_dep_order_descriptors`), and delegates capacity registration
    to :func:`mindsos_capacity.reactivate_from_descriptors`, which
    (re-)registers each onto the CL Local (``local_capacity:<user_id>``)
    with ``if_exists="upsert"``. Referenced Global DataStates are
    mirrored Local-side by ``register_capacity`` itself (ADR-0185 §A2′).

    ``session`` is a Local-scoped session-like object (needs
    ``user_id``); the caller supplies it (the server owns ``Session``).
    Returns the list of re-activated capacity IRIs, in dependency order.
    """
    local_mg = kl.local_metagraph(user_id)
    descriptors = _learned_parameter_descriptors(local_mg)
    ordered = _dep_order_descriptors(descriptors)
    return reactivate_from_descriptors(cl, ordered, session=session)


def boot_local(
    cl: Any,
    kl: Any,
    persister: Any,
    user_id: str,
    *,
    session: Any,
) -> Tuple[Metagraph, bool, List[str]]:
    """Lazy load-on-first-access for one user's Local.

    Load-or-mint the durable KL Local, then re-activate its learned
    capacities onto the CL. Returns
    ``(metagraph, minted, reactivated_iris)``. Per-``user_id`` (PB-D);
    no global scan.
    """
    mg, minted = load_or_mint_local(kl, persister, user_id)
    reactivated = reactivate_local_capacities(cl, kl, user_id, session=session)
    return mg, minted, reactivated
