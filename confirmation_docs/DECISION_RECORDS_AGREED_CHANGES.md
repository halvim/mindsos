---
title: Decision Records — agreed changes across the seam/planning exchange
status: Agreed between chats — the record of record for both lanes
date: 2026-08-08
source: cross-chat exchange, 15 replies (channel file is scratch and never committed)
---

# Agreed changes — LLM seam chat ↔ Decision Records planning chat

Eight exchanges between the LLM seam lane and this lane. Everything below is agreed by both.

---

## LLM seam lane — agreed, owner: seam chat

| # | Change | Why |
|---|---|---|
| S1 | Family is `comprehension`, shape `OPTIONAL_RETURN`; ratified out of `DEFERRED_DEFAULT_CATEGORIES` (5→4) | Sidesteps the `adapter → DATASTATE_MARKER` trap |
| S2 | Decline is `{value: None, record: {...}}`, **not** `NeedsInput` | `NeedsInput` short-circuits output validation ⟹ no node in the run graph stating why |
| S3 | One reader per field (`register_reader` factory); one origin record type per reader | Blackboard is one value per DataState IRI — a shared record type displaces provenance |
| S4 | `expected_basis` (registered, present on every refusal) vs `basis` (observed, `None` on refusal) | A refusal must still say whether the field was *meant* to be stated or inferred |
| S5 | Refusal records keep every **registered** fact; only observed facts absent | Pinned by `test_a_refusal_keeps_every_registered_fact` |
| S6 | `origin_party` is a closed token, never printed; prose lives in `*_phrase` fields, identifier-refused at registration | G6 — no IRI or MindsOS vocabulary in a lawyer's document |
| S7 | Quote verification: no verbatim span found ⟹ refusal, model's claimed words retained | Fabrication becomes a refusal by construction |
| S8 | No model-reported confidence stored as uncertainty | A self-scored float is another output of the process under question |
| S9 | `model_unreachable` + **`environment_fault: true\|false`** | *"Our service was down"* must not pad the customer's refusal list — that list is the artifact the engagement is sold on |
| S10 | `value_not_coercible`; reader coerces to the declared `ShapeDescriptor` | Otherwise the threshold step compares `"47 days"` to `30` |
| S11 | Rename `<value>_reading` → `<value>_origin`, `origin_record_iri()` | A policy lookup does not produce a *reading* |
| S12 | Lift the origin shape out of `comprehension_v0` into `mindsos_capacity`, **ADR'd not merged quietly** | Core surface arriving from a GTM branch is what RULES §8 exists to stop |
| S13 | `origin_producer_kind` + `supplied_fields`, **denormalised on every record** | So absence never carries meaning; and an archived Episode must not depend on a module that later gained a producer |
| S14 | `basis`, `source_version`, `source_in_force_from`, `source_in_force_to` as **separate** optional fields | One slot would mean a field whose meaning depends on who wrote it |
| S15 | **`source_identity_phrase`** added (every producer); `origin_party_phrase` narrowed to *who asserted* | A lookup consults an authority; it has no asserting party |
| S16 | Replay raises `RecordedResponseMiss`, **no live fallback anywhere**; readings byte-identical; temperature pinned 0.0 and in the key | The demo must not silently go live when venue wifi is down |
| S17 | `LLMCallBudgetExceeded` / `RecordedResponseMiss` keep **raising**, not graph-resident | A batch stopping loudly beats 300 Records blaming the customer's documents for our configuration |
| S18 | Two-readers-one-document pinned: one document node, both `CONSUMES` at it, one instance of each of four types, exactly two `PRODUCES` per capacity | The failure is invisible from the document end — G7 would not catch it |

**Open on their side:** `no_source_in_force` + `source_unreachable` in the reason set; whether
the reason vocabulary is a global union with per-producer declared subsets; where the
"performed live on <date>" timestamp comes from.

---

## Decision Records lane — agreed, owner: this lane

