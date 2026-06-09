"""L4 retention monitoring instrumentation (Chat B §7 R1 / PB-QQ; ADR-0179 posture).

v1 ships **instrumentation only** — an episode count, an episode-size
histogram, a Memory count, and a Falkor-row count (nodes + edges) over a
user's ``episodic_memories`` Local. Retention **policy** (aging / top-K /
eviction) is deferred to v1.5 if growth is observed (PB-QQ); this module
exports the numbers Phase 49 surfaces but takes no action on them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
from mindsos_knowledge.metagraph_view import MetagraphView
from mindsos_knowledge.schemas.episodic_memories import NODE_EPISODE, NODE_MEMORY


@dataclass
class RetentionMetrics:
    episode_count: int
    memory_count: int
    size_histogram: Dict[str, int]
    falkor_row_count: int  # nodes + edges in the role-graph (Falkor-row proxy)


def _size_bucket(value: Any) -> str:
    n = len(repr(value))
    if n < 256:
        return "<256"
    if n < 1024:
        return "256-1k"
    if n < 4096:
        return "1k-4k"
    return ">=4k"


def export_retention_metrics(kl: Any, user_id: str) -> RetentionMetrics:
    """Compute retention metrics over ``user_id``'s ``episodic_memories`` Local.

    Returns zeroed metrics when the role-graph is absent (no episodes yet)."""
    graphs = MetagraphView(kl.local_metagraph(user_id)).graphs_by_role(
        ROLE_EPISODIC_MEMORIES
    )
    if not graphs:
        return RetentionMetrics(0, 0, {}, 0)
    g = graphs[0]
    episodes = [n for n in g.nodes.values() if n.type_name == NODE_EPISODE]
    memories = [n for n in g.nodes.values() if n.type_name == NODE_MEMORY]
    histogram: Dict[str, int] = {}
    for n in episodes:
        bucket = _size_bucket(n.value)
        histogram[bucket] = histogram.get(bucket, 0) + 1
    return RetentionMetrics(
        episode_count=len(episodes),
        memory_count=len(memories),
        size_histogram=histogram,
        falkor_row_count=len(g.nodes) + len(g.edges),
    )


__all__ = ["RetentionMetrics", "export_retention_metrics"]
