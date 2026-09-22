"""ADR-0210 amendment 4 (plan item I-8) — the tree facts the ruling rests on.

Amendment 4 is a DESIGN RECORD with no product code, which is exactly the
shape that rots: every one of its claims is a statement about this tree, and
nothing would notice the day one stopped being true. This file is the
enforcement, and each test pins ONE measured claim:

* **The seam's call carries the prompt WORDS and never the prompt's NAME.**
  ⚠ **REPOINTED 2026-09-22 by plan R21 / ADR-0210 am-7 (plan item I-17).**
  This test used to pin amendment 4's measurement *"no prompt text crosses the
  transport seam"*. That was true, and it was the defect: the words were
  resolved by a resolver injected into the ADAPTER, below the client that
  stamps the answer, so no answer could name what was asked. R21 moves
  resolution to the client, which now hands the transport everything the
  model receives. The claim is kept, inverted, not deleted: the words MUST
  cross, and ``prompt_iri`` / ``prompt_version`` must NOT — a transport that
  can see the name can fetch its own words. Still read off the call
  ``LiveLLM.read`` builds, by AST, never from prose. (Amendment 5's
  consequence — a prompt edition is written as an INPUT record, not recorded
  off an answer — is unchanged: the recorder still reads answers, and an
  answer carries a digest of the words, not the words.)
* **``prompts`` is dual-scope.** ⚠ **Repointed by ADR-0210 am-5**: this test used
  to assert it of ``policies``, which am-4 wrongly had prompt editions reusing.
  The owner's 2026-09-14 ruling (prompt editions are not Local-only) needs both
  realms of the role that actually holds them. Narrow it and the ruling is
  unimplementable.
* **``comprehension`` is a FAMILY_RULES key.** Amendment 3 places the recorder
  in that family rather than an ``llm`` one. ⚠ **Amendment 6 (plan R10) withdrew
  the recorder's don't-know**: ``OPTIONAL_RETURN`` is the READER's shape, and the
  recorder refuses. The family must still exist, or every reader's contract falls
  to the permissive default silently.
* **The amendment is labelled ``**Amendment status:**``.** ADR-0157/0210's
  checker reads the FIRST ``**Status:**`` line as the ADR's own (RULES §9), so
  an amendment that uses the bare label shadows the ADR's real status.

⚠ **Two of the checkers are tested against FABRICATED input**, so this file
cannot be a green guard that never fails: ``_seam_call_keys`` is shown refusing
a transport call that carries prompt text, and ``_missing_realms`` is shown
refusing a single-scope role — neither offence existing anywhere in the tree.

⚠ **Why the dual-scope claim is born red by FABRICATION and not by a tree
mutation.** ``_LOCAL_NAMED_ROLES`` is consumed by every local-bootstrap path,
so *any* edit to it reddens the whole of ``tests/phase_14`` — a designated
mutation over it predicted 4 reds and produced 21, and no honest prediction can
be derived from the constant because the blast radius is the bootstrap, not the
claim. The smallest edit that makes *this* claim false is a fabricated pair of
scope sets (RULES §12, SMALLEST EDIT).
"""

from __future__ import annotations

import ast
from pathlib import Path

from mindsos_capacity import FAMILY_RULES, FamilyDontKnowShape
from mindsos_knowledge.bootstrap import _GLOBAL_NAMED_ROLES, _LOCAL_NAMED_ROLES
from mindsos_knowledge.identifiers import ROLE_PROMPTS


_REPO_ROOT = Path(__file__).resolve().parents[2]
_LIVE = _REPO_ROOT / "mindsos_llm" / "live.py"
_ADR = _REPO_ROOT / "docs" / "decisions" / "adr" / "0210-llm-communication-layering.md"

#: The seam's call as plan R21 rules it: everything the model receives, and
#: nothing that only names it. ⚠ **Hand-written, never imported** from
#: ``mindsos_llm.live.TRANSPORT_CALL_KEYS`` — a checker's list derived from the
#: code it checks cannot notice that code drifting. (Amendment 4's set was
#: ``{prompt_iri, prompt_version, source_text, extraction_schema, timeout_s}``.)
SEAM_CALL_KEYS = frozenset(
    {
        "prompt_text", "source_text", "extraction_schema", "tool_name",
        "tool_description", "model_id", "temperature", "max_tokens",
        "timeout_s",
    }
)

#: The key that carries the prompt WORDS. It must be in the call (R21).
PROMPT_WORDS_KEY = "prompt_text"

