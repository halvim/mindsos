"""MindsOS Core Layer — slim Phase 02 surface.

Phase 02 ships only the identity primitives:

    from mindsos_core import (
        IdentityError, IdentityRegistry, generate_uuid,
        IdStrategy, UUID4Strategy, UUID5FromContentStrategy,
        IRIPassthroughStrategy, NAMESPACE_MINDSOS,
    )

Subsequent phases append: Phase 03 brings ``Graph``/``Node``/``Edge``,
Phase 04 brings ``Schema``, Phase 05 brings ``Metagraph``, Phase 07
brings persistence, etc. Each phase that adds a new sub-package must
also extend ``[tool.setuptools.packages.find].include`` in
``pyproject.toml`` if it introduces a new top-level subdirectory.

The Core Layer owns data primitives, schema, identity, persistence,
and reconstruction. It owns no reasoning, no derivation, and no
domain logic — those belong to the Intellectual Capacity, Intelligence,
and Mental Model layers built on top of this package.
"""

from __future__ import annotations

from .exceptions import CoreError, IdentityError
from .models.identity import (
    IRIPassthroughStrategy,
    IdentityRegistry,
    IdStrategy,
    NAMESPACE_MINDSOS,
    UUID4Strategy,
    UUID5FromContentStrategy,
    generate_uuid,
)

__all__ = [
    # exceptions
    "CoreError",
    "IdentityError",
    # identity
    "IdentityRegistry",
    "generate_uuid",
    # ADR-0131 — pluggable id strategies
    "IdStrategy",
    "UUID4Strategy",
    "UUID5FromContentStrategy",
    "IRIPassthroughStrategy",
    "NAMESPACE_MINDSOS",
]

__version__ = "0.0.0+phase02"
