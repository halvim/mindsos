"""Direct unit tests for Cypher identifier validation (ADR-0021)."""

from __future__ import annotations

import pytest

from mindsos_core import (
    CypherError,
    validate_edge_type_identifier,
    validate_label_identifier,
)


@pytest.mark.parametrize("name", ["WORKS_AT", "FOLLOWS", "REL_1", "A"])
def test_valid_edge_type(name):
    validate_edge_type_identifier(name)  # no raise


@pytest.mark.parametrize(
    "name",
    [
        "works_at",       # lowercase
        "Works_At",       # mixed case
        "WORKS-AT",       # hyphen
        "1WORKS",         # digit prefix
        "",               # empty
        " WORKS_AT ",     # leading/trailing whitespace
        "A" * 65,         # too long (max 64 chars)
    ],
)
def test_invalid_edge_type_raises(name):
    with pytest.raises(CypherError):
        validate_edge_type_identifier(name)


def test_edge_type_non_string_raises():
    with pytest.raises(CypherError):
        validate_edge_type_identifier(42)  # type: ignore[arg-type]


def test_label_allows_mixed_case():
    """Cypher labels (PascalCase convention) accept mixed case."""
    validate_label_identifier("NodeInstance")  # no raise
    validate_label_identifier("Graph")
    validate_label_identifier("snake_case_too")


@pytest.mark.parametrize("name", ["1Bad", "-leading-dash", "", "has space"])
def test_invalid_label_raises(name):
    with pytest.raises(CypherError):
        validate_label_identifier(name)
