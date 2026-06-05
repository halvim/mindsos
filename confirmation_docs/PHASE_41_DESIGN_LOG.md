# PHASE 41 DESIGN LOG — Rail B slot 2: L3 X2 (ADR-0155 Monitor-lifecycle retirement)

Branch `phase-41` off `main`-tip `5c12ba1`. Impl phase of a settled design
(L1_L3_REFRAME_DECISIONS §D36, saturated R3; ADR-0155 status **Accepted**).
No version bump (high-water-mark: 41 ≤ manifest 44, PB-2 convention shipped Phase 40).

---

## §0 — Process discipline (inherited)

- **Ground-first consumer discipline (Phase 44 §5–§12).** Every retired/renamed
  surface grepped across `mindsos_*` / `tests/` / `docs/` BEFORE editing. Done at R0 (§2).
- **S2 lesson (Phase 40 §10).** A hard-break sweep must include **test-fixture and
  docs/docstring consumers**, not just production definers. Phase 40's 38-failure
  gate-1 cascade came from missed test-fixture consumers. Applied — see PB-3.
- **Manifest high-water-mark (Phase 40 §11).** `__version__ = "0.0.0+phase44"` and the
  manifest stay untouched. `confirm-phase --phase 41` accepted by
  `_phase_exceeds_manifest`. Do not bump.
- **Ceremony hygiene (Phase 40 §11 anomalies to avoid).** Run `confirm-phase` on
  post-squash `main`, not branch tip; fix Linux box `git config` author identity before
  committing confirm artifacts. (Git writes run Mac-side: the Cowork Linux sandbox cannot
  write the mounted `.git`.)

## §0.1 — Prereq record

| Check | Result |
|---|---|
| `phase-40-confirmed` tag exists | ✅ `cf3faeb` |
| Tree clean at branch point | ✅ after committing 2 orphaned Phase-40 closure files to `main` (`5c12ba1`); untracked demo/spec files left alone (out of scope) |
| `main`-tip = Phase 40 closure descendant | ✅ `5c12ba1` → `ce6edc3` → `cf3faeb` |
| Branch `phase-41` off `main`-tip | ✅ |
| No version bump (41 ≤ 44) | ✅ guardrail held |

## §0.2 — ADR-0155 transcription parity probe

ADR-on-disk (`docs/decisions/adr/0155-monitor-lifecycle-relocated-from-l3-to-l4.md`):
status **Accepted**, date 2026-06-01, supersedes ADR-0073. **No status flip needed on
ship** (already Accepted). Retire/keep/L4-owns lists in §Decision match PHASE_MAP Phase 41
detail + §D36 settlement verbatim. One nuance: ADR §Cost says "~2 file edits (phase_27 +
phase_28)" for the node_kind rename — grounding shows phase_28 may need **zero** edits
(see PB-5). Correct the draft estimate, not the ADR.

---

## §1 — R0 saturation agenda (S-surfaces)

### S1 — Production deletions (surgical, NOT whole-module)
- `runtime.py`: delete `ResidentSubscription` dataclass (l.266–342) + `__all__` entry
  (l.350); scrub Phase-31 resident docstring block (l.1–32, l.263); drop now-unused
  imports (`ResidentError`; verify `Monitor`/`Callable` still used elsewhere — they are
  not after deletion → drop). **Keep** `invoke`/`ProblemTraceSink`/`ProblemTraceRecord`
  (Phase 30).
- `exceptions.py`: delete `ResidentError` class (l.131–157) + `__all__` entry (l.228);
  scrub the `start_resident` mention in `CapacityRegistrationError` docstring (l.49–50)
  and the Phase-31 line in the module docstring (l.10–11). **Keep** the other 7 classes.
- `capacity_layer.py`: delete `start_resident`/`stop_resident`/`active_subscriptions`
  (l.599–721) + `self._subscriptions` field (l.178); drop `ResidentError`/
  `ResidentSubscription` imports (l.98,102); scrub resident docstring (l.33–42, l.176–177).
  **Keep** `Monitor` import (needed by `iter_monitors`).

### S2 — `KIND_RESIDENT` → `KIND_MONITOR` rename (symbol + VALUE)
- `identifiers.py`: `KIND_RESIDENT = "resident"` → `KIND_MONITOR = "monitor"` (l.138);
  swap in `NODE_KINDS` frozenset (l.142). **Value changes** "resident"→"monitor" (PB-4).
