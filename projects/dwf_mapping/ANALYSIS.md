# DWF Mapping — Analysis vs Shipped MindsOS

> **Project:** DOLCE-DULplus ↔ Open English WordNet (v4) + OEWN ↔ FrameNet (v6 expansion).
> **Project status:** Substantially finished, not finalized. v6 is the latest shipped version; v7 (triangle-driven DOLCE revision) is named on the roadmap but not executed. HANDOFF claims 100% coverage of OEWN POS but the workspace master TSV has 104,728 rows vs the claimed 107,518 (2,790 row discrepancy unresolved).
> **Analysis date:** 2026-05-28.
> **Source materials:** `projects/dwf_mapping/source/` — 53 files copied from the user-supplied zip. The HANDOFF references `release-v4/`, `release-v6/`, `FINAL_PACKAGE/`, and `scripts/` directories which exist in the zip but are empty; the ready-to-import bundles (Cypher / MeTTa / JSON-LD / NTriples / CSV) and the v6 OEWN↔FrameNet master TSV named in CHANGES_v5_to_v6.md are **not in the zip**.
> **Triage shape:** four bins — A (already implemented in MindsOS), B (not implemented + no conflict; additive), C (not implemented + would conflict; design decision required), D (shipped in MindsOS but inconsistent/incomplete — must reconcile before importing this project).

---

## 1. Source-material inventory

| File | Size | Role |
|---|---|---|
| `HANDOFF_latest.md` | 24KB | Authoritative project handoff at v6; supersedes v4/v5 |
| `HANDOFF_v4.md`, `HANDOFF_v5.md` | 24KB+12KB | Historical context; superseded |
| `CHANGES_v5_to_v6.md` | 4KB | Documents the v6 OEWN↔FrameNet extension; v7 plan |
| `oewn-dulplus-master.tsv` | 16MB | **Primary deliverable.** 104,728 rows. Columns: oewn_id, pos, dulplus_class, method, primary_lemma, provenance, gloss |
| `oewn-dulplus-alignment.tsv` | 11MB | Phase 1 intermediate format. 69,074 rows. Columns: oewn_id, dulplus_class, source, framester_id, pos, ili, primary_lemma, definition |
| `decisions-top57.tsv` | 24KB | Phase 7 hand-reviewed top-57 doubts with rationale |
| `decisions-full.tsv` | (referenced; not in zip) | Phase 8 systematic 10,650 decisions |
| `phase9f-judgements-consolidated.tsv` | 92KB | 500-synset stratified LLM-judge sample |
| `doubtful-mappings-register.tsv` | 3MB | 10,650 doubt entries with priority scores |
| `dulplus-reference.md` | (small) | DULplus class reference used by LLM judges; lists `dul:` prefix vocabulary |
| `english-wordnet-2025.ttl` | 3MB | OEWN 2025 source data |
| 16 Python scripts | total ~600KB | Pipeline machinery (phase1-9f); not deliverables |
| 7 phase-report markdown docs | mixed | Per-phase implementation reports |
| 4 empty directories: `release/`, `release-v6/`, `FINAL_PACKAGE/`, `scripts/` | — | **MISSING content — likely contains the ready-to-import bundles per HANDOFF §3** |

---

## 2. Triage table

### Bin A — Already implemented in shipped MindsOS

| # | Proposition | Implementing phase / file | Notes |
|---|---|---|---|
| A1 | DOLCE loaded as typed L2 subgraph (HANDOFF D-MI-1 assumption) | Phase 15a `mindsos_admin/importers/dolce.py` | DolceImporter writes to `ontology` Global role-graph |
| A2 | OEWN loaded as typed L2 subgraph (D-MI-1 assumption) | Phase 15a `mindsos_admin/importers/oewn.py` | OewnImporter writes to `lexicon` Global role-graph |
| A3 | FrameNet loaded as typed L2 subgraph (D-MI-1 assumption) | Phase 15a `mindsos_admin/importers/framenet.py` | FrameNetImporter writes to `concepts` Global role-graph |
| A5 | Alignment role-graph is Global-only at v1 | ADR-0150 §amendment-1 | `ensure_local_role_graph` rejects alignment prefixes |
| A6 | Repo-shippable ImporterProtocol pattern | Phase 15a | `mindsos_admin/importers/__init__.py` defines ImporterProtocol with `target_roles` self-description |
| A7 | Alignment edge vocabulary includes SKOS-cognate types | Phase 13 `mindsos_knowledge/schemas/alignment.py` | Ships 8-type closed vocab: LEXICALIZES, EXACT_MATCH, **CLOSE_MATCH**, NARROWER_THAN, BROADER_THAN, EVOKES, INSTANCE_OF_CLASS, RELATED_TO. `extra_edge_types` kwarg lets importer add types per-graph |
| A8 | `AlignmentAnchor` shared-anchor pattern as alignment node type | Phase 13 `schemas/alignment.py` | One anchor per source entity carries `ref:<role>`; entity in N mappings has ONE anchor hosting N outgoing edges |

