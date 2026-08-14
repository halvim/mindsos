# ADR-0209 — Member-level in-band refusal (shape (a)): the type declares it, the reducer decodes it, plan construction enforces it

**Status:** Accepted (2026-08-15). The substrate ship of
`core-collection-member-dont-know`, owner-ruled 2026-08-14 to **shape (a)**.
The manifest field and stop token this contract leans on are ADR-0201
amendment 5; this ADR owns the type-system halves: the DataState property,
the reducer declaration, and the static check.

## Context

A map member that cannot decide its exposure had no way to say so. A member
returning `success=False` raises `MemberAbortError` and aborts the whole
request; there is no member-level `dont_know`. The only workaround — a
member returning `success=True` carrying a sentinel the fold decodes — was
named in review as *"an unenforced, undocumented convention"*, and that
convention is exactly what ADR-0208 shipped one level down, sound and gated
there, enforced by nothing when promoted to member level.

**Owner ruling (2026-08-14): shape (a).** An exposure that cannot be decided
says so as an **in-band refusal value** carrying its origin record — not as a
third member outcome. The grounds are doctrine, not cost: the system has
ruled this same question three times at three levels — seam S2 (a decline is
`{value: None, record}`, never `NeedsInput`), ADR-0208 D4 (the lookup's
refusal RETURNS in-band; only outages raise), and L-2's stop design —
settling that **machinery outcomes are binary and epistemic outcomes are
values in the graph**. Shape (b) — a third member outcome — would contradict
that stack; it stays filed as the possible long-term form, carrying the #158
member-order hazard. Never name it `dont_know`: no third member outcome
exists under (a).

Shape (a) as *"copy ADR-0208 verbatim one level up"* does not survive two
refusals: bare `None` per refusing member gives the fold's seeded list
indistinguishable entries while their member blocks differ — precisely the
N-F2 shape the renderer bijection refuses. The correlation fix is
structural, not a value contract (ADR-0201 am-5 `member_graph_ids`); what
remains — and what this ADR decides — is how anything downstream can KNOW a
member set may contain refusals, instead of inferring it from values.

## Decision

**D1 — the DataState declares refusal capability.**
`DataState.refusal_capable: bool = False` (`mindsos_capacity/datastate.py`),
emitted to node properties as `refusal_capable` when true, following the
ADR-0199 `collection`/`member_ds` precedent (a frozen dataclass field with a
verified property-emission home). A refusal-capable type's **values** may be
an ADR-0208-shaped in-band refusal — a value that says "this cannot be
decided", whose refusal PROSE travels in the member's own origin record per
ADR-0208. The type governs decoding; the record carries the words.

**D2 — free-standing, deliberately.** The flag is NOT restricted to types
that are currently some collection's `member_ds`: that tie would make
registration order-dependent and block a future leaf consumer. No coherence
pair rule until a second consumer exists (§44 Q2). The plan-construction
check below is the sole consumer today.

**D3 — the reducer declares it decodes.**
`decodes_refusals: bool = False` on the capacity declaration
(`mindsos_capacity/capacity.py`), the `printable_phrase` precedent: optional,
default-false, every existing capacity unchanged. Like `input_group`
(ADR-0159 Decision 8) it is a registration-time fact read off the
declaration, **not** emitted to the graph — run evidence of what a reducer
concluded already grounds; what it was *promised to handle* is declaration
data.

**D4 — the check is static, at plan construction — and on both entry
roads.** `plan_construction.check_fold_reducer_decode`: for every `fold`
spec (including nested `sub_plan`s), when `in_ds` resolves to a collection
whose `member_ds` is `refusal_capable`, the reducer's declaration must carry
`decodes_refusals=True`, else `FoldReducerDecodeError` — statically, before
any member runs. There is deliberately **no registration-time site**: the
fold spec names no member capacity and the map spec names DataStates only,
the member capacity being resolved at run time — so "a reducer over a
refusal-capable member set" first exists where `reducer_iri` and `in_ds`
coexist, which is the plan. Called from `_build_from_milestones` (the
planner road) **and** from `execution.run` intake (the direct-`PlanResult`
road every current demo driver uses): a contract enforced on one of two
roads is a convention. Both sites read declarations only. DataState nodes
the scope-correct views cannot see are skipped (the `start_phrases`
tolerance); an **unresolvable reducer declaration over a refusal-capable
member set fails the check** — the point is a static refusal, and "could not
verify" is not "verified".

## Consequences

- Nothing that exists changes behaviour: no shipped DataState sets
  `refusal_capable`, so the check passes every current plan untouched, and
  both new fields default to the pre-ADR state.
- The demo's headline beat (a per-exposure refusal beside a per-exposure
  answer) becomes buildable: the exposure-verdict DS is declared
  refusal-capable, the demo reducer declares the decode, and the refusing
  member's graph renders by manifest position (ADR-0201 am-5). Demo
  consumption is a demo-lane ship (owner ruling D5).
- The **machinery half is explicitly not solved here**
  (`core-member-machinery-failure-partial-record`, split out by critic §38
  condition 1 so shape (a) cannot bury it): (a) makes an *undecidable*
  exposure an in-band value — the epistemic half; a member whose capacity
  *crashes* still aborts the request. Partial results are that ship, on this
  substrate.
- `origin_v0`'s union stays frozen: an in-band refusal value carries the
  member's own origin record (ADR-0208's producers), so no new
  `producer_kind` and no new capacity CATEGORY (Gate 4's restated terms) is
  needed.
