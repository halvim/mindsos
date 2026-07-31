"""L4 D'1 inline-on-retire read consumer (ADR-0177 §2; Chat B §4.4).

Resolves an episode's version-pinned ``(node_iri, version_int)`` references via
``kl.read_at_version``; when a version node carries the
``_retired_inline_pending`` marker (ADR-0161/0177, written by
``kl.retire_version``), the content is inlined — the lazy inline-on-retire
path. Outgoing refs of inlined content stay pinned and inline on their own
next read (bounded transitive inflation: one level per read).

**v1 consumer status (PB-9):** the v1 dream driver re-runs from the episode's
``task_input`` rather than reconstructing the full episode MM, so this
resolver has **no live v1 consumer** and ships unit-test-only. Its real
consumers — episode reconstruction / retrieval — wire later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Tuple

_RETIRE_MARKER = "_retired_inline_pending"


@dataclass
class ResolvedRef:
    iri: str
    version: int
    value: Any
    inlined: bool  # True iff the version was retired → content inlined (D'1)


def resolve_ref(kl: Any, iri: str, version: int) -> Optional[ResolvedRef]:
    """Resolve a single version-pinned ref. Returns ``None`` when unknown.
    ``inlined=True`` signals the retired-content lazy inline (the marker was
    consulted on this read)."""
    node = kl.read_at_version(iri, version)
    if node is None:
        return None
    props = getattr(node, "properties", {}) or {}
    return ResolvedRef(
        iri=iri,
        version=version,
        value=getattr(node, "value", None),
        inlined=bool(props.get(_RETIRE_MARKER)),
    )


def resolve_refs(
    kl: Any, refs: Iterable[Tuple[str, int]]
) -> List[ResolvedRef]:
    """Resolve version-pinned ``(iri, version)`` refs, inlining retired versions
    lazily (bounded transitive inflation — one level per read, ADR-0177)."""
    out: List[ResolvedRef] = []
    for iri, version in refs:
        resolved = resolve_ref(kl, iri, version)
        if resolved is not None:
            out.append(resolved)
    return out


__all__ = ["ResolvedRef", "resolve_ref", "resolve_refs"]
