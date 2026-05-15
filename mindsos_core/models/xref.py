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

**Phase 09 P53 — drop inert fields.** v3 baseline carried two fields
with no setters (``target_stale`` + ``deprecated_at``); both ship in
Phase 10 alongside their setters. P09 omits them so the deserialiser
cannot smuggle stale values through state-file injection.

**Phase 09 P57 — kw_only.** Matches the Phase 05a precedent
(``MetaEdge`` / ``MetaHyperEdge``). Eliminates positional API
fragility for future field reorders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

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
    """

    source_metagraph_id: str
    source_id: str
    target_metagraph_id: str
    target_role: str
    target_id: str
    ref_type: str
    xref_id: str = field(default_factory=generate_uuid)
    properties: Dict[str, Any] = field(default_factory=dict)

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
