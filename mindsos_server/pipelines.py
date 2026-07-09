"""Read-only accessors over the brain's pipelines.

Two sources, per the design decision (PB-3):

* **promoted** — ``Pipeline`` nodes in the Global ``promoted-pipelines``
  role-graph (ADR-0071 promotion output).
* **learned** — pipeline-shaped ``LearnedParameter`` descriptors in a user's
  Local ``learned-parameters`` role-graph (a value dict carrying ``steps`` +
  ``target_datastate``; the composition-lifecycle descriptor form).

Server-layer readers over ``kl`` (mirrors ``skills.records`` / ``episodes``)
so the CLI never reaches into L2 internals; no versioned domain surface.
"""

from __future__ import annotations

from typing import Any, Iterator, Tuple

from mindsos_knowledge import ROLE_LEARNED_PARAMETERS, ROLE_PROMOTED_PIPELINES

_PROMOTED_PIPELINE_TYPE = "Pipeline"


def iter_promoted_pipelines(kl: Any) -> Iterator[Any]:
    """Yield Global promoted ``Pipeline`` nodes, sorted by IRI."""
    hits = []
    for g in kl.global_metagraph().graphs.values():
        if g.role == ROLE_PROMOTED_PIPELINES:
            hits.extend(n for n in g.nodes.values() if n.type_name == _PROMOTED_PIPELINE_TYPE)
    for n in sorted(hits, key=lambda n: n.node_id):
        yield n


def iter_learned_pipelines(kl: Any, user: str) -> Iterator[Any]:
    """Yield pipeline-shaped ``LearnedParameter`` nodes from a user's Local."""
    hits = []
    mg = kl.local_metagraph(user)
    for g in mg.graphs.values():
        if g.role == ROLE_LEARNED_PARAMETERS:
            for n in g.nodes.values():
                val = n.value if isinstance(n.value, dict) else {}
                if "steps" in val and "target_datastate" in val:
                    hits.append(n)
    for n in sorted(hits, key=lambda n: n.node_id):
        yield n


def iter_pipelines(kl: Any, user: str, scope: str = "both") -> Iterator[Tuple[str, Any]]:
    """Yield ``(source, node)`` where source is ``promoted`` | ``learned``.

    ``scope`` ``global`` -> promoted only; ``local`` -> learned only;
    ``both`` -> promoted then learned.
    """
    if scope in ("both", "global"):
        for n in iter_promoted_pipelines(kl):
            yield ("promoted", n)
    if scope in ("both", "local"):
        for n in iter_learned_pipelines(kl, user):
            yield ("learned", n)


__all__ = ["iter_promoted_pipelines", "iter_learned_pipelines", "iter_pipelines"]