| # | Change | Why |
|---|---|---|
| D1 | **G7** — every `DataStateInstance` the Record attributes has a path to the grounding root | `seed()` mints with no incoming edge; a start-input value is unattributable, permanently and silently. A guard beats a written-down cross-lane constraint |
| D2 | C2 split: reader declares the document as an input (seam) / document reachable from the root (**run driver, this lane**) | I had bundled a constraint on them with one on the caller |
| D3 | **C3 amended — origin is denormalised onto the record at write time** | Verified: `persist_capacity_mm` persists only the run graphs; the L3 catalog is separate and mutable, so an archived Episode + a changed registration renders the wrong origin. A Record states what was true *when it ran* |
| D4 | Phrasing precedence: phrase from `basis` when admitted, `expected_basis` only when refused | Phrasing from `expected_basis` unconditionally makes a mismatch print as a lie |
| D5 | A systematic expected/observed mismatch is a **registration defect → batch report**, not a per-case refusal | One mismatch is language variation; a batch of them is a mis-registered reader |
| D6 | Replay attestation goes in a **provenance footer**, not the header | The first line of a Decision Record belongs to the outcome |
| D7 | **The as-of date stays out of the document**, entering as its own DataState into the lookup | The replay key hashes exact source text — run 5 would have become *"different documents give different limits"* |
| D8 | Batch-stop accounting (*"stopped at case 47 of 300"*) is this lane's | Raising leaves a gap that a silent short batch reads as a complete one |
| D9 | The **policy lookup is origin's second producer** — and the deciding argument for origin being core | The most load-bearing origin statement in the product is produced by a `decision`-family capacity and never touches a model |
| D10 | **The money sentence is the acceptance test for the field set** | It found two real holes on its first two runs |

---

## The method that worked

Testing the abstract contract against **one concrete artifact** — the sentence
*"Denied: elapsed days 47 against a limit of 30, from the claims policy, version 4, in force
since 12 March"* — found `source_identity_phrase` (a field already doing two jobs) and
`no_source_in_force` (a refusal reason that did not exist for one of the slice's five
required runs). Neither was visible from principles.

---

## The standing risk

**Eight exchanges, zero lines of the slice.** The origin contract has grown
from a field on a record to a core module + an ADR + a CR + a ~25-field closed union with a
governance process — all before a single Record has been rendered. The two holes found were
found by testing against a concrete artifact; the remaining holes will be found the same
way, and finding them in code is cheaper than finding them in correspondence.

---

## Later agreements (replies 12–15) and the final pin

| # | Change | Owner |
|---|---|---|
| S19 | `REFUSAL_NO_VERSION_IN_FORCE` → **`REFUSAL_NO_SOURCE_IN_FORCE`**; **`REFUSAL_SOURCE_UNREACHABLE`** added to `ENVIRONMENT_FAULT_REASONS` | seam |
| S20 | **`FIELD_POSSIBLE_REFUSAL_REASONS`** on the spine; `build_origin_record` **raises** on an undeclared reason. Spine 12, union 30 | seam |
| S21 | Origin module ships at **`mindsos_capacity/builtins/origin_v0.py`** (not core proper — `reduction_v0` precedent); ADR `Proposed`, number unassigned | seam |
| S22 | `register_reader(session=…)`; **every guard and registry walk is scope-aware** | seam |
| S23 | `opaque_into_decision(capacity_layer, user_id=…)` exposed as a **function**, called from the demo-Skill boot test — one definition of the rule, not two | seam |
| S24 | **The union is v0 and NOT frozen** — the policy lookup is its second producer and shapes the last of it | seam |
| D11 | **v0 = runs 1 and 2, guards G2/G3/G7/G8.** Runs 3–5 and G1/G4/G6 deferred | this lane |
| D12 | The criterion is **named**: *a filer must file when gross income reaches the threshold in force for their status and tax year* | this lane |
| D13 | E/F branch off `feat/decision-records` when **pushed**, not merged — the slice is the evidence for merging | this lane |
| D14 | **Timestamp exists**: `consolidated_at` is an Episode *content* field (`episodic_memories.py`). No core work needed | this lane |
| D15 | **G8** — the policy lookup and decision capacity must resolve **Global**. The union rule is *shadow, not merge* (`views.py:216`), so a Local capacity at either IRI silently replaces the authority | this lane |

## THE PIN (set 2026-08-08)

**Core `origin/main` `476444e` · seam `feat/decision-records` rebased onto it.**
Zero file overlap between the two — verified, so the rebase cannot conflict.

`8400d6f` (#122) + `476444e` (#123) shipped the **Local-preferring union finder view**, which
**killed the Local-only constraint**: a Local reader now composes with a Global lookup, and
the Local-then-Global retry is retired (one session-scoped find, one verdict). Re-verified at
the pin: `_select_finder` still keys off **start** arity (defect **D-A** open), so the
slice's three-starts choice stands and must not be copied as a general pattern.

## The one thing with no evidence behind it

**Nothing in either lane has ever invoked a finder** — every pipeline in `tests/llm_seam/` is
hand-built. The plan's first rule is that the route must be *found*. **The day-one route
check is the only test that can invalidate both lanes, and it runs before anything else.**
