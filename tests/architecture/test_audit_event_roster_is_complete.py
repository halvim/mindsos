"""Every ``EVT_*`` constant in ``mindsos_server.audit`` is in the roster.

⚠ **This drift has already happened once, and the source admits it.**
``ALL_AUDIT_EVENTS`` carries the comment *"Phase 44 (L2-39) — declared at
Phase 44 but omitted from this tuple at ship time; appended at Phase 50
(latent-drift fix)"*. A constant was defined, used, and left out of the roster
for six phases, and nothing caught it — because the roster had no mechanical
inverse. ``write_audit`` deliberately does not validate against it (the
convention is for greppability, not runtime enforcement), so an omitted event
writes rows perfectly well and is simply invisible to anything that enumerates
what this system audits.

**This is the same shape as ``test_no_subsystem_ownership``'s fix at
``2c8b784``**: a hand-listed domain that could be quietly narrowed OR quietly
widened, asked in the direction it was never asked. Found by ADR-0210 slice 2,
whose own new event would have been added to the tuple with nothing checking
that it had been — a mutation reddening nothing, which is a finding.

The question is asked of the MODULE's structure, not of its text: a grep for
``EVT_`` matches docstrings, comments and the tuple itself.
"""

from __future__ import annotations

import ast
from pathlib import Path

import mindsos_server.audit as audit


def _declared_event_constants() -> set[str]:
    tree = ast.parse(Path(audit.__file__).read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        for t in targets:
            if isinstance(t, ast.Name) and t.id.startswith("EVT_"):
                names.add(t.id)
    return names


def test_every_declared_event_is_in_the_roster():
    declared = _declared_event_constants()
    in_roster = {
        name for name in declared if getattr(audit, name) in audit.ALL_AUDIT_EVENTS
    }
    missing = sorted(declared - in_roster)
    assert missing == [], (
        f"{missing} are EVT_ constants that no roster enumerates. "
        "write_audit does not validate against ALL_AUDIT_EVENTS, so an omitted "
        "event writes rows and is invisible to anything asking what this "
        "system audits - which is exactly what happened to "
        "EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY between Phase 44 and Phase 50."
    )


def test_the_roster_holds_nothing_that_is_not_declared():
    """The other direction. A value in the tuple with no constant behind it
    is a string literal pretending to be part of the roster."""
    declared_values = {getattr(audit, n) for n in _declared_event_constants()}
    strays = sorted(set(audit.ALL_AUDIT_EVENTS) - declared_values)
    assert strays == [], f"{strays} are in ALL_AUDIT_EVENTS with no EVT_ constant"


def test_the_scan_is_not_empty():
    """The domain-emptied failure mode: if the AST walk stops finding
    constants, both tests above pass vacuously."""
    assert len(_declared_event_constants()) >= 20
