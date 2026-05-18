"""Phase 13 PB-14 — alignment's ``extra_edge_types`` kwarg.

The alignment vocabulary is intentionally OPEN. Callers register extra
mapping edge types at build time; Cypher rel-type regex still applies.
"""

from __future__ import annotations

import pytest

from mindsos_core import CypherError

from mindsos_knowledge.schemas import build_alignment_schema
from mindsos_knowledge.schemas.alignment import ALIGNMENT_EDGE_TYPES


def test_default_vocabulary_no_extras() -> None:
    s = build_alignment_schema()
    assert set(s.edge_types) == set(ALIGNMENT_EDGE_TYPES)


def test_extra_edge_types_extends_vocabulary() -> None:
    s = build_alignment_schema(extra_edge_types=("CUSTOM_MAP",))
    assert "CUSTOM_MAP" in s.edge_types
    assert set(s.edge_types) == set(ALIGNMENT_EDGE_TYPES) | {"CUSTOM_MAP"}


def test_multiple_extras() -> None:
    s = build_alignment_schema(extra_edge_types=("FOO", "BAR"))
    assert "FOO" in s.edge_types
    assert "BAR" in s.edge_types


def test_extra_edge_type_violates_cypher_regex_rejected() -> None:
    # ADR-0021 — ``^[A-Z][A-Z0-9_]{0,63}$``. Lowercase + leading digit fail.
    with pytest.raises(CypherError):
        build_alignment_schema(extra_edge_types=("bad_lowercase",))
