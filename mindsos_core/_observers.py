"""Observer plumbing for Core remove methods (Phase 06).

Provides a minimal subscribe-style observer API used by ``Graph`` and
``Metagraph`` to notify external consumers (e.g.,
:class:`mindsos_instances.ElementRegistry`) that an element is about to
be removed.

Design (Phase 06 row §F + round-7 P49 B + P65 A):

* Core ships **plumbing only** — no import of ``mindsos_instances``.
  Consumers subscribe by calling ``register_remove_observer(cb)`` on the
  relevant ``Graph`` or ``Metagraph`` and receive an
  :class:`ObserverHandle` for later unsubscribe.

* Observer dispatch is **precheck-style (P65 A pick)**: each remove
  method invokes the registered callbacks BEFORE the underlying
  mutation. A callback that raises aborts the remove — the originating
  Core state stays consistent (no mutation happened). The downstream
  consumer's cascade is the callback; the callback either succeeds
  (cascade applied) or raises (cascade not applied, originating remove
  refused).

* Phase 06 ships with a single-observer expectation
  (:class:`ElementRegistry`); multi-observer atomic semantics across
  partial-cascade-success is a future-work concern.

The :class:`ObserverHandle` returned by ``register_remove_observer``
exposes an ``unsubscribe()`` method that removes the callback from the
observer list. The handle is the only public surface for unsubscribe;
callers should retain handles they may later wish to revoke.
"""

from __future__ import annotations

from typing import Callable, List

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
