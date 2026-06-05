# PHASE 40 DESIGN LOG — Rail B slot 1 (L3 reframe X1)

**Phase:** 40 — L3 X1: family-specific dont-know contracts (ADR-0157) + DataState realm naming convention (ADR-0158).
**Rail:** B (root). **Depends on:** 38. Parallel to Rails A/C/D.
**Spec:** `confirmation_docs/PHASE_40_NEXT_CHAT_PROMPT.md`. **Design ground truth:** `L1_L3_REFRAME_DECISIONS.md` §D46 + §D48; ADR-0157 + ADR-0158 (Accepted on disk).
**Status:** R0 in progress (saturation agenda + grounding). Not yet branched.

---

## §0 — Process discipline (inherited)

- **Ground-first consumer discipline (Phase 44 lesson).** Before building any surface, grep for its v1 consumer. If none and it is not the phase's explicit contract deliverable, defer it and record the deferral. Phase 44 reversed CR-2 / CR-3 / S6 / L2-10 for absent consumers; apply the same test here.
- **ADR transcription parity (Phase 43 NPB11-META).** R1 step 0 = grep every design-pass / PHASE_MAP transcription against the Accepted ADR on disk; correct the *draft*, not the ADR. Several drifts surfaced at R0 (see §2).
- **Pair-execution** (Cowork prepares content; user runs git on Mac; Linux runs gates via docker). Sandbox is Py3.10 + no FalkorDB → syntax-compile + pure-logic checks only; real gates on Linux docker.
- **9-surface manifest bump** + **6-step confirm-phase** + **docker rebuild before each gate** (HANDOFF §9). **Manifest-under-DAG nuance unresolved — see §5/S7.**
- **L0-24 import cycle** (pre-existing, `admin↔persistence↔mindsos_admin`). Phase 40 is L3-only; likely unaffected. See §5/S8.

---

## §1 — R0 saturation agenda (S-surfaces)

