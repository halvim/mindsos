# M8 / ADR-0117 audit — does CompositionalMetaEdge need the ADR-0130 property bag?

> **⚠️ SUPERSEDED 2026-05-05.** This audit assumed `CompositionalMetaEdge` would ship in Phase 05c per HANDOFF L1 §12.10. The Phase 05a row-refinement chat (2026-05-05) **dropped `CompositionalMetaEdge` entirely.** ADR-0117 will be **Withdrawn in Phase 05b** (was: Reserved). The compositional concept moved to a `compositional: bool` flag on the new `IntergraphEdge` / `IntergraphHyperEdge` primitives.
>
> The audit's verdict ("composition does NOT need ADR-0130") remains correct as a property-bag design point, but the framing — that composition lives at the graph level — is now obsolete. The current canonical design is:
>
> **`halvim_mindsos/confirmation_docs/INTERGRAPH_EDGES_DESIGN.md`** — covers `IntergraphEdge` (Phase 05b) + `IntergraphHyperEdge` (Phase 05c), both carrying `compositional: bool` flag with the same `CompositionalImmutableError` semantic, but at the node level (correct for cat=c+a+t).
>
> Future chats: read INTERGRAPH_EDGES_DESIGN.md for compositional design. This audit note is preserved for the property-bag-doesn't-need-composition-rules verdict only.

---

**Date:** 2026-05-04 (original); 2026-05-05 supersession header added.
**Audit context:** Pre-Phase-05a gating decision (round-6 pushback #29 / #41).
**Sources read:**

- `mindsos_core/models/metagraph.py` lines 57–118 (MetaEdge + CompositionalMetaEdge subclass).
- `docs/HANDOFF_L1_REDESIGN_2026-04-27.md` §M8.
- `docs/decisions/adr/0130-property-bag-on-metagraph-graph.md` §Decision.

## Verdict

**NO — composition does NOT need ADR-0130's property bag.**

## Evidence

1. `CompositionalMetaEdge(MetaEdge)` inherits MetaEdge's fields verbatim. It declares **zero new fields**. (`mindsos_core/models/metagraph.py:93–118`.)
2. The composition semantic is encoded as **class identity** — `isinstance(me, CompositionalMetaEdge)` is the marker. The only behavior override is `.deprecate()` raising `CompositionalImmutableError`.
3. The class docstring (lines 95–112) is explicit: *"Composition is identity… The class identity (isinstance check) is the immutability marker."* No rule-data is stored.
4. ADR-0130 scopes the bag to `Metagraph` and `Graph` ONLY. MetaEdge already has its own `properties: Dict[str, Any]` field (line 70) — independent of ADR-0130 — and CompositionalMetaEdge inherits it. If composition metadata were ever wanted, that pre-existing field is the home; ADR-0130 doesn't enter.

## Implications

- **05a property-bag work can proceed in its straightforward form.** Bag schema does NOT need to accommodate composition rules.
- **Round-6 pushback #45** (composition vocabulary unspecified) is closed: composition vocabulary is "class-identity is the rule." Immutability is the only behavior. No vocabulary to pin.
- **05c CompositionalMetaEdge work** remains scoped to: factory wiring (`Metagraph.add_compositional_metaedge(...)`), loader discrimination (stamped `_compositional` property reconstruction), invariant enforcement (`remove_metaedge` raises on the subclass). All of this is described in HANDOFF_L1_REDESIGN §12.10 and is independent of ADR-0130.

## Side-finding (not part of audit but surfaces here)

**Soft-delete is already implemented in code.** `MetaEdge.deprecated_at` / `disputed_at` exist at line 72–73; `MetaHyperEdge` carries the same at lines 134–135. Round-5 pushback #20 ("promote soft-delete machinery to 05a") was framed as if soft-delete needed to be BUILT in 05a. Reality: the data fields and ADR-0133 representation already exist in `mindsos_core/models/metagraph.py`. 05a scope reduces from "build soft-delete substrate" to "verify existing fields are exercised by Phase 05a CLI/persistence/tests."

## Outcome

Audit verdict closed. 05a row refinement is unblocked. Properties bag (ADR-0130) and CompositionalMetaEdge (M8/ADR-0117 reserved) are orthogonal.
