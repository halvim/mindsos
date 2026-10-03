"""Excision's judgements — the L3 half of plan item I-12.

``docs/plans/MINDSOS_LLM_PLAN.md`` R39: judging agreement between two values
is a capability (R28 puts it in L3), and L4 dispatches it. The category is
``predicate`` — the family ``predicate.sufficient`` already uses for a verdict
L4 dispatches — so its don't-know shape is ``NO_DONT_KNOW``: a verdict always
answers, and a check that cannot run is a named failure, never a guess.

**Shown is what ran** (R20, R24, R36, R40). Two independent checks:

* the **key**: ``request_key`` recomputed from the record's stamps and the
  source text found in the grounding graph (R27) must equal the record's. One
  match verifies the source text, the schema, the framing and the model
  settings at once, because the v2 key hashes all of them (R22);
* the **words**: ``text_digest`` of the stored prompt edition must equal the
  record's ``prompt_digest``. Core does not guarantee the words sent are the
  stored edition; it detects a mismatch (R36).

A record keyed under v1 carries no ``key_schema_version`` stamp (R34) and the
tree holds no v1 key function, so it is reported unverifiable rather than
guessed at.

**A re-derived value agrees** (R28, R41) when its canonical JSON equals the
model's — exactly, a refusal's ``null`` included. No ruling admits a
tolerance, and Python's ``==`` is not the test: it calls ``True`` and ``1``
equal, and they are different conclusions.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional

from mindsos_llm.recording import (
    KEY_SCHEMA_VERSION,
    UNSTAMPED_KEY_SCHEMA_VERSION,
    text_digest,
    what_was_asked,
)

from ..bootstrap import ensure_datastate_graph
from ..capacity import Capacity
from ..datastate import DataState, ShapeDescriptor
from ..identifiers import CATEGORY_PREDICATE, capacity_iri, datastate_iri

DS_SHOWN_CLAIM = datastate_iri("excision.shown_claim")
DS_SHOWN_VERDICT = datastate_iri("excision.shown_verdict")
DS_REDERIVED_CLAIM = datastate_iri("excision.rederived_claim")
DS_REDERIVED_VERDICT = datastate_iri("excision.rederived_verdict")

SHOWN_IS_WHAT_RAN_IRI = capacity_iri(CATEGORY_PREDICATE, "shown_is_what_ran")
REDERIVED_AGREES_IRI = capacity_iri(CATEGORY_PREDICATE, "rederived_agrees")

#: The four failures *shown* can name (plan R40). Nothing is shown in the
#: place of what failed.
SHOWN_KEY_UNVERIFIABLE = "keyed_under_an_unverifiable_key_version"
SHOWN_SOURCE_NOT_FOUND = "source_text_not_in_the_grounding_graph"
SHOWN_NOT_WHAT_RAN = "shown_material_is_not_what_ran"
SHOWN_NO_EDITION_MATCHES = "no_stored_edition_matches_what_ran"


def _recomputed_key(record: Mapping[str, Any], source_text: str) -> Optional[str]:
    try:
        return what_was_asked(
            prompt_iri=record["prompt_iri"],
            prompt_version=record["prompt_version"],
            prompt_digest=record["prompt_digest"],
            extraction_schema=json.loads(record["extraction_schema"]),
            tool_name=record["tool_name"],
            tool_description=record["tool_description"],
            max_tokens=record["max_tokens"],
            model_id=record["model_id"],
            model_version=record["model_version"],
            temperature=record["temperature"],
            source_text=source_text,
        )["request_key"]
    except (KeyError, TypeError, ValueError):
        return None


def judge_shown(
    record: Mapping[str, Any],
    source_text: Optional[str],
    edition_text: Optional[str],
) -> Dict[str, Any]:
    """The verdict on one conclusion's shown material. Pure; no store."""
    failures: List[str] = []
    version = record.get("key_schema_version") or UNSTAMPED_KEY_SCHEMA_VERSION
    key_verified = False
    if version != KEY_SCHEMA_VERSION:
        failures.append(SHOWN_KEY_UNVERIFIABLE)
    elif source_text is None:
        failures.append(SHOWN_SOURCE_NOT_FOUND)
    elif _recomputed_key(record, source_text) == record.get("request_key"):
        key_verified = True
    else:
        failures.append(SHOWN_NOT_WHAT_RAN)
    edition_verified = (
        edition_text is not None
        and record.get("prompt_digest") == text_digest(edition_text)
    )
    if not edition_verified:
        failures.append(SHOWN_NO_EDITION_MATCHES)
    return {
        "verified": not failures,
        "failures": failures,
        "key_verified": key_verified,
        "edition_verified": edition_verified,
    }