### Bin B — Not implemented + no conflict (additive; needs go/no-go for future implementation)

| # | Proposition | Why no conflict | Where it lands in MindsOS |
|---|---|---|---|
| B1 | OEWN↔DOLCE alignment data (104,728 rows in master TSV) | This IS the project deliverable; needs consumer | Would populate `alignment:lexicon<->ontology` Global role-graph |
| B2 | OEWN↔FrameNet alignment data (v6; 38,998 mappings claimed) | Additive second alignment graph | Would populate `alignment:concepts<->lexicon` (sorted naming) — **but the v6 master TSV file is NOT IN THE ZIP** |
| B3 | Per-edge confidence score 0..1 derived from method priority (D-MI-3) | MindsOS alignment edges have no confidence schema; additive | Edge property `confidence: float` added to alignment edge schema |
| B4 | Per-edge method + provenance properties (D-MI-1 design) | Additive edge metadata | Properties `method: str`, `provenance: str` added to alignment edge schema |
| B5 | DWF uses `BROADER_THAN` / `CLOSE_MATCH` SKOS-cognate semantics | MindsOS already ships these as native edge types | Direct mapping: `skos:broadMatch` → `BROADER_THAN`; `skos:closeMatch` → `CLOSE_MATCH` |
| B6 | Idempotent re-runnable import (D-MI-5) | Mirrors Phase 15a importer idempotency contract | New importer follows existing pattern |
| B7 | Method-priority deduplication (D-04) | Pure importer logic | Importer behavior, not schema |

### Bin C — Not implemented + would conflict (design decision required in future chat)

| # | Proposition | Conflict surface | Picks for future chat (defaults documented in FUTURE_CHAT_PROMPT.md) |
|---|---|---|---|
| C1 | **DOLCE version: DULplus (207 classes)** — DWF target | MindsOS DolceImporter pins **DOLCE-DUL 4.1 (107 classes)**. DULplus is a documented superset; 65 distinct classes used per HANDOFF §12. Without side-by-side OWL files the exact class-IRI overlap can't be predicted | Per user-deferred DWF-PB-3 |
| C2 | **OEWN version: 2025** — DWF source | MindsOS OewnImporter pins **OEWN 2024**. OEWN release notes between 2024 and 2025 are mostly additive but the 2,790-row discrepancy between HANDOFF's 107,518 claim and the workspace TSV's 104,728 rows suggests some divergence | Per user-deferred DWF-PB-3 |
| C3 | **FrameNet version: unspecified in v6 docs** | MindsOS pins FrameNet 1.7. CHANGES_v5_to_v6 doesn't name the FrameNet release. v6 FrameNet alignment file is not in zip — version verification blocked | Per user-deferred DWF-PB-3 |
| C4 | Custom OEWN IRI scheme `https://en-word.net/id/oewn-{offset}-{pos}` (HANDOFF D-MI-1 §"Assumptions NOT yet verified") | MindsOS source-prefix table has `oewn-` → ROLE_LEXICON but the full IRI form within MindsOS may differ. The DWF master TSV uses `oewn-00001740-n` (offset-pos) which matches MindsOS's `oewn-` prefix convention. The IRI scheme is mostly compatible | Per user-deferred design |
| C6 | "Multi-class collapsed to single class via method priority" (HANDOFF D-04) | MindsOS alignment schema (shared-anchor pattern) allows multi-edge per anchor; collapsing loses 791 within-synset multi-class assignments per HANDOFF §9.2 open question | Per user-deferred DWF-PB-2 |
| C7 | `dul:Quality + dct:relation annotation` for pertainyms (HANDOFF D-05) | MindsOS has no `dct:` (Dublin Core Terms) machinery on alignment edges; would need a property name decision | Per user-deferred design |
| C8 | Import to Global vs Local pending audit (DWF-PB-2 + DWF-PB-5) | DWF reports 89.2% acceptable precision = ~11.5k known-wrong edges. Importing to Global means every user sees those errors. ADR-0150 §am-1 forbids Local alignment graphs at v1 | Per user-deferred DWF-PB-2/5 |

