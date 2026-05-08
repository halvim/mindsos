# Phase 05d Implementation Log

**Status:** In progress (chat dated 2026-05-07).
**Branch:** `phase-05d` off `origin/main` (commit `b2650c5` = `phase-05c-confirmed`).
**Tag on confirm:** `phase-05d-confirmed`.
**Confirmation doc target:** `confirmation_docs/PHASE_05d_CONFIRMED.md`.

This log captures the round-7 reanalysis pass that ran at the start of the implementation chat, plus the implementation-time decisions, bug ledger, and forward-compat notes. The rounds-1–6 pick log (M1–M7 + P1–P30) lives in `PHASE_05d_DESIGN_LOG.md` and remains the canonical historical record of the design-chat.

---

## §1 Round 7 pushback ledger (P31–P44) — implementation-chat reanalysis

User invitation 2026-05-07: "ADR decisions can be changed if it decided in this chat." Pushback well drained over two reanalysis passes (P31–P38 first pass; P39–P44 second pass after first-pass picks were applied). All eight P31–P38 picks accepted; all six P39–P44 picks accepted.

### P31 — Drop fingerprint-based explicit-consent re-attach mechanism. **Pick: A.**

**What it reverses:** P12 B → P14 A → P17 B → P26 B → P30 B chain locked the `last_attached_vocab_fingerprint` versioned-envelope state-tracking pattern + `--accept-vocab-change` consent flag.

**Why reverse:** The cumulative chain solved a problem eager-attach already covers. Vocab changes that BREAK existing metaedges already surface loudly via eager-attach validation; vocab changes that DON'T break anything are by definition harmless — refusing them on principle is friction without information. ADR-0014's Core stance is explicit: "no reasoning, no migrations, no concurrency control"; fingerprint-diff-as-consent-gate is a soft form of concurrency control.

**Consequences:** §F, §G(metagraph bump), §H(`--accept-vocab-change` flag), §I (re-attach-vocab-additive-refusal), and the entire ADR-0014 third amendment Section 2 disappear from the row. Saves ~150 LOC implementation, one state-file migration step, and the `vocab_fingerprint_match` field in `validate --json` (closed by P40).

### P32 — Add `--schema MS` opt-in to `validate` verb. **Pick: A.**

**What it reverses/extends:** P18 B locked `validate --metagraph MG` only (resolves schema via `MG.schema_name`). Added: optional `--schema MS` arg.

**Why:** The dry-run-against-local-schema-edits use case requires the explicit-schema path. P19 A's "verbs own their concerns" still holds: the `--schema` opt-in is read-only and doesn't mutate `MG.schema_name` or `MG.schema`.

### P33 — Strike P11 A (instance-graph forward-compat assertion). **Pick: A.**

**What it reverses:** P11 A claimed Phase 06 instance-graphs preserve source `role` transparently. Pre-binds Phase 06 without authority. Future-work entry under P24 B stays.

**Why:** 05d's vocab validation reads `Graph.role` from whichever Graph object is in the metagraph; instance-vs-base distinction belongs to Phase 06's row. The forward-compat assertion neither helps the implementation nor binds Phase 06 to the right answer.

### P34 — State-file bumps fragility. **Pick: A (closes via P31).**

**What it reverses/refines:** P20 A locked TWO independent state-file bumps (metagraph v=3 → v=4 + metagraph-schema v=2 → v=3) with cross-file dependency in `_v3_to_v4` (reads schema file to compute fingerprint). After P31 A drops the metagraph bump entirely, only the schema bump remains; no cross-file dependency.

### P38 — Cross-vocab same-name hint becomes informational only. **Pick: B.**

**What it refines:** P6 B locked an editorial recommendation ("you might want vocab segregation") in `UnknownTypeError` text. P2 A explicitly allows the same name across all four vocabs, so the recommendation second-guessed a legitimate operator choice.

**New text:** `"Name 'X' is registered in IntergraphEdgeType but not in MetaEdgeType."` Information without judgment.

### P39 — Empty-vocab semantics on eager-attach + add + validate need explicit clauses. **Pick: A.**

