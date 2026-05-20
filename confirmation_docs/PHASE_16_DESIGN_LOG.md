# Phase 16 — Design Log

**Phase:** 16 — L2 admin similarity surface (read-only).
**Branch:** `phase-16` off `origin/main` tip `ec94565` (Phase 15b design-only squash).
**Chat date:** 2026-05-20.
**Tag on confirm:** `phase-16-confirmed` AFTER squash-merge per
`feedback_release_tag_after_squash_merge_only.md`.

---

## 0. Scope at chat-open

### Handoff inheritance (PHASE_16_NEXT_CHAT_PROMPT.md as drafted by Phase 15b)

The handoff asked Phase 16 to ship:

* `mindsos_admin/promotion.py` with `propose_for_promotion(...)` (ADR-0118
  pivot name) implementing the **pre-pivot** mechanics of ADR-0049
  (similarity gate) + ADR-0053 (per-candidate undo-stack atomicity) +
  ADR-0055 (crude similarity heuristic: exact 1.0 + prefix 0.7,
  threshold 0.5) + ADR-0056 (input-order preservation) +
  ADR-0052 (content-hash `report_id`).
* `list_candidates(mg, *, role) -> list[CandidateRef]`.
* `PromotionResult` + `SimilarityReport` + `CandidateRef` dataclasses.
* CLI verbs `mindsos admin promote {list, similarity, propose}`.
* Pre-pivot scope only — Phase 24 owns the full ADR-0118 pivot.
* Forward-cited from Phase 15a PB-3-i Round 4 + ADR-0140 §amendment-1
  §Decision §2 supersession: location is `mindsos_admin/`, not
  `mindsos_server/`.

### Pre-impl probe finding (mirrors Phase 15b discipline)

Per `feedback_pre_impl_probe_check_existing_modules.md`:

```
grep -rnE "propose_for_promotion|SimilarityReport|CandidateRef|PromotionResult" \
    mindsos_admin/ mindsos_knowledge/ mindsos_server/ mindsos_core/ \
    mindsos_instances/ mindsos_capacity/

mindsos_admin/__init__.py:33: forward-cite docstring ("Phase 16 will add...")
mindsos_core/persistence/wal.py:16: example WAL kind string
                                    ("kind=\"kl.propose_for_promotion\"")
                                    in module docstring — non-functional
                                    illustration only.

ls mindsos_admin/promotion.py 2>/dev/null
(not yet shipped)
```

