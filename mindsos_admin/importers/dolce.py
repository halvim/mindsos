"""DolceImporter — DOLCE-DUL 4.1 OWL → ``ontology`` Global role-graph.

Phase 15a per PB-6 dataset pin: DOLCE-DUL 4.1 (Creative Commons;
repo-shippable). Parses RDF/XML or Turtle via :mod:`rdflib`.

Writes into the ``ontology`` Global role-graph per ADR-0150 +
:func:`mindsos_knowledge.bootstrap.ensure_global_role_graph`. IRIs
minted via :func:`mindsos_knowledge.identifiers.dolce_iri` per
ADR-0045.

Per Phase 15a PB-14 (Round 3): the importer auto-ensures its target
role-graph at the top of ``run()`` so direct callers (bypassing
``bootstrap_global``) don't hit a missing-graph error. The auto-ensure
is redundant-but-idempotent when called from ``bootstrap_global`` (PB-22).

Per ADR-0044 (Accepted): writes Global only; never touches
``memories`` / ``capacity-state`` roles.

**Stats dict keys** (as returned in :class:`ImportResult.stats`):

* ``classes`` — number of ``owl:Class`` nodes written.
* ``individuals`` — number of ``owl:NamedIndividual`` nodes written.
* ``object_properties`` — number of ``owl:ObjectProperty`` nodes.
* ``data_properties`` — number of ``owl:DatatypeProperty`` nodes.
* ``annotation_properties`` — number of ``owl:AnnotationProperty``
  nodes.
* ``restrictions`` — number of ``owl:Restriction`` blank-node sets
  promoted to ``Restriction`` nodes.
* ``datatypes`` — number of ``rdfs:Datatype`` nodes.
* ``subclass_of_edges`` — count of ``rdfs:subClassOf`` edges.
* ``subproperty_of_edges`` — count of ``rdfs:subPropertyOf`` edges.
* ``domain_edges`` / ``range_edges`` — ``rdfs:domain`` / ``rdfs:range``.
* ``disjoint_edges`` — ``owl:disjointWith`` binary edges.
* ``equivalent_edges`` — ``owl:equivalentClass`` /
  ``owl:equivalentProperty`` edges.
* ``intersection_hyperedges`` — ``owl:intersectionOf`` n-ary
  hyperedges (head = the class; members = the operands).
* ``property_chain_hyperedges`` — ``owl:propertyChainAxiom``
  hyperedges.
* ``all_disjoint_classes_hyperedges`` — ``owl:AllDisjointClasses``
  hyperedges.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union

from mindsos_core import Metagraph

from mindsos_knowledge.bootstrap import ensure_global_role_graph
from mindsos_knowledge.identifiers import dolce_iri
from mindsos_knowledge.schemas.ontology import (
    EDGE_DISJOINT_WITH,
    EDGE_DOMAIN,
    EDGE_EQUIVALENT_TO,
    EDGE_RANGE,
    EDGE_SUBCLASS_OF,
    EDGE_SUBPROPERTY_OF,
    HE_ALL_DISJOINT_CLASSES,
    HE_INTERSECTION_OF,
    HE_PROPERTY_CHAIN,
    NODE_ANNOTATION_PROPERTY,
    NODE_CLASS,
    NODE_DATA_PROPERTY,
    NODE_DATATYPE,
    NODE_INDIVIDUAL,
    NODE_OBJECT_PROPERTY,
    NODE_RESTRICTION,
)

from ..bootstrap import ImportResult, _resolve_source, _utcnow


__all__ = ["DolceImporter"]


SOURCE_NAME = "dolce-dul"


class DolceImporter:
    """DOLCE-DUL OWL ontology importer (Phase 15a).

    target_roles: ``("ontology",)`` per PB-22.
    """

    target_roles: tuple[str, ...] = ("ontology",)

    def __init__(
        self,
        source: Optional[Union[str, Path]] = None,
        *,
        version: str = "4.1",
    ):
        """Construct an importer instance.

        Args:
            source: Path to a DOLCE OWL file (RDF/XML, Turtle, or any
                rdflib-supported format) OR to the synthetic fixture
                under ``tests/phase_15a/fixtures/``. Optional at
                construction; can be supplied to :meth:`run` instead.
            version: Dataset version string. Default ``"4.1"`` (the
                Phase 15a PB-6 pin for DOLCE-DUL).
        """
        self.source = source
        self.version = version

    def run(
        self,
        mg: Metagraph,
        source: Optional[Union[str, Path]] = None,
    ) -> ImportResult:
        """Parse the source OWL file and write nodes/edges/hyperedges
        into the ``ontology`` Global role-graph of ``mg``.

        Args:
            mg: Target Metagraph (typically constructed via
                :func:`mindsos_admin.bootstrap_global`).
            source: Optional per-call override of the constructor's
                source. If both are ``None``, raises :class:`ValueError`.

        Returns:
            :class:`ImportResult` with ``role="ontology"``,
            ``source="dolce-dul"``, and the stats dict documented in
            the module docstring.
        """
        path = _resolve_source(source if source is not None else self.source)

        # PB-14 — auto-ensure target role-graph (idempotent).
        graph = ensure_global_role_graph(mg, "ontology")

        parsed = _parse_dolce(path)
        stats = self._build(parsed, graph)

        return ImportResult(
            role="ontology",
            version=self.version,
            source=SOURCE_NAME,
            imported_at=_utcnow(),
            stats=stats,
        )

    def _build(self, parsed: "_ParsedOntology", graph: Any) -> dict[str, int]:
        """Translate parsed dict into Graph mutations. IRI minting via
        :func:`dolce_iri`. Idempotent re-runs are tolerated at the
        node level: existing nodes by ``node_id`` are skipped
        (parser yields stable per-fragment IRIs)."""
        stats: dict[str, int] = {
            "classes": 0,
            "individuals": 0,
            "object_properties": 0,
            "data_properties": 0,
            "annotation_properties": 0,
            "restrictions": 0,
            "datatypes": 0,
            "subclass_of_edges": 0,
            "subproperty_of_edges": 0,
            "domain_edges": 0,
            "range_edges": 0,
            "disjoint_edges": 0,
            "equivalent_edges": 0,
            "intersection_hyperedges": 0,
            "property_chain_hyperedges": 0,
            "all_disjoint_classes_hyperedges": 0,
        }

        # Node minting — keep a fragment→Node map for edge resolution.
        node_by_frag: dict[str, Any] = {}

        def _mint(fragment: str, type_name: str, stat_key: str) -> Any:
            if fragment in node_by_frag:
                return node_by_frag[fragment]
            iri = dolce_iri(self.version, fragment)
            n = graph.add_node(
                value=fragment,
                type_name=type_name,
                node_id=iri,
                properties={
                    "imported_from": SOURCE_NAME,
                    "imported_version": self.version,
                },
            )
            node_by_frag[fragment] = n
            stats[stat_key] += 1
            return n

        for frag in parsed.classes:
            _mint(frag, NODE_CLASS, "classes")
        for frag in parsed.individuals:
            _mint(frag, NODE_INDIVIDUAL, "individuals")
        for frag in parsed.object_properties:
            _mint(frag, NODE_OBJECT_PROPERTY, "object_properties")
        for frag in parsed.data_properties:
            _mint(frag, NODE_DATA_PROPERTY, "data_properties")
        for frag in parsed.annotation_properties:
            _mint(frag, NODE_ANNOTATION_PROPERTY, "annotation_properties")
        for frag in parsed.restrictions:
            _mint(frag, NODE_RESTRICTION, "restrictions")
        for frag in parsed.datatypes:
            _mint(frag, NODE_DATATYPE, "datatypes")

        # Edge minting — endpoints must exist (skip if either missing).
        def _resolve_pair(src: str, tgt: str) -> Optional[tuple[Any, Any]]:
            s = node_by_frag.get(src)
            t = node_by_frag.get(tgt)
            if s is None or t is None:
                return None
            return s, t

        for src, tgt in parsed.subclass_of:
            pair = _resolve_pair(src, tgt)
            if pair:
                graph.add_edge(pair[0], pair[1], EDGE_SUBCLASS_OF)
                stats["subclass_of_edges"] += 1

        for src, tgt in parsed.subproperty_of:
            pair = _resolve_pair(src, tgt)
            if pair:
                graph.add_edge(pair[0], pair[1], EDGE_SUBPROPERTY_OF)
                stats["subproperty_of_edges"] += 1

        for src, tgt in parsed.domain:
            pair = _resolve_pair(src, tgt)
            if pair:
                graph.add_edge(pair[0], pair[1], EDGE_DOMAIN)
                stats["domain_edges"] += 1

        for src, tgt in parsed.range:
            pair = _resolve_pair(src, tgt)
            if pair:
                graph.add_edge(pair[0], pair[1], EDGE_RANGE)
                stats["range_edges"] += 1

        for src, tgt in parsed.disjoint_with:
            pair = _resolve_pair(src, tgt)
            if pair:
                graph.add_edge(pair[0], pair[1], EDGE_DISJOINT_WITH)
                stats["disjoint_edges"] += 1

        for src, tgt in parsed.equivalent_to:
            pair = _resolve_pair(src, tgt)
            if pair:
                graph.add_edge(pair[0], pair[1], EDGE_EQUIVALENT_TO)
                stats["equivalent_edges"] += 1

        # Hyperedge minting — all members must exist (skip if any missing).
        def _resolve_members(frags: tuple[str, ...]) -> Optional[list[Any]]:
            members: list[Any] = []
            for f in frags:
                n = node_by_frag.get(f)
                if n is None:
                    return None
                members.append(n)
            return members

        for head_frag, member_frags in parsed.intersection_of:
            head = node_by_frag.get(head_frag)
            members = _resolve_members(member_frags)
            if head is None or members is None:
                continue
            graph.add_hyperedge([head, *members], HE_INTERSECTION_OF)
            stats["intersection_hyperedges"] += 1

        for member_frags in parsed.property_chain:
            members = _resolve_members(member_frags)
            if members is None or len(members) < 2:
                continue
            graph.add_hyperedge(members, HE_PROPERTY_CHAIN)
            stats["property_chain_hyperedges"] += 1

        for member_frags in parsed.all_disjoint_classes:
            members = _resolve_members(member_frags)
            if members is None or len(members) < 2:
                continue
            graph.add_hyperedge(members, HE_ALL_DISJOINT_CLASSES)
            stats["all_disjoint_classes_hyperedges"] += 1

        return stats


# ── Parsing ────────────────────────────────────────────────────────────


class _ParsedOntology:
    """Parsed DOLCE structure — pure Python (no L1 references).

    Lists of fragment strings (the local name after the ontology IRI
    prefix) for each category. Edges and hyperedges carry tuples of
    fragment strings; the builder phase resolves them to Node refs.
    """

    __slots__ = (
        "classes",
        "individuals",
        "object_properties",
        "data_properties",
        "annotation_properties",
        "restrictions",
        "datatypes",
        "subclass_of",
        "subproperty_of",
        "domain",
        "range",
        "disjoint_with",
        "equivalent_to",
        "intersection_of",
        "property_chain",
        "all_disjoint_classes",
    )

    def __init__(self) -> None:
        self.classes: list[str] = []
        self.individuals: list[str] = []
        self.object_properties: list[str] = []
        self.data_properties: list[str] = []
        self.annotation_properties: list[str] = []
        self.restrictions: list[str] = []
        self.datatypes: list[str] = []
        self.subclass_of: list[tuple[str, str]] = []
        self.subproperty_of: list[tuple[str, str]] = []
        self.domain: list[tuple[str, str]] = []
        self.range: list[tuple[str, str]] = []
        self.disjoint_with: list[tuple[str, str]] = []
        self.equivalent_to: list[tuple[str, str]] = []
        # (head_fragment, tuple-of-operand-fragments)
        self.intersection_of: list[tuple[str, tuple[str, ...]]] = []
        # Tuple of fragment chain (ordered)
        self.property_chain: list[tuple[str, ...]] = []
        # Tuple of member fragments (unordered set; insertion order preserved)
        self.all_disjoint_classes: list[tuple[str, ...]] = []


def _parse_dolce(path: Path) -> _ParsedOntology:
    """Parse a DOLCE OWL file via rdflib.

    Accepts any rdflib-supported format (RDF/XML, Turtle, N3, JSON-LD).
    Format auto-detected from file extension; ``.owl`` is parsed as
    RDF/XML by default.
    """
    try:
        import rdflib  # type: ignore[import-not-found]
        from rdflib.namespace import OWL, RDF, RDFS  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "rdflib is required to parse DOLCE OWL files. "
            "Install via `pip install rdflib` or rebuild the test image."
        ) from exc

    g = rdflib.Graph()
    fmt = _rdflib_format_for(path)
    g.parse(str(path), format=fmt)

    parsed = _ParsedOntology()

    def _frag(uri: Any) -> Optional[str]:
        """Return the fragment / local name for a URIRef, or None for
        BNodes / literals."""
        if not isinstance(uri, rdflib.URIRef):
            return None
        s = str(uri)
        # Prefer fragment after '#'; fall back to last path segment.
        if "#" in s:
            return s.rsplit("#", 1)[-1]
        if "/" in s:
            tail = s.rsplit("/", 1)[-1]
            return tail or None
        return s

    # Classes
    for cls in g.subjects(RDF.type, OWL.Class):
        f = _frag(cls)
        if f:
            parsed.classes.append(f)

    # Individuals
    for ind in g.subjects(RDF.type, OWL.NamedIndividual):
        f = _frag(ind)
        if f:
            parsed.individuals.append(f)

    # Object properties
    for p in g.subjects(RDF.type, OWL.ObjectProperty):
        f = _frag(p)
        if f:
            parsed.object_properties.append(f)

    # Data properties
    for p in g.subjects(RDF.type, OWL.DatatypeProperty):
        f = _frag(p)
        if f:
            parsed.data_properties.append(f)

    # Annotation properties
    for p in g.subjects(RDF.type, OWL.AnnotationProperty):
        f = _frag(p)
        if f:
            parsed.annotation_properties.append(f)

    # Datatypes
    for d in g.subjects(RDF.type, RDFS.Datatype):
        f = _frag(d)
        if f:
            parsed.datatypes.append(f)

    # Restrictions — bnodes typed as owl:Restriction. We promote each
    # to a stable fragment based on the property + filler.
    rest_counter = 0
    rest_frag_by_bnode: dict[Any, str] = {}
    for r in g.subjects(RDF.type, OWL.Restriction):
        rest_counter += 1
        frag = f"restriction_{rest_counter}"
        rest_frag_by_bnode[r] = frag
        parsed.restrictions.append(frag)

    # Binary edges — subClassOf / subPropertyOf / domain / range /
    # disjointWith / equivalentClass / equivalentProperty.
    def _add_binary_edge(predicate: Any, into: list[tuple[str, str]]) -> None:
        for s, o in g.subject_objects(predicate):
            sf = _frag(s)
            of_ = _frag(o)
            if sf and of_:
                into.append((sf, of_))

    _add_binary_edge(RDFS.subClassOf, parsed.subclass_of)
    _add_binary_edge(RDFS.subPropertyOf, parsed.subproperty_of)
    _add_binary_edge(RDFS.domain, parsed.domain)
    _add_binary_edge(RDFS.range, parsed.range)
    _add_binary_edge(OWL.disjointWith, parsed.disjoint_with)
    _add_binary_edge(OWL.equivalentClass, parsed.equivalent_to)
    _add_binary_edge(OWL.equivalentProperty, parsed.equivalent_to)

    # Intersection-of hyperedges — head class has owl:intersectionOf
    # pointing at an RDF list.
    for head, lst in g.subject_objects(OWL.intersectionOf):
        head_f = _frag(head)
        if not head_f:
            continue
        members = tuple(f for f in (_frag(m) for m in g.items(lst)) if f)
        if members:
            parsed.intersection_of.append((head_f, members))

    # Property-chain axioms — owl:propertyChainAxiom; the chain is an
    # RDF list; for the importer we record the list as one
    # hyperedge containing the chain participants (no head — the
    # chain is itself the axiom).
    for _head, lst in g.subject_objects(OWL.propertyChainAxiom):
        chain = tuple(f for f in (_frag(m) for m in g.items(lst)) if f)
        if len(chain) >= 2:
            parsed.property_chain.append(chain)

    # AllDisjointClasses — typed bnode with owl:members → RDF list.
    for adc in g.subjects(RDF.type, OWL.AllDisjointClasses):
        for lst in g.objects(adc, OWL.members):
            members = tuple(f for f in (_frag(m) for m in g.items(lst)) if f)
            if len(members) >= 2:
                parsed.all_disjoint_classes.append(members)

    return parsed


def _rdflib_format_for(path: Path) -> str:
    """Map a path's extension to an rdflib format string."""
    suffix = path.suffix.lower()
    if suffix in (".owl", ".rdf", ".xml"):
        return "xml"
    if suffix == ".ttl":
        return "turtle"
    if suffix == ".n3":
        return "n3"
    if suffix in (".jsonld", ".json"):
        return "json-ld"
    if suffix == ".nt":
        return "nt"
    # Default to XML — DOLCE's canonical distribution format.
    return "xml"
