"""The recorded-sets store — appending and reading recorded-set pointers.

``mindsos_llm`` plan item **I-10**, rulings **R1**, **R2**, **R8**, **R13**–**R18**
(``docs/plans/MINDSOS_LLM_PLAN.md``); shape recorded as ADR-0210 amendment 6.
L2 HOLDS the pointer; L3 WRITES it. The schema lives in
:mod:`mindsos_knowledge.schemas.recorded_sets`; the L3 write capacity calls
:func:`write_recorded_set` through a ``KLWriteHandle`` it is given.

**What this module takes, and from whom.** A *description* of the file — the
mapping ``mindsos_llm.recorded_sets.describe_set`` returns — plus the facts of
the write. ⚠ **This module does not import ``mindsos_llm``.** L2 depending on
the stand-in would make the store of what the stand-in produced disappear with
it, which defeats the module's end state (plan §1: a conclusion stays
re-runnable *once MindsOS reads text itself*). The description is checked here
as a plain mapping, key by key.

**Nothing unverifiable is stored** (R9): every property is either derived from
the file's bytes (``sha256``, ``responses``, ``key_schema_version``,
``credential_level``) or a fact about the write itself (``file_uri``,
``recorded_at``, ``recorded_by``, ``note``, ``storage_mode``).
"""

from __future__ import annotations

from typing import Any, List, Mapping, Optional

from .identifiers import ROLE_RECORDED_SETS, recorded_set_iri
from .schemas.recorded_sets import NODE_RECORDED_SET, PAYLOAD_STORAGE_MODE


PROP_SHA256 = "sha256"
PROP_FILE_URI = "file_uri"
PROP_RESPONSES = "responses"
PROP_KEY_SCHEMA_VERSION = "key_schema_version"
PROP_RECORDED_AT = "recorded_at"
PROP_RECORDED_BY = "recorded_by"
PROP_STORAGE_MODE = "storage_mode"
PROP_CREDENTIAL_LEVEL = "credential_level"
PROP_NOTE = "note"

#: What a description must carry — exactly what ``describe_set`` returns (R13).
DESCRIPTION_KEYS = (
    "path",
    "sha256",
    "responses",
    "key_schema_version",
    "identities",
    "prompts",
    "request_keys",
    "credential_level",
)

#: The payload: the derived manifest plus the SORTED request_keys (ADR-0210
#: am-4, am-6). The keys are load-bearing — a conclusion carries a
#: request_key and nothing else that names its set.
PAYLOAD_KEYS = ("responses", "key_schema_version", "identities", "prompts", "request_keys")


class RecordedSetStoreError(Exception):
    """Base for recorded-sets store refusals."""


class RecordedSetDescriptionError(RecordedSetStoreError):
    """The mapping handed in is not a description of a recorded-set file."""


class RecordedSetExistsError(RecordedSetStoreError):
    """A pointer to these exact bytes is already stored (R8, R18)."""


class RecordedSetNotFoundError(RecordedSetStoreError):
    """This view holds no pointer with that ``sha256``."""


def _checked(description: Mapping[str, Any]) -> Mapping[str, Any]:
    missing = [k for k in DESCRIPTION_KEYS if k not in description]
    if missing:
        raise RecordedSetDescriptionError(
            f"description is missing {missing!r}. A pointer is written from "
            f"what the file proves, and a field the caller did not derive "
            f"would be a claim about it instead."
        )
    keys = list(description["request_keys"])
    if not keys:
        raise RecordedSetDescriptionError(
            "description names no request_keys; a pointer to it could never "
            "be reached from a conclusion."
        )
    if keys != sorted(keys):
        raise RecordedSetDescriptionError(
            "request_keys are not sorted. The payload is binary-searched from "
            "a conclusion's request_key, so an unsorted list answers 'not "
            "here' for keys that are."
        )
    if len(keys) != int(description["responses"]):
        raise RecordedSetDescriptionError(
            f"description counts {description['responses']!r} responses but "
            f"lists {len(keys)} request_keys; it does not describe one file."
        )
    return description


