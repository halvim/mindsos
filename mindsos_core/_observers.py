"""Observer plumbing for Core remove + persist + after-load events.

Provides a minimal subscribe-style observer API used by ``Graph`` and
``Metagraph`` to notify external consumers (e.g.,
:class:`mindsos_instances.ElementRegistry` and Phase 08's
:class:`mindsos_instances.reconstruction.InstanceLoader`) at three
lifecycle points: remove (Phase 06), persist (Phase 07), and after-load
(Phase 08).

Design (Phase 06 row §F + round-7 P49 B + P65 A; Phase 07 M9 + P96 A;
Phase 08 PB-4 A + RR-9 A):

* Core ships **plumbing only** — no import of ``mindsos_instances``.
  Consumers subscribe by calling ``register_<event>_observer(cb)`` on
  the relevant ``Graph`` or ``Metagraph`` and receive an
  :class:`ObserverHandle` for later unsubscribe.

* **Remove** (Phase 06): precheck-style — callbacks fire BEFORE the
  underlying mutation. A callback that raises aborts the remove.
  Exception isolation: NONE (a raise aborts the originating remove).

* **Persist** (Phase 07): post-commit — callbacks fire AS STEP 3 of
  the 4-step ``MetagraphRepository.persist`` lifecycle (after Core
  writes commit + WAL stamped). A callback that raises leaves
  Core+WAL state consistent but instance-side persistence partial;
  tester convention is to re-run ``persist`` (MERGE-idempotent).
  Exception isolation: NONE (a raise propagates).

* **After-load** (Phase 08 — diverges from persist by design):
  post-load — callbacks fire ONCE after :meth:`MetagraphLoader.load`
  has completed all sub-reads (anchor → graphs → meta-edges →
  meta-hyperedges → intergraph-edges → intergraph-hyperedges per
  R4-1 A locked sequence). **Per-observer exception isolation per
  RR-9 A**: a failing callback is logged + swallowed; subsequent
  callbacks fire; the originating load returns the constructed
  Metagraph unmodified. The locked rationale: a half-rehydrated
  sibling-package (e.g., a failing InstanceLoader) should NOT tear
  down the entire load. Operator surfaces partial-rehydration via
  ``verify`` rather than via the load's call site.

The :class:`ObserverHandle` returned by ``register_*_observer`` methods
exposes an ``unsubscribe()`` method that removes the callback from the
observer list. The handle is the only public surface for unsubscribe.
"""

from __future__ import annotations

import logging
from typing import Callable, List

_log = logging.getLogger(__name__)

#: Type alias for remove-event callbacks. Callback receives the removed
#: element's id string. Phase 06 observers (`ElementRegistry`) examine
#: the id for both ``template_id == id`` matches and
#: ``SubGraphInstance.node_ids/edge_ids`` membership (round-7 P59 A).
RemoveCallback = Callable[[str], None]


class ObserverHandle:
    """Opaque handle returned by ``register_remove_observer``.

    Retain to call ``unsubscribe()`` when the observer should stop
    receiving events. Calling ``unsubscribe()`` more than once is a
    no-op (idempotent).
    """

    __slots__ = ("_callbacks", "_callback", "_subscribed")

    def __init__(
        self,
        callbacks: List[RemoveCallback],
        callback: RemoveCallback,
    ) -> None:
        self._callbacks = callbacks
        self._callback = callback
        self._subscribed = True

    def unsubscribe(self) -> None:
        """Remove the associated callback from the observer list."""
        if self._subscribed and self._callback in self._callbacks:
            self._callbacks.remove(self._callback)
        self._subscribed = False

    @property
    def is_subscribed(self) -> bool:
        return self._subscribed


def _register(
    callbacks: List[RemoveCallback],
    callback: RemoveCallback,
) -> ObserverHandle:
    """Append ``callback`` to ``callbacks`` and return an
    :class:`ObserverHandle`."""
    callbacks.append(callback)
    return ObserverHandle(callbacks, callback)


def _dispatch_precheck(
    callbacks: List[RemoveCallback],
    removed_id: str,
) -> None:
    """Invoke each registered callback with ``removed_id``.

    Per round-7 P65 A: precheck-style — callbacks fire BEFORE the
    originating Core mutation. A callback that raises propagates the
    exception immediately; subsequent callbacks (and the originating
    remove) do not run.
    """
    for callback in callbacks:
        callback(removed_id)


# ── Phase 07 — persist observer (M9 + P96 A 4-step lifecycle) ──────────────

#: Persist-event callback. Receives the :class:`Metagraph` that was just
#: persisted (post-Core-write, post-WAL-commit) so consumers can run
#: sibling-side persistence (e.g., ``mindsos_instances.InstanceRepository``
#: persisting instances after the Core anchors and elements landed).
#:
#: Typed as ``Callable[[Any], None]`` to avoid an import cycle with
#: ``models.metagraph`` — the consumer narrows the type at use site.
PersistCallback = Callable[["object"], None]


def _dispatch_after_persist(
    callbacks: List[PersistCallback],
    metagraph: "object",
) -> None:
    """Invoke each registered persist-callback with the persisted Metagraph.

    Per M9 + P96 A 4-step lifecycle in
    :class:`MetagraphRepository.persist`: callbacks fire AS STEP 3
    (after Core writes succeed at step 1 and WAL entries commit at
    step 2). A callback that raises leaves Core+WAL state consistent
    but instance persistence may be partial; tester convention per
    P33 A is to re-run ``persist`` (MERGE-idempotent).
    """
    for callback in callbacks:
        callback(metagraph)


# ── Phase 08 — after_load observer (RR-9 A + PB-4 A + RPB-9 A) ─────────────

#: After-load callback. Receives the :class:`Metagraph` that was just
#: reconstructed by :meth:`MetagraphLoader.load`. Consumers (e.g.
#: :class:`mindsos_instances.reconstruction.InstanceLoader` and the
#: Phase 09 ``XRefLoader`` per RR-10 A) use this to populate sibling-
#: package state after Core + all sub-reads have completed.
#:
#: Typed as ``Callable[[Any], None]`` to avoid an import cycle with
#: ``models.metagraph`` — consumer narrows the type at use site.
AfterLoadCallback = Callable[["object"], None]


def _dispatch_after_load(
    callbacks: List[AfterLoadCallback],
    metagraph: "object",
) -> None:
    """Invoke each registered after-load callback with the loaded Metagraph.

    Per Phase 08 R4-1 A locked sequence: callbacks fire ONCE after
    :meth:`MetagraphLoader.load` has completed all sub-reads (recover →
    anchor → contained graphs → meta-edges → meta-hyperedges →
    intergraph-edges → intergraph-hyperedges).

    **Per-observer exception isolation (RR-9 A)** — diverges from
    :func:`_dispatch_after_persist`. A failing callback is logged at
    WARNING + swallowed; subsequent callbacks still fire; the
    originating load returns the constructed Metagraph unchanged. The
    locked rationale: a half-rehydrated sibling-package (e.g., a
    failing InstanceLoader subscription) should NOT tear down the
    entire load. Operator surfaces partial-rehydration via ``verify``,
    not via the load's call site.
    """
    for callback in callbacks:
        try:
            callback(metagraph)
        except Exception:
            # RR-9 A — per-observer isolation. Log and continue so that
            # subsequent observers still fire and the loader's return
            # value is not perturbed by a sibling-package failure.
            _log.warning(
                "after_load observer %r raised during dispatch on %r; "
                "swallowing per Phase 08 RR-9 A locked behaviour",
                callback,
                metagraph,
                exc_info=True,
            )
