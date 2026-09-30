"""Excision — the borrowed model is a removable stand-in (plan item I-12).

``docs/plans/MINDSOS_LLM_PLAN.md`` §1: every conclusion that leaned on the
borrowed model can be **identified** as such, **shown** (including what was
asked), and **re-run** without it. This module is the L4 half — it locates and
dispatches; judging agreement is L3's (plan R28, R39). I-12 ships in four
gates, one claim each (plan §6, 2026-09-29); gate 1 builds IDENTIFY.

**Identified** (R26, R38): an origin record whose ``origin_method`` is
``read_by_model``, in every mode — a replayed answer is still the model's —
refusals the model produced included, and ``environment_fault`` refusals
excluded, because no reading happened. ⚠ Measured 2026-09-29: no reader writes
an ``environment_fault`` record today (``comprehension_v0`` raises on an
outage instead), so the exclusion filters nothing the tree emits. It stays:
the field is derived from the refusal reason, and a producer that one day
records its outage must not be listed as a reading.

**Domain** (R27): the run graphs of a persisted Episode — ``read_episode``'s
``capacity_run_graphs`` — the only place a conclusion's source text lives.
The walk reads nodes only, so it answers the same on a live graph and on one
reloaded from FalkorDB; ``tests/llm_seam/test_excision_identifies.py`` proves
the round trip.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Mapping, Tuple

from mindsos_capacity.builtins.origin_v0 import (
    FIELD_ENVIRONMENT_FAULT,
    FIELD_ORIGIN_METHOD,
    ORIGIN_READ_BY_MODEL,
    origin_record_iri,
)
from mindsos_capacity.identifiers import (
    NODE_TYPE_DATASTATE_INSTANCE,
    PROP_DATASTATE_INSTANCE_TYPE,
)

#: The suffix every origin-record DataState carries, taken from the one
#: function that makes it rather than spelled again here.
_ORIGIN_SUFFIX = origin_record_iri("")


@dataclass(frozen=True)
class ModelConclusion:
    """One conclusion the borrowed model produced, as found in a run graph."""

    graph_id: str
    record_node_id: str
    value_datastate: str
    record: Mapping[str, Any]


def _is_model_reading(record: Any) -> bool:
    return (
        isinstance(record, Mapping)
        and record.get(FIELD_ORIGIN_METHOD) == ORIGIN_READ_BY_MODEL
        and record.get(FIELD_ENVIRONMENT_FAULT) is not True
    )


def identify(graphs: Iterable[Any]) -> Tuple[ModelConclusion, ...]:
    """Every model-produced conclusion in ``graphs``, in a stable order."""
    found: List[ModelConclusion] = []
    for graph in graphs:
        for node in graph.nodes.values():
            if node.type_name != NODE_TYPE_DATASTATE_INSTANCE:
                continue
            instance_type = (node.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE)
            if not isinstance(instance_type, str) or not instance_type.endswith(_ORIGIN_SUFFIX):
                continue
            if not _is_model_reading(node.value):
                continue
            found.append(
                ModelConclusion(
                    graph_id=graph.graph_id,
                    record_node_id=node.node_id,
                    value_datastate=instance_type[: -len(_ORIGIN_SUFFIX)],
                    record=node.value,
                )
            )
    return tuple(sorted(found, key=lambda c: (c.graph_id, c.record_node_id)))


__all__ = ["ModelConclusion", "identify"]