#: Keys that NAME a prompt rather than carry it. None may cross (R21): a
#: transport that can see the name can resolve words of its own. A FLOOR, not
#: a ceiling — a new spelling escapes it, so add to it.
PROMPT_NAME_SPELLINGS = ("prompt_iri", "prompt_version", "prompt_id", "prompt_name")


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


def _seam_call_problems(got: frozenset[str]) -> list[str]:
    """What is wrong with a transport call's key set, against R21."""
    problems = []
    if got != SEAM_CALL_KEYS:
        problems.append(
            f"key set {sorted(got)!r} != R21's {sorted(SEAM_CALL_KEYS)!r}"
        )
    if PROMPT_WORDS_KEY not in got:
        problems.append("the prompt WORDS do not cross the seam")
    named = sorted(k for k in got if k in PROMPT_NAME_SPELLINGS)
    if named:
        problems.append(f"the prompt's NAME crosses the seam: {named!r}")
    return problems


def test_the_seam_carries_the_prompt_words_and_never_the_prompt_name():
    got = _seam_call_keys(_LIVE.read_text(encoding="utf-8"))
    assert _seam_call_problems(got) == [], (
        "plan R21 / ADR-0210 am-7: the client hands the transport everything "
        "the model receives, and nothing that would let it resolve words of "
        f"its own. {_seam_call_problems(got)!r}"
    )


def test_the_checker_refuses_the_amendment_4_call_it_replaced():
    """Born red against FABRICATED input: the pre-R21 call shape — a name,
    no words — is exactly what this checker exists to refuse."""
    fabricated = (
        "class LiveLLM:\n"
        "    def read(self, **kw):\n"
        "        call = dict(prompt_iri=1, prompt_version=2,\n"
        "                    source_text=4, extraction_schema=5, timeout_s=6)\n"
        "        return call\n"
    )
    problems = _seam_call_problems(_seam_call_keys(fabricated))
    assert any("do not cross" in p for p in problems)
    assert any("prompt_iri" in p and "prompt_version" in p for p in problems)


def _missing_realms(role: str, global_roles, local_roles) -> tuple[str, ...]:
    """The realms ``role`` is absent from. Empty means dual-scope."""
    return tuple(
        realm
        for realm, roles in (("global", global_roles), ("local", local_roles))
        if role not in roles
    )


def test_prompts_is_dual_scope_so_a_prompt_edition_can_be_global():
    assert _missing_realms(ROLE_PROMPTS, _GLOBAL_NAMED_ROLES, _LOCAL_NAMED_ROLES) == (), (
        "the owner ruled 2026-09-14 that prompt editions are NOT Local-only "
        "(ADR-0210 am-4): a prompt held Local-only cannot be shown to anyone "
        "but the user whose reading produced it, and the Local form is the "
        "per-user trial an L3 write targets - L3 cannot write Global, so "
        "without it nothing below admin can author a prompt at all."
    )


def test_the_checker_refuses_a_fabricated_single_scope_role():
    assert _missing_realms("r", frozenset({"r"}), frozenset()) == ("local",)
    assert _missing_realms("r", frozenset(), frozenset({"r"})) == ("global",)
    assert _missing_realms("r", frozenset(), frozenset()) == ("global", "local")
    assert _missing_realms("r", frozenset({"r"}), frozenset({"r"})) == ()


def test_comprehension_is_a_family_and_keeps_its_dont_know_shape():
    assert FAMILY_RULES.get("comprehension") is FamilyDontKnowShape.OPTIONAL_RETURN, (
        "ADR-0210 am-3 places the recorder in the 'comprehension' family; "
        "OPTIONAL_RETURN is the READER's don't-know shape. (am-4 read it as "
        "the recorder's too - WITHDRAWN by am-6 / plan R10: the recorder "
        "refuses.) A changed shape changes every reader's contract."
    )


def test_amendment_4_uses_the_amendment_status_label():
    text = _ADR.read_text(encoding="utf-8")
    assert "## Amendment 4" in text, "ADR-0210 amendment 4 is missing"
    assert "## Amendment 5" in text, "ADR-0210 amendment 5 is missing"
    assert "## Amendment 6" in text, "ADR-0210 amendment 6 is missing"
    for n in ("4", "6"):
        head = text.split("## Amendment " + n, 1)[1].split("\n## ", 1)[0]
        assert "**Amendment status:**" in head, (
            f"RULES §9: amendment {n} must label its status '**Amendment "
            "status:**'. The bare label shadows the ADR's own status line."
        )
    assert text.count("\n**Status:**") == 1, (
        "an amendment used the bare '**Status:**' label — the ADR checker "
        "reads the FIRST one as the ADR's own status."
    )
