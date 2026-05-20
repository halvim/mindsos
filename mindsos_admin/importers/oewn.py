"""OewnImporter — Open English WordNet 2024 → ``lexicon`` Global role-graph.

Phase 15a per PB-6 dataset pin: OEWN 2024 (CC-BY-SA 4.0; repo-shippable).
Parses the OEWN-LMF XML distribution.

Writes into the ``lexicon`` Global role-graph per ADR-0150 +
:func:`mindsos_knowledge.bootstrap.ensure_global_role_graph`. IRIs minted
via :func:`mindsos_knowledge.identifiers.oewn_synset_iri` /
``oewn_sense_iri`` / ``oewn_lemma_iri`` per ADR-0045.

Per Phase 15a PB-14: importer auto-ensures ``lexicon`` role-graph at
``run()`` top.

**Stats dict keys** (as returned in :class:`ImportResult.stats`):

* ``synsets`` — number of Synset nodes.
* ``lemmas`` — number of Lemma nodes (deduped across senses).
* ``senses`` — number of Sense nodes.
* ``has_sense_edges`` — Lemma→Sense ``HAS_SENSE`` edges.
* ``in_synset_edges`` — Sense→Synset ``IN_SYNSET`` edges.
* ``synset_relations`` — synset-level relation edges (hypernym,
  meronym, etc.).
* ``sense_relations`` — sense-level relation edges (antonym,
  derivationally-related-to, etc.).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union

from mindsos_core import Metagraph

from mindsos_knowledge.bootstrap import ensure_global_role_graph
from mindsos_knowledge.identifiers import (
    oewn_lemma_iri,
    oewn_sense_iri,
    oewn_synset_iri,
)
from mindsos_knowledge.schemas.lexicon import (
    EDGE_ANTONYM_OF,
    EDGE_DERIVATIONALLY_RELATED_TO,
    EDGE_HAS_SENSE,
    EDGE_HOLONYM_MEMBER_OF,
    EDGE_HOLONYM_PART_OF,
    EDGE_HOLONYM_SUBSTANCE_OF,
    EDGE_HYPERNYM_OF,
    EDGE_HYPONYM_OF,
    EDGE_INSTANCE_HYPERNYM_OF,
    EDGE_INSTANCE_HYPONYM_OF,
    EDGE_IN_SYNSET,
    EDGE_MERONYM_MEMBER_OF,
    EDGE_MERONYM_PART_OF,
    EDGE_MERONYM_SUBSTANCE_OF,
    EDGE_SIMILAR_TO,
    NODE_LEMMA,
    NODE_SENSE,
    NODE_SYNSET,
)

from ..bootstrap import ImportResult, _resolve_source, _utcnow


__all__ = ["OewnImporter"]


SOURCE_NAME = "oewn"


# OEWN synset-relation rel-type → MindsOS EdgeType name.
_SYNSET_REL_MAP: dict[str, str] = {
    "hypernym": EDGE_HYPERNYM_OF,
    "hyponym": EDGE_HYPONYM_OF,
    "instance_hypernym": EDGE_INSTANCE_HYPERNYM_OF,
    "instance_hyponym": EDGE_INSTANCE_HYPONYM_OF,
    "mero_part": EDGE_MERONYM_PART_OF,
    "mero_member": EDGE_MERONYM_MEMBER_OF,
    "mero_substance": EDGE_MERONYM_SUBSTANCE_OF,
    "holo_part": EDGE_HOLONYM_PART_OF,
    "holo_member": EDGE_HOLONYM_MEMBER_OF,
    "holo_substance": EDGE_HOLONYM_SUBSTANCE_OF,
    "similar": EDGE_SIMILAR_TO,
}

# OEWN sense-relation rel-type → MindsOS EdgeType name.
_SENSE_REL_MAP: dict[str, str] = {
    "antonym": EDGE_ANTONYM_OF,
    "derivation": EDGE_DERIVATIONALLY_RELATED_TO,
}


class OewnImporter:
    """Open English WordNet 2024 importer (Phase 15a).

    target_roles: ``("lexicon",)`` per PB-22.
    """

    target_roles: tuple[str, ...] = ("lexicon",)

    def __init__(
        self,
        source: Optional[Union[str, Path]] = None,
        *,
        version: str = "2024",
    ):
        """Construct an importer instance.

        Args:
            source: Path to an OEWN-LMF XML file (or the synthetic
                fixture). Optional at construction.
            version: Dataset version string. Default ``"2024"`` (the
                Phase 15a PB-6 pin for OEWN).
        """
        self.source = source
        self.version = version

    def run(
        self,
        mg: Metagraph,
        source: Optional[Union[str, Path]] = None,
    ) -> ImportResult:
        """Parse OEWN-LMF XML and write into the ``lexicon`` role-graph."""
        path = _resolve_source(source if source is not None else self.source)

        graph = ensure_global_role_graph(mg, "lexicon")

        parsed = _parse_oewn(path)
        stats = self._build(parsed, graph)

        return ImportResult(
            role="lexicon",
            version=self.version,
            source=SOURCE_NAME,
            imported_at=_utcnow(),
            stats=stats,
        )

    def _build(self, parsed: "_ParsedLexicon", graph: Any) -> dict[str, int]:
        stats: dict[str, int] = {
            "synsets": 0,
            "lemmas": 0,
            "senses": 0,
            "has_sense_edges": 0,
            "in_synset_edges": 0,
            "synset_relations": 0,
            "sense_relations": 0,
        }

        synset_by_id: dict[str, Any] = {}
        lemma_by_key: dict[tuple[str, str], Any] = {}
        sense_by_id: dict[str, Any] = {}

        # Synsets first (senses point at them).
        for syn_id, pos, definition in parsed.synsets:
            iri = oewn_synset_iri(self.version, syn_id, pos)
            n = graph.add_node(
                value=syn_id,
                type_name=NODE_SYNSET,
                node_id=iri,
                properties={
                    "pos": pos,
                    "definition": definition or "",
                    "imported_from": SOURCE_NAME,
                    "imported_version": self.version,
                },
            )
            synset_by_id[syn_id] = n
            stats["synsets"] += 1

        # Lemmas (deduped by (lemma, pos)).
        for lemma_text, pos in parsed.lemmas:
            key = (lemma_text, pos)
            if key in lemma_by_key:
                continue
            iri = oewn_lemma_iri(self.version, lemma_text, pos)
            n = graph.add_node(
                value=lemma_text,
                type_name=NODE_LEMMA,
                node_id=iri,
                properties={
                    "pos": pos,
                    "imported_from": SOURCE_NAME,
                    "imported_version": self.version,
                },
            )
            lemma_by_key[key] = n
            stats["lemmas"] += 1

        # Senses + HAS_SENSE + IN_SYNSET edges.
        for sense_id, lemma_text, pos, synset_id in parsed.senses:
            iri = oewn_sense_iri(self.version, sense_id)
            n = graph.add_node(
                value=sense_id,
                type_name=NODE_SENSE,
                node_id=iri,
                properties={
                    "lemma": lemma_text,
                    "pos": pos,
                    "imported_from": SOURCE_NAME,
                    "imported_version": self.version,
                },
            )
            sense_by_id[sense_id] = n
            stats["senses"] += 1

            lemma_node = lemma_by_key.get((lemma_text, pos))
            if lemma_node is not None:
                graph.add_edge(lemma_node, n, EDGE_HAS_SENSE)
                stats["has_sense_edges"] += 1

            synset_node = synset_by_id.get(synset_id)
            if synset_node is not None:
                graph.add_edge(n, synset_node, EDGE_IN_SYNSET)
                stats["in_synset_edges"] += 1

        # Synset relations.
        for src_id, tgt_id, rel_type in parsed.synset_relations:
            edge_type = _SYNSET_REL_MAP.get(rel_type)
            if edge_type is None:
                continue
            s = synset_by_id.get(src_id)
            t = synset_by_id.get(tgt_id)
            if s is None or t is None:
                continue
            graph.add_edge(s, t, edge_type)
            stats["synset_relations"] += 1

        # Sense relations.
        for src_id, tgt_id, rel_type in parsed.sense_relations:
            edge_type = _SENSE_REL_MAP.get(rel_type)
            if edge_type is None:
                continue
            s = sense_by_id.get(src_id)
            t = sense_by_id.get(tgt_id)
            if s is None or t is None:
                continue
            graph.add_edge(s, t, edge_type)
            stats["sense_relations"] += 1

        return stats


# ── Parsing ────────────────────────────────────────────────────────────


class _ParsedLexicon:
    """Parsed OEWN structure — pure Python (no L1 references)."""

    __slots__ = ("synsets", "lemmas", "senses", "synset_relations", "sense_relations")

    def __init__(self) -> None:
        # (synset_id, pos, definition)
        self.synsets: list[tuple[str, str, str]] = []
        # (lemma_text, pos)
        self.lemmas: list[tuple[str, str]] = []
        # (sense_id, lemma_text, pos, synset_id)
        self.senses: list[tuple[str, str, str, str]] = []
        # (src_synset_id, tgt_synset_id, rel_type)
        self.synset_relations: list[tuple[str, str, str]] = []
        # (src_sense_id, tgt_sense_id, rel_type)
        self.sense_relations: list[tuple[str, str, str]] = []


def _parse_oewn(path: Path) -> _ParsedLexicon:
    """Parse an OEWN-LMF XML file.

    OEWN-LMF schema (abbreviated):
      <LexicalResource>
        <Lexicon>
          <LexicalEntry id="...">
            <Lemma writtenForm="..." partOfSpeech="..."/>
            <Sense id="..." synset="..."/>
            <SenseRelation relType="..." target="..."/>
          </LexicalEntry>
          <Synset id="..." partOfSpeech="...">
            <Definition>...</Definition>
            <SynsetRelation relType="..." target="..."/>
          </Synset>
        </Lexicon>
      </LexicalResource>

    Parser uses lxml when available (faster on real OEWN, ~30 MB);
    falls back to stdlib :mod:`xml.etree.ElementTree` for environments
    without lxml.
    """
    parser_mod = _xml_parser_module()
    tree = parser_mod.parse(str(path))
    root = tree.getroot()

    parsed = _ParsedLexicon()

    # OEWN-LMF doesn't declare a namespace on its DTD-shaped XML;
    # support both bare tags and any default-ns prefix.
    def _iter_tag(node: Any, tag: str) -> Any:
        for el in node.iter():
            local = el.tag.rsplit("}", 1)[-1] if isinstance(el.tag, str) else el.tag
            if local == tag:
                yield el

    # Synsets.
    for syn in _iter_tag(root, "Synset"):
        syn_id = syn.get("id", "")
        pos = syn.get("partOfSpeech", "n")
        definition_text = ""
        for d in _iter_tag(syn, "Definition"):
            if d.text:
                definition_text = d.text.strip()
                break
        if syn_id:
            parsed.synsets.append((syn_id, pos, definition_text))

    # Synset relations (separate pass — lxml iter() over the same root
    # is cheap; ensures we've registered synsets first).
    for syn in _iter_tag(root, "Synset"):
        syn_id = syn.get("id", "")
        for rel in _iter_tag(syn, "SynsetRelation"):
            target = rel.get("target", "")
            rel_type = rel.get("relType", "")
            if syn_id and target and rel_type:
                parsed.synset_relations.append((syn_id, target, rel_type))

    # Lexical entries → Lemma + Sense + SenseRelations.
    for entry in _iter_tag(root, "LexicalEntry"):
        lemma_text = ""
        pos = "n"
        for lemma_el in _iter_tag(entry, "Lemma"):
            lemma_text = lemma_el.get("writtenForm", "")
            pos = lemma_el.get("partOfSpeech", "n")
            break
        if lemma_text:
            parsed.lemmas.append((lemma_text, pos))

        for sense_el in _iter_tag(entry, "Sense"):
            sense_id = sense_el.get("id", "")
            synset_id = sense_el.get("synset", "")
            if sense_id and synset_id and lemma_text:
                parsed.senses.append((sense_id, lemma_text, pos, synset_id))

                for srel in _iter_tag(sense_el, "SenseRelation"):
                    target = srel.get("target", "")
                    rel_type = srel.get("relType", "")
                    if target and rel_type:
                        parsed.sense_relations.append((sense_id, target, rel_type))

    return parsed


def _xml_parser_module() -> Any:
    """Return :mod:`lxml.etree` if installed, else :mod:`xml.etree.ElementTree`."""
    try:
        from lxml import etree  # type: ignore[import-not-found]
        return etree
    except ImportError:
        import xml.etree.ElementTree as etree  # type: ignore[no-redef]
        return etree
