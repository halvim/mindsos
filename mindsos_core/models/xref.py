"""Cross-metagraph reference primitive (ADR-0128, M2).

Per the L1 redesign hybrid model:

* **Cross-metagraph refs** (Local → Global, Local → Other-Local) become
  first-class :class:`XRef` rows on this primitive. Validated at
  write time when the target metagraph is resolvable. Indexed lookup
  by source and by target makes the pivot's auto-upgrade migration
  cheap.
* **Intra-metagraph refs** continue to use the ``ref:<role>`` property
  string convention (ADR-0016 retained). Cheap, no auto-upgrade need,
  KL invariants unchanged.

The class lives in Core; persistence + reconstruction follow the
existing repository / loader pattern.

**Phase 10 P53 reversal — fields restored.** v3 baseline carried
``target_stale: bool`` and ``deprecated_at: datetime | None``; Phase 09
P53 dropped them as inert until setters shipped. Phase 10 restores both
alongside the XRef quartet (``mark_xref_stale`` / ``unmark_xref_stale`` /
``deprecate_xref`` / ``undeprecate_xref`` — PX2). ``target_stale`` is
also stamped by ``Metagraph.remove_graph(force=True)`` on every incoming
XRef of the removed graph (ADR-0135).

**Phase 09 P57 — kw_only.** Matches the Phase 05a precedent
(``MetaEdge`` / ``MetaHyperEdge``). Eliminates positional API
fragility for future field reorders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from .identity import generate_uuid


@dataclass(kw_only=True)
class XRef:
    """A first-class cross-metagraph reference (ADR-0128).

    Attributes:
        source_metagraph_id: Metagraph the source element lives in.
        source_id: id of the source ``Node``/``Edge``/``HyperEdge``.
        target_metagraph_id: Metagraph the target element lives in.
        target_role: Role of the target graph (e.g. ``"lexicon"``).
        target_id: id of the target element.
        ref_type: One of the KL ``REF_TYPES`` vocabulary
            (``SPECIALISES``, ``INSTANCE_OF``, ``RENAMES``, ``EXTENDS``,
            ``CONTRADICTS``, ``PROXY``, ``PROMOTED``). Core does not
            enforce the vocabulary — KL does at the write boundary.
        xref_id: UUID stable across the lifetime of the XRef.
        properties: Optional per-XRef property bag (rare; usually empty).
        target_stale: ``True`` once the target metagraph removal/archival
            invalidates this XRef's target id (Phase 10 P53 reversal;
            stamped by ``Metagraph.remove_graph(force=True)`` per
            ADR-0135, or by ``Metagraph.mark_xref_stale`` per ADR-0128
            §Revisions amendment-3). Readers respect by filtering or
            surfacing per consumer policy.
        deprecated_at: ``datetime`` when the XRef itself was deprecated
            (admin retired). ``None`` = active. Symmetric to Edge/HyperEdge
            soft-delete (ADR-0133). No ``disputed_at`` on XRef per
            ADR-0128 amendment-3.
    """

    source_metagraph_id: str
    source_id: str
    target_metagraph_id: str
    target_role: str
    target_id: str
    ref_type: str
    xref_id: str = field(default_factory=generate_uuid)
    properties: Dict[str, Any] = field(default_factory=dict)
    # Phase 10 P53 reversal — restored alongside the XRef quartet (PX2).
    target_stale: bool = False
    deprecated_at: Optional[datetime] = None

    def __hash__(self) -> int:
        return hash(self.xref_id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, XRef) and self.xref_id == other.xref_id

    def __repr__(self) -> str:
        return (
            f"XRef({self.source_id[:8]}-[{self.ref_type}]->"
            f"{self.target_metagraph_id[:8]}/{self.target_role}/"
            f"{self.target_id[:8]}, id={self.xref_id[:8]})"
        )


__all__ = ["XRef"]
