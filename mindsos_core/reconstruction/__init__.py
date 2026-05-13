"""Single-Graph reconstruction (Phase 07 — M14).

Phase 07 ships ``load_graph(client, graph_id) -> Graph`` only. Metagraph
loader + streaming (per ADR-0124) deferred to Phase 08.
"""

from __future__ import annotations

from .graph_loader import load_graph

__all__ = ["load_graph"]
