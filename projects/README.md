# MindsOS Projects — Intake Index

> Three sister projects intended for integration into MindsOS. Each was analyzed in the 2026-05-28 housekeeping + intake chat. Per-project folders contain (a) source materials, (b) an analysis document triaging propositions against shipped MindsOS, and (c) a future-chat prompt for the design-resolution chat that finalizes the project's installation.

> [!NOTE]
> **This index covers the three intake sister projects only.** `projects/` has since accumulated
> other lanes — `amii_study/`, `brain-viewer/`, `maintenance/`, `skill_acquisition/`,
> `decision_records_demo/` — that are not sister projects and are not tracked in the tables
> below. Only `decision_records_demo/` is documented here; the rest are undocumented and
> someone should say what they are.

## Non-sister lanes

**`decision_records_demo/`** — the **Decision Records demo** lane. Zero-revenue;
sales evidence, not product. It owns no architectural mechanism (RULES §8) and nothing in
`mindsos_*` imports it. Design decisions do not live there — they live in
`confirmation_docs/DECISION_RECORDS_{DEMO_PLAN,V0_SLICE_PLAN,AGREED_CHANGES}.md`. The folder
holds demo and evidence *research* only: domain material, sourced taxonomies, scenario notes.

Two boundaries recorded there, both learned the hard way:

- `Projects/Sanmyaku-GTM/` is **meeting operations with real humans** and is not this lane.
  Demo and research artifacts never go there.
- `DECISION_RECORDS_DEMO_PLAN.md` §2.5 is five seeded synthetic cases — **no intake-routing
  beat, no claim-classification stage, no lines-of-business taxonomy.** A 2026-08-11 task
  prompt quoted one; the quote is not in the file (md5 `83fe6c6b93f7a09ff4853f0aff43ec70`).
  **Grep a cited file for a quoted §-reference before building on it.**

## Layout

```
projects/
├── README.md                       ← this file
├── dwf_mapping/                    ← DOLCE-WordNet-FrameNet alignment (knowledge installation)
│   ├── ANALYSIS.md                 — A/B/C/D triage + Phase-38 carry-forward + analysis-PB list
│   ├── FUTURE_CHAT_PROMPT.md       — design-resolution chat seed
│   └── source/                     — 53 files from "Dolce - WordNet - FrameNet Mapping.zip"
├── wsd/                            ← Word Sense Disambiguation skill (skill acquisition; FIRST)
│   ├── ANALYSIS.md
│   ├── FUTURE_CHAT_PROMPT.md
│   └── source/                     — 21 files from "Word Sense Disambiguation.zip"
└── fol/                            ← First-Order Logic skill (skill acquisition; SECOND)
    ├── ANALYSIS.md
    ├── FUTURE_CHAT_PROMPT.md
    └── source/                     — 9 files from "First Order Logic Layer for MindsOS.zip"
```

## Project category vocabulary

Per the user 2026-05-28:

- **Knowledge acquisition** — process of installing finished knowledge artifacts into MindsOS L2 as one or more role-graphs. Renamed from earlier "knowledge installation." DWF is the load-bearing first example.
- **Skill acquisition** — process of installing a multi-layer intelligent system (a "skill") into MindsOS, spanning L1+L2+L3+L4+L5 artifacts as a coherent unit. Renamed from earlier "intelligence installation." WSD + FOL are the two named instances.

Both processes are designed in future chats, not in the 2026-05-28 intake chat.

## Project status summary

| Project | Status | Source completeness | Triage shape | Design saturation |
|---|---|---|---|---|
| DWF Mapping | v6 substantially finished; v7 unexecuted | **Incomplete** — `release/`, `release-v6/`, `FINAL_PACKAGE/` directories are empty in the zip; ready-to-import bundles missing. Master TSV (16MB) at workspace root is the canonical input | A=8, B=7, C=7 (deferred), **D=3** | Knowledge-acquisition chat resolves PB-7 (naming) and PB-1 (AlignmentsImporter body) first |
| WSD | Goal-finalized; pre-code | Complete | A≈13 across layers, **B≈70+** across layers, **C≈15** across layers (incl. 3 architectural reframes + 7 L4 critique-push picks), D=several | Skill-acquisition chat resolves section A first; many sections belong in L4/L5 plan chat instead |
| FOL | Mid-design; 13 open pushbacks unresolved | Complete (design materials only; no shippable artifact) | A=5, B=24, C=5, D=3 | Skill-acquisition chat (downstream of WSD); inherits WSD's resolutions |

## Recommended chat ordering

Based on dependency analysis (see each FUTURE_CHAT_PROMPT.md):

1. ~~**L4/L5 plan chat**~~ — **DONE** (Chats A/B 2026-05; shipped Phases 46-48).
2. ~~**Skill-acquisition process chat**~~ — **CLOSED 2026-06-09** (`confirmation_docs/SKILL_ACQUISITION_PROCESS_DESIGN_LOG.md` + `SKILL_ACQUISITION_PROCESS_PHASE_MAP.md`); **install lifecycle SHIPPED at Phase 50 (2026-06-10)** — driver at `mindsos_server/skills/`, tag `phase-50-confirmed`.
3. **WSD installation chat** — **NEXT.** Inherits L4/L5 plan resolutions + the Phase-50 install driver (`SKILL_ACQUISITION_PROCESS_PHASE_MAP.md §5` + `PHASE_50_DESIGN_LOG.md` bundle-author rules).
4. **FOL installation chat** — applies skill acquisition to FOL. Inherits WSD resolutions on shared propositions (sense-correlations, learned-parameters, Coherence Loop fate, 7 L4 pushes).
5. **Knowledge-acquisition process chat + DWF installation** — independent of skill acquisition (DWF is L2-only). Can run in parallel with chats 3-4.

Original upstream-blocker note retained for forensics: the L4/L5 plan chat resolved all 7 critique pushes at Chat A (2026-05-28).

## Cross-project shared blockers

| Blocker | DWF | WSD | FOL | Owner |
|---|---|---|---|---|
| 7 L4 critique pushes pending | — | yes (C-L4-1..C-L4-7) | yes (pushback #1, #2, #5) | L4/L5 plan |
| Coherence Loop fate | — | yes (§6.1) | yes (pushback #2-#5) | Shared resolution |
| `sense-correlations` + `learned-parameters` not shipped (R0-PB-9) | — | yes | yes | L4/L5 plan or skill acquisition |
| L1 InterGraph naming reconciliation | yes (D1; 3 conventions ship in MindsOS) | yes (C-L1-1) | — | MindsOS internal; resolve before any consumer ships |
| `AlignmentsImporter` body unshipped | yes (D2; PRIORITY) | — | — | Knowledge acquisition |

## Source completeness audit (key finding)

The DWF zip is **missing the ready-to-import bundles** (5 formats × 2 versions). Master TSV at workspace root (16MB, 104,728 rows vs HANDOFF-claimed 107,518) is the canonical input. Either the bundles are at a different location not provided here, or they need to be generated by re-running the DWF export pipeline.

WSD + FOL zips are complete (design materials only; no shippable artifact in either project).

---

*End of projects/README.md*
