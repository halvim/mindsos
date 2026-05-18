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

Phase 14+ append: ``BootstrapError`` (Phase 14), ``PromotionError``
(Phase 16), etc.
"""

from __future__ import annotations


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