def _shown_is_what_ran(**kwargs: Any) -> Dict[str, Any]:
    claim = kwargs[DS_SHOWN_CLAIM]
    return {
        DS_SHOWN_VERDICT: judge_shown(
            claim["record"], claim.get("source_text"), claim.get("edition_text")
        )
    }


def build_shown_is_what_ran() -> Capacity:
    return Capacity(
        name="shown_is_what_ran",
        category=CATEGORY_PREDICATE,
        inputs=(DS_SHOWN_CLAIM,),
        outputs=(DS_SHOWN_VERDICT,),
        implementation=_shown_is_what_ran,
        description=(
            "Whether a model-produced conclusion's shown material is what ran: "
            "the recomputed request_key and the stored prompt edition's digest."
        ),
    )


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def judge_agreement(model_value: Any, rederived_value: Any) -> Dict[str, Any]:
    """Whether a re-derived value IS the model's (plan R41). Pure; no store."""
    return {"agrees": _canonical(model_value) == _canonical(rederived_value)}


def _rederived_agrees(**kwargs: Any) -> Dict[str, Any]:
    claim = kwargs[DS_REDERIVED_CLAIM]
    return {
        DS_REDERIVED_VERDICT: judge_agreement(
            claim["model_value"], claim["rederived_value"]
        )
    }


def build_rederived_agrees() -> Capacity:
    return Capacity(
        name="rederived_agrees",
        category=CATEGORY_PREDICATE,
        inputs=(DS_REDERIVED_CLAIM,),
        outputs=(DS_REDERIVED_VERDICT,),
        implementation=_rederived_agrees,
        description=(
            "Whether a value re-derived without the model is the model's: "
            "exact equality of canonical JSON, a refusal's null included."
        ),
    )


def _excision_datastates() -> List[DataState]:
    return [
        DataState(
            name=name,
            shape=ShapeDescriptor.opaque(name),
            description="Excision (plan I-12) DataState.",
            provenance_category=CATEGORY_PREDICATE,
        )
        for name in (
            "excision.shown_claim",
            "excision.shown_verdict",
            "excision.rederived_claim",
            "excision.rederived_verdict",
        )
    ]


def install_excision_v0(capacity_layer) -> None:
    """Register excision's judgements in Global. Idempotent; opt-in, like
    ``install_orchestration_v0`` — nothing boots it until a caller needs it."""
    metagraph = capacity_layer.global_metagraph()
    ds_graph = ensure_datastate_graph(metagraph, strict=capacity_layer._strict)
    for ds in _excision_datastates():
        if datastate_iri(ds.name) not in ds_graph.nodes:
            capacity_layer.register_datastate(ds, allow_new_realm=True)
    index = capacity_layer._capacity_index.get(metagraph.metagraph_id, {})
    if SHOWN_IS_WHAT_RAN_IRI not in index:
        capacity_layer.register_capacity(build_shown_is_what_ran())
    if REDERIVED_AGREES_IRI not in index:
        capacity_layer.register_capacity(build_rederived_agrees())


__all__ = [
    "DS_REDERIVED_CLAIM",
    "DS_REDERIVED_VERDICT",
    "DS_SHOWN_CLAIM",
    "DS_SHOWN_VERDICT",
    "REDERIVED_AGREES_IRI",
    "SHOWN_IS_WHAT_RAN_IRI",
    "SHOWN_KEY_UNVERIFIABLE",
    "SHOWN_NOT_WHAT_RAN",
    "SHOWN_NO_EDITION_MATCHES",
    "SHOWN_SOURCE_NOT_FOUND",
    "build_rederived_agrees",
    "build_shown_is_what_ran",
    "install_excision_v0",
    "judge_agreement",
    "judge_shown",
]
