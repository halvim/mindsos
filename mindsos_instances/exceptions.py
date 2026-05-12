"""Exceptions raised by ``mindsos_instances`` (Phase 06)."""

from __future__ import annotations

from mindsos_core.exceptions import CoreError


class InstanceError(CoreError):
    """Base class for all ``mindsos_instances`` errors.

    Subclasses :class:`mindsos_core.exceptions.CoreError` so callers can
    catch the broad MindsOS error tree without distinguishing layers.
    """


class DanglingTemplateError(InstanceError):
    """Materialise was called on an instance whose template has been
    hard-removed and the cascade observer failed to clean up.

    Defense-in-depth path. Under normal operation
    :class:`ElementRegistry`'s cascade observer removes orphan instances
    before this error can fire.
    """


class CompositeCycleError(InstanceError):
    """``CompositeInstance.add_member`` detected a cycle.

    A composite cannot contain itself, nor can it transitively contain
    a composite that contains it. Detection runs at compose-time
    (Phase 06 P25 A) — the offending ``add_member`` raises without
    mutating the member list.
    """


class CrossMetagraphCompositeError(InstanceError):
    """A composite member's ``metagraph_id`` differs from the
    composite's own ``metagraph_id``.

    Phase 06 (P43 C + round-7 P50 A) forbids composites that span
    metagraphs. Future-work entry tracks a possible L4/L5 use-case
    relaxation.
    """


class SubGraphInvariantError(InstanceError):
    """``SubGraphInstance`` invariant violated (P20 A — strict).

    Every edge in ``edge_ids`` must have BOTH endpoints in ``node_ids``;
    every hyperedge in ``edge_ids`` must have ALL its members in
    ``node_ids``. Enforced at construction AND after each structural
    override mutation (P21 A → amended P29 C).
    """


class OverrideScopeError(InstanceError):
    """An override key violates the per-subclass allow-list (Phase 06
    P36 A + round-7 P47 C + P48 A + P64 A bifurcated routing).

    Raised when:

    * A key is in the universally-forbidden set
      (``id`` / ``template_id`` / ``kind`` / ``metagraph_id`` /
      ``type_name`` for Edge-family subclasses).
    * A reserved-property key from
      :data:`mindsos_core.schema.RESERVED_PROPERTY_KEYS` lands in the
      user-property bucket (i.e., it isn't in the subclass's structural
      allow-list).
    """
