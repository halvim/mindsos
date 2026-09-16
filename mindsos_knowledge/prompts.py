"""The prompts store — reading and appending versioned prompt text.

``mindsos_llm`` plan item **I-9**, ruling **R2**: L2 HOLDS prompt text and
versions, L3 WRITES it. This module is L2's half of that — the schema lives in
:mod:`mindsos_knowledge.schemas.prompts`, and the L3 write capacity calls
:func:`write_prompt_edition` through a ``KLWriteHandle`` it is given.

**What a caller actually has.** A stored conclusion carries ``prompt_iri`` and
``prompt_version`` and nothing else about what was asked. So the store's whole
job is to answer *"show me that text"* from exactly those two fields, with no
lookup in between — which is why they are the node's address rather than
properties to scan for.

⚠ **THE ONE CONVERSION, AND WHY IT IS HERE.** ``prompt_version`` is an ``int``
on an answer and a string inside an IRI. :func:`edition_id_for` is the only
place that crosses that boundary, and the writer and the reader both go
through it. A second ``str()`` elsewhere is how a write of ``3`` and a read of
``"3"`` come to miss silently — a miss that reads as *"the prompt was never
stored"* rather than as *"you asked in a different alphabet"*.
"""

from __future__ import annotations

from typing import Any, List, Optional

from .identifiers import ROLE_PROMPTS
from .schemas.prompts import NODE_PROMPT_EDITION


PROP_PROMPT_IRI = "prompt_iri"
PROP_PROMPT_VERSION = "prompt_version"
PROP_RECORDED_AT = "recorded_at"


class PromptStoreError(Exception):
    """Base for every refusal this store makes."""


class PromptEditionExistsError(PromptStoreError):
    """``(prompt_iri, prompt_version)`` is already stored.

    ⚠ Not an overwrite. The role is ``append_only`` because *shown* has to
    mean *what ran*; a version that can be restated after the fact is a
    version a reader cannot be shown as evidence. Correct a prompt by
    appending the next version, never by rewriting one.
    """


class PromptEditionNotFoundError(PromptStoreError):
    """No edition of ``prompt_iri`` at ``prompt_version`` in this view.

    ⚠ **This is the honest end of a real gap, not an error to route around.**
    Every conclusion written before this role existed names a version that was
    never stored. The caller is being told the text is absent, which is true;
    inventing a nearest-version fallback would hand a reader a prompt that was
    not the one that ran.
    """


def edition_id_for(prompt_version: Any) -> str:
    """The edition fragment for ``prompt_version``. The ONLY int->str crossing.

    Both the writer and the reader call this, so a version stored from an
    ``int`` and looked up from an ``int`` cannot disagree about its own
    spelling. See this module's docstring for why that is worth a function.
    """
    return str(prompt_version)


def editions_of(view: Any, prompt_iri: str) -> List[Any]:
    """Every ``PromptEdition`` node of ``prompt_iri`` in ``view``.

    ``view`` is a :class:`~mindsos_knowledge.metagraph_view.MetagraphView` —
    Global for the curated library, Local for a user's trial. Unordered here:
    ordering is the ``prompt_version`` property and a caller that wants it
    sorted knows what it is sorting by.
    """
    return [
        node
        for node in view.iter_nodes(ROLE_PROMPTS, type_=NODE_PROMPT_EDITION)
        if (node.properties or {}).get(PROP_PROMPT_IRI) == prompt_iri
    ]


def edition_at_version(view: Any, *, prompt_iri: str, prompt_version: Any) -> Any:
    """The one edition of ``prompt_iri`` at ``prompt_version``.

    Raises:
        PromptEditionNotFoundError: this view holds no such edition.
    """
    wanted = edition_id_for(prompt_version)
    for node in editions_of(view, prompt_iri):
        if edition_id_for((node.properties or {}).get(PROP_PROMPT_VERSION)) == wanted:
            return node
    raise PromptEditionNotFoundError(
        f"no edition of {prompt_iri!r} at version {wanted!r} in this view. A "
        f"conclusion stamped with it cannot be shown what was asked, which is "
        f"the gap this role exists to close - append the edition, and never "
        f"answer with a different version."
    )


def prompt_text(view: Any, *, prompt_iri: str, prompt_version: Any) -> str:
    """The text a conclusion stamped ``(prompt_iri, prompt_version)`` was read under.

    The two arguments are the two fields the conclusion already carries, which
    is the point of the role: showing what was asked needs no other lookup.

    Raises:
        PromptEditionNotFoundError: this view holds no such edition.
    """
    node = edition_at_version(
        view, prompt_iri=prompt_iri, prompt_version=prompt_version
    )
    return node.value


def write_prompt_edition(
    handle: Any,
    *,
    prompt_iri: str,
    prompt_version: Any,
    text: str,
    recorded_at: Optional[str] = None,
) -> Any:
    """Append one edition of ``prompt_iri`` through ``handle``.

    ``handle`` is a :class:`~mindsos_knowledge.write_handle.KLWriteHandle`
    bound to ``(ROLE_PROMPTS, scope)``.

    ``text`` becomes the node's **payload**, because ``value`` is a
    ``RESERVED_PROPERTY_KEYS`` member owned by the Core Layer and property
    bags are primitives-only. That split is the role's, not this function's;
    it is restated here because getting it wrong is invisible until the first
    write, and this is the first write.

    ``prompt_version`` is both the edition's ``prompt_version`` property and
    its ``edition_id`` IRI fragment, converted once by :func:`edition_id_for`.
    One concept, one argument.

    Raises:
        PromptEditionExistsError: ``(prompt_iri, prompt_version)`` is already
            in the store.
    """
    edition_id = edition_id_for(prompt_version)
    iri = handle.mint_iri(
        NODE_PROMPT_EDITION, prompt_iri=prompt_iri, prompt_version=edition_id
    )
    if handle.graph().nodes.get(iri) is not None:
        raise PromptEditionExistsError(
            f"version {edition_id!r} of {prompt_iri!r} already exists at {iri}. "
            f"The prompts role is append_only: correct a prompt by appending "
            f"the next version, never by rewriting one - a version that can be "
            f"restated is not evidence of what ran."
        )

    properties = {
        PROP_PROMPT_IRI: prompt_iri,
        PROP_PROMPT_VERSION: edition_id,
    }
    if recorded_at is not None:
        properties[PROP_RECORDED_AT] = recorded_at

    return handle.write_and_validate(
        value=text,
        type_=NODE_PROMPT_EDITION,
        properties=properties,
        prompt_iri=prompt_iri,
        prompt_version=edition_id,
    )


__all__ = [
    "PROP_PROMPT_IRI",
    "PROP_PROMPT_VERSION",
    "PROP_RECORDED_AT",
    "PromptEditionExistsError",
    "PromptEditionNotFoundError",
    "PromptStoreError",
    "edition_at_version",
    "edition_id_for",
    "editions_of",
    "prompt_text",
    "write_prompt_edition",
]
