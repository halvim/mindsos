# Phase 05d Design Log

**Status:** Active design refinement (chat dated 2026-05-07).
**Target:** Lock the Phase 05d row text in `confirmation_docs/PHASE_MAP.md` §5 (currently a stub authored 2026-05-06 in the 05c chat per P15-A).
**Scope:** `MetaEdgeType` + `MetaHyperEdgeType` schema vocabularies on `MetagraphSchema`; eager-attach extension; CLI; v=2 → v=3 migration; ADR amendments.
**Cascade position:** `05a → 05b → 05c → 05d → 06`. CASC-1 unblocked 05d once 05c shipped (tag `phase-05c-confirmed`, 901 passed + 2 skipped in-container).

---

## Pre-flight audit (resolved 2026-05-07)

The P3 audit task deferred from 05c (does `MetaEdge.type_name` exist on 05a's dataclass?) is **resolved**:

- `mindsos_core/models/metagraph.py:136` — `MetaEdge.type_name: str` (required; ADR-0021 regex via `__post_init__` line 146).
- `mindsos_core/models/metagraph.py:180` — `MetaHyperEdge.type_name: str` (required; regex via `__post_init__` line 200).

Implication: **the 05a-v2 supersession branch in the row stub is dead.** No dataclass expansion, no rehydration tolerance, no cascade reorder needed. 05d ships pure-vocab additions on top of an already-typed primitive.

`Graph.role: Optional[str]` confirmed at `mindsos_core/models/graph.py:94` — so `allowed_*_graphs` role-based constraints have a real attribute to bind against (mirrors 05b/05c precedent).

---

## Meta-plan locks (M-series)

These govern the chat itself, not the row. All accepted by user 2026-05-07.

### M1 — Excise the supersession branch from the row stub at chat-end. Replace the audit clause with a single-line "P3 audit RESOLVED 2026-05-07: `type_name: str` already on both dataclasses (file:line cited)."
**Pick: C.** Preserves the historical trace (P3 deferral) while eliminating the live decision.

### M2 — No round-count target. Drive rounds until pushback well is dry, even if that's 2 rounds.
**Pick: B.** "Pushback well dry" is the actual stop condition; round-count targets cause padding.

### M3 — Pushback numbering restarts at P1 per 05a/05b/05c precedent. Cross-chat references use the form "05c P1-B" for disambiguation.
**Pick: A.** Precedent intact; no benefit to changing it.

### M4 — ADR re-litigation scope: any ADR touched by 05d's row (0014, 0017, possibly 0148). ADRs already shipped and consumed elsewhere remain locked.
**Pick: A.** Broad enough for 05d's actual surface, narrow enough to preserve 05a/05b/05c locks.

### M5 — Scope renegotiation authority: only if a forward-compat or risk argument materializes during rounds (i.e., not opened speculatively).
**Pick: C.** Don't open speculatively; don't pre-foreclose if a real argument surfaces.

### M6 — Reading scope: design-relevant only during rounds. Implementation-chat artifacts (`feedback_docker_compose_invocation`, `user_two_machine_setup`, `feedback_terse_step_recipes`, `feedback_state_dir_env_var`, `feedback_release_workflow_ordering`, `feedback_tag_regex_audit`) deferred to handoff-prompt-drafting time.
**Pick: B.** Saves context, no quality loss for design rounds.

### M7 — Eager-attach drift narrative reframed at chat-end (mechanical correction; no separate pushback). Drift = "metaedge `type_name` not registered in `MetaEdgeType` vocab" (vocab-gap), NOT "field-absence."
**Pick: B.** Mechanical correction; doesn't need adversarial round time.

---

## Critical primitive distinction (load-bearing — read before any 05d decision)

There are FOUR edge primitives at L1 / metagraph layer:

| Primitive             | Connects                              | Repetition allowed?                              | `ordered` field? |
|-----------------------|---------------------------------------|--------------------------------------------------|------------------|
| `MetaEdge`            | graph ↔ graph (in metagraph)          | source ≠ target enforced                         | N/A (binary)     |
| `MetaHyperEdge`       | n graphs (in metagraph), n≥2          | **NO** graph repetition (`metagraph.py:194`)     | **vestigial**    |
| `IntergraphEdge`      | node ↔ node (across graphs)           | source ≠ target node-pair                        | N/A (binary)     |
| `IntergraphHyperEdge` | n nodes (across graphs), n≥2          | **YES** node repetition (compositional)          | **MEANINGFUL**   |

**Canonical example (user 2026-05-07):** A COMPOSITIONAL `IntergraphHyperEdge` from a letter graph (nodes a, b, c, …, t, …) to a word graph (node "letter") has members `l → e → t → t → e → r` — `t` and `e` repeat AND order matters. This rationale (P18-A `ordered=True` default) applies ONLY to `IntergraphHyperEdge`; `MetaHyperEdge.graph_ids` is a uniqueness-enforced set.

Full reference: `~/Library/Application Support/.../memory/reference_mindsos_four_edge_primitives.md`.

---

## Round 1 pushbacks (P1–P7) — LOCKED 2026-05-07

### P1 — Drop `ordered` field from `MetaHyperEdgeType` entirely.
**Pick: C.** P18-A precedent (cat=c+a+t) does not apply: `MetaHyperEdge.graph_ids` is uniqueness-enforced (`metagraph.py:194`), so "ordered=True permits duplicates" rationale collapses. The field has no semantic at the metagraph layer.
**User reinforcement 2026-05-07:** explicitly distinguished MetaHyperEdge (graph↔graph, no repetition) from IntergraphHyperEdge (node↔node, repetition for compositional cases). Pick C confirmed.

### P2 — 4-vocab Cypher namespace policy: mirror 05c (separate dicts, no cross-check, same name across vocabs allowed).
**Pick: A.** Precedent-consistent. Phase 11 schema-migrator owns deferred cross-collision flagging if it ever bites.

### P3 — Eager-attach precheck iteration order documented as implementation-detail.
**Pick: C.** Contract is "atomic precheck, refuses on first violation, error message names the offender unambiguously." Iteration order is not part of the contract; tests match error content, not iteration position.

### P4 — Strike "non-strict attach" recovery from drift narrative.
**Pick: A.** `MetagraphSchema.strict` gates property-type validation only; cannot bypass eager-attach vocab-gap refusal. Recovery is solely "modify schema vocab THEN re-attach." `--lenient` knob (B) would weaken the strong attach-time invariant 05b/05c locked.

### P5 — `Metagraph.add_metaedge` validation order: vocab checks AFTER structural, BEFORE properties.
**Pick: A.** Order: regex → containment → source≠target → require_meta_edge_type → validate_meta_edge (allowed_*_graphs vs Graph.role) → validate_meta_edge_properties (strict only). Mirrors 05b IntergraphEdge precedent.

### P6 — Cross-vocab same-name lookup at attach: refuse strict, but error-hint specifically.
**Pick: B.** `UnknownTypeError` includes hint when same name exists in sibling vocab — e.g., "MetaHyperEdge type 'X' has no MetaHyperEdgeType vocab entry; the schema does have IntergraphHyperEdgeType 'X' registered — check vocab segregation." Strict invariant + helpful error path.

### P7 — Draft full ADR amendment text in 05d row (mirror 05b/05c precedent).
**Pick: A.** Faithful capture of intent; Phase 38 chat is mechanical transcription. ~30-line cost in row text bought against drift risk.

---

## Round 2 pushbacks (P8–P13) — LOCKED 2026-05-07

### P8 — Schema-mutation footgun extension to `add-meta-edge-type` / `add-meta-hyperedge-type`: reuse `_find_attached_metagraphs` helper as-is; warning text mirrors 05c verbatim.
**Pick: A.** Helper at `mindsos_cli/commands/metagraph_schema.py:171` is already vocab-agnostic (used by 5 verbs). Mechanical reuse; no extra surface.

### P9 — Add a single `mindsos metagraph-schema validate --schema MS --metagraph MG` smoke verb across all vocabs.
**Pick: B** *(user override — original pick was A=skip).* Single debug entry point that walks the same eager-attach validation logic without modifying state. Required to support testers debugging "why is attach refusing?" without forced detach + re-attach cycles. Implementation: walk-only; structured report; one verb across all 4 vocabs.

### P10 — ADR-0017 footnote/clarification (not formal amendment).
**Pick: B.** ADR-0017's strictness model is unchanged semantically; only its scope of application widened. Stub language updated from "amended" to "footnoted" at chat-end. No revision header on ADR-0017 itself.

### P11 — Phase 06 forward-compat: instance-graphs carry source graph's `role`; metaedge vocab validation runs against them transparently.
**Pick: A.** Vocab transparency is the natural extension. File "instance-graph role mutability" as a future-work entry to be addressed in Phase 06 row refinement.

### P12 — Re-attach with vocab change: refuse unless `--accept-vocab-change` is passed.
**Pick: B** *(user override — original pick was A=auto-pass).* Explicit consent on vocab change. Requires fingerprint state tracking (Round 3 surfaces storage location, shape, and additive-vs-tightening scope).

### P13 — Strict-mode property validation runs eager at attach time alongside vocab-existence checks.
**Pick: A.** Mirror 05b/05c contract. Strict is opt-in; users who opt in want the full contract.

---

## Round 3 pushbacks (P14–P19) — LOCKED 2026-05-07

### P14 — Re-attach refusal scope: any vocab change (including pure additions) refuses.
**Pick: A** *(user override — original pick was B=tightening-only).* Simpler rule; max explicit-consent friction. Implementation: any non-zero diff between current and stored fingerprints triggers refusal.

### P15 — Fingerprint storage location: per-metagraph (alongside `schema_name` on metagraph state file).
**Pick: A.** Attach state lives on the metagraph (already true at `metagraph.py:296`); fingerprint joins it. **Consequence:** metagraph state file gains a new field, requiring its own version bump (locked in Round 4 P20).

### P16 — Fingerprint shape: per-type-name hash map.
**Pick: B.** Structure: `{ "MetaEdgeType": {"X": hash, "Y": hash}, "MetaHyperEdgeType": {...}, "IntergraphEdgeType": {...}, "IntergraphHyperEdgeType": {...} }`. Diff-friendly without duplicating the vocab. Refusal message names the offender directly.

### P17 — `--accept-vocab-change` rejected on first attach.
**Pick: B** *(user override — original pick was A=optional-noop).* Surfaces user confusion ("you weren't actually re-attaching"). Scripts wanting idempotency must check for prior attach themselves.

### P18 — `validate` verb signature: `--metagraph MG` only (use the metagraph's stored `schema_name`).
**Pick: B.** Avoids passing mismatched `--schema` values. Exit codes: 0 pass, 1 violation, 2 other (schema/metagraph not found). `--json` flag for structured.

### P19 — `validate` verb + re-attach: no interaction. Each verb owns its concern.
**Pick: A.** `validate` is read-only smoke test; `attach` always checks fingerprint independently. Redundant work for user is acceptable; documentation drift from coupling is not.

---

## Round 4 pushbacks (P20–P25) — LOCKED 2026-05-07

### P20 — Two state-file version bumps in 05d: metagraph v=3 → v=4 (adds fingerprint field), schema v=2 → v=3 (adds vocab arrays).
**Pick: A.** Respects 05b/05c separation (schema owns vocab; metagraph owns attach state). Stub at PHASE_MAP §5 must be amended to name both bumps.

### P21 — Fingerprint canonicalization: `sha256(json.dumps(asdict(type), sort_keys=True, default=...).encode()).hexdigest()`; per-type hash → top-level map per P16 B.
**Pick: A.** Stdlib only. `default` lambda must handle `frozenset` (sort to list) and `PropertyType` (str-Enum value); exact lambda locked in row text at chat-end.

### P22 — Re-attach refusal error: single-line scriptable. "Vocab fingerprint mismatch since last attach. Changed: <vocab>[<type> (added|modified|removed)], …. Pass `--accept-vocab-change` to confirm."
**Pick: A.** Testers grep for "fingerprint mismatch"; structured output already covered by `validate --json` (P25 A).

### P23 — ADR-0014 third amendment: two-section. Vocab additions (brief, formulaic) + fingerprint mechanism (detailed, new state-tracking pattern).
**Pick: C.** Matches information density; future readers don't reverse-engineer fingerprint from PHASE_MAP.

### P24 — File 2 future-work entries: (i) instance-graph role mutability (Phase 06); (ii) Phase 11 cross-vocab name-collision flagging.
**Pick: B.** Drop the granular smoke-verb entry; `validate` covers debug needs.

### P25 — `validate --json` shape: `{ "passed": bool, "schema_name": str, "metagraph_name": str, "violations": [{...full detail...}], "vocab_fingerprint_match": bool }`.
**Pick: A.** Field-level test assertions; vocab-fingerprint-match is the consent signal complementing `passed`.

---

## Round 5 pushbacks (P26–P29) — LOCKED 2026-05-07

### P26 — Field rename `vocab_fingerprint` → `last_attached_vocab_fingerprint`. Preserved after detach (separate lifecycle from `schema_name`).
**Pick: B.** Closes the detach-bypass bug. State machine: `schema_name` is set on attach / cleared on detach; `last_attached_vocab_fingerprint` is set on first successful attach / overwritten on subsequent successful attach / never cleared. Truly-first-attach (never attached) sees `last_attached_vocab_fingerprint=None` and rejects `--accept-vocab-change` per P17 B.

### P27 — Migration `_v3_to_v4`: compute fingerprint from current schema state if `schema_name` is set; null otherwise.
**Pick: A.** Existing 05c-attached metagraphs survive 05d migration transparently. Migration tool reads the schema file (already does for `_find_attached_metagraphs` reverse scan).

### P28 — `validate` on unattached metagraph: error with exit code 2.
**Pick: A.** Validating the unattached state is a user error. P18 exit-code surface stays tight (0/1/2).

### P29 — `--json` parity on `add-meta-edge-type` / `add-meta-hyperedge-type`.
**Pick: A.** Mechanical 05c precedent-following.

---

## Round 6 pushback (P30) — LOCKED 2026-05-07

### P30 — Versioned fingerprint envelope.
**Pick: B.** Field shape: `last_attached_vocab_fingerprint: { "fingerprint_version": 1, "algorithm": "sha256-jsonsort-v1", "hashes": { "MetaEdgeType": {"X": "<hex>"}, "MetaHyperEdgeType": {...}, "IntergraphEdgeType": {...}, "IntergraphHyperEdgeType": {...} } }`. On load, if `fingerprint_version` < current, treat as "needs recomputation" — re-attach proceeds without `--accept-vocab-change` for the version-bump scenario only. Future hash/canonicalization changes get a clean migration path.

**Bikeshed declined:** B1 (`validate` verb name) — locked as `validate`. B2 (`--accept-vocab-change` flag spelling) — locked as written.

**Well status: dry.** No further legitimate design pushbacks identified across exhaustive rescan.

---

## Final lock summary (2026-05-07)

**Total picks:** 7 meta-plan (M1–M7) + 30 design (P1–P30) = 37 numbered locks across 6 reanalysis rounds.
**User overrides:** 5 (P9 B, P12 B, P14 A, P17 B; P1 reinforced via primitive distinction clarification).
**Audit pre-resolution:** P3 audit RESOLVED 2026-05-07 (`type_name` already on both 05a dataclasses; no 05a-v2 supersession risk surface). Closed ~25% of original stub's risk surface.
**Bug found in earlier locks:** Detach-bypass surfaced in Round 5 (P26); closed by renaming field + decoupling lifecycle from `schema_name`.

### Files written / amended in chat

| File | Action | Purpose |
|------|--------|---------|
| `confirmation_docs/PHASE_05d_DESIGN_LOG.md` | created | Full pick log (M1–M7 + P1–P30) — this file. |
| `confirmation_docs/PHASE_MAP.md` §5 Phase 05d row | rewritten | Replaced stub with locked row text (10 sub-sections + ADR-0014 third amendment text + future-work pointers). |
| `confirmation_docs/PHASE_05d_NEXT_CHAT_PROMPT.md` | rewritten | Implementation-chat handoff prompt (mirrors 05c precedent). |
| `_source_backup/root/mindsos_future_plans.md` | extended | 2 new entries: (i) Instance-graph role mutability (Phase 06); (ii) Phase 11 cross-vocab name-collision flagging. |
| `~/.../memory/reference_mindsos_four_edge_primitives.md` | created | Canonical primitive distinction (load-bearing for future chats). |
| `~/.../memory/project_mindsos_phase_05d_design.md` | rewritten | Stub → full lock state. |
| `~/.../memory/MEMORY.md` | extended | Index entry for the new reference memory + updated 05d design entry. |

### Implementation-chat readiness checklist

- ☑ Row text fully locked (PHASE_MAP §5 lines 1762+ replaced).
- ☑ Field name `last_attached_vocab_fingerprint` consistent across all sections.
- ☑ ADR-0014 third amendment full text inline in row (Phase 38 transcription target).
- ☑ ADR-0017 reframed as footnote (P10 B), NOT formal amendment.
- ☑ Two state-file version bumps documented (P20 A).
- ☑ Fingerprint canonicalization lambda spec'd verbatim (P21 A).
- ☑ Versioned envelope shape spec'd verbatim (P30 B).
- ☑ CLI verb signatures + exit codes locked.
- ☑ Eager-attach contract reframed per M7 (vocab-gap, not field-absence).
- ☑ Future-work entries filed (P24 B).
- ☑ Memory updated (full-lock state + primitive distinction reference).
- ☑ Handoff prompt authored (8 docs + 14 memory files reading list).

### Implementation-chat hooks

The next chat starts with **Step 0 pre-implementation audit** — verify the four file:line citations from §F of the row text + state-version test files. If audit reveals contradictions with locked design, surface as P31+ pushback (not silent re-design).

Cascade unblock: Phase 06 dep is `03, 05d` per CASC-1 strict-sequential. Phase 06 row refinement opens after 05d ships.

**Chat status: design refinement COMPLETE. Awaiting tester to start implementation chat with `confirmation_docs/PHASE_05d_NEXT_CHAT_PROMPT.md` body.**

---

## Final row lock

*TBD at chat-end. Will replace the stub at PHASE_MAP §5 lines 1762–1797.*

---

## Future-work entries filed

*TBD; filed to `_source_backup/root/mindsos_future_plans.md` when surfaced.*

---

## Implementation-chat handoff

*Drafted at chat-end as `confirmation_docs/PHASE_05d_NEXT_CHAT_PROMPT.md` (mirrors 05c precedent).*
