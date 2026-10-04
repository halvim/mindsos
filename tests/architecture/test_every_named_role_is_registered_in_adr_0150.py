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
_ADR_REL = "docs/decisions/adr/0150-l2-knowledge-lifecycle.md"
_ADR = _ROOT / _ADR_REL

#: The headings whose blocks REGISTER a role. ``## Decision`` holds the
#: original closed-set table; ``## Revisions`` holds every amendment that
#: added, renamed or re-scoped one. Every other section of this ADR argues
#: about roles without registering any.
_REGISTRY_HEADINGS: Tuple[str, ...] = ("## Decision", "## Revisions")


def _blocks(text: str) -> Dict[str, List[Tuple[int, str]]]:
    """Map each registry heading to its (1-based line number, line) pairs, up
    to the next ``## `` heading.

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
    out: Dict[str, List[Tuple[int, str]]] = {}
    for heading in _REGISTRY_HEADINGS:
        start = starts[heading]
        after = [i for i in ordered if i > start]
        end = after[0] if after else len(lines)
        out[heading] = [(i + 1, lines[i]) for i in range(start, end)]
    return out


def _registering_lines(text: str, roles: Sequence[str]) -> List[Tuple[int, str]]:
    """Every line the guard JUDGES: (line number, role) for each line of a
    registry block that names a role backticked. The one walk both callers
    share, so what is reported as adjudicated and what counts as registered
    cannot drift apart. A registry-block line naming no role, and every line
    outside the two blocks, is scanned and never judged."""
    out: List[Tuple[int, str]] = []
    for pairs in _blocks(text).values():
        for n, line in pairs:
            for role in roles:
                if f"`{role}`" in line:
                    out.append((n, role))
    return out


def unregistered_roles(text: str, roles: Sequence[str]) -> List[str]:
    """The roles ``text`` does not register, sorted. Empty is the passing state."""
    registered = {role for _, role in _registering_lines(text, roles)}
    return sorted(set(roles) - registered)


def adjudicated_sites(root: Path) -> List[Tuple[str, int]]:
    """Report mode (`tools/claim_inventory.py`, the emit contract): the
    `file:line` sites this guard adjudicated -- the registry-block lines of
    ADR-0150 that register a role of ``ALL_ROLES``. An UNREGISTERED role has
    no line, so it is reported as a problem and emits nothing: there is no
    site to point at. An ADR is a dated record, so these sites add nothing to
    any live page's coverage."""
    text = (root / _ADR_REL).read_text(encoding="utf-8")
    return sorted({(_ADR_REL, n) for n, _ in _registering_lines(text, sorted(ALL_ROLES))})


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


# -- report mode -----------------------------------------------------------

def test_it_emits_the_registering_lines_and_only_those(tmp_path):
    """Line 3 names a role outside the registry blocks; line 6 is a registry
    line naming none; lines 7 and 12 register one each."""
    role_a, role_b = sorted(ALL_ROLES)[:2]
    text = (
        "## Context\n\n"
        f"Planning reads `{role_a}` here, which registers nothing.\n"
        "\n## Decision\n\n"
        f"| Global | `{role_a}` |\n"
        "\n## Revisions\n\n"
        "### amendment-1 - adds a role\n"
        f"Registers `{role_b}`.\n"
    )
    adr = tmp_path / _ADR_REL
    adr.parent.mkdir(parents=True)
    adr.write_text(text, encoding="utf-8")
    assert adjudicated_sites(tmp_path) == [(_ADR_REL, 7), (_ADR_REL, 12)]


def test_a_role_with_an_emitted_line_is_never_reported_unregistered():
    text = "## Decision\n\n| Global | `ontology` |\n\n## Revisions\n\nnothing\n"
    assert [r for _, r in _registering_lines(text, ["ontology", "policies"])] == ["ontology"]
    assert unregistered_roles(text, ["ontology", "policies"]) == ["policies"]