**What it surfaces:** Without an explicit clause in §C/§D, the implementation chat could read "walks metaedges + metahyperedges" as unconditional `require_meta_edge_type` — which would break every 05c-migrated metagraph (their schemas have empty `meta_edge_types: []` after `_v2_to_v3`; their metaedges have valid `type_name` but no vocab entries).

**Locked behavior (mirrors 05b/05c "Pushback 24-hybrid" precedent for `IntergraphEdgeType`):**
- Empty `MetaEdgeType` vocab + non-strict + existing metaedges on eager-attach → **skip walk silently**.
- Empty vocab + strict + existing metaedges on eager-attach → **fail** (vocab-existence is the strict invariant).
- Empty vocab + `add_metaedge` → **raise UnknownTypeError regardless of strict** (precedent asymmetry — operator workaround documented in §C).
- `validate` verb mirrors eager-attach (non-strict + empty pass; strict + empty fail).

### P40 — Drop `vocab_fingerprint_match` from `validate --json` shape. **Pick: A.**

**What it reverses:** P25 A locked `{ "passed", "schema_name", "metagraph_name", "violations", "vocab_fingerprint_match" }`. After P31 A drops fingerprint mechanism, `vocab_fingerprint_match` has no input source.

**New shape:** `{ "passed": bool, "schema_name": str, "metagraph_name": str, "violations": [...] }`.

### P41 — Split `validate` exit code 2 into 2/3. **Pick: A.**

**What it refines:** P18 B / P25 A bucketed "schema not found", "metagraph not found", and "no schema attached" all into exit 2. After P32 A's `--schema` opt-in, "no schema attached" is recoverable (operator passes `--schema MS`) — different ergonomic from "metagraph doesn't exist" (typo).

**New codes:** 0 pass; 1 violation; 2 resource-not-found (schema or metagraph file missing); 3 no-usable-schema (neither attached nor `--schema` supplied).

### P42 — Lightweight ADR pointer (replaces P35 A and P36 A). **Pick: C.**

**What it reverses:** P35 A and P36 A both preferred inline amendments to ADR-0014 / ADR-0017 in 05d's PR. Audit found 05b and 05c amendments are NOT on disk in those ADR files (they're deferred to Phase 38 per shipped precedent). Inline amendments would catch up 05b + 05c retroactively (scope creep) or break the precedent unilaterally.

**Locked behavior:** Add a single line at the top of each ADR file: "*See `confirmation_docs/PHASE_MAP.md` §5 for amendments through Phase 05d.*" Closes the filename-search discoverability gap; full transcription stays Phase 38. ~4 LOC across two files.

### P43 — Step 0 audit correction after P31 A. **Info, not a pushback.**

The Step 0 audit flagged 11 hard-coded `_state_version` sites in `tests/phase_05c/test_state_v3_round_trip.py`. After P31 A removes the metagraph state-file bump, only 4 schema-side sites need migration to dynamic `ms_migrations.CURRENT_VERSION`:

| Line | Status under P31 A |
|---|---|
| 16, 36, 51, 72, 75-77, 150, 164 | **survives** — metagraph stays v=3 |
| 19, 89, 112, 115-117 | **breaks** — schema bumps v=2 → v=3; needs migration |

### P44 — Mirror actual 05b validation order (replaces P5 A and P37 A). **Pick: A.**

**What it reverses:** P5 A claimed `add_metaedge` validation order should mirror 05b precedent with cypher regex FIRST (steps 1-7: regex → containment → source≠target → vocab → properties). Verification at `metagraph.py:735-798` shows the actual 05b order is INVERTED: containment first; cypher regex deferred to `__post_init__` (fires at construction step 12). The P5 A claim "Mirrors 05b IntergraphEdge precedent" was factually wrong.

**Locked behavior (real 05b mirror):** containment → source≠target → properties bag → (if schema) require_*_type → validate_* → validate_*_properties (strict only) → register-and-construct (regex via `__post_init__`). Behavior on multiply-broken inputs unchanged from today's `add_metaedge`.

---