No prior code to reframe. Probe was clean. The architectural reframe in
this chat is driven by ADR-cross-reading, not by stale module discovery
(Phase 15b's reframe driver).

### What ADR-cross-reading surfaced

Beyond the handoff-cited ADRs (0010, 0049, 0052, 0053, 0055, 0056,
0118, 0140), this chat read the broader promotion-related set: ADRs
0006, 0009, 0050, 0051, 0054, 0057, 0137, 0138, 0141, 0142, 0143, 0144.

The reading surfaced an **architectural contradiction** in the handoff
scope: PHASE_MAP §16 mixed three ADR contracts that are not jointly
consistent:

| Pre-pivot ADR | Superseding ADR (Proposed) | Conflict at Phase 16 |
|---|---|---|
| ADR-0049 (freshness gate on `promote()`) | ADR-0144 (similarity moves to release-ship audit gate) | Gate at the wrong point |
| ADR-0053 (in-memory undo-stack atomicity) | ADR-0118 (SQLite-tx + `MetagraphSnapshot` per-user at release-ship) | Atomicity model already retired |
| ADR-0055 (exact+prefix, 0.5 threshold) | ADR-0144 §Heuristic (Lev + Jaccard×2, 0.85 threshold; **calls 0055 "Pareto-dominated"**) | Heuristic Phase 24 deletes |
| `kl.promote()` (the ADR-0049 gate's callee) | ADR-0141 (DELETE `KL.promote()`; `propose_for_promotion` is canonical) | No callee at Phase 16 — `pending_global` doesn't exist yet |
| `PromotionResult` | ADR-0141 (replaces with `PromotionRequestResult`) | A dataclass Phase 24 throws away |

The handoff framed this as "Phase 16 ships pre-pivot mechanics; Phase 24
ships the full pivot." But there is no clean pre-pivot landing zone: the
function name is pivot-only; the home is post-amendment; the gate's
callee (`KL.promote`) is slated for deletion; and the heuristic is
explicitly Pareto-dominated. Building 0049/0053/0055 mechanics at 16
ships code Phase 24 deletes.

The chat then iterated through 5 rounds of pushbacks closing on a
**reframe** mirroring Phase 15b's reframe shape (pre-impl probe → narrow
scope → defer the wrong-contract surface).

---

## 1. Design pushbacks (5 rounds, all user-agreed)

### Round 1 — load-bearing reframe (Pushback 1..4)

#### PB-1 — API surface + entry-point

Cited: PHASE_MAP §16, ADR-0140 §amendment-1, ADR-0118, ADR-0141.

Four considered:

* (1a) Literal PHASE_MAP §16 — ship `propose_for_promotion(...)` writing
  directly to Global under pivot name; mechanics pre-pivot.
* (1b) Rename to `promote_to_global` under same home; mechanics
  pre-pivot.
* **(1c) Read-only surface only at 16; defer mutating entry-point to 24.**
  Ship `similarity.py` with `compute_similarity` + `list_candidates` +
  `SimilarityReport` + `CandidateRef`. Reserve `promotion.py` for
  Phase 24 (where ADR-0118 + ADR-0141 land together). Amend Phase 15a
  PB-19 forward-cite the same way Phase 15b amended the scanner
  forward-cite.
* (1d) Reframe 16 to DESIGN-ONLY (like 15b). Ratify ADR-0144 +
  supersede 0049/0053/0055/0056; flip pivot ADRs 0118/0141 to
  Accepted. No code. Rejected — pivot ADRs aren't ready to flip
  without Phase 24's implementation evidence.

**Lock: PB-1c.** Mirror Phase 15b's reframe shape (pre-impl-probe-driven
scope narrow). Zero code-rip-out debt at Phase 24; admin similarity
heuristic ships once, in its final shape. PHASE_MAP §16 row needs
rewrite (mirroring Phase 15b's design-only reframe but as
code-narrowed; Phase 23 + 24 rows also touched).

#### PB-2 — Similarity heuristic algorithm

Cited: ADR-0055 vs ADR-0144 §Heuristic.

Three considered:

* (2a) Ship ADR-0055 verbatim (exact 1.0 + prefix 0.7, threshold 0.5).
* **(2b) Ship ADR-0144's spec** (Levenshtein + structural Jaccard + reference
  Jaccard, weights 0.4/0.4/0.2, threshold 0.85). Supersede 0055 via
  amendment.
* (2c) Protocol (`SimilarityScorer`) with both `CrudeScorer` (0055) +
  `WeightedScorer` (0144) selectable.

**Lock: PB-2b.** ADR-0055 was a deliberate placeholder; ADR-0144 is the
final algorithm. No value in shipping the placeholder when the final
spec is already drafted. `report_id` content-hash (ADR-0052) is
orthogonal and stays.

#### PB-3 — Dataclass + module homes

Cited: Phase 15a PB-20 (conservative day-one layout).

Three considered:

* (3a) Everything in `mindsos_admin/promotion.py`. Rejected — under
  PB-1c, `promotion.py` doesn't ship at 16.
* **(3b) `mindsos_admin/similarity.py`** for the read surface; reserve
  `promotion.py` for Phase 24.
* (3c) `mindsos_admin/types.py` for shared dataclasses + `similarity.py`
  for the function. Rejected — skinny `types.py` is the ceremony noise
  Phase 15a PB-20 explicitly avoided.

**Lock: PB-3b.** Mirrors Phase 15a's `bootstrap.py` (orchestration) vs
`importers/` (mechanics) split.

#### PB-4 — PHASE_MAP §23 + §24 cascade

PHASE_MAP §23 "Server: promotion lock + MetagraphSnapshot rollback" has
deps 10, 16, 19. Phase 23's callee was Phase 16's
`propose_for_promotion`. Under PB-1c, that entry-point defers to 24.

Three considered:

* (4a) Phase 23 keeps scope; locks/snapshot infrastructure ship without
  a promotion caller.
