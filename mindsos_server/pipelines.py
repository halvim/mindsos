"""Read/write accessors over the brain's pipelines.

Two sources, per the design decision (PB-3):

* **promoted** — ``Pipeline`` nodes in the Global ``promoted-pipelines``
  role-graph (ADR-0071 promotion output).
* **learned** — taught ``ConjunctionFinder`` pipelines in a user's Local
  ``learned-pipelines`` role-graph (ADR-0203). Each teach APPENDS an
  immutable ``LearnedPipeline`` node whose ``value`` is the full
  ``Pipeline.to_dict()`` opaque ADR-0182 blob (incl. ``edges`` +
  ``start_datastates``); ``pipeline_name`` is a flat content property and
  ``taught_seq`` is the append ordinal. Latest-per-name is resolved at read
  time by ``max(taught_seq)`` — there is no active-version routing to filter
  (ADR-0150 §am-3), mirroring the ``installed-skills`` append-ordinal reader
  (``mindsos_server/skills/records.py``).

**Supersession (ADR-0203 §Q5).** The pre-existing shape-guess reader
``iter_learned_pipelines`` (a ``LearnedParameter`` value-dict discriminated by
``"steps" in val and "target_datastate" in val``, ignoring ``edges``) is
replaced by :func:`iter_local_pipelines` over the dedicated role. It had zero
external importers — only :func:`iter_pipelines` called it — so the only
contract preserved is ``iter_pipelines(scope=...)`` behaviour (its real
consumer is the CLI ``brain.py``), which still yields ``(source, node)``.

Server-layer read/write over ``kl`` (mirrors ``skills.records`` / ``episodes``)
so the CLI never reaches into L2 internals; no versioned domain surface.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Iterator, List, Tuple

from mindsos_knowledge import (
    ROLE_LEARNED_PIPELINES,
    ROLE_PROMOTED_PIPELINES,
    learned_pipeline_iri,
)
from mindsos_knowledge.schemas.learned_pipelines import NODE_LEARNED_PIPELINE

_PROMOTED_PIPELINE_TYPE = "Pipeline"

#: Role-version literal embedded into minted learned-pipeline IRIs. The
#: single version under the current one-graph-per-role store (ADR-0150 §am-3);
#: matches ``KnowledgeLayer.writeable``'s default ``"v1"``.
_LEARNED_PIPELINE_VERSION = "v1"


def _now_iso() -> str:
    """ISO-8601 UTC millisecond timestamp (Phase 18 PB-35 format)."""
    now = datetime.now(UTC)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def iter_promoted_pipelines(kl: Any) -> Iterator[Any]:
    """Yield Global promoted ``Pipeline`` nodes, sorted by IRI."""
    hits = []
    for g in kl.global_metagraph().graphs.values():
        if g.role == ROLE_PROMOTED_PIPELINES:
            hits.extend(
                n for n in g.nodes.values()
                if n.type_name == _PROMOTED_PIPELINE_TYPE
            )
    for n in sorted(hits, key=lambda n: n.node_id):
        yield n


def _learned_pipelines_graph(kl: Any, user: str):
    """The user's Local ``learned-pipelines`` role-graph, or ``None``.

    Reads through ``kl.local_metagraph(user)`` (lazy-ensures the Local named
    roles, incl. ``learned-pipelines``). A reloaded Local (F9) comes back
    schema-less system-wide, but node ``type_name`` + properties still read.
    """
    mg = kl.local_metagraph(user)
    for g in mg.graphs.values():
        if g.role == ROLE_LEARNED_PIPELINES:
            return g
    return None


def _iter_learned_pipeline_nodes(kl: Any, user: str) -> List[Any]:
    """All ``LearnedPipeline`` nodes in the user's Local, taught_seq-ascending.

    Global append order (like ``skills.records.iter_skill_records``): the
    monotonic ``taught_seq`` gives a total order across all names.
    """
    g = _learned_pipelines_graph(kl, user)
    if g is None:
        return []
    nodes = [
        n for n in g.nodes.values() if n.type_name == NODE_LEARNED_PIPELINE
    ]
    nodes.sort(key=lambda n: int((n.properties or {}).get("taught_seq", 0)))
    return nodes


def iter_local_pipelines(kl: Any, user: str) -> Iterator[Any]:
    """Yield the latest ``LearnedPipeline`` node per ``pipeline_name`` (ADR-0203).

    Groups by ``pipeline_name`` and keeps the highest ``taught_seq`` (the last
    teach of that name) — the read-time last-active resolution the append-only
    ``installed-skills`` reader uses (``latest_records_by_bundle``). Yields one
    node per name, name-sorted for deterministic ``pl`` output.
    """
    latest: dict[str, Any] = {}
    for n in _iter_learned_pipeline_nodes(kl, user):  # taught_seq-ascending
        name = str((n.properties or {}).get("pipeline_name"))
        latest[name] = n  # later (higher-seq) wins
    for name in sorted(latest):
        yield latest[name]


def iter_pipelines(
    kl: Any, user: str, scope: str = "both"
) -> Iterator[Tuple[str, Any]]:
    """Yield ``(source, node)`` where source is ``promoted`` | ``learned``.

    ``scope`` ``global`` -> promoted only; ``local`` -> learned only;
    ``both`` -> promoted then learned. Behaviourally stable across the
    ADR-0203 reader supersession: the learned half now resolves latest-per-name
    over the dedicated ``learned-pipelines`` role.
    """
    if scope in ("both", "global"):
        for n in iter_promoted_pipelines(kl):
            yield ("promoted", n)
    if scope in ("both", "local"):
        for n in iter_local_pipelines(kl, user):
            yield ("learned", n)


def learn_pipeline(kl: Any, user: str, name: str, pipeline: Any) -> Any:
    """Teach (persist) a composed ``Pipeline`` under ``name`` for ``user``.

    APPENDS a new immutable ``LearnedPipeline`` node (ADR-0203,
    ``immutable_successor``): re-teaching a name does NOT replace or link a
    successor — it appends a fresh node stamped with the next monotonic
    ``taught_seq``; the reader returns the max-ordinal node per name. Not
    idempotent-by-name.

    The node ``value`` is the full ``pipeline.to_dict()`` opaque ADR-0182 blob
    (all four keys incl. ``edges`` + ``start_datastates``); ``pipeline_name``
    (content) + ``taught_seq`` / ``recorded_at`` (metadata) are lifted flat as
    queryable properties (ADR-0182 rule 5). The blob is validated by a
    ``from_dict`` round-trip before persist (§P2) — a Pipeline whose codec form
    does not reconstruct identically is rejected rather than silently stored.

    Returns the newly-appended :class:`Node`.
    """
    from mindsos_capacity.pipeline import Pipeline

    blob = pipeline.to_dict()
    # ADR-0203 §P2 — opaque blob validated by from_dict round-trip. (Capacity
    # resolution + DAG-reaches-target are the consumer's obligation and need a
    # CapacityLayer the server writer does not hold.)
    if Pipeline.from_dict(blob) != pipeline:
        raise ValueError(
            f"learn_pipeline({name!r}): Pipeline does not round-trip through "
            f"its ADR-0182 to_dict/from_dict codec; refusing to persist a "
            f"lossy blob."
        )

    mg = kl.local_metagraph(user)  # lazy-ensures the learned-pipelines graph
    g = None
    for cand in mg.graphs.values():
        if cand.role == ROLE_LEARNED_PIPELINES:
            g = cand
            break
    if g is None:  # pragma: no cover — lazy-ensure guarantees presence
        raise KeyError(
            f"learn_pipeline: no {ROLE_LEARNED_PIPELINES!r} role-graph in "
            f"Local for user {user!r}."
        )

    existing = _iter_learned_pipeline_nodes(kl, user)  # taught_seq-ascending
    seq = (
        int((existing[-1].properties or {}).get("taught_seq", 0)) + 1
        if existing
        else 1
    )
    iri = learned_pipeline_iri(
        _LEARNED_PIPELINE_VERSION, pipeline_name=name, record_id=str(seq)
    )
    g.add_node(
        blob,
        NODE_LEARNED_PIPELINE,
        properties={
            "pipeline_name": name,
            "taught_seq": seq,
            "recorded_at": _now_iso(),
        },
        node_id=iri,
    )
    return g.nodes[iri]


__all__ = [
    "iter_promoted_pipelines",
    "iter_local_pipelines",
    "iter_pipelines",
    "learn_pipeline",
]
