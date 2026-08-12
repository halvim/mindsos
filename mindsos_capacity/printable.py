"""The one rule for prose a Decision Record is allowed to print.

**Why this is its own module.** The rule was written inside
``builtins/origin_v0.py`` because origin records were its first user. It has
two users now — an origin record's registered phrases, and a capacity's
:attr:`~mindsos_capacity.capacity._CapacityBase.printable_phrase` — and the
second is validated by ``CapacityLayer.register_capacity``, which is core.
Core importing from ``builtins/`` would invert the layering, so the rule
moves here and both callers import it. This module imports nothing.

**It returns a problem rather than raising.** The same rule has to produce
``OriginContractError`` when an origin record breaks it and
``CapacityRegistrationError`` when a registration does, and each layer owns
its own exception type. A shared raiser would force one of them to be wrong.
:func:`assert_printable_phrase` is kept for callers that want the plain
behaviour.

**What it cannot catch, stated so nobody assumes otherwise.** A DataState
name is ``<realm>.<name>`` and carries no colon, so this rule passes
``"where the value of dr.filing_threshold came from"`` — the exact leak
found by probe D and fixed in PR #151. Refusing a description that names its
own DataState needs the name in hand and lives at the factory that has it
(``policy_lookup_v0.assert_printable_description``). This module is the
floor, not the ceiling.
"""

from __future__ import annotations

from typing import Any, Optional


class PhraseNotPrintable(ValueError):
    """Raised by :func:`assert_printable_phrase` for callers with no
    layer-specific exception of their own."""


#: Substrings that mark a string as an identifier rather than prose. ``":"``
#: catches every IRI form at once; the two prefixes are kept because the error
#: they produce names the actual offender, which is what the author needs.
IDENTIFIER_MARKERS = (":", "datastate:", "capacity:")


def printable_phrase_problem(phrase: Any, field_name: str) -> Optional[str]:
    """Return why ``phrase`` may not be printed, or ``None`` if it may.

    A Decision Record is read by claims managers and lawyers. It forbids
    every IRI and every MindsOS term, and catching that at registration beats
    catching it in front of a lawyer.
    """
    if not phrase or not str(phrase).strip():
        return (
            f"{field_name} is required and must be prose the Record can print — "
            f"'their submission email', 'the claims policy'."
        )
    text = str(phrase)
    for marker in IDENTIFIER_MARKERS:
        if marker in text:
            return (
                f"{field_name} must be prose, not an identifier: {phrase!r} "
                f"contains {marker!r}."
            )
    return None


def assert_printable_phrase(phrase: Any, field_name: str) -> None:
    """Raise :class:`PhraseNotPrintable` unless ``phrase`` may be printed."""
    problem = printable_phrase_problem(phrase, field_name)
    if problem is not None:
        raise PhraseNotPrintable(problem)


__all__ = [
    "IDENTIFIER_MARKERS",
    "PhraseNotPrintable",
    "assert_printable_phrase",
    "printable_phrase_problem",
]