* (4b) Merge Phase 23 into Phase 24. Rejected — Phase 24 already net-new
  with 4 proposers + RELEASE_SHIP_LOCK + release manifest + lazy
  migration.
* **(4c) Phase 23 narrows to MetagraphSnapshot infrastructure only.**
  The lock moves to 24 (where the consumer lives). Snapshot stays at 23
  (ADR-0129 anchor). PHASE_MAP §23 row rewrite; ADR-0129 anchors it.

**Lock: PB-4c.** Phase 23 ships a useful, testable primitive (snapshot +
rollback context manager); doesn't depend on a consumer; Phase 24 picks
it up.

### Round 2 — sub-design (Pushback A..E)

#### PB-A — ADR-0144 partial-flip mechanism

ADR-0144 is one ADR but two decisions: §Heuristic + §Placement. Phase 16
ships the algorithm; Phase 24 ships the placement.

Three considered:

* (A1) Single Status, stay Proposed (16 ships code under Proposed ADR).
* **(A2) ADR-0144 §amendment-1 (Phase 16) carves out placement.**
  §Heuristic flips Accepted; §Placement stays Proposed.
* (A3) Split ADR-0144 into two ADRs. Rejected — breaks
  immutable-ADR convention.

**Lock: PB-A2.** Same mechanism Phase 15a / 15b used for ADR-0042 /
0140 / 0150 amendments. ADR-0055 supersedes-by-amendment to ADR-0144
§Heuristic (one-liner amendment in 0055 pointing at 0144's algorithm).

#### PB-B — Per-role vs generic structural scorer

ADR-0144 lists Jaccard features as "frame-element set + synonym set +
parent-class set" — FrameNet/OEWN/DOLCE-specific.

Three considered:

* (B1) Generic property-bag Jaccard. Rejected — noise; not ADR-0144 spec.
* **(B2) Per-role scorer modules** (`_extract_ontology` / `_extract_lexicon`
  / `_extract_concepts`); generic combiner.
* (B3) Generic core + role-overrideable feature extractor. Rejected —
  premature abstraction.

**Lock: PB-B2 with bounded scope.** Three extractors (ontology /
lexicon / concepts) match the three Phase 15a importers; alignment /
promoted-pipelines / task-patterns / problem-trace return empty
features at 16 (no candidates exist in those roles yet — empty-pair
exclusion under PB-G2 handles it).

#### PB-C — `list_candidates` filter + signature

PHASE_MAP §16 cites `list_candidates(mg, *, role) -> list[CandidateRef]`.
Candidate criterion was undefined.

Three considered:

* (C1) All same-role nodes. Rejected — returns the entire Global.
* **(C2) Exclude PROMOTED breadcrumbs (ADR-0051 `ref_type = "PROMOTED"`)
  + caller-provided `where` predicate.**
* (C3) Caller-provided predicate only. Rejected — barely earns its name.

**Lock: PB-C2 + a `where` keyword.** Default behaviour returns same-role
nodes minus PROMOTED. Override exposes the criterion to Phase 24
(`source_user_id`-derived predicates).

#### PB-D — Dataclass shapes Phase 24 must inherit

Three considered:

* (D1) Minimal now, extend at 24. Rejected — Phase 24 has to re-derive
  classification.
* **(D2) Future-proofed shape.** `CandidateRef(node_id, role, node_type,
  source_user_id=None)`. `Finding(candidate_id, candidate_node_type,
  matched_id, matched_node_type, matched_is_candidate, score, breakdown,
  classification)`. `SimilarityReport(report_id, findings,
  threshold_blocking, threshold_review)`. All `frozen=True`.
* (D3) Frozen dataclass + open `extra: dict`. Rejected — anti-pattern.

**Lock: PB-D2** with `source_metagraph_id` omitted at 16 (one mg per
call; trivially added at 24 if needed).

#### PB-E — PHASE_MAP §23 + §24 cascade

(Locked as PB-4c above. Recorded here for cross-reference.)

### Round 3 — finer details (Pushback F..I)

#### PB-F — `metagraph_content_hash` scope

ADR-0052 is silent on what counts as "the metagraph". Determines when
`report_id` invalidates.

Four considered:

* (F1) Hash entire Metagraph. Rejected — unrelated mutation invalidates
  in-flight `report_id`.
* **(F2) Hash role-graph being scored** (one graph per call).
* (F3) Hash candidate-subgraph + matched-target subgraph. Rejected —
  over-engineered for Phase 16.
* (F4) Hash candidate-ids + role-graph nodes-of-this-NodeType. Rejected —
  schema lookup cost without payoff.

**Lock: PB-F2 with ADR-0052 §amendment-1.** Role-graph scope; WAL +
tombstones excluded by construction (different graph in the metagraph;
not visited).

#### PB-G — Per-role extractor return shape

ADR-0144 §Heuristic: "frame-element set + synonym set + parent-class
set". Per-role mapping: DOLCE has only parents; OEWN has synonyms +
hypernyms; FrameNet has frame-elements + parents.

Three considered:

* (G1) One flat string-set per extractor. Rejected — loses traceability.
* **(G2) Three named sets per extractor**; combiner runs three Jaccards
  and weights/averages them; empty-pair exclusion at inner Jaccard.
* (G3) Three sets, weighted average over non-empty pairs only. Rejected —
  per-role weights drift from ADR-0144 spec.

**Lock: PB-G2 with ADR-0144 §amendment-2.** Combiner rule: if both
candidate-set and matched-set are empty for a sub-feature, that
sub-feature is EXCLUDED from the structural Jaccard mean (not 0/0 NaN).
ADR-0144 §amendment-2 documents the exclusion rule.

#### PB-H — Finding output: combiner + tie-break + thresholds

Three considered:

* Bundle I — Top-1 + hard-coded thresholds + lex tie-break.
* **Bundle II — All-above-review + constructor-param thresholds + lex
  tie-break.**
* Bundle III — Top-K=5 + constructor-param thresholds + lex tie-break.

**Lock: Bundle II.** Phase 24's audit gate needs every candidate-target
pair above review threshold (per ADR-0144 §Placement). Hiding sub-top
matches at Phase 16 forces Phase 24 to re-implement discovery.
Thresholds as constructor parameters with ADR-0144 defaults
(`threshold_blocking=0.85`, `threshold_review=0.5`). report_id includes
the thresholds in the content hash.

#### PB-I — CLI Metagraph source

No state-file write surface at 16 (Phase 26 owns).

Four considered:

* **(I1) `--state-file <path>` only.** Read Phase 09 state-file.
* (I2) `--falkordb-graph <metagraph-id>` only. Rejected — couples CLI
  to FalkorDB sidecar.
* (I3) `--fixture <path>` only. Rejected — doesn't help admin scanning a
  real populated Global.
* (I4) All three with auto-detect. Rejected — YAGNI.

**Lock: PB-I1.** State-file path is the durable contract; Phase 26's
write surface lands later but the read surface (Phase 09) ships. For
dev iteration, an admin can build a Metagraph in Python and dump a
state-file. Phase 26 ships FalkorDB-source CLI alongside state-file
write.

### Round 4 — consumer contracts (Pushback J..M)

#### PB-J — NodeType discrimination within `role`

Phase 13's schemas declare multiple NodeTypes per role. `list_candidates`
and `compute_similarity` both need a rule.

Three considered:

* (J1) Role-wide, all NodeTypes. Findings span types.
* (J2) NodeType-required keyword. Surgical but verbose.
* **(J3) Role-wide default + `node_type` optional filter.**

**Lock: PB-J3.** Default returns role-wide; `Finding` carries
`candidate_node_type` + `matched_node_type` (always equal under
same-type pairing). `compute_similarity` partitions internally by
NodeType; one combined `SimilarityReport` per call. Phase 24's audit
gate can pass `node_type=` for per-NodeType audit rows.

#### PB-K — Phase 24 reuse signature: `target_mg` keyword

Phase 16's signature is intra-mg; Phase 24's audit gate is cross-mg
(pending vs canonical Global).

Three considered:

* (K1) Intra-mg only; Phase 24 merges via view-Metagraph. Rejected —
  view-Metagraph is non-trivial machinery.
* **(K2) `target_mg` keyword defaulting to `mg`.** When `target_mg is
  None`, intra-mg; otherwise cross-mg.
* (K3) Two functions. Rejected — Phase 24 ships a near-clone.

**Lock: PB-K2.** Additive, default-preserving, single function.
report_id input set extends to `(mg_role_hash, target_mg_role_hash)`
when cross-mg; symmetric when intra-mg.

#### PB-L — Outer-mean re-weighting under empty-pair exclusion

PB-G2 locked the rule for the INNER structural-Jaccard. The OUTER
weighted-mean is `0.4·Lev + 0.4·Struct + 0.2·Ref`. Open: when one of
the three outer components is undefined, what happens?

Three considered:

* **(L1) Same rule as inner: drop undefined; renormalize.**
* (L2) Treat undefined as 0.0 contribution. Rejected — score artificially
  suppressed.
* (L3) Treat undefined as 1.0. Rejected — arbitrary; misleading.

**Lock: PB-L1.** ADR-0144 §amendment-2 wording extends to both inner and
outer means: "exclude undefined components; renormalize remaining
weights to sum 1.0; if all three components undefined, raise
`EmptyComparisonError`." `EmptyComparisonError` ships at
`mindsos_admin.exceptions`.

#### PB-M — Self + inter-candidate handling in `findings`

Three considered:

* (M1) Self excluded; inter-candidate excluded.
* **(M2) Self excluded; inter-candidate included** with
  `Finding.matched_is_candidate: bool` flag.
* (M3) Self excluded; inter-candidate in separate field.

**Lock: PB-M2.** Single findings list; `Finding` carries
`matched_is_candidate: bool`. Phase 24's audit-gate review of
pending-vs-pending duplicates uses the same surface as
pending-vs-canonical.

### Round 5 — implementation locks (Pushback S..V)

#### PB-S — Read-surface type: `Metagraph` vs `MetagraphView`

ADR-0010 says L2 read API is `MetagraphView`. Admin is L2-adjacent.

Three considered:

* **(S1) Take `Metagraph` (raw L1).** Admin reads directly.
* (S2) Take `MetagraphView`. Rejected — caller ceremony.
* (S3) Union. Rejected — dual code path.

**Lock: PB-S1.** Phase 15a's `bootstrap_global` returns `Metagraph`;
mirror that. Phase 17 role-version routing applies inside KL's
cognitive-loop reads, not inside admin similarity scans.

#### PB-T — Score / threshold FP precision

Test determinism + cross-machine reproducibility require explicit
precision.

Three considered:

* (T1) No rounding; trust IEEE-754. Rejected — refactor-fragile.
* **(T2) Round `Finding.score` to 6 decimals; canonicalize thresholds
  to 6 decimals before hashing.**
* (T3) `Decimal` throughout. Rejected — premature precision.

**Lock: PB-T2.** One rule: `round(x, 6)` applied to (i) `Finding.score`,
(ii) every numeric input to `report_id` hash (thresholds + sub-scores
that enter the hash). Threshold floats canonicalized to `f"{x:.6f}"`
before joining into the hash input string. ADR-0052 §amendment-1
covers.

#### PB-U — ADR-0049 / 0053 / 0056 status under reframe

Three ADRs describe code Phase 16 doesn't ship and Phase 24 deletes.

Three considered:

* (U1) Leave Accepted; Phase 24 supersedes when `KL.promote()`
  deletes. Convention-correct but reader-confusing.
* (U2) Preemptive Supersede at Phase 16's ship. Rejected — supersession
  by a Proposed ADR (0141) is logically inverted.
* **(U3) Status amendment via §amendment-1 on each ADR** —
  documentary; status untouched; points at ADR-0141.

**Lock: PB-U3.** Honors the "Status flips when code flips" convention;
documents the divergence visibly. Three amendments at Phase 16
(0049, 0053, 0056) + ADR-0055 §amendment-1 = 4 ADR touches. Plus
ADR-0052 §amendment-1 + ADR-0144 §amendment-1 + §amendment-2 = 7 ADR
touches total.

#### PB-V — Fixture strategy

Three considered:

* (V1) Hand-crafted in test code only. CLI tests need state-file at
  setup time.
* **(V2) Hand-crafted in test code + one shared synthetic state-file**
  at `tests/phase_16/fixtures/similarity_corpus.state-file`. Generator
  script + sentinel.
* (V3) Reuse Phase 15a synthetic fixtures. Rejected — conflates
  importer behavior with similarity behavior.

**Lock: PB-V2.** Unit tests build in-process; CLI tests use shared
corpus; `test_corpus_regenerates_deterministically.py` is the
generator-vs-corpus sentinel.

---

## 2. What ships in Phase 16 (final scope)

### Code (NEW in `mindsos_admin/`)

* **`mindsos_admin/similarity.py`** — main public surface (~500 LOC):
  * `CandidateRef` (frozen dataclass): `node_id`, `role`, `node_type`,
    `source_user_id` (optional, defaults None).
  * `Finding` (frozen dataclass): `candidate_id`, `candidate_node_type`,
    `matched_id`, `matched_node_type`, `matched_is_candidate`, `score`,
    `breakdown` (dict), `classification` (`"blocking" | "review"`).
  * `SimilarityReport` (frozen dataclass): `report_id`, `findings`
    (tuple), `threshold_blocking`, `threshold_review`.
  * `list_candidates(mg, *, role, node_type=None, where=None)` —
    PB-C2 + PB-J3.
  * `compute_similarity(mg, candidates, *, role, target_mg=None,
    threshold_blocking=0.85, threshold_review=0.5)` — PB-K2.
  * In-house Levenshtein DP (`_levenshtein_distance` + `_levenshtein_score`).
  * Per-role feature extractors: `_extract_ontology`, `_extract_lexicon`,
    `_extract_concepts` (PB-B2). Returns `(frame_elements, synonyms,
    parents)` triple per node.
  * Reference Jaccard reads UNION of `ref:<role>` properties + XRef rows
    (per ADR-0142 read-fallback contract).
  * Weighted-mean combiner with empty-pair exclusion + renormalization
    at BOTH inner Jaccard AND outer weighted-mean (PB-G2 + PB-L1).
  * All numeric outputs rounded to 6 decimals (PB-T2).
* **`mindsos_admin/_content_hash.py`** — Phase 24-reusable helper:
  * `metagraph_content_hash(mg, *, role)` per ADR-0052 §amendment-1
    (role-scoped). Canonical JSON: sorted graphs → sorted nodes/edges
    → sorted properties. Frozenset → sorted tuple, datetime → ISO 8601,
    UUID4 → str. Excludes WAL + tombstones + soft-deleted nodes (per
    Phase 10 `is_deprecated` filter; ADR-0133).
* **`mindsos_admin/exceptions.py`** — NEW module:
  * `EmptyComparisonError(Exception)` — raised when all three weighted
    similarity components (Lev/Struct/Ref) undefined for a
    candidate-matched pair per ADR-0144 §amendment-2.

### `mindsos_admin/__init__.py` re-exports (added)

* `compute_similarity`, `list_candidates`
* `SimilarityReport`, `CandidateRef`, `Finding`
* `EmptyComparisonError`
* `metagraph_content_hash` (public — Phase 24 audit gate consumes)
* `__version__` bumped to `0.0.0+phase16`.

### CLI

* **`mindsos admin promote list`** — read state-file → Metagraph → call
  `list_candidates(...)` → print text or JSON.
* **`mindsos admin promote similarity`** — read state-file → Metagraph →
  call `list_candidates` + `compute_similarity(...)` → print text or
  JSON (`SimilarityReport.to_dict()`).
* Flags: `--state-file PATH` (required), `--role NAME` (required),
  `--node-type NAME` (optional), `--threshold-blocking FLOAT`
  (similarity only, default 0.85), `--threshold-review FLOAT`
  (similarity only, default 0.5), `--json` (default text output).
* NO `propose` verb at Phase 16 (deferred to Phase 24).

### Tests (`tests/phase_16/`)

* `test_levenshtein.py` — DP correctness; normalization; symmetry;
  empty-string edge cases.
* `test_content_hash.py` — determinism; role-scope invariance under
  unrelated mutation; 6-decimal canonicalization.
* `test_extractors.py` — per-role feature extraction (3 extractors;
  fixture-based).
* `test_compute_similarity.py` — J3 multi-NodeType partition; K2
  cross-mg `target_mg`; L1 renormalization on undefined components;
  M2 inter-candidate findings; T2 6-decimal rounding;
  `EmptyComparisonError`.
* `test_list_candidates.py` — default (role-wide minus PROMOTED);
  `node_type` filter; `where` predicate; deterministic ordering.
* `test_cli_promote.py` — text + `--json` output for both verbs.
* `test_adr_amendment_sentinels.py` — 7 ADR amendments (0049, 0052,
  0053, 0055, 0056, 0144 × 2).
* `test_import_isolation.py` — admin/similarity has no `mindsos_server`
  / `mindsos_cli` imports (per ADR-0010).
* `fixtures/build_corpus.py` — deterministic generator.
* `fixtures/similarity_corpus.state-file` — checked-in shared CLI
  fixture.
* `test_corpus_regenerates_deterministically.py` — generator-vs-corpus
  sentinel.

### ADR amendments (parent project tree per Model C)

7 amendments at Phase 16's ship:

1. **ADR-0049 §amendment-1 (Phase 16 ship)** — documentary; status
   untouched; points at ADR-0141 (Proposed). Body: "Phase 16 ships
   a read-only `compute_similarity` surface at `mindsos_admin/similarity.py`;
   the gate-on-`promote()` mechanism in §Decision does NOT ship at 16.
   `KL.promote()` deletion (and this ADR's Status flip to Superseded)
   await ADR-0141 Accept at Phase 24."
2. **ADR-0052 §amendment-1 (Phase 16 ship)** — role-scoped hash +
   6-decimal canonicalization. Body: "Per Phase 16 PB-F2: hash scope is
   the role-graph being scored; cross-role mutation does not invalidate.
   Per Phase 16 PB-T2: numeric inputs are canonicalized via
   `f'{x:.6f}'` before joining into the hash input; outputs
   (`Finding.score`) are `round(x, 6)`. Hash input set extends to
   `(mg_role_hash, target_mg_role_hash)` when `compute_similarity`'s
   `target_mg` kwarg is given (PB-K2)."
3. **ADR-0053 §amendment-1 (Phase 16 ship)** — documentary; points at
   ADR-0141.
4. **ADR-0055 §amendment-1 (Phase 16 ship)** — supersedes-by-amendment
   to ADR-0144 §Heuristic. Body: "The crude exact+prefix heuristic
   described in §Decision is superseded by ADR-0144 §Heuristic
   (Levenshtein + structural Jaccard + reference Jaccard, weights
   0.4/0.4/0.2, threshold 0.85). This ADR's status remains Accepted
   for historical record; the heuristic it describes does not ship at
   Phase 16."
5. **ADR-0056 §amendment-1 (Phase 16 ship)** — documentary; points at
   ADR-0141.
6. **ADR-0144 §amendment-1 (Phase 16 ship)** — §Heuristic Accepted at
   Phase 16; §Placement stays Proposed (Phase 24 ships the
   release-ship audit gate consumer).
7. **ADR-0144 §amendment-2 (Phase 16 ship)** — empty-pair exclusion at
   inner Jaccard AND outer weighted-mean; `EmptyComparisonError` raised
   when all three components undefined.

### PHASE_MAP edits

* **§Phase 16 row** — full rewrite. Net-new code = Yes
  (`mindsos_admin/similarity.py` + `_content_hash.py` + `exceptions.py`).
  Scope = read-only similarity surface. Mutation entry-point
  (`propose_for_promotion` + per-user transactional model) deferred
  to §Phase 24.
* **§Phase 23 row** — narrows to MetagraphSnapshot rollback infrastructure
  only (per PB-4c). Lock consumer moves to §Phase 24.
* **§Phase 24 row** — absorbs the promotion lock + `propose_for_promotion`
  entry-point alongside RELEASE_SHIP_LOCK + release manifest + lazy
  migration.

### NOT in Phase 16 scope (per pushback locks)

* `mindsos_admin/promotion.py` (`propose_for_promotion()` entry-point) —
  Phase 24.
* `PromotionResult` / `PromotionRequestResult` dataclass — Phase 24.
* `mindsos admin promote propose` CLI verb — Phase 24.
* `force` flag / `reviewed_similarity_report_id` parameter — Phase 24
  (these are gate parameters on the mutating entry-point that doesn't
  ship at 16).
* Per-candidate atomic rollback (ADR-0053) — Phase 24.
* Release-ship audit gate placement (ADR-0144 §Placement) — Phase 24.
* `bloom-filter` / `blocking-key` similarity pre-filtering for
  scalability — Phase 24+ optimization (Phase 16 scope = correctness on
  importer-populated Globals).
* FalkorDB-direct CLI source (`--falkordb-graph`) — Phase 26 alongside
  state-file write surface.
* Capability-gating (`CAN_PROPOSE_MUTATION`) — Phase 18+ (server
  capability framework).

---

## 3. Cross-chat dependencies

### Closed (Phase 15a → Phase 16)

* `mindsos_admin/` package home permanence (Phase 15a PB-17 +
  ADR-0140 §amendment-1). Phase 16 consumes the package without
  relocation.
* Phase 15a PB-19 forward-cite ("Phase 16 lands `mindsos_admin/
  promotion.py`") — **amended in Phase 16 design log** to "Phase 16
  lands `mindsos_admin/similarity.py`; `promotion.py` deferred to
  Phase 24 under the ADR-0118 + ADR-0141 contract".
* Phase 13 schemas (ontology / lexicon / concepts) — Phase 16's
  per-role extractors consume the NodeType / EdgeType constants
  verbatim.
* Phase 12 IRI builders — Phase 16's IRI tail rule
  (`iri.rsplit(":", 1)[-1]`) is implicit-Phase-12 contract.
* Phase 09 state-file reader (`MetagraphLoader`) — Phase 16's CLI
  consumes via `--state-file` path.
* Phase 10 soft-delete (`is_deprecated`) — Phase 16's content hash
  excludes soft-deleted nodes from the role-graph hash input.

### Forward (Phase 16 → later phases)

* **Phase 17** (versioning + breadcrumbs) — independent of Phase 16
  similarity surface; no carry-forwards.
* **Phase 23** (server promotion lock + MetagraphSnapshot rollback) —
  narrowed by PB-4c to snapshot infra only.
* **Phase 24** (per-user transactional promotion) — consumes
  `compute_similarity` for the release-ship audit gate (ADR-0144
  §Placement); consumes `metagraph_content_hash` for audit-row
  invariants; locks ADR-0144 §amendment-1 §Placement clause Accepted.
  Also lands `mindsos_admin/promotion.py` (the deferred entry-point)
  under the ADR-0118 + ADR-0141 contract.
* **ADR Status flips** — ADR-0141 Accept at Phase 24 triggers Status
  flip of ADRs 0049 / 0053 / 0056 from Accepted to Superseded (per PB-U3
  amendment text). ADR-0055 stays Accepted as historical (its
  §amendment-1 supersedes the heuristic only, not the ADR itself).

---

## 4. ADR amendments (full text — Phase 16 authors)

The actual amendment text lives in the parent project tree at
`/Layered Intelligence/docs/decisions/adr/<adr>.md` per Model C
(`feedback_docs_source_of_truth.md`). Phase 16's PR adds these 7
amendments to those files (not to `halvim_mindsos/`).

See:

* `docs/decisions/adr/0049-similarity-report-before-promotion.md` —
  §Revisions amendment-1
* `docs/decisions/adr/0052-report-id-deterministic-content-hash.md` —
  §Revisions amendment-1
* `docs/decisions/adr/0053-promote-per-candidate-atomic-rollback.md` —
  §Revisions amendment-1
* `docs/decisions/adr/0055-baseline-similarity-heuristic-crude.md` —
  §Revisions amendment-1
* `docs/decisions/adr/0056-promotion-result-preserves-input-order.md` —
  §Revisions amendment-1
* `docs/decisions/adr/0144-similarity-at-release-ship-audit-gate.md` —
  §Revisions amendment-1 + amendment-2

The `tests/phase_16/test_adr_amendment_sentinels.py` test asserts each
amendment header is present + body substrings match.

---

## 5. Sign-off

User signed off via iterative "I agree with all your suggestions"
acknowledgments after each of 5 rounds plus a final "agreed... proceed"
at design close. Mirror of Phase 15b's signed-off-by-iteration pattern.

Branch `phase-16` cut off `origin/main` tip `ec94565` (Phase 15b
design-only squash). Implementation follows.