- `capacity.py`: import (l.34) + `Monitor.node_kind = KIND_RESIDENT` (l.132) → `KIND_MONITOR`.
- `__init__.py`: import (l.242) + `__all__` (l.377) `KIND_RESIDENT` → `KIND_MONITOR`.

### S3 — `cl.iter_monitors()` producer (net-new ~10 LOC)
- `capacity_layer.py`: add `iter_monitors() -> List[Monitor]`, Local-wins merged
  enumeration mirroring `_resolve_declaration` / `iter_declarations`; filter to `Monitor`.
  No v1 consumer (L4 `MonitorSubscriptionRegistry` ships Phase 46 — acceptable per DAG,
  mirrors Phase 40 `family_rules` ahead of its consumer).

### S4 — Export-slate sentinels (count flip + membership edits)
- Count `114 → 112` in **4** files: `tests/phase_29/31/33/34_*export_slate*` (net −3 +1).
- Membership-list drop of `"ResidentSubscription"`+`"ResidentError"` in **2** files:
  `tests/phase_31` (l.18–19) + `tests/phase_33` (l.46–47) + their count-math comments.

### S5 — Test retirement + rename
- `tests/phase_31/` resident test files delete **whole** (8 files:
  `_fixtures.py`, `test_resident_active_list/emit_on_signal/start/state_slot/stop/
  subscription_eq/unknown_iri_raises/wrong_type_raises`,
  `test_capacity_layer_subscriptions_init`). Verify no orphan import remains in phase_31
  package (`_fixtures` consumers).
- `tests/phase_27/test_capacity_dataclass.py`: `KIND_RESIDENT`→`KIND_MONITOR` (import l.40,
  asserts l.131,185). phase_28: empirically zero (PB-5) — verify.

### S6 — New Phase 41 tests (PHASE_MAP)
- `test_resident_infrastructure_retired.py` (hard-break sentinel — scope per PB-2),
  `test_iter_monitors.py`, `test_kind_monitor_rename.py`,
  `test_adr_amendment_sentinels.py` (anchors ADR-0155; chains from Phase 40).

### S7 — Docs amendments
- `HANDOFF.md` §3.1 (strike retired methods from L3-surface-L4-consumes; add `iter_monitors`).
- `docs/concepts/monitors.md` relocation amendment.
- ADR-0073 status → Superseded (PB-6). ADR-0155 already Accepted.
- CHANGELOG entry. `docs/decisions/summary/capacity.md` + `docs/dev/internals/capacity.md`
  resident references → past-tense/retired note.

---

## §2 — Blast radius (grep, code+tests+docs)

| Symbol | Production (live) | Tests | Docs |
|---|---|---|---|
| `start_resident` | capacity_layer (def) + runtime/__init__ docstrings | phase_31 ×8 | 6 ADR/summary/internals + L3_FUTURE_WORK |
| `stop_resident` | capacity_layer (def) + docstrings | phase_31 ×2 | ADR-0073/0155, L3_FUTURE_WORK |
| `active_subscriptions` | capacity_layer (def) + docstrings | phase_31 ×3 | ADR-0073/0155 |
| `_subscriptions` | capacity_layer (field) + docstrings | phase_31 ×4 | ADR/CHANGELOG |
| `ResidentSubscription` | runtime (def) + capacity_layer/__init__ | phase_29/31/33 slates + phase_31 resident/sentinel | ADR/CHANGELOG/summary |
| `ResidentError` | exceptions (def) + runtime/capacity_layer/__init__ | phase_29/31/33 slates + phase_31 | ADR/CHANGELOG |
| `KIND_RESIDENT` | identifiers (def) + capacity/__init__ | phase_27 dataclass | ADR-0155 |

Out-of-`mindsos_capacity` production consumers: **none** (no mindsos_server/cli/core hits)
→ grounds "internal-only; safe hard-break."

---

## §3 — Pushbacks (pre-impl) — RESOLVED

