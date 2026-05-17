"""MindsOS Knowledge Layer — slim Phase 12 exception hierarchy.

Independent root from ``mindsos_core.CoreError`` per PB-21 lock —
mirrors the discipline used in ``mindsos_instances.exceptions``
(Phase 06). Consumers wanting a catch-all across L1 + L2 use
``except (CoreError, KnowledgeError):``.

Phase 12 ships only the two classes needed by ``identifiers.py``:

* ``KnowledgeError`` — base class for every L2-domain error.
* ``RefFormatError`` — raised by IRI builders + parser on malformed
  input (empty / non-string / unknown prefix / bad version / bad
  user_id charset etc.).

Phase 13+ append: ``SchemaValidationError`` (Phase 13),
``BootstrapError`` (Phase 14), ``PromotionError`` (Phase 16), etc.
"""

from __future__ import annotations


class KnowledgeError(Exception):
    """Base class for all L2 Knowledge-Layer errors."""


class RefFormatError(KnowledgeError):
    """Raised on malformed IRI input — bad prefix / version / fragment /
    user_id, or non-string passed to a builder or parser."""
