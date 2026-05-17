"""Tier 9 — ADR-0021 rel-type regex adversarial regression.

Phase 07 shipped ``validate_edge_type_identifier`` enforcing
``^[A-Z][A-Z0-9_]{0,63}$``. PHASE_MAP §Phase 11 explicitly lists
rel-type-validation regression coverage. Phase 11 ships 5-10
additional adversarial inputs covering the corners commonly seen in
real-world data drift.
"""

from __future__ import annotations

import pytest

from mindsos_core.cypher import validate_edge_type_identifier
from mindsos_core.exceptions import CypherError


# ── valid inputs (must pass) ────────────────────────────────────────────────


@pytest.mark.parametrize("good", [
    "X",                  # single uppercase letter (minimum).
    "WORKS_AT",           # typical.
    "REFINES",            # single-word.
    "A0",                 # uppercase + digit.
    "A_B_C",              # underscores.
    "A" * 64,             # at length boundary (1 + 63).
    "UNSPECIFIED",        # Phase 04-v2 SENT-1 sentinel.
    "WORKS_AT_2026",      # mixed alphanumeric.
])
def test_valid_rel_type_accepted(good: str) -> None:
    """ADR-0021 regex accepts well-formed identifiers."""
    validate_edge_type_identifier(good)  # must not raise


# ── invalid inputs (must reject) ────────────────────────────────────────────


@pytest.mark.parametrize("bad", [
    "",                                       # empty.
    "lowercase",                              # starts lower.
    "0LEADING_DIGIT",                         # starts with digit.
    "_LEADING_UNDERSCORE",                    # starts with underscore.
    "WORKS-AT",                               # hyphen.
    "WORKS AT",                               # space.
    "WORKS.AT",                               # dot.
    "WORKS;DROP TABLE Edge",                  # injection attempt.
    "A" * 65,                                 # one past 64-char max.
    "WORKS\nAT",                              # newline.
    "WORKSüAT",                          # non-ASCII letter.
    "BACKTICK`WRAP",                          # backtick.
    "{escape}",                               # braces.
])
def test_invalid_rel_type_rejected(bad: str) -> None:
    """ADR-0021 regex rejects malformed / injection-prone identifiers."""
    with pytest.raises(CypherError):
        validate_edge_type_identifier(bad)
