"""Family-specific dont-know contracts for L3 capacities (ADR-0157).

Maps a capacity IRI to its dont-know shape via a two-level prefix
lookup (name-prefix first, then category, then a permissive
``DATASTATE_MARKER`` default). The rule is implicit from the capacity
IRI prefix; there is no per-capacity registration field.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Dict

from .identifiers import REALM_MARKER, datastate_iri, parse_capacity_iri

log = logging.getLogger(__name__)


class FamilyDontKnowShape(Enum):
    DATASTATE_MARKER = "datastate_marker"
    OPTIONAL_RETURN = "optional_return"
    VERDICT = "verdict"
    VALIDATION_RESULT = "validation_result"
    NO_DONT_KNOW = "no_dont_know"


DS_UNHANDLED_INPUT = datastate_iri(f"{REALM_MARKER}.unhandled_input")


FAMILY_RULES: Dict[str, FamilyDontKnowShape] = {
    "combination": FamilyDontKnowShape.OPTIONAL_RETURN,
    "comparator": FamilyDontKnowShape.OPTIONAL_RETURN,
    "evaluator": FamilyDontKnowShape.OPTIONAL_RETURN,
    "metric": FamilyDontKnowShape.OPTIONAL_RETURN,
    "mechanism": FamilyDontKnowShape.OPTIONAL_RETURN,
    "scoring": FamilyDontKnowShape.OPTIONAL_RETURN,
    "decision": FamilyDontKnowShape.VERDICT,
    "predicate": FamilyDontKnowShape.NO_DONT_KNOW,
    "validate": FamilyDontKnowShape.VALIDATION_RESULT,
    "transform": FamilyDontKnowShape.DATASTATE_MARKER,
    "derive": FamilyDontKnowShape.DATASTATE_MARKER,
    "perception": FamilyDontKnowShape.DATASTATE_MARKER,
    "process": FamilyDontKnowShape.DATASTATE_MARKER,
    "hint": FamilyDontKnowShape.OPTIONAL_RETURN,
    "planning": FamilyDontKnowShape.OPTIONAL_RETURN,
    "dream": FamilyDontKnowShape.OPTIONAL_RETURN,
    "code": FamilyDontKnowShape.DATASTATE_MARKER,
    "retrieval": FamilyDontKnowShape.OPTIONAL_RETURN,
    "promotion_rule": FamilyDontKnowShape.OPTIONAL_RETURN,
    "signal": FamilyDontKnowShape.OPTIONAL_RETURN,
    "adapter": FamilyDontKnowShape.DATASTATE_MARKER,
    "pattern": FamilyDontKnowShape.OPTIONAL_RETURN,
    "als": FamilyDontKnowShape.OPTIONAL_RETURN,
    "phase6": FamilyDontKnowShape.OPTIONAL_RETURN,
}


def family_rule_for(capacity_iri: str) -> FamilyDontKnowShape:
    category, name = parse_capacity_iri(capacity_iri)
    name_prefix = name.split(".")[0]
    if name_prefix in FAMILY_RULES:
        return FAMILY_RULES[name_prefix]
    if category in FAMILY_RULES:
        return FAMILY_RULES[category]
    log.info(
        "no family rule for capacity %r (category=%r); "
        "defaulting to DATASTATE_MARKER",
        capacity_iri,
        category,
    )
    return FamilyDontKnowShape.DATASTATE_MARKER
