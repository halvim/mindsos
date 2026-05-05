# Phase 10 audit — what's in scope after pin reverts

> **⚠️ PARTIALLY SUPERSEDED 2026-05-05.** The "Side finding" section about Phase 05 row + Round-3 #3 (single Phase 05 vs 05a/05b/05c split) is now obsolete. The Phase 05a row-refinement chat (2026-05-05) **kept the 05a/05b/05c split** AND further decided:
>
> - `CompositionalMetaEdge` is **dropped** (not deferred to 05c). The compositional concept moves to a flag on intergraph primitives.
> - Phase 05 splits into 05a (port; ships in 05a) + 05b (binary `IntergraphEdge` + `MetagraphSchema` + 4 *EdgeTypes + ADR-0148 first draft + ADR-0117 Withdrawn) + 05c (n-ary `IntergraphHyperEdge` + `IntergraphHyperEdgeType` + ADR-0148 amended).
> - This audit's recommendation ("revert round-3 #3") is **rejected** in favor of the new 3-way split.
>
> The Phase 10 ADR-scope verdict (six ADRs: 0027 / 0028 / 0129 / 0130 / 0133 / 0135) is **partially correct** — but ADR-0130 has now landed in Phase 05a (Metagraph property bag); only `Graph.properties` deferral remains for Phase 10. ADR-0130 row in §6 of PHASE_MAP reflects this.
>
> Canonical sources: `halvim_mindsos/confirmation_docs/PHASE_MAP.md` Phase 05a row + `INTERGRAPH_EDGES_DESIGN.md`.

---

**Date:** 2026-05-04 (original); 2026-05-05 supersession header added.
**Audit context:** Round-6 pushback #37 ("if bag pulled forward, what's left in Phase 10?"). With #28 and #20 reverted (soft-delete audit verdict), this audit also confirms what was authored in Phase 10 originally.

## Phase 10 row (verbatim from slim PHASE_MAP)

> Phase 10 — L1 Snapshot + soft-delete + RemovalImpact
> **Deps:** 07, 08. **Layer:** L1. **Net-new?** Soft-delete partial (ADR-0133 properties exist; full enforcement may be NEW CODE).
> **Features:** snapshot take + restore (in-process only per ADR-0028); deprecate / dispute element with reason; removal-impact report.
> **Risks:** soft-delete read-path enforcement scope is an open question (§7).
> **Docs:** `docs/usage/core/snapshots.md`, ADRs 0027/0028/0129/**0130**/0133/0135.

## Verdict on round-6 #37

**False premise.** #37 framed Phase 10 as "centered on the bag" and asked what's left if bag is pulled forward. Reality: Phase 10 is a **multi-ADR sweep** owning **six ADRs** (0027 / 0028 / 0129 / **0130** / 0133 / 0135). Bag is one of six.

If #28 had stuck (bag → 05a), Phase 10 would still have:
- ADR-0027 / 0028 — `MetagraphSnapshot.restore_into` (in-process)
- ADR-0129 — `MetagraphSnapshot` narrowed to release-ship
- ADR-0133 — soft-delete substrate (properties + enforcement)
- ADR-0135 — `RemovalImpact` on `remove_graph`

These five would NOT be empty without ADR-0130. #37's "Phase 10 might be empty after pulling bag" was wrong.

## Verdict with #28 + #20 reverted

Phase 10 retains its **authored six-ADR scope.** No re-scoping needed. No "rollback discipline" repurposing required (#37 option B is moot).

## Side finding worth surfacing — Phase 05 row contradicts round-3 #3

Slim PHASE_MAP §Phase 05 features (line 667):

> Metagraph CRUD; place a Graph inside a Metagraph; binary MetaEdge; n-ary MetaHyperEdge; **CompositionalMetaEdge unwrap.**

**The slim author bundles CompositionalMetaEdge with the rest in Phase 05.** Round-3 #3 split CompositionalMetaEdge out into 05c on the framing "most semantically rich element in L1." Per the M8 audit, CompositionalMetaEdge is actually a **thin subclass of MetaEdge with zero new data fields** — just an immutability marker via `isinstance` check. Round-3's "semantically rich" framing was incorrect.

Slim author also pre-scoped Q13 (IntergraphEdge) as a Phase 05 feature increment if greenlit (line 668: *"scope a feature increment to Phases 05 (primitive), 07 (persistence), 10 (snapshot scope), 11 (Cypher builders)"*).

This means the slim author's Phase 05 intent is:
- Metagraph
- MetaEdge
- MetaHyperEdge
- CompositionalMetaEdge unwrap
- IntergraphEdge primitive (if Q13 greenlit)
- IntergraphEdge persistence/snapshot/cypher distributed across Phases 07/10/11

That's a single bundled Phase 05, not the 05a/05b/05c split from round 3.

## Recommendation

Revert round-3 #3 (split into 05a/b/c) at minimum to recombine 05a+05c (CompositionalMetaEdge bundled with the rest). IntergraphEdge as a separate sub-phase remains defensible because its design surface (4 pins + IntergraphSchema) is genuinely new beyond what slim author planned.

Decision to surface to user: revert #3 fully (single Phase 05) OR partial (05a + 05b for IntergraphEdge only)?

## Outcome

Phase 10 audit: **scope unchanged from slim PHASE_MAP author.** Six ADRs (0027 / 0028 / 0129 / 0130 / 0133 / 0135) all stay in Phase 10. Round-6 #37 is closed by this audit (false premise; no repurposing needed).

Round-3 #3 needs re-decision based on this finding.
