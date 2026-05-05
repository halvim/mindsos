# ADR-0133 soft-delete feature-completeness audit

**Date:** 2026-05-04
**Audit context:** Re-scope decision for round-5 pushback #20 ("promote soft-delete machinery to 05a").
**Audit scope:** Both repos — full project-root `mindsos_core/` AND slim release-target `halvim_mindsos/mindsos_core/`.

## Headline

The full repo and the slim repo diverge significantly. **Round-6 pin #20 (and adjacent #28) was reasoned against the full repo, not the slim release target.** The slim repo's source code explicitly defers soft-delete and the Graph property bag to **Phase 10** (not Phase 05/05a).

## Full repo (`mindsos_core/`) — soft-delete IS implemented

✅ **Data fields** — `deprecated_at` / `disputed_at` on Edge (`models/edge.py:45-46`), HyperEdge (`models/edge.py:81-82`), MetaEdge (`models/metagraph.py:72-73`), MetaHyperEdge (`models/metagraph.py:134-135`), XRef (`models/xref.py:57`).
✅ **Iterators with filter** — Graph.iter_edges/iter_hyperedges/get_edges_for_node, Metagraph.iter_metaedges/iter_metahyperedges/iter_xrefs all carry `include_deprecated=False`.
✅ **Mutation API** — Graph.{deprecate,undeprecate,dispute,undispute}_edge — full quartet for Edge.
✅ **Cypher builders** — `mindsos_core/cypher/builders.py:405,420,434` handle deprecated_at parameter.
✅ **CompositionalMetaEdge subclass** — `.deprecate()` raises CompositionalImmutableError (`metagraph.py:114`).
✅ **XRef persistence** — `xref_repository.py:38`, `xref_loader.py:25,56,65–81`.

❌ **Gaps in the full repo:**

1. **HyperEdge has NO mutation API.** Graph has no `deprecate_hyperedge` / `undeprecate_hyperedge` / `dispute_hyperedge` / `undispute_hyperedge`. Data fields exist but no method to mutate them.
2. **API inconsistency between Graph and Metagraph.** Graph uses 4-method quartet (deprecate/undeprecate/dispute/undispute); Metagraph uses single `deprecate_metaedge(at=None)` overload. Different surfaces for the same semantic.
3. **Metagraph has no `dispute_metaedge` / `dispute_metahyperedge`.** Only the deprecate path exists.
4. **CompositionalMetaEdge bypass bug.** `Metagraph.deprecate_metaedge` directly assigns `me.deprecated_at = at` (line 428) without `isinstance(me, CompositionalMetaEdge)` check. The subclass's `.deprecate()` method raises CompositionalImmutableError, BUT the metagraph method bypasses that path entirely. **Real correctness defect.**
5. **GraphLoader.load() has no `include_deprecated` parameter.** ADR-0133 §"Loader behavior" mandates Cypher-level filtering. Current signature: `load(graph_id, identity=None, schema=None)` — filter is missing.

By design (NOT gaps):
- Node has no soft-delete. ADR-0133 §"Edges only; nodes are not soft-deletable" is explicit.

## Slim repo (`halvim_mindsos/mindsos_core/`) — soft-delete is DELIBERATELY ABSENT

Source code comments are explicit about deferral:

- `halvim_mindsos/mindsos_core/models/edge.py:7` — *"Phase 03 strips the soft-delete fields (`deprecated_at` / `disputed_at`, ADR-0133) — those land in **Phase 10** alongside the snapshot / RemovalImpact machinery."*
- `halvim_mindsos/mindsos_core/models/graph.py:18` — *"`properties` parameter / graph-level property bag (ADR-0130) — **Phase 05/10**."*

Slim repo state at Phase 04 confirmed:
- ✅ Edge.properties / HyperEdge.properties / Node.properties — bags exist (line 31 / 61 / Node).
- ✗ Edge / HyperEdge: NO `deprecated_at` / `disputed_at` (explicitly stripped per Phase 03 comment → Phase 10).
- ✗ Graph: NO graph-level properties bag (per Phase 04 comment → Phase 05/10).
- ✗ No Metagraph / MetaEdge / MetaHyperEdge / CompositionalMetaEdge present.
- ✗ State-file `graph-<name>.json` v=2 schema does not include graph-level `properties` or edge `deprecated_at` (lines 32-45 of `mindsos_cli/state.py`).

## Implication for round-5 / round-6 pins

**Round-6 pin #20 (promote soft-delete machinery to 05a)** — was reasoned against the full repo (where it exists). Against the slim repo, it's a **port-and-build**, not a verification. The original slim plan defers to Phase 10. Round-6's anti-pattern argument ("ship 05a hard-delete, retrofit at 10") holds in spirit but ignores that Phase 03 already shipped Edge/HyperEdge without soft-delete and was tester-confirmed. Promoting soft-delete to 05a creates *asymmetry* — Edge has no soft-delete, MetaEdge does. Honoring slim's Phase 10 plan keeps the symmetry: all four edge variants get soft-delete in one phase together.

**Round-6 pin #28 (promote bag to 05a)** — slim Graph explicitly says "Phase 05/10". Same logic: stay at the original deferral, OR override.

## Verdict on #20

Re-scope #20 from "promote to 05a (build)" → **revert to slim's Phase 10 plan, soft-delete substrate lands at Phase 10 across all four edge variants uniformly.** This restores the symmetry argument: Phase 05a ships MetaEdge / MetaHyperEdge with the same shape as Phase 03's Edge / HyperEdge (no soft-delete fields, just `properties`). Phase 10 retrofits all four together.

Counter-pick (if user prefers anti-pattern argument): keep #20 as build-in-05a, accept asymmetry through Phase 06–09.

## Verdict on #28

Same logic: revert to Phase 05/10 (slim's intent). Verify in Phase 10 audit (task #3) which one slim authored.

## Verdict on #34 (soft-delete read-API semantics)

Moot until soft-delete substrate lands. The full-repo gaps (#1–5 above) belong to whatever phase ports soft-delete to slim — likely Phase 10.

## Recommendations for the actual Phase 05a row

Based on the slim repo's authored intent, Phase 05a row should pin:

1. **Metagraph + MetaEdge + MetaHyperEdge ship WITHOUT soft-delete fields** (matching Phase 03 Edge/HyperEdge precedent). Symmetric.
2. **Metagraph and Graph ship WITHOUT graph-level property bag** if Phase 10 owns it (defer per slim authoring).
3. **Phase 05a state-file `metagraph-<name>.json` does not need to plan space for soft-delete or graph-bag fields** — those are added uniformly at Phase 10.
4. **CompositionalMetaEdge subclass NOT shipped in 05a** (independent — falls under M8/ADR-0117 reserved; original PHASE_MAP has 05c separate).

## Carry-forward gaps for whichever phase ports soft-delete to slim

All five full-repo defects above (HyperEdge no API, API inconsistency, Metagraph missing dispute methods, CompositionalMetaEdge bypass bug, Loader missing filter param) are cleanup items for the porting phase (Phase 10 if reverted, 05a if pin held).