| PB | Finding | Decision |
|---|---|---|
| PB-1 | "Phase 31 module deletes whole" false for production | **Surgical** removals from shared modules; whole-delete is **test-only** (8 files). |
| PB-2 | grep-zero pass criterion unsatisfiable repo-wide | Sentinel = **importability assertion + text grep scoped to `mindsos_capacity/**/*.py`** (excl. sentinel) → zero. Forces S2 docstring scrub. (user sign-off) |
| PB-3 | export-slate is count + membership | Count **114→112** in `phase_29/31/33/34`; drop `ResidentSubscription`/`ResidentError` membership in `phase_31`+`phase_33`. |
| PB-4 | rename is a VALUE change | `KIND_MONITOR="monitor"` per ADR; node_kind value migration empty-at-v1 (note). |
| PB-5 | ADR "phase_27+phase_28 edits" overstates | Edit phase_27; **verify phase_28 empirically** (expect zero). |
| PB-6 | ADR-0073 status not flipped | **Flip ADR-0073 → Superseded by ADR-0155** + note. (user sign-off) |
| PB-7 | iter_monitors no v1 consumer | Buildable, mirrors `iter_declarations` Local-wins; consumer Phase 46 (DAG-OK). |
| PB-8 | manifest/version | **No bump** (41 ≤ 44). Guardrail. |

## §5 — Impl-time grounding findings (consumer discipline; Phase 44 §5–§12 pattern)

| IPB | Finding (spec/PHASE_MAP framing vs ground truth) | Resolution |
|---|---|---|
| IPB-1 | "Phase 31 module deletes whole (~6-8 files)" undercounts. Actual: **9** resident test files delete whole (8 `test_resident_*` + `test_capacity_layer_subscriptions_init`). | Delete 9 Mac-side. |
| IPB-2 | `tests/phase_31/_fixtures.py` is **shared by 5 surviving text tests** (`make_fresh_layer`/`make_layer_with_text`) — cannot delete whole. | **Surgical prune** of the 2 resident-only helpers + unused imports; text helpers kept. |
| IPB-3 | PHASE_MAP "HANDOFF §3.1 amendment (Phase 41 finalizes)". | **Already final** (Chat C pre-drafted line 118 with `iter_monitors` + retirement note). No edit. |
| IPB-4 | PHASE_MAP "Modules touched"/"confirms" lists `docs/concepts/monitors.md`. | **File does not exist** (phantom). Redirected doc amendments → `glossary.md` (Resident entry), `summary/capacity.md` (ADR-0073 row), `dev/internals/capacity.md` (2 prose refs). |
| IPB-5 | PHASE_MAP implies a CHANGELOG-style record. | CHANGELOG stops at Phase 38; 39/40/43/44 added **no** entry. Phase 41 follows suit — **no CHANGELOG line** (consistency). |
| IPB-6 | `capacity.py` flags `typing.List` unused under pyflakes. | **Pre-existing** (not introduced by Phase 41; untouched line). Left as-is — out of scope. |
| IPB-7 | Export-slate "membership drop" vs codebase flip convention. | **Flipped** present→absent (`[[feedback-parity-test-sentinel-flip-at-target-phase]]`) in `phase_31`/`phase_33`, not bare-deleted — actively guards re-introduction. |

**Sandbox constraint:** the Cowork Linux mount allows file **writes** but not
**deletes** on the repo (`Operation not permitted`), and cannot write `.git/`.
All deletions + git + tests + `confirm-phase` run **Mac-side** (pair-execution).
A stray `tests/phase_41_canary_5.txt` (delete-capability probe) must be removed Mac-side.

**Static verification done in-sandbox (read-only):** `__all__` count = **112**
(AST); scoped grep over `mindsos_capacity/**/*.py` = **zero**; cross-package
production grep = **zero**; `py_compile` clean on all edited modules + new tests.
Runtime pytest + `mkdocs build --strict` deferred to Mac gate (deps).

## §4 — Sentinel ledger (locked)
- Export count: **112** (`phase_29/31/33/34` count) + membership drop (`phase_31`/`phase_33`).
- Retirement sentinel: importability (`from mindsos_capacity import X` → ImportError) +
  scoped grep `mindsos_capacity/**/*.py` zero (excl. `test_resident_infrastructure_retired.py`).
- ADR-0155 status: Accepted (anchor, no flip). ADR-0073: Accepted → **Superseded**.
