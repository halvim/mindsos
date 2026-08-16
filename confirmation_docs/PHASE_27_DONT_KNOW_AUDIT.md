# Phase 27 Dont-Know Audit (ADR-0157 / L3-57)

**Status:** Closed — Phase 42 (X3) sub-deliverable.
**Date:** 2026-06-05.
**Scope:** Reconcile the shipped `FAMILY_RULES` dont-know-shape dict
(`mindsos_capacity/family_rules.py`, ADR-0157) against the shipped
`FUNCTIONAL_CATEGORIES` (`mindsos_capacity/identifiers.py`, ADR-0065).
Mandated by `L1_L3_REFRAME_DECISIONS.md` §D38 cascade + the Phase 40
ship pushback **PB-8** (the dict was transcribed verbatim at Phase 40
with a latent key-vocabulary mismatch) tracked as **L3-57**.

---

## 1. Background — the latent mismatch (Phase 40 PB-8)

Phase 40 shipped ADR-0157's `FAMILY_RULES` dict **verbatim**. The dict's
two-level lookup (`family_rule_for`) resolves a capacity IRI by
**name-prefix first, then category, then a permissive `DATASTATE_MARKER`
default**. The verbatim keys used `derive` / `signal`, but the shipped
`FUNCTIONAL_CATEGORIES` are `derivation` / `signalling`, and seven
categories had no key at all — so **9 of the 13 categories resolved via
the silent default** rather than by intent. Latent at v1 (the 3 shipped
capacities classify correctly because the default happens to match), but
a misclassification foot-gun once WSD/FOL ship real capacities in those
categories.

## 2. The 13 shipped FUNCTIONAL_CATEGORIES (ADR-0065) and their shapes

| Category | Dont-know shape | Resolves via |
|---|---|---|
| perception | DATASTATE_MARKER | explicit key |
| comprehension | OPTIONAL_RETURN | explicit key (ratified — see §amendment-2) |
| derivation | DATASTATE_MARKER | explicit key (renamed from `derive`) |
| decomposition | DATASTATE_MARKER | **deferred default** |
| combination | OPTIONAL_RETURN | explicit key |
| path-finding | DATASTATE_MARKER | **deferred default** |
| retrieval | OPTIONAL_RETURN | explicit key |
| scoring | OPTIONAL_RETURN | explicit key |
| trace | DATASTATE_MARKER | explicit key (added; grounded by `trace:problem`) |
| signalling | OPTIONAL_RETURN | explicit key (renamed from `signal`) |
| interaction | DATASTATE_MARKER | **deferred default** |
| learning-methods | DATASTATE_MARKER | **deferred default** |
| consolidate | DATASTATE_MARKER | explicit key (added; grounded by `consolidate:mm`) |

## 3. Decision — L3-57 (PB-8 Option 3: fix the groundable, defer the unknown)

Three options were weighed (`PHASE_42_DESIGN_LOG.md §5` PB-8):

- **Option 1** — fix all 9 now. Rejected: forces guessing shapes for
  categories with zero shipped capacities.
- **Option 2** — keep the permissive default, document only. Rejected:
  leaves a silent foot-gun behind a `log.info`.
- **Option 3 (chosen)** — fix what is unambiguously wrong or groundable
  now; defer what is genuinely unknown, but make the deferral explicit
  and test-pinned.

Applied in ADR-0157 §amendment-1 (`family_rules.py`):

1. **Rename** `derive` → `derivation`, `signal` → `signalling` (typo-class
   mismatches vs the shipped category names; intended shape unchanged).
2. **Add** `consolidate` → `DATASTATE_MARKER` and `trace` →
   `DATASTATE_MARKER` — shapes grounded by the shipped `consolidate:mm`
   and `trace:problem` write capacities.
3. **Defer** the remaining 5 categories to their owning installation
   chats, recorded as `family_rules.DEFERRED_DEFAULT_CATEGORIES` and
   pinned by `tests/phase_42/test_phase_27_audit_doc.py`.

Net: 4 of the 9 fall-throughs resolved by intent; the other 5 converted
from a silent default into a documented, test-pinned deferral.

## 4. Deferred-by-design categories (shape ratified at owning chat)

These four intentionally resolve via the permissive `DATASTATE_MARKER`
default until their owning installation chat ratifies a concrete shape.
The list is frozen as `family_rules.DEFERRED_DEFAULT_CATEGORIES`:

- `decomposition`
- `path-finding`
- `interaction`
- `learning-methods`

Owning chats: WSD installation (comprehension / decomposition /
path-finding slices), FOL installation, code-skill installation. Each
adds the explicit `FAMILY_RULES` key when it ships the first capacity in
that category, and removes the category from
`DEFERRED_DEFAULT_CATEGORIES`.

## 5. Non-category keys retained

`FAMILY_RULES` also keys downstream **name-prefix** families that are not
ADR-0065 categories (`combination`/method libraries, `predicate`,
`validate`, `decision`, `transform`, `process`, `hint`, `planning`,
`dream`, `code`, `promotion_rule`, `adapter`, `pattern`, `als`,
`phase6`, plus the `comparator`/`evaluator`/`metric`/`mechanism`
method-library prefixes). These are resolved by the name-prefix tier and
are out of scope for the category reconciliation above.

## amendment-2 — `comprehension` ratified (external-model reading seam)

`comprehension` leaves `DEFERRED_DEFAULT_CATEGORIES` and takes an explicit
`OPTIONAL_RETURN` key. Four remain.

The owning installation is the external-model reading family
(`mindsos_capacity/builtins/comprehension_v0.py`), which ships the first
capacities in this category. §4 prescribes exactly this exit: the owning
chat adds the key and removes the category.

**Why `OPTIONAL_RETURN` and not `VERDICT`.** A reading capacity's don't-know
is a null value on its declared value output; the reason is carried on the
reader's paired reading-record output, so it still reaches the run's
grounding graph. `VERDICT` was rejected: verdict shapes belong to capacities
that state an outcome, and the reader's registration guard exists precisely
to keep a reading capacity from producing into `decision` / `comparator` /
`predicate`. Giving the family a verdict shape would have argued the
opposite of that guard.

**Why not `NeedsInput`.** It short-circuits output validation, so a reader
raising it would leave no node in the grounding graph saying why the value
is missing. The escalation is instead raised by the decision step that finds
it cannot evaluate its condition, which is also where the refusal belongs.
