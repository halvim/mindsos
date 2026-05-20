---
last_confirmed_phase: 15a
---

# DOLCE-DUL ontology source

Phase 15a's `DolceImporter` reads the **DOLCE Ultra-Light (DUL) 4.1**
upper ontology distribution and writes it into the `ontology` Global
role-graph per [ADR-0150](../decisions/adr/0150-l2-knowledge-lifecycle.md).

## Pin

* **Version:** DOLCE-DUL 4.1 (Phase 15a PB-6 lock).
* **Source URL:** http://www.ontologydesignpatterns.org/ont/dul/DUL.owl
* **License:** Creative Commons — repo-shippable, no click-through.
* **Format:** RDF/XML (OWL). Parser: `rdflib`.

## Download

```sh
scripts/fetch_datasets.sh dolce
# or:
python scripts/fetch_datasets.py dolce
```

Real dataset lands at `data/datasets/dolce-dul-4.1.owl` (gitignored).
Synthetic test fixture at `tests/phase_15a/fixtures/dolce_synth.owl`.

## Import command

```sh
mindsos admin import dolce \
    --source data/datasets/dolce-dul-4.1.owl \
    --version 4.1 \
    --json
```

## Expected stats

The importer reports a `stats` dict in `ImportResult`. Key counts:

| Key | What it counts |
|---|---|
| `classes` | `owl:Class` declarations |
| `individuals` | `owl:NamedIndividual` declarations |
| `object_properties` | `owl:ObjectProperty` declarations |
| `data_properties` | `owl:DatatypeProperty` declarations |
| `annotation_properties` | `owl:AnnotationProperty` declarations |
| `restrictions` | `owl:Restriction` blank nodes promoted to `Restriction` nodes |
| `datatypes` | `rdfs:Datatype` declarations |
| `subclass_of_edges` | `rdfs:subClassOf` |
| `subproperty_of_edges` | `rdfs:subPropertyOf` |
| `domain_edges` | `rdfs:domain` |
| `range_edges` | `rdfs:range` |
| `disjoint_edges` | `owl:disjointWith` |
| `equivalent_edges` | `owl:equivalentClass` + `owl:equivalentProperty` |
| `intersection_hyperedges` | `owl:intersectionOf` (head + operands) |
| `property_chain_hyperedges` | `owl:propertyChainAxiom` (ordered chain) |
| `all_disjoint_classes_hyperedges` | `owl:AllDisjointClasses` (member set) |

IRIs minted via `mindsos_knowledge.identifiers.dolce_iri(version, fragment)`
per [ADR-0045](../decisions/adr/0045-per-role-iri-builders.md).

## Why the `ontology` role-graph

Per [ADR-0150](../decisions/adr/0150-l2-knowledge-lifecycle.md)'s
closed-role-set lock: DOLCE-DUL is the canonical upper ontology;
upper-layer roles (`promoted-pipelines`, `task-patterns`,
`problem-trace`) reference ontology classes via XRefs per
[ADR-0128](../decisions/adr/0128-hybrid-xref-cross-metagraph-refs.md).
