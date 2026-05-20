"""FrameNetImporter — FrameNet 1.7 → ``concepts`` Global role-graph.

Phase 15a per PB-6 dataset pin: FrameNet 1.7 (Berkeley click-through;
**NOT repo-shippable** — see ``docs/knowledge-sources/framenet.md`` for
the manual download instruction). Parses the FrameNet XML
distribution; per Phase 15a PB-15 the synthetic fixture under
``tests/phase_15a/fixtures/framenet_synth.xml`` is the test surface.

Writes into the ``concepts`` Global role-graph per ADR-0150 +
:func:`mindsos_knowledge.bootstrap.ensure_global_role_graph`. IRIs minted
via :func:`mindsos_knowledge.identifiers.framenet_frame_iri` /
``framenet_fe_iri`` / ``framenet_lu_iri`` per ADR-0045.

Per Phase 15a PB-14: importer auto-ensures ``concepts`` role-graph at
``run()`` top.

**Stats dict keys** (as returned in :class:`ImportResult.stats`):

* ``frames`` — number of Frame nodes.
* ``frame_elements`` — number of FrameElement nodes.
* ``lexical_units`` — number of LexicalUnit nodes.
* ``has_fe_edges`` — Frame→FE ``HAS_FE`` edges.
* ``evokes_edges`` — LU→Frame ``EVOKES`` edges.
* ``frame_relations`` — Frame→Frame relations (inherits, uses, etc.).
* ``fe_mappings_edges`` — FE→FE ``FE_MAPPED_TO`` edges (via frame-
  relation FE-to-FE mappings).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union

from mindsos_core import Metagraph

from mindsos_knowledge.bootstrap import ensure_global_role_graph
from mindsos_knowledge.identifiers import (
    framenet_fe_iri,
    framenet_frame_iri,
    framenet_lu_iri,
)
from mindsos_knowledge.schemas.concepts import (
    EDGE_EVOKES,
    EDGE_FE_MAPPED_TO,
    EDGE_HAS_FE,
    EDGE_INHERITS_FROM,
    EDGE_IS_CAUSATIVE_OF,
    EDGE_IS_INCHOATIVE_OF,
    EDGE_PERSPECTIVE_ON,
    EDGE_PRECEDES,
    EDGE_SUBFRAME_OF,
    EDGE_USES,
    NODE_FRAME,
    NODE_FRAME_ELEMENT,
    NODE_LEXICAL_UNIT,
)

from ..bootstrap import ImportResult, _resolve_source, _utcnow


__all__ = ["FrameNetImporter"]


SOURCE_NAME = "framenet"


# FrameNet frame-relation type → MindsOS EdgeType name.
_FRAME_REL_MAP: dict[str, str] = {
    "Inheritance": EDGE_INHERITS_FROM,
    "Using": EDGE_USES,
    "Perspective_on": EDGE_PERSPECTIVE_ON,
    "Subframe": EDGE_SUBFRAME_OF,
    "Precedes": EDGE_PRECEDES,
    "Causative_of": EDGE_IS_CAUSATIVE_OF,
    "Inchoative_of": EDGE_IS_INCHOATIVE_OF,
}


class FrameNetImporter:
    """Berkeley FrameNet 1.7 importer (Phase 15a).

    target_roles: ``("concepts",)`` per PB-22.
    """

    target_roles: tuple[str, ...] = ("concepts",)

    def __init__(
        self,
        source: Optional[Union[str, Path]] = None,
        *,
        version: str = "1.7",
    ):
        """Construct an importer instance.

        Args:
            source: Path to a FrameNet XML file (single-file synthetic
                fixture) OR a directory containing per-frame XML files
                (Berkeley FrameNet 1.7 distribution layout: ``frame/``
                + ``frRelation.xml``). Optional at construction.
            version: Dataset version string. Default ``"1.7"`` (the
                Phase 15a PB-6 pin for FrameNet).
        """
        self.source = source
        self.version = version

    def run(
        self,
        mg: Metagraph,
        source: Optional[Union[str, Path]] = None,
    ) -> ImportResult:
        """Parse FrameNet XML and write into the ``concepts`` role-graph."""
        path = _resolve_source(source if source is not None else self.source)

        graph = ensure_global_role_graph(mg, "concepts")

        parsed = _parse_framenet(path)
        stats = self._build(parsed, graph)

        return ImportResult(
            role="concepts",
            version=self.version,
            source=SOURCE_NAME,
            imported_at=_utcnow(),
            stats=stats,
        )

    def _build(self, parsed: "_ParsedConcepts", graph: Any) -> dict[str, int]:
        stats: dict[str, int] = {
            "frames": 0,
            "frame_elements": 0,
            "lexical_units": 0,
            "has_fe_edges": 0,
            "evokes_edges": 0,
            "frame_relations": 0,
            "fe_mappings_edges": 0,
        }

        frame_by_id: dict[str, Any] = {}
        fe_by_pair: dict[tuple[str, str], Any] = {}  # (frame_id, fe_id)
        lu_by_id: dict[str, Any] = {}

        # Frames.
        for frame_id, frame_name in parsed.frames:
            iri = framenet_frame_iri(self.version, frame_id)
            n = graph.add_node(
                value=frame_name,
                type_name=NODE_FRAME,
                node_id=iri,
                properties={
                    "frame_id": frame_id,
                    "imported_from": SOURCE_NAME,
                    "imported_version": self.version,
                },
            )
            frame_by_id[frame_id] = n
            stats["frames"] += 1

        # Frame elements + HAS_FE edges.
        for frame_id, fe_id, fe_name in parsed.frame_elements:
            iri = framenet_fe_iri(self.version, frame_id, fe_id)
            n = graph.add_node(
                value=fe_name,
                type_name=NODE_FRAME_ELEMENT,
                node_id=iri,
                properties={
                    "frame_id": frame_id,
                    "fe_id": fe_id,
                    "imported_from": SOURCE_NAME,
                    "imported_version": self.version,
                },
            )
            fe_by_pair[(frame_id, fe_id)] = n
            stats["frame_elements"] += 1

            frame_node = frame_by_id.get(frame_id)
            if frame_node is not None:
                graph.add_edge(frame_node, n, EDGE_HAS_FE)
                stats["has_fe_edges"] += 1

        # Lexical units + EVOKES edges.
        for lu_id, lu_name, frame_id in parsed.lexical_units:
            iri = framenet_lu_iri(self.version, lu_id)
            n = graph.add_node(
                value=lu_name,
                type_name=NODE_LEXICAL_UNIT,
                node_id=iri,
                properties={
                    "lu_id": lu_id,
                    "frame_id": frame_id,
                    "imported_from": SOURCE_NAME,
                    "imported_version": self.version,
                },
            )
            lu_by_id[lu_id] = n
            stats["lexical_units"] += 1

            frame_node = frame_by_id.get(frame_id)
            if frame_node is not None:
                graph.add_edge(n, frame_node, EDGE_EVOKES)
                stats["evokes_edges"] += 1

        # Frame-to-frame relations + FE-to-FE mappings within each.
        for super_id, sub_id, rel_type, fe_pairs in parsed.frame_relations:
            edge_type = _FRAME_REL_MAP.get(rel_type)
            if edge_type is None:
                continue
            super_node = frame_by_id.get(super_id)
            sub_node = frame_by_id.get(sub_id)
            if super_node is None or sub_node is None:
                continue
            # Frame-relation direction: child → parent (sub inherits
            # from super).
            graph.add_edge(sub_node, super_node, edge_type)
            stats["frame_relations"] += 1

            for super_fe_id, sub_fe_id in fe_pairs:
                super_fe = fe_by_pair.get((super_id, super_fe_id))
                sub_fe = fe_by_pair.get((sub_id, sub_fe_id))
                if super_fe is None or sub_fe is None:
                    continue
                graph.add_edge(sub_fe, super_fe, EDGE_FE_MAPPED_TO)
                stats["fe_mappings_edges"] += 1

        return stats


# ── Parsing ────────────────────────────────────────────────────────────


class _ParsedConcepts:
    """Parsed FrameNet structure — pure Python (no L1 references)."""

    __slots__ = ("frames", "frame_elements", "lexical_units", "frame_relations")

    def __init__(self) -> None:
        # (frame_id, frame_name)
        self.frames: list[tuple[str, str]] = []
        # (frame_id, fe_id, fe_name)
        self.frame_elements: list[tuple[str, str, str]] = []
        # (lu_id, lu_name, frame_id)
        self.lexical_units: list[tuple[str, str, str]] = []
        # (super_frame_id, sub_frame_id, rel_type, [(super_fe_id, sub_fe_id), ...])
        self.frame_relations: list[
            tuple[str, str, str, list[tuple[str, str]]]
        ] = []


def _parse_framenet(path: Path) -> _ParsedConcepts:
    """Parse a FrameNet XML source.

    Two layouts supported:

    1. **Synthetic single-file fixture** (Phase 15a tests) — one XML
       document with a ``<framenet>`` root containing all frames /
       frame-elements / lexical-units / frame-relations as direct
       children. Used for ``tests/phase_15a/fixtures/framenet_synth.xml``.

    2. **Berkeley distribution layout** — directory with ``frame/*.xml``
       (one frame per file) + ``frRelation.xml`` (cross-frame relations).
       Parser auto-detects by ``path.is_dir()``.

    Returns a :class:`_ParsedConcepts` with the four lists populated.
    """
    parser_mod = _xml_parser_module()
    parsed = _ParsedConcepts()

    if path.is_dir():
        _parse_framenet_directory(path, parser_mod, parsed)
    else:
        _parse_framenet_single_file(path, parser_mod, parsed)

    return parsed


def _local_name(tag: Any) -> str:
    """Strip namespace prefix from an ElementTree tag."""
    if isinstance(tag, str):
        return tag.rsplit("}", 1)[-1]
    return str(tag)


def _iter_tag(node: Any, tag: str) -> Any:
    """Yield descendants whose local name matches ``tag``."""
    for el in node.iter():
        if _local_name(el.tag) == tag:
            yield el


def _parse_framenet_single_file(
    path: Path, parser_mod: Any, parsed: _ParsedConcepts
) -> None:
    """Parse a synthetic single-file fixture."""
    tree = parser_mod.parse(str(path))
    root = tree.getroot()

    # Frames.
    for frame_el in _iter_tag(root, "frame"):
        frame_id = frame_el.get("ID") or frame_el.get("id", "")
        frame_name = frame_el.get("name", "")
        if frame_id:
            parsed.frames.append((frame_id, frame_name or frame_id))

            # FEs nested inside <frame>.
            for fe_el in _iter_tag(frame_el, "FE"):
                fe_id = fe_el.get("ID") or fe_el.get("id", "")
                fe_name = fe_el.get("name", "")
                if fe_id:
                    parsed.frame_elements.append((frame_id, fe_id, fe_name or fe_id))

            # LUs nested inside <frame>.
            for lu_el in _iter_tag(frame_el, "lexUnit"):
                lu_id = lu_el.get("ID") or lu_el.get("id", "")
                lu_name = lu_el.get("name", "")
                if lu_id:
                    parsed.lexical_units.append(
                        (lu_id, lu_name or lu_id, frame_id)
                    )

    # Frame relations (synthetic schema: <frameRelation type=... superFrame=... subFrame=...>).
    for rel_el in _iter_tag(root, "frameRelation"):
        rel_type = rel_el.get("type", "")
        super_id = rel_el.get("superFrame") or rel_el.get("superID", "")
        sub_id = rel_el.get("subFrame") or rel_el.get("subID", "")
        if not (rel_type and super_id and sub_id):
            continue
        fe_pairs: list[tuple[str, str]] = []
        for fer in _iter_tag(rel_el, "FERelation"):
            super_fe = fer.get("superID") or fer.get("superFE", "")
            sub_fe = fer.get("subID") or fer.get("subFE", "")
            if super_fe and sub_fe:
                fe_pairs.append((super_fe, sub_fe))
        parsed.frame_relations.append((super_id, sub_id, rel_type, fe_pairs))


def _parse_framenet_directory(
    path: Path, parser_mod: Any, parsed: _ParsedConcepts
) -> None:
    """Parse a Berkeley-layout FrameNet directory (``frame/`` + ``frRelation.xml``)."""
    frame_dir = path / "frame"
    if frame_dir.is_dir():
        for xml_file in sorted(frame_dir.glob("*.xml")):
            tree = parser_mod.parse(str(xml_file))
            root = tree.getroot()
            frame_id = root.get("ID") or root.get("id", "")
            frame_name = root.get("name", "")
            if not frame_id:
                continue
            parsed.frames.append((frame_id, frame_name or frame_id))

            for fe_el in _iter_tag(root, "FE"):
                fe_id = fe_el.get("ID") or fe_el.get("id", "")
                fe_name = fe_el.get("name", "")
                if fe_id:
                    parsed.frame_elements.append((frame_id, fe_id, fe_name or fe_id))

            for lu_el in _iter_tag(root, "lexUnit"):
                lu_id = lu_el.get("ID") or lu_el.get("id", "")
                lu_name = lu_el.get("name", "")
                if lu_id:
                    parsed.lexical_units.append(
                        (lu_id, lu_name or lu_id, frame_id)
                    )

    rel_path = path / "frRelation.xml"
    if rel_path.is_file():
        tree = parser_mod.parse(str(rel_path))
        root = tree.getroot()
        for rel_el in _iter_tag(root, "frameRelation"):
            rel_type = rel_el.get("type") or rel_el.getparent().get("name", "")  # type: ignore[union-attr]
            super_id = rel_el.get("superFrameID") or rel_el.get("superFrame", "")
            sub_id = rel_el.get("subFrameID") or rel_el.get("subFrame", "")
            if not (rel_type and super_id and sub_id):
                continue
            fe_pairs: list[tuple[str, str]] = []
            for fer in _iter_tag(rel_el, "FERelation"):
                super_fe = fer.get("superFEID") or fer.get("superFE", "")
                sub_fe = fer.get("subFEID") or fer.get("subFE", "")
                if super_fe and sub_fe:
                    fe_pairs.append((super_fe, sub_fe))
            parsed.frame_relations.append((super_id, sub_id, rel_type, fe_pairs))


def _xml_parser_module() -> Any:
    """Return :mod:`lxml.etree` if installed, else :mod:`xml.etree.ElementTree`."""
    try:
        from lxml import etree  # type: ignore[import-not-found]
        return etree
    except ImportError:
        import xml.etree.ElementTree as etree  # type: ignore[no-redef]
        return etree