def write_recorded_set(
    handle: Any,
    *,
    description: Mapping[str, Any],
    recorded_by: str,
    recorded_at: str,
    note: Optional[str] = None,
) -> Any:
    """Append one recorded-set pointer through ``handle``.

    ``handle`` is a :class:`~mindsos_knowledge.write_handle.KLWriteHandle`
    bound to ``(ROLE_RECORDED_SETS, "local")``.

    ``file_uri`` is the description's ``path`` — the file that was HASHED —
    and is never a separate argument (R18), so the pointer cannot name one
    file and carry another's identity.

    ``credential_level`` becomes a property only when it is an ``int`` (R15):
    ``None`` means the payloads state no level, and a stored ``None`` would read
    as a level. The file still distinguishes *"no credential in force"* from
    *"recorded before levels were stamped"*, and the ``sha256`` makes the file
    verifiable.

    Raises:
        RecordedSetDescriptionError: ``description`` is not one.
        RecordedSetExistsError: these exact bytes are already pointed at.
    """
    d = _checked(description)
    sha = str(d["sha256"])
    iri = handle.mint_iri(NODE_RECORDED_SET, sha256=sha)
    if handle.graph().nodes.get(iri) is not None:
        raise RecordedSetExistsError(
            f"a pointer to these exact bytes already exists at {iri}. The "
            f"identity is the file's sha256 (R8): a re-capture of the same "
            f"bytes is the same set, and append_only means it is not written "
            f"twice. A changed or re-exported set is different bytes."
        )
    properties = {
        PROP_SHA256: sha,
        PROP_FILE_URI: str(d["path"]),
        PROP_RESPONSES: int(d["responses"]),
        PROP_KEY_SCHEMA_VERSION: str(d["key_schema_version"]),
        PROP_RECORDED_AT: str(recorded_at),
        PROP_RECORDED_BY: str(recorded_by),
        PROP_STORAGE_MODE: PAYLOAD_STORAGE_MODE,
    }
    level = d["credential_level"]
    if isinstance(level, int) and not isinstance(level, bool):
        properties[PROP_CREDENTIAL_LEVEL] = level
    if note:
        properties[PROP_NOTE] = str(note)
    payload = {k: d[k] for k in PAYLOAD_KEYS}
    payload["request_keys"] = list(d["request_keys"])
    return handle.write_and_validate(
        value=payload,
        type_=NODE_RECORDED_SET,
        properties=properties,
        sha256=sha,
    )


def recorded_sets(view: Any) -> List[Any]:
    """Every ``RecordedSet`` pointer in ``view`` (a user's Local view)."""
    return list(view.iter_nodes(ROLE_RECORDED_SETS, type_=NODE_RECORDED_SET))


def recorded_set_at(view: Any, sha256: str) -> Any:
    """The pointer whose identity is ``sha256``.

    Raises:
        RecordedSetNotFoundError: this view holds none. No nearest match —
            a pointer to a different file answers a different question.
    """
    wanted = str(sha256)
    for node in recorded_sets(view):
        if (node.properties or {}).get(PROP_SHA256) == wanted:
            return node
    raise RecordedSetNotFoundError(
        f"no recorded set with sha256 {wanted!r} in this view "
        f"(address {recorded_set_iri('v1', wanted) if len(wanted) == 64 else 'n/a'})."
    )


__all__ = [
    "DESCRIPTION_KEYS",
    "PAYLOAD_KEYS",
    "PROP_CREDENTIAL_LEVEL",
    "PROP_FILE_URI",
    "PROP_KEY_SCHEMA_VERSION",
    "PROP_NOTE",
    "PROP_RECORDED_AT",
    "PROP_RECORDED_BY",
    "PROP_RESPONSES",
    "PROP_SHA256",
    "PROP_STORAGE_MODE",
    "RecordedSetDescriptionError",
    "RecordedSetExistsError",
    "RecordedSetNotFoundError",
    "RecordedSetStoreError",
    "recorded_set_at",
    "recorded_sets",
    "write_recorded_set",
]
