---
last_confirmed_phase: 13
---

# Alignment role schema

Cross-role mapping graphs use the **shared-anchor pattern**.
**1 NodeType, 8 EdgeTypes (open), 0 HyperEdgeTypes** at `strict=False`.

## NodeType

`AlignmentAnchor` — carries a `ref:<role>` property pointing at the
aligned entity on each side. **Shared-anchor rule:** if the same
entity participates in N mappings, ONE anchor node serves all N.

## EdgeTypes (open vocabulary)

Starter set: `LEXICALIZES`, `EXACT_MATCH`, `CLOSE_MATCH`,
`NARROWER_THAN`, `BROADER_THAN`, `EVOKES`, `INSTANCE_OF_CLASS`,
`RELATED_TO`.

Callers extend via the `extra_edge_types` kwarg per Phase 13 PB-14:

```python
schema = build_alignment_schema(extra_edge_types=("CUSTOM_MAP",))
```

## Parametric

The same builder serves all role-pair alignment graphs:
`alignment:concepts:lexicon`, `alignment:lexicon:ontology`, etc.
The graph *name* (per `alignment_role(a, b)`) differs per pair; the
*schema* is identical. `alignment_role` sorts the two roles and joins
them with a `:` separator (ADR-0154), so `alignment_role("lexicon",
"concepts")` and `alignment_role("concepts", "lexicon")` both return
`alignment:concepts:lexicon`.

## Anchor IRI minting

Phase 13 deliberately does **NOT** mint anchor IRIs — that decision is
deferred to Phase 14 (KL bootstrap) per Phase 13 PB-5. Two candidate
patterns are documented in the design log:

- (b.i) Anchor reuses the referenced entity's IRI directly.
- (b.ii) Anchor mints a wrapper IRI (e.g.,
  `alignment:concepts:lexicon:anchor:<source_iri>`).

Phase 14 picks per consumer need.

## Strict-tighten status

`strict=False` (ADR-0149). The alignment vocabulary is intentionally
open (the `extra_edge_types` kwarg is the reason).
