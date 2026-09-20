"""Every named L2 role is registered in ADR-0150 — plan ruling R11 (OWNER 2026-09-18).

``docs/plans/MINDSOS_LLM_PLAN.md`` §2 R11. ADR-0150 §Decision closes the L2
role-set and its own escape clause (§am-5, restated by §am-9) says a new
**named** role requires a §Revisions entry on that ADR. The rule has been
skipped: the ADR is the register, and nothing read it.

**The predicate, and why it is not a substring search.** A role counts as
registered when its name appears **backticked** inside one of the two blocks
in which this ADR registers roles — the §Decision table, or a §Revisions
amendment. A bare substring search over the whole file reports
``policies`` as present because §Context says *"L4 orchestration policies
plan against fixed role-graphs"*, which registers nothing. That false
positive is the reason for both halves: the backticks, and the block.

⚠ **A FLOOR, NOT A CEILING.** Presence of the name in a registry block does
not say the entry names the right scope, builder or discipline. This guard
holds the mechanical half — that the register mentions the role at all — and
a wrong entry is caught by reading, as every other claim of this class is.

⚠ **The role set is DERIVED from ``ALL_ROLES``, never typed here.** A guard
carrying its own list is a second place to update, which is the defect it
exists to stop. Adding a role reddens this file until the ADR records it.

**Vacuous green is the failure mode this guard has to survive**, so the block
finder raises on a missing heading rather than returning an empty block: a
registry that cannot be located would otherwise mark every role registered.
``tests/architecture`` runs in the test image, which COPYs ``docs/``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import pytest

from mindsos_knowledge.identifiers import ALL_ROLES

_ROOT = Path(__file__).resolve().parents[2]
_ADR = _ROOT / "docs" / "decisions" / "adr" / "0150-l2-knowledge-lifecycle.md"

#: The headings whose blocks REGISTER a role. ``## Decision`` holds the
#: original closed-set table; ``## Revisions`` holds every amendment that
#: added, renamed or re-scoped one. Every other section of this ADR argues
#: about roles without registering any.
_REGISTRY_HEADINGS: Tuple[str, ...] = ("## Decision", "## Revisions")


def _blocks(text: str) -> Dict[str, List[str]]:
    """Map each registry heading to its lines, up to the next ``## `` heading.

    Raises:
        AssertionError: a registry heading is absent. Returning an empty
            block instead would make every role look unregistered-or-
            registered depending on the caller, and a guard that cannot find
            its own domain must fail, not decide.
    """
    lines = text.split("\n")
    starts = {
        line.strip(): i for i, line in enumerate(lines) if line.startswith("## ")
    }
    missing = [h for h in _REGISTRY_HEADINGS if h not in starts]
    assert not missing, (
        f"ADR-0150 has no {missing!r} heading, so this guard cannot locate the "
        f"register it checks. Headings found: {sorted(starts)!r}."
    )
    ordered = sorted(starts.values())
    out: Dict[str, List[str]] = {}
    for heading in _REGISTRY_HEADINGS:
        start = starts[heading]
        after = [i for i in ordered if i > start]
        end = after[0] if after else len(lines)
        out[heading] = lines[start:end]
    return out


def unregistered_roles(text: str, roles: Sequence[str]) -> List[str]:
    """The roles ``text`` does not register, sorted. Empty is the passing state."""
    blocks = _blocks(text)
    registered = set()
    for role in roles:
        token = f"`{role}`"
        for lines in blocks.values():
            if any(token in line for line in lines):
                registered.add(role)
                break
    return sorted(set(roles) - registered)


def test_every_named_role_is_registered_in_adr_0150():
    missing = unregistered_roles(_ADR.read_text(encoding="utf-8"), sorted(ALL_ROLES))
    assert not missing, (
        f"ADR-0150 registers no entry for {missing!r}. Plan R11: the ADR is "
        f"the register of the closed L2 role-set, and its own §am-5 escape "
        f"clause requires a §Revisions entry per named role. A role that "
        f"ships without one leaves the register saying a set that no longer "
        f"exists is closed."
    )


def test_a_role_named_only_outside_the_registry_blocks_is_unregistered():
    """Door 1 — the false positive a substring search produces."""
    text = (
        "## Context\n\nL4 orchestration `policies` plan against role-graphs.\n"
        "\n## Decision\n\n| Global | `ontology` |\n"
        "\n## Revisions\n\n### amendment-1 — nothing\n"
    )
    assert unregistered_roles(text, ["policies", "ontology"]) == ["policies"]


def test_a_role_registered_in_a_revisions_amendment_is_registered():
    """Door 2 — where every post-Phase-13 role is registered."""
    text = (
        "## Decision\n\n| Global | `ontology` |\n"
        "\n## Revisions\n\n### amendment-9 — adds `subminds`\n"
    )
    assert unregistered_roles(text, ["ontology", "subminds"]) == []


def test_a_role_named_without_backticks_is_unregistered():
    """The other half of the predicate: prose naming is not registration."""
    text = (
        "## Decision\n\n| Global | `ontology` |\n"
        "\n## Revisions\n\n### amendment-9 — adds subminds, a new role\n"
    )
    assert unregistered_roles(text, ["subminds"]) == ["subminds"]


def test_a_register_with_no_revisions_heading_fails_rather_than_passing():
    """Vacuous green: an unlocatable register is an error, not a clean bill."""
    text = "## Decision\n\n| Global | `ontology` |\n\n## Source\n\nnothing\n"
    with pytest.raises(AssertionError, match="no \\['## Revisions'\\] heading"):
        unregistered_roles(text, ["ontology"])
