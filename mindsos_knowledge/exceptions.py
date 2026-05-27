"""MindsOS Knowledge Layer exception hierarchy.

Independent root from ``mindsos_core.CoreError`` per PB-21 lock —
mirrors the discipline used in ``mindsos_instances.exceptions``
(Phase 06). Consumers wanting a catch-all across L1 + L2 use
``except (CoreError, KnowledgeError):``.

Phase 12 shipped:

* ``KnowledgeError`` — base class for every L2-domain error.
* ``RefFormatError`` — raised by IRI builders + parser on malformed
  input (empty / non-string / unknown prefix / bad version / bad
  user_id charset etc.).

Phase 13 adds:

* ``UnknownRoleError`` — raised by ``schema_for_role(role)`` when the
  supplied role isn't recognised (not in ``ALL_ROLES`` and not an
  ``alignment:<a>:<b>`` prefix form). PB-11 lock.

Phase 14 adds:

* ``AlreadyInstalledError`` — raised by
  ``KnowledgeLayer.install_local_metagraph(user_id, ...)`` when a
  Local for ``user_id`` is already installed (ADR-0042 §Decision —
  "refuses with AlreadyInstalledError if a Local is already present").
* ``NotInstalledError`` — raised by
  ``KnowledgeLayer.extract_local_metagraph(user_id)`` when no Local
  is installed for ``user_id`` (ADR-0042 §Decision — "raises
  NotInstalledError" on miss).

Phase 36 adds:

* ``SemanticValidationError`` — raised by L3 write capacities when a
  semantic validator returns a failed
  :class:`mindsos_knowledge.validators.ValidationResult`. Carries the
  result on ``.result`` for downstream PTR-construction (the
  ADR-0146 §amendment-1 clause 1 closure is deferred — Phase 36 stays
  with Phase 34's raise-not-PTR posture). ADR-0139 §Capacity-contract
  + ``docs/dev/review-checklist.md`` §4.

Phase 16+ append: ``PromotionError``, etc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .validators import ValidationResult


class KnowledgeError(Exception):
    """Base class for all L2 Knowledge-Layer errors."""


class RefFormatError(KnowledgeError):
    """Raised on malformed IRI input — bad prefix / version / fragment /
    user_id, or non-string passed to a builder or parser."""


class UnknownRoleError(KnowledgeError):
    """Raised by ``schema_for_role(role)`` when ``role`` is not a
    recognised L2 role.

    Phase 13 — PB-11 lock. Mirrors Phase 11's ``UnknownEdgeTypeError``
    discipline for L1. Message includes the sorted ``ALL_ROLES`` list
    plus a hint that ``alignment:<role_a>:<role_b>`` is accepted via
    prefix-match.
    """


class AlreadyInstalledError(KnowledgeError):
    """Raised by ``KnowledgeLayer.install_local_metagraph(user_id, mg)``
    when a Local metagraph is already installed for ``user_id``.

    ADR-0042 §Decision: ``install_local_metagraph`` refuses with this
    error if a Local is already present. The server is expected to
    ``extract_local_metagraph`` before installing a replacement.
    """


class NotInstalledError(KnowledgeError):
    """Raised by ``KnowledgeLayer.extract_local_metagraph(user_id)``
    when no Local is installed for ``user_id``.

    ADR-0042 §Decision: ``extract_local_metagraph`` raises this error
    on miss rather than silently returning ``None``.
    """


class SemanticValidationError(KnowledgeError):
    """Raised by L3 write capacities on semantic-validator failure.

    Carries the failed :class:`ValidationResult` on ``.result``;
    canonical message defaults to the result's ``violation`` string.

    Phase 36 (ADR-0139 §Capacity-contract). Capacity bodies call
    ``handle.validate_node(...)`` (or compose validators directly per
    ADR-0139 §Capacity-contract fallback) and raise this on
    ``not result.ok`` — the ``runtime.invoke`` envelope catches per
    ADR-0072 and surfaces as ``InvocationResult(success=False,
    error=<this>)``.

    Phase 36 stays with Phase 34's raise-not-PTR posture (ADR-0146
    §amendment-1 clause 1 remains open). When the L4 consumer drives
    the eventual clause-1 closure, the ``.result`` attribute lets the
    consumer construct a :class:`ProblemTraceRecord` from the carried
    :class:`ValidationResult` without re-running the validator.
    """

    def __init__(self, result: "ValidationResult") -> None:
        super().__init__(result.violation or "semantic validation failed")
        self.result = result
