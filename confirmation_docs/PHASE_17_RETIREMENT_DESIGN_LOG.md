# Phase 17 — Retirement Design Log

**Date:** 2026-05-20
**Decision class:** RETIRED (design-only-with-code; tag-free)
**Squash-merge SHA:** (filled at merge)
**ADR amendment:** ADR-0150 §amendment-3 (parent tree; lands first
per M3-B)

---

## §0 — Summary

Phase 17 ("L2 Versioning + breadcrumbs") was chartered to ship
`step(version=)` active-version routing, a per-role version map, and
a PROMOTED breadcrumb reader (per Phase 14 PB-15 + PB-13 carry-
forwards + the original PHASE_MAP §17 row scope).

Pre-impl probe at the retirement chat established that the shipped
one-graph-per-role invariant leaves the carry-forward incoherent.
The phase retires; minimal absorbing code ships in the retirement PR
itself; ADR-0150 §amendment-3 locks the version-dispatch model.

Four design rounds, 26 picks total, all user-agreed. This log
records the ledger.

---

## §1 — Pre-impl probe findings

Grep across `mindsos_knowledge/`, `mindsos_core/`, `mindsos_cli/`,
`mindsos_admin/`:

* `_find_role_graph(mg, role)` keys on `g.role == role` — one graph
  per role per metagraph is the structural invariant.
* `DolceImporter` / `OewnImporter` / `FrameNetImporter` all call
  `ensure_global_role_graph(mg, role)` (idempotent on role string)
  and write version-qualified IRIs into the same role-graph
  regardless of the version constructor argument.
* `parse_iri(iri).version` is the source of truth for extracting
  the version from any version-qualified IRI; shipped Phase 12.
* No `register_version_graph` / `active_version` / `version_for_role`
  / `versions_by_role` code exists. The Phase 14 PB-15 deferral note
  (`metagraph_view.py` lines 33, 109, 155 + docstring) is the only
  shipped artifact pointing at "Phase 17 amends with active-version
  selection" — and it references a model that has no place for
  version to dispatch.
* `mindsos_admin/similarity.py::list_candidates` already
  **defensively excludes** nodes carrying `ref_type="PROMOTED"`
  (Phase 16 PB-C2). That's the only L2 code that touches PROMOTED
  today; nothing in shipped code WRITES PROMOTED (`KL.promote()`
  was dropped at Phase 14 per ADR-0138 honoured by absence; the L3
  promote write capacity is Phase 33).

The probe matched the Phase 15b precedent shape: "Phase row's
scope is at odds with what shipped."

---

## §2 — Round 1: structural pushbacks (P1-P3)

### P1 — `step(version=)` carry-forward is incoherent against the shipped model

Three options. **Pick: A — cosmetic only** (drop `step(version=)`;
ship `versions_in_role` IRI-scan enumerator). B was multi-week
scope under "Net-new? No" label; C was plumbing that resolved to A
in behaviour.

### P2 — PROMOTED breadcrumb has no producer at Phase 17

Phase 16's `list_candidates` already excludes PROMOTED defensively;
no writer exists until Phase 33's L3 promote capacity (ADR-0138 + L3
write capacities). Phase 17 would ship a reader for data no shipped
writer produces. **Pick: A — retire Phase 17; absorb reader into
Phase 24** (later revised to Phase 33 per N1).

### P3 — ADR-0142 (Proposed) puts Phase 17 on shifting substrate

XRef cutover for `ref:global_*` is the canonical breadcrumb home;
ADR-0142 is Proposed; no migration shipped; no XRef-creating writer
exists. Phase 17 has no settled substrate to read from. **Pick: A
— read properties only; marked deprecation-target.** Compounds with
P2-A toward "retire."

---

## §3 — Round 2: retirement mechanics (R1-R7)

### R1 — Phase 14 PB-13 (KL CLI verbs) is a separate carry-forward

PB-13 named TWO verbs: `mindsos knowledge versions` AND
`active-version`. Only PB-15 (`step(version=)`) is vacuous; PB-13's
`versions` verb is genuine missing surface. **Pick: A — land CLI
verbs in the retirement chat itself** (5-LOC enumerator + 1 typer
command; drop `active-version` per P1-A).

### R2 — Tombstone-vs-delete the §17 row