### Bin D — Shipped in MindsOS but inconsistent or incomplete; must reconcile before importing

| # | Issue | Evidence | Reconciliation owner |
|---|---|---|---|
| D1 | **Three different alignment role-graph naming conventions ship in MindsOS code + docs + tests.** | `identifiers.py:303` `alignment_role()` returns `alignment:<a><->b>` (arrow). ADR-0150 §82 + `bootstrap.py` use `alignment:<a>:<b>` (colon). `tests/phase_36/test_validators.py:153` exercises `alignment:<a>-<b>` (dash). All three appear in shipped tests | Must pick one canonical form before DWF importer can target a role-graph |
| D2 | **`AlignmentsImporter` body never shipped.** | `mindsos_admin/importers/` contains only `dolce.py`, `oewn.py`, `framenet.py`. Phase 15b shipped design-only per memory `[[project-mindsos-phase-15b-shipped]]`; the body was deferred to "Phase 28 review closure" but never landed | **PRIORITY per user pick on DWF-PB-4.** Body design is now part of the knowledge-acquisition future-chat scope. Carry-forward inherited from Phase 38 §4 item 1 |
| D3 | **Phase 15b deferred FN↔WN extraction + per-edge IRI builder + idempotency.** | Memory `[[project-mindsos-phase-15b-shipped]]` documents these as "re-deferred to Phase 28 review closure" — also never shipped | Part of D2 same scope |

---

## 3. Cross-reference with Phase 38 19-item carry-forward

The DWF project intersects multiple items from `PHASE_38_DESIGN_LOG §4`:

| Phase 38 item | DWF intersection |
|---|---|
| §4.10 strict-lift / Model C remediation | Likely moot post-housekeeping (50 mkdocs warnings, all filename-drift in summary pages) |
| §4.16 `usage/knowledge/memories.md` §6 drift | Unrelated to DWF |
| §4.17 `concepts/promotion-bridge.md` Phase 24 amendment verification | Unrelated to DWF |
| (new) `AlignmentsImporter` body unshipped | **D2 above** — promotes from Phase 15b/28 backlog to DWF-knowledge-acquisition scope |

---

## 4. Documented design pushbacks (deferred to future chat)

User picks confirmed in this analysis chat:
- **DWF-PB-1** — Missing release artifacts. User confirmed: files inside zip in their folders. Re-probe confirmed the release dirs ARE empty in the zip; the ready-to-import bundles were not extracted. Listed in FUTURE_CHAT_PROMPT.md as a load-bearing input gap.
- **DWF-PB-2** — "Finalized" is overstated. Deferred.
- **DWF-PB-3** — OEWN/DOLCE/FrameNet version drift. Deferred.
- **DWF-PB-4** — `AlignmentsImporter` doesn't exist. **PRIORITY** per user. To be designed alongside the knowledge-acquisition process in the future chat.
- **DWF-PB-5** — Local-vs-Global alignment tension. Deferred.
- **DWF-PB-6** — Predicate choice (now downgraded — MindsOS ships CLOSE_MATCH / BROADER_THAN / NARROWER_THAN already; conflict was over-stated).

Analysis-side corrections logged in this chat:
- **PB-A1** — DWF-PB-6 was over-stated; SKOS-cognate edge types already ship. Moved C5 → B5.
- **PB-A2** — Triage A4 (naming convention) was over-stated; three conventions ship. Created D1.
- **PB-A3** — DWF-PB-3 (version drift) asserted breakage without side-by-side OWL files; documented as analysis-blocked.
- **PB-A4** — DWF-PB-4 body design space is wider than I sketched; AlignmentAnchor shared-anchor pattern adds grouping requirement.
- **PB-A5** — v7 (`FINAL_PACKAGE/` empty dir) reinforces DWF-PB-2: the project's own roadmap names an unexecuted phase.
- **PB-A6** — Reading `dulplus-reference.md` confirmed `dul:` IRI prefix; class IRIs match the DULplus canonical naming.

---

*End of analysis. See `FUTURE_CHAT_PROMPT.md` for the design-resolution chat seed.*
