---
title: Alignment role-graph canonical form is `alignment:<a>:<b>`
status: Accepted
date: 2026-06-01
layer: L2
---

# ADR-0154: Alignment role-graph canonical naming

**Status:** Accepted

**Date:** 2026-06-01 (L2 chat closure)

**Related (Accepted):** [ADR-0045](0045-per-role-iri-builders.md),
[ADR-0149](0149-l2-role-schemas-strict-false-and-tightening-rule.md),
[ADR-0150](0150-l2-knowledge-lifecycle.md) §amendment-1 + §amendment-2.

**Companion docs:** `_workbench/L2_CHAT_DECISIONS.md` D-L2-1;
`HANDOFF.md` §6.3 drifts-to-reconcile table.

## Context

Phase 36 closure surfaced a 3-form naming drift in shipped MindsOS
code for alignment role-graphs:

| Form | Where shipped |
|---|---|
| `alignment:<a><->b>` | `mindsos_knowledge/identifiers.py:303` `alignment_role()` body |
| `alignment:<a>-<b>` | `identifiers.py:297` docstring; Phase 36 validator tests |
| `alignment:<a>:<b>` | ADR-0150 §amendment-1 + `mindsos_knowledge/bootstrap.py:8,128` |

The 3 forms in flight prevent downstream consumers from picking a
stable reference shape. DWF installation chat needs alignment IRIs
to write `AlignmentsImporter` bodies; WSD installation chat needs
the canonical form for cross-system mappings (§5 of WSD
`coordinated_change_L2`).

HANDOFF.md §6.3 originally routed this to DWF chat as "PB-7 in DWF
FUTURE_CHAT_PROMPT" but L2 chat is the structural owner of role-graph
naming. L2 chat picks; DWF chat ratifies or re-litigates with use-case
pressure.

The 3 candidate forms are not equivalent:

- `<a><->b>` has no parser semantics; the `<->` substring is decorative
  prose that doesn't survive code review consistently.
- `<a>-<b>` is structurally ambiguous when `<a>` or `<b>` contains
  hyphens. The role-set already contains `promoted-pipelines` and
  `task-patterns`, both of which would produce ambiguous alignment
  graph names: `alignment:promoted-pipelines-task-patterns` could
  parse as `(promoted, pipelines-task-patterns)`,
  `(promoted-pipelines, task-patterns)`, or
  `(promoted-pipelines-task, patterns)`.
- `<a>:<b>` uses the parser-reserved separator already used in every
  other IRI surface. ADR-0150 §amendment-1 + `bootstrap.py` already
  commit to it in the load-bearing surfaces (schema bootstrap).

## Decision

**Canonical form: `alignment:<a>:<b>`.**

The two role names are sorted alphabetically before composition so
`alignment_role("lexicon", "concepts")` and
`alignment_role("concepts", "lexicon")` return the same string.

**Rules:**

1. **Separator is `:` (colon).** Not `-`, not `<->`.
2. **Role names are joined as-is** (no escaping or transformation).
3. **Roles are sorted alphabetically** before composition (canonical
   form is independent of argument order).
4. **The result is NOT a version-qualified IRI** per ADR-0150
   §amendment-1 — this is a *graph name* used for metagraph routing;
   `parse_iri()` rejects it.

**Shipped-code reconciliation:**

- `mindsos_knowledge/identifiers.py` `alignment_role()` body fixed:
  `f"alignment:{a}:{b}"` (was `f"alignment:{a}<->{b}"`).
- `identifiers.py:297` docstring rewritten to match.
- Phase 36 validator tests in `tests/phase_36/test_validators.py`
  amended to assert `alignment:<a>:<b>` form.
- `mindsos_knowledge/bootstrap.py` unchanged (already canonical).
- ADR-0150 §amendment-1 unchanged (already canonical).

## Rationale

**Why colon.** Three reasons converge:

1. **Already-canonical authority.** ADR-0150 §amendment-1 (Phase 14
   ship) explicitly specifies `alignment:<a>:<b>` as the form
   accepted by `ensure_global_role_graph` / rejected by
   `ensure_local_role_graph`. Two of the three shipped forms (the
   `<->` and `-` variants) postdate this ADR and contradict it.

2. **Parser separator already established.** Every other IRI in the
   codebase uses `:` as the structural separator (`dolce-dul-<v>:
   <body>`, `oewn-<v>:synset:<id>`,
   `episodic-memories-<v>:episode:<u>:<id>` per ADR-0044 §amendment-3
   Phase 39 rename).
   Reusing the established separator is cheaper than introducing a
   new one for one role family.

3. **Unambiguous with hyphenated role names.** `promoted-pipelines`
   and `task-patterns` (and future `parameter-staging`,
   `pending-promotions`, `capacity-gaps`, `learned-parameters`,
   `episodic_memories`) all contain hyphens or underscores. Any
   dash-based separator is structurally ambiguous; colon is not.

**Why pick now, before DWF chat.** DWF installation chat needs
canonical form to write `AlignmentsImporter` bodies; WSD installation
chat needs it for cross-system InterGraphEdges (per WSD §5).
Postponing the pick blocks both. L2 chat is the structural owner of
role-graph naming; DWF can re-litigate via L2_CHAT_DECISIONS
amendment if use-case pressure surfaces.

## Consequences

**Good:**

- Single canonical form across code + ADRs + tests. The 3-form drift
  closes.
- Downstream chats (DWF, WSD installation) inherit one shape;
  unblocks both.
- Parser semantics consistent with rest of IRI surface.
- Documentation (`HANDOFF.md` §6.3) gets one row removed from the
  drifts-to-reconcile table.

**Tradeoffs:**

- Touches Phase 36 validator tests (~3-5 assertions). One-shot fix.
- `identifiers.py:303` is the lone wrong implementation surface;
  one-line body change. Atomic with the test fix.
- DWF chat may re-litigate if a use-case requires a different
  separator. Considered unlikely (the structural ambiguity argument
  is grounded in the existing role-set; DWF would need to argue for
  a separator that handles hyphens better than colon).

**Lock-ins:**

- Once shipped, downstream consumers depend on the colon separator.
  Future amendment requires migration of all alignment graph names
  in shipped state.

## Alternatives considered

1. **`alignment:<a><->b>` (current `identifiers.py:303`).** Rejected —
   `<->` has no parser semantics; decorative; doesn't survive code
   review consistently; hard to type accurately.

2. **`alignment:<a>-<b>` (current Phase 36 tests + docstring).**
   Rejected — structurally ambiguous with hyphenated role names. The
   role-set already contains 7+ hyphenated names post-ADR-0150
   §amendment-4; ambiguity is intrinsic, not edge-case.

3. **Defer to DWF chat.** Rejected — L2 chat is the structural owner;
   DWF is a downstream consumer with a write-side use case; structural
   picks belong upstream. DWF ratifies or re-litigates.

4. **Different separator (e.g., `__` double-underscore).** Rejected —
   no existing precedent in the IRI surface; introduces a new
   separator family without benefit over colon.

5. **Disallow hyphenated role names instead.** Rejected — would
   require renaming `promoted-pipelines`, `task-patterns`,
   `parameter-staging`, etc. Far more invasive than picking a colon
   separator.

## Source

`_workbench/L2_CHAT_DECISIONS.md` D-L2-1; `HANDOFF.md` §6.3
drifts-to-reconcile table; `mindsos_knowledge/identifiers.py:297-303`;
`mindsos_knowledge/bootstrap.py:8,128`; ADR-0150 §amendment-1;
WSD `coordinated_change_L2_lexicon_layers_and_role_graphs.md` §5
(cross-system InterGraphEdges depending on alignment naming).