Phase 37 precedent: strikethrough + RETIRED status block + cross-
refs amended. **Pick: C — tombstone §17 + amend all 8 cross-
references in the same chat** (orphan-refs make tombstones worse
than Phase 37's situation).

### R3 — `versions_in_role` home

Phase 36 (my initial pick) is wrong — it's an enumerator, not a
validator. **Pick: A — land in retirement chat as
`MetagraphView.versions_in_role(role) -> set[str]`** (~5 LOC IRI-
scan).

### R4 — PROMOTED reader home

Phase 24 (initial pick) inflates an already-saturated phase. **Pick
revised in N1: B — no future-phase reader needed; Phase 16's
defensive exclude is the only L2 reader; production reader ships
symmetric with Phase 33's promote write capacity per ADR-0146.**

### R5 — Chat scope

Phase 15b precedent: design-only chat shipped a PR. **Pick: A —
Phase 15b-style; retirement chat ships its own PR** (PHASE_MAP +
8-file cleanup + `versions_in_role` + CLI verb + memory + Phase 18
NEXT prompt; tag-free).

### R6 — ADR-0150 §amendment-3 needed

Retirement implicitly locks an architectural decision; better to
document via ADR than as a phase-log footnote. **Pick: A — amend
ADR-0150 §amendment-3** ("version dispatch is IRI-string only; one
graph per role; no `(role, version)` discriminator").

### R7 — Memory shape for a retired phase

**Pick: A — new `project_mindsos_phase_17_retired.md`** (distinct
from `_implemented` shape for future-chat recognition).

---

## §4 — Round 3: mechanics-of-mechanics (N1-N7)

### N1 — R4 correction: PROMOTED reader belongs at Phase 33, not Phase 28

Phase 28 is bootstrap/categories, not breadcrumb-walking. Phase 33
ships the L3 promote write capacity (one of 5 write categories per
ADR-0145); ADR-0146 symmetric write contract puts reader with
writer. Phase 16 already ships defensive exclude — that's the only
L2 reader needed pre-Phase-33. **Pick: B — no future-phase L2
reader; Phase 33's symmetric contract covers production.**

### N2 — `active-version` verb drop = explicit Phase 14 PB-13 amendment

**Pick: A — amend Phase 14 design log PB-13 in retirement chat**
("partially closed; `versions` shipped; `active-version` dropped
per PB-15 vacuum").

### N3 — Version-string bump policy

Phase 15b (design-only) didn't bump. Retirement ships code. **Pick:
A — bump `+phase16 → +phase17` across 5 packages** (linear progression
beats "minimum-change PR" optics; phase numbers are project
anchors).

### N4 — Tests directory placement

**Pick: A — `tests/phase_17/` with sentinels + method tests + CLI
verb tests** (Phase 15b precedent).

### N5 — ADR-0150 §amendment-3 escape-hatch language

Locking "version dispatch is IRI-string-only forever" over-locks.
**Pick: A — include explicit escape clause** mirroring Phase 14a §Q
amendment-escape pattern ("may be re-opened via §amendment-N citing
specific use case + impacted ADRs + resolution option (a/b/c)").

### N6 — `docs/usage/knowledge/versioning.md` ship-or-skip

PHASE_MAP §17 named the doc. **Pick: A — ship minimal doc** (30-50
lines; matches `docs/usage/knowledge/` directory pattern from Phase
13's 9 stub pages).

### N7 — Drop Phase 16 NEXT prompt amendment from cleanup list

That prompt initiated THIS chat; amending it post-hoc is strange.
**Pick: B — add one-line "Superseded by retirement" trailer**
(future-grep value beats historical-purity).

---

## §5 — Round 4: stopping criterion (M1-M6)

### M1 — CHANGELOG.md entry forgotten

**Pick: A — ship entry** (convention match).

### M2 — mkdocs.yml nav entry for `versioning.md`

**Pick: A — add nav entry** (under `Usage > Knowledge`).

### M3 — Two-repo commit coordination

ADRs live in `/Layered Intelligence/` parent tree; code/docs/memory
live in `halvim_mindsos`. **Pick: B — parent-tree ADR amendment
FIRST, then halvim_mindsos PR cites it** (cross-link captures the
parent SHA; mirrors Phase 14a pattern).

### M4 — PHASE_MAP §3 phase-index table strikethrough

**Pick: A — strike table row to match detail row** (table consistency
+ future-grep `Phase 17` surfaces retirement).

### M5 — Branch + PR title

**Pick: A — branch `phase-17`; PR title "Phase 17 — RETIRED: vacuous
against ADR-0150 §closure; `versions_in_role` enumerator + CLI verb
+ ADR-0150 §amendment-3 (#26)"** (honest signalling).

### M6 — Stop iterating

Four rounds; diminishing returns; pushbacks are now formatting-level.
Phase 16 ran 5 rounds and shipped clean. **Pick: A — stop after this
round; draft retirement PR contents next** (if something small
surfaces during drafting, surface it as B-17-T* hotfix per
shipped-phase pattern).

---

## §6 — Final picks summary (26 picks)

| # | Concern | Pick |
|---|---------|------|
| P1 | step(version=) vacuous | A — cosmetic only |
| P2 | PROMOTED no producer | A — retire (initial); refined by N1 |
| P3 | ADR-0142 shifting | A — properties only, deprecation-target |
| R1 | PB-13 CLI verbs separate | A — land CLI verbs in retirement chat |
| R2 | Tombstone mechanics | C — tombstone + 8-file cross-ref cleanup |
| R3 | versions_in_role home | A — retirement chat (5-LOC method) |
| R4 | PROMOTED reader home | B (revised) — no L2 reader; Phase 33 covers |
| R5 | Chat scope | A — retirement-PR with code + docs |
| R6 | ADR-0150 amendment | A — §amendment-3 |
| R7 | Memory shape | A — new `_retired.md` type |
| N1 | R4 correction | B — Phase 33 symmetric covers; no L2 reader |
| N2 | active-version drop closure | A — amend Phase 14 PB-13 |
| N3 | Version bump | A — `+phase16 → +phase17` everywhere |
| N4 | Tests dir | A — `tests/phase_17/` |
| N5 | Amendment escape language | A — escape clause included |
| N6 | versioning.md | A — ship minimal doc |
| N7 | Phase 16 NEXT prompt | B — trailer line |
| M1 | CHANGELOG entry | A — ship |
| M2 | mkdocs nav | A — add |
| M3 | Two-repo order | B — ADR first, code PR second |
| M4 | §3 table strike | A — strike row |
| M5 | Branch + PR title | A — descriptive |
| M6 | Stop iterating | A — sign-off + draft |

(Note: R4 is counted once; N1 is the revision that picked the final
home. Picks total 23 active + 3 revised-by-later = 26 in the
ledger; revised picks are reconciled in §6 toward final state.)

---

## §7 — Final shipped state

**Parent tree (`/Layered Intelligence/`):**

* `docs/decisions/adr/0150-l2-knowledge-lifecycle.md` — §amendment-3
  added (version-dispatch model lock + escape clause).

**halvim_mindsos:**

Code (3 sites):

* `mindsos_knowledge/metagraph_view.py` — new `versions_in_role`
  method; 3 docstring cleanups (header + `graphs_by_role` +
  `get_node` + `step`).
* `mindsos_cli/commands/knowledge.py` — new `versions` CLI verb +
  `_load_metagraph_or_die` helper.
* Version bump across 5 `__init__.py` files + `manifest.toml` +
  `pyproject.toml` + `docker-compose.yml` (2 image tags): `+phase16
  → +phase17`.

Tests (1 new dir):

* `tests/phase_17/__init__.py`
* `tests/phase_17/test_versions_in_role.py` — method behaviour
* `tests/phase_17/test_cli_knowledge_versions.py` — CLI verb
* `tests/phase_17/test_retirement_sentinels.py` — assert no
  `version=` kwarg on `step`; assert ADR-0150 §amendment-3 exists.

Docs (3 sites + 1 new):

* `docs/usage/knowledge/versioning.md` — NEW user-facing doc.
* `mkdocs.yml` — nav entry.
* `docs/changelog/CHANGELOG.md` — Phase 17 retirement entry +
  `last_design_only_phase: 17`.
* `docs/concepts/global-local.md` — 3 sites updated (table row;
  step kwarg defer; CLI verbs defer).
* `docs/concepts/knowledge-lifecycle.md` — table row rewritten.
* `docs/concepts/admin-global-shipping.md` — version-graph paragraph
  rewritten.

Design logs (2 sites):

* `confirmation_docs/PHASE_MAP.md` — §17 detail strikethrough +
  RETIRED block; §3 table row strike.
* `confirmation_docs/PHASE_14_DESIGN_LOG.md` — PB-13 closure
  amendment + PB-15 vacated amendment.
* `confirmation_docs/PHASE_17_RETIREMENT_DESIGN_LOG.md` — this file.
* `confirmation_docs/PHASE_16_NEXT_CHAT_PROMPT.md` — trailer line.

Exit:

* `confirmation_docs/PHASE_18_NEXT_CHAT_PROMPT.md` — handoff prompt.

Memory (parent-tree path, but written by retirement chat):

* `spaces/.../memory/project_mindsos_phase_17_retired.md` — NEW.
* `spaces/.../memory/MEMORY.md` — index row added.

---

## §8 — Why not tag

Tag-free per Phase 15b design-only precedent extended to "design-
only-with-code" — the shipped code surface is ~5 LOC of method + 1
CLI verb + amendments. Tag would imply this is a code-shipping phase
warranting a release.yml run + GitHub Release; the substantive
deliverable is the architectural lock (ADR-0150 §amendment-3) +
PHASE_MAP closure, not the absorbing code.

Phase 18 (next coded phase) tags as `phase-18-confirmed` per the
shipped-phase precedent.

---

## §9 — Why this is the last design round

Four rounds total. P1-P3 were structural ("does Phase 17 even make
sense?"). R1-R7 were retirement mechanics. N1-N7 were mechanics-of-
mechanics. M1-M6 surfaced CHANGELOG / mkdocs / branch name — the
diminishing-returns frontier.

Phase 16 ran 5 design rounds before shipping clean. We stopped one
round earlier because (a) the retirement is structurally simpler
than Phase 16's reframe (no new ADR §amendment battery; one lock),
(b) the pushback ledger had converged to mechanics, (c) M6's
explicit "stop or continue" pick was sign-off.

Any small surface unsurfaced becomes a B-17-T* hotfix (precedent:
Phase 15a/16 batched 3 hotfixes each post-design).
