"""ADR-0210 amendment 4 (plan item I-8) — the tree facts the ruling rests on.

Amendment 4 is a DESIGN RECORD with no product code, which is exactly the
shape that rots: every one of its claims is a statement about this tree, and
nothing would notice the day one stopped being true. This file is the
enforcement, and each test pins ONE measured claim:

* **No prompt text crosses the transport seam.** This is why a prompt edition
  is AUTHORED rather than recorded — no run can write text it never sees. The
  claim is read off the call ``LiveLLM.read`` builds, by AST, never from prose.
* **``policies`` is dual-scope.** This is the role a prompt edition reuses, and
  the owner's 2026-09-14 ruling (prompt editions are not Local-only) needs both
  realms to exist. Narrow it and the ruling is unimplementable.
* **``comprehension`` is a FAMILY_RULES key.** Amendment 3 places the recorder
  in that family rather than an ``llm`` one; a family that stops existing turns
  the recorder's don't-know contract into the permissive default silently.
* **The amendment is labelled ``**Amendment status:**``.** ADR-0157/0210's
  checker reads the FIRST ``**Status:**`` line as the ADR's own (RULES §9), so
  an amendment that uses the bare label shadows the ADR's real status.

⚠ **The checker is itself tested against a FABRICATED source**, so this file
cannot be a green guard that never fails: ``_seam_call_keys`` is shown
refusing a transport call that carries prompt text, without that text existing
anywhere in the tree.
"""

from __future__ import annotations

import ast
from pathlib import Path

from mindsos_capacity import FAMILY_RULES, FamilyDontKnowShape
from mindsos_knowledge.bootstrap import _GLOBAL_NAMED_ROLES, _LOCAL_NAMED_ROLES
from mindsos_knowledge.identifiers import ROLE_POLICIES


_REPO_ROOT = Path(__file__).resolve().parents[2]
_LIVE = _REPO_ROOT / "mindsos_llm" / "live.py"
_ADR = _REPO_ROOT / "docs" / "decisions" / "adr" / "0210-llm-communication-layering.md"

#: The seam's call, as amendment 4 measured it. Every name here is metadata
#: ABOUT a prompt; none of them is the prompt.
SEAM_CALL_KEYS = frozenset(
    {"prompt_iri", "prompt_version", "source_text", "extraction_schema", "timeout_s"}
)

#: A key whose value would BE prompt text rather than a pointer at it. A
#: FLOOR, not a ceiling: a new spelling escapes this set, so add to it rather
#: than arguing the call is fine.
PROMPT_TEXT_SPELLINGS = ("prompt_text", "prompt_body", "prompt_source", "prompt")


def _seam_call_keys(source: str) -> frozenset[str]:
    """The keyword names of the ``call`` dict built inside ``LiveLLM.read``.

    Read from the AST. A signature or a call is read from the code that
    makes it, never from a docstring that describes it.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != "LiveLLM":
            continue
        for fn in node.body:
            if not isinstance(fn, ast.FunctionDef) or fn.name != "read":
                continue
            for stmt in ast.walk(fn):
                if (
                    isinstance(stmt, ast.Assign)
                    and any(getattr(t, "id", "") == "call" for t in stmt.targets)
                    and isinstance(stmt.value, ast.Call)
                ):
                    return frozenset(
                        kw.arg for kw in stmt.value.keywords if kw.arg is not None
                    )
    raise AssertionError(
        "LiveLLM.read no longer builds a 'call' mapping — the seam's shape "
        "changed and ADR-0210 amendment 4's first claim is unverifiable."
    )


def test_no_prompt_text_crosses_the_transport_seam():
    got = _seam_call_keys(_LIVE.read_text(encoding="utf-8"))
    assert got == SEAM_CALL_KEYS, (
        "the transport call's key set changed. ADR-0210 am-4 rules that a "
        "prompt edition is AUTHORED because no prompt text reaches a run; a "
        f"new key may falsify that. Got {sorted(got)!r}"
    )
    assert not [k for k in got if k in PROMPT_TEXT_SPELLINGS], (
        "a prompt BODY now crosses the seam. Amendment 4's ruling that the "
        "recorder cannot write a prompt edition no longer holds — re-open it."
    )


def test_the_checker_refuses_a_fabricated_call_that_carries_prompt_text():
    fabricated = (
        "class LiveLLM:\n"
        "    def read(self, **kw):\n"
        "        call = dict(prompt_iri=1, prompt_version=2, prompt_text=3,\n"
        "                    source_text=4, extraction_schema=5, timeout_s=6)\n"
        "        return call\n"
    )
    got = _seam_call_keys(fabricated)
    assert "prompt_text" in got
    assert got != SEAM_CALL_KEYS
    assert [k for k in got if k in PROMPT_TEXT_SPELLINGS] == ["prompt_text"]


def test_policies_is_dual_scope_so_a_prompt_edition_can_be_global():
    assert ROLE_POLICIES in _GLOBAL_NAMED_ROLES, (
        "the owner ruled 2026-09-14 that prompt editions are NOT Local-only "
        "(ADR-0210 am-4): a prompt held Local-only cannot be shown to anyone "
        "but the user whose reading produced it."
    )
    assert ROLE_POLICIES in _LOCAL_NAMED_ROLES, (
        "the Local form is the per-user trial an L3 write targets; L3 cannot "
        "write Global, so without it nothing below admin can author a prompt."
    )


def test_comprehension_is_a_family_and_keeps_its_dont_know_shape():
    assert FAMILY_RULES.get("comprehension") is FamilyDontKnowShape.OPTIONAL_RETURN, (
        "ADR-0210 am-3 places the recorder in the 'comprehension' family and "
        "am-4 reads its don't-know as a null on the declared pointer output. "
        "A changed shape changes the recorder's contract."
    )


def test_amendment_4_uses_the_amendment_status_label():
    text = _ADR.read_text(encoding="utf-8")
    assert "## Amendment 4" in text, "ADR-0210 amendment 4 is missing"
    head = text.split("## Amendment 4", 1)[1]
    assert "**Amendment status:**" in head, (
        "RULES §9: an in-file amendment labels its status '**Amendment "
        "status:**'. The bare label shadows the ADR's own status line."
    )
    assert text.count("\n**Status:**") == 1, (
        "an amendment used the bare '**Status:**' label — the ADR checker "
        "reads the FIRST one as the ADR's own status."
    )
