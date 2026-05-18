---
last_confirmed_phase: 13
---

# Ontology role schema

DOLCE + full-OWL ontology vocabulary. **10 NodeTypes, 13 EdgeTypes,
7 HyperEdgeTypes** at `strict=False`.

Phase 13 PB-4 lifts the 7 hyperedge "label" constants from v3 (which
predated Phase 04-v2's `HyperEdgeType`) into proper `HyperEdgeType`
registrations on the Schema.

## NodeTypes

`Class`, `Individual`, `ObjectProperty`, `DataProperty`,
`AnnotationProperty`, `Restriction`, `ClassExpression`, `Datatype`,
`DatatypeRestriction`, `Axiom`.

## EdgeTypes

`SUBCLASS_OF`, `DISJOINT_WITH`, `EQUIVALENT_TO`, `TYPE_OF`, `DOMAIN`,
`RANGE`, `INVERSE_OF`, `SUBPROPERTY_OF`, `SAME_AS`, `DIFFERENT_FROM`,
`RESTRICTS_PROPERTY`, `HAS_FILLER`, `ON_DATATYPE`.

## HyperEdgeTypes

`INTERSECTION_OF`, `UNION_OF`, `ONE_OF`, `PROPERTY_CHAIN`,
`DISJOINT_UNION_OF`, `ALL_DISJOINT_CLASSES`, `ALL_DIFFERENT`.

**Ordering note.** Phase 04-v2's `HyperEdgeType` is symmetric across
members; the ordering claim for `PROPERTY_CHAIN` lives at the
**instance** level (`HyperEdge.members` is a list preserving insertion
order). Importers (Phase 15) own ordering discipline.

## Strict-tighten status

`strict=False` (ADR-0149). OWL property surface is open — tightening
deferred until the inventory helper observes which property keys
importers actually write.

## Where it's used

Phase 15 (OWL/DOLCE importer) is the first content consumer.
Phase 14 (KL bootstrap) calls `ensure_role_graph(global_mg, "ontology")`.
