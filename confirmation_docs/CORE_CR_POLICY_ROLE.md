# CORE CR — the policy role (`policies`)

**Filed:** 2026-08-09. **Status:** BUILT on `feat/policy-role`, pre-filtered, **not gated**.
**Base:** `origin/main` `ab30f5b` (current main, deliberately **not** the Decision Records
slice pin — core work should not ride a GTM lane's frozen pin).
**ADR:** amends **ADR-0150**, amendment number **unassigned** (the §21 precedent).
**Requested by:** the Decision Records v0 slice (work item A, the policy store).

---

## 1. What this adds

A 17th L2 role, `policies`: **dated, versioned editions of an authority**, dual-scope,
`append_only`, one NodeType (`PolicyEdition`), zero edge types.

The Decision Records slice needs a limit and its version to enter a derivation as
**produced DataStates** from a real lookup capacity — `CapacityMMWriter.record` writes only
`(capacity_iri, input IRIs, outputs)`, so anything read from a context snapshot never
reaches the grounding graph and the acceptance gate fails at step one. That forces a store
the lookup can read. This is that store.

---

## 2. Three homes were considered. Two were wrong.

**`learned-parameters` — rejected, and it is the one item in the Revenue Build Plan that is
actively wrong.** Three independent grounds: doctrine (a policy limit is *fixed*, not
learned), safety (Local shadows Global **per knob**, so a user override silently shadows a
policy), and the gate (it reaches a body through the context snapshot, not through the
graph).

**`dataset:<name>` — rejected on doctrine, after being seriously considered.** It fits
mechanically: registered per-instance schema, `append_only` default, Local-only, a JSON
content field that would hold both policy text and the seam's prompt bodies, and **zero core
change**. It was rejected because a dataset is a *corpus a brain owns* and a policy is an
*authority a decision cites*. That distinction is not cosmetic in this product: a Decision
Record states **which authority, which edition, in force when**, so the store's identity is
part of the claim being made. Squatting a prefix whose meaning is "corpus" would put the
wrong word in the one place the product is read most carefully.

**A new fixed role — chosen.** Cost accepted knowingly: core surface, its own branch, its
own gate, and it breaks a closed set on purpose (§4).

---

## 3. Fixed role, not a parametric `policy:<name>` prefix

`dataset:` is parametric because dataset **shapes** genuinely differ per brain — arc1 holds
`Task` nodes with grid content, arc3 holds `Game` handles — which is why ADR-0150 §am-9 says
*"core owns no dataset shape"*.

The opposite holds here. `in_force_from` / `in_force_to` / version / text is the **same**
shape for a statutory dollar threshold and for a versioned prompt body, and that generality
is the entire argument for the role existing. A per-owner shape registry would hand back the
doctrine the role was created to buy.

---

## 4. Blast radius — measured, not estimated

**Nine touch points**, and the ninth was found only by running the suite:

| # | File | What |
|---|---|---|
| 1 | `mindsos_knowledge/identifiers.py` | `ROLE_POLICIES`, `UPPER_LAYER_ROLES`, `policy_edition_iri`, `_mint_policy_edition`, `_IRI_BUILDERS`, `_PREFIXES`, `_KINDS_PER_ROLE` |
| 2 | `mindsos_knowledge/schemas/policies.py` | **new** |
| 3 | `mindsos_knowledge/schemas/__init__.py` | import + `_ROLE_SCHEMA_BUILDERS` |
| 4 | `mindsos_knowledge/bootstrap.py` | import, `_GLOBAL_NAMED_ROLES`, `_LOCAL_NAMED_ROLES`, bootstrap-order map |
| 5 | `mindsos_knowledge/__init__.py` | six export lines |
| 6 | **`mindsos_admin/bootstrap.py`** | **`_GLOBAL_ROLE_ORDER`** — a Phase-14 PB-21 **parity contract** asserted at *import time*. Missing it produced **21 collection errors** and −658 passing tests, in modules with no visible connection to roles |

**And it deliberately breaks the closed-set guard in 19 tests across 13 files.** I first
estimated four, by grepping `len(ALL_ROLES) == 16`. That was wrong: the closed set is pinned
in **seven different shapes**, and only one of them mentions `ALL_ROLES`:

- `len(ALL_ROLES)` — 4 files
- `len(_ROLE_SCHEMA_BUILDERS)` — 3 files
- `len(_GLOBAL_NAMED_ROLES | _LOCAL_NAMED_ROLES)` — 1
- role-set **literals** (`UPPER_LAYER_ROLES`, `_EXPECTED_GLOBAL_ROLES`, `_EXPECTED_LAZY_LOCAL_ROLES`, `_ALL_NAMED_ROLES`, local-role sets) — 6
- **metagraph graph counts** (`len(g.graphs) == 11`, `len(local.graphs) == 9`, `len(view.roles())`) — 4
- the `_IRI_BUILDERS` **key-set literal** — 2
- the **kahn scheduler order tuple** — 1

The guard system is doing exactly its job, and the spread is the point: **a 17th role cannot
be added quietly.** That is worth preserving, not simplifying.

One test was *not* changed: `_ADR_0045_BUILDERS` in `tests/phase_12` stays at 15. It is a
frozen ADR-0045-era builder list — `learned_pipeline_iri`, `installed_capability_iri` and
the rest are absent from it too, so `policy_edition_iri` does not belong in it. I bumped it
by reflex first and reverted.

---

## 5. Two shape decisions worth reviewing

**The node's `value` payload IS the edition's text.** `value` is a `RESERVED_PROPERTY_KEYS`
member — `mindsos_core` owns it as the node payload — so a `PolicyEdition` carrying a
`value` *property* raises `PropertyShapeError` at registration. `learned-parameters` sets
the precedent (`learn_parameter` calls `add_node(value=value, ...)` and never puts `value`
in `props`). So the payload holds the authority's words, the ADR-0151 `storage_mode`
declaration names `value` as the large-payload field, and the typed thing a criterion
compares against is a **`stated_value` property**. A test pins the collision, because it is
invisible until the first write and the first write is in another lane.

**No edge types, and edition ordering is derived.** Two editions of one authority are
related by their in-force dates and by nothing else. An ordering edge or an append ordinal
would be a second place for that truth to live — ADR-0192's criterion, the same one that
rejected a stored `fundamental` boolean and a stored step order.

---

## 6. The thing to read before quoting this role

**`append_only` is DECLARED, NOT ENFORCED.** `validate_mutation_discipline` is uncalled
system-wide — `schemas/dataset.py` says so outright — so nothing in core stops an edition
being overwritten. The role declares the discipline it needs and a later enforcement pass
reads that declaration, which is why declaring it is still right.

But *"append-only policy store"* is a sentence someone will put in front of a customer, and
it is **not true of the substrate today** — only of the intent.
`test_append_only_is_declared_but_not_enforced` pins the gap and will go red the day
enforcement lands. Delete it then, and say so in the commit.

---

## 7. Verification status

Pre-filtered in the Cowork container on **Python 3.12** (`requires-python = ">=3.12"`;
3.10 and 3.11 both fail this repo for different reasons), against a pristine copy of the
same tree:

- **Zero newly-failing tests** vs baseline, by name-level diff — not by count.
- **Zero new collection errors** vs baseline.
- Passing: **3521** vs baseline **3506** (+15 = 12 new `tests/policy_role` + 3 sentinels
  that now assert the corrected values).
- `tests/policy_role` — **12 passed**.

**This is a pre-filter, not the gate.** RULES §4: the docker image bakes source via `COPY`,
so only `docker compose -p mindsos-core --profile test run --rm --build` counts, and the
counts above should be treated as a prediction until Linux says otherwise.

---

## 8. What is NOT in this CR

- ~~**The lookup capacity.**~~ ✅ **BUILT 2026-08-12, ADR-0208** — but at
  `capacity:retrieval:*`, **not** `capacity:decision:*` as written here. The reasoning is in
  that ADR §D1; the short version is that the two rules said to agree on the `decision` shape
  do not, because `family_rule_for` has no caller in any shipped module. As-of selection by
  window containment lives in **`mindsos_knowledge/policies.py`**, beside this role rather
  than inside the capacity, because the next consumer of the store must not re-derive it
  (RULES §8).
- ~~**Any write path**, and therefore any append-only enforcement.~~ ⚠ **PARTLY BUILT.**
  `mindsos_knowledge.policies.write_policy_edition` is the store's writer and it **refuses to
  replace an existing edition**, so append-only is real *at the only door there is*.
  `validate_mutation_discipline` remains uncalled system-wide and §6's caveat below stands
  unchanged — `handle.graph().remove_node()` still bypasses everything, and **"append-only
  policy store" is still not a sentence anyone may put in front of a customer.**
- **Seeding the seam's prompt bodies.** The role can hold them — a prompt body is authored
  text under a version with the same in-force semantics — but wiring that is the seam
  lane's.