## §2 Implementation order (post-row-update)

  1. Vocab dataclasses (`MetaEdgeType`, `MetaHyperEdgeType`) in `mindsos_core/schema/types.py`.
  2. `MetagraphSchema` extension methods (`add_meta_edge_type`, `require_meta_edge_type`, `validate_meta_edge`, `validate_meta_edge_properties`, plus symmetric `*_meta_hyperedge_*`); cross-vocab informational hint.
  3. `Metagraph.attach_schema` eager-walk extension; empty-vocab pass-silently rule.
  4. `Metagraph.add_metaedge` / `add_metahyperedge` validation wiring (real 05b order).
  5. Schema state-file v=2 → v=3 migration (`_v2_to_v3`); state serializer/loader plumbed for the two new arrays.
  6. CLI: `add-meta-edge-type`, `add-meta-hyperedge-type` verbs (with schema-mutation footgun warning).
  7. CLI: `validate` verb with `--schema` opt-in; exit codes 0/1/2/3; `--json` shape per P40 A.
  8. ADR pointer line in `0014-layer-boundary-core-only.md` and `0017-schema-strictness-opt-in.md`.
  9. Tests in `tests/phase_05d/`; migration of 4 hard-coded schema-side `_state_version` constants in `tests/phase_05c/test_state_v3_round_trip.py`.
  10. `notes-phase-05d.md` tester recipe; Dockerfile comment bump 05c → 05d; CHANGELOG entry; confirm-phase preflight.
  11. (Tester) in-container test run; iterate to green.
  12. PR + squash-merge + tag + Release CI.

---

## §3 Bug ledger

### Sandbox verification at code-time

Mac-side sandbox (Python 3.10, no FalkorDB) executed all non-subprocess
tests cleanly:

  - `tests/phase_05d/` (92 tests): **all pass**.
  - `tests/phase_05a + 05b + 05c + 05d` non-CLI subset (419 tests):
    **all pass** (CLI subprocess tests require Python 3.12 / `tomllib`
    in the test container; they are deselected in the sandbox).

Cumulative in-container baseline projection: ≥ 901 (05c baseline) +
~92 added in `tests/phase_05d/`. Tester records actual count after the
canonical in-container run.

### In-container bugs

*(Filled by tester during the canonical in-container run.)*

---

## §4 Implementation pushbacks (P45+)

### P45 — P39 A's "mirrors 05b/05c Pushback 24-hybrid" claim is imprecise; behavior is a deliberate divergence, not a precedent mirror.

**What I found at code-time.** 05b/05c `attach_schema` walks every existing intergraph_edge unconditionally and lets `schema.require_intergraph_edge_type(edge.type_name)` raise. The 05b docstring's "Pushback 24-hybrid: empty MetagraphSchema (no IntergraphEdgeType registered): in non-strict mode, succeed silently (no edges to validate against vocab)" describes the case where **the metagraph has zero intergraph_edges** — the loop body simply doesn't run. The case "empty vocab + existing edges + non-strict" was never tested in 05b/05c and IS NOT silent — it raises `UnknownTypeError` from `require_*_type` on the first iteration.

**What 05d ships.** P39 A locks an explicit empty-vocab guard on the new metaedge / metahyperedge walks: `if schema._meta_edge_types or schema.strict` skips the walk when both conditions are false. This is **deliberately different** from 05b/05c IntergraphEdge behavior — the latter has no guard. The asymmetry is justified by the 05c-migration scenario: 05c-shipped metagraphs may have metaedges, and 05d-migrated 05c schemas have empty `meta_edge_types: []`. Without the guard, every 05c-migrated metagraph would refuse re-attach even though nothing was broken.

**Action:** Row §D and CHANGELOG entry phrased as "mirrors 05b/05c Pushback 24-hybrid precedent" — that phrasing is mildly imprecise (it's an extension, not a strict mirror). No action on the row text (the behavior is correct; a future audit may sharpen the phrasing). Leaving this here so a Phase 06+ reader doesn't try to "fix" the asymmetry by removing the guard.

---

## §5 Forward-compat notes for Phase 06+

*(Filled at chat-end summarizing items that affect downstream phases.)*
