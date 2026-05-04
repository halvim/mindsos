"""Cypher identifier safety.

FalkorDB (and openCypher) treat relationship type names and labels as
identifiers, which means they are interpolated *verbatim* into query text
rather than parameterised. Allowing arbitrary user strings there is a
Cypher injection vector.

The Core Layer enforces a conservative identifier shape — an uppercase
letter followed by up to 63 uppercase letters / digits / underscores —
via a single regex, and rejects anything that fails to match. This
replaces the v3 approach (hardcoded allowlist) with a rule that is easy
to extend while keeping every string safe to splice into Cypher.

Per ADR-0021 (load-bearing for Phase 03's invalid-rel-type pass criterion).
"""

from __future__ import annotations

import re

from ..exceptions import CypherError

#: Edge / relationship type identifiers used in Cypher queries.
EDGE_TYPE_IDENTIFIER_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")

#: Node labels. We allow mixed case here because FalkorDB labels are
#: conventionally PascalCase (e.g. ``:NodeInstance``).
LABEL_IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")


def validate_edge_type_identifier(name: str) -> None:
    """Raise :class:`CypherError` if ``name`` is unsafe for Cypher."""
    if not isinstance(name, str) or not EDGE_TYPE_IDENTIFIER_RE.match(name):
        raise CypherError(
            f"Invalid edge type identifier {name!r}: must match "
            f"{EDGE_TYPE_IDENTIFIER_RE.pattern}"
        )


def validate_label_identifier(name: str) -> None:
    """Raise :class:`CypherError` if ``name`` is unsafe as a Cypher label."""
    if not isinstance(name, str) or not LABEL_IDENTIFIER_RE.match(name):
        raise CypherError(
            f"Invalid label identifier {name!r}: must match "
            f"{LABEL_IDENTIFIER_RE.pattern}"
        )
