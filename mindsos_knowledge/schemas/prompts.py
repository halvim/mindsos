"""Prompts role-graph schema — versioned prompt text (``mindsos_llm`` I-9).

Plan ruling **R2** (`docs/plans/MINDSOS_LLM_PLAN.md`): ``mindsos_knowledge``
(L2) **HOLDS prompt text and versions**; ``mindsos_capacity`` (L3) **WRITES**
it. This module is the holding half.

**The problem it closes.** A reader stamps ``prompt_iri`` and
``prompt_version`` on every conclusion, and nothing held what either named —
the text lived in deployment code. So a stored conclusion said *"read by model
X under prompt P v3"* and the system could not show P v3. The module's end
state is that a conclusion which leaned on the borrowed model can be
identified, **shown** — including what was asked — and re-run without it.

**Single NodeType** (``PromptEdition``); **no EdgeTypes** — the
``learned-parameters`` / ``learned-pipelines`` / ``policies`` zero-edge shape.
Editions of one prompt are related by their ``prompt_version`` and by nothing
else, and an edge would be a second place for that truth to live (ADR-0192's
criterion).

**Discipline: ``append_only``.** A version is never rewritten. That is the
whole basis on which *shown* means anything: if v3 can be edited after the
fact, the text a reader is shown is not evidence of what ran.
⚠ **DECLARED, NOT ENFORCED at v1** — ``validate_mutation_discipline`` is
uncalled system-wide (stated outright in ``schemas/dataset.py`` and repeated
in ``schemas/policies.py``). This role declares the discipline it needs; the
write path must enforce it, and until something does, *shown* means
RETRIEVABLE rather than VERIFIABLE. Filed as
``core-llm-prompt-edition-append-only-unenforced``.

**The node's ``value`` payload IS the prompt text.** Not a property —
``value`` is a ``RESERVED_PROPERTY_KEYS`` member (``mindsos_core`` owns it as
the node payload), and property bags are primitives-only and always inline.
``learned-parameters`` set that precedent and ``policies`` follows it.

**Dual-scope**, by owner ruling 2026-09-14: Global is the curated library
(admin-authored), Local is a per-user trial. A prompt held Local-only could
not be shown to anyone but the user whose own reading produced it, which
defeats the end state for every shared or exported conclusion. **L3 cannot
write Global**, so the asymmetry needs no new gate.

⚠ **Why this is not the ``policies`` role.** The shape of a versioned body is
shared, and ``policies`` says so in its own docstring. But a policy is an
authority a decision **cites** and a prompt is an instrument a reading
**used**; ``policies`` was created for a consumer of this system, and a module
generic to any text interpretation does not borrow a consumer's store. Reusing
it would leave a prompt indistinguishable from an authority to anything that
enumerates that graph, with an id prefix as the only separation — identity
carried by a naming convention.

``strict=False`` per ADR-0149.
"""

from __future__ import annotations

from typing import Literal

from mindsos_core import NodeType

from ._base import Discipline, L2Schema


# ── Node type ──────────────────────────────────────────────────────────

NODE_PROMPT_EDITION = "PromptEdition"

PROMPTS_NODE_TYPES: tuple[str, ...] = (NODE_PROMPT_EDITION,)


# ── Edge types ─────────────────────────────────────────────────────────

PROMPTS_EDGE_TYPES: tuple[str, ...] = ()  # v1 has no edge types.


# ── Advisory property constants ────────────────────────────────────────

PROMPT_EDITION_PROPS: frozenset[str] = frozenset({
    # The two fields a reader stamps on every conclusion. Together they are
    # the node's address, which is why a stored conclusion needs nothing else
    # to resolve its text.
    "prompt_iri",
    "prompt_version",
    # When this edition was appended. Not an in-force window: a conclusion
    # names the VERSION it used, exactly, so there is nothing to resolve by
    # date and a window would be a second, weaker answer to a question the
    # version already settles.
    "recorded_at",
    "storage_mode",
})

#: The edition's text is the node's ``value`` **payload**, not a property —
#: see the module docstring. Named here so a reader looking for "where does
#: the text live" finds the answer next to the property list.
PAYLOAD_IS_PROMPT_TEXT = True


# ── Per-NodeType large-payload field declaration (ADR-0151) ───────────

STORAGE_MODE_FIELDS: dict[str, frozenset[str]] = {
    NODE_PROMPT_EDITION: frozenset({"value"}),
}


def build_prompts_schema(
    strict: bool = False,
    scope: Literal["local", "global"] = "global",
) -> L2Schema:
    """Construct the prompts role Schema.

    ``scope`` is accepted for signature parity with the other dual-scope role
    builders and is deliberately **not** branched on: both realms are
    ``append_only``. A prompt's version history is the same kind of thing
    whoever holds it, and a Local realm that permitted rewriting would let a
    user silently restate what was asked — which is the one thing the role
    exists to prevent.

    Args:
        strict: Opt-in property-type enforcement. Default ``False`` per
            ADR-0149.
        scope: ``"global"`` (default) or ``"local"``. Present for parity;
            both yield ``append_only``.
    """
    s = L2Schema(mutation_discipline=Discipline.APPEND_ONLY, strict=strict)

    for nt in PROMPTS_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    # No EdgeTypes in v1 — version ordering is carried by the
    # ``prompt_version`` property, never stored as an edge.
    return s


__all__ = [
    "NODE_PROMPT_EDITION",
    "PAYLOAD_IS_PROMPT_TEXT",
    "PROMPTS_EDGE_TYPES",
    "PROMPTS_NODE_TYPES",
    "PROMPT_EDITION_PROPS",
    "STORAGE_MODE_FIELDS",
    "build_prompts_schema",
]