### S1 — REALM constants home (DRIFT — file-home correction)
- **Drift:** PHASE_MAP §4 Phase 40 row + chat-opener prereq #5 say `mindsos_knowledge/identifiers.py`. ADR-0158 line 45 + §D48 R3 refinement (line 166) + every shipped DataState surface say **`mindsos_capacity/identifiers.py`**.
- **Grounding:** all DataState machinery (`datastate_iri()`, `_DATASTATE_NAME_RE`, every `DS_*`, `register_datastate`) lives in `mindsos_capacity`. `mindsos_capacity/identifiers.py` last touched **Phase 33** — untouched by 39/43/44.
- **Ruling (proposed):** correct to `mindsos_capacity/identifiers.py` (ADR is authoritative; layer-correct — DataStates are pure L3). **Consequence:** Phase-40 `identifiers.py` PB-Z collision concern (prereq #5, PHASE_MAP risk #1) **evaporates** — no Phase-39/43/44 overlap, no rebase-for-collision needed. The plan author conflated the L2 and L3 `identifiers.py` files.
- Ship: 9 `REALM_*` string constants + `RESERVED_REALMS` frozenset (verbatim ADR-0158 lines 48-62). Consumer present at v1: `register_datastate` validator (S2) + `family_rules.py` `REALM_MARKER` import (S3).

### S2 — `register_datastate` strict realm validation (+ shipped-fixture break risk)
- Add `allow_new_realm: bool = False` kwarg + validation: require single-dot `<realm>.<name>`; reject multi-dot; reject realm ∉ `RESERVED_REALMS` unless opt-in. ADR-0158 lines 71-91. Insertion at `capacity_layer.py:199` `register_datastate`.
- **Consumer:** runs at every `register_datastate` call now → has a live v1 consumer. SHIP.
- **Break risk (real):** production DataStates are all single-dot reserved-realm (`text.*`, `mm.*`, `problem_trace.*`) → safe. **But test fixtures `datastate_iri("phase33.probe.input")` / `("phase33.probe.output")` are multi-dot + unreserved realm (`phase33`)** → rejected under strict validation → Phase 33 cumulative-gate breakage.
- **Ruling (proposed):** rename the Phase 33 probe fixtures to a reserved single-dot form (e.g. `mm.probe_input` / `mm.probe_output`) in the same phase. Track as impl-time test-churn item; confirm no production reference. (Negative test `datastate_iri("Bad!Name")` is unaffected — it tests the existing regex, not the realm validator.)

### S3 — `family_rules.py` module (FAMILY_RULES + lookup fn)
- New `mindsos_capacity/family_rules.py`: `FamilyDontKnowShape` enum (5 shapes) + `FAMILY_RULES` dict + two-level lookup (name-prefix → category → DATASTATE_MARKER permissive default + info log). Verbatim ADR-0157 lines 33-90. Imports `REALM_MARKER` from identifiers; defines `DS_UNHANDLED_INPUT`.
- **Consumer:** runtime consumer = L4 dispatch (Phase 46) — **none at v1.** This is **not** deferrable-speculative: it is the explicit X1 contract deliverable, exactly analogous to Phase 41 shipping `cl.iter_monitors()` (consumer Phase 46) and Phase 45 shipping `dream.*` (consumer L4). The reframe X1/X2/X3 sequencing *is* "ship the L3-side contract ahead of its L4 consumer." SHIP.
- **Drifts to reconcile (correct draft to ADR):**
  - Fn name: ADR `family_rule_for(capacity_iri)`; PHASE_MAP/test-name say `lookup_rule`. → pick ADR `family_rule_for`; optionally alias `lookup_rule`. (minor; track)
  - Input form: ADR splits full IRI `capacity:<cat>:<name>`; PHASE_MAP pass-criterion examples pass bare `"predicate.is_question"`. → implement per ADR (full IRI); treat PHASE_MAP examples as loose shorthand; tests use full IRIs.
  - `scoring` shape: ADR = **OPTIONAL_RETURN** (line 51); PHASE_MAP pass-criterion example says `scoring.confidence → DATASTATE_MARKER` — **wrong/stale**. ADR wins.

### S4 — `DontKnowReason.UNHANDLED_INPUT` (CONSUMER-DISCIPLINE FLAG — needs ruling)
- **Grounding:** `DontKnowReason` does **not exist anywhere in the repo** (zero hits). Its four sibling values (`NO_MATCHING_PATTERN`, `LOW_MAPPING_CONFIDENCE`, `PIPELINE_UNAVAILABLE`, `UNRESOLVED_AMBIGUITY`) are Chat A / L4 MappingResult semantics. L4 ships Phase 46+. **No enum to extend; no v1 consumer.**
- Textbook Phase-44 case (S6/CR-3 pattern). Options + recommendation in §4 PB-1. **User decision required.**

### S5 — `DS_UNHANDLED_INPUT` marker DataState registration
- `DS_UNHANDLED_INPUT = "datastate:marker.unhandled_input"` (ADR-0157 line 92; constant in `family_rules.py`). ADR-0158 marker realm = "partial (`DS_UNHANDLED_INPUT` via ADR-0157)" → this is the marker realm's v1 entry. Register as Global-bootstrap marker DataState; PHASE_MAP test `test_ds_unhandled_input_registered.py`.
- Passes strict validator (`marker` reserved, single-dot). **Open:** registration site (Global bootstrap path) — confirm at R1.

### S6 — `docs/concepts/capacity-families.md` (net-new doc)
- Does not exist. Phase 40 ships it documenting the 5-shape catalog. ADR-0157 + ADR-0158 flip Proposed→Accepted (already Accepted on disk — verify frontmatter; likely a no-op + sentinel anchor only).

### S7 — DAG manifest nuance (prereq #6 — surface before ship)
- Manifest `[mindsos] phase = "44"`. `mindsos confirm-phase --phase 40` will mismatch a `phase="44"` manifest (check assumes serial phases). Do **not** blind-bump 44→40 (backwards). Options + recommendation in §4 PB-2. **User decision required before ship ceremony.**

### S8 — L0-24 import cycle (maintenance preface decision)
- Pre-existing `admin↔persistence↔mindsos_admin` cycle bites isolated `pytest tests/phase_NN/` runs that import `mindsos_server` cold. Phase 40 is L3-only; `tests/phase_40/` likely never imports `mindsos_server` → probably unaffected. Spec encourages clearing it as a maintenance preface (lazy-import fix in `mindsos_admin/promotion.py` + remove `tests/phase_44/conftest.py` band-aid; ~1-3 lines). Options in §4 PB-3.

---

## §2 — ADR transcription parity register (R1 step 0, run early at R0)

| # | Drift | Draft says | ADR-on-disk says | Resolution |
|---|---|---|---|---|
| D1 | REALM constants home | PHASE_MAP + prereq #5: `mindsos_knowledge/identifiers.py` | ADR-0158:45 + §D48:166: `mindsos_capacity/identifiers.py` | Correct draft → `mindsos_capacity`. Collision concern evaporates (S1). |
| D2 | `scoring` dont-know shape | PHASE_MAP pass-crit: `scoring.confidence → DATASTATE_MARKER` | ADR-0157:51: `scoring → OPTIONAL_RETURN` | Correct draft → OPTIONAL_RETURN. |
| D3 | lookup fn name | PHASE_MAP + test file: `lookup_rule` | ADR-0157:76: `family_rule_for` | Pick ADR name; optional `lookup_rule` alias. |
| D4 | lookup input form | PHASE_MAP examples: bare `"predicate.is_question"` | ADR-0157:76-86: full `capacity:<cat>:<name>` | Implement per ADR; PHASE_MAP examples illustrative. |
| D5 | DontKnowReason | PHASE_MAP + §D46: "enum value added" | enum absent from repo | See PB-1 (defer vs birth). |

---

## §3 — Consumer-grounding summary (Phase 44 discipline applied per surface)

| Surface | v1 consumer | Verdict |
|---|---|---|
| `REALM_*` + `RESERVED_REALMS` | `register_datastate` validator (this phase) + `family_rules` import | SHIP |
| `register_datastate` strict validation + `allow_new_realm` | every register call (now) | SHIP (+ fixture rename, S2) |
| `family_rules.py` (FAMILY_RULES + `family_rule_for`) | L4 dispatch (Phase 46) — none at v1 | SHIP — explicit X1 contract deliverable (not speculative; cf. Phase 41/45 pattern) |
| `DS_UNHANDLED_INPUT` marker DataState | marker-family discipline (WSD/L4 future) | SHIP — marker realm's mandated v1 entry per ADR-0158 |
| `DontKnowReason.UNHANDLED_INPUT` | none; enum absent; L4 type | **DEFER (proposed)** — PB-1 |

---

## §4 — Pre-impl pushbacks (options + chosen pick)

### PB-1 — `DontKnowReason.UNHANDLED_INPUT`: defer vs birth now  *(user decision)*
The enum does not exist; its siblings are L4 MappingResult semantics; nothing consumes it at v1.
- **Option A (recommended) — Defer.** Drop `DontKnowReason.UNHANDLED_INPUT` (and `test_dont_know_reason_enum.py`) from Phase 40. Whoever ships `DontKnowReason` (L4, Phase 46/47) adds the value then. ADR-0157 already documents the intended value; the L3-consumable artifact (`DS_UNHANDLED_INPUT`) ships now regardless.
  - Pros: matches Phase 44 S6/CR-3 consumer discipline; no L4 type born in L3; narrow-and-correct.
  - Cons: PHASE_MAP §4 Phase 40 row + §D46 list it in X1 → a documented deferral (record in design log + PHASE_MAP row).
- **Option B — Birth the full enum in `mindsos_capacity` now.** Create `DontKnowReason` (5 values) at L3.
  - Pros: literal PHASE_MAP/ADR text satisfied; one place.
  - Cons: speculative forward-shape; 4/5 values have no consumer; puts an L4 type in L3; the exact pattern CR-2/CR-3 rejected.
- **Option C — Birth a 1-value enum now, extend at L4.** Minimal `DontKnowReason{UNHANDLED_INPUT}`.
  - Pros: satisfies the X1 test literally.
  - Cons: still consumer-less; guarantees an L4-phase edit to add the other four → churn; worst of both.

**My pick: A (defer).** → **RULED A (user, 2026-06-05).** Drop `DontKnowReason.UNHANDLED_INPUT` + `test_dont_know_reason_enum.py` from Phase 40. Record deferral in PHASE_MAP §4 Phase 40 row + here. L4 phase (46/47) that births `DontKnowReason` adds the value. `DS_UNHANDLED_INPUT` still ships (S5).

### PB-2 — Manifest `[mindsos] phase` under parallel DAG  *(user decision; before ship, not R0)*
`confirm-phase --phase 40` vs manifest `phase="44"`.
- **Option A (recommended) — Manifest tracks max(confirmed phase), not current ship.** Leave manifest at the highest shipped integer (44); do **not** regress to 40. Adjust the confirm-phase / doctor parity check to treat `[mindsos] phase` as a high-water mark under DAG (or pass the ship phase to confirm-phase without rewriting the manifest down). Need to read `confirm_phase.py` + `doctor.py` check #5 to pick the exact mechanism.
  - Pros: monotonic manifest; no backwards bump; no version regression on 7 packages / pyproject / docker tags.
  - Cons: the 9-surface bump checklist (designed for serial phases) needs a DAG-aware reinterpretation; tooling read required.
- **Option B — Bump manifest to a higher integer anyway.** Not applicable cleanly (40 < 44).
- **Option C — Decouple per-phase version from manifest under DAG.** Larger tooling change.

**My pick: A**, pending a read of `confirm_phase.py` + `doctor.py`. → **RULED A (user, 2026-06-05): high-water mark, read tooling first.**

**Tooling read (2026-06-05) — the coupling is non-trivial:**
- `confirm_phase.py:539-548`: `nn = phase.zfill(2)`; `expected = manifest["mindsos"]["phase"]`; **hard equality** `if nn != expected: raise Exit(2)`. With manifest `"44"`, `--phase 40` is rejected outright.
- `confirm_phase.py:557`: `image_tag = f"mindsos:phase{nn}-prod"` → `mindsos:phase40-prod`. `docker-compose.yml` only carries `mindsos:phase44-prod` / `phase44-test`. `_docker_image_id(image_tag)` + `_suite_hash(nn)` also key off `nn`.
- `doctor.py` `--self-test`: (a) compose image-tag regex vs manifest phase (line 44); (b) version-string parity across manifest / pyproject / all 7 package `__version__` (line 56); (c) python/falkordb pins.
- **Implication:** bumping manifest *down* to 40 would regress `0.0.0+phase44 → +phase40` across 7 packages + pyproject + 2 docker tags (backwards version bump — rejected). Leaving manifest at 44 makes the `nn != expected` equality reject `--phase 40` and the `phase40-prod` image absent.

**Recommended mechanism (high-water mark; ship-ceremony preface — NOT R0-blocking):** treat `[mindsos] phase` as a monotonic **release counter** decoupled from the phase *slot id*. Concretely, two viable forms (decide at ship):
- **M1 (smallest tooling touch):** Phase 40 ship **bumps manifest forward 44 → 45** (next monotonic integer), and confirm-phase is invoked with the release counter, while branch/tag/test-dir/`PHASE_40_CONFIRMED.md` keep the slot id `40`. Requires confirm-phase to accept a release-counter arg distinct from the slot, OR run `--phase 45` for the manifest check while writing slot-40 artifacts. Still needs `phase45-*` images.
- **M2 (DAG-aware equality):** relax `confirm_phase.py:542` to allow `int(nn) <= int(expected)` when shipping an out-of-order rail slot (manifest already higher), and derive `image_tag` from the manifest phase, not `nn`. Slot 40 confirms against a `phase44`-tagged image; manifest stays 44; no version regression; no phase40 image needed.

**Disposition:** M2 is the cleaner fit for the DAG (no spurious version inflation, no per-slot image). Carry as a **Phase-40 ship-ceremony tooling preface** (Stream-A-style one-file edit to `confirm_phase.py` + a doctor self-test note); finalize the exact form with the user immediately before the confirm ceremony, after R1 impl lands. Does not block R0/R1 design or the code surfaces.

### PB-3 — Clear L0-24 as a maintenance preface?  *(user decision; low stakes)*
- **Option A (recommended) — Verify-then-skip.** Confirm `tests/phase_40/` doesn't import `mindsos_server` cold (L3-only; expected clean). If clean, no conftest band-aid needed; leave L0-24 to MAINTENANCE_CHAT.
  - Pros: keeps Phase 40 scope pure-L3; no cross-layer maintenance entangled in a contract phase.
  - Cons: L0-24 stays open (already tracked).
- **Option B — Clear L0-24 now** (lazy-import in `promotion.py` + remove `tests/phase_44/conftest.py`).
  - Pros: removes a known foot-gun; spec encourages it.
  - Cons: touches L0/admin in an L3 phase; adds a cross-cutting cumulative-gate variable; better isolated in a maintenance window.

**My pick: A.** → **RULED A (user, 2026-06-05): verify-then-skip.** **Verified clean:** `mindsos_capacity` imports nothing from `mindsos_server`; no existing L3-only test dir (phase_27–34) carries a conftest server/admin warm-up. `tests/phase_40/` (pure L3) will not import `mindsos_server` cold → L0-24 does not bite Phase 40. No conftest band-aid needed; L0-24 stays with MAINTENANCE_CHAT.

---

## §5 — Prereq check result (2026-06-05)

| # | Check | Result |
|---|---|---|
| 1 | `phase-44-confirmed` tag exists | PASS |
| 2 | clean working tree | PASS |
| 3 | `main`-tip = Phase 44 closure-docs commit (`54f6afa`) | PASS |
| 4 | branch `phase-40` off `main`-tip | pending (not yet branched) |
| 5 | `identifiers.py` collision discipline | **REASSESSED** — drift D1: REALM constants belong in `mindsos_capacity/identifiers.py` (untouched since Phase 33) → no Phase-39/43/44 collision. Concern dissolved. |
| 6 | DAG manifest nuance | **SURFACED** — PB-2; manifest at `phase="44"`; do not blind-bump. Resolve before ship. |

No prereq is a hard fail. All three pre-impl rulings landed (PB-1/2/3 → A/A/A).

---

## §6 — R0 closure → locked R1 scope (2026-06-05)

**As-shipping (narrowed from PHASE_MAP row by D1 home-correction + PB-1 deferral):**

1. **`mindsos_capacity/identifiers.py`** — 9 `REALM_*` constants + `RESERVED_REALMS` frozenset (ADR-0158 §Decision). *(not `mindsos_knowledge` — D1)*
2. **`mindsos_capacity/family_rules.py`** (NEW) — `FamilyDontKnowShape` (5 shapes) + `FAMILY_RULES` dict + `family_rule_for(capacity_iri)` two-level lookup + `DS_UNHANDLED_INPUT` constant (imports `REALM_MARKER`). *(fn name per ADR; optional `lookup_rule` alias — D3)*
3. **`mindsos_capacity/capacity_layer.py`** — `register_datastate` gains `allow_new_realm=False` + strict single-dot / reserved-realm validation (ADR-0158 lines 71-91).
4. **`mindsos_capacity/__init__.py`** — export `family_rules` surface + `DS_UNHANDLED_INPUT` + `REALM_*` (no `DontKnowReason` — PB-1 defer).
5. **`DS_UNHANDLED_INPUT`** — constant (in `family_rules.py`) + DATASTATE_MARKER wiring **only; NO node-registration bootstrap** (PB-6 / round 2). Symmetric with all other builtin DataStates (none are bootstrap-registered in product).
6. **Test churn:** rename Phase 33 probe fixtures `phase33.probe.input/output` → reserved single-dot (e.g. `mm.probe_input/output`) — S2.
7. **Tests** `tests/phase_40/`: `test_family_rules_lookup.py`, `test_realm_validation.py`, `test_ds_unhandled_input_defined.py` (reframed from `_registered` per PB-6 — verifies constant value/realm + registerable via validator, not node existence), `test_adr_amendment_sentinels.py`. **Dropped:** `test_dont_know_reason_enum.py` (PB-1).
8. **Docs:** `docs/concepts/capacity-families.md` (new); ADR-0157 + ADR-0158 sentinel anchors (already Accepted on disk — verify frontmatter).
9. **9-surface manifest bump** — gated by PB-2 ship-ceremony resolution (M2 recommended).

**Deferred (recorded):** `DontKnowReason.UNHANDLED_INPUT` → L4 phase 46/47 (PB-1). L0-24 → MAINTENANCE_CHAT (PB-3).

**Ship-ceremony preface:** PB-2 manifest/DAG tooling (M2) — finalize with user right before confirm-phase.

**Next:** R1 impl-locks — read `mindsos_capacity/__init__.py` + `family_rules` import surface + the Phase 33 probe-fixture registration sites + `bootstrap` DataState-registration path; then begin pair-execution build on branch `phase-40`.

---

## §7 — Round 2 pre-impl pushbacks (2026-06-05)

- **PB-4 — S2 fixture break confirmed REAL (not overstated).** Verified `tests/phase_33/test_invoke_session_context_injection.py:44-47` calls `register_datastate(DataState(name="phase33.probe.input"/"phase33.probe.output"))` — multi-dot + unreserved realm → rejected by strict validator. **Ruling:** rename → `mm.probe_input` / `mm.probe_output` (shipped realm, single-dot); rename `DS_PROBE`/`DS_PROBE_OUT` IRIs in that file. The capacity name `phase33.probe` is unaffected (capacity-name regex allows dots). Other phase_33 `register_datastate(ds)` sites use `problem_trace.record` / `mm.composite_instance` (safe).
- **PB-5 — `family_rule_for` malformed-input robustness.** ADR code does raw `iri.split(":")[1]/[2]` → `IndexError` on malformed IRI. **Ruling (my pick, low-stakes):** route through existing `parse_capacity_iri` (validates + raises clear `ValueError`), then two-level lookup, then permissive `DATASTATE_MARKER` default + info log for well-formed-but-unknown families. Malformed → error; unknown → default.
- **PB-6 — `DS_UNHANDLED_INPUT` registration → constant-only. RULED A (user, 2026-06-05).** Grounding: no product bootstrap registers any builtin DataState node (`text.*`/`mm.*`/`problem_trace.*` are constants registered only by tests/consumers). Building a node-registration bootstrap for one marker with no v1 reader = consumer-less forward-shape (Phase 44 discipline). Ship constant + `family_rules` DATASTATE_MARKER wiring only; reframe test to `test_ds_unhandled_input_defined.py` (value/realm + registerable-via-validator, not node existence).
- **PB-7 — mkdocs nav.** New `docs/concepts/capacity-families.md` must be added to `mkdocs.yml` nav or it emits a build warning. Mechanical; track at impl.

**Saturation status (after round 2):** Round 1 → 5 items (D1, PB-1/2/3, S2). Round 2 → 1 real (PB-6) + 1 decided (PB-5) + 2 minors (PB-4 confirm, PB-7). Converging.

---

## §8 — Round 3 pre-impl pushbacks (2026-06-05)

- **PB-8 — ADR-0157 `FAMILY_RULES` vocabulary ≠ shipped category vocabulary (latent at v1).** Shipped `FUNCTIONAL_CATEGORIES` (identifiers.py): perception, comprehension, derivation, decomposition, combination, path_finding, retrieval, scoring, trace, signalling, interaction, learning_methods, consolidate. ADR-0157 `FAMILY_RULES` keys use `derive` (≠ `derivation`) + `signal` (≠ `signalling`) and omit comprehension/decomposition/path_finding/trace/interaction/learning_methods/consolidate. → 9/13 shipped categories resolve via the permissive `DATASTATE_MARKER` default.
  - **Severity: latent.** Grounded the only shipped capacities: `text.*` = `perception` → explicit DATASTATE_MARKER ✓; `consolidate:mm` = `consolidate` → default DATASTATE_MARKER ✓; `trace:problem` = `trace` → default DATASTATE_MARKER ✓. All DataState-producing → correct shape under verbatim dict. Mismatch bites only when capacities are registered in unkeyed categories (WSD/FOL installation).
  - **RULING (my pick): Option A — transcribe ADR-0157 verbatim; route the mismatch as a hard finding to (1) the X3 Phase 27 dont-know audit (`PHASE_27_DONT_KNOW_AUDIT.md` — designated reconciliation point), (2) the WSD/FOL installation chats (own the unkeyed families), (3) the Phase 46 L4-dispatch consumer.** Rejected B (amend the saturated ADR inside an impl phase + guess shapes the ADR deliberately left to domain authors). Pending user confirm (A vs amend).
  - **Test alignment:** `test_family_rules_lookup.py` must assert *actual verbatim-dict behavior* incl. shipped categories hitting the default (e.g. `family_rule_for("capacity:consolidate:mm") == DATASTATE_MARKER` via default; `capacity:perception:text.space_split == DATASTATE_MARKER` via explicit key; `capacity:scoring:x == OPTIONAL_RETURN`).

**Saturation status (after round 3):** §9 3-round budget reached. Net new substantive finding this round: PB-8 (latent, routed). Remaining unknowns are impl-time (exact `__init__` export list, sentinel string selection, mkdocs nav placement) — R1 reading resolves them, §9.1 absorbs anything else. **Design saturated; ready to lock R1 on PB-8 confirmation.**

---

## §9 — Buildability scan (pre-branch, §9 discipline) — 2026-06-05

Pushback rounds saturated at 3 (per HANDOFF §9). This is the buildability scan over locked surfaces (exactly-N sentinels + fixture-keyed tests), not a 4th pushback round.

- **PB-9 (must-flip; mechanical) — `mindsos_capacity.__all__` exactly-N sentinel.** `tests/phase_29/test_phase_29_export_slate.py:87` asserts `len(mindsos_capacity.__all__) == 110`. Phase 40 adds package exports (`FamilyDontKnowShape`, `FAMILY_RULES`, `family_rule_for`, `DS_UNHANDLED_INPUT`; optionally `REALM_*` + `RESERVED_REALMS`). **Action:** bump the `== 110` literal by the exact count added + register a `PHASE_40_NEW_EXPORTS` frozenset assertion mirroring `tests/phase_30/test_phase_30_export_slate.py`'s `PHASE_30_NEW_EXPORTS` pattern. Decide the surfaced set at R1 (recommend: the 4 family_rules names public; keep `REALM_*`/`RESERVED_REALMS` imported directly from `.identifiers` by consumers → NOT in package `__all__`, so +4 → `== 114`). Confirm exact delta at impl.
- **Confirmed NOT tripped:** `tests/phase_27/test_identifiers.py:80` `len(FUNCTIONAL_CATEGORIES) == 13` — `REALM_*` are DataState realms, not capacity categories; category count unchanged.
- **Sentinel chain:** root = `tests/phase_39/test_adr_amendment_sentinels.py` (Phase 39 form: `"amendment-3" in text`). Phase 40 `test_adr_amendment_sentinels.py` chains from it, anchoring ADR-0157 (5-shape catalog strings) + ADR-0158 (9-realm strings) canonical text. ADRs already `status: Accepted` on disk → no Proposed→Accepted flip; sentinel asserts presence only.

- **PR shape (recommendation):** single PR + single squash + single tag. Phase 40 is small (~60 LOC src + tests); the Phase 39/43 multi-PR split was driven by large scope (rename across 87 files / 4 new schemas). No split rationale here.
- **Manifest 9-surface bump sequencing:** do NOT include the manifest bump in the code commits until PB-2 (manifest/DAG, M2) is resolved at ship-ceremony. Build + gate code green first; resolve PB-2 tooling; then manifest bump + confirm-phase. (Phase 39 §9.4 atomicity still applies to the 9 surfaces *when* bumped.)

**FINAL SATURATION:** 3 pushback rounds + buildability scan complete. Open items at R1 lock: PB-8 disposition (A recommended), PB-9 export-count delta (resolve at impl), PB-2 (ship-ceremony). No design forks remain.

---

## §10 — Implementation record + gate-driven follow-ups

**Commits on `phase-40`:** `3829369` (source) → `1f3e28e` (tests) → `40c147f` (docs).

**Gate 1 (cumulative, 2026-06-05): 38 failed / 3626 passed / 8 skipped.** Single root cause — the strict realm validator (S2) rejected pre-existing **test fixtures** registering DataStates in non-reserved realms. Broader than R0's S2 grounding, which only checked production DataStates + the phase_33 probe and missed the phase_29/30 fixture hubs. **Lesson:** S2's "shipped DataState" sweep must include all test-fixture register sites, not just production + one probe file.

**Follow-up commit (gate-driven, within §9 budget):**
- **phase_29 `analysis` realm** → renamed `analysis.sentiment` → `nlu.sentiment` in `tests/phase_29/_fixtures.py` (builder-local; 0 external refs; `nlu` reserved + apt). Fixes all 14 phase_29 failures via the shared builder.
- **phase_30 `test` realm** → `allow_new_realm=True` added at all 12 `register_datastate` sites (4 in `_fixtures.py` builders + 8 inline across 3 test files). Preserves the fixtures' deliberate `test.` isolation namespace (per `_ds` docstring) + all `datastate:test.*` IRI-literal assertions in currently-passing files (test_cli_capacity_find, test_pipeline_dataclasses). Fixes all 24 phase_30 failures.
- **Decision rationale:** rename where builder-local + 0 churn (phase_29); opt-in where the realm is deliberate + IRI-asserted (phase_30). `allow_new_realm` is the ADR-0158-designed escape for exactly this admin/test-context case.

**3-realm count unchanged; PB-9 export count 114 confirmed via targeted gate (106 passed).**

---

## §11 — Ship closure (2026-06-05)

**SHIPPED.** Squash-merge `5aee00f` on `main`; confirm artifacts cherry-picked at `cf3faeb`; tag `phase-40-confirmed` at `cf3faeb`. Cumulative gate **3670 passed / 8 skipped / 0 failed**.

**Commit trail:** `3829369` (source) → `1f3e28e` (tests) → `40c147f` (docs) → `c4e61d2` (fixture follow-up) → `d0d8201` (PB-2 tooling) → squashed to `5aee00f` → `cf3faeb` (confirm artifacts).

**PB-2 validated live:** `confirm-phase --phase 40` accepted against manifest `44` (no "ahead of manifest" error); no version bump (slot 40 ≤ high-water 44). `mindsos doctor --self-test` green; `family_rule_for` + `DS_UNHANDLED_INPUT` smoke green in the live env.

**Ceremony anomalies (non-blocking):**
1. confirm-phase ran on the `phase-40` branch tip (`d0d8201`), not post-squash `main` — content byte-identical to the squash, so the recorded gate result is valid; the CONFIRMED.md `git_sha` reflects `d0d8201`, not `5aee00f` (same class as the Phase 39 anomaly). The confirm artifacts were cherry-picked from `phase-40` onto `main`.
2. The cherry-picked confirm-artifacts commit (`cf3faeb`) carries the Linux box's placeholder author `EngAdhamTamer <your@email.com>` (stale Linux `git config`). Fix the Linux identity before the next ship.

**Deferrals carried forward:** `DontKnowReason.UNHANDLED_INPUT` → L4 (Phase 46/47); PB-8 FAMILY_RULES vocabulary reconciliation → Phase 42 (X3) Phase-27 audit + WSD/FOL installation chats.

**Lesson (for future S-surface grounding):** the S2 "shipped DataState" sweep must include **all test-fixture register sites**, not just production code + one probe file — the gate-1 38-failure cascade came entirely from phase_29/30 fixture hubs missed at R0.

**Next:** Phase 41 (Rail B X2 — ADR-0155 Monitor lifecycle retirement) branches off `main`; depends on `phase-40-confirmed`.
