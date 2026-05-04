"""Exception hierarchy for the Core Layer (Phase 02 slim).

All Core-Layer errors inherit from ``CoreError`` so higher layers can
catch one base type. Phase 02 ships only the identity-related subclass;
later phases append schema / cypher / persistence / reconstruction
exceptions as their feature surface lands.

The full hierarchy lives in the parent project at
``mindsos_core/exceptions.py`` and will be ported phase-by-phase.
"""

from __future__ import annotations


class CoreError(Exception):
    """Base class for every error raised by mindsos_core."""


# ── Identity ──────────────────────────────────────────────────────────────────

class IdentityError(CoreError):
    """Duplicate id, unknown id, or replace-with-conflict."""
