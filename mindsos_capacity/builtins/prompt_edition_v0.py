"""``capacity:comprehension:write_prompt_edition`` — append one prompt edition.

``mindsos_llm`` plan item **I-9**, rulings **R2** and **R3**.

**R2 — L3 writes what L2 holds.** ``mindsos_knowledge`` holds prompt text and
versions; this capacity is the write half. The store's own refusals and its
append-only discipline live in :mod:`mindsos_knowledge.prompts`; this module
is the L3 declaration plus the ADR-0180 write-body wiring, and it adds no
rule of its own.

**R3 — the family is ``comprehension``, not ``llm``.** A family named for the
borrowed model names the crutch rather than the work, and goes wrong the day
the stand-in is removed. Reading text is the work; a prompt is the instrument
a reading used, so the instrument's store sits in the reading family.

⚠ **THE TEXT ARRIVES AS AN INPUT, NOT FROM AN ANSWER.** Measured: the
transport call carries ``prompt_iri``, ``prompt_version``, ``source_text``,
``extraction_schema`` and ``timeout_s`` — **no prompt text crosses the seam**,
so no answer contains it and no reading can produce it. The text comes from
whoever authored the prompt, through this capacity's input record, exactly as
``learn_parameter`` receives a value it did not compute.

⚠ **This capacity consults no model.** It reaches the write capability and
no model client, so ``EXPECTED_EXTERNAL_CLIENT_CONSUMERS`` stays at its one
entry: a bookkeeping step must not inherit the failure modes of a model call
- an outage, a ceiling, an answer that will not decode.

**Realm: always ``scope="local"``.** The Global prompt library is
admin-authored; L3 cannot write Global, and that asymmetry is the ruling, not
a limitation to work around. A Local edition is a per-user trial.

**Outputs: ``()``** — write-capacity terminator, the ``learn_parameter``
precedent (R2 PB-K). The runtime surfaces the :class:`WriteResult` via
``InvocationResult.write_outcome``.
"""

from __future__ import annotations

from typing import Any, List

from ..capacity import Capacity
from ..datastate import DataState, ShapeDescriptor
from ..identifiers import CATEGORY_COMPREHENSION, datastate_iri


# ── DataState IRI (record shape) ───────────────────────────────────────

DS_PROMPT_EDITION_WRITE = datastate_iri("core.prompt_edition_write")


def prompt_edition_datastates() -> List[DataState]:
    """The record DataState ``capacity:comprehension:write_prompt_edition`` reads.

    Required keys: ``prompt_iri`` (str), ``prompt_version`` (Any — an ``int``
    on every answer, normalised once by the store), ``text`` (str). Optional:
    ``recorded_at`` (str|None), read defensively in the body.
    """
    return [
        DataState(
            name="core.prompt_edition_write",
            shape=ShapeDescriptor.record(
                {
                    "prompt_iri": "str",
                    "prompt_version": "Any",
                    "text": "str",
                },
                opaque_tag="core.prompt_edition_write",
            ),
            description=(
                "Record bearing one prompt edition to append to the user's "
                "Local prompts role-graph: prompt_iri + prompt_version are "
                "the two fields a reader stamps on every conclusion and "
                "together they address the node, text is the payload, "
                "recorded_at is optional provenance."
            ),
            provenance_category=CATEGORY_COMPREHENSION,
        ),
    ]


# ── Capacity body ──────────────────────────────────────────────────────


def _write_prompt_edition_impl(**kwargs: Any) -> Any:
    """Body of ``capacity:comprehension:write_prompt_edition`` (ADR-0180).

    Obtains its :class:`KLWriteHandle` from the **pre-authorized**
    ``context.writeable`` capability; the body holds no session and makes no
    authorization decision.
    """
    from mindsos_knowledge.identifiers import ROLE_PROMPTS
    from mindsos_knowledge.prompts import write_prompt_edition

    from ..exceptions import WriteHandleNotWiredError

    context = kwargs.get("context")
    writeable = getattr(context, "writeable", None)
    if writeable is None:
        raise WriteHandleNotWiredError(
            "capacity:comprehension:write_prompt_edition requires L4 dispatch: "
            "the CapacityContext must carry a pre-authorized `writeable` "
            "capability (ADR-0180). Write capacities are not invocable via the "
            "L3-internal dict path."
        )

    rec = kwargs[DS_PROMPT_EDITION_WRITE]
    handle = writeable(role=ROLE_PROMPTS, scope="local", version="v1")

    return write_prompt_edition(
        handle,
        prompt_iri=str(rec["prompt_iri"]),
        prompt_version=rec["prompt_version"],
        text=str(rec["text"]),
        recorded_at=rec.get("recorded_at"),
    )


# ── Capacity factory ───────────────────────────────────────────────────


def build_write_prompt_edition() -> Capacity:
    """Build the ``capacity:comprehension:write_prompt_edition`` declaration."""
    return Capacity(
        name="write_prompt_edition",
        category=CATEGORY_COMPREHENSION,
        inputs=(DS_PROMPT_EDITION_WRITE,),
        outputs=(),
        implementation=_write_prompt_edition_impl,
        description=(
            "Append one prompt edition to the user's Local prompts "
            "role-graph, addressed by (prompt_iri, prompt_version); the store "
            "is append_only and refuses a version that already exists. Write "
            "terminator (outputs=())."
        ),
        cost_prior=2.0,
        latency_ms_prior=5.0,
    )


__all__ = [
    "DS_PROMPT_EDITION_WRITE",
    "build_write_prompt_edition",
    "prompt_edition_datastates",
]
