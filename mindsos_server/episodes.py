"""Read-only accessors over a user's Local Episodes.

The resident-brain REPL's ``episodes`` / ``episode`` probe verbs (and the
``status`` count) need to enumerate a user's Episodes without the CLI
reaching across into L2 metagraph internals. This mirrors the
``mindsos_server.skills.records`` pattern: a server-layer reader over
``kl`` that keeps the L2 domain surface untouched (no version bump).

An Episode is a node of type ``"Episode"`` in the Local
``episodic_memories`` role-graph (ADR-0044; §am-3 renamed ``memories`` ->
``episodic_memories``).
"""

from __future__ import annotations

from typing import Any, Iterator, Optional

from mindsos_knowledge import ROLE_EPISODIC_MEMORIES

_EPISODE_TYPE = "Episode"


def _episodic_graph(kl: Any, user: str):
    """The user's Local ``episodic_memories`` role-graph, or ``None``."""
    mg = kl.local_metagraph(user)
    for g in mg.graphs.values():
        if g.role == ROLE_EPISODIC_MEMORIES:
            return g
    return None


def iter_episodes(kl: Any, user: str) -> Iterator[Any]:
    """Yield ``user``'s Local Episode nodes, sorted by IRI."""
    g = _episodic_graph(kl, user)
    if g is None:
        return
    eps = [n for n in g.nodes.values() if n.type_name == _EPISODE_TYPE]
    for n in sorted(eps, key=lambda n: n.node_id):
        yield n


def get_episode(kl: Any, user: str, iri: str) -> Optional[Any]:
    """Return one Episode node by IRI, or ``None`` if absent/wrong type."""
    g = _episodic_graph(kl, user)
    if g is None:
        return None
    n = g.nodes.get(iri)
    if n is None or n.type_name != _EPISODE_TYPE:
        return None
    return n


__all__ = ["iter_episodes", "get_episode"]
